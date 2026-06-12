"""Generate nakshatra/pada boundary fixtures from docs/nakshatra.md rules.

This script is intentionally independent of backend.app.engines.nakshatra_engine:
the generated JSON is the judge for that engine, not a reflection of it.
"""

from __future__ import annotations

import json
from pathlib import Path

FULL_ZODIAC_ARCSEC = 1_296_000
NAKSHATRA_ARCSEC = 48_000
PADA_ARCSEC = 12_000

NAKSHATRAS = [
    ("Ashwini", "Ketu"),
    ("Bharani", "Venus"),
    ("Krittika", "Sun"),
    ("Rohini", "Moon"),
    ("Mrigashira", "Mars"),
    ("Ardra", "Rahu"),
    ("Punarvasu", "Jupiter"),
    ("Pushya", "Saturn"),
    ("Ashlesha", "Mercury"),
    ("Magha", "Ketu"),
    ("Purva Phalguni", "Venus"),
    ("Uttara Phalguni", "Sun"),
    ("Hasta", "Moon"),
    ("Chitra", "Mars"),
    ("Swati", "Rahu"),
    ("Vishakha", "Jupiter"),
    ("Anuradha", "Saturn"),
    ("Jyeshtha", "Mercury"),
    ("Mula", "Ketu"),
    ("Purva Ashadha", "Venus"),
    ("Uttara Ashadha", "Sun"),
    ("Shravana", "Moon"),
    ("Dhanishta", "Mars"),
    ("Shatabhisha", "Rahu"),
    ("Purva Bhadrapada", "Jupiter"),
    ("Uttara Bhadrapada", "Saturn"),
    ("Revati", "Mercury"),
]

SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

OUTPUT_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "nakshatra"
    / "boundaries_330.json"
)


def normalize_arcsec(longitude: float) -> int:
    return round((longitude % 360.0) * 3600.0) % FULL_ZODIAC_ARCSEC


def longitude_from_arcsec(arcsec: int) -> float:
    return (arcsec % FULL_ZODIAC_ARCSEC) / 3600.0


def expected_for_arcsec(arcsec: int) -> dict:
    arcsec %= FULL_ZODIAC_ARCSEC
    nakshatra_zero_based = arcsec // NAKSHATRA_ARCSEC
    nakshatra_offset = arcsec % NAKSHATRA_ARCSEC
    pada_zero_based = nakshatra_offset // PADA_ARCSEC
    pada_offset = nakshatra_offset % PADA_ARCSEC
    name, lord = NAKSHATRAS[nakshatra_zero_based]

    return {
        "expected_name": name,
        "expected_index": nakshatra_zero_based + 1,
        "expected_lord": lord,
        "expected_degree_in_nakshatra": nakshatra_offset / 3600.0,
        "expected_pada": pada_zero_based + 1,
        "expected_degree_in_pada": pada_offset / 3600.0,
        "expected_navamsa_sign": SIGNS[(arcsec // PADA_ARCSEC) % 12],
    }


def row_for_longitude(longitude: float) -> dict:
    arcsec = normalize_arcsec(longitude)
    return {
        "input_longitude": longitude,
        "normalized_arcsec": arcsec,
        **expected_for_arcsec(arcsec),
    }


def row_for_arcsec(arcsec: int) -> dict:
    return row_for_longitude(longitude_from_arcsec(arcsec))


def build_rows() -> list[dict]:
    rows = []

    for boundary_index in range(108):
        boundary = boundary_index * PADA_ARCSEC
        rows.append(row_for_arcsec(boundary - 1))
        rows.append(row_for_arcsec(boundary))
        rows.append(row_for_arcsec(boundary + 1))

    rows.append(row_for_arcsec(0))
    rows.append(row_for_arcsec(FULL_ZODIAC_ARCSEC - 1))

    for longitude in (359.9999, 359.99999, 360.0, -0.0001):
        rows.append(row_for_longitude(longitude))

    assert len(rows) == 330
    return rows


def main() -> None:
    rows = build_rows()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(rows, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
