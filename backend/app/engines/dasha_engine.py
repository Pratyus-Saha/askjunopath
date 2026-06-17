"""Internal Vimshottari dasha engine (true tropical solar years).

Spec: docs/dasha.md. This engine is **internal only** (D023/D027): it returns a
plain timeline object and never touches the public chart payload. The public
``chart.dashas`` field stays ``null``; the chart router does not call this
engine, and no schema or engine version changes.

Convention (locked, docs/dasha.md)
----------------------------------
* **Order** — the Vimshottari sequence ``Ketu, Venus, Sun, Moon, Mars, Rahu,
  Jupiter, Saturn, Mercury`` with the year counts below, summing to 120.
* **Started from Moon** — the birth mahadasha lord is the Moon's nakshatra lord
  (read from the existing chart Moon nakshatra block; the Moon is never
  recomputed here). The birth-MD *balance* is
  ``MD_years * (NAK_SPAN - moon_degree_in_nakshatra) / NAK_SPAN``.
* **True tropical solar years** — JHora's screenshot setting. A dasha boundary
  at cumulative time ``T`` years from the (back-projected) birth-MD start is the
  instant the **true/geometric tropical Sun** has advanced ``T * 360 deg`` from
  its longitude at that start. Because the Sun's apparent speed varies, each
  "solar year" has a slightly different length — this is the whole point of
  *true* tropical solar years, and a single fixed-day constant cannot reproduce
  JHora's table (it is off by ~2.5 days at PD level). ``MEAN_TROPICAL_YEAR_DAYS``
  is only the mean year used to seed the transit solver, never a period length.
* **Nesting** — antardashas subdivide their mahadasha in proportion
  ``MD_years * AD_years / 120``; pratyantardashas subdivide their antardasha in
  proportion ``AD_span * PD_years / 120``. AD/PD orders start with their parent
  lord and proceed in Vimshottari order.
* **Boundaries** — start-inclusive, end-exclusive: an exact boundary timestamp
  belongs to the new (next) period.
* **Timezone** — boundaries are computed on a continuous (UTC/Julian) time scale
  and rendered in the birth timezone for display and comparison (Asia/Kolkata
  for the User 1 fixture). India has no DST, so this is exact there; for DST
  zones the continuous scale is the defined convention.

The judge is ``tests/fixtures/jhora/dasha_expected.json`` (AGENTS.md Rule 8).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any
from zoneinfo import ZoneInfo

import swisseph as swe

# ---------------------------------------------------------------------------
# Locked constants
# ---------------------------------------------------------------------------

# Vimshottari lord sequence (matches the nakshatra lord cycle in docs/nakshatra.md).
VIMSHOTTARI_ORDER: tuple[str, ...] = (
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn",
    "Mercury",
)

# Dasha years per lord; they sum to the 120-year cycle.
DASHA_YEARS: dict[str, int] = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17,
}

TOTAL_DASHA_YEARS = 120

# One nakshatra spans 13 deg 20 min = 13.333... deg (docs/nakshatra.md).
NAKSHATRA_SPAN_DEG = 13.0 + 20.0 / 60.0

# Mean tropical year, in days. Used ONLY to seed the Sun-transit solver and as a
# documented reference value — it is NOT used as a period length. The true
# period lengths come from real Sun transits (see module docstring / docs/dasha.md).
MEAN_TROPICAL_YEAR_DAYS = 365.2425

# True/geometric tropical Sun: Swiss ephemeris, with speed, TRUE position, and
# NO sidereal flag (tropical longitude). FLG_TRUEPOS matches the ephemeris
# engine's geometric convention; the absence of FLG_SIDEREAL keeps it tropical.
SUN_CALC_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_TRUEPOS

_UTC = dt_timezone.utc


# ---------------------------------------------------------------------------
# Order / balance (pure, no ephemeris)
# ---------------------------------------------------------------------------

def vimshottari_order_from(lord: str) -> list[str]:
    """Rotate the Vimshottari sequence to start at ``lord``.

    Raises ValueError if ``lord`` is not a Vimshottari dasha lord.
    """
    if lord not in DASHA_YEARS:
        raise ValueError(f"{lord!r} is not a Vimshottari dasha lord")
    i = VIMSHOTTARI_ORDER.index(lord)
    return list(VIMSHOTTARI_ORDER[i:]) + list(VIMSHOTTARI_ORDER[:i])


def birth_balance(moon_nakshatra_lord: str, moon_degree_in_nakshatra: float) -> tuple[str, float]:
    """Return (birth MD lord, balance years remaining) from the Moon.

    The birth mahadasha lord IS the Moon's nakshatra lord. The remaining balance
    is ``MD_years * (NAK_SPAN - moon_degree_in_nakshatra) / NAK_SPAN``.
    """
    if moon_nakshatra_lord not in DASHA_YEARS:
        raise ValueError(f"{moon_nakshatra_lord!r} is not a Vimshottari dasha lord")
    if not (0.0 <= moon_degree_in_nakshatra <= NAKSHATRA_SPAN_DEG + 1e-9):
        raise ValueError(
            f"moon_degree_in_nakshatra {moon_degree_in_nakshatra} is outside "
            f"[0, {NAKSHATRA_SPAN_DEG}]"
        )
    md_years = DASHA_YEARS[moon_nakshatra_lord]
    remaining_fraction = (NAKSHATRA_SPAN_DEG - moon_degree_in_nakshatra) / NAKSHATRA_SPAN_DEG
    return moon_nakshatra_lord, md_years * remaining_fraction


# ---------------------------------------------------------------------------
# Swiss ephemeris helpers (tropical true Sun)
# ---------------------------------------------------------------------------

def _init_swe() -> None:
    """Point Swiss Ephemeris at SE_EPHE_PATH (no sidereal mode — we want tropical).

    Mirrors the ephemeris engine's path handling so the dasha engine uses the
    same ``.se1`` files. Sidereal mode is intentionally NOT set: SUN_CALC_FLAGS
    omits FLG_SIDEREAL, so longitudes are tropical regardless.
    """
    ephe_path = os.environ.get("SE_EPHE_PATH")
    swe.set_ephe_path(ephe_path if ephe_path else None)


def _to_jd_ut(aware_dt: datetime) -> float:
    utc_dt = aware_dt.astimezone(_UTC)
    decimal_hour = (
        utc_dt.hour
        + utc_dt.minute / 60.0
        + utc_dt.second / 3600.0
        + utc_dt.microsecond / 3_600_000_000.0
    )
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, decimal_hour, swe.GREG_CAL)


def _from_jd_ut(jd: float, tz: ZoneInfo) -> datetime:
    year, month, day, hour = swe.revjul(jd, swe.GREG_CAL)
    utc_dt = datetime(year, month, day, tzinfo=_UTC) + timedelta(hours=hour)
    # Render whole-second civil time in the birth zone (JHora displays seconds).
    utc_dt = utc_dt.replace(microsecond=0) + timedelta(
        seconds=1 if utc_dt.microsecond >= 500_000 else 0
    )
    return utc_dt.astimezone(tz)


def _sun_longitude_speed(jd: float) -> tuple[float, float]:
    xx, _retflag = swe.calc_ut(jd, swe.SUN, SUN_CALC_FLAGS)
    return xx[0] % 360.0, xx[3]


def _solve_transit(anchor_jd: float, anchor_lon: float, advance_deg: float) -> float:
    """Julian day (UT) at which the true tropical Sun has advanced ``advance_deg``.

    ``advance_deg`` is a signed cumulative angle from ``anchor_lon`` (may exceed
    360 deg or be negative). Newton's method seeded by the mean tropical year
    lands within ~2 days of the target, so the mod-360 residual never crosses a
    revolution and convergence is unambiguous.
    """
    jd = anchor_jd + advance_deg / 360.0 * MEAN_TROPICAL_YEAR_DAYS
    target = (anchor_lon + advance_deg) % 360.0
    for _ in range(60):
        lon, speed = _sun_longitude_speed(jd)
        diff = ((lon - target + 180.0) % 360.0) - 180.0  # signed, in (-180, 180]
        step = diff / speed
        jd -= step
        if abs(step) < 1e-10:
            break
    return jd


# ---------------------------------------------------------------------------
# Timeline data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DashaPeriod:
    """One dasha period. ``level`` is "MD"/"AD"/"PD"; ``lords`` is the chain.

    Boundaries are start-inclusive, end-exclusive (docs/dasha.md).
    """

    level: str
    lords: tuple[str, ...]
    start: datetime
    end: datetime

    @property
    def lord(self) -> str:
        """The deepest (own) lord of this period."""
        return self.lords[-1]

    def contains(self, when: datetime) -> bool:
        return self.start <= when < self.end


@dataclass(frozen=True)
class DashaTimeline:
    """A full Vimshottari timeline: 9 MD, 81 AD, 729 PD from the birth-MD start."""

    birth: datetime
    birth_balance_lord: str
    birth_balance_years: float
    mahadashas: tuple[DashaPeriod, ...]
    antardashas: tuple[DashaPeriod, ...]
    pratyantardashas: tuple[DashaPeriod, ...]

    def _pd_at(self, when: datetime) -> DashaPeriod:
        first = self.pratyantardashas[0]
        last = self.pratyantardashas[-1]
        if not (first.start <= when < last.end):
            raise ValueError(
                f"{when.isoformat()} is outside the computed dasha timeline "
                f"[{first.start.isoformat()}, {last.end.isoformat()})"
            )
        # The PDs tile the whole range contiguously; binary-search their starts.
        lo, hi = 0, len(self.pratyantardashas) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.pratyantardashas[mid].start <= when:
                lo = mid
            else:
                hi = mid - 1
        return self.pratyantardashas[lo]

    def current_stack(self, when: datetime) -> tuple[DashaPeriod, DashaPeriod, DashaPeriod]:
        """Return the (mahadasha, antardasha, pratyantardasha) active at ``when``.

        Raises ValueError if ``when`` falls outside the computed timeline.
        """
        if when.tzinfo is None:
            raise ValueError("`when` must be timezone-aware")
        pd = self._pd_at(when)
        md = next(p for p in self.mahadashas if p.lords == pd.lords[:1])
        ad = next(p for p in self.antardashas if p.lords == pd.lords[:2])
        return md, ad, pd

    def current_lords(self, when: datetime) -> tuple[str, str, str]:
        md, ad, pd = self.current_stack(when)
        return md.lord, ad.lord, pd.lord


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_dasha(
    *,
    moon_nakshatra_lord: str,
    moon_degree_in_nakshatra: float,
    birth: datetime,
) -> DashaTimeline:
    """Compute the full Vimshottari timeline for a birth.

    Args:
        moon_nakshatra_lord: the Moon's nakshatra lord from the chart (the birth
            mahadasha lord). The Moon is never recomputed here.
        moon_degree_in_nakshatra: the Moon's degree within its nakshatra (chart).
        birth: timezone-aware birth datetime. Output boundaries are rendered in
            ``birth.tzinfo``.

    Returns a DashaTimeline. Pure with respect to its inputs; mutates nothing.
    """
    if birth.tzinfo is None:
        raise ValueError("`birth` must be timezone-aware")
    tz = birth.tzinfo

    birth_lord, balance_years = birth_balance(moon_nakshatra_lord, moon_degree_in_nakshatra)
    elapsed_years = DASHA_YEARS[birth_lord] - balance_years  # already-run portion at birth

    _init_swe()
    birth_jd = _to_jd_ut(birth)
    birth_sun, _speed = _sun_longitude_speed(birth_jd)

    # Anchor = birth-MD start: the Sun retreated elapsed_years * 360 deg from birth.
    anchor_jd = _solve_transit(birth_jd, birth_sun, -elapsed_years * 360.0)
    anchor_lon, _ = _sun_longitude_speed(anchor_jd)

    # Cache cumulative-year breakpoint -> rendered datetime. Shared boundaries
    # use the identical cumulative float, so they resolve to the identical
    # datetime, guaranteeing continuity and exact nesting.
    boundary_cache: dict[float, datetime] = {}

    def at(cumulative_years: float) -> datetime:
        cached = boundary_cache.get(cumulative_years)
        if cached is None:
            jd = _solve_transit(anchor_jd, anchor_lon, cumulative_years * 360.0)
            cached = _from_jd_ut(jd, tz)
            boundary_cache[cumulative_years] = cached
        return cached

    mahadashas: list[DashaPeriod] = []
    antardashas: list[DashaPeriod] = []
    pratyantardashas: list[DashaPeriod] = []

    cum = 0.0
    for md in vimshottari_order_from(birth_lord):
        md_start_cum = cum
        for ad in vimshottari_order_from(md):
            ad_start_cum = cum
            ad_span_years = DASHA_YEARS[md] * DASHA_YEARS[ad] / TOTAL_DASHA_YEARS
            for pd in vimshottari_order_from(ad):
                pd_span_years = ad_span_years * DASHA_YEARS[pd] / TOTAL_DASHA_YEARS
                pratyantardashas.append(
                    DashaPeriod("PD", (md, ad, pd), at(cum), at(cum + pd_span_years))
                )
                cum += pd_span_years
            antardashas.append(
                DashaPeriod("AD", (md, ad), at(ad_start_cum), at(cum))
            )
        mahadashas.append(DashaPeriod("MD", (md,), at(md_start_cum), at(cum)))

    return DashaTimeline(
        birth=birth,
        birth_balance_lord=birth_lord,
        birth_balance_years=balance_years,
        mahadashas=tuple(mahadashas),
        antardashas=tuple(antardashas),
        pratyantardashas=tuple(pratyantardashas),
    )


# ---------------------------------------------------------------------------
# Chart adapter (reads the existing Moon nakshatra block; never mutates)
# ---------------------------------------------------------------------------

def _get(obj: Mapping[str, Any] | Any, key: str) -> Any:
    if isinstance(obj, Mapping):
        return obj[key]
    return getattr(obj, key)


def compute_dasha_from_chart(chart: Mapping[str, Any] | Any) -> DashaTimeline:
    """Compute the dasha timeline from an assembled chart payload.

    Reads only the Moon's nakshatra block (``planets[Moon].nakshatra.lord`` and
    ``.degree_in_nakshatra``) and ``birth`` (``datetime_local`` + ``timezone``).
    The Moon is consumed from the chart, never recomputed (docs/dasha.md). The
    chart payload is read-only; nothing is mutated and no public field is set.
    """
    planets = _get(chart, "planets")
    moon = next(p for p in planets if _get(p, "name") == "Moon")
    nakshatra = _get(moon, "nakshatra")

    birth = _get(chart, "birth")
    datetime_local = _get(birth, "datetime_local")
    timezone_name = _get(birth, "timezone")
    birth_dt = datetime.fromisoformat(datetime_local).replace(tzinfo=ZoneInfo(timezone_name))

    return compute_dasha(
        moon_nakshatra_lord=_get(nakshatra, "lord"),
        moon_degree_in_nakshatra=_get(nakshatra, "degree_in_nakshatra"),
        birth=birth_dt,
    )
