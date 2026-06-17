"""Tests for the internal Vimshottari dasha engine (true tropical solar years).

The judge is tests/fixtures/jhora/dasha_expected.json — JHora's Vimshottari
export for User 1 Kolkata, with the screenshot settings "Using true tropical
solar years" and "Started from Moon". Code conforms to the fixture, never the
reverse (AGENTS.md Rule 8).

The engine implements the *true tropical solar year* convention: each dasha
boundary is the instant the true/geometric tropical Sun has advanced
``cumulative_years * 360 deg`` from its longitude at the (back-projected) birth
mahadasha start. This reproduces every JHora row to ~3.8h on this chart; the
residual is the irreducible anchor offset from our Swiss ephemeris Moon
differing from JHora's by ~1 arc-second. A fixed-constant-year model (365.25 /
365.24219 / 365.2425) is off by 54-60h and fails the 6h tolerance — that gap is
how the PD-level tests prove the convention (docs/dasha.md).

Parity tests run the real pipeline (ephemeris -> chart payload -> dasha) and are
guarded by ephemeris_files_ok(); they skip loudly on a possible Moshier
fallback, mirroring the KP/significator gates. The pure tests (order, balance,
locked constants) need no ephemeris. The public chart API is unchanged:
chart.dashas stays null (this engine is internal only, D023/D027).
"""

from __future__ import annotations

import copy
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

import pytest  # noqa: E402
import swisseph as swe  # noqa: E402

from app.engines.dasha_engine import (  # noqa: E402
    DASHA_YEARS,
    MEAN_TROPICAL_YEAR_DAYS,
    NAKSHATRA_SPAN_DEG,
    SUN_CALC_FLAGS,
    TOTAL_DASHA_YEARS,
    VIMSHOTTARI_ORDER,
    DashaPeriod,
    DashaTimeline,
    birth_balance,
    compute_dasha,
    compute_dasha_from_chart,
    vimshottari_order_from,
)
from app.engines.ephemeris_engine import (  # noqa: E402
    compute_ephemeris,
    ephemeris_files_ok,
)
from app.routers.chart import _build_chart_payload  # noqa: E402
from app.schemas.models import BirthDataRequest  # noqa: E402

FIXTURE_PATH = ROOT / "tests" / "fixtures" / "jhora" / "dasha_expected.json"
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
CHART_FX = FIXTURE["charts"][0]
CONV = FIXTURE["convention"]

TZ = ZoneInfo(CONV["timezone"])
TOL = timedelta(seconds=CONV["tolerance_seconds"])

requires_swiss = pytest.mark.skipif(
    not ephemeris_files_ok(),
    reason="SWISS_EPHE_REQUIRED: dasha parity needs .se1 files; current run may "
    "be Moshier fallback.",
)


def _ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)


# ---------------------------------------------------------------------------
# Real-pipeline helpers (chart -> dasha). Cached so the ephemeris runs once.
# ---------------------------------------------------------------------------

_CACHE: dict[str, object] = {}


def _user1_chart() -> dict:
    if "chart" not in _CACHE:
        inp = CHART_FX["input"]
        ephemeris = compute_ephemeris(
            datetime_local=f"{inp['date']}T{inp['time']}",
            timezone=inp["iana_timezone"],
            lat=inp["latitude"],
            lon=inp["longitude"],
        )
        request_data = BirthDataRequest(
            birth_date=inp["date"], birth_time=inp["time"][:5], birth_city=inp["place"]
        )
        _CACHE["chart"] = _build_chart_payload(
            ephemeris=ephemeris,
            place_label=inp["place"],
            request_data=request_data,
            geo_lat=inp["latitude"],
            geo_lon=inp["longitude"],
            timezone_str=inp["iana_timezone"],
        )
    return copy.deepcopy(_CACHE["chart"])  # callers never share state


def _timeline() -> DashaTimeline:
    if "timeline" not in _CACHE:
        _CACHE["timeline"] = compute_dasha_from_chart(_user1_chart())
    return _CACHE["timeline"]


def _birth_dt() -> datetime:
    inp = CHART_FX["input"]
    return datetime.fromisoformat(f"{inp['date']}T{inp['time']}").replace(tzinfo=TZ)


# ===========================================================================
# 1. Vimshottari order
# ===========================================================================

def test_vimshottari_order_is_the_canonical_sequence():
    assert VIMSHOTTARI_ORDER == (
        "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn",
        "Mercury",
    )


def test_order_from_rotates_to_start_at_the_given_lord():
    assert vimshottari_order_from("Venus") == [
        "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
        "Ketu",
    ]
    assert vimshottari_order_from("Moon") == [
        "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury", "Ketu", "Venus",
        "Sun",
    ]
    assert vimshottari_order_from("Ketu") == list(VIMSHOTTARI_ORDER)


def test_order_from_rejects_a_non_dasha_lord():
    with pytest.raises((KeyError, ValueError)):
        vimshottari_order_from("Pluto")


@requires_swiss
def test_mahadasha_lords_follow_vimshottari_order_from_birth_lord():
    tl = _timeline()
    assert [p.lord for p in tl.mahadashas] == vimshottari_order_from("Venus")


@requires_swiss
def test_antardasha_and_pd_orders_start_with_their_parent_lord():
    tl = _timeline()
    # ADs of the Venus MD start with Venus and run in Vimshottari order.
    venus_ads = [p for p in tl.antardashas if p.lords[0] == "Venus"]
    assert [p.lord for p in venus_ads] == vimshottari_order_from("Venus")
    # PDs of Venus/Moon start with Moon.
    vm_pds = [p for p in tl.pratyantardashas if p.lords[:2] == ("Venus", "Moon")]
    assert [p.lord for p in vm_pds] == vimshottari_order_from("Moon")


# ===========================================================================
# 2. 120-year cycle
# ===========================================================================

def test_dasha_years_sum_to_120():
    assert sum(DASHA_YEARS.values()) == 120
    assert TOTAL_DASHA_YEARS == 120
    assert set(DASHA_YEARS) == set(VIMSHOTTARI_ORDER)
    assert DASHA_YEARS == {
        "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18,
        "Jupiter": 16, "Saturn": 19, "Mercury": 17,
    }


@requires_swiss
def test_full_cycle_has_nine_mahadashas_spanning_about_120_tropical_years():
    tl = _timeline()
    assert len(tl.mahadashas) == 9
    assert {p.lord for p in tl.mahadashas} == set(VIMSHOTTARI_ORDER)
    span_days = (tl.mahadashas[-1].end - tl.mahadashas[0].start).total_seconds() / 86400.0
    # 120 true tropical solar years; the mean tropical year is ~365.2425 days.
    assert abs(span_days - 120 * MEAN_TROPICAL_YEAR_DAYS) < 1.0


# ===========================================================================
# 3. Birth MD lord derives from the Moon nakshatra lord
# ===========================================================================

def test_birth_balance_lord_is_the_moon_nakshatra_lord():
    lord, _years = birth_balance("Venus", 3.7641666666666667)
    assert lord == "Venus"


def test_birth_balance_years_use_the_remaining_fraction_formula():
    # remaining = MD_years * (NAK_SPAN - moon_deg) / NAK_SPAN
    moon_deg = 3.7641666666666667
    _lord, years = birth_balance("Venus", moon_deg)
    expected = DASHA_YEARS["Venus"] * (NAKSHATRA_SPAN_DEG - moon_deg) / NAKSHATRA_SPAN_DEG
    assert years == pytest.approx(expected)
    assert 0.0 <= years <= DASHA_YEARS["Venus"]


def test_birth_balance_endpoints():
    # Moon at the very start of a nakshatra -> the whole MD remains.
    assert birth_balance("Moon", 0.0)[1] == pytest.approx(DASHA_YEARS["Moon"])
    # Moon at the very end -> essentially nothing remains.
    assert birth_balance("Moon", NAKSHATRA_SPAN_DEG)[1] == pytest.approx(0.0)


@requires_swiss
def test_timeline_birth_md_lord_matches_chart_moon_nakshatra_lord():
    chart = _user1_chart()
    moon = next(p for p in chart["planets"] if p["name"] == "Moon")
    tl = compute_dasha_from_chart(chart)
    assert tl.birth_balance_lord == moon["nakshatra"]["lord"] == "Venus"
    assert tl.mahadashas[0].lord == "Venus"


# ===========================================================================
# 4. Birth dasha stack = Venus / Moon / Venus
# ===========================================================================

@requires_swiss
def test_birth_stack_is_venus_moon_venus():
    tl = _timeline()
    md, ad, pd = tl.current_stack(_birth_dt())
    expected = CHART_FX["birth_stack"]
    assert (md.lord, ad.lord, pd.lord) == (expected["md"], expected["ad"], expected["pd"])
    assert (md.lord, ad.lord, pd.lord) == ("Venus", "Moon", "Venus")


# ===========================================================================
# 5/6/7. MD / AD / PD fixture dates within tolerance
# ===========================================================================

@requires_swiss
@pytest.mark.parametrize(
    "row", CHART_FX["mahadashas"], ids=[r["md"] for r in CHART_FX["mahadashas"]]
)
def test_mahadasha_dates_match_jhora_within_tolerance(row):
    tl = _timeline()
    period = next(p for p in tl.mahadashas if p.lord == row["md"])
    assert abs(period.start - _ts(row["start"])) <= TOL, f"{row['md']} start"
    assert abs(period.end - _ts(row["end"])) <= TOL, f"{row['md']} end"


def _ad_rows():
    rows = []
    for md, ads in CHART_FX["antardashas"].items():
        for r in ads:
            rows.append((md, r))
    return rows


@requires_swiss
@pytest.mark.parametrize(
    "md,row", _ad_rows(), ids=[f"{md}-{r['ad']}" for md, r in _ad_rows()]
)
def test_antardasha_dates_match_jhora_within_tolerance(md, row):
    tl = _timeline()
    period = next(
        p for p in tl.antardashas if p.lords == (md, row["ad"])
    )
    assert abs(period.start - _ts(row["start"])) <= TOL, f"{md}/{row['ad']} start"
    assert abs(period.end - _ts(row["end"])) <= TOL, f"{md}/{row['ad']} end"


def _pd_rows():
    rows = []
    for key, pds in CHART_FX["pratyantardashas"].items():
        md, ad = key.split("/")
        for r in pds:
            rows.append((md, ad, r))
    return rows


@requires_swiss
@pytest.mark.parametrize(
    "md,ad,row", _pd_rows(),
    ids=[f"{md}-{ad}-{r['pd']}" for md, ad, r in _pd_rows()],
)
def test_pratyantardasha_dates_match_jhora_within_tolerance(md, ad, row):
    tl = _timeline()
    period = next(
        p for p in tl.pratyantardashas if p.lords == (md, ad, row["pd"])
    )
    assert abs(period.start - _ts(row["start"])) <= TOL, f"{md}/{ad}/{row['pd']} start"
    assert abs(period.end - _ts(row["end"])) <= TOL, f"{md}/{ad}/{row['pd']} end"


# ===========================================================================
# 8. current_stack at midnight, noon, and the exact boundary
# ===========================================================================

@requires_swiss
@pytest.mark.parametrize(
    "case", CHART_FX["current_stack_cases"],
    ids=[c["at"] for c in CHART_FX["current_stack_cases"]],
)
def test_current_stack_cases(case):
    tl = _timeline()
    md, ad, pd = tl.current_stack(_ts(case["at"]))
    assert (md.lord, ad.lord, pd.lord) == (case["md"], case["ad"], case["pd"]), case["note"]


@requires_swiss
def test_current_lords_helper_agrees_with_current_stack():
    tl = _timeline()
    at = _ts("2026-06-17 12:00:00")
    md, ad, pd = tl.current_stack(at)
    assert tl.current_lords(at) == (md.lord, ad.lord, pd.lord)


@requires_swiss
def test_boundary_is_start_inclusive_end_exclusive():
    # At an exact internal boundary, the NEW period owns the instant.
    tl = _timeline()
    boundary = tl.mahadashas[1].start  # == mahadashas[0].end
    assert tl.mahadashas[0].end == boundary
    assert tl.current_stack(boundary)[0].lord == tl.mahadashas[1].lord
    # one microsecond before the boundary still belongs to the old period
    assert tl.current_stack(boundary - timedelta(microseconds=1))[0].lord == tl.mahadashas[0].lord


# ===========================================================================
# 9/10/11. Continuity and nesting
# ===========================================================================

@requires_swiss
def test_mahadashas_are_continuous_and_strictly_increasing():
    tl = _timeline()
    for a, b in zip(tl.mahadashas, tl.mahadashas[1:]):
        assert a.end == b.start
        assert a.start < a.end


@requires_swiss
def test_antardashas_tile_their_mahadasha_exactly():
    tl = _timeline()
    for md in tl.mahadashas:
        ads = [p for p in tl.antardashas if p.lords[0] == md.lord]
        assert ads[0].start == md.start
        assert ads[-1].end == md.end
        for a, b in zip(ads, ads[1:]):
            assert a.end == b.start
        for ad in ads:
            assert md.start <= ad.start < ad.end <= md.end


@requires_swiss
def test_pratyantardashas_tile_their_antardasha_exactly():
    tl = _timeline()
    for ad in tl.antardashas:
        pds = [p for p in tl.pratyantardashas if p.lords[:2] == ad.lords]
        assert pds[0].start == ad.start
        assert pds[-1].end == ad.end
        for a, b in zip(pds, pds[1:]):
            assert a.end == b.start
        for pd in pds:
            assert ad.start <= pd.start < pd.end <= ad.end


@requires_swiss
def test_counts_are_9_81_729():
    tl = _timeline()
    assert len(tl.mahadashas) == 9
    assert len(tl.antardashas) == 81
    assert len(tl.pratyantardashas) == 729


# ===========================================================================
# 12. The engine does not mutate the input chart payload
# ===========================================================================

@requires_swiss
def test_compute_dasha_from_chart_does_not_mutate_input():
    chart = _user1_chart()
    before = copy.deepcopy(chart)
    compute_dasha_from_chart(chart)
    assert chart == before


# ===========================================================================
# 13. Public chart API is unchanged: chart.dashas stays null
# ===========================================================================

@requires_swiss
def test_public_chart_payload_leaves_dashas_null():
    # The internal dasha engine populates no public field; the assembled chart
    # still validates with dashas == None (D023/D027: internal only).
    chart = _user1_chart()
    assert chart["dashas"] is None
    # Running the engine changes nothing about the public payload.
    compute_dasha_from_chart(chart)
    assert chart["dashas"] is None


# ===========================================================================
# Locked convention + proof that a constant year cannot reproduce JHora
# ===========================================================================

def test_locked_convention_constants():
    # Mean tropical year (Newton seed / nominal); the engine's period lengths
    # come from real Sun transits, not this constant (docs/dasha.md).
    assert MEAN_TROPICAL_YEAR_DAYS == 365.2425
    assert NAKSHATRA_SPAN_DEG == 13.333333333333334
    # True/geometric tropical Sun: TRUEPOS on, SIDEREAL off.
    assert SUN_CALC_FLAGS & swe.FLG_TRUEPOS
    assert SUN_CALC_FLAGS & swe.FLG_SWIEPH
    assert not (SUN_CALC_FLAGS & swe.FLG_SIDEREAL)


def test_fixture_year_length_is_not_constant():
    # If JHora used a fixed year, every MD's implied year length would be equal.
    # They are not: the true tropical solar year varies with the Sun's speed.
    implied = {}
    for r in CHART_FX["mahadashas"]:
        days = (_ts(r["end"]) - _ts(r["start"])).total_seconds() / 86400.0
        implied[r["md"]] = days / DASHA_YEARS[r["md"]]
    spread = max(implied.values()) - min(implied.values())
    assert spread * 86400 > 120, implied  # > 2 minutes/yr of variation


@requires_swiss
def test_constant_year_model_fails_the_tolerance_proving_the_convention():
    # Independent oracle: build the same ladder with a FIXED year, anchored from
    # the same Moon balance, and show it cannot reproduce the deep 2026 PDs.
    # The real engine matches within TOL (tested above); a constant cannot.
    chart = _user1_chart()
    moon = next(p for p in chart["planets"] if p["name"] == "Moon")
    moon_deg = moon["nakshatra"]["degree_in_nakshatra"]
    birth = _birth_dt()

    def constant_pd_start(year_days: float, md: str, ad: str, pd: str) -> datetime:
        elapsed = DASHA_YEARS["Venus"] * (moon_deg / NAKSHATRA_SPAN_DEG)
        anchor = birth - timedelta(days=elapsed * year_days)
        cum = 0.0
        for m in vimshottari_order_from("Venus"):
            for a in vimshottari_order_from(m):
                ad_len = DASHA_YEARS[m] * DASHA_YEARS[a] / 120.0
                for p in vimshottari_order_from(a):
                    pd_len = ad_len * DASHA_YEARS[p] / 120.0
                    if (m, a, p) == (md, ad, pd):
                        return anchor + timedelta(days=cum * year_days)
                    cum += pd_len
        raise AssertionError("pd not found")

    row = CHART_FX["pratyantardashas"]["Moon/Ketu"][5]  # Moon/Ketu/Rahu
    assert row["pd"] == "Rahu"
    expected = _ts(row["start"])
    for year_days in (365.25, 365.24219, 365.2425):
        got = constant_pd_start(year_days, "Moon", "Ketu", "Rahu")
        assert abs(got - expected) > TOL, f"constant {year_days} unexpectedly matched"

    # And the real engine DOES match the same row within TOL.
    tl = _timeline()
    period = next(p for p in tl.pratyantardashas if p.lords == ("Moon", "Ketu", "Rahu"))
    assert abs(period.start - expected) <= TOL


# ===========================================================================
# DashaPeriod / DashaTimeline shape sanity
# ===========================================================================

@requires_swiss
def test_period_objects_have_expected_shape():
    tl = _timeline()
    md = tl.mahadashas[0]
    assert isinstance(md, DashaPeriod)
    assert md.level == "MD"
    assert md.lords == ("Venus",)
    assert md.lord == "Venus"
    assert md.start.tzinfo is not None
    assert md.contains(md.start)  # start inclusive
    assert not md.contains(md.end)  # end exclusive
    ad = tl.antardashas[0]
    assert ad.level == "AD" and len(ad.lords) == 2
    pd = tl.pratyantardashas[0]
    assert pd.level == "PD" and len(pd.lords) == 3


def test_compute_dasha_requires_timezone_aware_birth():
    with pytest.raises(ValueError):
        compute_dasha(
            moon_nakshatra_lord="Venus",
            moon_degree_in_nakshatra=3.764,
            birth=datetime(1998, 8, 14, 6, 45, 0),  # naive -> rejected
        )
