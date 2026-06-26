"""Tests for the transit window engine (T8).

The primary chart is User "Pratyus" (20 Aug 2002, 15:45, Siliguri), the
JHora-verified KP-Newcomb chart used throughout the project. The chart dict is
assembled by hand here (no ephemeris call for the *natal* side) so the natal
positions, KP cusp sub-lords, dasha lords and node-aware significators are
fixed, deterministic inputs; only the *transit* side touches Swiss Ephemeris.

``significator_of_houses`` for each planet is the node-aware significator output
(D028) for this chart, computed once via ``significator_engine`` and pinned here
as constants — the transit engine reads these straight from the chart dict and
imports no other engine.

Fixture routing (Test 1). The withdrawn Venus->natal-Sun fixture was correct KP
behaviour: natal Sun signifies only houses 8 and 12, which are *blocking* in
every domain, so a transit over it must never raise a domain window. Each
remaining fixture is routed to the domain where its natal point genuinely has
significance:

* Jupiter -> natal Jupiter : relationship (Jupiter occupies house 7, is MD+AD
  lord, signifies the 7th).
* Mars -> natal Saturn : career (Saturn occupies house 6, signifies 2/6/11).
* Sun -> natal Jupiter : relationship (same natal Jupiter contact).

Each fixture is verified with a focused (<=30 day) scan centred on its contact
date: that keeps the window construction in its un-tightened regime, so the
named conjunction itself anchors the window rather than being summarised away by
the dense-period orb tightening that a long multi-month scan triggers.
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.engines.transit_engine import compute_transit_windows, find_next_contact

# The four slow bodies are the only ones find_next_contact may return.
SLOW_PLANETS = {"Jupiter", "Saturn", "Rahu", "Ketu"}
NEXT_CONTACT_KEYS = {
    "planet", "natal_point", "natal_longitude", "estimated_date", "days_away"
}

# ---------------------------------------------------------------------------
# Swiss-ephemeris availability gate (mirrors conftest's SE_EPHE_PATH wiring so
# the module is self-contained when run directly).
# ---------------------------------------------------------------------------

_EPHE_DIR = Path(__file__).resolve().parent.parent / "ephe"
if not os.environ.get("SE_EPHE_PATH") and _EPHE_DIR.is_dir():
    os.environ["SE_EPHE_PATH"] = str(_EPHE_DIR)


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

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "transit" / "known_contacts_jun_aug_2026.json"
ALL_DOMAINS = ("career", "finance", "relationship")

# ---------------------------------------------------------------------------
# Pinned natal chart data (JHora-verified KP-Newcomb, Pratyus 20 Aug 2002)
# ---------------------------------------------------------------------------

_NATAL_LONGITUDE = {
    "Sun": 123.44, "Moon": 274.61, "Mars": 120.37, "Mercury": 327.99,
    "Jupiter": 100.29, "Venus": 169.41, "Saturn": 62.94, "Rahu": 51.50,
    "Ketu": 231.50,
}
_SIGN = {
    "Sun": ("Leo", "Sun"), "Moon": ("Capricorn", "Saturn"), "Mars": ("Leo", "Sun"),
    "Mercury": ("Aquarius", "Saturn"), "Jupiter": ("Cancer", "Moon"),
    "Venus": ("Virgo", "Mercury"), "Saturn": ("Gemini", "Mercury"),
    "Rahu": ("Taurus", "Venus"), "Ketu": ("Scorpio", "Mars"),
}
_HOUSE_OCCUPIED = {
    "Sun": 8, "Moon": 1, "Mars": 8, "Mercury": 3, "Jupiter": 7, "Venus": 9,
    "Saturn": 6, "Rahu": 6, "Ketu": 12,
}
# KP star/sub lord at each planet's longitude (Krishnamurti ayanamsa).
_PLANET_KP = {
    "Sun": ("Ketu", "Sun"), "Moon": ("Sun", "Saturn"), "Mars": ("Ketu", "Ketu"),
    "Mercury": ("Jupiter", "Venus"), "Jupiter": ("Saturn", "Venus"),
    "Venus": ("Moon", "Mercury"), "Saturn": ("Mars", "Venus"),
    "Rahu": ("Moon", "Venus"), "Ketu": ("Mercury", "Venus"),
}
# Node-aware significator_of_houses (D028) for this chart, pinned from
# significator_engine.compute_node_aware_significators().
_SIGNIFICATOR_OF_HOUSES = {
    "Sun": [8, 12],
    "Moon": [1, 8],
    "Mars": [4, 8, 11, 12],
    "Mercury": [1, 3, 7, 9],
    "Jupiter": [1, 2, 3, 6, 7, 12],
    "Venus": [1, 5, 6, 8, 9, 10],
    "Saturn": [2, 3, 4, 6, 8, 11, 12],
    "Rahu": [1, 5, 6, 8, 9, 10],
    "Ketu": [1, 2, 3, 4, 6, 7, 8, 9, 11, 12],
}
_PLANET_ORDER = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")

# Placidus KP-Newcomb cusps 1..12 with their KP star/sub lords and sign lords.
_CUSP_LONGITUDE = {
    1: 263.60, 2: 299.99, 3: 318.54, 4: 9.14, 5: 35.65, 6: 59.26,
    7: 83.60, 8: 119.79, 9: 158.55, 10: 189.17, 11: 215.64, 12: 227.46,
}
_CUSP_SIGN = {
    1: ("Sagittarius", "Jupiter"), 2: ("Capricorn", "Saturn"), 3: ("Aquarius", "Saturn"),
    4: ("Aries", "Mars"), 5: ("Taurus", "Venus"), 6: ("Taurus", "Venus"),
    7: ("Gemini", "Mercury"), 8: ("Cancer", "Moon"), 9: ("Virgo", "Mercury"),
    10: ("Libra", "Venus"), 11: ("Scorpio", "Mars"), 12: ("Scorpio", "Mars"),
}
_CUSP_KP = {
    1: ("Venus", "Saturn"), 2: ("Mars", "Saturn"), 3: ("Rahu", "Moon"),
    4: ("Ketu", "Jupiter"), 5: ("Sun", "Mercury"), 6: ("Mars", "Saturn"),
    7: ("Jupiter", "Saturn"), 8: ("Mercury", "Saturn"), 9: ("Sun", "Venus"),
    10: ("Rahu", "Jupiter"), 11: ("Saturn", "Mercury"), 12: ("Mercury", "Mercury"),
}
# Bhava (JHora midpoint span) occupants, derived from house_occupied above.
_OCCUPANTS = {h: [] for h in range(1, 13)}
for _planet, _house in _HOUSE_OCCUPIED.items():
    _OCCUPANTS[_house].append(_planet)


def build_test_chart() -> dict:
    """Assemble the Pratyus chart dict in the shape the engines read."""
    planets = []
    for name in _PLANET_ORDER:
        sign, sign_lord = _SIGN[name]
        star_lord, sub_lord = _PLANET_KP[name]
        planets.append(
            {
                "name": name,
                "longitude": _NATAL_LONGITUDE[name],
                "sign": sign,
                "sign_lord": sign_lord,
                "house_occupied": _HOUSE_OCCUPIED[name],
                "retrograde": False,
                "combust": False,
                "kp": {"star_lord": star_lord, "sub_lord": sub_lord},
                "significator_of_houses": list(_SIGNIFICATOR_OF_HOUSES[name]),
            }
        )

    houses = []
    for house_number in range(1, 13):
        cusp_sign, cusp_sign_lord = _CUSP_SIGN[house_number]
        star_lord, sub_lord = _CUSP_KP[house_number]
        houses.append(
            {
                "house": house_number,
                "cusp_longitude": _CUSP_LONGITUDE[house_number],
                "cusp_sign": cusp_sign,
                "cusp_sign_lord": cusp_sign_lord,
                "kp": {"star_lord": star_lord, "sub_lord": sub_lord},
                "occupants": list(_OCCUPANTS[house_number]),
            }
        )

    # Current Vimshottari stack as of 2026-06-25: Jupiter > Jupiter > Mercury.
    dashas = {
        "system": "VIMSHOTTARI",
        "current": {
            "mahadasha": {"lord": "Jupiter", "start": date(2014, 1, 1), "end": date(2030, 1, 1)},
            "antardasha": {"lord": "Jupiter", "start": date(2026, 2, 15), "end": date(2027, 6, 10)},
            "pratyantardasha": {"lord": "Mercury", "start": date(2026, 6, 1), "end": date(2026, 8, 20)},
        },
        "upcoming_pd": [],
    }

    return {"planets": planets, "houses": houses, "dashas": dashas}


@pytest.fixture
def test_chart() -> dict:
    return build_test_chart()


def _covers(window: dict, contact_date: str) -> bool:
    return window["start_date"] <= contact_date <= window["end_date"]


def _span_days(window: dict) -> int:
    start = date.fromisoformat(window["start_date"])
    end = date.fromisoformat(window["end_date"])
    return (end - start).days


# ---------------------------------------------------------------------------
# Test 1 — JHora fixture validation
# ---------------------------------------------------------------------------

@requires_swiss
def test_jhora_fixtures_detected(test_chart):
    """Each verified transit contact is detected by a window in its routed domain.

    A focused scan centred on the contact date (so the window stays under the
    30-day orb-tightening threshold) must return at least one window that both
    covers the exact contact date and actually carries the named
    transit-planet -> natal-point trigger.
    """
    fixtures = json.loads(FIXTURE_PATH.read_text())
    assert len(fixtures) == 3

    for fixture in fixtures:
        domain = fixture["domain"]
        transit_planet = fixture["transit_planet"]
        natal_point = fixture["natal_point"]
        contact_date = fixture["exact_contact_date"]

        scan_start = date.fromisoformat(contact_date) - timedelta(days=10)
        windows = compute_transit_windows(
            test_chart, domain, start_date=scan_start, scan_days=21
        )

        covering = [w for w in windows if _covers(w, contact_date)]
        assert covering, (
            f"{fixture['description']} ({domain}): no window covers {contact_date}; "
            f"got {[(w['start_date'], w['end_date']) for w in windows]}"
        )
        assert any(
            trigger["planet"] == transit_planet and trigger["natal_point"] == natal_point
            for window in covering
            for trigger in window["triggers"]
        ), f"{fixture['description']}: covering window lacks the {transit_planet}->{natal_point} trigger"


# ---------------------------------------------------------------------------
# Test 2 — property: window length <= 30 days
# ---------------------------------------------------------------------------

@requires_swiss
def test_windows_never_exceed_30_days(test_chart):
    for domain in ALL_DOMAINS:
        windows = compute_transit_windows(
            test_chart, domain, start_date=date(2026, 6, 25), scan_days=90
        )
        for window in windows:
            assert _span_days(window) <= 30, f"{domain} window too long: {window}"


# ---------------------------------------------------------------------------
# Test 3 — property: every window has at least two triggers
# ---------------------------------------------------------------------------

@requires_swiss
def test_windows_have_minimum_triggers(test_chart):
    for domain in ALL_DOMAINS:
        windows = compute_transit_windows(
            test_chart, domain, start_date=date(2026, 6, 25), scan_days=90
        )
        for window in windows:
            assert window["trigger_count"] >= 2, f"{domain} window under-triggered: {window}"
            assert len(window["triggers"]) == window["trigger_count"]


# ---------------------------------------------------------------------------
# Test 4 — property: returned windows are >= 7 days apart
# ---------------------------------------------------------------------------

@requires_swiss
def test_windows_separated_by_seven_days(test_chart):
    for domain in ALL_DOMAINS:
        windows = compute_transit_windows(
            test_chart, domain, start_date=date(2026, 6, 25), scan_days=90
        )
        if len(windows) < 2:
            continue
        ordered = sorted(windows, key=lambda w: w["start_date"])
        for earlier, later in zip(ordered, ordered[1:]):
            gap = (date.fromisoformat(later["start_date"]) - date.fromisoformat(earlier["end_date"])).days
            assert gap >= 7, f"{domain} windows too close: {earlier} / {later}"


# ---------------------------------------------------------------------------
# Test 5 — empty-result safety
# ---------------------------------------------------------------------------

def test_invalid_domain_returns_empty(test_chart):
    """An unknown domain returns [] without raising and without any swiss call."""
    assert compute_transit_windows(test_chart, "invalid_domain") == []
    assert compute_transit_windows(test_chart, "", start_date=date(2026, 6, 25)) == []


# ---------------------------------------------------------------------------
# Test 6 — Moon-only rejection
# ---------------------------------------------------------------------------

@requires_swiss
def test_moon_only_window_rejected(test_chart):
    """A far-future 3-day scan, where at most the fast Moon brushes a contact,
    yields no window: a Moon-only candidate is always rejected."""
    far_future = date(2031, 1, 8)
    for domain in ALL_DOMAINS:
        windows = compute_transit_windows(
            test_chart, domain, start_date=far_future, scan_days=3
        )
        assert windows == [], f"{domain} produced a window from Moon-only contacts: {windows}"


# ---------------------------------------------------------------------------
# Test 7 — retrograde (Rahu) deduplication
# ---------------------------------------------------------------------------

@requires_swiss
def test_rahu_not_duplicated_within_30_days(test_chart):
    """Rahu (always retrograde, deduped within 14 days) never anchors two
    windows on the same natal point within any 30-day span."""
    windows = compute_transit_windows(
        test_chart, "relationship", start_date=date(2026, 6, 25), scan_days=180
    )

    rahu_windows_by_point: dict[str, list[tuple[date, date]]] = {}
    for window in windows:
        points = {t["natal_point"] for t in window["triggers"] if t["planet"] == "Rahu"}
        for point in points:
            rahu_windows_by_point.setdefault(point, []).append(
                (date.fromisoformat(window["start_date"]), date.fromisoformat(window["end_date"]))
            )

    for point, ranges in rahu_windows_by_point.items():
        ranges.sort()
        for (start_a, end_a), (start_b, end_b) in zip(ranges, ranges[1:]):
            assert (start_b - start_a).days > 30, (
                f"Rahu produced two windows on {point} within 30 days: "
                f"{start_a}..{end_a} and {start_b}..{end_b}"
            )


# ---------------------------------------------------------------------------
# Test 8 — find_next_contact: forward slow-planet contact search
# ---------------------------------------------------------------------------

@requires_swiss
def test_find_next_contact_shape_and_slow_planet(test_chart):
    """For every domain the forward scan yields a populated, well-formed contact
    anchored on a slow planet at least ``after_days`` out."""
    for domain in ALL_DOMAINS:
        contact = find_next_contact(test_chart, domain)
        assert contact, f"{domain}: find_next_contact returned empty"
        assert set(contact) == NEXT_CONTACT_KEYS, contact
        assert contact["planet"] in SLOW_PLANETS, contact
        assert 0.0 <= contact["natal_longitude"] < 360.0, contact
        # Default after_days=90: the contact is never sooner than that.
        assert contact["days_away"] >= 90, contact
        # estimated_date is a real ISO date consistent with days_away.
        estimated = date.fromisoformat(contact["estimated_date"])
        assert (estimated - date.today()).days == contact["days_away"], contact


@requires_swiss
def test_find_next_contact_respects_after_days(test_chart):
    """A larger ``after_days`` pushes the earliest qualifying contact further out."""
    for domain in ALL_DOMAINS:
        contact = find_next_contact(test_chart, domain, after_days=400)
        assert contact["days_away"] >= 400, contact


@requires_swiss
def test_find_next_contact_is_deterministic(test_chart):
    """Same chart, domain and after_days on the same day -> identical contact."""
    for domain in ALL_DOMAINS:
        first = find_next_contact(test_chart, domain)
        second = find_next_contact(test_chart, domain)
        assert first == second, domain


@requires_swiss
def test_find_next_contact_never_empty_for_valid_domains(test_chart):
    """The defining guarantee: a valid domain always gets a non-empty contact."""
    for domain in ALL_DOMAINS:
        assert find_next_contact(test_chart, domain), domain


def test_find_next_contact_invalid_domain_returns_empty(test_chart):
    """An unknown domain returns {} without raising (no swiss call needed)."""
    assert find_next_contact(test_chart, "invalid_domain") == {}
    assert find_next_contact(test_chart, "") == {}
