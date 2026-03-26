"""
fetch_overpass.py — Pull Connaught Place infrastructure from OpenStreetMap via Overpass API.

Bounding box: lat 28.62-28.65, lng 77.20-77.23 (Connaught Place, Delhi)
Fetches: drains, roads, transformers, water mains, public toilets, parks, garbage zones.

Usage:
    python fetch_overpass.py            # prints JSON to stdout
    from fetch_overpass import fetch_all_features
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger(__name__)

OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")

# Connaught Place bounding box: south,west,north,east
BBOX = "28.62,77.20,28.65,77.23"

# OSM tag queries mapped to our node type labels
QUERIES: list[tuple[str, str]] = [
    ("drain", f'way["waterway"="drain"]({BBOX});'),
    ("drain", f'way["waterway"="ditch"]({BBOX});'),
    ("road", f'way["highway"~"primary|secondary|residential|tertiary"]({BBOX});'),
    ("transformer", f'node["power"="transformer"]({BBOX});'),
    ("transformer", f'way["power"="substation"]({BBOX});'),
    ("water_main", f'node["man_made"="water_works"]({BBOX});'),
    ("water_main", f'way["man_made"="pipeline"]({BBOX});'),
    ("water_main", f'node["amenity"="drinking_water"]({BBOX});'),
    ("toilet", f'node["amenity"="toilets"]({BBOX});'),
    ("park", f'way["leisure"="park"]({BBOX});'),
    ("park", f'node["leisure"="garden"]({BBOX});'),
    ("garbage_zone", f'node["amenity"="waste_basket"]({BBOX});'),
    ("garbage_zone", f'node["amenity"="recycling"]({BBOX});'),
    ("garbage_zone", f'way["amenity"="waste_transfer_station"]({BBOX});'),
]


def _build_overpass_query() -> str:
    """Construct a single Overpass QL query for all infrastructure types."""
    parts = "\n  ".join(q for _, q in QUERIES)
    return f"""
[out:json][timeout:60];
(
  {parts}
);
out center tags;
""".strip()


def _element_to_feature(element: dict, infra_type: str) -> dict[str, Any] | None:
    """Convert a raw OSM element to our feature dict. Returns None if unusable."""
    tags = element.get("tags", {})
    osm_id = str(element["id"])

    # Get coordinates
    if element["type"] == "node":
        lat = element.get("lat")
        lng = element.get("lon")
    else:
        # For ways/relations Overpass returns a 'center' with out center
        center = element.get("center", {})
        lat = center.get("lat")
        lng = center.get("lon")

    if lat is None or lng is None:
        return None

    name = (
        tags.get("name")
        or tags.get("name:en")
        or tags.get("ref")
        or f"{infra_type.replace('_', ' ').title()} {osm_id[-4:]}"
    )

    return {
        "osm_id": osm_id,
        "type": infra_type,
        "name": name,
        "lat": float(lat),
        "lng": float(lng),
    }


def fetch_all_features(
    max_retries: int = 5,
    base_delay: float = 2.0,
) -> list[dict[str, Any]]:
    """
    Fetch Connaught Place infrastructure from Overpass API.
    Retries up to `max_retries` times with exponential back-off.

    Returns a list of feature dicts: {osm_id, type, name, lat, lng}
    """
    query = _build_overpass_query()

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Overpass API attempt %d/%d …", attempt, max_retries)
            with httpx.Client(timeout=90.0) as client:
                response = client.post(OVERPASS_URL, data={"data": query})
                response.raise_for_status()

            data = response.json()
            elements = data.get("elements", [])
            logger.info("Overpass returned %d raw elements", len(elements))

            features: list[dict[str, Any]] = []
            seen_ids: set[str] = set()

            for el in elements:
                tags = el.get("tags", {})
                # Determine infra_type from OSM tags
                infra_type = _classify_element(tags)
                if infra_type is None:
                    continue

                feature = _element_to_feature(el, infra_type)
                if feature and feature["osm_id"] not in seen_ids:
                    seen_ids.add(feature["osm_id"])
                    features.append(feature)

            logger.info("Parsed %d valid features from Overpass", len(features))
            return features

        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            wait = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "Overpass API error (attempt %d): %s. Retrying in %.1fs…",
                attempt, exc, wait,
            )
            if attempt < max_retries:
                time.sleep(wait)
            else:
                raise RuntimeError(
                    f"Overpass API failed after {max_retries} attempts: {exc}"
                ) from exc
        except Exception as exc:
            logger.error("Unexpected error fetching Overpass data: %s", exc)
            raise

    return []  # unreachable, but keeps mypy happy


def _classify_element(tags: dict) -> str | None:
    """Map OSM tags to our infra type labels."""
    amenity = tags.get("amenity", "")
    waterway = tags.get("waterway", "")
    highway = tags.get("highway", "")
    power = tags.get("power", "")
    leisure = tags.get("leisure", "")
    man_made = tags.get("man_made", "")

    if waterway in ("drain", "ditch", "canal"):
        return "drain"
    if highway in ("primary", "secondary", "tertiary", "residential", "unclassified"):
        return "road"
    if power in ("transformer", "substation"):
        return "transformer"
    if man_made in ("water_works", "pipeline") or amenity == "drinking_water":
        return "water_main"
    if amenity == "toilets":
        return "toilet"
    if leisure in ("park", "garden"):
        return "park"
    if amenity in ("waste_basket", "recycling", "waste_transfer_station"):
        return "garbage_zone"
    return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    features = fetch_all_features()
    print(json.dumps(features, indent=2, ensure_ascii=False))
    print(f"\n# Total features: {len(features)}", file=sys.stderr)
