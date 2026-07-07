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
from datetime import datetime, timedelta, timezone
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
from app.engines.transit_engine import compute_transit_windows  # noqa: E402
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
    """The same chart with significators + dashas explicitly populated.

    Carries BOTH consumer shapes: the flat ``md_lord``/``ad_lord``/``pd_lord``
    keys the prediction engines read, and the ``mahadasha``/``antardasha``/
    ``pratyantardasha`` period blocks (+ ``upcoming_pd``) the transit engine
    reads. The transit-facing stack is derived exactly the way the transit
    engine's starved-payload recompute derives it (midnight UTC of the scan
    start, 90-day upcoming-PD horizon), so a starved chart and this enriched
    chart must produce identical windows.
    """
    enriched = copy.deepcopy(chart)
    pth = compute_node_aware_significators(
        chart["planets"], chart["houses"]
    ).planet_to_houses
    for planet in enriched["planets"]:
        planet["significator_of_houses"] = list(pth[planet["name"]])

    timeline = compute_dasha_from_chart(chart)
    md, ad, pd = timeline.current_stack(AS_OF)
    scan_moment = datetime(
        AS_OF.year, AS_OF.month, AS_OF.day, tzinfo=timezone.utc
    )
    tmd, tad, tpd = timeline.current_stack(scan_moment)
    horizon = AS_OF.date() + timedelta(days=90)
    enriched["dashas"] = {
        "system": "VIMSHOTTARI",
        "current": {
            "md_lord": md.lord,
            "ad_lord": ad.lord,
            "pd_lord": pd.lord,
            "mahadasha": {
                "lord": tmd.lord, "start": tmd.start.date(), "end": tmd.end.date(),
            },
            "antardasha": {
                "lord": tad.lord, "start": tad.start.date(), "end": tad.end.date(),
            },
            "pratyantardasha": {
                "lord": tpd.lord, "start": tpd.start.date(), "end": tpd.end.date(),
            },
        },
        "upcoming_pd": [
            {"pd": p.lord, "start": p.start.date(), "end": p.end.date()}
            for p in timeline.pratyantardashas
            if tpd.end <= p.start and p.start.date() <= horizon
        ],
    }
    return enriched


def _neutered(chart: dict) -> dict:
    """A variant with NO transit-usable dasha/significator signal, simulating the
    pre-fix starved behaviour: every planet signifies only house 4 (in no
    domain's house groups, so contact rule 2 matches nothing) and the dasha
    block is present-but-lordless (rule 3 and the PD bonus find nothing, and the
    truthy ``current`` suppresses the engines' starvation recompute)."""
    neutered = copy.deepcopy(chart)
    for planet in neutered["planets"]:
        planet["significator_of_houses"] = [4]
    neutered["dashas"] = {
        "system": "VIMSHOTTARI",
        "current": {"mahadasha": {}, "antardasha": {}, "pratyantardasha": {}},
        "upcoming_pd": [],
    }
    return neutered


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
    """The starved public shape and the fully-populated shape must agree on
    EVERY field, transit-derived ones included (the transit engine now
    recomputes starved inputs internally, Task 7).

    Only ``transit_summary.next_contact`` is excluded: that scan anchors at
    *today*, so the starved chart's recomputed dasha stack (current at today)
    can legitimately differ from the AS_OF stack stored in the enriched chart.
    """
    from_public = engine(public_chart, as_of=AS_OF)
    from_populated = engine(_enriched(public_chart), as_of=AS_OF)
    for prediction in (from_public, from_populated):
        prediction["transit_summary"] = {
            key: value
            for key, value in prediction["transit_summary"].items()
            if key != "next_contact"
        }
    assert from_public == from_populated


# ---------------------------------------------------------------------------
# Task 7: the TRANSIT layer itself must fire rules 2/3 + PD bonus on public
# payloads. The neutered variant simulates the pre-fix starved behaviour.
# ---------------------------------------------------------------------------

TRANSIT_DOMAINS = ("career", "finance", "relationship")


@pytest.mark.parametrize("domain", TRANSIT_DOMAINS)
def test_transit_windows_score_higher_with_recomputed_contact_points(
    public_chart, domain
):
    """Window scores must differ meaningfully: the public chart (recomputed
    rules 2/3 + PD bonus) vs a chart with no dasha/significator signal."""
    windows_public = compute_transit_windows(
        public_chart, domain, start_date=AS_OF.date(), scan_days=90
    )
    windows_neutered = compute_transit_windows(
        _neutered(public_chart), domain, start_date=AS_OF.date(), scan_days=90
    )
    assert windows_public, "public chart produced no transit windows"
    best_public = max(w["window_score"] for w in windows_public)
    best_neutered = max(
        (w["window_score"] for w in windows_neutered), default=0.0
    )
    # "Meaningfully": not a rounding artefact — the extra contact points and
    # the PD bonus must move the score, not tie it.
    assert best_public > best_neutered, (best_public, best_neutered)


@pytest.mark.parametrize("domain", TRANSIT_DOMAINS)
def test_transit_contact_rules_2_and_3_fire_on_public_chart(public_chart, domain):
    """Public-chart windows must carry natal_* contact points beyond the rule-4
    primary-cusp sub-lords — proof that recomputed significators (rule 2) and
    dasha lords (rule 3) actually contribute contact points."""
    houses_by_num = {h["house"]: h for h in public_chart["houses"]}
    primary = {"career": [10], "finance": [2, 11], "relationship": [7]}[domain]
    rule4_points = {
        f"natal_{houses_by_num[n]['kp']['sub_lord'].lower()}" for n in primary
    }

    windows = compute_transit_windows(
        public_chart, domain, start_date=AS_OF.date(), scan_days=90
    )
    natal_points = {
        trigger["natal_point"]
        for window in windows
        for trigger in window["triggers"]
        if trigger["natal_point"].startswith("natal_")
    }
    assert natal_points - rule4_points, (
        f"no rule-2/3 contact points in {domain} windows: {sorted(natal_points)}"
    )

    neutered_points = {
        trigger["natal_point"]
        for window in compute_transit_windows(
            _neutered(public_chart), domain, start_date=AS_OF.date(), scan_days=90
        )
        for trigger in window["triggers"]
        if trigger["natal_point"].startswith("natal_")
    }
    assert neutered_points <= rule4_points, neutered_points - rule4_points


def test_pd_overlap_bonus_fires_on_public_chart(public_chart):
    """At least one domain's public-chart windows must earn the supporting-PD
    overlap bonus (recomputed PD periods); the neutered chart never can."""
    public_overlaps = []
    for domain in TRANSIT_DOMAINS:
        for window in compute_transit_windows(
            public_chart, domain, start_date=AS_OF.date(), scan_days=90
        ):
            public_overlaps.append(window["pd_overlap"])
        for window in compute_transit_windows(
            _neutered(public_chart), domain, start_date=AS_OF.date(), scan_days=90
        ):
            assert window["pd_overlap"] is False, domain
    assert any(public_overlaps), "PD overlap bonus never fired on the public chart"


@pytest.mark.parametrize("domain,engine", ENGINES, ids=[d for d, _ in ENGINES])
def test_confidence_tier_reflects_transit_support_on_public_chart(
    public_chart, domain, engine
):
    """End to end: with recomputed dasha support + slow-planet windows the
    public chart reaches a real confidence tier, while the no-signal variant
    stays 'low' — the tiers must differ, not merely the scores."""
    from_public = engine(public_chart, as_of=AS_OF)
    from_neutered = engine(_neutered(public_chart), as_of=AS_OF)

    assert from_public["confidence"] != from_neutered["confidence"]
    assert from_neutered["confidence"] == "low"  # house 4 promises nothing
    # This pinned chart + AS_OF has full dasha support and a slow-planet window
    # in the scan span, so the unified five-branch table lands on "high".
    assert from_public["confidence"] == "high"
    assert from_public["transit_summary"]["has_slow_planet_contact"] is True
    assert from_public["signal_strength"] > from_neutered["signal_strength"]


@pytest.mark.parametrize("domain,engine", ENGINES, ids=[d for d, _ in ENGINES])
def test_engine_does_not_mutate_public_chart(public_chart, domain, engine):
    before = copy.deepcopy(public_chart)
    engine(public_chart, as_of=AS_OF)
    assert public_chart == before
