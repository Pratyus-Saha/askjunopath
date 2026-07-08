"""Tests for POST /chart/dasha endpoint."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

import pytest
from fastapi.testclient import TestClient

from app import main as app_main
from app.core.auth import get_current_user

FIXTURE_PATH = ROOT / "frontend" / "src" / "fixtures" / "chart.sample.json"
SAMPLE_CHART = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
if not SAMPLE_CHART["birth"]["datetime_utc"].endswith("Z"):
    SAMPLE_CHART["birth"]["datetime_utc"] += "Z"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(
        app_main.app.dependency_overrides,
        get_current_user,
        lambda: "dasha-test-user",
    )
    yield TestClient(app_main.app)
    app_main.app.dependency_overrides.clear()


def test_dasha_returns_mahadasha_data(client):
    resp = client.post("/chart/dasha", json={"chart": SAMPLE_CHART})
    assert resp.status_code == 200
    data = resp.json()
    assert "mahadashas" in data
    assert "antardashas" in data
    assert "pratyantardashas" in data
    assert len(data["mahadashas"]) == 9
    for md in data["mahadashas"]:
        assert "lords" in md
        assert "start" in md
        assert "end" in md


def test_dasha_invalid_chart_returns_422(client):
    resp = client.post("/chart/dasha", json={"chart": {"bad": "data"}})
    assert resp.status_code == 422
    assert resp.json()["detail"]["error"] == "INVALID_CHART"


def test_dasha_requires_auth():
    unauthenticated_client = TestClient(app_main.app)
    resp = unauthenticated_client.post(
        "/chart/dasha", json={"chart": SAMPLE_CHART}
    )
    assert resp.status_code == 401
