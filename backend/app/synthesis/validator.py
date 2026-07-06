"""Validator + D029 fallback for the Gemini synthesis layer (Phase 2).

Gemini is pinned to the payload by its system prompt, but the prompt is not a
guarantee — this module is the enforcement boundary. Each synthesised paragraph
is checked against the strict payload:

* it must reference at least one planet or house that actually exists in the
  payload — a paragraph with zero payload references is rejected as ungrounded;
* for the finance domain it must not contain trading vocabulary (``invest``,
  ``buy``, ``sell``, ``trade``, ``stock``, ``profit``, ``instrument``).

If more than 20% of the paragraphs are rejected the synthesis is considered
untrustworthy and the **D029 fallback** fires: the Gemini text is discarded
entirely and a deterministic, payload-templated summary is returned in its place
— planet/house facts only, no model prose. The same fallback covers the empty
input case.
"""

from __future__ import annotations

import re
from typing import Any

from app.synthesis.payload_builder import known_house_numbers, known_planet_names

# Above this rejection rate the Gemini output is dropped for the D029 fallback.
REJECTION_THRESHOLD = 0.20

# Finance market/trading vocabulary banned from synthesised output (audit
# finding #10; matches the project's own engine-output ban list). Matched as
# stems anywhere inside a word (case-insensitive), so suffixed forms
# ("investing", "profits", "yields") and prefixed forms ("reinvest",
# "disinvestment", "refund") all trip.
FINANCE_BANNED_WORDS: tuple[str, ...] = (
    "invest", "buy", "sell", "trade", "stock", "profit", "instrument",
    "return", "purchase", "asset", "portfolio", "fund", "yield",
)
_BANNED_RE = re.compile(
    r"\b\w*(?:" + "|".join(re.escape(word) for word in FINANCE_BANNED_WORDS) + r")\w*",
    re.IGNORECASE,
)


def _references_payload(paragraph: dict, planets: set[str], houses: set[int]) -> bool:
    """True if the paragraph cites at least one planet/house present in the payload."""
    for ref in paragraph.get("references") or []:
        if ref in planets:
            return True
        if isinstance(ref, str) and ref.startswith("house_"):
            try:
                if int(ref[len("house_"):]) in houses:
                    return True
            except ValueError:
                continue
    return False


def _has_banned_word(paragraph: dict) -> bool:
    return bool(_BANNED_RE.search(paragraph.get("text", "")))


def _fallback_paragraphs(payload: dict, domain: str) -> list[dict]:
    """Deterministic, payload-only summary (D029) — no Gemini text at all.

    Built straight from the payload's computed fields: each primary-house cusp
    sub-lord, the dasha period, each transit window, and a signal-strength note.
    Every paragraph carries genuine payload references by construction.
    """
    paragraphs: list[dict] = []

    cusp = payload.get("cusp_sublords") or {}
    primary = cusp.get("primary_houses") or {}
    significations = cusp.get("sublord_significations") or {}
    for house, lord in primary.items():
        signified = significations.get(lord) or []
        signified_text = (
            ", ".join(str(h) for h in signified) if signified else "no recorded houses"
        )
        references = ([lord] if lord else []) + [f"house_{house}"]
        paragraphs.append(
            {
                "text": (
                    f"The cusp sub-lord of house {house} is {lord}, "
                    f"which signifies houses {signified_text}."
                ),
                "references": references,
            }
        )

    dasha = payload.get("dasha_period") or {}
    md, ad, pd = dasha.get("md_lord"), dasha.get("ad_lord"), dasha.get("pd_lord")
    if md and ad and pd:
        paragraphs.append(
            {
                "text": (
                    f"The active dasha period runs {md} (mahadasha), "
                    f"{ad} (antardasha) and {pd} (pratyantardasha)."
                ),
                "references": [lord for lord in (md, ad, pd) if lord],
            }
        )

    for window in payload.get("transit_windows") or []:
        trigger_planets = window.get("trigger_planets") or []
        if not trigger_planets:
            continue
        paragraphs.append(
            {
                "text": (
                    f"A transit window runs {window.get('start_date')} to "
                    f"{window.get('end_date')}, triggered by "
                    f"{', '.join(trigger_planets)}."
                ),
                "references": list(trigger_planets),
            }
        )

    # Signal-strength note, anchored to a real payload planet so it too carries a
    # reference (the dasha mahadasha lord, else any harvested natal planet).
    anchor = md or next(iter(payload.get("planets") or {}), None)
    if anchor:
        paragraphs.append(
            {
                "text": (
                    f"Overall signal strength is {payload.get('signal_strength')} "
                    f"(tier: {payload.get('confidence')}), which describes how many "
                    f"chart factors such as {anchor} converge, not the probability "
                    "of any event."
                ),
                "references": [anchor],
            }
        )

    return paragraphs


def validate(paragraphs: list[dict], payload: dict, domain: str) -> dict:
    """Validate synthesised paragraphs against the payload; fall back if needed.

    Args:
        paragraphs: the list from :func:`synthesize`.
        payload: the strict payload from :func:`build_payload`.
        domain: ``"career"``, ``"finance"`` or ``"relationship"``.

    Returns:
        ``{"paragraphs", "fallback_used", "rejection_count", "total_count"}``.
        ``paragraphs`` holds the validated survivors, or — when more than 20% are
        rejected (or there were none) — the deterministic D029 fallback.
    """
    planets = known_planet_names(payload)
    houses = known_house_numbers(payload)

    total = len(paragraphs)
    kept: list[dict] = []
    rejection_count = 0
    for paragraph in paragraphs:
        if not _references_payload(paragraph, planets, houses):
            rejection_count += 1
            continue
        if domain == "finance" and _has_banned_word(paragraph):
            rejection_count += 1
            continue
        kept.append(paragraph)

    rejection_rate = (rejection_count / total) if total else 1.0
    fallback_used = total == 0 or rejection_rate > REJECTION_THRESHOLD
    if fallback_used:
        kept = _fallback_paragraphs(payload, domain)

    return {
        "paragraphs": kept,
        "fallback_used": fallback_used,
        "rejection_count": rejection_count,
        "total_count": total,
    }
