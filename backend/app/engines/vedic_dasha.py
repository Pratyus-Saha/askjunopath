"""Vimshottari dasha for the Vedic (Parashari) engine — current-path only.

This is a SEPARATE fork from ``app.engines.dasha_engine`` (the KP path). It
shares only the Swiss Ephemeris tropical layer and the time->Julian-Day helper
(``_julian_day_ut``) from ``ephemeris_engine``; everything else is forked so the
KP engine is never touched.

Scope (frozen, per task spec)
-----------------------------
* Vimshottari, seeded from the Moon's longitude within its nakshatra.
* FOUR levels only: Mahadasha (MD) -> Antardasha (AD) -> Pratyantardasha (PD)
  -> Sookshma (SD). Never below Sookshma.
* For a given target datetime, expose ONLY the active running MD/AD/PD/SD, each
  with start/end datetimes. The full nested tree is never materialised — only
  the boundaries along the active path are solved.

Convention (matches the project's JHora reference in ``dasha_engine.py``)
------------------------------------------------------------------------
* Order: ``Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury``,
  year counts summing to 120.
* Birth MD lord = the Moon's nakshatra lord. Birth-MD balance =
  ``MD_years * (NAK_SPAN - moon_degree_in_nakshatra) / NAK_SPAN``.
* True tropical solar years: a boundary at cumulative time ``T`` years from the
  back-projected birth-MD start is the instant the true/geometric tropical Sun
  has advanced ``T * 360 deg`` from its longitude at that start. Each level
  subdivides its parent in proportion ``parent_years * child_years / 120``.
* Boundaries are start-inclusive, end-exclusive.

NOTE (flagged, not validated): the true-solar-year convention is inherited from
the KP reference because JHora is the shared oracle; it must be reconfirmed
against ``vedic_fixtures.json`` when that file exists. A different year length
(365.25 mean days, 360 savana days) shifts SD boundaries by minutes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Callable

import swisseph as swe

# Shared time->Julian-Day helper (the ONLY thing imported from the KP layer).
from app.engines.ephemeris_engine import _julian_day_ut

# ---------------------------------------------------------------------------
# Locked Vimshottari constants (forked copy — the KP engine is untouched)
# ---------------------------------------------------------------------------

VIMSHOTTARI_ORDER: tuple[str, ...] = (
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn",
    "Mercury",
)

DASHA_YEARS: dict[str, int] = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18,
    "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}

TOTAL_DASHA_YEARS = 120

# One nakshatra spans 13 deg 20 min.
NAKSHATRA_SPAN_DEG = 13.0 + 20.0 / 60.0

# Mean tropical year in days — ONLY seeds the Sun-transit solver, never a period
# length (period lengths come from real Sun transits).
MEAN_TROPICAL_YEAR_DAYS = 365.2425

# True/geometric tropical Sun: Swiss ephemeris, with speed and TRUE position,
# and NO sidereal flag (tropical longitude for the solar-year clock).
_SUN_CALC_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_TRUEPOS

_UTC = dt_timezone.utc

# The four dasha levels this engine computes, top to bottom.
_LEVELS = ("MD", "AD", "PD", "SD")


# ---------------------------------------------------------------------------
# Order / balance (pure)
# ---------------------------------------------------------------------------

def vimshottari_order_from(lord: str) -> list[str]:
    """Rotate the Vimshottari sequence to start at ``lord``."""
    if lord not in DASHA_YEARS:
        raise ValueError(f"{lord!r} is not a Vimshottari dasha lord")
    i = VIMSHOTTARI_ORDER.index(lord)
    return list(VIMSHOTTARI_ORDER[i:]) + list(VIMSHOTTARI_ORDER[:i])


def birth_balance(moon_nakshatra_lord: str,
                  moon_degree_in_nakshatra: float) -> tuple[str, float]:
    """Return (birth MD lord, balance years remaining) from the Moon."""
    if moon_nakshatra_lord not in DASHA_YEARS:
        raise ValueError(
            f"{moon_nakshatra_lord!r} is not a Vimshottari dasha lord"
        )
    if not (0.0 <= moon_degree_in_nakshatra <= NAKSHATRA_SPAN_DEG + 1e-9):
        raise ValueError(
            f"moon_degree_in_nakshatra {moon_degree_in_nakshatra} is outside "
            f"[0, {NAKSHATRA_SPAN_DEG}]"
        )
    md_years = DASHA_YEARS[moon_nakshatra_lord]
    remaining = (NAKSHATRA_SPAN_DEG - moon_degree_in_nakshatra) / NAKSHATRA_SPAN_DEG
    return moon_nakshatra_lord, md_years * remaining


# ---------------------------------------------------------------------------
# Swiss ephemeris helpers (tropical true Sun)
# ---------------------------------------------------------------------------

def _init_swe() -> None:
    """Point Swiss Ephemeris at SE_EPHE_PATH; no sidereal mode (Sun is tropical)."""
    ephe_path = os.environ.get("SE_EPHE_PATH")
    swe.set_ephe_path(ephe_path if ephe_path else None)


def _from_jd_ut(jd: float, tz: dt_timezone) -> datetime:
    """Julian Day (UT) -> whole-second civil datetime in ``tz``."""
    year, month, day, hour = swe.revjul(jd, swe.GREG_CAL)
    utc_dt = datetime(year, month, day, tzinfo=_UTC) + timedelta(hours=hour)
    utc_dt = utc_dt.replace(microsecond=0) + timedelta(
        seconds=1 if utc_dt.microsecond >= 500_000 else 0
    )
    return utc_dt.astimezone(tz)


def _sun_longitude_speed(jd: float) -> tuple[float, float]:
    xx, _retflag = swe.calc_ut(jd, swe.SUN, _SUN_CALC_FLAGS)
    return xx[0] % 360.0, xx[3]


def _solve_transit(anchor_jd: float, anchor_lon: float, advance_deg: float) -> float:
    """Julian day (UT) at which the true tropical Sun has advanced ``advance_deg``.

    ``advance_deg`` is a signed cumulative angle from ``anchor_lon`` (may exceed
    360 or be negative). Newton's method seeded by the mean year converges in a
    few iterations.
    """
    jd = anchor_jd + advance_deg / 360.0 * MEAN_TROPICAL_YEAR_DAYS
    target = (anchor_lon + advance_deg) % 360.0
    for _ in range(60):
        lon, speed = _sun_longitude_speed(jd)
        diff = ((lon - target + 180.0) % 360.0) - 180.0  # signed (-180, 180]
        step = diff / speed
        jd -= step
        if abs(step) < 1e-10:
            break
    return jd


# ---------------------------------------------------------------------------
# Current-path computation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DashaLevel:
    """One active dasha period on the running path."""

    level: str          # "MD" | "AD" | "PD" | "SD"
    lord: str
    start: datetime
    end: datetime


def _descend(order_lord: str, start_cum: float, span_years: float,
             at: Callable[[float], datetime],
             target: datetime) -> tuple[str, float, float, datetime, datetime]:
    """Find the child period (in Vimshottari order from ``order_lord``) that is
    active at ``target``.

    ``span_years`` is the parent period's total length in years; each child gets
    ``span_years * child_years / 120``. At the MD level ``span_years`` is 120 so
    each child MD gets exactly its ``DASHA_YEARS``.

    Returns ``(child_lord, child_start_cum, child_span_years, start_dt, end_dt)``.
    """
    cum = start_cum
    last = None
    for lord in vimshottari_order_from(order_lord):
        child_span = span_years * DASHA_YEARS[lord] / TOTAL_DASHA_YEARS
        start_dt = at(cum)
        end_dt = at(cum + child_span)
        last = (lord, cum, child_span, start_dt, end_dt)
        if start_dt <= target < end_dt:
            return last
        cum += child_span
    # Float edge exactly on the closing boundary: attribute to the last child.
    if last is not None and target == last[4]:
        return last
    raise ValueError(
        f"target {target.isoformat()} is outside the {order_lord} period "
        f"[{at(start_cum).isoformat()}, {at(start_cum + span_years).isoformat()})"
    )


def compute_current_dasha(
    *,
    moon_longitude: float,
    moon_nakshatra_lord: str,
    moon_degree_in_nakshatra: float,
    birth: datetime,
    target: datetime,
) -> dict:
    """Return the active MD/AD/PD/SD at ``target`` for a birth Moon.

    Args:
        moon_longitude: sidereal Moon longitude (kept for provenance; the lord
            and degree-in-nakshatra are the actual seeds).
        moon_nakshatra_lord: the Moon's nakshatra lord (birth MD lord).
        moon_degree_in_nakshatra: Moon's degrees into its nakshatra [0, 13.333].
        birth: timezone-aware birth datetime.
        target: timezone-aware datetime to evaluate the running dasha at.

    Returns a dict ``{"maha","antar","pratyantar","sookshma"}`` each mapping to
    ``{"lord","start","end"}`` (ISO-8601 strings in ``target``'s zone), plus
    ``birth_balance_lord`` / ``birth_balance_years`` for provenance.
    """
    if birth.tzinfo is None or target.tzinfo is None:
        raise ValueError("`birth` and `target` must be timezone-aware")
    tz = target.tzinfo

    birth_lord, balance_years = birth_balance(
        moon_nakshatra_lord, moon_degree_in_nakshatra
    )
    elapsed_years = DASHA_YEARS[birth_lord] - balance_years  # run at birth

    _init_swe()
    birth_jd = _julian_day_ut(birth.astimezone(_UTC))
    birth_sun, _ = _sun_longitude_speed(birth_jd)

    # Anchor = birth-MD start: Sun retreated elapsed_years * 360 deg from birth.
    anchor_jd = _solve_transit(birth_jd, birth_sun, -elapsed_years * 360.0)
    anchor_lon, _ = _sun_longitude_speed(anchor_jd)

    boundary_cache: dict[float, datetime] = {}

    def at(cumulative_years: float) -> datetime:
        cached = boundary_cache.get(cumulative_years)
        if cached is None:
            jd = _solve_transit(anchor_jd, anchor_lon, cumulative_years * 360.0)
            cached = _from_jd_ut(jd, tz)
            boundary_cache[cumulative_years] = cached
        return cached

    # Descend the four levels along the active path only.
    result: dict[str, DashaLevel] = {}
    order_lord = birth_lord
    start_cum = 0.0
    span_years = float(TOTAL_DASHA_YEARS)
    for level in _LEVELS:
        lord, child_start, child_span, start_dt, end_dt = _descend(
            order_lord, start_cum, span_years, at, target
        )
        result[level] = DashaLevel(level, lord, start_dt, end_dt)
        # The chosen child becomes the parent for the next (deeper) level.
        order_lord = lord
        start_cum = child_start
        span_years = child_span

    def render(dl: DashaLevel) -> dict:
        return {
            "lord": dl.lord,
            "start": dl.start.isoformat(),
            "end": dl.end.isoformat(),
        }

    return {
        "birth_balance_lord": birth_lord,
        "birth_balance_years": balance_years,
        "target": target.isoformat(),
        "maha": render(result["MD"]),
        "antar": render(result["AD"]),
        "pratyantar": render(result["PD"]),
        "sookshma": render(result["SD"]),
    }
