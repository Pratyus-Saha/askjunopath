"""Route-level tests for the public prediction endpoints (Phase 3).

Covers POST /predict/{career,finance,relationship}:

* unauthenticated requests (no Bearer token, real JWT dependency) -> 401;
* the authenticated happy path returns exactly the contract keys, with the
  synthesis being the validator-filtered paragraphs (never raw Gemini output);
* a Gemini failure inside ``synthesize`` degrades to ``fallback_used=True`` and
  the engine's deterministic D029 ``summary`` instead of a 500;
* a chart that fails ChartData v1.2 validation -> 422 with a generic message
  (matching /internal/predict/career), before any engine runs;
* an unexpected engine exception -> generic 500, never a raw traceback detail.

Both the engines and the Gemini synthesis layer are mocked at the predict-router
module level, so these tests exercise wiring/auth only and never make a network
call or run the real KP math. Auth is overridden via ``dependency_overrides``,
matching tests/test_chart_route.py. The request chart is built once through the
same trusted path the internal-route tests use, so it always passes the route's
ChartData validation.
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
from app.engines.ephemeris_engine import compute_ephemeris  # noqa: E402
from app.routers import chart as chart_router  # noqa: E402
from app.routers import predict as predict_router  # noqa: E402
from app.schemas.models import BirthDataRequest  # noqa: E402
from app.synthesis.disclaimer import get_disclaimer  # noqa: E402

TEST_USER_ID = "predict-route-test-user"


def _valid_chart() -> dict:
    """A full, schema-valid ChartData payload built through the trusted path."""
    req = BirthDataRequest(
        birth_date="1998-08-14", birth_time="06:45", birth_city="Kolkata, India"
    )
    eph = compute_ephemeris(
        datetime_local="1998-08-14T06:45:00",
        timezone="Asia/Kolkata",
        lat=22.5725,
        lon=88.363889,
    )
    return chart_router._build_chart_payload(
        ephemeris=eph,
        place_label="Kolkata, India",
        request_data=req,
        geo_lat=22.5725,
        geo_lon=88.363889,
        timezone_str="Asia/Kolkata",
    )


REQUEST_BODY = {"chart": _valid_chart()}
INVALID_REQUEST_BODY = {"chart": {"planets": [], "houses": []}}

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


# ---------------------------------------------------------------------------
# Input validation: malformed chart -> 422 (generic), never an engine 500
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path,domain,_engine", ROUTES)
def test_invalid_chart_returns_422_with_generic_message(
    authed_client, path, domain, _engine
):
    response = authed_client.post(path, json=INVALID_REQUEST_BODY)
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail == {
        "error": "INVALID_CHART",
        "message": "chart failed ChartData v1.2 validation",
    }


@pytest.mark.parametrize(
    "bad_chart",
    [{}, {"planets": "not-a-list"}, {"schema_version": "1.2"}],
    ids=["empty", "wrong-types", "missing-sections"],
)
def test_malformed_chart_shapes_return_422(authed_client, bad_chart):
    response = authed_client.post("/predict/career", json={"chart": bad_chart})
    assert response.status_code == 422, response.text


# ---------------------------------------------------------------------------
# Engine crash: generic 500, no exception detail leaked
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path,domain,engine_name", ROUTES)
def test_engine_exception_returns_generic_500(
    authed_client, monkeypatch, path, domain, engine_name
):
    def boom(chart, *, as_of):
        raise KeyError("some-internal-key")

    monkeypatch.setattr(predict_router, engine_name, boom)

    response = authed_client.post(path, json=REQUEST_BODY)
    assert response.status_code == 500, response.text
    detail = response.json()["detail"]
    assert detail == "Prediction computation failed."
    assert "some-internal-key" not in response.text
    assert "KeyError" not in response.text
