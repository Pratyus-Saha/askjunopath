from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas.models import ChartData  # noqa: E402


PLANETS = [
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
    "Rahu",
    "Ketu",
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
SIGN_LORDS = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}


def _planet(index: int, offset: float = 0.0) -> dict:
    longitude = (index * 30.0 + 1.25 + offset) % 360.0
    sign = SIGNS[int(longitude // 30)]
    return {
        "name": PLANETS[index],
        "longitude": round(longitude, 4),
        "sign": sign,
        "sign_lord": SIGN_LORDS[sign],
        "sign_degree": round(longitude % 30, 4),
        "retrograde": PLANETS[index] in {"Saturn", "Rahu", "Ketu"},
        "combust": False,
        "speed_deg_per_day": -0.05 if PLANETS[index] in {"Rahu", "Ketu"} else 1.0,
    }


def _house(house: int, offset: float = 0.0) -> dict:
    longitude = ((house - 1) * 30.0 + 3.5 + offset) % 360.0
    sign = SIGNS[int(longitude // 30)]
    return {
        "house": house,
        "cusp_longitude": round(longitude, 4),
        "cusp_sign": sign,
        "cusp_sign_lord": SIGN_LORDS[sign],
    }


def valid_chart(offset: float = 0.0) -> dict:
    return {
        "schema_version": "1.0",
        "birth": {
            "datetime_local": "1994-03-21T14:35:00",
            "datetime_utc": "1994-03-21T09:05:00Z",
            "timezone": "Asia/Kolkata",
            "lat": 28.4595,
            "lon": 77.0266,
            "place_label": "Gurugram, India",
            "approximate_time": False,
            "julian_day_ut": 2449432.87847,
        },
        "settings": {
            "ayanamsa": "KP_NEWCOMB",
            "ayanamsa_value_deg": 23.7261,
            "node_type": "TRUE",
            "house_system": "PLACIDUS",
            "zodiac": "SIDEREAL",
        },
        "ascendant": {
            "longitude": round((98.2331 + offset) % 360.0, 4),
            "sign": "Cancer",
            "sign_degree": round((8.2331 + offset) % 30.0, 4),
        },
        "planets": [_planet(index, offset) for index in range(9)],
        "houses": [_house(house, offset) for house in range(1, 13)],
        "dashas": None,
        "strengths": [],
        "divisional": {"d9": None, "d10": None},
        "transits": {"computed_at": None, "windows": []},
        "prediction_features": {
            "career": None,
            "finance": None,
            "relationship": None,
        },
    }


def assert_round_trip(chart: dict) -> None:
    parsed = ChartData.model_validate(chart)
    dumped = json.loads(parsed.model_dump_json())
    reparsed = ChartData.model_validate(dumped)
    assert reparsed.model_dump(mode="json") == parsed.model_dump(mode="json")


@pytest.mark.parametrize("offset", [0.0, 0.1, 0.2, 0.3, 0.4])
def test_five_valid_chart_examples_round_trip(offset: float) -> None:
    assert_round_trip(valid_chart(offset))


def test_progressive_optional_fields_can_be_absent() -> None:
    chart = valid_chart()
    for planet in chart["planets"]:
        assert "nakshatra" not in planet
        assert "kp" not in planet
        assert "house_occupied" not in planet
    assert_round_trip(chart)


def test_populated_later_engine_blocks_round_trip() -> None:
    chart = valid_chart()
    chart["planets"][6].update(
        {
            "house_occupied": 10,
            "nakshatra": {
                "name": "Purva Bhadrapada",
                "index": 25,
                "lord": "Jupiter",
                "degree_in_nakshatra": 8.7184,
                "pada": 3,
                "degree_in_pada": 2.0517,
                "navamsa_sign": "Libra",
            },
            "kp": {
                "star_lord": "Jupiter",
                "sub_lord": "Venus",
                "sub_sub_lord": "Saturn",
            },
            "significator_of_houses": [3, 6, 10, 11],
            "significator_levels": {"3": "C", "6": "B", "10": "A", "11": "D"},
        }
    )
    chart["houses"][9]["significators"] = {
        "A_in_star_of_occupants": ["Mercury", "Ketu"],
        "B_occupants": ["Saturn"],
        "C_in_star_of_owner": ["Sun"],
        "D_owner": ["Mercury"],
    }
    chart["dashas"] = {
        "system": "VIMSHOTTARI",
        "birth_balance": {"lord": "Venus", "years_remaining": 11.42},
        "current": {
            "mahadasha": {"lord": "Venus", "start": "2008-04-12", "end": "2028-04-12"},
            "antardasha": {"lord": "Saturn", "start": "2025-08-03", "end": "2028-04-12"},
            "pratyantardasha": {
                "lord": "Mercury",
                "start": "2026-05-21",
                "end": "2026-10-29",
            },
        },
        "upcoming_md_ad": [
            {"md": "Venus", "ad": "Mercury", "start": "2028-04-12", "end": "2031-02-11"}
        ],
        "upcoming_pd": [
            {
                "md": "Venus",
                "ad": "Saturn",
                "pd": "Ketu",
                "start": "2026-05-21",
                "end": "2026-06-03",
            }
        ],
    }
    chart["strengths"] = [
        {
            "planet": planet,
            "v1_score": 64,
            "components": {
                "dignity": 12,
                "house_placement": 6,
                "dig_bala": 0,
                "retrograde": 0,
                "combustion": 0,
                "aspects_net": -4,
                "base": 50,
            },
            "tier": "MODERATE",
            "notes": ["sample note"],
            "derived": planet in {"Rahu", "Ketu"},
        }
        for planet in PLANETS
    ]
    chart["divisional"] = {
        "d9": {
            "placements": {planet: SIGNS[index % 12] for index, planet in enumerate(PLANETS)},
            "flags": {"vargottama": ["Saturn"], "debilitated_in_d9": ["Venus"]},
        },
        "d10": {
            "placements": {
                planet: SIGNS[(index + 1) % 12] for index, planet in enumerate(PLANETS)
            },
            "flags": {
                "tenth_lord_well_placed": False,
                "tenth_lord_in_dusthana": False,
            },
        },
    }
    chart["transits"] = {
        "computed_at": "2026-06-18T07:30:00Z",
        "windows": [
            {
                "domain": "career",
                "start": "2026-07-12",
                "end": "2026-07-28",
                "triggers": ["Saturn trine natal 10th cusp"],
                "window_score": 0.74,
            }
        ],
    }
    chart["prediction_features"]["career"] = {
        "domain": "career",
        "primary_cusp_sub_lord": "Venus",
        "cusp_sub_lord_signifies": [2, 10, 11],
        "event_promise": True,
        "active_dasha_lords": ["Venus", "Saturn", "Mercury"],
        "dasha_support": {"Venus": [2, 10, 11], "Saturn": [6, 10]},
        "supporting_significators": ["Venus", "Saturn", "Mercury"],
        "blocking_significators": ["Mars"],
        "blocking_houses_hit": [5],
        "relevant_strengths": {"Venus": 71, "Saturn": 64, "Mercury": 58},
        "transit_windows": [
            {
                "start": "2026-07-12",
                "end": "2026-07-28",
                "triggers": ["Saturn trine natal 10th cusp"],
                "window_score": 0.74,
            }
        ],
        "rag_alignment": {"status": "aligned", "chunk_ids": ["kp_0231"]},
        "raw_score": 78,
        "confidence_tier": "MEDIUM",
        "probability_pct": 68,
    }

    assert_round_trip(chart)


@pytest.mark.parametrize(
    ("mutator", "expected_fragment"),
    [
        (lambda c: c.pop("schema_version"), "schema_version"),
        (lambda c: c["planets"][0].update({"longitude": 361.0}), "longitude"),
        (lambda c: c["houses"][0].update({"cusp_longitude": -0.01}), "cusp_longitude"),
        (lambda c: c["birth"].update({"lat": 70.0}), "lat"),
        (lambda c: c["birth"].update({"lon": 181.0}), "lon"),
        (lambda c: c["planets"][0].update({"longitude_deg": 12.3}), "longitude_deg"),
        (
            lambda c: c["planets"][0].update(
                {
                    "nakshatra": {
                        "name": "Ashwini",
                        "index": 1,
                        "lord": "Ketu",
                        "degree_in_nakshatra": 1.0,
                        "pada": 5,
                        "degree_in_pada": 1.0,
                        "navamsa_sign": "Aries",
                    }
                }
            ),
            "pada",
        ),
        (lambda c: c["houses"][0].update({"house": 13}), "house"),
        (lambda c: c["settings"].pop("ayanamsa"), "ayanamsa"),
    ],
)
def test_invalid_chart_constraints_rejected(mutator, expected_fragment: str) -> None:
    chart = valid_chart()
    mutator(chart)
    with pytest.raises(ValidationError) as exc_info:
        ChartData.model_validate(chart)
    assert expected_fragment in str(exc_info.value)


def test_unknown_planet_name_rejected() -> None:
    chart = valid_chart()
    chart["planets"][0]["name"] = "Pluto"
    with pytest.raises(ValidationError):
        ChartData.model_validate(chart)


def test_schema_file_was_generated_from_chart_model() -> None:
    schema = json.loads((ROOT / "schemas" / "chart.json").read_text())
    assert schema["title"] == "ChartData"
    assert schema["additionalProperties"] is False
    assert "schema_version" in schema["required"]
