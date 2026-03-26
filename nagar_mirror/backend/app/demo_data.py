"""
demo_data.py — Synthetic Connaught Place data used when Neo4j is unavailable.
Provides realistic demo responses for all API endpoints.
"""
from __future__ import annotations

import random
import hashlib
from datetime import datetime, timedelta, timezone

random.seed(42)

# ── Connaught Place synthetic nodes (30 representative ones for map display) ──
CP_NODE_NAMES = [
    ("drain",        "Janpath Drain North"),
    ("drain",        "Barakhamba Road Storm Drain"),
    ("drain",        "Rajiv Chowk Drain East"),
    ("drain",        "Sansad Marg Drain"),
    ("drain",        "KG Marg Drain"),
    ("road",         "Janpath"),
    ("road",         "Barakhamba Road"),
    ("road",         "Connaught Circus"),
    ("road",         "Sansad Marg"),
    ("road",         "Kasturba Gandhi Marg"),
    ("road",         "Windsor Place"),
    ("road",         "Parliament Street"),
    ("transformer",  "Rajiv Chowk Substation A"),
    ("transformer",  "Barakhamba Power Unit 2"),
    ("transformer",  "Janpath Distribution T/F"),
    ("transformer",  "CP Central T/F"),
    ("water_main",   "CP Water Works Station"),
    ("water_main",   "Janpath Water Main"),
    ("water_main",   "Inner Circle Drinking Point"),
    ("water_main",   "Barakhamba Water Pipe"),
    ("toilet",       "Rajiv Chowk Metro Toilet"),
    ("toilet",       "Palika Bazaar Public Toilet"),
    ("toilet",       "Barakhamba Toilet Block"),
    ("park",         "Central Park CP"),
    ("park",         "Inner Circle Garden"),
    ("park",         "Baba Kharak Singh Garden"),
    ("garbage_zone", "CP Market Waste Point"),
    ("garbage_zone", "Palika Bazaar Recycling Zone"),
    ("garbage_zone", "Barakhamba Waste Transfer"),
    ("garbage_zone", "Sansad Marg Waste Basket Row"),
]

_CP_BASE_LAT = 28.6315
_CP_BASE_LNG = 77.2167

_HEALTH_RANGES = {
    "drain":        (20, 65),
    "road":         (30, 80),
    "transformer":  (45, 95),
    "water_main":   (25, 75),
    "toilet":       (15, 70),
    "park":         (40, 90),
    "garbage_zone": (10, 60),
}

rng = random.Random(42)

def _make_node(i: int, infra_type: str, name: str) -> dict:
    node_id = "cp_" + hashlib.md5(name.encode()).hexdigest()[:9]
    lo, hi = _HEALTH_RANGES.get(infra_type, (30, 80))
    health = rng.randint(lo, hi)
    age = rng.randint(5, 30)
    days_ago = rng.randint(30, min(age * 365, 1825))
    last_maint = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    # Spread nodes around CP center in a circle pattern
    import math
    angle = (i / len(CP_NODE_NAMES)) * 2 * math.pi
    radius_lat = 0.012 * rng.random()
    radius_lng = 0.015 * rng.random()
    return {
        "id": node_id,
        "name": name,
        "type": infra_type,
        "health_score": health,
        "lat": round(_CP_BASE_LAT + radius_lat * math.sin(angle), 6),
        "lng": round(_CP_BASE_LNG + radius_lng * math.cos(angle), 6),
        "age_years": age,
        "zone_type": "connaught_place",
        "last_maintenance_date": last_maint,
        "complaint_count": rng.randint(0, 25),
    }

DEMO_NODES = [_make_node(i, t, n) for i, (t, n) in enumerate(CP_NODE_NAMES)]

DEMO_TRUST_SCORE = {
    "ward_id": "connaught_place",
    "resolution_authenticity": 68.0,
    "proactive_rate": 32.0,
    "recurrence_prevention": 61.0,
    "response_equity": 58.0,
    "moral_alert_response": 54.0,
    "overall_score": 54.6,
    "computed_at": datetime.now(timezone.utc).isoformat(),
}

def _make_trend():
    base = datetime.now(timezone.utc)
    rows = []
    for i in range(12):
        week_dt = base - timedelta(weeks=11 - i)
        score = round(42 + i * 2.8 + (i % 3) * 1.5, 1)
        rows.append({"week": week_dt.strftime("%Y-%m-%d"), "overall_score": score})
    return rows

DEMO_TRUST_TREND = _make_trend()

DEMO_NARRATIVES = [
    {
        "id": "syn_001",
        "complaint_type": "water_main",
        "description": "The Janpath water main has been broken for 23 days. 340 households and 12 commercial establishments near Connaught Place have no piped supply.",
        "days_open": 23,
        "severity_estimate": "critical",
    },
    {
        "id": "syn_002",
        "complaint_type": "drain",
        "description": "The storm drain near Rajiv Chowk Metro Exit Gate 7 has been overflowing since heavy rains 18 days ago, creating a health hazard and blocking pedestrian movement.",
        "days_open": 18,
        "severity_estimate": "high",
    },
    {
        "id": "syn_003",
        "complaint_type": "transformer",
        "description": "The Barakhamba Road substation has been partially down for 15 days. 120 businesses and 80 residential units are dependent on backup generators.",
        "days_open": 15,
        "severity_estimate": "critical",
    },
    {
        "id": "syn_004",
        "complaint_type": "road",
        "description": "A wide pothole on Kasturba Gandhi Marg near CP inner circle has caused 4 vehicle accidents in 12 days. The ULB has not responded.",
        "days_open": 12,
        "severity_estimate": "high",
    },
    {
        "id": "syn_005",
        "complaint_type": "garbage_zone",
        "description": "Palika Bazaar waste collection has failed for 9 consecutive days. Waste is overflowing onto the pavement along the Inner Circle.",
        "days_open": 9,
        "severity_estimate": "high",
    },
]
