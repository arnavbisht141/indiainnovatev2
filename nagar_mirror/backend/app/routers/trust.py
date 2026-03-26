"""
Trust Ledger router — immutable record of citizen/officer verdicts.
Feeds the Ward Trust Score radar chart.

Endpoints:
  POST /api/trust/record      — write an entry to the trust ledger
  GET  /api/trust/score/{ward_id} — compute aggregate trust dimensions
  GET  /api/trust/trend/{ward_id} — 12-week trend data for charts
  GET  /api/trust/narratives/{ward_id} — top 5 unresolved high-grief complaints
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import get_driver, is_db_available

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Trust"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class TrustRecord(BaseModel):
    complaint_id: str
    ward_id: str
    event_type: Literal[
        "citizen_confirmed_fix",
        "citizen_disputed_fix",
        "officer_resolved",
        "auto_escalated",
        "proactive_action",
    ]
    actor: Literal["citizen", "officer", "system"] = "citizen"
    notes: str | None = None


class TrustDimensions(BaseModel):
    ward_id: str
    resolution_authenticity: float
    proactive_rate: float
    recurrence_prevention: float
    response_equity: float
    moral_alert_response: float
    overall_score: float
    computed_at: str


class WeeklyScore(BaseModel):
    week: str  # ISO date of Monday
    overall_score: float


class NarrativeComplaint(BaseModel):
    id: str
    complaint_type: str
    description: str
    days_open: int
    severity_estimate: str


# ---------------------------------------------------------------------------
# POST /api/trust/record
# ---------------------------------------------------------------------------
@router.post("/trust/record", status_code=201)
async def record_trust_event(body: TrustRecord, driver=Depends(get_driver)):
    record_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    async with driver.session() as session:
        await session.run(
            """
            CREATE (t:TrustLedger {
                id: $id,
                complaint_id: $complaint_id,
                ward_id: $ward_id,
                event_type: $event_type,
                actor: $actor,
                notes: $notes,
                recorded_at: $now
            })
            """,
            id=record_id,
            complaint_id=body.complaint_id,
            ward_id=body.ward_id,
            event_type=body.event_type,
            actor=body.actor,
            notes=body.notes,
            now=now,
        )
    return {"id": record_id, "recorded_at": now}


# ---------------------------------------------------------------------------
# GET /api/trust/score/{ward_id} — with demo fallback
# ---------------------------------------------------------------------------
@router.get("/trust/score/{ward_id}", response_model=TrustDimensions)
async def get_trust_score(ward_id: str):
    """
    Compute the 5 trust dimensions from the ledger + complaint data.
    All dimensions normalized to 0-100.
    Falls back to demo defaults when database has no data yet.
    """
    if not is_db_available():
        from app.demo_data import DEMO_TRUST_SCORE
        return TrustDimensions(
            **{**DEMO_TRUST_SCORE, "ward_id": ward_id,
               "computed_at": datetime.now(timezone.utc).isoformat()}
        )

    driver = await get_driver()
    async with driver.session() as session:
        # Resolution Authenticity: % of resolved complaints confirmed by citizens
        ra_result = await session.run(
            """
            MATCH (t:TrustLedger {ward_id: $ward})
            WHERE t.event_type IN ['citizen_confirmed_fix', 'citizen_disputed_fix']
            RETURN
              sum(CASE WHEN t.event_type = 'citizen_confirmed_fix' THEN 1 ELSE 0 END) AS confirmed,
              count(t) AS total
            """,
            ward=ward_id,
        )
        ra_rec = await ra_result.single()
        ra = (ra_rec["confirmed"] / ra_rec["total"] * 100) if ra_rec and ra_rec["total"] > 0 else 50.0

        # Proactive Rate: events tagged proactive_action / total resolutions
        pr_result = await session.run(
            """
            MATCH (t:TrustLedger {ward_id: $ward})
            WHERE t.event_type IN ['proactive_action', 'officer_resolved']
            RETURN
              sum(CASE WHEN t.event_type = 'proactive_action' THEN 1 ELSE 0 END) AS proactive,
              count(t) AS total
            """,
            ward=ward_id,
        )
        pr_rec = await pr_result.single()
        pr = (pr_rec["proactive"] / pr_rec["total"] * 100) if pr_rec and pr_rec["total"] > 0 else 30.0

        # Recurrence Prevention: 1 - (re-opened count / total resolved count) ratio
        rp_result = await session.run(
            """
            OPTIONAL MATCH (c_reopened:Complaint {status: 'reopened'})
            WITH count(c_reopened) AS reopened
            OPTIONAL MATCH (c_closed:Complaint {status: 'closed'})
            RETURN reopened, count(c_closed) AS closed
            """,
        )
        rp_rec = await rp_result.single()
        if rp_rec and (rp_rec["closed"] + rp_rec["reopened"]) > 0:
            rp = (1 - rp_rec["reopened"] / (rp_rec["closed"] + rp_rec["reopened"])) * 100
        else:
            rp = 60.0

        # Response Equity & Moral Alert Response — computed from avg infrastructure health
        health_result = await session.run(
            """
            MATCH (n:Infrastructure {zone_type: $zone})
            RETURN avg(n.health_score) AS avg_health, count(n) AS total_nodes
            """,
            zone=ward_id,
        )
        health_rec = await health_result.single()
        avg_health = (health_rec["avg_health"] or 65.0) if health_rec and health_rec["total_nodes"] > 0 else 65.0

        equity = min(100.0, max(0.0, avg_health * 0.9 + 5))
        critical_result = await session.run(
            """
            MATCH (n:Infrastructure {zone_type: $zone})
            WHERE n.complaint_count > 10
            RETURN avg(n.health_score) AS avg_critical_health
            """,
            zone=ward_id,
        )
        critical_rec = await critical_result.single()
        moral = (critical_rec["avg_critical_health"] or 55.0) if critical_rec else 55.0

    overall = round((ra + pr + rp + equity + moral) / 5, 1)

    return TrustDimensions(
        ward_id=ward_id,
        resolution_authenticity=round(ra, 1),
        proactive_rate=round(pr, 1),
        recurrence_prevention=round(rp, 1),
        response_equity=round(equity, 1),
        moral_alert_response=round(moral, 1),
        overall_score=overall,
        computed_at=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# GET /api/trust/trend/{ward_id} — with demo fallback
# ---------------------------------------------------------------------------
@router.get("/trust/trend/{ward_id}", response_model=list[WeeklyScore])
async def get_trust_trend(ward_id: str):
    """Return 12-week historical overall trust score for the trend line chart."""
    if not is_db_available():
        from app.demo_data import DEMO_TRUST_TREND
        return [WeeklyScore(**r) for r in DEMO_TRUST_TREND]

    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (t:TrustLedger {ward_id: $ward})
            WITH date(datetime(t.recorded_at)) AS d, t.event_type AS evt
            WITH date.truncate('week', d) AS week_start, evt
            WITH week_start,
                 sum(CASE WHEN evt = 'citizen_confirmed_fix' THEN 1 ELSE 0 END) AS confirmed,
                 sum(CASE WHEN evt = 'citizen_disputed_fix' THEN 1 ELSE 0 END) AS disputed,
                 count(*) AS total
            ORDER BY week_start DESC
            LIMIT 12
            RETURN
              toString(week_start) AS week,
              CASE WHEN total > 0
                   THEN round(confirmed * 100.0 / total)
                   ELSE 50 END AS overall_score
            """,
            ward=ward_id,
        )
        rows = await result.data()

    if not rows:
        base = datetime.now(timezone.utc)
        rows = [
            {
                "week": (base - timedelta(weeks=11 - i)).strftime("%Y-%m-%d"),
                "overall_score": round(42 + i * 2.8 + (i % 3) * 1.5, 1),
            }
            for i in range(12)
        ]

    return [WeeklyScore(**r) for r in rows]


# ---------------------------------------------------------------------------
# GET /api/trust/narratives/{ward_id} — with demo fallback
# ---------------------------------------------------------------------------
@router.get("/trust/narratives/{ward_id}", response_model=list[NarrativeComplaint])
async def get_suffering_narratives(ward_id: str):
    """
    Top 5 unresolved high-severity complaints for 'Suffering Narratives' screen.
    Anonymized — no officer or citizen names.
    Falls back to Connaught Place synthetic narratives when no real data exists.
    """
    if not is_db_available():
        from app.demo_data import DEMO_NARRATIVES
        return [NarrativeComplaint(**r) for r in DEMO_NARRATIVES]

    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Complaint)
            WHERE c.status IN ['filed', 'reopened']
              AND c.severity_estimate IN ['high', 'critical']
            WITH c,
                 duration.between(datetime(c.filed_at), datetime()).days AS days_open
            ORDER BY days_open DESC
            LIMIT 5
            RETURN
                c.id               AS id,
                c.complaint_type   AS complaint_type,
                c.description      AS description,
                days_open          AS days_open,
                c.severity_estimate AS severity_estimate
            """,
        )
        rows = await result.data()

    if not rows:
        from app.demo_data import DEMO_NARRATIVES
        rows = DEMO_NARRATIVES

    return [NarrativeComplaint(**r) for r in rows]
