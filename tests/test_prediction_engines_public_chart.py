"""Finance/relationship engines over a REAL public /chart/generate payload.

Audit finding #1: the public chart keeps ``planets[].significator_of_houses``
reserved-empty (D023) and ``chart["dashas"]`` null, but the finance and
relationship engines used to read both directly — so every real user got a
degenerate prediction (``promise_met=False``, null dasha lords, ``confidence``
pinned to "low") regardless of the chart.

These tests feed each engine a chart built through the exact public trusted
path (``compute_ephemeris`` + ``_build_chart_payload``, the same shape
``/chart/generate`` returns) and assert the output is non-degenerate: dasha
lords are real planets and the promise is evaluated against recomputed
node-aware significators. They also assert equivalence: the engine output over
the starved public payload must match the output over the same chart with
``significator_of_houses`` and ``dashas.current`` explicitly populated (the
shape the flat engine fixtures use), so both input shapes stay in lockstep.
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

_EPHE_DIR = ROOT / "backend" / "ephe"
if not os.environ.get("SE_EPHE_PATH") and _EPHE_DIR.is_dir():
    os.environ["SE_EPHE_PATH"] = str(_EPHE_DIR)

import pytest  # noqa: E402

from app.engines.dasha_engine import compute_dasha_from_chart  # noqa: E402
from app.engines.ephemeris_engine import compute_ephemeris  # noqa: E402
from app.engines.prediction_finance_engine import compute_finance_prediction  # noqa: E402
from app.engines.prediction_relationship_engine import (  # noqa: E402
    compute_relationship_prediction,
)
from app.engines.significator_engine import compute_node_aware_significators  # noqa: E402
from app.routers import chart as chart_router  # noqa: E402
from app.schemas.models import BirthDataRequest  # noqa: E402

KOL = ZoneInfo("Asia/Kolkata")
AS_OF = datetime(2026, 6, 17, 12, 0, tzinfo=KOL)

CLASSICAL_PLANETS = {
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
}

USER1 = {
    "date": "1998-08-14",
    "time": "06:45:00",
    "place": "Kolkata, India",
    "latitude": 22.5725,
    "longitude": 88.363889,
    "iana_timezone": "Asia/Kolkata",
}

ENGINES = (
    ("finance", compute_finance_prediction),
    ("relationship", compute_relationship_prediction),
)


def _public_chart() -> dict:
    """A chart in the exact shape /chart/generate returns (trusted build path)."""
    req = BirthDataRequest(
        birth_date=USER1["date"], birth_time=USER1["time"][:5], birth_city=USER1["place"]
    )
    eph = compute_ephemeris(
        datetime_local=f"{USER1['date']}T{USER1['time']}",
        timezone=USER1["iana_timezone"],
        lat=USER1["latitude"],
        lon=USER1["longitude"],
    )
    return chart_router._build_chart_payload(
        ephemeris=eph,
        place_label=USER1["place"],
        request_data=req,
        geo_lat=USER1["latitude"],
        geo_lon=USER1["longitude"],
        timezone_str=USER1["iana_timezone"],
    )


def _enriched(chart: dict) -> dict:
    """The same chart with significators + dashas.current explicitly populated,
    matching the fully-populated flat shape the engine unit fixtures use."""
    enriched = copy.deepcopy(chart)
    pth = compute_node_aware_significators(
        chart["planets"], chart["houses"]
    ).planet_to_houses
    for planet in enriched["planets"]:
        planet["significator_of_houses"] = list(pth[planet["name"]])
    md, ad, pd = compute_dasha_from_chart(chart).current_stack(AS_OF)
    enriched["dashas"] = {
        "current": {"md_lord": md.lord, "ad_lord": ad.lord, "pd_lord": pd.lord}
    }
    return enriched


@pytest.fixture(scope="module")
def public_chart() -> dict:
    return _public_chart()


def test_public_chart_is_starved(public_chart):
    """Precondition: the public payload really is what the audit describes."""
    assert public_chart["dashas"] is None
    for planet in public_chart["planets"]:
        assert planet["significator_of_houses"] == []


@pytest.mark.parametrize("domain,engine", ENGINES, ids=[d for d, _ in ENGINES])
def test_engine_recomputes_dasha_lords_from_public_chart(public_chart, domain, engine):
    prediction = engine(public_chart, as_of=AS_OF)
    timing = prediction["dasha_timing"]
    for key in ("md_lord", "ad_lord", "pd_lord"):
        assert timing[key] in CLASSICAL_PLANETS, f"{key} degenerate: {timing[key]!r}"


@pytest.mark.parametrize("domain,engine", ENGINES, ids=[d for d, _ in ENGINES])
def test_engine_evaluates_promise_from_public_chart(public_chart, domain, engine):
    prediction = engine(public_chart, as_of=AS_OF)
    significations = prediction["cusp_sublords"]["sublord_significations"]
    assert significations, "no cusp sub-lord significations were recorded"
    for lord, houses in significations.items():
        assert lord in CLASSICAL_PLANETS
        assert houses, f"{lord} has empty significations — promise never evaluated"
    assert isinstance(prediction["promise_met"], bool)


@pytest.mark.parametrize("domain,engine", ENGINES, ids=[d for d, _ in ENGINES])
def test_public_chart_output_matches_populated_chart_output(
    public_chart, domain, engine
):
    """The starved public shape and the fully-populated flat shape must agree on
    every promise/dasha-derived field.

    Transit-derived fields (transit_windows, transit_summary, and the
    confidence/signal_strength/event_types computed from them) are excluded:
    the transit engine reads ``significator_of_houses`` / ``dashas`` off the
    chart as given, for the starved and populated shapes alike — the same
    behaviour the career engine has today.
    """
    from_public = engine(public_chart, as_of=AS_OF)
    from_populated = engine(_enriched(public_chart), as_of=AS_OF)
    for key in ("domain", "promise_met", "caution_flag", "dasha_timing", "cusp_sublords"):
        assert from_public[key] == from_populated[key], key


@pytest.mark.parametrize("domain,engine", ENGINES, ids=[d for d, _ in ENGINES])
def test_engine_does_not_mutate_public_chart(public_chart, domain, engine):
    before = copy.deepcopy(public_chart)
    engine(public_chart, as_of=AS_OF)
    assert public_chart == before
