"""Founder GOLDEN fixtures for the internal career prediction v1 engine (D029).

These are **founder golden fixtures, NOT JHora oracle fixtures.** The distinction
matters and is load-bearing:

* A *JHora oracle* fixture (e.g. ``tests/fixtures/jhora/*``) carries values exported
  from Jagannatha Hora and is the **judge** of astrological correctness — the engine
  conforms to it (AGENTS.md Rule 8).
* A *founder golden* fixture (this file's fixtures, ``tests/fixtures/career/*``) carries
  the engine's **own deterministic output** for three hand-picked career archetypes,
  reviewed by the founder for *reasonableness and safety*. It does NOT assert
  astrological ground truth. There is no JHora career oracle yet, and the significator
  foundation is AstroSage-compared only (D028). So these fixtures lock the documented
  v1 *behaviour* and the *safety contract* (no invented entities, no unsafe certainty,
  confidence capped at ``medium``, internal-only), and give the founder a concrete,
  reviewable artifact — they are not a correctness oracle.

Charts are rebuilt from the **golden (JHora-validated) longitudes/cusps** of the
referenced ``tests/fixtures/charts/*`` fixtures, so the build is Swiss-independent and
the promise-side / significator facts are exact. ``as_of`` for each fixture sits well
inside its MD/AD/PD periods, so the active dasha stack is identical under Swiss or
Moshier Sun timing (the documented sub-day date residual cannot flip the active lords);
the tests therefore never assert exact period-boundary dates, only that no date outside
the engine's own ``as_of`` + AD/PD windows is emitted.

See docs/prediction-career.md ("Founder golden fixtures") and DECISIONS.md D029.
"""

from __future__ import annotations

import copy
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

import pytest  # noqa: E402

from app.engines.ephemeris_engine import _sign_fields, normalize_longitude  # noqa: E402
from app.engines.house_engine import occupants as house_occupants  # noqa: E402
from app.engines.kp_engine import get_kp_sub_lord  # noqa: E402
from app.engines.nakshatra_engine import nakshatra_block, nakshatra_name  # noqa: E402
from app.engines.prediction_career_engine import (  # noqa: E402
    CAREER_HOUSES,
    CHALLENGING_HOUSES,
    VERSION,
    compute_career_prediction,
)

CAREER_DIR = ROOT / "tests" / "fixtures" / "career"
CHARTS_DIR = ROOT / "tests" / "fixtures" / "charts"

CLASSICAL_PLANETS = {
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
}
# Bodies that must NEVER appear in v1 output (KP/Vimshottari use 9 grahas only).
FORBIDDEN_BODIES = ["Pluto", "Neptune", "Uranus", "Chiron", "Lilith"]

GOLDEN_FIXTURES = [
    json.loads(p.read_text(encoding="utf-8"))
    for p in sorted(CAREER_DIR.glob("career_*.json"))
]
FIXTURE_IDS = [fx["fixture_id"] for fx in GOLDEN_FIXTURES]


# --------------------------------------------------------------------------- #
# Swiss-independent chart build from a referenced golden chart fixture.
# Positions/sub-lords/significators derive from the JHora-validated longitudes.
# Fields the career path never reads (retrograde/combust/speed) get neutral
# placeholders; the reserved public significator fields are kept empty so the
# internal-only / no-mutation assertions are meaningful.
# --------------------------------------------------------------------------- #
def _build_golden_chart(chart_fixture_id: str) -> dict:
    fx = json.loads((CHARTS_DIR / f"{chart_fixture_id}.json").read_text(encoding="utf-8"))
    inp, exp = fx["input"], fx["expected"]
    cusps = [normalize_longitude(exp["cusps"][str(h)]) for h in range(1, 13)]

    planets = []
    for name, raw_lon in exp["planets"].items():
        lon = normalize_longitude(raw_lon)
        sf = _sign_fields(lon)
        kp = get_kp_sub_lord(lon)
        planets.append({
            "name": name, "longitude": lon, **sf,
            "retrograde": False, "combust": False, "speed_deg_per_day": 0.0,
            "nakshatra": nakshatra_block(lon),
            "kp": {"star_lord": kp["star_lord"], "sub_lord": kp["sub_lord"]},
            "significator_of_houses": [],
            "significator_levels": {},
        })

    occ = house_occupants(planets, cusps)
    house_of = {pn: h for h, names in occ.items() for pn in names}
    for planet in planets:
        planet["house_occupied"] = house_of[planet["name"]]

    houses = []
    for h in range(1, 13):
        lon = cusps[h - 1]
        sf = _sign_fields(lon)
        kp = get_kp_sub_lord(lon)
        houses.append({
            "house": h, "cusp_longitude": lon,
            "cusp_sign": sf["sign"], "cusp_sign_lord": sf["sign_lord"],
            "cusp_nakshatra": nakshatra_name(lon),
            "kp": {"star_lord": kp["star_lord"], "sub_lord": kp["sub_lord"]},
            "occupants": occ[h],
            "significators": None,
        })

    return {
        "schema_version": "1.2",
        "birth": {
            "datetime_local": inp["datetime_local"],
            "timezone": inp["timezone"],
        },
        "dashas": None,
        "planets": planets,
        "houses": houses,
    }


def _prediction_for(fixture: dict) -> tuple[dict, dict]:
    chart = _build_golden_chart(fixture["chart_input_ref"])
    as_of = datetime.fromisoformat(fixture["as_of"])
    assert as_of.tzinfo is not None, "fixture as_of must be timezone-aware"
    pred = compute_career_prediction(chart, as_of=as_of)
    return chart, pred


def _all_strings(obj, out):
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _all_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _all_strings(v, out)


def _blob(pred: dict) -> str:
    out: list[str] = []
    _all_strings(pred, out)
    return " ".join(out)


def _mentioned_planets(pred: dict) -> set[str]:
    blob = _blob(pred)
    return {p for p in CLASSICAL_PLANETS if re.search(rf"\b{p}\b", blob)}


def _mentioned_house_ints(pred: dict) -> set[int]:
    """Every house integer the output refers to, structured + free text."""
    houses: set[int] = set()
    # Structured significations (authoritative).
    houses.update(pred["promise"]["tenth_cusp_sub_lord_signifies"])
    houses.update(pred["promise"]["promised_career_houses"])
    for info in pred["promise"]["career_house_cusp_sub_lords"].values():
        houses.update(info["signifies"])
    for level in pred["dasha_support"].values():
        houses.update(level["signifies"])
    for item in pred["evidence"]:
        houses.update(item["signifies"])
    houses.update(int(k) for k in pred["career_house_activation"])
    # Free-text house references (e.g. "career houses 2, 6, 11", "(house 12)").
    text = " ".join([
        pred["summary"], pred["timing_interpretation"], " ".join(pred["career_themes"]),
    ])
    for m in re.findall(r"house[s]?\s+([\d,\s]*\d)", text):
        houses.update(int(x) for x in re.findall(r"\d+", m))
    for m in re.findall(r"\(house\s+(\d+)\)", text):
        houses.add(int(m))
    return {int(h) for h in houses}


def _mentioned_dates(pred: dict) -> set[str]:
    return set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", _blob(pred)))


def _valid_dates(pred: dict) -> set[str]:
    stack = pred["current_dasha_stack"]
    valid = {
        pred["as_of"][:10],
        stack["antardasha_window"][0], stack["antardasha_window"][1],
        stack["pratyantardasha_window"][0], stack["pratyantardasha_window"][1],
    }
    # Block 4+5: transit windows and the forward next-contact are a *legitimate*
    # source of day-level dates in the unified contract (they come from the
    # transit engine, not free text). They are valid, not "invented".
    for window in pred.get("transit_windows", []):
        valid.add(window["start_date"])
        valid.add(window["end_date"])
        for trigger in window["triggers"]:
            valid.add(trigger["contact_date"])
    next_contact = pred.get("transit_summary", {}).get("next_contact") or {}
    if next_contact.get("estimated_date"):
        valid.add(next_contact["estimated_date"])
    return valid


# --------------------------------------------------------------------------- #
# Sanity: the fixtures span three distinct, documented profiles.
# --------------------------------------------------------------------------- #
def test_three_distinct_profiles_present():
    profiles = {fx["profile"] for fx in GOLDEN_FIXTURES}
    assert profiles == {"supportive", "mixed_change", "weak_no_signal"}
    assert len(GOLDEN_FIXTURES) == 3
    for fx in GOLDEN_FIXTURES:
        assert fx["kind"] == "founder_golden", fx["fixture_id"]


# --------------------------------------------------------------------------- #
# Expected deterministic facts (the golden values the founder reviews).
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("fixture", GOLDEN_FIXTURES, ids=FIXTURE_IDS)
def test_promise_and_timing_match_expected(fixture):
    _chart, pred = _prediction_for(fixture)
    exp = fixture["expected"]

    assert pred["version"] == exp["version"] == VERSION

    stack = pred["current_dasha_stack"]
    assert stack["mahadasha"] == exp["current_dasha_stack"]["mahadasha"]
    assert stack["antardasha"] == exp["current_dasha_stack"]["antardasha"]
    assert stack["pratyantardasha"] == exp["current_dasha_stack"]["pratyantardasha"]

    assert pred["promise"]["tenth_cusp_sub_lord"] == exp["tenth_cusp_sub_lord"]
    assert (
        pred["promise"]["tenth_cusp_sub_lord_signifies"]
        == exp["tenth_cusp_sub_lord_signifies"]
    )

    actual_csl = {
        h: pred["promise"]["career_house_cusp_sub_lords"][h]["sub_lord"]
        for h in ("2", "6", "10", "11")
    }
    assert actual_csl == exp["career_house_cusp_sub_lords"]

    assert pred["promise"]["promised_career_houses"] == exp["promise_career_houses"]

    activated = sorted(
        int(h) for h, info in pred["career_house_activation"].items()
        if info["activated"]
    )
    assert activated == exp["activated_career_houses"]

    assert (
        sorted(pred["confidence_basis"]["challenge_houses_hit"])
        == exp["challenge_houses"]
    )


# --------------------------------------------------------------------------- #
# Safety contract — the heart of these fixtures.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("fixture", GOLDEN_FIXTURES, ids=FIXTURE_IDS)
def test_no_invented_planets(fixture):
    chart, pred = _prediction_for(fixture)
    chart_planets = {p["name"] for p in chart["planets"]}
    for planet in _mentioned_planets(pred):
        assert planet in chart_planets, f"invented planet: {planet}"
    blob = _blob(pred)
    for body in FORBIDDEN_BODIES:
        assert not re.search(rf"\b{body}\b", blob), f"forbidden body emitted: {body}"
    # Every cited evidence source is a real chart planet.
    for item in pred["evidence"]:
        assert item["source"] in chart_planets, item


@pytest.mark.parametrize("fixture", GOLDEN_FIXTURES, ids=FIXTURE_IDS)
def test_no_invented_houses(fixture):
    _chart, pred = _prediction_for(fixture)
    for house in _mentioned_house_ints(pred):
        assert 1 <= house <= 12, f"invented house: {house}"


@pytest.mark.parametrize("fixture", GOLDEN_FIXTURES, ids=FIXTURE_IDS)
def test_no_invented_dates(fixture):
    _chart, pred = _prediction_for(fixture)
    valid = _valid_dates(pred)
    for date_text in _mentioned_dates(pred):
        assert date_text in valid, (
            f"invented date {date_text} not in as_of/AD/PD windows {sorted(valid)}"
        )


@pytest.mark.parametrize("fixture", GOLDEN_FIXTURES, ids=FIXTURE_IDS)
def test_no_unsafe_certainty_language(fixture):
    _chart, pred = _prediction_for(fixture)
    safe = fixture["safe_language"]
    prose = " ".join([pred["summary"], pred["timing_interpretation"]]).lower()
    for banned in safe["banned_phrases"]:
        assert banned not in prose, f"banned phrase leaked: {banned!r}"
    assert any(marker in prose for marker in safe["required_hedge_markers_any"]), (
        pred["summary"]
    )
    assert safe["caveat_must_contain"] in pred["caveat"].lower()


@pytest.mark.parametrize("fixture", GOLDEN_FIXTURES, ids=FIXTURE_IDS)
def test_confidence_capped_at_medium(fixture):
    # NOTE: the v1 "medium cap" is LIFTED under the unified contract (Block 4+5):
    # career confidence now follows the five-branch table and may reach "high".
    # This test is retained (no deletion) and now asserts the table-derived tier
    # matches the fixture's reviewed expectation.
    _chart, pred = _prediction_for(fixture)
    exp = fixture["expected"]
    assert pred["confidence"] in {"low", "medium", "high"}
    assert pred["confidence"] in exp["confidence_tier_range"]
    # The raw, pre-table career-signal heuristic tier is still exposed transparently.
    assert pred["confidence_basis"]["raw_tier"] == exp["raw_tier"]
    assert pred["confidence_basis"]["career_signal"] == exp["career_signal"]
    assert pred["confidence_basis"]["challenge_signal"] == exp["challenge_signal"]
    assert "not validated" in pred["confidence_basis"]["note"].lower()


@pytest.mark.parametrize("fixture", GOLDEN_FIXTURES, ids=FIXTURE_IDS)
def test_outputs_remain_internal_only(fixture):
    chart = _build_golden_chart(fixture["chart_input_ref"])
    before = copy.deepcopy(chart)
    compute_career_prediction(chart, as_of=datetime.fromisoformat(fixture["as_of"]))
    # No mutation of the input chart.
    assert chart == before
    # Reserved public fields stay reserved (D023); dasha stays null.
    assert chart["dashas"] is None
    for planet in chart["planets"]:
        assert planet["significator_of_houses"] == []
        assert planet["significator_levels"] == {}
    for house in chart["houses"]:
        assert house["significators"] is None


@pytest.mark.parametrize("fixture", GOLDEN_FIXTURES, ids=FIXTURE_IDS)
def test_theme_constraints(fixture):
    _chart, pred = _prediction_for(fixture)
    exp = fixture["expected"]
    themes = " ".join(pred["career_themes"]).lower()
    for required in exp["required_theme_substrings"]:
        assert required in themes, f"missing required theme substring: {required!r}"
    for forbidden in exp["forbidden_theme_substrings"]:
        assert forbidden not in themes, f"forbidden theme substring present: {forbidden!r}"
    # Every theme references a known career/challenge house label.
    label_blob = " ".join(
        {**CAREER_HOUSES, **CHALLENGING_HOUSES}.values()
    ).lower()
    for theme in pred["career_themes"]:
        label = theme.split(" (house")[0].lower()
        assert label in label_blob, f"unexpected theme label: {theme}"


# --------------------------------------------------------------------------- #
# Profile-specific behaviour (what each archetype must demonstrate).
# --------------------------------------------------------------------------- #
def _fixture(profile: str) -> dict:
    return next(fx for fx in GOLDEN_FIXTURES if fx["profile"] == profile)


def test_supportive_shows_the_medium_cap_in_action():
    fx = _fixture("supportive")
    _chart, pred = _prediction_for(fx)
    # The raw career-signal heuristic is the maximum tier ("high"), yet the unified
    # confidence lands at "medium" here — not because of a cap, but because no
    # slow-planet transit window forms at this fixture's as_of (high needs one).
    assert pred["confidence_basis"]["raw_tier"] == "high"
    assert pred["confidence"] == "medium"
    assert pred["transit_summary"]["has_slow_planet_contact"] is False
    assert pred["confidence_basis"]["career_signal"] >= 3
    assert pred["confidence_basis"]["challenge_signal"] <= 1


def test_mixed_surfaces_change_and_challenge():
    fx = _fixture("mixed_change")
    _chart, pred = _prediction_for(fx)
    # Both challenge houses active and blocking factors present.
    assert sorted(pred["confidence_basis"]["challenge_houses_hit"]) == [8, 12]
    assert pred["blocking_factors"], "mixed chart must expose blocking factors"
    # Change/instability language must be surfaced, not suppressed.
    prose = pred["summary"].lower()
    assert any(word in prose for word in ("instability", "change", "loss", "remote", "expense"))


def test_weak_stays_low_and_non_committal():
    fx = _fixture("weak_no_signal")
    _chart, pred = _prediction_for(fx)
    # Promise is unmet (the 10th/primary cusp sub-lord touches no career house),
    # so the unified table holds this at "low" regardless of any transit windows.
    assert pred["promise_met"] is False
    assert pred["confidence"] == "low"
    activated = [h for h, info in pred["career_house_activation"].items() if info["activated"]]
    assert len(activated) <= fx["expected"]["max_activated_career_houses"]


# --------------------------------------------------------------------------- #
# Unified contract (Block 4+5) — career now carries the cross-domain fields and
# may reach "high"; confidence follows the five-branch table.
# --------------------------------------------------------------------------- #
def _expected_unified_confidence(pred: dict) -> str:
    promise = pred["promise_met"]
    dt = pred["dasha_timing"]
    dasha_supports = (dt["md_supports"] + dt["ad_supports"] + dt["pd_supports"]) >= 2
    slow = pred["transit_summary"]["has_slow_planet_contact"]
    has_windows = bool(pred["transit_windows"])
    if not promise:
        return "low"
    if dasha_supports:
        return "high" if slow else "medium"
    return "medium" if has_windows else "low"


def test_career_reaches_high_under_unified_table():
    # The medium cap is lifted: the mixed/change chart converges promise + full
    # dasha support + a slow-planet transit window, so confidence is "high".
    # "high" here denotes factor convergence (signal strength), not a good outcome
    # — the challenge houses remain surfaced as blocking factors / disruption.
    fx = _fixture("mixed_change")
    _chart, pred = _prediction_for(fx)
    assert pred["confidence"] == "high"
    assert pred["promise_met"] is True
    assert pred["transit_summary"]["has_slow_planet_contact"] is True
    assert "career-disruption caution" in pred["event_types"]
    assert pred["blocking_factors"], "high confidence must not suppress disruption"


@pytest.mark.parametrize("fixture", GOLDEN_FIXTURES, ids=FIXTURE_IDS)
def test_unified_confidence_follows_five_branch_table(fixture):
    _chart, pred = _prediction_for(fixture)
    assert pred["confidence"] == pred["confidence"].lower()
    assert pred["confidence"] == _expected_unified_confidence(pred)


@pytest.mark.parametrize("fixture", GOLDEN_FIXTURES, ids=FIXTURE_IDS)
def test_unified_contract_fields_present(fixture):
    _chart, pred = _prediction_for(fixture)
    for key in (
        "domain", "promise_met", "signal_strength", "caution_flag",
        "dasha_timing", "transit_windows", "transit_summary", "event_types",
        "cusp_sublords",
    ):
        assert key in pred, key
    assert pred["domain"] == "career"
    assert isinstance(pred["promise_met"], bool)
    assert isinstance(pred["caution_flag"], bool)
    assert isinstance(pred["signal_strength"], int)
    assert 0 <= pred["signal_strength"] <= 100
    assert isinstance(pred["transit_windows"], list)
    assert set(pred["dasha_timing"]) == {
        "md_lord", "ad_lord", "pd_lord", "md_supports", "ad_supports", "pd_supports",
    }
    ts = pred["transit_summary"]
    assert set(ts) == {"windows_found", "has_slow_planet_contact", "next_contact", "framing"}
    assert ts["framing"] and ts["next_contact"]
    assert ts["next_contact"]["planet"] in {"Jupiter", "Saturn", "Rahu", "Ketu"}
    assert pred["event_types"]
    for event in pred["event_types"]:
        assert event in {
            "career-advancement window", "opportunity window",
            "career-disruption caution", "steady-progress window",
        }
    assert set(pred["cusp_sublords"]) == {"primary_houses", "sublord_significations"}
    assert set(pred["cusp_sublords"]["primary_houses"]) == {"10"}
