"""
Complaints router — handles citizen complaint filing, tracking, and dispute.

Endpoints:
  POST   /api/complaints              — file a new complaint
  GET    /api/complaints              — list recent complaints (officer view)
  GET    /api/complaints/{id}         — track complaint status
  PUT    /api/complaints/{id}/resolve — officer marks resolved
  POST   /api/complaints/{id}/dispute — citizen disputes resolution
  WS     /api/complaints/{id}/ws      — real-time status updates
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.db import get_driver, is_db_available

# ---------------------------------------------------------------------------
# In-memory fallback store (used when Neo4j unavailable — demo mode)
# ---------------------------------------------------------------------------
_DEMO_COMPLAINTS: dict[str, dict] = {}

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Complaints"])

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}

    async def connect(self, complaint_id: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(complaint_id, []).append(ws)

    def disconnect(self, complaint_id: str, ws: WebSocket):
        if complaint_id in self.active:
            try:
                self.active[complaint_id].remove(ws)
            except ValueError:
                pass

    async def broadcast(self, complaint_id: str, data: dict):
        for ws in list(self.active.get(complaint_id, [])):
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(complaint_id, ws)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ComplaintCreate(BaseModel):
    complaint_type: str
    description: str
    severity_estimate: Literal["low", "medium", "high", "critical"] = "medium"
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    infra_node_id: str | None = None
    source: Literal["voice", "text"] = "text"
    offline_draft_id: str | None = None  # for syncing offline submissions


class ComplaintTimeline(BaseModel):
    event: str
    timestamp: str
    actor: str | None = None


class ComplaintResponse(BaseModel):
    id: str
    complaint_type: str
    description: str
    severity_estimate: str
    lat: float
    lng: float
    status: str
    filed_at: str
    officer_name: str | None = None
    estimated_resolution: str | None = None
    timeline: list[ComplaintTimeline] = []
    tracking_url: str


class ComplaintSummary(BaseModel):
    id: str
    complaint_type: str
    description: str
    severity_estimate: str
    status: str
    filed_at: str
    lat: float
    lng: float


class DisputeRequest(BaseModel):
    citizen_verdict: Literal["fixed", "still_broken"]
    notes: str | None = None


# ---------------------------------------------------------------------------
# POST /api/complaints — file new complaint
# ---------------------------------------------------------------------------
@router.post("/complaints", response_model=ComplaintResponse, status_code=201)
async def file_complaint(
    body: ComplaintCreate,
):
    complaint_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    initial_timeline = [{"event": "Complaint filed", "timestamp": now, "actor": "citizen"}]

    if not is_db_available():
        # Save to in-memory store for demo
        _DEMO_COMPLAINTS[complaint_id] = {
            "id": complaint_id,
            "complaint_type": body.complaint_type,
            "description": body.description,
            "severity_estimate": body.severity_estimate,
            "lat": body.lat,
            "lng": body.lng,
            "status": "filed",
            "filed_at": now,
            "source": body.source,
            "timeline": initial_timeline,
        }
        return ComplaintResponse(
            id=complaint_id,
            complaint_type=body.complaint_type,
            description=body.description,
            severity_estimate=body.severity_estimate,
            lat=body.lat,
            lng=body.lng,
            status="filed",
            filed_at=now,
            timeline=[ComplaintTimeline(**t) for t in initial_timeline],
            tracking_url=f"/track/{complaint_id}",
        )

    # DB path
    driver = await get_driver()
    complaint_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    initial_timeline = json.dumps([{"event": "Complaint filed", "timestamp": now, "actor": "citizen"}])

    async with driver.session() as session:
        await session.run(
            """
            CREATE (c:Complaint {
                id: $id,
                complaint_type: $complaint_type,
                description: $description,
                severity_estimate: $severity,
                lat: $lat,
                lng: $lng,
                infra_node_id: $infra_node_id,
                status: 'filed',
                filed_at: $now,
                source: $source,
                offline_draft_id: $draft_id,
                timeline: $timeline
            })
            """,
            id=complaint_id,
            complaint_type=body.complaint_type,
            description=body.description,
            severity=body.severity_estimate,
            lat=body.lat,
            lng=body.lng,
            infra_node_id=body.infra_node_id,
            now=now,
            source=body.source,
            draft_id=body.offline_draft_id,
            timeline=initial_timeline,
        )

        # Link to infrastructure node if provided
        if body.infra_node_id:
            await session.run(
                """
                MATCH (c:Complaint {id: $cid}), (n:Infrastructure {id: $nid})
                MERGE (c)-[:ABOUT]->(n)
                """,
                cid=complaint_id,
                nid=body.infra_node_id,
            )

    return ComplaintResponse(
        id=complaint_id,
        complaint_type=body.complaint_type,
        description=body.description,
        severity_estimate=body.severity_estimate,
        lat=body.lat,
        lng=body.lng,
        status="filed",
        filed_at=now,
        timeline=[ComplaintTimeline(event="Complaint filed", timestamp=now, actor="citizen")],
        tracking_url=f"/track/{complaint_id}",
    )


# ---------------------------------------------------------------------------
# GET /api/complaints — list recent complaints (officer / dashboard use)
# ---------------------------------------------------------------------------
@router.get("/complaints", response_model=list[ComplaintSummary])
async def list_complaints(
    status: str | None = Query(default=None, description="Filter by status"),
    limit: int = Query(default=20, ge=1, le=100),
    driver=Depends(get_driver),
):
    """Return recent complaints, optionally filtered by status."""
    async with driver.session() as session:
        if status:
            result = await session.run(
                """
                MATCH (c:Complaint {status: $status})
                RETURN c { .id, .complaint_type, .description, .severity_estimate,
                            .status, .filed_at, .lat, .lng } AS complaint
                ORDER BY c.filed_at DESC LIMIT $limit
                """,
                status=status,
                limit=limit,
            )
        else:
            result = await session.run(
                """
                MATCH (c:Complaint)
                RETURN c { .id, .complaint_type, .description, .severity_estimate,
                            .status, .filed_at, .lat, .lng } AS complaint
                ORDER BY c.filed_at DESC LIMIT $limit
                """,
                limit=limit,
            )
        rows = await result.data()

    return [ComplaintSummary(**r["complaint"]) for r in rows]


# ---------------------------------------------------------------------------
# GET /api/complaints/{id} — track complaint
# ---------------------------------------------------------------------------
@router.get("/complaints/{complaint_id}", response_model=ComplaintResponse)
async def track_complaint(complaint_id: str):
    # Demo mode: look up from in-memory store
    if not is_db_available():
        c = _DEMO_COMPLAINTS.get(complaint_id)
        if not c:
            raise HTTPException(status_code=404, detail=f"Complaint '{complaint_id}' not found.")
        return ComplaintResponse(
            id=c["id"],
            complaint_type=c["complaint_type"],
            description=c["description"],
            severity_estimate=c["severity_estimate"],
            lat=c["lat"],
            lng=c["lng"],
            status=c["status"],
            filed_at=c["filed_at"],
            timeline=[ComplaintTimeline(**t) for t in c.get("timeline", [])],
            tracking_url=f"/track/{complaint_id}",
        )
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Complaint {id: $id})
            OPTIONAL MATCH (c)-[:ASSIGNED_TO]->(o:Officer)
            RETURN c {
                .id, .complaint_type, .description, .severity_estimate,
                .lat, .lng, .status, .filed_at,
                .estimated_resolution, .timeline
            } AS complaint,
            o.first_name AS officer_name
            """,
            id=complaint_id,
        )
        record = await result.single()

    if not record:
        raise HTTPException(status_code=404, detail=f"Complaint '{complaint_id}' not found.")

    c = record["complaint"]
    timeline_raw = c.get("timeline") or "[]"
    try:
        timeline = json.loads(timeline_raw) if isinstance(timeline_raw, str) else timeline_raw
    except Exception:
        timeline = []

    return ComplaintResponse(
        id=c["id"],
        complaint_type=c["complaint_type"],
        description=c["description"],
        severity_estimate=c["severity_estimate"],
        lat=c["lat"],
        lng=c["lng"],
        status=c["status"],
        filed_at=c["filed_at"],
        officer_name=record["officer_name"],
        estimated_resolution=c.get("estimated_resolution"),
        timeline=[ComplaintTimeline(**t) for t in timeline],
        tracking_url=f"/track/{complaint_id}",
    )


# ---------------------------------------------------------------------------
# PUT /api/complaints/{id}/resolve — officer marks resolved
# ---------------------------------------------------------------------------
@router.put("/complaints/{complaint_id}/resolve")
async def resolve_complaint(complaint_id: str, driver=Depends(get_driver)):
    now = datetime.now(timezone.utc).isoformat()
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Complaint {id: $id})
            SET c.status = 'resolved_pending_citizen',
                c.resolved_at = $now
            RETURN c.id AS id
            """,
            id=complaint_id,
            now=now,
        )
        record = await result.single()

    if not record:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    await manager.broadcast(complaint_id, {"status": "resolved_pending_citizen", "timestamp": now})
    return {"id": complaint_id, "status": "resolved_pending_citizen"}


# ---------------------------------------------------------------------------
# POST /api/complaints/{id}/dispute — citizen confirms or disputes resolution
# ---------------------------------------------------------------------------
@router.post("/complaints/{complaint_id}/dispute")
async def dispute_or_confirm(
    complaint_id: str,
    body: DisputeRequest,
    driver=Depends(get_driver),
):
    now = datetime.now(timezone.utc).isoformat()
    new_status = "closed" if body.citizen_verdict == "fixed" else "reopened"

    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Complaint {id: $id})
            SET c.status = $status, c.citizen_verdict = $verdict, c.verdict_at = $now
            RETURN c.id AS id
            """,
            id=complaint_id,
            status=new_status,
            verdict=body.citizen_verdict,
            now=now,
        )
        record = await result.single()

    if not record:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    await manager.broadcast(complaint_id, {"status": new_status, "timestamp": now})

    # Write to trust ledger
    trust_event = "citizen_confirmed_fix" if body.citizen_verdict == "fixed" else "citizen_disputed_fix"
    async with driver.session() as session:
        await session.run(
            """
            CREATE (t:TrustLedger {
                id: $tid,
                complaint_id: $cid,
                ward_id: 'connaught_place',
                event_type: $event_type,
                actor: 'citizen',
                notes: $notes,
                recorded_at: $now
            })
            """,
            tid=str(uuid.uuid4()),
            cid=complaint_id,
            event_type=trust_event,
            notes=body.notes,
            now=now,
        )

    return {"id": complaint_id, "status": new_status, "verdict": body.citizen_verdict}


# ---------------------------------------------------------------------------
# WebSocket /api/complaints/{id}/ws — real-time status updates
# ---------------------------------------------------------------------------
@router.websocket("/complaints/{complaint_id}/ws")
async def complaint_ws(complaint_id: str, websocket: WebSocket):
    await manager.connect(complaint_id, websocket)
    try:
        while True:
            # Keep connection alive; client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(complaint_id, websocket)
