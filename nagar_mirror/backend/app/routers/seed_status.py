"""
Seed status router — quick health check on how many nodes are seeded.
GET /api/seed/status
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.db import get_driver

router = APIRouter(tags=["Seed"])


class SeedStatus(BaseModel):
    node_count: int
    edge_count: int
    type_breakdown: dict[str, int]
    ready_for_mapbox: bool  # True when node_count >= 30


@router.get("/seed/status", response_model=SeedStatus)
async def get_seed_status(driver=Depends(get_driver)):
    """Returns current node / edge counts — used by the team to verify seeding progress."""
    async with driver.session() as session:
        node_result = await session.run(
            "MATCH (n:Infrastructure) RETURN count(n) AS total"
        )
        node_record = await node_result.single()
        node_count: int = node_record["total"]

        edge_result = await session.run(
            "MATCH ()-[r:AFFECTS]->() RETURN count(r) AS total"
        )
        edge_record = await edge_result.single()
        edge_count: int = edge_record["total"]

        breakdown_result = await session.run(
            """
            MATCH (n:Infrastructure)
            RETURN n.type AS type, count(n) AS cnt
            ORDER BY cnt DESC
            """
        )
        breakdown = {r["type"]: r["cnt"] async for r in breakdown_result}

    return SeedStatus(
        node_count=node_count,
        edge_count=edge_count,
        type_breakdown=breakdown,
        ready_for_mapbox=node_count >= 30,
    )
