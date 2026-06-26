"""Internal finance prediction (Block 4) — deterministic KP evidence engine.

Like the career engine, this answers "what does the chart + current dasha +
near-term transits say about *finances*, and *why*" as a structured,
evidence-first object. It is **internal only**:

* it reads an already-computed chart payload read-only and mutates nothing;
* it is **not** imported by any router and populates **no** public field;
* it **does not call any LLM** — ``summary`` is templated from the evidence.

Model. KP separates *promise* from *timing*, and we add a transit layer:

* **Promise** — the 2nd and 11th cusp sub-lords and the houses they signify
  (read straight from each planet's ``significator_of_houses``). Promise is met
  when either of those sub-lords signifies a supportive finance house
  (2 income, 6 dues/service, 10 profession/standing, 11 gains). A sub-lord that
  *primarily* signifies blocking houses (8 loss, 12 outflow) raises a caution
  flag and reframes the summary toward "caution and review".
* **Dasha timing** — the current MD/AD/PD lords (read from
  ``chart["dashas"]["current"]``) and whether each signifies a supportive
  finance house. The stack "supports" finance when at least two of the three
  lords do.
* **Transit timing** — domain-aware Gochara windows from ``transit_engine`` and a
  forward "next contact" estimate, both for the finance domain.

Confidence (finance may reach "high", unlike the v1 career cap):

    promise_met AND dasha_supports AND slow-planet window   -> "high"
    promise_met AND dasha_supports AND no slow-planet window -> "medium"
    promise_met AND dasha_weak     AND any transit window    -> "medium"
    promise_met AND dasha_weak     AND no transit window      -> "low"
    NOT promise_met                                           -> "low"

``signal_strength`` (0-100) describes *factor convergence*, not probability — it
is labelled "signal strength", never "likelihood".

Safe language. The summary is templated, never free-generated, and deliberately
avoids market and trading vocabulary. It speaks only of inflow / outflow periods,
dues-recovery, and financial decisions deserving slower review — never of markets,
holdings, or trading actions. A source scan for that vocabulary is part of the
test suite.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.engines.transit_engine import compute_transit_windows, find_next_contact

VERSION = "finance-v1"
DOMAIN = "finance"

# KP house groups for the finance domain (T8 / Block 4).
PRIMARY_HOUSES: list[int] = [2, 11]
SUPPORTING_HOUSES: list[int] = [6, 10]
BLOCKING_HOUSES: list[int] = [8, 12, 5]

# Promise + dasha-support set = primary ∪ supporting (the favourable finance houses).
SUPPORT_SET: tuple[int, ...] = (2, 6, 10, 11)
# A cusp sub-lord "primarily signifies [8, 12]" -> caution.
CAUTION_HOUSES: tuple[int, ...] = (8, 12)
# The 2nd AND 11th cusp sub-lords gate the promise.
CHECKED_CUSP_HOUSES: tuple[int, ...] = (2, 11)

# Slow transit bodies — a window carrying one of these is a "slow-planet window".
SLOW_PLANETS: tuple[str, ...] = ("Jupiter", "Saturn", "Rahu", "Ketu")
_SCAN_DAYS = 90

# Allowed event-type labels for finance windows (templated, never free text).
EVENT_INCOME = "income-rise window"
EVENT_EXPENSE = "large-expense caution span"
EVENT_DUES = "dues-recovery window"
EVENT_REVIEW = "financial-decision review window"


def _significations(chart: Mapping[str, Any]) -> dict[str, list[int]]:
    """planet name -> its signified houses, read straight from the chart dict."""
    out: dict[str, list[int]] = {}
    for planet in chart.get("planets", []) or []:
        out[planet["name"]] = sorted(
            int(h) for h in (planet.get("significator_of_houses") or [])
        )
    return out


def _supports(lord: str | None, sig: Mapping[str, list[int]]) -> bool:
    """True when ``lord`` signifies any favourable finance house."""
    return bool(lord and (set(sig.get(lord, [])) & set(SUPPORT_SET)))


def _transit_framing(
    transit_windows: list[dict[str, Any]],
    slow_planet_window: bool,
    next_contact: dict[str, Any],
) -> str:
    """A short, always-non-empty human framing of the transit picture."""
    if slow_planet_window:
        return (
            "A slow-planet contact window is active in the scanned span, so the "
            "transit timing signal is at its strongest here."
        )
    if transit_windows:
        return (
            "Only fast-planet contact windows form in the scanned span, so the "
            "transit timing signal is light and short-lived."
        )
    planet = next_contact.get("planet")
    estimated = next_contact.get("estimated_date")
    if planet and estimated:
        return (
            "No contact windows form in the scanned span; the next slow-planet "
            f"contact ({planet}) is estimated around {estimated}."
        )
    return "No contact windows form in the scanned span."


def _build_summary(
    *,
    as_of: datetime,
    dasha_timing: Mapping[str, Any],
    promise_met: bool,
    caution_flag: bool,
    transit_windows: list[dict[str, Any]],
    slow_planet_window: bool,
) -> str:
    """Templated, hedged finance summary. No LLM, no banned market vocabulary."""
    md = dasha_timing["md_lord"]
    ad = dasha_timing["ad_lord"]
    pd = dasha_timing["pd_lord"]
    parts: list[str] = [
        f"As of {as_of.date().isoformat()}, the active Vimshottari stack is "
        f"{md} (mahadasha) > {ad} (antardasha) > {pd} (pratyantardasha)."
    ]

    if promise_met and not caution_flag:
        parts.append(
            "The 2nd and 11th cusp sub-lords signify supportive financial houses, "
            "so inflow indications strengthen across this period."
        )
    elif caution_flag:
        parts.append(
            "The 2nd and 11th cusp sub-lords lean toward blocking houses, so this "
            "reads more as an outflow period: financial decisions deserve slower "
            "review and added caution."
        )
    else:
        parts.append(
            "The 2nd and 11th cusp sub-lords do not clearly signify supportive "
            "financial houses, so the inflow signal stays muted."
        )

    if transit_windows and slow_planet_window:
        parts.append(
            "A slow-planet transit window strengthens the timing signal and may "
            "mark an inflow period or a dues-recovery window, not an exact event."
        )
    elif transit_windows:
        parts.append(
            "Lighter transit contact windows form, which may colour the timing but "
            "carry less weight."
        )
    else:
        parts.append(
            "No close transit contact windows form in the scanned span, so timing "
            "stays at the dasha-period level."
        )

    if caution_flag:
        parts.append(
            "Given these caution signals, treat any financial decisions with slower "
            "review."
        )

    parts.append(
        "This is reflective guidance based on KP significators and Vimshottari "
        "timing, not a guarantee of any specific outcome, and not financial advice."
    )
    return " ".join(parts)


def compute_finance_prediction(
    chart: Mapping[str, Any],
    *,
    as_of: datetime,
) -> dict[str, Any]:
    """Compute the internal finance evidence object for ``chart`` as of ``as_of``.

    ``as_of`` must be timezone-aware; its date anchors the (deterministic) transit
    scan. The input chart is not mutated and no public field is populated. Returns
    a JSON-serializable dict carrying the unified prediction contract.
    """
    if as_of.tzinfo is None:
        raise ValueError("`as_of` must be timezone-aware")

    houses = chart["houses"]
    houses_by_num = {house["house"]: house for house in houses}
    sig = _significations(chart)

    # ---- Promise: the 2nd AND 11th cusp sub-lords ----------------------------
    primary_sublords: dict[str, str] = {}
    sublord_significations: dict[str, list[int]] = {}
    promise_hits: list[int] = []
    caution_flag = False
    for house_number in CHECKED_CUSP_HOUSES:
        sub_lord = houses_by_num[house_number]["kp"]["sub_lord"]
        signifies = sig.get(sub_lord, [])
        primary_sublords[str(house_number)] = sub_lord
        sublord_significations[sub_lord] = signifies
        favourable = sorted(set(signifies) & set(SUPPORT_SET))
        blocking = sorted(set(signifies) & set(CAUTION_HOUSES))
        if favourable:
            promise_hits.extend(favourable)
        # "primarily signifies [8, 12]": blocking present, no favourable offset.
        if blocking and not favourable:
            caution_flag = True
    promise_met = bool(promise_hits)

    cusp_sublords = {
        "primary_houses": primary_sublords,
        "sublord_significations": sublord_significations,
    }

    # ---- Dasha timing (read straight from chart.dashas.current) ---------------
    current = (chart.get("dashas") or {}).get("current") or {}
    md_lord = current.get("md_lord")
    ad_lord = current.get("ad_lord")
    pd_lord = current.get("pd_lord")
    md_supports = _supports(md_lord, sig)
    ad_supports = _supports(ad_lord, sig)
    pd_supports = _supports(pd_lord, sig)
    dasha_supports = (md_supports + ad_supports + pd_supports) >= 2
    blocking_dasha = any(
        set(sig.get(lord, [])) & set(BLOCKING_HOUSES)
        for lord in (md_lord, ad_lord, pd_lord)
        if lord
    )
    dasha_timing = {
        "md_lord": md_lord,
        "ad_lord": ad_lord,
        "pd_lord": pd_lord,
        "md_supports": md_supports,
        "ad_supports": ad_supports,
        "pd_supports": pd_supports,
    }

    # ---- Transit timing (deterministic: scan anchored at as_of) --------------
    transit_windows = (
        compute_transit_windows(
            chart, DOMAIN, start_date=as_of.date(), scan_days=_SCAN_DAYS
        )
        or []
    )
    slow_planet_window = any(
        any(trigger["planet"] in SLOW_PLANETS for trigger in window["triggers"])
        for window in transit_windows
    )
    next_contact = find_next_contact(chart, DOMAIN)
    transit_summary = {
        "windows_found": len(transit_windows),
        "has_slow_planet_contact": slow_planet_window,
        "next_contact": next_contact,
        "framing": _transit_framing(transit_windows, slow_planet_window, next_contact),
    }

    # ---- Confidence (finance may reach "high") -------------------------------
    if not promise_met:
        confidence = "low"
    elif dasha_supports:
        confidence = "high" if slow_planet_window else "medium"
    else:
        confidence = "medium" if transit_windows else "low"

    # ---- signal_strength: factor convergence (0-100), NOT a probability ------
    supporting_lords = md_supports + ad_supports + pd_supports
    signal_strength = 0
    if promise_met:
        signal_strength += 30
    signal_strength += 10 * supporting_lords
    if slow_planet_window:
        signal_strength += 20
    if transit_windows:
        signal_strength += 10
    if promise_met and not caution_flag:
        signal_strength += 10
    signal_strength = max(0, min(100, signal_strength))

    # ---- Event types (templated labels only) ---------------------------------
    event_types: list[str] = []
    if promise_met and dasha_supports and slow_planet_window:
        event_types.append(EVENT_INCOME)
    elif promise_met and (transit_windows or dasha_supports):
        event_types.append(EVENT_DUES)
    if caution_flag or blocking_dasha:
        event_types.append(EVENT_EXPENSE)
    event_types.append(EVENT_REVIEW)

    summary = _build_summary(
        as_of=as_of,
        dasha_timing=dasha_timing,
        promise_met=promise_met,
        caution_flag=caution_flag,
        transit_windows=transit_windows,
        slow_planet_window=slow_planet_window,
    )

    return {
        "domain": DOMAIN,
        "promise_met": promise_met,
        "confidence": confidence,
        "signal_strength": signal_strength,
        "caution_flag": caution_flag,
        "dasha_timing": dasha_timing,
        "transit_windows": transit_windows,
        "transit_summary": transit_summary,
        "event_types": event_types,
        "summary": summary,
        "cusp_sublords": cusp_sublords,
    }
