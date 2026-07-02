"""Tests for the Vedic (Parashari) engine.

Two tiers, kept strictly separate (task spec):

* STRUCTURAL self-tests — no JHora oracle. They assert invariants that are true
  by construction (Ketu = Rahu + 180, houses tile 12, varga range, the classical
  varga mapping, dasha nesting, settings block). These run unconditionally.

* FIELD A (placements/houses/vargas/dasha vs JHora) — needs
  ``tests/fixtures/vedic_fixtures.json``. That file does not exist yet, so these
  tests SKIP with a "blocked on fixtures" message. They never fabricate values.

Field B (dignity / graha drishti) is NOT asserted here: no ground truth exists.
It is printed for human review by ``scripts/vedic_validate.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.engines.vedic_engine import (
    SETTINGS,
    aspected_houses,
    compute_vedic_chart,
    dignity_of,
    varga_sign_index,
    whole_sign_house,
)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "vedic_fixtures.json"

# One self-chosen SMOKE chart (Bengaluru, +05:30). NOT a fixture, NOT validation
# — only exercises the code paths so the structural invariants have data.
_SMOKE = dict(
    datetime_local="1990-01-01T14:35:00",
    gmt_offset=5.5,
    lat=12.9716,
    lon=77.5946,
    target_date="2026-07-02T12:00:00",
)


@pytest.fixture(scope="module")
def smoke_chart() -> dict:
    return compute_vedic_chart(**_SMOKE)


# ---------------------------------------------------------------------------
# Structural self-tests (no oracle)
# ---------------------------------------------------------------------------

def test_settings_block_present_and_correct(smoke_chart):
    assert smoke_chart["settings"] == {
        "ayanamsa": "lahiri", "houses": "whole_sign", "nodes": "mean",
    }
    assert smoke_chart["settings"] == SETTINGS
    assert smoke_chart["settings"] is not SETTINGS  # a copy, not the shared dict


def test_ketu_is_opposite_rahu(smoke_chart):
    planets = {p["name"]: p for p in smoke_chart["planets"]}
    rahu, ketu = planets["Rahu"], planets["Ketu"]
    assert ketu["longitude"] == pytest.approx((rahu["longitude"] + 180.0) % 360.0)
    assert (ketu["sign_index"] - rahu["sign_index"]) % 12 == 6


def test_nine_planets_fixed_order(smoke_chart):
    names = [p["name"] for p in smoke_chart["planets"]]
    assert names == [
        "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
        "Rahu", "Ketu",
    ]


def test_houses_tile_all_planets_exactly_once(smoke_chart):
    houses = smoke_chart["houses"]
    assert sorted(houses) == list(range(1, 13))
    occupants = [name for h in range(1, 13) for name in houses[h]]
    assert len(occupants) == 9
    assert set(occupants) == {p["name"] for p in smoke_chart["planets"]}
    # occupancy dict agrees with each planet's own house field
    for p in smoke_chart["planets"]:
        assert p["name"] in houses[p["house"]]
        assert 1 <= p["house"] <= 12


def test_lagna_is_house_one(smoke_chart):
    assert smoke_chart["lagna"]["house"] == 1


def test_whole_sign_house_counts_from_lagna():
    # Lagna in Aries (idx 0): a planet in Aries is house 1; Scorpio (idx 7) -> 8.
    assert whole_sign_house(0, 0) == 1
    assert whole_sign_house(7, 0) == 8
    # Lagna in Cancer (idx 3): Cancer -> 1, Gemini (idx 2) wraps to house 12.
    assert whole_sign_house(3, 3) == 1
    assert whole_sign_house(2, 3) == 12


# ---- Varga: the classical Parashari mapping is locked here (pure algorithm) --

def test_varga_d1_is_identity():
    for deg in (0.0, 15.0, 29.99, 200.0):
        assert varga_sign_index(deg, 1) == int((deg % 360) // 30)


def test_varga_d9_classical_starts():
    # movable (Aries 0) -> itself; fixed (Taurus 0) -> 9th (Capricorn);
    # dual (Gemini 0) -> 5th (Libra).
    assert varga_sign_index(0.0, 9) == 0          # Aries
    assert varga_sign_index(30.0, 9) == 9         # Taurus -> Capricorn
    assert varga_sign_index(60.0, 9) == 6         # Gemini -> Libra
    # last navamsa of Aries (26.67-30) -> Sagittarius (idx 8)
    assert varga_sign_index(29.9, 9) == 8


def test_varga_d10_classical_starts():
    # odd sign (Aries) -> itself; even sign (Taurus) -> 9th (Capricorn).
    assert varga_sign_index(0.0, 10) == 0         # Aries
    assert varga_sign_index(30.0, 10) == 9        # Taurus -> Capricorn
    # 2nd dashamsha of Aries (3-6 deg) -> Taurus (idx 1)
    assert varga_sign_index(4.0, 10) == 1


def test_varga_out_of_scope_divisor_raises():
    with pytest.raises(NotImplementedError):
        varga_sign_index(10.0, 7)


def test_varga_result_always_in_range(smoke_chart):
    for p in smoke_chart["planets"]:
        assert p["d9_sign"] in _SIGNS
        assert p["d10_sign"] in _SIGNS


# ---- Dignity (structure only; values are field B, reviewed manually) --------

def test_dignity_known_occupancy_cases():
    assert dignity_of("Mars", "Scorpio", 16.0) == "own_sign"
    assert dignity_of("Sun", "Aries", 10.0) == "exalted"
    assert dignity_of("Saturn", "Aries", 20.0) == "debilitated"
    assert dignity_of("Sun", "Leo", 10.0) == "moolatrikona"   # Leo 0-20
    assert dignity_of("Sun", "Leo", 25.0) == "own_sign"       # past MT range
    assert dignity_of("Rahu", "Capricorn", 5.0) == "not_applicable"


def test_dignity_relationship_cases():
    # Sun in Sagittarius (lord Jupiter) -> Jupiter is Sun's friend.
    assert dignity_of("Sun", "Sagittarius", 16.0) == "friend"
    # Jupiter in Gemini (lord Mercury) -> Mercury is Jupiter's enemy.
    assert dignity_of("Jupiter", "Gemini", 11.0) == "enemy"


# ---- Graha drishti (structure only; field B) --------------------------------

def test_aspects_generic_seventh():
    assert aspected_houses("Sun", 1) == [7]
    assert aspected_houses("Venus", 10) == [4]


def test_aspects_special_planets():
    # Mars in H1: 4th, 7th, 8th
    assert aspected_houses("Mars", 1) == [4, 7, 8]
    # Jupiter in H1: 5th, 7th, 9th
    assert aspected_houses("Jupiter", 1) == [5, 7, 9]
    # Saturn in H1: 3rd, 7th, 10th
    assert aspected_houses("Saturn", 1) == [3, 7, 10]


def test_rahu_ketu_cast_no_aspects():
    assert aspected_houses("Rahu", 5) == []
    assert aspected_houses("Ketu", 9) == []


# ---- Dasha: 4 levels, nested, target inside each ----------------------------

def test_dasha_four_levels_nested(smoke_chart):
    from datetime import datetime

    d = smoke_chart["dasha"]
    assert set(d) >= {"maha", "antar", "pratyantar", "sookshma"}
    levels = [d[k] for k in ("maha", "antar", "pratyantar", "sookshma")]
    target = datetime.fromisoformat(d["target"])
    prev_start = prev_end = None
    for lvl in levels:
        start = datetime.fromisoformat(lvl["start"])
        end = datetime.fromisoformat(lvl["end"])
        assert start < end
        assert start <= target < end               # target inside every level
        if prev_start is not None:                  # child nested within parent
            assert prev_start <= start
            assert end <= prev_end
        prev_start, prev_end = start, end


# ---------------------------------------------------------------------------
# Field A — JHora-oracle validation (skips: fixtures do not exist yet)
# ---------------------------------------------------------------------------

def _load_fixtures():
    if not FIXTURE_PATH.exists():
        pytest.skip(
            "BLOCKED ON FIXTURES: tests/fixtures/vedic_fixtures.json is absent. "
            "Per spec, functions are built and validation stops here; JHora "
            "values are never fabricated."
        )
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


# India charts (+05:30) run first; NYC/Sydney only after they are green.
_FIELD_A_ORDER = ["vedic_01", "vedic_02", "vedic_05", "vedic_03", "vedic_04"]


@pytest.mark.parametrize("chart_id", _FIELD_A_ORDER)
def test_field_a_against_jhora(chart_id):
    fixtures = _load_fixtures()
    if chart_id not in fixtures:
        pytest.skip(f"{chart_id} not in fixtures")
    _assert_field_a(chart_id, fixtures[chart_id])


_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
    "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

_ARCSEC_TOLERANCE_DEG = 60.0 / 3600.0   # target < 60"


def _assert_field_a(chart_id: str, fx: dict) -> None:
    """Assert one chart against its JHora expectations (see fixture schema doc
    in scripts/vedic_validate.py). Longitudes within <60"; sign/nakshatra/pada/
    house/D-9/D-10 exact; dasha lords + start/end to the minute."""
    result = compute_vedic_chart(
        datetime_local=fx["datetime_local"],
        gmt_offset=fx["gmt_offset"],
        lat=fx["lat"],
        lon=fx["lon"],
        target_date=fx["datetime_local"],   # dasha_at_birth is evaluated at birth
    )
    exp = fx["expected"]
    planets = {p["name"]: p for p in result["planets"]}

    for name, ep in exp["planets"].items():
        gp = planets[name]
        if "longitude" in ep:
            assert abs(gp["longitude"] - ep["longitude"]) <= _ARCSEC_TOLERANCE_DEG, (
                f"{chart_id} {name} longitude"
            )
        for field in ("sign", "nakshatra", "pada", "house", "d9_sign", "d10_sign"):
            if field in ep:
                assert gp[field] == ep[field], f"{chart_id} {name} {field}"

    if "lagna" in exp:
        for field, val in exp["lagna"].items():
            if field == "longitude":
                assert abs(result["lagna"]["longitude"] - val) <= _ARCSEC_TOLERANCE_DEG
            else:
                assert result["lagna"][field] == val, f"{chart_id} lagna {field}"

    if "dasha_at_birth" in exp:
        _assert_dasha_to_the_minute(chart_id, result["dasha"], exp["dasha_at_birth"])


def _assert_dasha_to_the_minute(chart_id: str, got: dict, exp: dict) -> None:
    from datetime import datetime

    for level in ("maha", "antar", "pratyantar", "sookshma"):
        assert got[level]["lord"] == exp[level]["lord"], f"{chart_id} {level} lord"
        for edge in ("start", "end"):
            g = datetime.fromisoformat(got[level][edge]).replace(second=0, microsecond=0)
            e = datetime.fromisoformat(exp[level][edge]).replace(second=0, microsecond=0)
            assert g == e, f"{chart_id} {level} {edge} (to the minute)"
