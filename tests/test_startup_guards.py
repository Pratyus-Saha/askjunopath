"""Startup guards and shared ephemeris-path config (audit findings #2, #16).

* In production the app must refuse to start when ``ephemeris_files_ok()`` is
  False (compute_ephemeris would otherwise silently degrade to Moshier).
  "Production" is fail-closed: anything not on the explicit non-production
  allow-list counts.
* In non-production environments the same condition is a WARNING, not a crash.
* ephemeris_engine and transit_engine resolve SE_EPHE_PATH through the single
  shared config helper, so their unset-variable fallbacks cannot diverge.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import pytest  # noqa: E402

from app import main as app_main  # noqa: E402
from app.core import config  # noqa: E402
from app.core.config import (  # noqa: E402
    DEFAULT_SE_EPHE_PATH,
    get_se_ephe_path,
    is_production,
    settings,
)
from app.engines import ephemeris_engine, transit_engine  # noqa: E402


# --------------------------------------------------------------------------- #
# Fail-closed production detection
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("env", ["development", "dev", "local", "test", " DEV ", "Test"])
def test_allow_listed_environments_are_not_production(env):
    assert is_production(env) is False


@pytest.mark.parametrize(
    "env", ["production", "prod", "staging", "PRODUCTION", "", "anything-else"]
)
def test_everything_else_is_production(env):
    assert is_production(env) is True


def test_is_production_defaults_to_settings(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    assert is_production() is True
    monkeypatch.setattr(settings, "environment", "development")
    assert is_production() is False


# --------------------------------------------------------------------------- #
# Ephemeris startup assertion
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("env", ["production", "staging", "", "typo-env"])
def test_production_refuses_to_start_without_ephemeris(monkeypatch, env):
    monkeypatch.setattr(settings, "environment", env)
    monkeypatch.setattr(ephemeris_engine, "ephemeris_files_ok", lambda: False)
    with pytest.raises(RuntimeError, match="Swiss Ephemeris"):
        app_main._assert_ephemeris_available()


def test_non_production_logs_warning_and_starts(monkeypatch, caplog):
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(ephemeris_engine, "ephemeris_files_ok", lambda: False)
    with caplog.at_level(logging.WARNING, logger="app.main"):
        app_main._assert_ephemeris_available()  # must not raise
    assert "Moshier fallback" in caplog.text


def test_healthy_ephemeris_is_silent(monkeypatch, caplog):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(ephemeris_engine, "ephemeris_files_ok", lambda: True)
    with caplog.at_level(logging.WARNING, logger="app.main"):
        app_main._assert_ephemeris_available()  # must not raise
    assert "Swiss Ephemeris" not in caplog.text


# --------------------------------------------------------------------------- #
# Shared SE_EPHE_PATH default (finding #16)
# --------------------------------------------------------------------------- #
def test_get_se_ephe_path_prefers_environment(monkeypatch):
    monkeypatch.setenv("SE_EPHE_PATH", "/somewhere/ephe")
    assert get_se_ephe_path() == "/somewhere/ephe"


def test_get_se_ephe_path_falls_back_to_shared_default(monkeypatch):
    monkeypatch.delenv("SE_EPHE_PATH", raising=False)
    assert get_se_ephe_path() == DEFAULT_SE_EPHE_PATH


def test_both_engines_resolve_the_path_through_config(monkeypatch):
    """ephemeris_engine and transit_engine must both call the shared helper."""
    calls: list[str] = []

    def probe() -> str | None:
        calls.append("hit")
        return os.environ.get("SE_EPHE_PATH")

    monkeypatch.setattr(ephemeris_engine, "get_se_ephe_path", probe)
    monkeypatch.setattr(transit_engine, "get_se_ephe_path", probe)
    ephemeris_engine._initialize_swe()
    transit_engine._init_swe()
    assert calls == ["hit", "hit"]


def test_engines_import_the_same_helper():
    assert ephemeris_engine.get_se_ephe_path is config.get_se_ephe_path
    assert transit_engine.get_se_ephe_path is config.get_se_ephe_path
