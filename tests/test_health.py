from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

from fastapi.testclient import TestClient  # noqa: E402

from app import main as app_main  # noqa: E402
from app.core import db  # noqa: E402


def test_health_returns_200_and_required_keys() -> None:
    response = TestClient(app_main.app).get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert {"status", "version", "app_env", "timestamp", "checks"}.issubset(payload)
    assert payload["status"] in {"ok", "degraded"}
    assert payload["version"] == "1.0.0"
    assert isinstance(payload["checks"], dict)


def test_health_includes_ephemeris_and_database_checks() -> None:
    response = TestClient(app_main.app).get("/health")

    assert response.status_code == 200
    checks = response.json()["checks"]
    assert "ephemeris" in checks
    assert "database" in checks
    assert checks["ephemeris"]["status"] in {"ok", "degraded", "skipped"}
    assert checks["database"]["status"] in {"ok", "degraded", "skipped"}


def test_missing_or_invalid_ephemeris_path_degrades_not_500(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SE_EPHE_PATH", str(tmp_path / "missing-ephe"))

    response = TestClient(app_main.app).get("/health")

    assert response.status_code == 200
    ephemeris = response.json()["checks"]["ephemeris"]
    assert ephemeris["status"] == "degraded"


def test_simulated_database_failure_degrades_not_500(monkeypatch) -> None:
    class BrokenSupabase:
        def __getattribute__(self, name: str):
            if name == "table":
                raise RuntimeError("simulated database failure")
            return super().__getattribute__(name)

    monkeypatch.setattr(db, "supabase", BrokenSupabase())

    response = TestClient(app_main.app).get("/health")

    assert response.status_code == 200
    database = response.json()["checks"]["database"]
    assert database["status"] == "degraded"
    assert "simulated database failure" in database["detail"]
