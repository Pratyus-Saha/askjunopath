"""Tests for the internal career prediction v1 engine (D029).

The career engine is **internal only**: it consumes already-computed chart data,
the internal node-aware significator engine (D028), and the internal Vimshottari
dasha engine (D027), and returns a structured evidence dict. It is NOT wired into
the public chart router, populates no public field, and bumps no schema/engine
version. It does NOT call any LLM.

There is **no JHora/founder golden fixture** for career output yet, so these
tests do not assert that the prediction is astrologically "correct" — they assert
the deterministic mechanics: output shape, that every cited evidence traces to a
real planet/house and to the validated sub-engines, that timing depends on the
`as_of` date, that the language is hedged (no guaranteed-outcome claims), that the
input chart is not mutated, and that the public contract is unchanged. Correctness
validation waits on a founder golden fixture / the JHora final significator table.
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

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

import pytest  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.engines.ephemeris_engine import compute_ephemeris, ephemeris_files_ok  # noqa: E402
from app.engines.prediction_career_engine import (  # noqa: E402
    CAREER_HOUSES,
    CHALLENGING_HOUSES,
    SUPPORTING_HOUSES,
    VERSION,
    compute_career_prediction,
)
from app.engines.significator_engine import compute_node_aware_significators  # noqa: E402
from app.routers.chart import _build_chart_payload  # noqa: E402
from app.schemas.models import BirthDataRequest  # noqa: E402

requires_swiss = pytest.mark.skipif(
    not ephemeris_files_ok(),
    reason="SWISS_EPHE_REQUIRED: career prediction needs .se1 files; current run "
    "may be Moshier fallback.",
)

KOL = ZoneInfo("Asia/Kolkata")
AS_OF_NOON = datetime(2026, 6, 17, 12, 0, tzinfo=KOL)
AS_OF_MIDNIGHT = datetime(2026, 6, 17, 0, 0, tzinfo=KOL)

USER1 = {
    "date": "1998-08-14",
    "time": "06:45:00",
    "place": "Kolkata, India",
    "latitude": 22.5725,
    "longitude": 88.363889,
    "iana_timezone": "Asia/Kolkata",
}

# Banned deterministic claims and the hedge words the summary must use instead.
BANNED_PHRASES = (
    "will get",
    "guaranteed",
    "will definitely",
    "definitely",
    "you will fail",
    "must leave",
    "certainly",
    "100%",
    "promise you",
)
HEDGE_MARKERS = ("may", "suggest", "indicat", "reflective", "not a guarantee")


def _user1_chart() -> dict:
    req = BirthDataRequest(
        birth_date=USER1["date"], birth_time=USER1["time"][:5], birth_city=USER1["place"]
    )
    eph = compute_ephemeris(
        datetime_local=f"{USER1['date']}T{USER1['time']}",
        timezone=USER1["iana_timezone"],
        lat=USER1["latitude"],
        lon=USER1["longitude"],
    )
    return _build_chart_payload(
        ephemeris=eph,
        place_label=USER1["place"],
        request_data=req,
        geo_lat=USER1["latitude"],
        geo_lon=USER1["longitude"],
        timezone_str=USER1["iana_timezone"],
    )


# --- Pure taxonomy (no ephemeris) ---------------------------------------------

def test_house_taxonomy_constants():
    assert set(CAREER_HOUSES) == {2, 6, 10, 11}
    assert set(SUPPORTING_HOUSES) == {1, 3, 5, 9}
    assert set(CHALLENGING_HOUSES) == {8, 12}
    # The three buckets are disjoint.
    assert not (set(CAREER_HOUSES) & set(SUPPORTING_HOUSES))
    assert not (set(CAREER_HOUSES) & set(CHALLENGING_HOUSES))


# --- Shape, determinism, guards ----------------------------------------------

@requires_swiss
def test_output_shape_and_version():
    pred = compute_career_prediction(_user1_chart(), as_of=AS_OF_NOON)
    assert pred["version"] == VERSION == "career-v1"
    for key in (
        "as_of",
        "summary",
        "promise",
        "career_house_activation",
        "current_dasha_stack",
        "dasha_support",
        "supporting_factors",
        "blocking_factors",
        "career_themes",
        "timing_interpretation",
        "confidence",
        "confidence_basis",
        "evidence",
        "caveat",
    ):
        assert key in pred, key
    # career_house_activation covers exactly the four career houses.
    assert set(pred["career_house_activation"]) == {"2", "6", "10", "11"}


@requires_swiss
def test_is_deterministic():
    a = compute_career_prediction(_user1_chart(), as_of=AS_OF_NOON)
    b = compute_career_prediction(_user1_chart(), as_of=AS_OF_NOON)
    assert a == b


@requires_swiss
def test_requires_timezone_aware_as_of():
    with pytest.raises(ValueError, match="timezone-aware"):
        compute_career_prediction(_user1_chart(), as_of=datetime(2026, 6, 17, 12, 0))


# --- Promise (KP cusp sub-lords of career houses) -----------------------------

@requires_swiss
def test_promise_cusp_sub_lords_user1():
    pred = compute_career_prediction(_user1_chart(), as_of=AS_OF_NOON)
    csl = pred["promise"]["career_house_cusp_sub_lords"]
    # 10th cusp sub-lord Saturn signifies house 6 -> service/employment signature.
    assert csl["10"]["sub_lord"] == "Saturn"
    assert csl["10"]["signifies"] == [6, 7, 9]
    assert csl["10"]["hits_career"] == [6]
    assert pred["promise"]["tenth_cusp_sub_lord"] == "Saturn"
    # 11th cusp sub-lord Sun signifies income (2) and gains (11).
    assert csl["11"]["sub_lord"] == "Sun"
    assert csl["11"]["hits_career"] == [2, 11]
    # 2nd cusp sub-lord Jupiter signifies 5, 8 -> no direct career-house hit.
    assert csl["2"]["sub_lord"] == "Jupiter"
    assert csl["2"]["hits_career"] == []


# --- Timing (current dasha stack) --------------------------------------------

@requires_swiss
def test_current_dasha_stack_user1_noon():
    pred = compute_career_prediction(_user1_chart(), as_of=AS_OF_NOON)
    stack = pred["current_dasha_stack"]
    assert stack["mahadasha"] == "Moon"
    assert stack["antardasha"] == "Ketu"
    assert stack["pratyantardasha"] == "Rahu"
    assert stack["antardasha_window"] == ["2026-03-19", "2026-10-22"]
    assert stack["pratyantardasha_window"] == ["2026-06-17", "2026-07-20"]


@requires_swiss
def test_dasha_support_classification_user1_noon():
    pred = compute_career_prediction(_user1_chart(), as_of=AS_OF_NOON)
    ds = pred["dasha_support"]
    assert ds["mahadasha"]["lord"] == "Moon"
    assert ds["mahadasha"]["career_hits"] == [10]
    assert ds["mahadasha"]["challenge_hits"] == [12]
    assert ds["antardasha"]["lord"] == "Ketu"
    assert ds["antardasha"]["career_hits"] == [6, 11]
    assert ds["antardasha"]["challenge_hits"] == [8]
    assert ds["pratyantardasha"]["lord"] == "Rahu"
    assert ds["pratyantardasha"]["career_hits"] == [2, 11]
    assert ds["pratyantardasha"]["challenge_hits"] == [12]


@requires_swiss
def test_career_house_activation_depends_on_as_of():
    # The pratyantardasha flips Mars->Rahu at 2026-06-17, so the activated career
    # houses differ between midnight and noon: this proves timing depends on
    # `as_of` and that the engine is deterministic per instant.
    noon = compute_career_prediction(_user1_chart(), as_of=AS_OF_NOON)
    midnight = compute_career_prediction(_user1_chart(), as_of=AS_OF_MIDNIGHT)

    def activated(pred):
        return {
            int(h)
            for h, info in pred["career_house_activation"].items()
            if info["activated"]
        }

    # Noon (Moon/Ketu/Rahu) activates all four career houses (Rahu adds 2).
    assert activated(noon) == {2, 6, 10, 11}
    # Midnight (Moon/Ketu/Mars) does not activate house 2.
    assert activated(midnight) == {6, 10, 11}
    assert noon["current_dasha_stack"]["pratyantardasha"] == "Rahu"
    assert midnight["current_dasha_stack"]["pratyantardasha"] == "Mars"


# --- Evidence integrity (every claim traces to a real entity + sub-engine) -----

@requires_swiss
def test_factors_and_evidence_cite_real_entities():
    chart = _user1_chart()
    pred = compute_career_prediction(chart, as_of=AS_OF_NOON)
    planet_names = {p["name"] for p in chart["planets"]}

    assert pred["evidence"], "evidence trail must be non-empty"
    for item in pred["evidence"]:
        assert item["source"] in planet_names, item
        for house in item["signifies"]:
            assert 1 <= house <= 12
        assert set(item["career_hits"]) <= set(CAREER_HOUSES)
        assert set(item["challenge_hits"]) <= set(CHALLENGING_HOUSES)
    # Blocking factors only ever cite challenge houses 8/12.
    for blk in pred["blocking_factors"]:
        assert set(blk["challenge_hits"]) <= {8, 12}
        assert blk["challenge_hits"]


@requires_swiss
def test_evidence_significations_match_node_aware_engine():
    # No fabrication: every cited signification list is exactly the node-aware
    # significator engine's output for that planet (D028).
    chart = _user1_chart()
    pred = compute_career_prediction(chart, as_of=AS_OF_NOON)
    sig = compute_node_aware_significators(chart["planets"], chart["houses"])
    for item in pred["evidence"]:
        assert item["signifies"] == sig.planet_to_houses[item["source"]], item


# --- Confidence (capped, transparent) ----------------------------------------

@requires_swiss
def test_confidence_is_transparent_and_capped():
    pred = compute_career_prediction(_user1_chart(), as_of=AS_OF_NOON)
    # The v1 medium cap is lifted (Block 4+5): confidence follows the unified
    # five-branch table. User 1 noon lands at "high" deterministically here:
    # promised + dasha support, and — now that the transit layer recomputes
    # significators/dashas for starved public-shaped charts (audit finding #1
    # follow-up) — a slow-planet contact window in the scanned span.
    assert pred["confidence"] in {"low", "medium", "high"}
    assert pred["confidence"] == "high"
    basis = pred["confidence_basis"]
    assert "career_signal" in basis and "challenge_signal" in basis
    assert "not validated" in basis["note"].lower()


@requires_swiss
def test_unified_contract_fields_present_on_live_chart():
    # The career engine now also carries the cross-domain unified contract fields
    # (Block 4+5), alongside its existing career-native keys.
    pred = compute_career_prediction(_user1_chart(), as_of=AS_OF_NOON)
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
    ts = pred["transit_summary"]
    assert set(ts) == {"windows_found", "has_slow_planet_contact", "next_contact", "framing"}
    assert ts["framing"], "framing must always be a non-empty string"
    assert ts["next_contact"]["planet"] in {"Jupiter", "Saturn", "Rahu", "Ketu"}
    assert ts["next_contact"]["days_away"] >= 90
    assert set(pred["cusp_sublords"]["primary_houses"]) == {"10"}


# --- Safe language (no guaranteed-outcome claims) -----------------------------

@requires_swiss
def test_summary_is_hedged_and_has_no_banned_claims():
    pred = compute_career_prediction(_user1_chart(), as_of=AS_OF_NOON)
    blob = " ".join([pred["summary"], pred["timing_interpretation"]]).lower()
    for banned in BANNED_PHRASES:
        assert banned not in blob, f"banned phrase leaked: {banned!r}"
    assert any(marker in blob for marker in HEDGE_MARKERS), pred["summary"]
    assert pred["caveat"].strip()
    assert "not a guarantee" in pred["caveat"].lower()


@requires_swiss
def test_career_themes_reflect_activated_houses():
    pred = compute_career_prediction(_user1_chart(), as_of=AS_OF_NOON)
    themes = " ".join(pred["career_themes"]).lower()
    # House 10 (profession) and 11 (gains) are activated at noon.
    assert "profession" in themes
    assert "gains" in themes


# --- Internal-only + no mutation + public API unchanged -----------------------

@requires_swiss
def test_engine_is_internal_only_and_mutates_nothing():
    chart = _user1_chart()
    before = copy.deepcopy(chart)
    compute_career_prediction(chart, as_of=AS_OF_NOON)
    assert chart == before
    # Reserved public fields stay reserved (D023); dasha stays null.
    assert chart["dashas"] is None
    for planet in chart["planets"]:
        assert planet["significator_of_houses"] == []
        assert planet["significator_levels"] == {}
    for house in chart["houses"]:
        assert house["significators"] is None


@requires_swiss
def test_public_api_and_versions_unchanged():
    chart = _user1_chart()
    assert chart["schema_version"] == "1.2"
    assert settings.chart_engine_version == "1.4.0"
    compute_career_prediction(chart, as_of=AS_OF_NOON)
    assert chart["schema_version"] == "1.2"
    assert settings.chart_engine_version == "1.4.0"
    assert chart["dashas"] is None
