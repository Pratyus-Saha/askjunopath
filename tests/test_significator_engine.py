"""Tests for the internal base KP A/B/C/D significator ladder engine.

Fixture parity (36 houses across User 1 Kolkata, User 2 Mumbai, User 5
Siliguri) is judged against tests/fixtures/jhora/t41_significator_ladders_expected.json,
whose expected values are the T4.1 hand-worked ladders cross-checked against
JHora (AGENTS.md Rule 8 — code conforms to the fixture, never the reverse).

The parity tests run the real pipeline: ephemeris_engine -> _build_chart_payload
(which fills kp.star_lord via the KP engine, cusp_sign_lord via ephemeris, and
occupants via the D024 bhava-span house engine) -> compute_house_significator_ladders.
They are guarded by ephemeris_files_ok() and skip loudly when the run may be on
Moshier fallback, mirroring the JHora gate.

The unit tests use hand-built inputs and need no ephemeris: they exercise empty
houses, multi-occupant houses, A/C star-lord matching, canonical order +
deduplication, Rahu/Ketu treated as normal names, loud failure on an unsupported
owner, and the guarantee that the engine populates no public chart field and
mutates no input.
"""

from __future__ import annotations

import copy
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

import pytest  # noqa: E402

from app.engines.ephemeris_engine import (  # noqa: E402
    compute_ephemeris,
    ephemeris_files_ok,
)
from app.engines.significator_engine import (  # noqa: E402
    CANONICAL_PLANET_ORDER,
    compute_house_significator_ladders,
)
from app.routers.chart import _build_chart_payload  # noqa: E402
from app.schemas.models import BirthDataRequest  # noqa: E402

FIXTURE_PATH = (
    ROOT / "tests" / "fixtures" / "jhora" / "t41_significator_ladders_expected.json"
)
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

LEVELS = ("A", "B", "C", "D")


# ---------------------------------------------------------------------------
# Fixture parity: the real pipeline reproduces every hand-worked ladder.
# ---------------------------------------------------------------------------

requires_swiss = pytest.mark.skipif(
    not ephemeris_files_ok(),
    reason="SWISS_EPHE_REQUIRED: significator parity needs .se1 files; current "
    "run may be Moshier fallback.",
)


def _chart_for(fixture_chart: dict) -> dict:
    chart_input = fixture_chart["input"]
    request_data = BirthDataRequest(
        birth_date=chart_input["date"],
        birth_time=chart_input["time"][:5],
        birth_city=chart_input["place"],
    )
    ephemeris = compute_ephemeris(
        datetime_local=f"{chart_input['date']}T{chart_input['time']}",
        timezone=chart_input["iana_timezone"],
        lat=chart_input["latitude"],
        lon=chart_input["longitude"],
    )
    return _build_chart_payload(
        ephemeris=ephemeris,
        place_label=chart_input["place"],
        request_data=request_data,
        geo_lat=chart_input["latitude"],
        geo_lon=chart_input["longitude"],
        timezone_str=chart_input["iana_timezone"],
    )


def test_fixture_has_three_charts_of_twelve_rows_each():
    assert len(FIXTURE["charts"]) == 3
    assert [c["chart_id"] for c in FIXTURE["charts"]] == [
        "user1_kolkata",
        "user2_mumbai",
        "user5_siliguri",
    ]
    total_rows = 0
    for chart in FIXTURE["charts"]:
        assert [row["house"] for row in chart["rows"]] == list(range(1, 13))
        total_rows += len(chart["rows"])
    assert total_rows == 36


@requires_swiss
@pytest.mark.parametrize(
    "fixture_chart", FIXTURE["charts"], ids=[c["chart_id"] for c in FIXTURE["charts"]]
)
def test_house_significator_ladders_match_fixture(fixture_chart):
    chart = _chart_for(fixture_chart)
    ladders = compute_house_significator_ladders(chart["planets"], chart["houses"])

    assert set(ladders) == set(range(1, 13)), fixture_chart["chart_id"]

    by_house = {h["house"]: h for h in chart["houses"]}
    for row in fixture_chart["rows"]:
        house = row["house"]
        cid = f"{fixture_chart['chart_id']} house {house}"

        # The inputs that drive the ladder must match the fixture too, so a
        # passing ladder can never be a coincidence of two wrong inputs.
        assert by_house[house]["cusp_sign_lord"] == row["owner"], cid
        assert by_house[house]["occupants"] == row["occupants"], cid

        for level in LEVELS:
            assert ladders[house][level] == row[level], f"{cid} level {level}"


@requires_swiss
def test_every_emitted_list_is_canonically_ordered_on_real_charts():
    order_index = {name: i for i, name in enumerate(CANONICAL_PLANET_ORDER)}
    for fixture_chart in FIXTURE["charts"]:
        chart = _chart_for(fixture_chart)
        ladders = compute_house_significator_ladders(
            chart["planets"], chart["houses"]
        )
        for house, levels in ladders.items():
            for level in LEVELS:
                names = levels[level]
                indices = [order_index[name] for name in names]
                assert indices == sorted(indices), (
                    f"{fixture_chart['chart_id']} house {house} level {level}"
                )
                assert len(names) == len(set(names))


# ---------------------------------------------------------------------------
# Targeted real-chart behaviors (User 1 Kolkata).
# ---------------------------------------------------------------------------

def _user1_chart() -> dict:
    return _chart_for(FIXTURE["charts"][0])


@requires_swiss
def test_empty_house_has_empty_a_and_b_but_owner_driven_c_and_d():
    # User 1 house 2 is empty: B and A are empty, C comes from owner star-lord
    # matches, D is the owner.
    ladders = compute_house_significator_ladders(
        _user1_chart()["planets"], _user1_chart()["houses"]
    )
    assert ladders[2]["B"] == []
    assert ladders[2]["A"] == []
    assert ladders[2]["C"] == ["Sun", "Mercury"]  # planets in star of owner Mercury
    assert ladders[2]["D"] == ["Mercury"]


@requires_swiss
def test_multi_occupant_house_lists_all_occupants_in_canonical_order():
    # User 1 house 12 has three occupants.
    ladders = compute_house_significator_ladders(
        _user1_chart()["planets"], _user1_chart()["houses"]
    )
    assert ladders[12]["B"] == ["Sun", "Mercury", "Venus"]
    # A = planets in the star of those occupants, canonical and deduped.
    assert ladders[12]["A"] == ["Sun", "Moon", "Mercury"]


@requires_swiss
def test_a_level_matches_star_lord_of_occupants():
    # User 1 house 7: only occupant is Ketu; A = planets whose star lord is Ketu
    # (Saturn and Rahu both sit in Ketu's nakshatra in this chart).
    ladders = compute_house_significator_ladders(
        _user1_chart()["planets"], _user1_chart()["houses"]
    )
    assert ladders[7]["B"] == ["Ketu"]
    assert ladders[7]["A"] == ["Saturn", "Rahu"]


@requires_swiss
def test_c_level_matches_star_lord_of_owner():
    # User 1 house 5: owner Jupiter; C = planets whose star lord is Jupiter.
    ladders = compute_house_significator_ladders(
        _user1_chart()["planets"], _user1_chart()["houses"]
    )
    assert ladders[5]["C"] == ["Mars", "Jupiter"]
    assert ladders[5]["D"] == ["Jupiter"]


@requires_swiss
def test_rahu_and_ketu_are_handled_as_normal_names():
    # House 1 occupant Rahu drives A=[Ketu] (Ketu's star lord is Rahu... matched
    # the other way: planets whose star lord is the occupant). House 7 occupant
    # Ketu drives A=[Saturn, Rahu]. Both prove nodes act as plain names for
    # star-lord matching and as occupants, with no extra node agency.
    ladders = compute_house_significator_ladders(
        _user1_chart()["planets"], _user1_chart()["houses"]
    )
    assert "Rahu" in ladders[1]["B"]
    assert ladders[1]["A"] == ["Ketu"]
    assert "Ketu" in ladders[7]["B"]
    assert ladders[7]["A"] == ["Saturn", "Rahu"]


@requires_swiss
def test_engine_does_not_populate_public_significator_fields_or_mutate_chart():
    chart = _user1_chart()

    # Pre-state: house task left significators reserved (D023).
    for planet in chart["planets"]:
        assert planet["significator_of_houses"] == []
        assert planet["significator_levels"] == {}
    for house in chart["houses"]:
        assert house["significators"] is None

    before = copy.deepcopy(chart)
    compute_house_significator_ladders(chart["planets"], chart["houses"])

    # The engine reads only: nothing in the chart changed, and the reserved
    # public significator fields are still unpopulated.
    assert chart == before
    for planet in chart["planets"]:
        assert planet["significator_of_houses"] == []
        assert planet["significator_levels"] == {}
    for house in chart["houses"]:
        assert house["significators"] is None


# ---------------------------------------------------------------------------
# Hand-built unit tests (no ephemeris): the deterministic ladder rules.
# ---------------------------------------------------------------------------

def _planet(name: str, star_lord: str) -> dict:
    return {"name": name, "kp": {"star_lord": star_lord, "sub_lord": star_lord}}


def _house(number: int, owner: str, occupants: list[str]) -> dict:
    return {"house": number, "cusp_sign_lord": owner, "occupants": occupants}


def test_levels_are_deduplicated_and_canonically_ordered():
    # Planets deliberately listed out of canonical order; Saturn shares a star
    # lord (Sun) with Mercury, and the occupants list carries a duplicate.
    planets = [
        _planet("Saturn", "Sun"),
        _planet("Mercury", "Sun"),
        _planet("Sun", "Moon"),
    ]
    # owner Sun -> C = planets whose star lord is Sun = {Saturn, Mercury},
    # which must come out canonically ordered as [Mercury, Saturn].
    houses = [_house(1, "Sun", ["Mars", "Mars"])]
    ladders = compute_house_significator_ladders(planets, houses)

    assert ladders[1]["C"] == ["Mercury", "Saturn"]
    assert ladders[1]["B"] == ["Mars"]  # duplicate collapsed
    assert ladders[1]["D"] == ["Sun"]


def test_empty_house_unit_behaviour():
    # No planet's star lord is the owner Venus, and there are no occupants, so
    # every level is empty except D = [owner].
    planets = [_planet("Mars", "Sun"), _planet("Jupiter", "Moon")]
    houses = [_house(1, "Venus", [])]
    ladders = compute_house_significator_ladders(planets, houses)
    assert ladders[1] == {"A": [], "B": [], "C": [], "D": ["Venus"]}


def test_outer_planets_and_non_classical_occupants_are_ignored():
    planets = [
        _planet("Sun", "Mars"),
        _planet("Pluto", "Mars"),  # ignored: not a classical planet
    ]
    houses = [_house(1, "Mars", ["Moon", "Uranus"])]  # Uranus ignored as occupant
    ladders = compute_house_significator_ladders(planets, houses)

    # Only the classical occupant survives in B; Pluto never appears anywhere.
    assert ladders[1]["B"] == ["Moon"]
    assert ladders[1]["C"] == ["Sun"]  # Sun's star lord is Mars (the owner)
    assert "Pluto" not in ladders[1]["C"]


def test_unsupported_owner_fails_loudly():
    planets = [_planet("Sun", "Moon")]
    houses = [_house(1, "Pluto", [])]  # Pluto is not a supported owner
    with pytest.raises(ValueError, match="supported classical planets"):
        compute_house_significator_ladders(planets, houses)


def test_star_lord_falls_back_to_nakshatra_lord_when_no_kp_block():
    planets = [{"name": "Sun", "nakshatra": {"lord": "Mars"}}]
    houses = [_house(1, "Mars", [])]
    ladders = compute_house_significator_ladders(planets, houses)
    assert ladders[1]["C"] == ["Sun"]  # Sun's (nakshatra) star lord is the owner
