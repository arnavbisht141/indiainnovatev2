"""
seed_graph.py — Professional Digital Twin Graph Seeder for Connaught Place.

Creates a rich, multi-label urban knowledge graph with:
  - 7 node types: Infrastructure, Zone, Citizen, Complaint, CivicOfficer, MetroStation, Ward
  - 8 relationship types: AFFECTS, FILED_IN, LOCATED_IN, SERVES, ASSIGNED_TO,
                          CONNECTS, OVERSEES, ESCALATED_TO
  - 500 Infrastructure nodes + 8 rich anchor nodes + 1200 edges

Run:
    cd /home/ajitesh/Desktop/nagar_mirror/seed
    python seed_graph.py

Idempotent: uses MERGE on id, safe to re-run.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

# Load .env from backend directory (where the user edited it)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

# ─── Connaught Place anchor coordinates ───────────────────────────────────────
CP_CENTER = (28.6315, 77.2167)

# ---------------------------------------------------------------------------
# ── Rich Synthetic Nodes for Fallback ──────────────────────────────────────
# ---------------------------------------------------------------------------
SYNTHETIC_NODES: list[dict[str, Any]] = [
    {"osm_id": "cp_drain_01", "type": "drain",        "name": "Janpath Drain North",              "lat": 28.6320, "lng": 77.2152},
    {"osm_id": "cp_drain_02", "type": "drain",        "name": "Barakhamba Road Storm Drain",       "lat": 28.6338, "lng": 77.2225},
    {"osm_id": "cp_drain_03", "type": "drain",        "name": "Connaught Circus Drain East",       "lat": 28.6330, "lng": 77.2198},
    {"osm_id": "cp_drain_04", "type": "drain",        "name": "Rajiv Chowk Underground Drain",     "lat": 28.6328, "lng": 77.2179},
    {"osm_id": "cp_drain_05", "type": "drain",        "name": "Kasturba Gandhi Marg Drain",        "lat": 28.6302, "lng": 77.2240},
    {"osm_id": "cp_drain_06", "type": "drain",        "name": "Sansad Marg Drain Segment",          "lat": 28.6297, "lng": 77.2137},
    {"osm_id": "cp_drain_07", "type": "drain",        "name": "Outer Circle Drain West",            "lat": 28.6335, "lng": 77.2145},
    {"osm_id": "cp_road_01",  "type": "road",         "name": "Janpath",                            "lat": 28.6315, "lng": 77.2148},
    {"osm_id": "cp_road_02",  "type": "road",         "name": "Barakhamba Road",                    "lat": 28.6340, "lng": 77.2231},
    {"osm_id": "cp_road_03",  "type": "road",         "name": "Connaught Circus",                   "lat": 28.6325, "lng": 77.2200},
    {"osm_id": "cp_road_04",  "type": "road",         "name": "Sansad Marg",                        "lat": 28.6290, "lng": 77.2140},
    {"osm_id": "cp_road_05",  "type": "road",         "name": "Kasturba Gandhi Marg",               "lat": 28.6300, "lng": 77.2245},
    {"osm_id": "cp_road_06",  "type": "road",         "name": "Tolstoy Marg",                       "lat": 28.6355, "lng": 77.2210},
    {"osm_id": "cp_road_07",  "type": "road",         "name": "Windsor Place",                      "lat": 28.6275, "lng": 77.2175},
    {"osm_id": "cp_road_08",  "type": "road",         "name": "Radial Road 1 (Inner Circle)",       "lat": 28.6310, "lng": 77.2170},
    {"osm_id": "cp_road_09",  "type": "road",         "name": "Parliament Street",                  "lat": 28.6283, "lng": 77.2163},
    {"osm_id": "cp_xfmr_01",  "type": "transformer",  "name": "Rajiv Chowk Substation A",           "lat": 28.6330, "lng": 77.2180},
    {"osm_id": "cp_xfmr_02",  "type": "transformer",  "name": "Barakhamba Power Unit 2",            "lat": 28.6345, "lng": 77.2220},
    {"osm_id": "cp_xfmr_03",  "type": "transformer",  "name": "Janpath Distribution T/F",           "lat": 28.6309, "lng": 77.2145},
    {"osm_id": "cp_xfmr_04",  "type": "transformer",  "name": "Connaught Place Central T/F",        "lat": 28.6328, "lng": 77.2167},
    {"osm_id": "cp_xfmr_05",  "type": "transformer",  "name": "Sansad Marg Junction T/F",           "lat": 28.6292, "lng": 77.2135},
    {"osm_id": "cp_water_01", "type": "water_main",   "name": "CP Water Works Station",             "lat": 28.6315, "lng": 77.2160},
    {"osm_id": "cp_water_02", "type": "water_main",   "name": "Janpath Water Main (East)",          "lat": 28.6318, "lng": 77.2153},
    {"osm_id": "cp_water_03", "type": "water_main",   "name": "Inner Circle Drinking Point",        "lat": 28.6325, "lng": 77.2185},
    {"osm_id": "cp_water_04", "type": "water_main",   "name": "Barakhamba Water Pipe",              "lat": 28.6342, "lng": 77.2228},
    {"osm_id": "cp_water_05", "type": "water_main",   "name": "KG Marg Water Tap",                 "lat": 28.6299, "lng": 77.2243},
    {"osm_id": "cp_toilet_01","type": "toilet",       "name": "Rajiv Chowk Metro Toilet",           "lat": 28.6327, "lng": 77.2179},
    {"osm_id": "cp_toilet_02","type": "toilet",       "name": "Palika Bazaar Public Toilet",        "lat": 28.6322, "lng": 77.2167},
    {"osm_id": "cp_toilet_03","type": "toilet",       "name": "Janpath Market Community Toilet",    "lat": 28.6311, "lng": 77.2149},
    {"osm_id": "cp_toilet_04","type": "toilet",       "name": "Barakhamba Toilet Block",            "lat": 28.6344, "lng": 77.2222},
    {"osm_id": "cp_park_01",  "type": "park",         "name": "Central Park CP",                    "lat": 28.6328, "lng": 77.2168},
    {"osm_id": "cp_park_02",  "type": "park",         "name": "Connaught Place Inner Circle Garden","lat": 28.6320, "lng": 77.2175},
    {"osm_id": "cp_park_03",  "type": "park",         "name": "Baba Kharak Singh Marg Garden",      "lat": 28.6288, "lng": 77.2120},
    {"osm_id": "cp_park_04",  "type": "park",         "name": "Tolstoy Park Strip",                 "lat": 28.6358, "lng": 77.2208},
    {"osm_id": "cp_gc_01",    "type": "garbage_zone", "name": "CP Market Waste Point",              "lat": 28.6322, "lng": 77.2170},
    {"osm_id": "cp_gc_02",    "type": "garbage_zone", "name": "Palika Bazaar Recycling Zone",       "lat": 28.6325, "lng": 77.2163},
    {"osm_id": "cp_gc_03",    "type": "garbage_zone", "name": "Janpath Market Garbage Dump",        "lat": 28.6308, "lng": 77.2145},
    {"osm_id": "cp_gc_04",    "type": "garbage_zone", "name": "Barakhamba Waste Transfer",          "lat": 28.6347, "lng": 77.2218},
    {"osm_id": "cp_gc_05",    "type": "garbage_zone", "name": "KG Marg Recycling Point",            "lat": 28.6298, "lng": 77.2240},
    {"osm_id": "cp_gc_06",    "type": "garbage_zone", "name": "Sansad Marg Waste Basket Row",       "lat": 28.6291, "lng": 77.2133},
]

# ========================================================================================
# ── Anchor graph objects (non-Infrastructure node types) ───────────────────────────────
# ========================================================================================

METRO_STATIONS = [
    {"id": "metro_rajiv",       "name": "Rajiv Chowk",         "line": "Blue/Yellow", "lat": 28.6328, "lng": 77.2197, "daily_footfall": 350000, "congestion_index": 0.91},
    {"id": "metro_barakhamba",  "name": "Barakhamba Road",      "line": "Blue",        "lat": 28.6342, "lng": 77.2237, "daily_footfall": 125000, "congestion_index": 0.61},
    {"id": "metro_patel_chowk", "name": "Patel Chowk",         "line": "Yellow",      "lat": 28.6260, "lng": 77.2180, "daily_footfall": 95000,  "congestion_index": 0.45},
]

ZONES = [
    {"id": "zone_inner_circle",  "name": "Inner Circle",   "zone_class": "commercial", "population_density": 4200, "avg_income": 85000},
    {"id": "zone_middle_circle", "name": "Middle Circle",  "zone_class": "mixed",      "population_density": 6800, "avg_income": 62000},
    {"id": "zone_outer_circle",  "name": "Outer Circle",   "zone_class": "mixed",      "population_density": 8500, "avg_income": 48000},
    {"id": "zone_janpath",       "name": "Janpath",         "zone_class": "commercial", "population_density": 3100, "avg_income": 72000},
    {"id": "zone_barakhamba",    "name": "Barakhamba",      "zone_class": "commercial", "population_density": 2900, "avg_income": 78000},
]

CIVIC_OFFICERS = [
    {"id": "officer_001", "name": "Rajesh Kumar",  "designation": "Ward Commissioner",   "department": "NDMC",         "contact": "9810000001", "active_cases": 12},
    {"id": "officer_002", "name": "Priya Sharma",  "designation": "JE – Roads",         "department": "PWD",          "contact": "9810000002", "active_cases": 8},
    {"id": "officer_003", "name": "Amit Verma",    "designation": "JE – Sanitation",    "department": "MCD",          "contact": "9810000003", "active_cases": 15},
    {"id": "officer_004", "name": "Sunita Yadav",  "designation": "JE – Water Supply",  "department": "DJB",          "contact": "9810000004", "active_cases": 6},
    {"id": "officer_005", "name": "Deepak Singh",  "designation": "Ward Health Officer","department": "NDMC Health",  "contact": "9810000005", "active_cases": 9},
]

CITIZENS = [
    {"id": "citizen_001", "name": "Ramesh Gupta",   "ward": "connaught_place", "trust_score": 82, "complaints_filed": 5},
    {"id": "citizen_002", "name": "Anita Bose",     "ward": "connaught_place", "trust_score": 55, "complaints_filed": 2},
    {"id": "citizen_003", "name": "Karim Ansari",   "ward": "connaught_place", "trust_score": 71, "complaints_filed": 8},
    {"id": "citizen_004", "name": "Kavya Menon",    "ward": "connaught_place", "trust_score": 90, "complaints_filed": 1},
    {"id": "citizen_005", "name": "Vijay Patel",    "ward": "connaught_place", "trust_score": 43, "complaints_filed": 12},
    {"id": "citizen_006", "name": "Lalita Devi",    "ward": "connaught_place", "trust_score": 67, "complaints_filed": 4},
    {"id": "citizen_007", "name": "Mohan Kapoor",   "ward": "connaught_place", "trust_score": 78, "complaints_filed": 3},
    {"id": "citizen_008", "name": "Sheela Tiwari",  "ward": "connaught_place", "trust_score": 60, "complaints_filed": 7},
]

COMPLAINTS_DATA = [
    {"id": "cmp_001", "title": "Overflowing drain near Janpath",          "category": "drain",         "severity": "high",   "status": "open",     "filed_by": "citizen_001", "assigned_to": "officer_003", "infra_id": "cp_drain_01"},
    {"id": "cmp_002", "title": "Pothole on Barakhamba Road",              "category": "road",          "severity": "medium", "status": "resolved", "filed_by": "citizen_002", "assigned_to": "officer_002", "infra_id": "cp_road_02"},
    {"id": "cmp_003", "title": "Street light failure on Sansad Marg",    "category": "transformer",   "severity": "high",   "status": "in_progress","filed_by": "citizen_003", "assigned_to": "officer_001", "infra_id": "cp_xfmr_05"},
    {"id": "cmp_004", "title": "Water leakage near CP Water Works",       "category": "water_main",    "severity": "critical","status": "open",     "filed_by": "citizen_005", "assigned_to": "officer_004", "infra_id": "cp_water_01"},
    {"id": "cmp_005", "title": "Dirty public toilet at Palika Bazaar",    "category": "toilet",        "severity": "medium", "status": "open",     "filed_by": "citizen_006", "assigned_to": "officer_003", "infra_id": "cp_toilet_02"},
    {"id": "cmp_006", "title": "Garbage dumped in Inner Circle Garden",   "category": "garbage_zone",  "severity": "high",   "status": "resolved", "filed_by": "citizen_007", "assigned_to": "officer_003", "infra_id": "cp_gc_01"},
    {"id": "cmp_007", "title": "Broken footpath on Connaught Circus",     "category": "road",          "severity": "low",    "status": "in_progress","filed_by": "citizen_004", "assigned_to": "officer_002", "infra_id": "cp_road_03"},
    {"id": "cmp_008", "title": "Blocked storm drain near Barakhamba",     "category": "drain",         "severity": "high",   "status": "open",     "filed_by": "citizen_008", "assigned_to": "officer_003", "infra_id": "cp_drain_02"},
    {"id": "cmp_009", "title": "Transformer humming loudly at night",     "category": "transformer",   "severity": "low",    "status": "open",     "filed_by": "citizen_001", "assigned_to": "officer_001", "infra_id": "cp_xfmr_01"},
    {"id": "cmp_010", "title": "No water supply in Outer Circle area",    "category": "water_main",    "severity": "critical","status": "escalated","filed_by": "citizen_003", "assigned_to": "officer_004", "infra_id": "cp_water_03"},
]

WARD = {
    "id": "ward_connaught_place",
    "name": "Connaught Place Ward",
    "ward_no": 1,
    "district": "New Delhi",
    "area_sqkm": 4.2,
    "population": 85000,
    "trust_score": 72,
    "governing_body": "NDMC",
}


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def _stable_id(osm_id: str) -> str:
    return "cp_" + hashlib.md5(osm_id.encode()).hexdigest()[:9]


def _random_health(infra_type: str, rng: random.Random) -> int:
    ranges = {
        "drain":        (20, 65),
        "road":         (30, 80),
        "transformer":  (45, 95),
        "water_main":   (25, 75),
        "toilet":       (15, 70),
        "park":         (40, 90),
        "garbage_zone": (10, 60),
    }
    lo, hi = ranges.get(infra_type, (30, 80))
    return rng.randint(lo, hi)


def _random_age(infra_type: str, rng: random.Random) -> int:
    ranges = {
        "drain":        (10, 40),
        "road":         (5, 25),
        "transformer":  (3, 20),
        "water_main":   (15, 50),
        "toilet":       (2, 15),
        "park":         (1, 30),
        "garbage_zone": (1, 10),
    }
    lo, hi = ranges.get(infra_type, (5, 20))
    return rng.randint(lo, hi)


def _last_maintenance(age: int, rng: random.Random) -> str:
    max_days_since = min(age * 365, 1825)
    days_ago = rng.randint(30, max_days_since)
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%d")


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _build_infra_edges(nodes: list[dict], rng: random.Random, target: int = 1200) -> list[dict]:
    edges: list[dict] = []
    seen: set[frozenset] = set()
    edge_type_rules = [
        ("drain",       "road",         "physical_flow"),
        ("water_main",  "toilet",       "service_dependency"),
        ("transformer", "water_main",   "service_dependency"),
        ("transformer", "park",         "service_dependency"),
        ("road",        "garbage_zone", "physical_flow"),
        ("garbage_zone","drain",        "risk_propagation"),
        ("toilet",      "garbage_zone", "risk_propagation"),
        ("park",        "road",         "physical_flow"),
        ("transformer", "road",         "service_dependency"),
        ("water_main",  "drain",        "risk_propagation"),
    ]
    type_index: dict[str, list[dict]] = {}
    for node in nodes:
        type_index.setdefault(node["type"], []).append(node)

    for src_type, tgt_type, edge_type in edge_type_rules:
        for src in type_index.get(src_type, []):
            candidates = sorted(
                type_index.get(tgt_type, []),
                key=lambda t: _haversine(src["lat"], src["lng"], t["lat"], t["lng"]),
            )
            for tgt in candidates[:3]:
                pair = frozenset({src["id"], tgt["id"]})
                if pair in seen:
                    continue
                seen.add(pair)
                dist = _haversine(src["lat"], src["lng"], tgt["lat"], tgt["lng"])
                edges.append({
                    "src": src["id"], "tgt": tgt["id"], "type": edge_type,
                    "weight": round(max(0.1, 1.0 - dist / 1000), 3),
                    "description": f"{src['name']} → {tgt['name']} ({edge_type})",
                })

    for i, src in enumerate(nodes):
        for tgt in nodes[i + 1:]:
            if len(edges) >= target:
                break
            pair = frozenset({src["id"], tgt["id"]})
            if pair in seen:
                continue
            dist = _haversine(src["lat"], src["lng"], tgt["lat"], tgt["lng"])
            if dist < 400:
                seen.add(pair)
                edge_type = "physical_flow" if src["type"] == tgt["type"] else "risk_propagation"
                edges.append({
                    "src": src["id"], "tgt": tgt["id"], "type": edge_type,
                    "weight": round(max(0.1, 1.0 - dist / 1000), 3),
                    "description": f"Proximity link: {src['name']} → {tgt['name']}",
                })

    rng.shuffle(edges)
    return edges[:target]


# ---------------------------------------------------------------------------
# Main seeder
# ---------------------------------------------------------------------------
async def seed(uri: str, user: str, password: str) -> None:
    rng = random.Random(42)

    console.rule("[bold cyan]Nagar Mirror — Advanced Digital Twin Graph Seeder")

    # ── 1. Fetch Infrastructure from Overpass ────────────────────────────
    try:
        from fetch_overpass import fetch_all_features
        console.print("[yellow]⟳  Fetching Connaught Place data from Overpass API…[/]")
        raw_features = fetch_all_features(max_retries=4)
    except Exception as exc:
        console.print(f"[red]⚠  Overpass fetch failed: {exc}[/]")
        raw_features = []

    if len(raw_features) < 500:
        existing_osm_ids = {f["osm_id"] for f in raw_features}
        for syn in SYNTHETIC_NODES:
            if syn["osm_id"] not in existing_osm_ids:
                raw_features.append(syn)
            if len(raw_features) >= 500:
                break

    raw_features = raw_features[:500]

    nodes: list[dict] = []
    for feat in raw_features:
        node_id = _stable_id(feat["osm_id"])
        age = _random_age(feat["type"], rng)
        health = _random_health(feat["type"], rng)
        # assign a zone
        zone_ids = [z["id"] for z in ZONES]
        nodes.append({
            "id":                    node_id,
            "type":                  feat["type"],
            "name":                  feat["name"],
            "lat":                   feat["lat"],
            "lng":                   feat["lng"],
            "health_score":          health,
            "status":                "critical" if health < 40 else ("warning" if health < 70 else "healthy"),
            "age_years":             age,
            "zone_type":             "connaught_place",
            "zone_id":               rng.choice(zone_ids),
            "last_maintenance_date": _last_maintenance(age, rng),
            "complaint_count":       rng.randint(0, 30),
            "risk_level":            rng.choice(["low", "medium", "high"]),
            "budget_allocated_lakh": round(rng.uniform(0.5, 25.0), 2),
        })

    console.print(f"[green]✓  {len(nodes)} Infrastructure nodes ready.[/]")

    edges = _build_infra_edges(nodes, rng, target=1200)
    console.print(f"[green]✓  {len(edges)} AFFECTS edges generated.[/]")

    # ── 2. Connect to Neo4j ──────────────────────────────────────────────
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        await driver.verify_connectivity()
        console.print("[green]✓  Connected to Neo4j Aura.[/]")
    except Exception as exc:
        console.print(f"[bold red]✗  Cannot connect to Neo4j: {exc}[/]")
        await driver.close()
        sys.exit(1)

    async with driver.session() as session:
        # ── Schema ──────────────────────────────────────────────────────
        console.print("[cyan]→  Setting up schema constraints…[/]")
        for cypher in [
            "CREATE CONSTRAINT infra_id IF NOT EXISTS FOR (n:Infrastructure)  REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT metro_id IF NOT EXISTS FOR (n:MetroStation)    REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT zone_id  IF NOT EXISTS FOR (n:Zone)            REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT officer_id IF NOT EXISTS FOR (n:CivicOfficer)  REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT citizen_id IF NOT EXISTS FOR (n:Citizen)       REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT complaint_id IF NOT EXISTS FOR (n:Complaint)   REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT ward_id IF NOT EXISTS FOR (n:Ward)             REQUIRE n.id IS UNIQUE",
        ]:
            await session.run(cypher)

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
            BarColumn(), TaskProgressColumn(), console=console
        ) as progress:

            # ── Ward Node ────────────────────────────────────────────────
            t = progress.add_task("Upserting Ward…", total=1)
            await session.run(
                "MERGE (w:Ward {id: $id}) SET w += $props",
                id=WARD["id"], props=WARD
            )
            progress.advance(t, 1)

            # ── Zone Nodes ───────────────────────────────────────────────
            t = progress.add_task("Upserting Zones…", total=len(ZONES))
            for z in ZONES:
                await session.run(
                    "MERGE (z:Zone {id: $id}) SET z += $props "
                    "WITH z MATCH (w:Ward {id: $ward_id}) MERGE (z)-[:PART_OF]->(w)",
                    id=z["id"], props=z, ward_id=WARD["id"]
                )
                progress.advance(t, 1)

            # ── MetroStation Nodes ───────────────────────────────────────
            t = progress.add_task("Upserting Metro Stations…", total=len(METRO_STATIONS))
            for m in METRO_STATIONS:
                await session.run(
                    "MERGE (m:MetroStation {id: $id}) SET m += $props",
                    id=m["id"], props=m
                )
                # CONNECTS metro to nearest zone
                await session.run(
                    "MATCH (m:MetroStation {id: $mid}), (z:Zone {id: 'zone_inner_circle'}) "
                    "MERGE (m)-[:CONNECTS]->(z)",
                    mid=m["id"]
                )
                progress.advance(t, 1)

            # ── CivicOfficer Nodes ───────────────────────────────────────
            t = progress.add_task("Upserting Civic Officers…", total=len(CIVIC_OFFICERS))
            for o in CIVIC_OFFICERS:
                await session.run(
                    "MERGE (o:CivicOfficer {id: $id}) SET o += $props "
                    "WITH o MATCH (w:Ward {id: $ward_id}) MERGE (o)-[:OVERSEES]->(w)",
                    id=o["id"], props=o, ward_id=WARD["id"]
                )
                progress.advance(t, 1)

            # ── Citizen Nodes ────────────────────────────────────────────
            t = progress.add_task("Upserting Citizens…", total=len(CITIZENS))
            for c in CITIZENS:
                await session.run(
                    "MERGE (c:Citizen {id: $id}) SET c += $props "
                    "WITH c MATCH (w:Ward {id: $ward_id}) MERGE (c)-[:LIVES_IN]->(w)",
                    id=c["id"], props=c, ward_id=WARD["id"]
                )
                progress.advance(t, 1)

            # ── Infrastructure Nodes ─────────────────────────────────────
            BATCH = 50
            t = progress.add_task("Upserting Infrastructure nodes…", total=len(nodes))
            for start in range(0, len(nodes), BATCH):
                batch = nodes[start: start + BATCH]
                await session.run(
                    "UNWIND $batch AS n MERGE (infra:Infrastructure {id: n.id}) SET infra += n",
                    batch=batch,
                )
                progress.advance(t, len(batch))

            # ── LOCATED_IN: Infra → Zone ─────────────────────────────────
            t = progress.add_task("Linking Infra → Zones…", total=len(nodes))
            for start in range(0, len(nodes), BATCH):
                batch = nodes[start: start + BATCH]
                await session.run(
                    """
                    UNWIND $batch AS n
                    MATCH (infra:Infrastructure {id: n.id}), (z:Zone {id: n.zone_id})
                    MERGE (infra)-[:LOCATED_IN]->(z)
                    """,
                    batch=batch,
                )
                progress.advance(t, len(batch))

            # ── AFFECTS edges ─────────────────────────────────────────────
            t = progress.add_task("Creating AFFECTS edges…", total=len(edges))
            for start in range(0, len(edges), BATCH):
                batch = edges[start: start + BATCH]
                await session.run(
                    """
                    UNWIND $batch AS e
                    MATCH (a:Infrastructure {id: e.src}), (b:Infrastructure {id: e.tgt})
                    MERGE (a)-[r:AFFECTS {type: e.type, src: e.src, tgt: e.tgt}]->(b)
                    SET r.weight = e.weight, r.description = e.description
                    """,
                    batch=batch,
                )
                progress.advance(t, len(batch))

            # ── Complaint Nodes + Relationships ───────────────────────────
            t = progress.add_task("Upserting Complaints + relations…", total=len(COMPLAINTS_DATA))
            for cmp in COMPLAINTS_DATA:
                infra_node_id = _stable_id(cmp["infra_id"])
                filed_at = (datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 90))).strftime("%Y-%m-%dT%H:%M:%SZ")
                await session.run(
                    """
                    MERGE (cmp:Complaint {id: $id})
                    SET cmp.title     = $title,
                        cmp.category  = $category,
                        cmp.severity  = $severity,
                        cmp.status    = $status,
                        cmp.filed_at  = $filed_at
                    WITH cmp
                    MATCH (c:Citizen      {id: $citizen_id})
                    MATCH (o:CivicOfficer {id: $officer_id})
                    MATCH (i:Infrastructure {id: $infra_id})
                    MERGE (c)-[:FILED]->(cmp)
                    MERGE (cmp)-[:ABOUT]->(i)
                    MERGE (cmp)-[:ASSIGNED_TO]->(o)
                    """,
                    id=cmp["id"], title=cmp["title"], category=cmp["category"],
                    severity=cmp["severity"], status=cmp["status"], filed_at=filed_at,
                    citizen_id=cmp["filed_by"], officer_id=cmp["assigned_to"],
                    infra_id=infra_node_id,
                )
                # Escalation chain for critical complaints
                if cmp["status"] == "escalated":
                    await session.run(
                        "MATCH (cmp:Complaint {id: $cmp_id}), (o:CivicOfficer {id: 'officer_001'}) "
                        "MERGE (cmp)-[:ESCALATED_TO]->(o)",
                        cmp_id=cmp["id"]
                    )
                progress.advance(t, 1)

            # ── SERVES: Metro → nearby Infrastructure ────────────────────
            t = progress.add_task("Linking Metro → Infrastructure…", total=len(METRO_STATIONS))
            for metro in METRO_STATIONS:
                near_infra = sorted(nodes, key=lambda n: _haversine(metro["lat"], metro["lng"], n["lat"], n["lng"]))[:10]
                for ni in near_infra:
                    await session.run(
                        "MATCH (m:MetroStation {id: $mid}), (i:Infrastructure {id: $iid}) "
                        "MERGE (m)-[:SERVES]->(i)",
                        mid=metro["id"], iid=ni["id"]
                    )
                progress.advance(t, 1)

    await driver.close()

    console.rule("[bold green]✅  Advanced Graph Seeding Complete!")
    console.print(f"\n   [bold]Infrastructure Nodes:[/]  {len(nodes)}")
    console.print(f"   [bold]AFFECTS Edges:[/]         {len(edges)}")
    console.print(f"   [bold]Metro Stations:[/]         {len(METRO_STATIONS)}")
    console.print(f"   [bold]Zones:[/]                  {len(ZONES)}")
    console.print(f"   [bold]Civic Officers:[/]         {len(CIVIC_OFFICERS)}")
    console.print(f"   [bold]Citizens:[/]               {len(CITIZENS)}")
    console.print(f"   [bold]Complaints:[/]             {len(COMPLAINTS_DATA)}")
    console.print(f"   [bold]Wards:[/]                  1")
    console.print("\n   [cyan]Open Neo4j Workspace → run  MATCH (n) RETURN n  to see the full graph![/]\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not password:
        console.print(
            "[bold red]✗  NEO4J_URI and NEO4J_PASSWORD must be set.[/]\n"
            "   Edit backend/.env and fill in your Aura credentials."
        )
        sys.exit(1)

    asyncio.run(seed(uri, user, password))
