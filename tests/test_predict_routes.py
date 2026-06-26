"""Route-level tests for the public prediction endpoints (Phase 3).

Covers POST /predict/{career,finance,relationship}:

* unauthenticated requests (no Bearer token, real JWT dependency) -> 401;
* the authenticated happy path returns exactly the contract keys, with the
  synthesis being the validator-filtered paragraphs (never raw Gemini output);
* a Gemini failure inside ``synthesize`` degrades to ``fallback_used=True`` and
  the engine's deterministic D029 ``summary`` instead of a 500.

Both the engines and the Gemini synthesis layer are mocked at the predict-router
module level, so these tests exercise wiring/auth only and never make a network
call or run the real KP math. Auth is overridden via ``dependency_overrides``,
matching tests/test_chart_route.py.
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
from fastapi.testclient import TestClient  # noqa: E402

from app import main as app_main  # noqa: E402
from app.core.auth import get_current_user  # noqa: E402
from app.routers import predict as predict_router  # noqa: E402
from app.synthesis.disclaimer import get_disclaimer  # noqa: E402

TEST_USER_ID = "predict-route-test-user"
REQUEST_BODY = {"chart": {"planets": [], "houses": []}}

ROUTES = (
    ("/predict/career", "career", "compute_career_prediction"),
    ("/predict/finance", "finance", "compute_finance_prediction"),
    ("/predict/relationship", "relationship", "compute_relationship_prediction"),
)

RESPONSE_KEYS = {
    "domain",
    "engine_output",
    "synthesis",
    "fallback_used",
    "disclaimer",
    "user_id",
}


def _engine_output(domain: str) -> dict:
    """A minimal stand-in for a unified prediction contract."""
    return {
        "domain": domain,
        "summary": f"Deterministic {domain} D029 summary.",
        "signal_strength": 42,
        "confidence": "medium",
    }


@pytest.fixture
def authed_client(monkeypatch):
    """TestClient with auth overridden and all engines + Gemini layer mocked."""

    # Stub every engine so no real KP math runs; each returns its own contract.
    for _path, domain, engine_name in ROUTES:
        monkeypatch.setattr(
            predict_router,
            engine_name,
            lambda chart, *, as_of, _domain=domain: _engine_output(_domain),
        )

    # Stub the Gemini synthesis layer (no network call).
    monkeypatch.setattr(predict_router, "build_payload", lambda engine_output: {"p": 1})
    monkeypatch.setattr(
        predict_router,
        "synthesize",
        lambda payload, domain: [{"text": "raw gemini", "references": ["Sun"]}],
    )
    monkeypatch.setattr(
        predict_router,
        "validate",
        lambda paragraphs, payload, domain: {
            "paragraphs": [{"text": "validated", "references": ["Sun"]}],
            "fallback_used": False,
            "rejection_count": 0,
            "total_count": len(paragraphs),
        },
    )

    monkeypatch.setitem(
        app_main.app.dependency_overrides,
        get_current_user,
        lambda: TEST_USER_ID,
    )
    return TestClient(app_main.app)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", [path for path, _domain, _engine in ROUTES])
def test_unauthenticated_request_returns_401(path):
    # No auth override and no Authorization header -> the real JWT dependency 401s.
    app_main.app.dependency_overrides.pop(get_current_user, None)
    response = TestClient(app_main.app).post(path, json=REQUEST_BODY)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Happy path: contract keys + validator-filtered synthesis
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path,domain,_engine", ROUTES)
def test_route_returns_required_response_keys(authed_client, path, domain, _engine):
    response = authed_client.post(path, json=REQUEST_BODY)
    assert response.status_code == 200
    body = response.json()

    assert set(body.keys()) == RESPONSE_KEYS
    assert body["domain"] == domain
    assert body["engine_output"] == _engine_output(domain)
    assert body["fallback_used"] is False
    assert body["disclaimer"] == get_disclaimer()
    assert body["user_id"] == TEST_USER_ID
    # Synthesis is the validator output, not the raw synthesize() paragraphs.
    assert body["synthesis"] == [{"text": "validated", "references": ["Sun"]}]


# ---------------------------------------------------------------------------
# Fallback: Gemini raising -> deterministic D029 summary
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path,domain,_engine", ROUTES)
def test_gemini_failure_triggers_d029_fallback(
    authed_client, monkeypatch, path, domain, _engine
):
    def boom(payload, domain):
        raise RuntimeError("simulated Gemini outage")

    monkeypatch.setattr(predict_router, "synthesize", boom)

    response = authed_client.post(path, json=REQUEST_BODY)
    assert response.status_code == 200
    body = response.json()

    assert body["fallback_used"] is True
    # Fallback synthesis comes straight from the engine output's summary field.
    assert body["synthesis"] == [
        {"text": _engine_output(domain)["summary"], "references": []}
    ]
    assert body["domain"] == domain
    assert body["user_id"] == TEST_USER_ID
