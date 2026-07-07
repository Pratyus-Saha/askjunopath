"""Settings contract for the audit env-var findings (#3, #11).

SUPABASE_KEY is required with no default (every authed endpoint depends on it,
so a missing key must fail at startup, not 500 at request time). GEMINI_API_KEY
stays optional — absence means deterministic-fallback mode, announced by a
startup WARNING from app.main.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.core.config import Settings  # noqa: E402

REQUIRED_ENV = {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
    "SUPABASE_KEY": "test-anon-key",
}


def _clean_env(monkeypatch):
    for name in (*REQUIRED_ENV, "GEMINI_API_KEY", "CHART_ENGINE_VERSION", "ENVIRONMENT"):
        monkeypatch.delenv(name, raising=False)


def test_missing_supabase_key_fails_loudly(monkeypatch):
    _clean_env(monkeypatch)
    for name, value in REQUIRED_ENV.items():
        if name != "SUPABASE_KEY":
            monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_gemini_api_key_is_optional_and_defaults_to_none(monkeypatch):
    _clean_env(monkeypatch)
    for name, value in REQUIRED_ENV.items():
        monkeypatch.setenv(name, value)
    settings = Settings(_env_file=None)
    assert settings.gemini_api_key is None
    assert settings.supabase_key == "test-anon-key"


def test_gemini_api_key_read_from_environment(monkeypatch):
    _clean_env(monkeypatch)
    for name, value in REQUIRED_ENV.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    assert Settings(_env_file=None).gemini_api_key == "test-gemini-key"


def test_missing_gemini_key_logs_startup_warning(monkeypatch, caplog):
    """app.main logs one clear WARNING when GEMINI_API_KEY is absent."""
    import importlib
    import logging

    from app import main as app_main
    from app.core.config import settings

    monkeypatch.setattr(settings, "gemini_api_key", None)
    with caplog.at_level(logging.WARNING, logger="app.main"):
        importlib.reload(app_main)
    assert (
        "GEMINI_API_KEY not set - all predictions will use deterministic fallback."
        in caplog.text
    )
    importlib.reload(app_main)  # restore a clean module for later tests


def test_env_example_chart_engine_version_matches_code():
    env_example = (ROOT / "backend" / ".env.example").read_text(encoding="utf-8")
    versions = [
        line.split("=", 1)[1].strip()
        for line in env_example.splitlines()
        if line.startswith("CHART_ENGINE_VERSION=")
    ]
    assert versions == [Settings(_env_file=None, **{
        k.lower(): v for k, v in REQUIRED_ENV.items()
    }).chart_engine_version]
