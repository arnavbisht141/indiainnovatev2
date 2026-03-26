"""
Neo4j driver singleton for Nagar Mirror backend.
Uses the official neo4j-python-driver with async session support.

Graceful mode: if Neo4j is unreachable, the driver is set to None and
all dependent endpoints will return 503 instead of crashing the whole process.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase, AsyncDriver

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Driver singleton
# ---------------------------------------------------------------------------
_driver: AsyncDriver | None = None
_db_available: bool = False


def is_db_available() -> bool:
    return _db_available


async def get_driver() -> AsyncDriver:
    """Return the shared Neo4j async driver. Raises 503 if DB unavailable."""
    if _driver is None or not _db_available:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Please ensure Neo4j is running and credentials are set in .env"
        )
    return _driver


async def init_driver() -> None:
    """Open the Neo4j connection and verify connectivity. Non-fatal if unreachable."""
    global _driver, _db_available

    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not password:
        logger.warning(
            "⚠  NEO4J_URI and NEO4J_PASSWORD not set. Backend will run in offline/demo mode."
        )
        _db_available = False
        return

    # FIX: assign to _driver (global), not a local variable
    _driver = AsyncGraphDatabase.driver(
        uri,
        auth=(user, password),
        max_connection_lifetime=200,        # close connections before Aura's 300s timeout
        max_connection_pool_size=10,
        connection_acquisition_timeout=30,
        keep_alive=True,
    )

    try:
        await _driver.verify_connectivity()
        logger.info("✅  Neo4j connectivity verified — %s", uri)
        _db_available = True
    except Exception as exc:
        logger.warning(
            "⚠  Neo4j connection failed: %s\n"
            "    Backend will start in DEMO mode (API endpoints return synthetic data).",
            exc,
        )
        await _driver.close()
        _driver = None
        _db_available = False
        return

    await _create_constraints()


async def close_driver() -> None:
    """Close the Neo4j driver gracefully."""
    global _driver, _db_available
    if _driver:
        await _driver.close()
        _driver = None
        _db_available = False
        logger.info("Neo4j driver closed.")


# ---------------------------------------------------------------------------
# Schema constraints (idempotent)
# ---------------------------------------------------------------------------
async def _create_constraints() -> None:
    """Create uniqueness constraints and indexes for the Infrastructure graph."""
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            """
            CREATE CONSTRAINT infra_id_unique IF NOT EXISTS
            FOR (n:Infrastructure) REQUIRE n.id IS UNIQUE
            """
        )
        await session.run(
            """
            CREATE INDEX infra_zone_type IF NOT EXISTS
            FOR (n:Infrastructure) ON (n.zone_type, n.type)
            """
        )
        await session.run(
            """
            CREATE INDEX infra_health IF NOT EXISTS
            FOR (n:Infrastructure) ON (n.health_score)
            """
        )
    logger.info("Neo4j constraints and indexes verified.")


# ---------------------------------------------------------------------------
# Convenience async context manager (useful in scripts / tests)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def neo4j_session() -> AsyncGenerator:
    driver = await get_driver()
    async with driver.session() as session:
        yield session