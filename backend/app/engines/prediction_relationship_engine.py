"""Internal relationship prediction (Block 5) — deterministic KP evidence engine.

Mirrors the finance engine's internal-only, evidence-first contract for the
*relationship / partnership* domain. It reads an already-computed chart payload
read-only, mutates nothing, is imported by no router, populates no public field,
and calls no LLM — ``summary`` is templated from the evidence.

Model. KP separates *promise* from *timing*, with a transit layer on top:

* **Promise** — the 7th cusp sub-lord and the houses it signifies (read from
  each planet's ``significator_of_houses`` when populated; public
  ``/chart/generate`` payloads keep that field reserved-empty per D023, in which
  case the node-aware significators are recomputed from the base chart, the same
  way the career engine does). Promise is met when the 7th sub-lord signifies a
  supportive partnership house (2 family/support, 5 romance, 7 partnership,
  11 friends/fulfilment). A 7th sub-lord that *primarily* signifies houses of
  friction and separation (6 disputes, 8 obstacles, 12 loss) raises a caution
  flag and reframes the summary toward patience and caution.
* **Dasha timing** — the current MD/AD/PD lords (from ``chart["dashas"]["current"]``
  when present; public payloads keep ``dashas`` null, in which case the current
  Vimshottari stack is recomputed from the base chart) and whether each signifies
  a supportive partnership house. The stack "supports" the domain when at least
  two of the three lords do.
* **Transit timing** — domain-aware Gochara windows from ``transit_engine`` plus a
  forward "next contact" estimate, both for the relationship domain.

Confidence (relationship may reach "high"):

    promise_met AND dasha_supports AND slow-planet window   -> "high"
    promise_met AND dasha_supports AND no slow-planet window -> "medium"
    promise_met AND dasha_weak     AND any transit window    -> "medium"
    promise_met AND dasha_weak     AND no transit window      -> "low"
    NOT promise_met                                           -> "low"

``signal_strength`` (0-100) describes *factor convergence*, not probability — it
is labelled "signal strength", never "likelihood". The summary is templated, never
free-generated, and always hedged.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.engines.dasha_engine import compute_dasha_from_chart
from app.engines.significator_engine import compute_node_aware_significators
from app.engines.transit_engine import compute_transit_windows, find_next_contact

VERSION = "relationship-v1"
DOMAIN = "relationship"

# KP house groups for the relationship domain (T8 / Block 5).
PRIMARY_HOUSES: list[int] = [7]
SUPPORTING_HOUSES: list[int] = [2, 5, 11]
BLOCKING_HOUSES: list[int] = [6, 8, 12]

# Promise + dasha-support set = primary ∪ supporting (favourable partnership houses).
SUPPORT_SET: tuple[int, ...] = (2, 5, 7, 11)
# A 7th cusp sub-lord "primarily signifies" these (friction / separation) -> caution.
CAUTION_HOUSES: tuple[int, ...] = (6, 8, 12)
# Only the 7th cusp sub-lord gates the promise.
CHECKED_CUSP_HOUSES: tuple[int, ...] = (7,)

# Slow transit bodies — a window carrying one of these is a "slow-planet window".
SLOW_PLANETS: tuple[str, ...] = ("Jupiter", "Saturn", "Rahu", "Ketu")
_SCAN_DAYS = 90

# Allowed event-type labels for relationship windows (templated, never free text).
EVENT_COMMITMENT = "commitment window"
EVENT_ROMANTIC = "romantic-opportunity window"
EVENT_FRICTION = "partnership-friction caution"
EVENT_SOCIAL = "social-connection window"


def _significations(chart: Mapping[str, Any]) -> dict[str, list[int]]:
    """planet name -> its signified houses.

    Read from each planet's ``significator_of_houses`` when populated. Public
    ``/chart/generate`` payloads keep that field reserved-empty (D023): in that
    case the node-aware significators are recomputed from the base chart, the
    same way the career engine does.
    """
    out: dict[str, list[int]] = {}
    for planet in chart.get("planets", []) or []:
        out[planet["name"]] = sorted(
            int(h) for h in (planet.get("significator_of_houses") or [])
        )
    if out and not any(out.values()):
        computed = compute_node_aware_significators(chart["planets"], chart["houses"])
        return {name: list(houses) for name, houses in computed.planet_to_houses.items()}
    return out


def _supports(lord: str | None, sig: Mapping[str, list[int]]) -> bool:
    """True when ``lord`` signifies any favourable partnership house."""
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
    """Templated, hedged relationship summary. No LLM."""
    md = dasha_timing["md_lord"]
    ad = dasha_timing["ad_lord"]
    pd = dasha_timing["pd_lord"]
    parts: list[str] = [
        f"As of {as_of.date().isoformat()}, the active Vimshottari stack is "
        f"{md} (mahadasha) > {ad} (antardasha) > {pd} (pratyantardasha)."
    ]

    if promise_met and not caution_flag:
        parts.append(
            "The 7th cusp sub-lord signifies supportive partnership houses, so "
            "commitment and relationship indications strengthen across this period."
        )
    elif caution_flag:
        parts.append(
            "The 7th cusp sub-lord leans toward houses of friction and separation, "
            "so partnership matters deserve patience, caution, and slower steps."
        )
    else:
        parts.append(
            "The 7th cusp sub-lord does not clearly signify supportive partnership "
            "houses, so the relationship signal stays muted."
        )

    if transit_windows and slow_planet_window:
        parts.append(
            "A slow-planet transit window strengthens the timing signal and may "
            "mark a commitment window or a meaningful connection, not an exact event."
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
            "Given these friction signals, approach partnership decisions with "
            "patience and added caution."
        )

    parts.append(
        "This is reflective guidance based on KP significators and Vimshottari "
        "timing, not a guarantee of any specific outcome, and not relationship or "
        "personal advice."
    )
    return " ".join(parts)


def compute_relationship_prediction(
    chart: Mapping[str, Any],
    *,
    as_of: datetime,
) -> dict[str, Any]:
    """Compute the internal relationship evidence object for ``chart`` as of ``as_of``.

    ``as_of`` must be timezone-aware; its date anchors the (deterministic) transit
    scan. The input chart is not mutated and no public field is populated. Returns
    a JSON-serializable dict carrying the unified prediction contract.
    """
    if as_of.tzinfo is None:
        raise ValueError("`as_of` must be timezone-aware")

    houses = chart["houses"]
    houses_by_num = {house["house"]: house for house in houses}
    sig = _significations(chart)

    # ---- Promise: the 7th cusp sub-lord --------------------------------------
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
        # "primarily signifies friction/separation": blocking present, no favourable.
        if blocking and not favourable:
            caution_flag = True
    promise_met = bool(promise_hits)

    cusp_sublords = {
        "primary_houses": primary_sublords,
        "sublord_significations": sublord_significations,
    }

    # ---- Dasha timing (from chart.dashas.current, else recomputed) -------------
    current = (chart.get("dashas") or {}).get("current") or {}
    md_lord = current.get("md_lord")
    ad_lord = current.get("ad_lord")
    pd_lord = current.get("pd_lord")
    if not (md_lord and ad_lord and pd_lord):
        # Public /chart/generate payloads keep chart["dashas"] null: recompute
        # the current Vimshottari stack from the base chart (career-engine
        # pattern, D027) instead of degrading to null lords.
        md, ad, pd = compute_dasha_from_chart(chart).current_stack(as_of)
        md_lord, ad_lord, pd_lord = md.lord, ad.lord, pd.lord
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

    # ---- Confidence (relationship may reach "high") --------------------------
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
        event_types.append(EVENT_COMMITMENT)
    elif promise_met and (transit_windows or dasha_supports):
        event_types.append(EVENT_ROMANTIC)
    if transit_windows and not caution_flag:
        event_types.append(EVENT_SOCIAL)
    if caution_flag or blocking_dasha:
        event_types.append(EVENT_FRICTION)
    if not event_types:
        event_types.append(EVENT_SOCIAL)

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
