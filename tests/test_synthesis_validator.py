"""Tests for the synthesis validator, D029 fallback, disclaimer and (mocked)
Gemini synthesizer (Phase 2).

These exercise the enforcement boundary with no network access: a hand-built
strict payload stands in for the builder's output, and the single Gemini network
call is monkeypatched. They assert that ungrounded paragraphs are rejected, that
finance trading vocabulary is rejected, that the D029 fallback fires once the
rejection rate passes 20%, that the disclaimer is exact, and that the synthesizer
parses a (mocked) Gemini reply into referenced paragraphs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

import pytest  # noqa: E402

from app.synthesis import gemini_synthesizer  # noqa: E402
from app.synthesis.disclaimer import get_disclaimer  # noqa: E402
from app.synthesis.gemini_synthesizer import synthesize  # noqa: E402
from app.synthesis.validator import validate  # noqa: E402

EXACT_DISCLAIMER = (
    "AskJunoPath computes chart positions using Swiss Ephemeris "
    "and explains them using KP astrology principles. Astrology's "
    "predictive accuracy is unproven. This is not professional advice."
)


def _payload() -> dict:
    """A strict payload (as build_payload would produce), built by hand here."""
    return {
        "domain": "finance",
        "planets": {"Jupiter": 200.0, "Saturn": 62.94},
        "houses": {"2": 211.0, "7": 1.0, "11": 121.0},
        "cusp_sublords": {
            "primary_houses": {"2": "Venus", "11": "Venus"},
            "sublord_significations": {"Venus": [2, 6, 11]},
        },
        "confidence": "high",
        "signal_strength": 70,
        "dasha_period": {"md_lord": "Jupiter", "ad_lord": "Jupiter", "pd_lord": "Mercury"},
        "transit_windows": [
            {
                "start_date": "2026-10-01",
                "end_date": "2026-10-12",
                "trigger_planets": ["Mars", "Saturn"],
            }
        ],
        "event_types": ["income-rise window"],
    }


def _grounded(text: str = "Jupiter is prominent.") -> dict:
    return {"text": text, "references": ["Jupiter"]}


# --------------------------------------------------------------------------- #
# Rejection of ungrounded paragraphs
# --------------------------------------------------------------------------- #
def test_paragraph_without_payload_reference_is_rejected():
    payload = _payload()
    # 5 paragraphs, exactly one ungrounded -> 20% rejection, just under the
    # threshold, so we observe the rejection without the fallback masking it.
    paragraphs = [_grounded() for _ in range(4)] + [
        {"text": "An unnamed force shapes the year.", "references": []}
    ]
    result = validate(paragraphs, payload, "finance")

    assert result["total_count"] == 5
    assert result["rejection_count"] == 1
    assert result["fallback_used"] is False
    assert len(result["paragraphs"]) == 4
    assert all(p["references"] for p in result["paragraphs"])


def test_reference_to_planet_absent_from_payload_is_rejected():
    payload = _payload()  # no Pluto/Sun/Moon in this payload's vocabulary
    paragraphs = [_grounded() for _ in range(4)] + [
        {"text": "Pluto rules transformation.", "references": ["Pluto"]}
    ]
    result = validate(paragraphs, payload, "finance")
    assert result["rejection_count"] == 1
    assert result["fallback_used"] is False


# --------------------------------------------------------------------------- #
# Finance banned vocabulary
# --------------------------------------------------------------------------- #
def test_finance_banned_words_trigger_rejection():
    payload = _payload()
    bad = {"text": "Jupiter says you should buy and invest now.", "references": ["Jupiter"]}
    paragraphs = [_grounded() for _ in range(4)] + [bad]

    result = validate(paragraphs, payload, "finance")
    assert result["rejection_count"] == 1  # grounded but banned -> rejected
    assert result["fallback_used"] is False
    assert bad not in result["paragraphs"]


def test_banned_words_only_apply_to_finance_domain():
    payload = dict(_payload())
    bad = {"text": "Jupiter favours a profit this season.", "references": ["Jupiter"]}
    paragraphs = [_grounded() for _ in range(4)] + [bad]

    # Same paragraph is fine outside the finance domain.
    result = validate(paragraphs, payload, "relationship")
    assert result["rejection_count"] == 0
    assert result["fallback_used"] is False
    assert bad in result["paragraphs"]


def test_banned_word_matches_as_stem():
    payload = _payload()
    for text in ("Investing heavily.", "Trades are likely.", "Selling pressure."):
        paragraphs = [_grounded() for _ in range(4)] + [
            {"text": f"Jupiter note: {text}", "references": ["Jupiter"]}
        ]
        result = validate(paragraphs, payload, "finance")
        assert result["rejection_count"] == 1, text


# --------------------------------------------------------------------------- #
# D029 fallback above the 20% rejection rate
# --------------------------------------------------------------------------- #
def test_fallback_fires_when_rejection_rate_exceeds_20_percent():
    payload = _payload()
    # 4 paragraphs, one ungrounded -> 25% > 20% -> fallback.
    paragraphs = [_grounded() for _ in range(3)] + [
        {"text": "A vague unnamed influence.", "references": []}
    ]
    result = validate(paragraphs, payload, "finance")

    assert result["fallback_used"] is True
    assert result["rejection_count"] == 1
    assert result["total_count"] == 4

    # Fallback paragraphs are payload-derived and every one carries a real
    # payload reference (planets/houses present in the payload).
    fallback = result["paragraphs"]
    assert fallback, "fallback must produce a deterministic templated summary"
    planets = set(payload["planets"]) | {"Venus", "Mars", "Mercury"}
    houses = {2, 6, 7, 11}
    for paragraph in fallback:
        grounded = any(
            ref in planets
            or (ref.startswith("house_") and int(ref[len("house_"):]) in houses)
            for ref in paragraph["references"]
        )
        assert grounded, paragraph
    # The fallback never reuses the (discarded) Gemini text.
    assert all("unnamed influence" not in p["text"] for p in fallback)


def test_empty_paragraph_list_uses_fallback():
    payload = _payload()
    result = validate([], payload, "finance")
    assert result["fallback_used"] is True
    assert result["total_count"] == 0
    assert result["paragraphs"]


# --------------------------------------------------------------------------- #
# Disclaimer
# --------------------------------------------------------------------------- #
def test_get_disclaimer_returns_exact_required_string():
    assert get_disclaimer() == EXACT_DISCLAIMER


# --------------------------------------------------------------------------- #
# Synthesizer with a mocked Gemini call (no real API)
# --------------------------------------------------------------------------- #
def test_synthesize_parses_plain_text_reply(monkeypatch):
    payload = _payload()
    canned = (
        "Jupiter sits with your 11th house and colours your gains.\n\n"
        "Saturn makes contact with house 2 this season."
    )
    monkeypatch.setattr(gemini_synthesizer, "_call_gemini", lambda p, d: canned)

    paragraphs = synthesize(payload, "finance")
    assert len(paragraphs) == 2
    assert "Jupiter" in paragraphs[0]["references"]
    assert "house_11" in paragraphs[0]["references"]
    assert "Saturn" in paragraphs[1]["references"]
    assert "house_2" in paragraphs[1]["references"]

    # Downstream validation keeps both (both are grounded, no banned words).
    result = validate(paragraphs, payload, "finance")
    assert result["fallback_used"] is False
    assert len(result["paragraphs"]) == 2


def test_synthesize_parses_structured_json_reply(monkeypatch):
    payload = _payload()
    canned = (
        '[{"text": "Jupiter strengthens house 11.", "references": ["Jupiter", "house_11"]},'
        ' {"text": "Saturn touches house 2."}]'
    )
    monkeypatch.setattr(gemini_synthesizer, "_call_gemini", lambda p, d: canned)

    paragraphs = synthesize(payload, "finance")
    assert paragraphs[0]["references"] == ["Jupiter", "house_11"]
    # Missing references are backfilled from the text against the payload.
    assert "Saturn" in paragraphs[1]["references"]
    assert "house_2" in paragraphs[1]["references"]


def test_synthesize_never_makes_a_real_call_when_mocked(monkeypatch):
    """Guard: the mock fully replaces the network path (no httpx, no API key)."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(
        gemini_synthesizer, "_call_gemini", lambda p, d: "Jupiter is steady."
    )
    paragraphs = synthesize(_payload(), "finance")
    assert paragraphs == [{"text": "Jupiter is steady.", "references": ["Jupiter"]}]
