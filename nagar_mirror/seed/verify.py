"""
verify.py — Verify Neo4j seeding results.

Run:
    python verify.py

Prints a rich summary table with node/edge counts and confirms readiness
for the Mapbox frontend developer.
"""
from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase
from rich.console import Console
from rich.table import Table

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
console = Console()


async def verify() -> None:
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not password:
        console.print("[bold red]✗  Set NEO4J_URI and NEO4J_PASSWORD in .env[/]")
        sys.exit(1)

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async with driver.session() as session:
        # Node counts by type
        type_result = await session.run(
            "MATCH (n:Infrastructure) RETURN n.type AS type, count(n) AS cnt ORDER BY cnt DESC"
        )
        type_rows = await type_result.data()

        # Edge counts by type
        edge_result = await session.run(
            "MATCH ()-[r:AFFECTS]->() RETURN r.type AS type, count(r) AS cnt ORDER BY cnt DESC"
        )
        edge_rows = await edge_result.data()

        # Geo-coverage check
        geo_result = await session.run(
            "MATCH (n:Infrastructure) WHERE n.lat IS NOT NULL AND n.lng IS NOT NULL RETURN count(n) AS total"
        )
        geo_record = await geo_result.single()
        geo_count = geo_record["total"]

        # Sample nodes for the Mapbox dev
        sample_result = await session.run(
            "MATCH (n:Infrastructure) RETURN n.id, n.name, n.type, n.lat, n.lng, n.health_score LIMIT 5"
        )
        samples = await sample_result.data()

    await driver.close()

    total_nodes = sum(r["cnt"] for r in type_rows)
    total_edges = sum(r["cnt"] for r in edge_rows)

    console.rule("[bold cyan]Nagar Mirror — Seed Verification")

    # Node table
    node_table = Table(title="Infrastructure Nodes", show_footer=True)
    node_table.add_column("Type", style="cyan")
    node_table.add_column("Count", justify="right", style="green", footer=str(total_nodes))
    for row in type_rows:
        node_table.add_row(row["type"], str(row["cnt"]))
    console.print(node_table)

    # Edge table
    edge_table = Table(title="AFFECTS Edges", show_footer=True)
    edge_table.add_column("Edge Type", style="cyan")
    edge_table.add_column("Count", justify="right", style="green", footer=str(total_edges))
    for row in edge_rows:
        edge_table.add_row(row["type"], str(row["cnt"]))
    console.print(edge_table)

    # Status summary
    console.print()
    mapbox_ready = geo_count >= 30
    console.print(
        f"  Nodes with coordinates: [bold]{geo_count}[/] "
        f"{'[green]✅ Mapbox dev UNBLOCKED[/]' if mapbox_ready else '[red]❌ Need ≥30[/]'}"
    )
    console.print(f"  Total AFFECTS edges   : [bold]{total_edges}[/]")
    console.print()

    # Sample for the Mapbox dev
    sample_table = Table(title="Sample Nodes (share with Mapbox dev)")
    sample_table.add_column("ID", style="dim")
    sample_table.add_column("Name")
    sample_table.add_column("Type", style="cyan")
    sample_table.add_column("Lat", justify="right")
    sample_table.add_column("Lng", justify="right")
    sample_table.add_column("Health", justify="right", style="yellow")
    for s in samples:
        sample_table.add_row(
            s["n.id"], s["n.name"], s["n.type"],
            str(s["n.lat"]), str(s["n.lng"]), str(s["n.health_score"])
        )
    console.print(sample_table)


if __name__ == "__main__":
    asyncio.run(verify())
