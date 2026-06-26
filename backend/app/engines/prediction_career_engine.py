"""Internal career prediction v1 (D029) — deterministic KP evidence engine.

This engine answers "what does the chart + current dasha say about career, and
*why*" as a structured, evidence-first object. It is **internal only**, like the
significator and dasha engines it consumes:

* it reads an already-computed chart payload read-only and mutates nothing;
* it is **not** imported by the chart router and populates **no** public field
  (``chart.dashas`` stays ``null``; the reserved significator fields stay empty,
  D023); it bumps **no** schema/engine version;
* it **does not call any LLM** — the ``summary`` is templated from the evidence.

Model (D029): KP separates *promise* from *timing*.

* **Promise** — for each career house (2 income, 6 service/job, 10 profession,
  11 gains) the engine reads the **cusp sub-lord** and the houses that sub-lord
  signifies (node-aware, D028). A career house is "promised" when its cusp
  sub-lord signifies any career house. The 10th cusp sub-lord is the headline.
* **Timing** — the current Vimshottari mahadasha / antardasha / pratyantardasha
  lords (internal dasha engine, D027) and the houses they signify. A career
  house is "activated" when a current dasha lord signifies it.

Every emitted factor cites a real planet and the houses it signifies (taken
verbatim from the node-aware significator engine), so the output is auditable.

Unified contract (Block 4+5). The engine now also emits the cross-domain
prediction contract shared with the finance/relationship engines — ``domain``,
``promise_met``, ``signal_strength``, ``caution_flag``, ``dasha_timing``,
``transit_windows``, ``transit_summary``, ``event_types`` and ``cusp_sublords`` —
alongside its existing career-native keys. ``confidence`` now follows the unified
five-branch table (promise + dasha support + transit) and may reach ``high``; the
old v1 ``medium`` cap is lifted. Timing gains a near-term transit (gochara) layer
on top of the dasha-period reading.

**Validation status.** There is no JHora/founder golden fixture for career output
yet, and the significator foundation is AstroSage-*compared* only (D028), not
JHora-validated. So this stays a deterministic *evidence scaffold*, not a validated
predictor: language is hedged, ``high`` confidence denotes factor *convergence*
(signal strength) rather than a guaranteed or purely positive outcome, and nothing
is exposed publicly. Correctness validation waits on a founder golden fixture / the
JHora final significator table.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.engines.dasha_engine import compute_dasha_from_chart
from app.engines.significator_engine import compute_node_aware_significators
from app.engines.transit_engine import compute_transit_windows, find_next_contact

VERSION = "career-v1"
DOMAIN = "career"

# Slow transit bodies — a window carrying one of these is a "slow-planet window".
SLOW_PLANETS: tuple[str, ...] = ("Jupiter", "Saturn", "Rahu", "Ketu")
_SCAN_DAYS = 90

# Allowed event-type labels for career windows (templated, never free text).
EVENT_ADVANCE = "career-advancement window"
EVENT_OPPORTUNITY = "opportunity window"
EVENT_DISRUPTION = "career-disruption caution"
EVENT_STEADY = "steady-progress window"

# Career-relevant house taxonomy (KP), house -> short human label.
CAREER_HOUSES: dict[int, str] = {
    2: "income/resources",
    6: "job/service/competition",
    10: "profession/status",
    11: "gains/network",
}
SUPPORTING_HOUSES: dict[int, str] = {
    1: "self/direction",
    3: "effort/skills/communication",
    5: "intelligence/creativity/education",
    9: "fortune/higher-learning/mentors",
}
CHALLENGING_HOUSES: dict[int, str] = {
    8: "instability/sudden-change/breaks",
    12: "loss/foreign/remote/isolation/expenses",
}

CAVEAT = (
    "Internal career prediction v1. This is reflective guidance based on KP "
    "significators and Vimshottari dasha timing, not a guarantee of any specific "
    "outcome, and not financial, medical, legal, or professional advice. The "
    "underlying significators are compared against AstroSage and are not validated "
    "against the JHora final significator table yet, so treat this as directional, "
    "not definitive. Use real-world judgement for real-world decisions."
)


def _classify(houses: list[int]) -> tuple[list[int], list[int], list[int]]:
    """Split a planet's signified houses into (career, supporting, challenging)."""
    present = set(houses)
    return (
        sorted(h for h in present if h in CAREER_HOUSES),
        sorted(h for h in present if h in SUPPORTING_HOUSES),
        sorted(h for h in present if h in CHALLENGING_HOUSES),
    )


def _tenth_theme(houses: list[int]) -> str:
    """A hedged reading of the 10th cusp sub-lord's significations."""
    present = set(houses)
    if 6 in present and 7 in present:
        return "salaried service alongside some independent or partnership work"
    if 6 in present:
        return "salaried service or employment"
    if 7 in present or 3 in present:
        return "business, partnership, or independent work"
    if 12 in present:
        return "foreign, remote, or behind-the-scenes work"
    return "a mixed professional pattern"


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


def compute_career_prediction(
    chart: Mapping[str, Any],
    *,
    as_of: datetime,
) -> dict[str, Any]:
    """Compute the internal career evidence object for ``chart`` as of ``as_of``.

    ``as_of`` must be timezone-aware (it indexes the dasha timeline). Returns a
    JSON-serializable dict. The input chart payload is not mutated and no public
    field is populated.
    """
    if as_of.tzinfo is None:
        raise ValueError("`as_of` must be timezone-aware")

    planets = chart["planets"]
    houses = chart["houses"]
    houses_by_num = {house["house"]: house for house in houses}

    # Node-aware significators (D028): planet -> sorted signified houses.
    sig = compute_node_aware_significators(planets, houses)
    pth = sig.planet_to_houses

    # ---- Promise: career-house cusp sub-lords ------------------------------
    career_house_cusp_sub_lords: dict[str, Any] = {}
    promised_career_houses: list[int] = []
    for house_number in sorted(CAREER_HOUSES):
        sub_lord = houses_by_num[house_number]["kp"]["sub_lord"]
        signifies = pth[sub_lord]
        career_hits, _support_hits, challenge_hits = _classify(signifies)
        career_house_cusp_sub_lords[str(house_number)] = {
            "sub_lord": sub_lord,
            "signifies": signifies,
            "hits_career": career_hits,
            "hits_challenge": challenge_hits,
        }
        if career_hits:
            promised_career_houses.append(house_number)

    tenth_sub_lord = houses_by_num[10]["kp"]["sub_lord"]
    promise = {
        "career_house_cusp_sub_lords": career_house_cusp_sub_lords,
        "tenth_cusp_sub_lord": tenth_sub_lord,
        "tenth_cusp_sub_lord_signifies": pth[tenth_sub_lord],
        "promised_career_houses": promised_career_houses,
    }

    # ---- Timing: current Vimshottari stack ---------------------------------
    timeline = compute_dasha_from_chart(chart)
    md, ad, pd = timeline.current_stack(as_of)
    levels = (("mahadasha", md), ("antardasha", ad), ("pratyantardasha", pd))

    dasha_support: dict[str, Any] = {}
    for level_name, period in levels:
        signifies = pth[period.lord]
        career_hits, support_hits, challenge_hits = _classify(signifies)
        dasha_support[level_name] = {
            "lord": period.lord,
            "signifies": signifies,
            "career_hits": career_hits,
            "support_hits": support_hits,
            "challenge_hits": challenge_hits,
        }

    current_dasha_stack = {
        "mahadasha": md.lord,
        "antardasha": ad.lord,
        "pratyantardasha": pd.lord,
        "antardasha_window": [
            ad.start.date().isoformat(),
            ad.end.date().isoformat(),
        ],
        "pratyantardasha_window": [
            pd.start.date().isoformat(),
            pd.end.date().isoformat(),
        ],
    }

    # ---- Career-house activation (timing) ----------------------------------
    career_house_activation: dict[str, Any] = {}
    for house_number in sorted(CAREER_HOUSES):
        activated_by: list[str] = []
        for _level_name, period in levels:
            if house_number in pth[period.lord] and period.lord not in activated_by:
                activated_by.append(period.lord)
        career_house_activation[str(house_number)] = {
            "label": CAREER_HOUSES[house_number],
            "activated": bool(activated_by),
            "activated_by": activated_by,
            "promised_by_cusp_sub_lord": house_number in promised_career_houses,
            "cusp_sub_lord": houses_by_num[house_number]["kp"]["sub_lord"],
        }

    # ---- Evidence trail (promise + timing) ---------------------------------
    evidence: list[dict[str, Any]] = []
    for house_number in sorted(CAREER_HOUSES):
        info = career_house_cusp_sub_lords[str(house_number)]
        if info["hits_career"] or info["hits_challenge"]:
            evidence.append(
                {
                    "type": "promise",
                    "house": house_number,
                    "source": info["sub_lord"],
                    "signifies": info["signifies"],
                    "career_hits": info["hits_career"],
                    "challenge_hits": info["hits_challenge"],
                    "note": (
                        f"{house_number}th cusp sub-lord {info['sub_lord']} "
                        f"signifies houses {info['signifies']}"
                    ),
                }
            )
    for level_name, period in levels:
        support = dasha_support[level_name]
        evidence.append(
            {
                "type": "timing",
                "level": level_name,
                "source": period.lord,
                "signifies": support["signifies"],
                "career_hits": support["career_hits"],
                "challenge_hits": support["challenge_hits"],
                "note": (
                    f"{level_name} lord {period.lord} signifies houses "
                    f"{support['signifies']}"
                ),
            }
        )

    supporting_factors = [item for item in evidence if item["career_hits"]]
    blocking_factors = [item for item in evidence if item["challenge_hits"]]

    # ---- Career themes (from the houses the current stack touches) ----------
    theme_houses: set[int] = set()
    for level_name, _period in levels:
        theme_houses.update(dasha_support[level_name]["career_hits"])
        theme_houses.update(dasha_support[level_name]["challenge_hits"])
    theme_labels = {**CAREER_HOUSES, **CHALLENGING_HOUSES}
    career_themes = [
        f"{theme_labels[house]} (house {house})" for house in sorted(theme_houses)
    ]

    # ---- Career-signal heuristic (raw_tier) ---------------------------------
    # raw_tier stays the transparent career-signal heuristic; the published
    # `confidence` now follows the unified five-branch table computed below.
    activated_career = {
        house
        for house in CAREER_HOUSES
        if career_house_activation[str(house)]["activated"]
    }
    challenge_hit: set[int] = set()
    for level_name, _period in levels:
        challenge_hit.update(dasha_support[level_name]["challenge_hits"])
    career_signal = len(activated_career)
    challenge_signal = len(challenge_hit)
    if career_signal >= 3 and challenge_signal <= 1:
        raw_tier = "high"
    elif career_signal >= 2:
        raw_tier = "medium"
    else:
        raw_tier = "low"
    confidence_basis = {
        "career_signal": career_signal,
        "challenge_signal": challenge_signal,
        "activated_career_houses": sorted(activated_career),
        "challenge_houses_hit": sorted(challenge_hit),
        "raw_tier": raw_tier,
        "note": (
            "Transparent career-signal heuristic; the published confidence now "
            "follows the unified five-branch table (promise + dasha + transit) and "
            "may reach 'high'. The underlying significators are AstroSage-compared "
            "and not validated against JHora yet."
        ),
    }

    # ---- Templated summary (no LLM, hedged) --------------------------------
    activated_str = (
        ", ".join(str(house) for house in sorted(activated_career)) or "none"
    )
    summary = (
        f"As of {as_of.date().isoformat()}, the active Vimshottari stack is "
        f"{md.lord} (mahadasha) > {ad.lord} (antardasha) > {pd.lord} "
        f"(pratyantardasha). This may activate career houses {activated_str}. "
        f"The 10th-cusp sub-lord {tenth_sub_lord} signifies houses "
        f"{pth[tenth_sub_lord]}, which suggests {_tenth_theme(pth[tenth_sub_lord])}. "
    )
    if challenge_hit:
        challenge_labels = ", ".join(
            CHALLENGING_HOUSES[house] for house in sorted(challenge_hit)
        )
        summary += (
            f"Activation of house(s) "
            f"{', '.join(str(house) for house in sorted(challenge_hit))} indicates "
            f"{challenge_labels}, so supportive periods may also carry change, "
            f"expense, or remote/behind-the-scenes work. "
        )
    summary += "This is reflective guidance, not a guarantee of any specific outcome."

    timing_interpretation = (
        "Dasha timing is read at the period level. The current antardasha "
        f"({ad.lord}) runs {ad.start.date().isoformat()} to "
        f"{ad.end.date().isoformat()}, and the pratyantardasha ({pd.lord}) runs "
        f"{pd.start.date().isoformat()} to {pd.end.date().isoformat()}. These "
        "windows may favour the activated career houses above. A separate near-term "
        "transit (gochara) scan adds day-level contact windows (see transit_windows "
        "/ transit_summary); those are indicative timing, not exact event dates."
    )

    # ---- Unified prediction contract (Block 4+5 parity) ---------------------
    # Adds the cross-domain contract fields alongside the existing career-native
    # keys; the existing keys are unchanged. `confidence` is recomputed from the
    # unified five-branch table (career may now reach "high").
    # Promise gate: the 10th (primary career house) cusp sub-lord — consistent
    # with the finance/relationship engines, which gate on their own primary-house
    # cusp sub-lords. Promise is met when it signifies any career house.
    tenth_info = career_house_cusp_sub_lords["10"]
    promise_met = bool(tenth_info["hits_career"])

    # Caution: the 10th (headline) cusp sub-lord points to challenge houses
    # (instability / loss) without touching a career house.
    caution_flag = bool(tenth_info["hits_challenge"]) and not tenth_info["hits_career"]

    md_supports = bool(dasha_support["mahadasha"]["career_hits"])
    ad_supports = bool(dasha_support["antardasha"]["career_hits"])
    pd_supports = bool(dasha_support["pratyantardasha"]["career_hits"])
    dasha_supports = (md_supports + ad_supports + pd_supports) >= 2
    blocking_dasha = any(
        dasha_support[level]["challenge_hits"]
        for level in ("mahadasha", "antardasha", "pratyantardasha")
    )
    dasha_timing = {
        "md_lord": md.lord,
        "ad_lord": ad.lord,
        "pd_lord": pd.lord,
        "md_supports": md_supports,
        "ad_supports": ad_supports,
        "pd_supports": pd_supports,
    }

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

    # Unified confidence — career may now reach "high" (the v1 medium cap is lifted).
    if not promise_met:
        confidence = "low"
    elif dasha_supports:
        confidence = "high" if slow_planet_window else "medium"
    else:
        confidence = "medium" if transit_windows else "low"

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

    event_types: list[str] = []
    if promise_met and dasha_supports and slow_planet_window:
        event_types.append(EVENT_ADVANCE)
    elif promise_met and (transit_windows or dasha_supports):
        event_types.append(EVENT_OPPORTUNITY)
    if caution_flag or blocking_dasha:
        event_types.append(EVENT_DISRUPTION)
    event_types.append(EVENT_STEADY)

    cusp_sublords = {
        "primary_houses": {"10": tenth_sub_lord},
        "sublord_significations": {tenth_sub_lord: tenth_info["signifies"]},
    }

    return {
        "version": VERSION,
        "as_of": as_of.isoformat(),
        "summary": summary,
        "promise": promise,
        "career_house_activation": career_house_activation,
        "current_dasha_stack": current_dasha_stack,
        "dasha_support": dasha_support,
        "supporting_factors": supporting_factors,
        "blocking_factors": blocking_factors,
        "career_themes": career_themes,
        "timing_interpretation": timing_interpretation,
        "confidence": confidence,
        "confidence_basis": confidence_basis,
        "evidence": evidence,
        "caveat": CAVEAT,
        # --- unified cross-domain contract fields ---
        "domain": DOMAIN,
        "promise_met": promise_met,
        "signal_strength": signal_strength,
        "caution_flag": caution_flag,
        "dasha_timing": dasha_timing,
        "transit_windows": transit_windows,
        "transit_summary": transit_summary,
        "event_types": event_types,
        "cusp_sublords": cusp_sublords,
    }
