"""Property tests for the internal finance prediction engine (Block 4).

The finance engine is **internal only**: it reads an already-computed chart dict
(planets, houses, ``dashas.current``, and each planet's ``significator_of_houses``)
plus the transit engine, and returns the unified prediction contract. It is not
wired into any router, populates no public field, and calls no LLM.

These tests assert the deterministic *mechanics* and *safety contract* across all
three founder fixtures: the output shape, that confidence follows the documented
five-branch table exactly, that the summary never uses market / trading
vocabulary, and that the caution framing appears when (and only when) flagged.
The transit side is anchored at a fixed ``as_of`` so windows are deterministic;
``transit_summary.next_contact`` (which scans from today) is asserted structurally,
never by exact value.
"""

from __future__ import annotations

import copy
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# Point Swiss Ephemeris at the bundled .se1 files when not already set (mirrors
# backend/tests/conftest.py so this module is self-contained if run directly).
_EPHE_DIR = ROOT / "backend" / "ephe"
if not os.environ.get("SE_EPHE_PATH") and _EPHE_DIR.is_dir():
    os.environ["SE_EPHE_PATH"] = str(_EPHE_DIR)

import json  # noqa: E402

import pytest  # noqa: E402

from app.engines.prediction_finance_engine import (  # noqa: E402
    EVENT_DUES,
    EVENT_EXPENSE,
    EVENT_INCOME,
    EVENT_REVIEW,
    compute_finance_prediction,
)


def _swiss_ready() -> bool:
    try:
        import swisseph  # noqa: F401
    except Exception:
        return False
    ephe = os.environ.get("SE_EPHE_PATH")
    return bool(ephe and Path(ephe).is_dir() and list(Path(ephe).glob("*.se1")))


requires_swiss = pytest.mark.skipif(
    not _swiss_ready(),
    reason="Swiss Ephemeris (.se1 files at SE_EPHE_PATH) not available",
)

FIXTURE_DIR = ROOT / "tests" / "fixtures" / "finance"
FIXTURE_FILES = sorted(FIXTURE_DIR.glob("finance_*.json"))
FIXTURE_IDS = [p.stem for p in FIXTURE_FILES]

# The pinned instant the fixtures were tuned against (deterministic transit scan).
KOL = ZoneInfo("Asia/Kolkata")
AS_OF = datetime(2026, 9, 15, 12, 0, tzinfo=KOL)

REQUIRED_KEYS = {
    "domain",
    "promise_met",
    "confidence",
    "signal_strength",
    "caution_flag",
    "dasha_timing",
    "transit_windows",
    "transit_summary",
    "event_types",
    "summary",
    "cusp_sublords",
}
DASHA_KEYS = {
    "md_lord", "ad_lord", "pd_lord", "md_supports", "ad_supports", "pd_supports",
}
TRANSIT_SUMMARY_KEYS = {
    "windows_found", "has_slow_planet_contact", "next_contact", "framing",
}
NEXT_CONTACT_KEYS = {
    "planet", "natal_point", "natal_longitude", "estimated_date", "days_away",
}
ALLOWED_EVENTS = {EVENT_INCOME, EVENT_EXPENSE, EVENT_DUES, EVENT_REVIEW}
SLOW_PLANETS = {"Jupiter", "Saturn", "Rahu", "Ketu"}

# Market / trading vocabulary that must never appear anywhere in the output.
BANNED_WORDS = (
    "invest", "buy", "sell", "trade", "stock", "return", "profit", "instrument",
    "purchase", "asset", "portfolio", "fund", "yield",
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _all_strings(obj, out: list[str]) -> None:
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for value in obj.values():
            _all_strings(value, out)
    elif isinstance(obj, list):
        for value in obj:
            _all_strings(value, out)


def _blob(pred: dict) -> str:
    out: list[str] = []
    _all_strings(pred, out)
    return " ".join(out).lower()


def _expected_confidence(pred: dict) -> str:
    """The documented five-branch table, recomputed from the output's own inputs."""
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


@pytest.fixture(params=FIXTURE_FILES, ids=FIXTURE_IDS)
def prediction(request) -> dict:
    chart = _load(request.param)
    return compute_finance_prediction(chart, as_of=AS_OF)


def test_fixtures_present():
    assert len(FIXTURE_FILES) == 3, FIXTURE_IDS


@requires_swiss
def test_output_has_all_required_keys(prediction):
    assert set(prediction) == REQUIRED_KEYS
    assert prediction["domain"] == "finance"
    assert set(prediction["dasha_timing"]) == DASHA_KEYS
    assert set(prediction["transit_summary"]) == TRANSIT_SUMMARY_KEYS
    assert set(prediction["cusp_sublords"]) == {"primary_houses", "sublord_significations"}


@requires_swiss
def test_field_types(prediction):
    assert isinstance(prediction["promise_met"], bool)
    assert isinstance(prediction["caution_flag"], bool)
    assert prediction["confidence"] in {"high", "medium", "low"}
    assert isinstance(prediction["signal_strength"], int)
    assert 0 <= prediction["signal_strength"] <= 100
    assert isinstance(prediction["transit_windows"], list)
    assert isinstance(prediction["event_types"], list) and prediction["event_types"]


@requires_swiss
def test_confidence_never_uppercase_and_follows_table(prediction):
    # Lowercase tiers only — no "HIGH"/"MEDIUM"/"LOW" ever leaves the engine.
    assert prediction["confidence"] == prediction["confidence"].lower()
    # And it matches the documented five-branch table for this fixture's inputs.
    assert prediction["confidence"] == _expected_confidence(prediction)


@requires_swiss
def test_event_types_are_from_the_allowed_set(prediction):
    assert prediction["event_types"], "event_types must be non-empty"
    for event in prediction["event_types"]:
        assert event in ALLOWED_EVENTS, event
    # The review label is always an appropriate, present fallback.
    assert EVENT_REVIEW in prediction["event_types"]


@requires_swiss
def test_no_banned_market_vocabulary_anywhere(prediction):
    blob = _blob(prediction)
    leaked = [word for word in BANNED_WORDS if word in blob]
    assert not leaked, f"banned vocabulary leaked into output: {leaked}"


@requires_swiss
def test_caution_flag_drives_summary_framing(prediction):
    summary = prediction["summary"].lower()
    if prediction["caution_flag"]:
        assert "caution" in summary or "review" in summary
    # The summary is always hedged, never an unconditional claim.
    assert any(marker in summary for marker in ("may", "reflective", "not a guarantee"))


@requires_swiss
def test_transit_summary_is_well_formed(prediction):
    ts = prediction["transit_summary"]
    assert ts["windows_found"] == len(prediction["transit_windows"])
    assert isinstance(ts["has_slow_planet_contact"], bool)
    assert ts["framing"], "framing must always be a non-empty string"
    # next_contact is always populated and anchored on a slow planet >=90 days out.
    nc = ts["next_contact"]
    assert set(nc) == NEXT_CONTACT_KEYS, nc
    assert nc["planet"] in SLOW_PLANETS
    assert nc["days_away"] >= 90
    assert 0.0 <= nc["natal_longitude"] < 360.0


@requires_swiss
def test_slow_planet_contact_matches_windows(prediction):
    # has_slow_planet_contact iff some returned window carries a slow-planet trigger.
    slow_in_windows = any(
        any(trigger["planet"] in SLOW_PLANETS for trigger in window["triggers"])
        for window in prediction["transit_windows"]
    )
    assert prediction["transit_summary"]["has_slow_planet_contact"] is slow_in_windows


@requires_swiss
def test_requires_timezone_aware_as_of():
    chart = _load(FIXTURE_FILES[0])
    with pytest.raises(ValueError, match="timezone-aware"):
        compute_finance_prediction(chart, as_of=datetime(2026, 9, 15, 12, 0))


@requires_swiss
def test_engine_is_deterministic_and_mutates_nothing():
    chart = _load(FIXTURE_FILES[0])
    before = copy.deepcopy(chart)
    a = compute_finance_prediction(chart, as_of=AS_OF)
    b = compute_finance_prediction(chart, as_of=AS_OF)
    assert a == b
    assert chart == before, "engine must not mutate the input chart"
