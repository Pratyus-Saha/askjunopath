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
from app.core.config import settings  # noqa: E402
from app.engines.significator_engine import (  # noqa: E402
    CANONICAL_PLANET_ORDER,
    NodeAgency,
    NodeAwareSignificators,
    compare_significators_to_reference,
    compute_house_significator_ladders,
    compute_node_agency,
    compute_node_aware_significators,
    compute_planet_significators,
)
from app.routers.chart import _build_chart_payload  # noqa: E402
from app.schemas.models import BirthDataRequest  # noqa: E402

FIXTURE_PATH = (
    ROOT / "tests" / "fixtures" / "jhora" / "t41_significator_ladders_expected.json"
)
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

ASTROSAGE_FIXTURE_PATH = (
    ROOT / "tests" / "fixtures" / "external" / "astrosage_user1_significators.json"
)
ASTROSAGE = json.loads(ASTROSAGE_FIXTURE_PATH.read_text(encoding="utf-8"))

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


# ===========================================================================
# Node agency v2 (D028) — node-aware significators, internal only.
#
# Baseline preserved: the node-blind A/B/C/D ladder above is unchanged. The
# node-aware layer is a SEPARATE internal computation that never touches the
# public chart payload (D023) and never bumps schema/engine versions.
#
# Model (D028): a node (Rahu/Ketu) acts as an agent for the classical planets it
# represents through three deterministic channels — its sign lord (dispositor),
# classical planets in the same sign (conjunction), and classical planets casting
# Parashari graha drishti onto its sign (aspect). The node's star lord is already
# represented by the base ladder. Agency is bidirectional and single-pass: the
# node gains each agent's node-blind significations, and each agent gains the
# house the node occupies; a node never borrows from another node.
#
# The AstroSage table is an EXTERNAL COMPATIBILITY REFERENCE ONLY, not a parity
# judge (it is not JHora; the JHora final significator table is unavailable).
# ===========================================================================

# User 1 Kolkata node-blind planet->houses (the transpose of the validated T4.1
# ladder fixture). Hand-derived and cross-checked against the live engine.
USER1_NODE_BLIND_PLANET_HOUSES = {
    "Sun": [1, 2, 11, 12],
    "Moon": [3, 9, 10, 12],
    "Mars": [4, 5, 8, 9, 11],
    "Mercury": [2, 11, 12],
    "Jupiter": [5, 8],
    "Venus": [3, 6, 7, 9, 10, 12],
    "Saturn": [6, 7, 9],
    "Rahu": [1, 7],
    "Ketu": [1, 7],
}
# Node-aware planet->houses after node agency. Rahu's only agent is its
# dispositor Sun; Ketu's agents are dispositor Saturn and Mars (Mars's 8th-sign
# aspect Cancer->Aquarius). Mars therefore gains Ketu's house 7 (bidirectional).
USER1_NODE_AWARE_PLANET_HOUSES = {
    "Sun": [1, 2, 11, 12],
    "Moon": [3, 9, 10, 12],
    "Mars": [4, 5, 7, 8, 9, 11],
    "Mercury": [2, 11, 12],
    "Jupiter": [5, 8],
    "Venus": [3, 6, 7, 9, 10, 12],
    "Saturn": [6, 7, 9],
    "Rahu": [1, 2, 7, 11, 12],
    "Ketu": [1, 4, 5, 6, 7, 8, 9, 11],
}


def _np(name: str, sign: str, sign_lord: str, house: int, star_lord: str | None = None):
    """Hand-built planet carrying the fields node agency reads."""
    star = star_lord or sign_lord
    return {
        "name": name,
        "sign": sign,
        "sign_lord": sign_lord,
        "house_occupied": house,
        "kp": {"star_lord": star, "sub_lord": star},
    }


# --- Agency channels (no ephemeris): the deterministic agent-resolution rules ---

def test_node_agency_sign_lord_channel():
    # Rahu in Leo, dispositor Sun, nobody conjunct or aspecting -> the sign lord
    # is the only agent.
    planets = [
        _np("Rahu", "Leo", "Sun", 1),
        _np("Sun", "Cancer", "Moon", 12),   # Cancer->Leo is the 2nd, not an aspect
        _np("Moon", "Cancer", "Moon", 12),
    ]
    agency = compute_node_agency(planets)
    assert isinstance(agency["Rahu"], NodeAgency)
    assert agency["Rahu"].sign_lord == "Sun"
    assert agency["Rahu"].conjunct == []
    assert agency["Rahu"].aspecting == []
    assert agency["Rahu"].agents == ["Sun"]


def test_node_agency_conjunction_channel():
    # A classical planet sharing the node's sign is a conjunct agent, alongside
    # the dispositor.
    planets = [
        _np("Ketu", "Gemini", "Mercury", 3),
        _np("Mars", "Gemini", "Moon", 3),   # same sign as Ketu -> conjunct
    ]
    agency = compute_node_agency(planets)
    assert agency["Ketu"].conjunct == ["Mars"]
    assert agency["Ketu"].sign_lord == "Mercury"
    assert agency["Ketu"].aspecting == []
    assert agency["Ketu"].agents == ["Mars", "Mercury"]  # canonical order


def test_node_agency_special_aspect_channel():
    # Mars casts its 8th-sign aspect (Cancer -> Aquarius) onto Ketu; Saturn is the
    # dispositor. Saturn (Aries) does NOT aspect Aquarius (11th), so it is an agent
    # only through the sign-lord channel.
    planets = [
        _np("Ketu", "Aquarius", "Saturn", 7),
        _np("Mars", "Cancer", "Moon", 12),
        _np("Saturn", "Aries", "Mars", 9),
    ]
    agency = compute_node_agency(planets)
    assert agency["Ketu"].aspecting == ["Mars"]
    assert agency["Ketu"].conjunct == []
    assert agency["Ketu"].sign_lord == "Saturn"
    assert agency["Ketu"].agents == ["Mars", "Saturn"]


def test_node_agency_seventh_aspect_applies_to_every_planet():
    # The 7th-sign aspect is cast by every classical planet; Venus opposite the
    # node is an agent even though it has no special aspects.
    planets = [
        _np("Rahu", "Aries", "Mars", 1),
        _np("Venus", "Libra", "Venus", 7),   # Libra is the 7th sign from Aries
    ]
    agency = compute_node_agency(planets)
    assert agency["Rahu"].aspecting == ["Venus"]
    assert "Venus" in agency["Rahu"].agents


def test_nodes_are_never_agents_of_each_other():
    # Rahu and Ketu are always 180 deg apart (mutual 7th aspect), but a node never
    # borrows from another node: agents are the seven classical planets only.
    planets = [
        _np("Rahu", "Leo", "Sun", 1),
        _np("Ketu", "Aquarius", "Saturn", 7),
    ]
    agency = compute_node_agency(planets)
    assert "Ketu" not in agency["Rahu"].agents
    assert "Rahu" not in agency["Ketu"].agents
    assert agency["Rahu"].agents == ["Sun"]
    assert agency["Ketu"].agents == ["Saturn"]


# --- Full node-aware path (no ephemeris): borrowing + bidirectional ------------

def _synthetic_chart_ketu_disposited_by_saturn():
    # Ketu in Aquarius (dispositor Saturn) occupying house 4, which Saturn does
    # NOT own, so the bidirectional house gain is observable. Saturn is Ketu's
    # only agent.
    houses = [
        _house(1, "Sun", []),
        _house(2, "Mercury", []),
        _house(3, "Venus", []),
        _house(4, "Mars", ["Ketu"]),
        _house(5, "Jupiter", []),
        _house(6, "Saturn", []),
        _house(7, "Saturn", []),
        _house(8, "Jupiter", []),
        _house(9, "Mars", ["Saturn"]),
        _house(10, "Venus", []),
        _house(11, "Mercury", []),
        _house(12, "Moon", []),
    ]
    planets = [
        _np("Saturn", "Aries", "Mars", 9, star_lord="Saturn"),
        _np("Ketu", "Aquarius", "Saturn", 4, star_lord="Rahu"),
    ]
    return planets, houses


def test_node_aware_borrowing_and_bidirectional_without_ephemeris():
    planets, houses = _synthetic_chart_ketu_disposited_by_saturn()
    blind = compute_planet_significators(planets, houses)
    result = compute_node_aware_significators(planets, houses)

    assert result.node_agency["Ketu"].agents == ["Saturn"]
    # The node borrows the agent's full node-blind significations.
    for house in blind["Saturn"]:
        assert house in result.planet_to_houses["Ketu"]
    # The node keeps its own occupation (house 4).
    assert 4 in result.planet_to_houses["Ketu"]
    # Bidirectional: Saturn gains Ketu's house 4 it did not signify before.
    assert 4 not in blind["Saturn"]
    assert 4 in result.planet_to_houses["Saturn"]


# --- Node-blind transpose + node-aware values on the real User 1 chart ---------

@requires_swiss
def test_node_blind_planet_significators_match_validated_ladder_transpose():
    chart = _user1_chart()
    blind = compute_planet_significators(chart["planets"], chart["houses"])
    assert blind == USER1_NODE_BLIND_PLANET_HOUSES


@requires_swiss
def test_node_aware_significators_user1_match_hand_computed():
    chart = _user1_chart()
    result = compute_node_aware_significators(chart["planets"], chart["houses"])
    assert isinstance(result, NodeAwareSignificators)
    assert result.node_blind_planet_to_houses == USER1_NODE_BLIND_PLANET_HOUSES
    assert result.planet_to_houses == USER1_NODE_AWARE_PLANET_HOUSES


@requires_swiss
def test_node_aware_agency_trace_on_real_user1_chart():
    chart = _user1_chart()
    result = compute_node_aware_significators(chart["planets"], chart["houses"])
    assert result.node_agency["Rahu"].sign_lord == "Sun"
    assert result.node_agency["Rahu"].agents == ["Sun"]
    assert result.node_agency["Ketu"].sign_lord == "Saturn"
    assert result.node_agency["Ketu"].aspecting == ["Mars"]
    assert result.node_agency["Ketu"].agents == ["Mars", "Saturn"]


@requires_swiss
def test_node_agency_is_bidirectional_mars_gains_ketu_house():
    # Mars aspects Ketu (house 7), so node-aware Mars signifies house 7 even though
    # node-blind Mars does not.
    chart = _user1_chart()
    result = compute_node_aware_significators(chart["planets"], chart["houses"])
    assert 7 not in result.node_blind_planet_to_houses["Mars"]
    assert 7 in result.planet_to_houses["Mars"]
    assert "Mars" in result.node_agency["Ketu"].agents


@requires_swiss
def test_node_aware_house_to_planets_is_inverse_of_planet_to_houses():
    chart = _user1_chart()
    result = compute_node_aware_significators(chart["planets"], chart["houses"])
    rebuilt = {h: [] for h in range(1, 13)}
    for planet in CANONICAL_PLANET_ORDER:
        for house in result.planet_to_houses[planet]:
            rebuilt[house].append(planet)
    assert result.house_to_planets == rebuilt


@requires_swiss
def test_node_aware_engine_is_separate_from_public_chart_and_mutates_nothing():
    chart = _user1_chart()

    # Reserved public significator fields stay unpopulated (D023) before the call.
    for planet in chart["planets"]:
        assert planet["significator_of_houses"] == []
        assert planet["significator_levels"] == {}
    for house in chart["houses"]:
        assert house["significators"] is None

    before = copy.deepcopy(chart)
    result = compute_node_aware_significators(chart["planets"], chart["houses"])

    # The node-aware output is a separate object; the chart payload is untouched.
    assert isinstance(result, NodeAwareSignificators)
    assert chart == before
    for planet in chart["planets"]:
        assert planet["significator_of_houses"] == []
        assert planet["significator_levels"] == {}
    for house in chart["houses"]:
        assert house["significators"] is None


@requires_swiss
def test_public_api_and_versions_unchanged_by_node_aware_engine():
    chart = _user1_chart()
    assert chart["schema_version"] == "1.2"
    assert chart["dashas"] is None
    assert settings.chart_engine_version == "1.4.0"

    compute_node_aware_significators(chart["planets"], chart["houses"])

    # No schema/engine version moved; reserved public fields stay empty.
    assert chart["schema_version"] == "1.2"
    assert settings.chart_engine_version == "1.4.0"
    assert chart["dashas"] is None
    for planet in chart["planets"]:
        assert planet["significator_of_houses"] == []
        assert planet["significator_levels"] == {}
    for house in chart["houses"]:
        assert house["significators"] is None


# --- AstroSage external reference + honest comparison --------------------------

def test_astrosage_fixture_is_external_reference_only_not_judge():
    assert ASTROSAGE["external_reference_only"] is True
    assert ASTROSAGE["is_judge"] is False
    assert "AstroSage" in ASTROSAGE["source"]
    # The reference must not masquerade as a JHora export.
    assert "JHora" not in ASTROSAGE["source"]
    assert ASTROSAGE["chart_id"] == "user1_kolkata"


def test_astrosage_fixture_two_directions_are_self_consistent():
    # Guards the reference data itself: planet->houses and house->planets invert.
    pth = ASTROSAGE["planet_to_houses"]
    htp = ASTROSAGE["house_to_planets"]
    rebuilt = {name: [] for name in CANONICAL_PLANET_ORDER}
    for house_str, names in htp.items():
        for name in names:
            rebuilt[name].append(int(house_str))
    for name in CANONICAL_PLANET_ORDER:
        assert sorted(rebuilt[name]) == pth[name], name


@requires_swiss
def test_comparison_report_against_astrosage_is_honest():
    chart = _user1_chart()
    result = compute_node_aware_significators(chart["planets"], chart["houses"])
    report = compare_significators_to_reference(result, ASTROSAGE)

    # The report never claims AstroSage is JHora or a parity judge.
    assert report["reference_is_judge"] is False
    assert report["external_reference_only"] is True
    assert "AstroSage" in report["reference_source"]

    per_planet = report["planet_to_houses"]
    # Naturally matching planets (no tuning): Sun, Mercury, Mars.
    assert per_planet["Sun"]["match"] is True
    assert per_planet["Mercury"]["match"] is True
    assert per_planet["Mars"]["match"] is True
    # The nodes diverge from AstroSage's convention; reported, never hidden.
    assert per_planet["Rahu"]["match"] is False
    assert per_planet["Ketu"]["match"] is False
    assert per_planet["Rahu"]["only_reference"] == [6]
    assert per_planet["Rahu"]["only_ours"] == [1, 2, 7, 11]

    assert report["summary"]["planets_total"] == 9
    assert report["summary"]["planets_matching"] == 3
    assert set(report["summary"]["matching_planets"]) == {"Sun", "Mercury", "Mars"}
