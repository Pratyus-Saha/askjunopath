"""Gemini 2.5 Flash synthesizer for the chart-explanation layer (Phase 2).

Takes the strict payload from :mod:`app.synthesis.payload_builder` and asks
Gemini 2.5 Flash to explain it back to the chart's owner, one referenced
paragraph at a time. The system prompt pins Gemini to the payload: every
sentence must cite a planet or house that is actually present, it may not invent
placements, it may not claim certainty beyond the ``signal_strength`` tier, and
for the finance domain it may not use trading vocabulary.

The model may answer either as a JSON array of ``{"text", "references"}`` objects
or as plain prose. Both are normalised here into a list of paragraph dicts; when
references are missing (or the model returned prose) they are extracted from the
text against the payload's own planet/house vocabulary, so a paragraph is never
tagged with an entity the payload does not contain.

The single network call lives in :func:`_call_gemini`; everything else is pure
and deterministic, which keeps the module importable without ``httpx`` or an API
key and makes the call trivial to mock in tests.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from app.synthesis.payload_builder import known_house_numbers, known_planet_names

MODEL = "gemini-2.5-flash"
_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
_TIMEOUT_SECONDS = 30.0

# System prompt — used verbatim (Phase 2 spec).
SYSTEM_PROMPT = (
    "You are explaining KP astrology chart data to the person "
    "whose chart this is. Every sentence you write must reference "
    "a specific planet or house from the input payload by name. "
    "Do not invent placements that are not in the payload. "
    "Do not state certainty beyond the signal_strength tier "
    "provided. Signal strength describes factor convergence, "
    "not probability of the event occurring. For finance domain "
    "output, never use these words: invest, buy, sell, trade, "
    "stock, profit, instrument."
)


def _extract_references(text: str, payload: dict) -> list[str]:
    """Return the payload planets/houses a paragraph cites, in first-seen order.

    Planets are matched by canonical name; houses by ``house_7`` / ``house 7`` /
    ``7th house`` forms, but only when the number is actually in the payload.
    """
    references: list[str] = []

    for planet in known_planet_names(payload):
        if re.search(rf"\b{re.escape(planet)}\b", text) and planet not in references:
            references.append(planet)

    houses = known_house_numbers(payload)

    def _add_house(number: int) -> None:
        token = f"house_{number}"
        if number in houses and token not in references:
            references.append(token)

    for match in re.finditer(r"\bhouse[_\s]+(\d{1,2})\b", text, re.IGNORECASE):
        _add_house(int(match.group(1)))
    for match in re.finditer(r"\b(\d{1,2})(?:st|nd|rd|th)\s+house\b", text, re.IGNORECASE):
        _add_house(int(match.group(1)))

    return references


def _parse_plain_text(text: str, payload: dict) -> list[dict]:
    """Split prose into paragraphs on blank lines and tag each with references."""
    paragraphs: list[dict] = []
    for block in re.split(r"\n\s*\n", text.strip()):
        block = block.strip()
        if not block:
            continue
        paragraphs.append({"text": block, "references": _extract_references(block, payload)})
    return paragraphs


def _strip_code_fence(raw: str) -> str:
    candidate = raw.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```[a-zA-Z0-9]*\n?", "", candidate)
        candidate = re.sub(r"\n?```$", "", candidate).strip()
    return candidate


def _parse_structured(raw: str, payload: dict) -> list[dict] | None:
    """Parse a JSON array of paragraph objects, or ``None`` if not structured.

    Each item may be ``{"text", "references"}`` or a bare string. Missing or
    empty references are backfilled from the text against the payload.
    """
    try:
        data = json.loads(_strip_code_fence(raw))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, list):
        return None

    paragraphs: list[dict] = []
    for item in data:
        if isinstance(item, dict) and "text" in item:
            text = str(item["text"])
            references = item.get("references")
            if isinstance(references, list) and references:
                references = [str(ref) for ref in references]
            else:
                references = _extract_references(text, payload)
            paragraphs.append({"text": text, "references": references})
        elif isinstance(item, str):
            paragraphs.append({"text": item, "references": _extract_references(item, payload)})
    return paragraphs or None


def _build_request_body(payload: dict, domain: str) -> dict:
    """The generateContent request body: system prompt + the strict payload."""
    user_text = (
        f"Domain: {domain}\n"
        "Explain this KP chart payload to its owner. Use only the planets, "
        "houses, sub-lords, dasha lords and transit windows present below.\n"
        f"Payload JSON:\n{json.dumps(payload, sort_keys=True, ensure_ascii=False)}"
    )
    return {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
    }


def _call_gemini(payload: dict, domain: str) -> str:
    """POST the payload to Gemini 2.5 Flash and return the raw text response.

    Isolated and side-effecting (reads ``GEMINI_API_KEY``, imports/uses
    ``httpx``) so the rest of the module stays pure and this is the single point
    to mock in tests.
    """
    import httpx

    from app.core.config import settings

    # Settings covers both the env var and backend/.env; the direct env read
    # keeps a key injected after process start working too.
    api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    response = httpx.post(
        _ENDPOINT.format(model=MODEL),
        params={"key": api_key},
        json=_build_request_body(payload, domain),
        timeout=_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()
    parts = data["candidates"][0]["content"]["parts"]
    return "".join(part.get("text", "") for part in parts)


def synthesize(payload: dict, domain: str) -> list[dict]:
    """Synthesise the payload into a list of referenced paragraph dicts.

    Args:
        payload: the strict payload from :func:`build_payload`.
        domain: ``"career"``, ``"finance"`` or ``"relationship"``.

    Returns:
        ``[{"text": str, "references": list[str]}, ...]`` where each paragraph's
        ``references`` tags the payload planets (canonical name) and houses
        (``house_<n>``) it cites. A structured JSON reply is honoured directly;
        plain prose is split on blank lines with references extracted from text.
    """
    raw = _call_gemini(payload, domain)
    structured = _parse_structured(raw, payload)
    if structured is not None:
        return structured
    return _parse_plain_text(raw, payload)
