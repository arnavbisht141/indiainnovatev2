"""
Infrastructure router — Neo4j query functions for the Connaught Place Digital Twin.

All 4 endpoints specified by the team leader:
  GET  /api/nodes/{id}/health          → get_node_health(id)
  PUT  /api/nodes/{id}/health          → update_node_health(id, new_score)
  GET  /api/nodes/{id}/cascade         → get_cascade_chain(id, depth)
  GET  /api/zones/{ward_id}/nodes      → get_zone_nodes(ward_id)

Bonus endpoints for Person 2 (App Dev):
  GET  /api/zones/{ward_id}/coordinates → get_node_coordinates(ward_id) — compact lat/lng/health export
  GET  /api/nodes/{id}/neighbours       → get_node_neighbours(id) — direct AFFECTS connections
  GET  /api/graph/summary               → graph_summary() — overall stats
"""
from __future__ import annotations

import asyncio
from neo4j.exceptions import SessionExpired, ServiceUnavailable

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.db import get_driver, is_db_available

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Infrastructure"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class NodeHealth(BaseModel):
    id: str
    name: str
    type: str
    health_score: int
    lat: float
    lng: float
    age_years: int
    zone_type: str
    last_maintenance_date: str
    complaint_count: int
    status: str | None = None
    risk_level: str | None = None
    budget_allocated_lakh: float | None = None


class HealthUpdateRequest(BaseModel):
    new_score: int = Field(..., ge=0, le=100, description="New health score 0-100")
    reason: str | None = None


class CascadeNode(BaseModel):
    id: str
    name: str
    type: str
    health_score: int
    status: str | None = None
    lat: float
    lng: float
    depth: int
    edge_type: str | None = None
    edge_weight: float | None = None


class NodeCoordinate(BaseModel):
    """Compact model for Person 2 (App dev) — just what Mapbox needs."""
    id: str
    name: str
    type: str
    lat: float
    lng: float
    health_score: int
    status: str | None = None


class NeighbourEdge(BaseModel):
    neighbour_id: str
    neighbour_name: str
    neighbour_type: str
    neighbour_health: int
    edge_type: str
    edge_weight: float
    description: str | None = None


class GraphSummary(BaseModel):
    total_nodes: int
    total_edges: int
    critical_nodes: int
    warning_nodes: int
    healthy_nodes: int
    avg_health_score: float
    top_complaint_node: str | None = None


# ---------------------------------------------------------------------------
# 1. get_node_health(id)
# ---------------------------------------------------------------------------
@router.get("/nodes/{node_id}/health", response_model=NodeHealth,
            summary="Get full health profile for a single infrastructure node")
async def get_node_health(node_id: str, driver=Depends(get_driver)):
    """Return full health profile for a single Infrastructure node."""
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (n:Infrastructure {id: $id})
            RETURN n {
                .id, .name, .type, .health_score,
                .lat, .lng, .age_years, .zone_type,
                .last_maintenance_date, .complaint_count,
                .status, .risk_level, .budget_allocated_lakh
            } AS node
            """,
            id=node_id,
        )
        record = await result.single()

    if not record:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")

    return NodeHealth(**record["node"])


# ---------------------------------------------------------------------------
# 2. update_node_health(id, new_score)
# ---------------------------------------------------------------------------
@router.put("/nodes/{node_id}/health", response_model=NodeHealth,
            summary="Update health_score for a node")
async def update_node_health(
    node_id: str,
    body: HealthUpdateRequest,
    driver=Depends(get_driver),
):
    """Update health_score for a node and automatically recalculate status."""
    new_status = "critical" if body.new_score < 40 else ("warning" if body.new_score < 70 else "healthy")
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (n:Infrastructure {id: $id})
            SET n.health_score = $score,
                n.status = $status
            RETURN n {
                .id, .name, .type, .health_score,
                .lat, .lng, .age_years, .zone_type,
                .last_maintenance_date, .complaint_count,
                .status, .risk_level, .budget_allocated_lakh
            } AS node
            """,
            id=node_id,
            score=body.new_score,
            status=new_status,
        )
        record = await result.single()

    if not record:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")

    logger.info("Updated health_score for %s → %d (%s). Reason: %s",
                node_id, body.new_score, new_status, body.reason or "N/A")
    return NodeHealth(**record["node"])


# ---------------------------------------------------------------------------
# 3. get_cascade_chain(id, depth)
# ---------------------------------------------------------------------------
@router.get("/nodes/{node_id}/cascade", response_model=list[CascadeNode])
async def get_cascade_chain(
    node_id: str,
    depth: int = Query(default=3, ge=1, le=6),
    driver=Depends(get_driver),
):
    for attempt in range(3):  # retry up to 3 times
        try:
            async with driver.session() as session:
                result = await session.run(
                    f"""
                    MATCH (root:Infrastructure)
                    WHERE root.id = $id
                    MATCH path = (root)-[r:AFFECTS*1..{depth}]->(n:Infrastructure)
                    WITH n, r, length(path) AS hop
                    ORDER BY hop
                    RETURN DISTINCT
                        n.id           AS id,
                        n.name         AS name,
                        n.type         AS type,
                        n.health_score AS health_score,
                        n.status       AS status,
                        n.lat          AS lat,
                        n.lng          AS lng,
                        hop            AS depth,
                        r[-1].type     AS edge_type,
                        r[-1].weight   AS edge_weight
                    """,
                    id=node_id
                )
                records = await result.data()
                return records

        except (SessionExpired, ServiceUnavailable) as e:
            if attempt == 2:
                raise HTTPException(status_code=503, detail="Database connection lost")
            await asyncio.sleep(0.5 * (attempt + 1))  # 0.5s, 1s backoff
# ---------------------------------------------------------------------------
# 4. get_zone_nodes(ward_id) — with demo fallback
# ---------------------------------------------------------------------------
@router.get("/zones/{ward_id}/nodes", response_model=list[NodeHealth],
            summary="Get all infrastructure nodes in a given ward/zone")
async def get_zone_nodes(ward_id: str):
    """Return all Infrastructure nodes belonging to a given ward/zone."""
    if not is_db_available():
        from app.demo_data import DEMO_NODES
        nodes = [n for n in DEMO_NODES if n.get("zone_type") == ward_id or ward_id == "connaught_place"]
        return [NodeHealth(**n) for n in nodes]

    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (n:Infrastructure {zone_type: $zone})
            RETURN n {
                .id, .name, .type, .health_score,
                .lat, .lng, .age_years, .zone_type,
                .last_maintenance_date, .complaint_count,
                .status, .risk_level, .budget_allocated_lakh
            } AS node
            ORDER BY n.health_score ASC
            """,
            zone=ward_id,
        )
        rows = await result.data()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No nodes found for zone '{ward_id}'.",
        )

    return [NodeHealth(**r["node"]) for r in rows]


# ---------------------------------------------------------------------------
# 5. BONUS: get_node_coordinates — compact export for Person 2 (App Dev)
# ---------------------------------------------------------------------------
@router.get("/zones/{ward_id}/coordinates", response_model=list[NodeCoordinate],
            summary="[For Mapbox dev] Compact lat/lng/health export for all nodes in a zone")
async def get_node_coordinates(ward_id: str):
    """
    Compact node export — exactly what the app developer (Person 2) needs 
    to start placing Mapbox markers. Returns id, name, type, lat, lng, 
    health_score, and status only.
    """
    if not is_db_available():
        from app.demo_data import DEMO_NODES
        nodes = [n for n in DEMO_NODES if n.get("zone_type") == ward_id or ward_id == "connaught_place"]
        return [NodeCoordinate(**{k: n[k] for k in NodeCoordinate.model_fields if k in n}) for n in nodes]

    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (n:Infrastructure {zone_type: $zone})
            RETURN n.id AS id, n.name AS name, n.type AS type,
                   n.lat AS lat, n.lng AS lng,
                   n.health_score AS health_score, n.status AS status
            ORDER BY n.health_score ASC
            """,
            zone=ward_id,
        )
        rows = await result.data()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No nodes found for zone '{ward_id}'.")

    return [NodeCoordinate(**r) for r in rows]


# ---------------------------------------------------------------------------
# 6. BONUS: get_node_neighbours — direct edge connections
# ---------------------------------------------------------------------------
@router.get("/nodes/{node_id}/neighbours", response_model=list[NeighbourEdge],
            summary="Get all nodes directly connected to this node via AFFECTS edges")
async def get_node_neighbours(node_id: str, driver=Depends(get_driver)):
    """Return all nodes directly connected to this infrastructure node."""
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (n:Infrastructure {id: $id})-[r:AFFECTS]->(m:Infrastructure)
            RETURN m.id       AS neighbour_id,
                   m.name     AS neighbour_name,
                   m.type     AS neighbour_type,
                   m.health_score AS neighbour_health,
                   r.type     AS edge_type,
                   r.weight   AS edge_weight,
                   r.description AS description
            ORDER BY r.weight DESC
            """,
            id=node_id,
        )
        rows = await result.data()

    return [NeighbourEdge(**r) for r in rows]


# ---------------------------------------------------------------------------
# 7. BONUS: graph_summary — overall stats for dashboards
# ---------------------------------------------------------------------------
@router.get("/graph/summary", response_model=GraphSummary,
            summary="Overall graph stats for the ward dashboard")
async def graph_summary():
    """Return high-level statistics about the entire infrastructure graph."""
    if not is_db_available():
        return GraphSummary(
            total_nodes=30, total_edges=45, critical_nodes=5,
            warning_nodes=12, healthy_nodes=13, avg_health_score=61.2,
            top_complaint_node="cp_drain_01"
        )

    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (n:Infrastructure)
            WITH count(n) AS total,
                 sum(CASE WHEN n.health_score < 40 THEN 1 ELSE 0 END) AS critical,
                 sum(CASE WHEN n.health_score >= 40 AND n.health_score < 70 THEN 1 ELSE 0 END) AS warning,
                 sum(CASE WHEN n.health_score >= 70 THEN 1 ELSE 0 END) AS healthy,
                 avg(n.health_score) AS avg_health
            MATCH ()-[r:AFFECTS]->()
            WITH total, critical, warning, healthy, avg_health, count(r) AS edges
            MATCH (top:Infrastructure) ORDER BY top.complaint_count DESC LIMIT 1
            RETURN total, critical, warning, healthy, avg_health, edges, top.id AS top_node
            """
        )
        row = await result.single()

    if not row:
        raise HTTPException(status_code=500, detail="Unable to fetch graph summary.")

    return GraphSummary(
        total_nodes=row["total"],
        total_edges=row["edges"],
        critical_nodes=row["critical"],
        warning_nodes=row["warning"],
        healthy_nodes=row["healthy"],
        avg_health_score=round(row["avg_health"], 1),
        top_complaint_node=row["top_node"],
    )
