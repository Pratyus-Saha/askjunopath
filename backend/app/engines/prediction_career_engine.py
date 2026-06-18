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

**Validation status.** There is no JHora/founder golden fixture for career output
yet, and the significator foundation is AstroSage-*compared* only (D028), not
JHora-validated. So v1 is a deterministic *evidence scaffold*, not a validated
predictor: language is hedged, confidence is capped at ``medium``, and nothing is
exposed publicly. Correctness validation waits on a founder golden fixture / the
JHora final significator table.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.engines.dasha_engine import compute_dasha_from_chart
from app.engines.significator_engine import compute_node_aware_significators

VERSION = "career-v1"

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

    # ---- Confidence (transparent heuristic, capped at "medium" in v1) -------
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
    # v1 never claims "high": the significators are not JHora-validated yet.
    confidence = "medium" if raw_tier == "high" else raw_tier
    confidence_basis = {
        "career_signal": career_signal,
        "challenge_signal": challenge_signal,
        "activated_career_houses": sorted(activated_career),
        "challenge_houses_hit": sorted(challenge_hit),
        "raw_tier": raw_tier,
        "note": (
            "v1 transparent heuristic, capped at 'medium'; the underlying "
            "significators are AstroSage-compared and not validated against JHora "
            "yet."
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
        "Timing is read at the dasha-period level (not day-level; v1 has no transit "
        f"precision). The current antardasha ({ad.lord}) runs "
        f"{ad.start.date().isoformat()} to {ad.end.date().isoformat()}, and the "
        f"pratyantardasha ({pd.lord}) runs {pd.start.date().isoformat()} to "
        f"{pd.end.date().isoformat()}. These windows may favour the activated "
        "career houses above; they are not exact event dates."
    )

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
    }
