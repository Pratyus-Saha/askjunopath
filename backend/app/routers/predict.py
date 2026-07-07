"""Public prediction endpoints (Phase 3) — chart -> engine -> Gemini synthesis.

Three authenticated routes (``/predict/career``, ``/predict/finance``,
``/predict/relationship``) that run the matching deterministic KP evidence engine
over a caller-supplied chart and then explain its unified prediction contract with
the Gemini synthesis layer. The flow per request is fixed:

    engine  -> build_payload -> synthesize (Gemini) -> validate

Trust discipline. Raw Gemini text is **never** returned: the response always
carries the validator-filtered paragraphs (:func:`app.synthesis.validator.validate`),
which drop any ungrounded paragraph and fall back to the deterministic D029 summary
when too many are rejected. If the Gemini call itself raises, the route catches it,
sets ``fallback_used=True`` and returns the engine's own templated ``summary`` (the
D029 deterministic summary) directly — so a Gemini outage degrades to deterministic
text rather than a 500.

No caching here (post-launch); the engines are read-only and mutate nothing.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError

from app.core.auth import get_current_user
from app.engines.prediction_career_engine import compute_career_prediction
from app.engines.prediction_finance_engine import compute_finance_prediction
from app.engines.prediction_relationship_engine import compute_relationship_prediction
from app.schemas.models import ChartData
from app.synthesis.disclaimer import get_disclaimer
from app.synthesis.gemini_synthesizer import synthesize
from app.synthesis.payload_builder import build_payload
from app.synthesis.validator import validate

logger = logging.getLogger(__name__)

router = APIRouter(tags=["predict"])


class PredictionRequest(BaseModel):
    """Request body: the full computed chart dict to run a prediction over."""

    chart: dict[str, Any]


def _predict(
    domain: str,
    engine: Callable[..., dict[str, Any]],
    chart: dict[str, Any],
    user_id: str,
) -> dict[str, Any]:
    """Shared pipeline: engine -> payload -> Gemini -> validator.

    The Gemini call (``synthesize`` + ``validate``) is wrapped so a Gemini failure
    degrades to the engine's deterministic D029 ``summary`` instead of a 500. On
    success the synthesis is always the validator-filtered paragraphs — never raw
    Gemini output.

    The caller-supplied chart is validated against the canonical v1.2 ChartData
    contract before it reaches the engine (matching /internal/predict/career);
    an invalid chart is a 422 with a generic message. An unexpected engine
    failure is logged server-side and returned as a generic 500 — never a raw
    traceback detail.
    """
    try:
        ChartData.model_validate(chart)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "INVALID_CHART",
                "message": "chart failed ChartData v1.2 validation",
            },
        ) from exc

    as_of = datetime.now(timezone.utc)
    try:
        engine_output = engine(chart, as_of=as_of)
    except Exception:
        logger.exception("%s prediction engine failed", domain)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction computation failed.",
        )
    payload = build_payload(engine_output)

    try:
        paragraphs = synthesize(payload, domain)
        validated = validate(paragraphs, payload, domain)
        synthesis = validated["paragraphs"]
        fallback_used = validated["fallback_used"]
    except Exception:
        # Gemini (or its validation) failed: fall back to the engine's own
        # deterministic, templated D029 summary — never a 500.
        synthesis = [{"text": engine_output["summary"], "references": []}]
        fallback_used = True

    return {
        "domain": domain,
        "engine_output": engine_output,
        "synthesis": synthesis,
        "fallback_used": fallback_used,
        "disclaimer": get_disclaimer(),
        "user_id": user_id,
    }


@router.post("/career")
def predict_career(
    request: PredictionRequest,
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Career prediction: KP career engine synthesised by Gemini."""
    return _predict("career", compute_career_prediction, request.chart, user_id)


@router.post("/finance")
def predict_finance(
    request: PredictionRequest,
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Finance prediction: KP finance engine synthesised by Gemini."""
    return _predict("finance", compute_finance_prediction, request.chart, user_id)


@router.post("/relationship")
def predict_relationship(
    request: PredictionRequest,
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    """Relationship prediction: KP relationship engine synthesised by Gemini."""
    return _predict(
        "relationship", compute_relationship_prediction, request.chart, user_id
    )
