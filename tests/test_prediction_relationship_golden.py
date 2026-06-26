"""Founder GOLDEN fixtures for the internal relationship prediction engine (Block 5).

Three hand-built, self-contained runnable chart dicts — one per archetype —
pinned to a fixed ``as_of`` so the transit side is deterministic. Each test runs
the engine on the fixture and asserts the exact reviewed values: ``promise_met``,
``confidence`` (each exercising a distinct branch of the five-branch table),
``caution_flag``, and that the archetype's headline event type appears.

These lock the documented *behaviour*, not astrological ground truth — there is no
JHora relationship oracle and the significators are author-supplied for the
archetype.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

_EPHE_DIR = ROOT / "backend" / "ephe"
if not os.environ.get("SE_EPHE_PATH") and _EPHE_DIR.is_dir():
    os.environ["SE_EPHE_PATH"] = str(_EPHE_DIR)

import pytest  # noqa: E402

from app.engines.prediction_relationship_engine import (  # noqa: E402
    EVENT_COMMITMENT,
    EVENT_FRICTION,
    EVENT_ROMANTIC,
    compute_relationship_prediction,
)


def _swiss_ready() -> bool:
    try:
        import swisseph  # noqa: F401
    except Exception:
        return False
    ephe = os.environ.get("SE_EPHE_PATH")
    return bool(ephe and Path(ephe).is_dir() and list(Path(ephe).glob("*.se1")))


requires_swiss = pytest.mark.skipif(
    not _swiss_ready(),
    reason="Swiss Ephemeris (.se1 files at SE_EPHE_PATH) not available",
)

FIXTURE_DIR = ROOT / "tests" / "fixtures" / "relationship"
KOL = ZoneInfo("Asia/Kolkata")
AS_OF = datetime(2026, 9, 15, 12, 0, tzinfo=KOL)


def _predict(fixture_name: str) -> dict:
    chart = json.loads((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8"))
    return compute_relationship_prediction(chart, as_of=AS_OF)


@requires_swiss
def test_supportive_is_high_confidence_commitment_archetype():
    """promise + dasha support + a slow-planet window -> the 'high' branch."""
    pred = _predict("relationship_supportive_v1.json")
    assert pred["promise_met"] is True
    assert pred["confidence"] == "high"
    assert pred["caution_flag"] is False
    assert pred["transit_summary"]["has_slow_planet_contact"] is True
    assert EVENT_COMMITMENT in pred["event_types"]


@requires_swiss
def test_mixed_is_medium_confidence_opportunity_archetype():
    """promise holds but the dasha is weak (MD/AD lord signifies a blocking house);
    a window keeps it at the 'medium' branch, never 'high'."""
    pred = _predict("relationship_mixed_commitment_v1.json")
    assert pred["promise_met"] is True
    assert pred["confidence"] == "medium"
    assert pred["caution_flag"] is False
    assert pred["transit_windows"], "mixed archetype must carry a timing window"
    assert EVENT_ROMANTIC in pred["event_types"]


@requires_swiss
def test_weak_is_low_confidence_friction_archetype():
    """7th cusp sub-lord points only to friction/separation houses -> no promise,
    caution on, and 'low' regardless of any transit windows present."""
    pred = _predict("relationship_weak_isolation_v1.json")
    assert pred["promise_met"] is False
    assert pred["confidence"] == "low"
    assert pred["caution_flag"] is True
    assert EVENT_FRICTION in pred["event_types"]
    assert "caution" in pred["summary"].lower() or "review" in pred["summary"].lower()
