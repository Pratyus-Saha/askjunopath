"""Transit window engine (T8) — domain-aware Gochara contact windows.

Given an assembled chart payload and a life ``domain`` (career / finance /
relationship), this engine scans the slow- and fast-moving transit (gochara)
planets over a date range and returns the few date windows where transits make
the densest contact with the chart's domain-relevant natal points. It is a pure
read-over-the-chart engine: it imports **no** other engine (it reads everything
it needs — longitudes, cusps, KP sub-lords, dasha lords, and significators —
straight from the chart dict) and never mutates the chart.

Swiss Ephemeris configuration is the locked KP convention used everywhere else
in the project (``ephemeris_engine.py`` / ``dasha_engine.py``): sidereal zodiac,
KP-Newcomb / Krishnamurti ayanamsa, true node, computed with
``FLG_SIDEREAL | FLG_SPEED``. The ephemeris path is the same ``SE_EPHE_PATH``
environment variable.

Contact-point model (domain-aware)
----------------------------------
For a domain the natal points scanned are:

1. **Cusp longitudes** of the domain's primary and supporting houses.
2. **Natal planet longitudes** of every planet whose *node-aware significators*
   (``planets[].significator_of_houses``) touch any house in the domain's
   primary, supporting, **or** blocking groups. This is the KP-faithful contact
   rule: a planet is relevant to a domain because it *signifies* a house of that
   domain, not merely because it sits in one. (Founder direction: the earlier
   "planets occupying primary/supporting houses" rule missed natal points that
   are domain-relevant purely through significators — e.g. a planet whose only
   domain link is an 8th/12th blocking signification.)
3. **Natal longitudes of the current dasha lords** (MD / AD / PD) read from
   ``chart["dashas"]["current"]``.
4. **Natal longitudes of the primary houses' KP cusp sub-lords**
   (``houses[h]["kp"]["sub_lord"]`` resolved to that planet's natal longitude).

The same natal point reached by several rules is a single contact point.

Window model
------------
Each transit planet is stepped across the scan range at its own cadence; every
step that lands within the planet's orb of a contact point is a *raw trigger*.
Raw triggers within 7 days of each other chain into a window candidate. A
candidate survives only if it carries >=2 triggers (or a single trigger that is
the PD lord landing on a primary cusp sub-lord) and at least one non-Moon
trigger (the Moon never forms a window alone). Overlapping candidates merge;
candidates longer than 30 days are tightened (orbs shrink 0.25 deg, floor 0.25)
and rescanned up to three times, then split at their sparsest point. Windows are
scored by contact weight and tightness, get a 1.3x bonus when they fall inside a
supporting pratyantardasha period, and the best three (>=7 days apart) are
returned. The engine never raises for an empty result — it returns ``[]``.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

import swisseph as swe

# ---------------------------------------------------------------------------
# Locked tables
# ---------------------------------------------------------------------------

# Domain -> house groups (T8 spec). Blocking houses participate in contact
# selection (rule 2) but never contribute cusp contacts (rule 1).
DOMAIN_HOUSES: dict[str, dict[str, list[int]]] = {
    "career": {"primary": [10], "supporting": [2, 6, 11], "blocking": [5, 9, 12]},
    "finance": {"primary": [2, 11], "supporting": [6, 10], "blocking": [8, 12, 5]},
    "relationship": {"primary": [7], "supporting": [2, 5, 11], "blocking": [6, 8, 12]},
}

# Transit planet -> (base orb deg, weight, step days). Fixed iteration order so
# output is deterministic regardless of dict ordering.
TRANSIT_PLANETS: tuple[tuple[str, float, int, int], ...] = (
    ("Jupiter", 1.0, 3, 3),
    ("Saturn", 1.0, 3, 3),
    ("Rahu", 1.0, 3, 3),
    ("Ketu", 1.0, 3, 3),
    ("Mars", 1.5, 2, 1),
    ("Venus", 1.5, 2, 1),
    ("Sun", 1.0, 1, 1),
    ("Mercury", 1.0, 1, 1),
    ("Moon", 1.0, 1, 1),
)

# Rahu uses the true node per D002; Ketu is derived as Rahu + 180 deg.
_SWE_BODY_IDS: dict[str, int] = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
    "Rahu": swe.TRUE_NODE,
}

_ALWAYS_RETROGRADE = frozenset({"Rahu", "Ketu"})
_MOON = "Moon"

# Same calc flags as the ephemeris engine, minus the geometric/combustion-only
# extras: sidereal longitude with speed (speed is read so retrograde is implicit
# in the position stream; Rahu/Ketu are forced retrograde by convention above).
_CALC_FLAGS = swe.FLG_SIDEREAL | swe.FLG_SPEED

# Window-construction constants (T8 spec).
_GROUP_GAP_DAYS = 7
_RETRO_DEDUP_DAYS = 14
_MAX_WINDOW_DAYS = 30
_ORB_FLOOR = 0.25
_ORB_TIGHTEN_STEP = 0.25
_MAX_TIGHTEN_PASSES = 3
_PD_OVERLAP_BONUS = 1.3
_TOP_N = 3
_MIN_SEPARATION_DAYS = 7


# ---------------------------------------------------------------------------
# Swiss ephemeris helpers (locked KP config, same SE_EPHE_PATH as the engines)
# ---------------------------------------------------------------------------

def _init_swe() -> None:
    """Apply the locked KP Swiss Ephemeris configuration before any calc.

    Path first, then sidereal mode (docs/ephemeris.md section 2). Re-applied at
    every entry so a sidereal-mode change elsewhere in the process cannot leak
    into the scan.
    """
    swe.set_ephe_path(os.getenv("SE_EPHE_PATH", "/app/ephe"))
    swe.set_sid_mode(swe.SIDM_KRISHNAMURTI, 0, 0)


def _julian_day(scan_date: date) -> float:
    """Julian day (UT) for a scan date, matching dasha_engine's julday call."""
    return swe.julday(scan_date.year, scan_date.month, scan_date.day, 0.0, swe.GREG_CAL)


def _transit_longitude(planet: str, jd: float) -> float:
    """Sidereal longitude of a transit planet in [0, 360).

    Ketu is Rahu's true-node longitude + 180 deg (D002); all others come
    straight from ``swe.calc_ut`` (``xx[0]`` is the longitude, exactly as the
    ephemeris engine reads it).
    """
    if planet == "Ketu":
        xx, _retflag = swe.calc_ut(jd, swe.TRUE_NODE, _CALC_FLAGS)
        return (xx[0] + 180.0) % 360.0
    xx, _retflag = swe.calc_ut(jd, _SWE_BODY_IDS[planet], _CALC_FLAGS)
    return xx[0] % 360.0


def _angular_diff(lon_a: float, lon_b: float) -> float:
    """Shortest angular separation between two longitudes, in [0, 180]."""
    d = abs(lon_a - lon_b) % 360.0
    return min(d, 360.0 - d)


# ---------------------------------------------------------------------------
# Contact-point construction (pure; reads the chart dict)
# ---------------------------------------------------------------------------

def _build_contact_points(chart: dict, groups: dict[str, list[int]]) -> dict[str, float]:
    """Return ``{point_name: natal_longitude}`` for a domain (deduped by name)."""
    primary = groups["primary"]
    supporting = groups["supporting"]
    relevant_houses = set(primary) | set(supporting) | set(groups["blocking"])

    planets = chart.get("planets", []) or []
    houses = chart.get("houses", []) or []
    planet_by_name = {p["name"]: p for p in planets}
    house_by_num = {h["house"]: h for h in houses}

    contacts: dict[str, float] = {}

    # Rule 1 — cusp longitudes of primary + supporting houses.
    for house_number in list(primary) + list(supporting):
        house = house_by_num.get(house_number)
        if house is not None:
            contacts[f"cusp_{house_number}"] = float(house["cusp_longitude"])

    # Rule 2 — natal planets whose significators touch any domain house.
    for planet in planets:
        signifies = set(planet.get("significator_of_houses") or [])
        if signifies & relevant_houses:
            contacts[f"natal_{planet['name'].lower()}"] = float(planet["longitude"])

    # Rule 3 — current dasha lords (MD / AD / PD).
    for lord in _current_dasha_lords(chart):
        planet = planet_by_name.get(lord)
        if planet is not None:
            contacts[f"natal_{lord.lower()}"] = float(planet["longitude"])

    # Rule 4 — KP cusp sub-lords of the primary houses.
    for house_number in primary:
        house = house_by_num.get(house_number)
        if house is None:
            continue
        sub_lord = (house.get("kp") or {}).get("sub_lord")
        planet = planet_by_name.get(sub_lord)
        if planet is not None:
            contacts[f"natal_{sub_lord.lower()}"] = float(planet["longitude"])

    return contacts


def _current_dasha_lords(chart: dict) -> list[str]:
    """The current MD / AD / PD lord names, or [] if no dasha block is present."""
    dashas = chart.get("dashas")
    if not dashas:
        return []
    current = dashas.get("current") or {}
    lords: list[str] = []
    for level in ("mahadasha", "antardasha", "pratyantardasha"):
        period = current.get(level)
        if period and period.get("lord"):
            lords.append(period["lord"])
    return lords


def _primary_sublord_points(chart: dict, groups: dict[str, list[int]]) -> set[str]:
    """Contact-point names of the primary houses' KP cusp sub-lords."""
    houses = chart.get("houses", []) or []
    house_by_num = {h["house"]: h for h in houses}
    points: set[str] = set()
    for house_number in groups["primary"]:
        house = house_by_num.get(house_number)
        if house is None:
            continue
        sub_lord = (house.get("kp") or {}).get("sub_lord")
        if sub_lord:
            points.add(f"natal_{sub_lord.lower()}")
    return points


def _pd_lord(chart: dict) -> str | None:
    dashas = chart.get("dashas")
    if not dashas:
        return None
    pd = (dashas.get("current") or {}).get("pratyantardasha")
    return pd["lord"] if pd and pd.get("lord") else None


def _supporting_pd_periods(chart: dict, groups: dict[str, list[int]]) -> list[tuple[date, date]]:
    """Date ranges of pratyantardasha periods whose lord signifies a supporting house.

    Reads the current PD plus any ``upcoming_pd`` periods. A window earns the PD
    overlap bonus when it falls entirely inside one of these ranges.
    """
    dashas = chart.get("dashas")
    if not dashas:
        return []
    supporting = set(groups["supporting"])
    sig_by_name = {
        p["name"]: set(p.get("significator_of_houses") or [])
        for p in chart.get("planets", []) or []
    }

    periods: list[tuple[date, date]] = []

    def consider(lord: str | None, start: Any, end: Any) -> None:
        if lord and (sig_by_name.get(lord, set()) & supporting):
            periods.append((start, end))

    current_pd = (dashas.get("current") or {}).get("pratyantardasha")
    if current_pd:
        consider(current_pd.get("lord"), current_pd.get("start"), current_pd.get("end"))
    for period in dashas.get("upcoming_pd", []) or []:
        consider(period.get("pd"), period.get("start"), period.get("end"))
    return periods


# ---------------------------------------------------------------------------
# Scanning and window construction
# ---------------------------------------------------------------------------

def _scan_triggers(
    contacts: dict[str, float],
    start_date: date,
    scan_days: int,
    tighten_passes: int,
) -> list[dict[str, Any]]:
    """Step every transit planet across the range, recording in-orb raw triggers.

    ``tighten_passes`` shrinks every orb by 0.25 deg per pass (floored at 0.25)
    for the >30-day re-scan loop. Retrograde nodes deduplicate repeat contacts
    on the same point within 14 days.
    """
    triggers: list[dict[str, Any]] = []
    for name, base_orb, weight, step in TRANSIT_PLANETS:
        orb = max(base_orb - _ORB_TIGHTEN_STEP * tighten_passes, _ORB_FLOOR)
        retrograde = name in _ALWAYS_RETROGRADE
        last_kept: dict[str, date] = {}
        day = 0
        while day < scan_days:
            scan_date = start_date + timedelta(days=day)
            longitude = _transit_longitude(name, _julian_day(scan_date))
            for point_name, natal_longitude in contacts.items():
                diff = _angular_diff(longitude, natal_longitude)
                if diff > orb:
                    continue
                if retrograde:
                    previous = last_kept.get(point_name)
                    if previous is not None and (scan_date - previous).days < _RETRO_DEDUP_DAYS:
                        continue
                    last_kept[point_name] = scan_date
                triggers.append(
                    {
                        "planet": name,
                        "natal_point": point_name,
                        "natal_point_longitude": natal_longitude,
                        "date": scan_date,
                        "angular_diff_deg": diff,
                        "weight": weight,
                    }
                )
            day += step
    return triggers


def _group_triggers(triggers: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Chain raw triggers within 7 days of each other into window candidates."""
    if not triggers:
        return []
    ordered = sorted(triggers, key=lambda t: t["date"])
    groups: list[list[dict[str, Any]]] = [[ordered[0]]]
    for trigger in ordered[1:]:
        if (trigger["date"] - groups[-1][-1]["date"]).days <= _GROUP_GAP_DAYS:
            groups[-1].append(trigger)
        else:
            groups.append([trigger])
    return groups


def _candidate_survives(
    group: list[dict[str, Any]],
    pd_lord: str | None,
    primary_sublord_points: set[str],
) -> bool:
    """Keep rule: >=2 triggers (or the PD-lord-on-primary-sublord single), and
    at least one non-Moon trigger (the Moon never forms a window alone)."""
    if not any(t["planet"] != _MOON for t in group):
        return False
    if len(group) >= 2:
        return True
    only = group[0]
    return (
        pd_lord is not None
        and only["planet"] == pd_lord
        and only["natal_point"] in primary_sublord_points
    )


def _span_days(group: list[dict[str, Any]]) -> int:
    dates = [t["date"] for t in group]
    return (max(dates) - min(dates)).days


def _merge_overlapping(groups: list[list[dict[str, Any]]]) -> list[list[dict[str, Any]]]:
    """Merge candidates whose date spans overlap (post-grouping safety net)."""
    if not groups:
        return []
    intervals = sorted(
        ((min(t["date"] for t in g), max(t["date"] for t in g), list(g)) for g in groups),
        key=lambda item: item[0],
    )
    merged: list[list[Any]] = [list(intervals[0])]
    for start, end, group in intervals[1:]:
        prev_start, prev_end, prev_group = merged[-1]
        if start <= prev_end:
            merged[-1][1] = max(prev_end, end)
            merged[-1][2] = prev_group + group
        else:
            merged.append([start, end, group])
    return [item[2] for item in merged]


def _enforce_max_span(
    groups: list[list[dict[str, Any]]],
    pd_lord: str | None,
    primary_sublord_points: set[str],
) -> list[list[dict[str, Any]]]:
    """Split any >30-day candidate at its sparsest internal gap until all fit.

    Split fragments are re-checked against the keep rule so a fragment can never
    re-enter as a sub-threshold window. Terminates because each split strictly
    shrinks the fragment.
    """
    result: list[list[dict[str, Any]]] = []
    stack = [list(g) for g in groups]
    while stack:
        group = stack.pop()
        if _span_days(group) <= _MAX_WINDOW_DAYS:
            result.append(group)
            continue
        ordered = sorted(group, key=lambda t: t["date"])
        split_at, widest = 0, -1
        for i in range(len(ordered) - 1):
            gap = (ordered[i + 1]["date"] - ordered[i]["date"]).days
            if gap > widest:
                widest, split_at = gap, i
        for fragment in (ordered[: split_at + 1], ordered[split_at + 1:]):
            if _candidate_survives(fragment, pd_lord, primary_sublord_points):
                stack.append(fragment)
    return result


# ---------------------------------------------------------------------------
# Scoring and selection
# ---------------------------------------------------------------------------

def _score_window(
    group: list[dict[str, Any]],
    supporting_pd_periods: list[tuple[date, date]],
) -> tuple[float, bool, date, date]:
    """``sum(distinct contact weights) * (1 - length/30)``, x1.3 inside a
    supporting PD period.

    Weight is summed over distinct ``(planet, natal_point)`` contacts rather than
    every daily step, so a slow planet dwelling on one point is not double-counted
    by its step cadence; ``trigger_count`` (the >=2 keep gate) still reflects the
    raw step triggers.
    """
    dates = [t["date"] for t in group]
    start, end = min(dates), max(dates)
    length = (end - start).days

    distinct_weight: dict[tuple[str, str], int] = {}
    for trigger in group:
        distinct_weight[(trigger["planet"], trigger["natal_point"])] = trigger["weight"]
    score = sum(distinct_weight.values()) * (1.0 - length / _MAX_WINDOW_DAYS)

    pd_overlap = any(start >= ps and end <= pe for ps, pe in supporting_pd_periods)
    if pd_overlap:
        score *= _PD_OVERLAP_BONUS
    return score, pd_overlap, start, end


def _separated(window_a: dict[str, Any], window_b: dict[str, Any]) -> bool:
    """True if two windows are >=7 days apart (and non-overlapping)."""
    if window_a["end_date"] < window_b["start_date"]:
        gap = (window_b["start_date"] - window_a["end_date"]).days
    elif window_b["end_date"] < window_a["start_date"]:
        gap = (window_a["start_date"] - window_b["end_date"]).days
    else:
        return False
    return gap >= _MIN_SEPARATION_DAYS


def _select_top(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Greedily take the highest-scoring windows that stay >=7 days apart."""
    selected: list[dict[str, Any]] = []
    for window in sorted(windows, key=lambda w: w["window_score"], reverse=True):
        if all(_separated(window, chosen) for chosen in selected):
            selected.append(window)
        if len(selected) == _TOP_N:
            break
    return selected


def _format_window(window: dict[str, Any]) -> dict[str, Any]:
    """Serialize an internal window (date objects) into the output dict."""
    return {
        "start_date": window["start_date"].isoformat(),
        "end_date": window["end_date"].isoformat(),
        "domain": window["domain"],
        "window_score": round(window["window_score"], 2),
        "pd_overlap": window["pd_overlap"],
        "trigger_count": window["trigger_count"],
        "triggers": [
            {
                "planet": trigger["planet"],
                "natal_point": trigger["natal_point"],
                "natal_point_longitude": round(trigger["natal_point_longitude"], 2),
                "contact_date": trigger["date"].isoformat(),
                "angular_diff_deg": round(trigger["angular_diff_deg"], 2),
                "weight": trigger["weight"],
            }
            for trigger in sorted(window["triggers"], key=lambda t: (t["date"], t["planet"]))
        ],
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_transit_windows(
    chart: dict,
    domain: str,
    start_date: date = None,
    scan_days: int = 90,
) -> list[dict]:
    """Return up to three domain-relevant transit windows for ``chart``.

    Args:
        chart: assembled chart payload (read-only). Reads ``planets`` (name,
            longitude, ``significator_of_houses``), ``houses`` (cusp_longitude,
            ``kp.sub_lord``) and, when present, ``dashas.current`` /
            ``dashas.upcoming_pd``.
        domain: ``"career"``, ``"finance"`` or ``"relationship"``. Any other
            value yields ``[]`` (never raises).
        start_date: first scan date; defaults to today.
        scan_days: number of days to scan from ``start_date``.

    Returns a list (length 0..3) of window dicts sorted by descending score.
    Never raises for an empty result.
    """
    if start_date is None:
        start_date = date.today()

    groups = DOMAIN_HOUSES.get(domain)
    if groups is None:
        return []

    contacts = _build_contact_points(chart, groups)
    if not contacts:
        return []

    pd_lord = _pd_lord(chart)
    primary_sublord_points = _primary_sublord_points(chart, groups)
    supporting_pd_periods = _supporting_pd_periods(chart, groups)

    _init_swe()

    # Scan, tightening orbs while any merged candidate runs longer than 30 days.
    candidates: list[list[dict[str, Any]]] = []
    for tighten_passes in range(_MAX_TIGHTEN_PASSES + 1):
        triggers = _scan_triggers(contacts, start_date, scan_days, tighten_passes)
        survivors = [
            group
            for group in _group_triggers(triggers)
            if _candidate_survives(group, pd_lord, primary_sublord_points)
        ]
        candidates = _merge_overlapping(survivors)
        if all(_span_days(group) <= _MAX_WINDOW_DAYS for group in candidates):
            break

    # Final guarantee: split anything still over 30 days at its sparsest gap.
    candidates = _enforce_max_span(candidates, pd_lord, primary_sublord_points)

    windows: list[dict[str, Any]] = []
    for group in candidates:
        score, pd_overlap, start, end = _score_window(group, supporting_pd_periods)
        windows.append(
            {
                "start_date": start,
                "end_date": end,
                "domain": domain,
                "window_score": score,
                "pd_overlap": pd_overlap,
                "trigger_count": len(group),
                "triggers": group,
            }
        )

    return [_format_window(window) for window in _select_top(windows)]
