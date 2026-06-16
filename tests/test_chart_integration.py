"""Integration tests: /chart/generate carries nakshatra, KP, and houses.

Every planet must carry a non-null 7-key NakshatraBlock computed from its
own longitude; every house cusp must carry the nakshatra NAME STRING in
cusp_nakshatra (never an object). Every planet and house must also carry the
D022 public KP block with only star_lord/sub_lord. House occupation is filled
by JHora bhava midpoint spans (D024), while significators, dasha, strength,
divisional, transits, and prediction features remain at their null/empty
defaults.

Geocoding and Supabase are mocked; ephemeris and nakshatra math are real.
Moon nakshatra/pada expectations below are hand-derived from each Day 1
fixture's JHora-expected Moon longitude using the docs/nakshatra.md
integer arc-second convention — independently of the engine under test.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import main as app_main  # noqa: E402
from app.engines.ephemeris_engine import compute_ephemeris  # noqa: E402
from app.engines.house_engine import house_of, occupants as house_occupants  # noqa: E402
from app.engines.kp_engine import get_kp_sub_lord  # noqa: E402
from app.engines.nakshatra_engine import (  # noqa: E402
    NAKSHATRAS,
    nakshatra_block,
    nakshatra_name,
)
from app.routers import chart as chart_router  # noqa: E402
from app.schemas.models import BirthDataRequest, ChartData  # noqa: E402

FIXTURES_DIR = ROOT / "tests" / "fixtures" / "charts"

APPROVED_NAKSHATRA_BLOCK_KEYS = {
    "name",
    "index",
    "lord",
    "degree_in_nakshatra",
    "pada",
    "degree_in_pada",
    "navamsa_sign",
}
APPROVED_KP_BLOCK_KEYS = {"star_lord", "sub_lord"}
INTERNAL_KP_KEYS = {
    "sub_index",
    "sub_start_longitude",
    "sub_end_longitude",
    "degree_in_sub",
    "sub_sub_lord",
    "nakshatra_index",
    "nakshatra_name",
    "row_index",
    "longitude",
    "arcsec",
}
LEGACY_CUSP_KP_FIELDS = {
    "cusp_star_lord",
    "cusp_sub_lord",
    "cusp_sub_sub_lord",
}

NAKSHATRA_NAMES = {name for name, _lord in NAKSHATRAS}

PLANET_ORDER = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
    "Rahu", "Ketu",
]

# Hand-derived per docs/nakshatra.md from expected.planets.Moon:
#   arcsec = round(L * 3600); index0 = arcsec // 48000;
#   pada = (arcsec % 48000) // 12000 + 1; lord from the frozen table.
# fixture_01: 76.917617  -> 276903"  -> Ardra (6), pada 4, Rahu
# fixture_02: 284.904583 -> 1025656" -> Shravana (22), pada 2, Moon
# fixture_03: 322.255028 -> 1160118" -> Purva Bhadrapada (25), pada 1, Jupiter
# fixture_04: 280.987392 -> 1011555" -> Shravana (22), pada 1, Moon
# fixture_05: 280.997386 -> 1011591" -> Shravana (22), pada 1, Moon
# Every value sits >900 arc-sec from the nearest pada boundary, so the
# engine's 5 arc-sec JHora tolerance cannot flip any expectation.
MOON_EXPECTATIONS = {
    "fixture_01_india": {"name": "Ardra", "pada": 4, "lord": "Rahu"},
    "fixture_02_us_dst": {"name": "Shravana", "pada": 2, "lord": "Moon"},
    "fixture_03_midnight": {
        "name": "Purva Bhadrapada", "pada": 1, "lord": "Jupiter",
    },
    "fixture_04_pre1990": {"name": "Shravana", "pada": 1, "lord": "Moon"},
    "fixture_05_southern": {"name": "Shravana", "pada": 1, "lord": "Moon"},
}

FIXTURES = [
    json.loads(path.read_text(encoding="utf-8"))
    for path in sorted(FIXTURES_DIR.glob("fixture_*.json"))
]

HEADERS = {"X-User-Id": "integration-test-user"}


def request_body_for(fixture_input: dict) -> dict:
    """Split fixture datetime_local into the route's date/time fields.

    The route reconstructs datetime_local as f"{date}T{time}:00", so the
    fixture's seconds must be :00 for the engine input to match exactly.
    """
    date_part, time_part = fixture_input["datetime_local"].split("T")
    assert time_part.endswith(":00"), fixture_input["datetime_local"]
    return {
        "birth_date": date_part,
        "birth_time": time_part[:5],
        "birth_city": "Fixture City",
    }


def generate_chart(monkeypatch, fixture: dict) -> tuple[dict, dict]:
    """POST /chart/generate on the MISS path for a Day 1 fixture input.

    Returns (response chart, chart_data passed to save_chart) so tests can
    assert the persisted object carries the same nakshatra fill as the
    response.
    """
    fixture_input = fixture["input"]
    geo_result = {
        "latitude": fixture_input["lat"],
        "longitude": fixture_input["lon"],
        "timezone": fixture_input["timezone"],
        "display_name": "Fixture Place",
        "country": "Fixtureland",
    }
    saved = {}

    async def fake_geocode(self, city_name: str) -> dict:
        return dict(geo_result)

    def fake_get_chart(user_id: str, fingerprint: str):
        return None

    def fake_save_chart(user_id, chart_fingerprint, birth_data, chart_data):
        saved["chart_data"] = chart_data
        return {"id": "integration-test-row-id"}

    monkeypatch.setattr(chart_router.GeocodingService, "geocode", fake_geocode)
    monkeypatch.setattr(chart_router, "get_chart_by_fingerprint", fake_get_chart)
    monkeypatch.setattr(chart_router, "save_chart", fake_save_chart)

    client = TestClient(app_main.app)
    response = client.post(
        "/chart/generate", json=request_body_for(fixture_input), headers=HEADERS
    )
    assert response.status_code == 200, response.text
    return response.json()["chart"], saved["chart_data"]


@pytest.fixture
def chart(monkeypatch):
    """Generated chart for fixture_01 (the canonical route-test input)."""
    return generate_chart(monkeypatch, FIXTURES[0])[0]


# ---------------------------------------------------------------------------
# Planet nakshatra blocks
# ---------------------------------------------------------------------------

def test_chart_has_nine_planets(chart):
    assert len(chart["planets"]) == 9
    assert [p["name"] for p in chart["planets"]] == PLANET_ORDER


def test_every_planet_has_a_non_null_nakshatra_block(chart):
    for planet in chart["planets"]:
        assert planet["nakshatra"] is not None, planet["name"]
        assert isinstance(planet["nakshatra"], dict), planet["name"]


def test_every_planet_nakshatra_block_has_exactly_the_seven_approved_keys(chart):
    for planet in chart["planets"]:
        assert (
            set(planet["nakshatra"].keys()) == APPROVED_NAKSHATRA_BLOCK_KEYS
        ), planet["name"]


def test_planet_nakshatra_block_values_are_well_formed(chart):
    for planet in chart["planets"]:
        block = planet["nakshatra"]
        assert block["name"] in NAKSHATRA_NAMES, planet["name"]
        assert 1 <= block["index"] <= 27, planet["name"]
        assert 1 <= block["pada"] <= 4, planet["name"]
        assert 0.0 <= block["degree_in_nakshatra"] < 13.333334, planet["name"]
        assert 0.0 <= block["degree_in_pada"] < 3.333334, planet["name"]


def test_planet_nakshatra_block_derives_from_that_planets_longitude(chart):
    # Wiring check: the block in the output is exactly the trusted engine's
    # block for the longitude in the same planet object. Boundary truth
    # itself is fixture-judged in tests/test_nakshatra_engine.py.
    for planet in chart["planets"]:
        assert planet["nakshatra"] == nakshatra_block(planet["longitude"]), (
            planet["name"]
        )


# ---------------------------------------------------------------------------
# House cusp nakshatra names
# ---------------------------------------------------------------------------

def test_chart_has_twelve_houses(chart):
    assert len(chart["houses"]) == 12
    assert [h["house"] for h in chart["houses"]] == list(range(1, 13))


def test_every_cusp_nakshatra_is_a_name_string_never_an_object(chart):
    for house in chart["houses"]:
        cusp_nakshatra = house["cusp_nakshatra"]
        assert isinstance(cusp_nakshatra, str), house["house"]
        assert not isinstance(cusp_nakshatra, dict)
        assert cusp_nakshatra in NAKSHATRA_NAMES, house["house"]


def test_cusp_nakshatra_derives_from_that_houses_cusp_longitude(chart):
    for house in chart["houses"]:
        assert house["cusp_nakshatra"] == nakshatra_name(
            house["cusp_longitude"]
        ), house["house"]


# ---------------------------------------------------------------------------
# Public KP blocks
# ---------------------------------------------------------------------------

def test_every_planet_has_public_kp_block_only(chart):
    for planet in chart["planets"]:
        kp = planet["kp"]
        assert isinstance(kp, dict), planet["name"]
        assert set(kp) == APPROVED_KP_BLOCK_KEYS, planet["name"]
        assert set(kp).isdisjoint(INTERNAL_KP_KEYS), planet["name"]


def test_planet_kp_block_derives_from_that_planets_longitude(chart):
    for planet in chart["planets"]:
        lookup = get_kp_sub_lord(planet["longitude"])
        assert planet["kp"] == {
            "star_lord": lookup["star_lord"],
            "sub_lord": lookup["sub_lord"],
        }, planet["name"]


def test_every_house_has_public_kp_block_only(chart):
    for house in chart["houses"]:
        kp = house["kp"]
        assert isinstance(kp, dict), house["house"]
        assert set(kp) == APPROVED_KP_BLOCK_KEYS, house["house"]
        assert set(kp).isdisjoint(INTERNAL_KP_KEYS), house["house"]
        assert set(house).isdisjoint(LEGACY_CUSP_KP_FIELDS), house["house"]


def test_house_kp_block_derives_from_that_houses_cusp_longitude(chart):
    for house in chart["houses"]:
        lookup = get_kp_sub_lord(house["cusp_longitude"])
        assert house["kp"] == {
            "star_lord": lookup["star_lord"],
            "sub_lord": lookup["sub_lord"],
        }, house["house"]


# ---------------------------------------------------------------------------
# House occupation
# ---------------------------------------------------------------------------

def test_every_planet_has_house_occupied(chart):
    for planet in chart["planets"]:
        assert isinstance(planet["house_occupied"], int), planet["name"]
        assert 1 <= planet["house_occupied"] <= 12, planet["name"]


def test_every_house_has_occupants_list(chart):
    for house in chart["houses"]:
        assert isinstance(house["occupants"], list), house["house"]


def test_planet_house_occupied_derives_from_bhava_spans(chart):
    cusps = [house["cusp_longitude"] for house in chart["houses"]]

    for planet in chart["planets"]:
        assert planet["house_occupied"] == house_of(
            planet["longitude"], cusps
        ), planet["name"]


def test_house_occupants_are_consistent_with_planet_house_occupied(chart):
    planet_house = {
        planet["name"]: planet["house_occupied"] for planet in chart["planets"]
    }

    for house in chart["houses"]:
        for occupant in house["occupants"]:
            assert planet_house[occupant] == house["house"]

    all_occupants = [
        occupant for house in chart["houses"] for occupant in house["occupants"]
    ]
    assert sorted(all_occupants) == sorted(PLANET_ORDER)


def test_house_occupant_round_trip_matches_house_engine(chart):
    cusps = [house["cusp_longitude"] for house in chart["houses"]]
    expected = house_occupants(chart["planets"], cusps)

    assert {
        house["house"]: house["occupants"] for house in chart["houses"]
    } == expected


# ---------------------------------------------------------------------------
# User 1 Kolkata regression: JHora "Planets in it" parity (D024)
# ---------------------------------------------------------------------------

# Birth: 1998-08-14 06:45, Kolkata, India. The expected house numbers below
# are transcribed from JHora's "House Start / Cusp / End / Planets in it"
# table for this chart and are the source of truth (AGENTS.md Rule 8). Only
# the 9 classical planets are asserted; JHora's outer-planet rows (Pluto H4,
# Uranus/Neptune H6) are intentionally not part of our public output.
USER1_KOLKATA = {
    "birth_date": "1998-08-14",
    "birth_time": "06:45",
    "datetime_local": "1998-08-14T06:45:00",
    "timezone": "Asia/Kolkata",
    "lat": 22.5725,
    "lon": 88.363889,
    "place": "Kolkata, India",
}
USER1_KOLKATA_JHORA_OCCUPATION = {
    "Rahu": 1,
    "Ketu": 7,
    "Jupiter": 8,
    "Moon": 9,
    "Saturn": 9,
    "Mars": 11,
    "Sun": 12,
    "Mercury": 12,
    "Venus": 12,
}


def _user1_kolkata_chart() -> dict:
    request_data = BirthDataRequest(
        birth_date=USER1_KOLKATA["birth_date"],
        birth_time=USER1_KOLKATA["birth_time"],
        birth_city=USER1_KOLKATA["place"],
    )
    ephemeris = compute_ephemeris(
        datetime_local=USER1_KOLKATA["datetime_local"],
        timezone=USER1_KOLKATA["timezone"],
        lat=USER1_KOLKATA["lat"],
        lon=USER1_KOLKATA["lon"],
    )
    return chart_router._build_chart_payload(
        ephemeris=ephemeris,
        place_label=USER1_KOLKATA["place"],
        request_data=request_data,
        geo_lat=USER1_KOLKATA["lat"],
        geo_lon=USER1_KOLKATA["lon"],
        timezone_str=USER1_KOLKATA["timezone"],
    )


def test_user1_kolkata_house_occupation_matches_jhora_planets_in_it():
    chart = _user1_kolkata_chart()

    occupied = {planet["name"]: planet["house_occupied"] for planet in chart["planets"]}
    for planet_name, house in USER1_KOLKATA_JHORA_OCCUPATION.items():
        assert occupied[planet_name] == house, planet_name

    # occupants[] round-trips with the JHora "Planets in it" placement.
    occupants_by_house = {
        house["house"]: set(house["occupants"]) for house in chart["houses"]
    }
    for planet_name, house in USER1_KOLKATA_JHORA_OCCUPATION.items():
        assert planet_name in occupants_by_house[house], planet_name


# ---------------------------------------------------------------------------
# Later-engine fields stay untouched
# ---------------------------------------------------------------------------

def test_significators_remain_unpopulated_by_house_task(chart):
    for planet in chart["planets"]:
        assert planet["significator_of_houses"] == [], planet["name"]
        assert planet["significator_levels"] == {}, planet["name"]
    for house in chart["houses"]:
        assert house["significators"] is None, house["house"]


def test_other_later_engine_fields_remain_at_defaults(chart):
    assert chart["dashas"] is None
    assert chart["strengths"] == []
    assert chart["divisional"] == {"d9": None, "d10": None}
    assert chart["transits"]["windows"] == []
    assert chart["prediction_features"] == {
        "career": None, "finance": None, "relationship": None,
    }


# ---------------------------------------------------------------------------
# Schema contract
# ---------------------------------------------------------------------------

def test_chart_with_metadata_validates_through_chartdata(chart):
    parsed = ChartData.model_validate(chart)
    assert parsed.schema_version == "1.2"
    assert parsed.metadata is not None
    assert parsed.metadata.engine_version == "1.4.0"
    for planet in parsed.planets:
        assert planet.nakshatra is not None, planet.name
        assert planet.kp is not None, planet.name
    for house in parsed.houses:
        assert isinstance(house.cusp_nakshatra, str), house.house
        assert house.kp is not None, house.house


def test_saved_chart_carries_the_same_nakshatra_fill(monkeypatch):
    chart, saved_chart = generate_chart(monkeypatch, FIXTURES[0])
    assert saved_chart == chart
    for planet in saved_chart["planets"]:
        assert set(planet["nakshatra"].keys()) == APPROVED_NAKSHATRA_BLOCK_KEYS
        assert set(planet["kp"].keys()) == APPROVED_KP_BLOCK_KEYS
    for house in saved_chart["houses"]:
        assert isinstance(house["cusp_nakshatra"], str)
        assert set(house["kp"].keys()) == APPROVED_KP_BLOCK_KEYS
        assert set(house).isdisjoint(LEGACY_CUSP_KP_FIELDS)


# ---------------------------------------------------------------------------
# Moon truth on the Day 1 fixture charts
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "fixture", FIXTURES, ids=[f["chart_id"] for f in FIXTURES]
)
def test_moon_nakshatra_and_pada_match_hand_derived_fixture_values(
    monkeypatch, fixture
):
    expected = MOON_EXPECTATIONS[fixture["chart_id"]]
    assert fixture["expected"]["planets"]["Moon"] is not None

    chart, _saved = generate_chart(monkeypatch, fixture)
    moon = next(p for p in chart["planets"] if p["name"] == "Moon")
    block = moon["nakshatra"]
    assert block["name"] == expected["name"], fixture["chart_id"]
    assert block["pada"] == expected["pada"], fixture["chart_id"]
    assert block["lord"] == expected["lord"], fixture["chart_id"]
