"""Internal-only career prediction wrapper (dev/test surface for D029).

This router exists ONLY so the backend can exercise the deterministic Career V1
engine (``compute_career_prediction``, ``docs/prediction-career.md``) through an
API-like path during development and testing. It is **not** a public endpoint and
follows the same internal-only discipline as the engine it wraps:

* it is **gated to non-production environments** via ``settings.environment``; any
  other environment returns 404, so the route is invisible in production;
* it does **not** touch the public chart router, populates **no** public chart
  field, and bumps **no** ``schema_version`` / ``chart_engine_version``;
* it calls **no LLM**: it returns the evidence-first object **verbatim** from the
  engine, with the engine's ``medium`` confidence cap intact;
* it accepts an **inline chart** payload (validated against the canonical v1.2
  ``ChartData`` contract) and a timezone-aware ``as_of`` (or safely derives one).

Public career exposure, when it ships, is a **separate** ``POST /predict/career``
endpoint gated behind founder-golden + JHora validation (``docs/prediction-career.md``,
TASKBOARD T11.2) — never this route, and never ``/chart/generate``.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import ValidationError

from app.core.config import is_production, settings
from app.engines.prediction_career_engine import compute_career_prediction
from app.schemas.models import ChartData, StrictModel

# The internal surface is exposed only in environments the shared fail-closed
# check recognises as non-production (config.NON_PRODUCTION_ENVIRONMENTS):
# anything else — typos, staging, empty strings — is production -> 404. Using
# the one shared helper keeps this gate in lockstep with the other
# production-only guards (audit finding #12).

# Optional defense-in-depth, read from os.environ at request time (NOT config.py)
# so it can be toggled per-deployment without a settings/schema change: when
# INTERNAL_CAREER_API_TOKEN is set, callers must also present the matching
# X-Internal-Career-Token header. Unset -> dev/local/test needs no header.
INTERNAL_TOKEN_ENV_VAR = "INTERNAL_CAREER_API_TOKEN"
INTERNAL_TOKEN_HEADER = "X-Internal-Career-Token"

INTERNAL_CAVEAT = (
    "INTERNAL/DEV ONLY. This endpoint wraps the deterministic Career V1 evidence "
    "engine for backend testing; it is not a public API, is not wired to any "
    "frontend, and its output is not validated for user-facing use. See "
    "docs/prediction-career.md."
)


def require_internal_access(
    x_internal_career_token: str | None = Header(
        default=None, alias=INTERNAL_TOKEN_HEADER
    ),
) -> None:
    """Gate the internal surface with defense-in-depth. Every failure is a 404
    (never 401/403), so the route is indistinguishable from a non-existent path.

    1. **Environment gate (fail-closed):** exposed only in non-production
       environments; anything else -> 404, *even with a correct token*.
    2. **Optional token gate:** when ``INTERNAL_CAREER_API_TOKEN`` is set, the
       matching ``X-Internal-Career-Token`` header is required (missing or wrong
       -> 404, constant-time compare). When the env var is unset, dev/local/test
       access needs no header.
    """
    if is_production(settings.environment):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    expected_token = os.environ.get(INTERNAL_TOKEN_ENV_VAR)
    if expected_token:
        presented = x_internal_career_token or ""
        if not secrets.compare_digest(presented, expected_token):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Not Found"
            )


router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(require_internal_access)],
)


class InternalCareerPredictionRequest(StrictModel):
    """Inline chart + optional as_of. ``chart_id`` is accepted but unsupported in v1."""

    chart: dict[str, Any] | None = None
    chart_id: str | None = None
    as_of: str | None = None


class InternalCareerPredictionResponse(StrictModel):
    internal_only: bool
    caveat: str
    as_of: str
    prediction: dict[str, Any]


def _resolve_as_of(raw: str | None) -> datetime:
    """Return a timezone-aware ``as_of``: parse ``raw`` (rejecting naive/invalid),
    or safely derive the current instant in UTC when ``raw`` is omitted."""
    if raw is None:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(raw)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"`as_of` is not a valid ISO-8601 datetime: {raw!r}",
        ) from exc
    if parsed.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "`as_of` must be timezone-aware (include a UTC offset, "
                "e.g. 2026-06-17T12:00:00+05:30 or 2026-06-17T06:30:00Z)."
            ),
        )
    return parsed


@router.post("/predict/career", response_model=InternalCareerPredictionResponse)
def internal_predict_career(
    request: InternalCareerPredictionRequest,
) -> InternalCareerPredictionResponse:
    """Run Career V1 over an inline chart and return its evidence object verbatim."""
    if request.chart_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "`chart_id` is not supported by the internal career route in v1; "
                "pass an inline `chart` payload instead."
            ),
        )
    if request.chart is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="`chart` (an inline ChartData v1.2 payload) is required.",
        )

    # Validate the inline chart against the canonical v1.2 contract. The original
    # mapping is handed to the engine unchanged (read-only), so the returned object
    # is exactly the deterministic engine output for this chart.
    try:
        ChartData.model_validate(request.chart)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "INVALID_CHART",
                "message": "chart failed ChartData v1.2 validation",
            },
        ) from exc

    as_of = _resolve_as_of(request.as_of)

    try:
        prediction = compute_career_prediction(request.chart, as_of=as_of)
    except ValueError as exc:
        # Defense in depth: naive as_of (already screened) or an as_of outside the
        # computed dasha timeline surfaces as a 422 rather than a 500.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return InternalCareerPredictionResponse(
        internal_only=True,
        caveat=INTERNAL_CAVEAT,
        as_of=as_of.isoformat(),
        prediction=prediction,
    )
