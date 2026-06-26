"""Tests for the strict Gemini payload builder (Phase 2).

The payload builder is the fabrication gate: it reduces a unified engine output
to names, numbers, dates and templated event labels only — no interpretive
prose. These tests assert (a) the payload always carries the documented key set,
(b) no free-text/interpretive string ever survives into a payload value, and
(c) both hold across all three domain engines (career / finance / relationship),
run on their own founder fixtures.

The transit side of every engine touches Swiss Ephemeris, so the cross-engine
tests are gated on the bundled ``.se1`` files; a hand-built engine-output case
covers the pure builder mechanics with no Swiss dependency.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

_EPHE_DIR = ROOT / "backend" / "ephe"
if not os.environ.get("SE_EPHE_PATH") and _EPHE_DIR.is_dir():
    os.environ["SE_EPHE_PATH"] = str(_EPHE_DIR)

import pytest  # noqa: E402

from app.engines.ephemeris_engine import _sign_fields, normalize_longitude  # noqa: E402
from app.engines.house_engine import occupants as house_occupants  # noqa: E402
from app.engines.kp_engine import get_kp_sub_lord  # noqa: E402
from app.engines.nakshatra_engine import nakshatra_block, nakshatra_name  # noqa: E402
from app.engines.prediction_career_engine import compute_career_prediction  # noqa: E402
from app.engines.prediction_finance_engine import compute_finance_prediction  # noqa: E402
from app.engines.prediction_relationship_engine import (  # noqa: E402
    compute_relationship_prediction,
)
from app.synthesis.payload_builder import (  # noqa: E402
    ALL_PLANETS,
    PAYLOAD_KEYS,
    build_payload,
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

FIXTURES = ROOT / "tests" / "fixtures"
KOL = ZoneInfo("Asia/Kolkata")
AS_OF = datetime(2026, 9, 15, 12, 0, tzinfo=KOL)

_CONFIDENCE_TIERS = {"high", "medium", "low"}
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_HOUSE_NUM = re.compile(r"\d{1,2}")


# --------------------------------------------------------------------------- #
# Build one unified engine output per domain (on the founder fixtures).
# --------------------------------------------------------------------------- #
def _build_golden_career_chart(chart_fixture_id: str) -> dict:
    """Swiss-independent natal chart from a golden chart fixture (career path)."""
    fx = json.loads(
        (FIXTURES / "charts" / f"{chart_fixture_id}.json").read_text(encoding="utf-8")
    )
    inp, exp = fx["input"], fx["expected"]
    cusps = [normalize_longitude(exp["cusps"][str(h)]) for h in range(1, 13)]

    planets = []
    for name, raw_lon in exp["planets"].items():
        lon = normalize_longitude(raw_lon)
        sf = _sign_fields(lon)
        kp = get_kp_sub_lord(lon)
        planets.append(
            {
                "name": name, "longitude": lon, **sf,
                "retrograde": False, "combust": False, "speed_deg_per_day": 0.0,
                "nakshatra": nakshatra_block(lon),
                "kp": {"star_lord": kp["star_lord"], "sub_lord": kp["sub_lord"]},
                "significator_of_houses": [],
                "significator_levels": {},
            }
        )

    occ = house_occupants(planets, cusps)
    house_of = {pn: h for h, names in occ.items() for pn in names}
    for planet in planets:
        planet["house_occupied"] = house_of[planet["name"]]

    houses = []
    for h in range(1, 13):
        lon = cusps[h - 1]
        sf = _sign_fields(lon)
        kp = get_kp_sub_lord(lon)
        houses.append(
            {
                "house": h, "cusp_longitude": lon,
                "cusp_sign": sf["sign"], "cusp_sign_lord": sf["sign_lord"],
                "cusp_nakshatra": nakshatra_name(lon),
                "kp": {"star_lord": kp["star_lord"], "sub_lord": kp["sub_lord"]},
                "occupants": occ[h], "significators": None,
            }
        )

    return {
        "schema_version": "1.2",
        "birth": {"datetime_local": inp["datetime_local"], "timezone": inp["timezone"]},
        "dashas": None, "planets": planets, "houses": houses,
    }


def _career_output() -> dict:
    fx = json.loads(
        (FIXTURES / "career" / "career_supportive_v1.json").read_text(encoding="utf-8")
    )
    chart = _build_golden_career_chart(fx["chart_input_ref"])
    return compute_career_prediction(chart, as_of=datetime.fromisoformat(fx["as_of"]))


def _finance_output() -> dict:
    chart = json.loads(
        (FIXTURES / "finance" / "finance_supportive_v1.json").read_text(encoding="utf-8")
    )
    return compute_finance_prediction(chart, as_of=AS_OF)


def _relationship_output() -> dict:
    chart = json.loads(
        (FIXTURES / "relationship" / "relationship_supportive_v1.json").read_text(
            encoding="utf-8"
        )
    )
    return compute_relationship_prediction(chart, as_of=AS_OF)


_DOMAIN_BUILDERS = {
    "career": _career_output,
    "finance": _finance_output,
    "relationship": _relationship_output,
}


@pytest.fixture(params=sorted(_DOMAIN_BUILDERS), ids=sorted(_DOMAIN_BUILDERS))
def engine_output(request) -> dict:
    return _DOMAIN_BUILDERS[request.param]()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _all_strings(obj, out: list[str]) -> None:
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for value in obj.values():
            _all_strings(value, out)
    elif isinstance(obj, list):
        for value in obj:
            _all_strings(value, out)


def _string_leaves(payload: dict) -> list[str]:
    out: list[str] = []
    _all_strings(payload, out)
    return out


# --------------------------------------------------------------------------- #
# Hand-built engine output — pure builder mechanics, no Swiss dependency.
# --------------------------------------------------------------------------- #
def _synthetic_engine_output() -> dict:
    return {
        "domain": "finance",
        "promise_met": True,
        "confidence": "high",
        "signal_strength": 70,
        "caution_flag": False,
        "summary": "As of 2026-09-15 this is reflective guidance, not a guarantee.",
        "caveat": "Internal prediction. Treat as directional, not definitive.",
        "dasha_timing": {
            "md_lord": "Jupiter", "ad_lord": "Jupiter", "pd_lord": "Mercury",
            "md_supports": True, "ad_supports": True, "pd_supports": False,
        },
        "transit_windows": [
            {
                "start_date": "2026-10-01", "end_date": "2026-10-12",
                "domain": "finance", "window_score": 4.2, "pd_overlap": False,
                "trigger_count": 3,
                "triggers": [
                    {
                        "planet": "Saturn", "natal_point": "natal_jupiter",
                        "natal_point_longitude": 200.0, "contact_date": "2026-10-05",
                        "angular_diff_deg": 0.4, "weight": 3,
                    },
                    {
                        "planet": "Mars", "natal_point": "cusp_2",
                        "natal_point_longitude": 211.0, "contact_date": "2026-10-08",
                        "angular_diff_deg": 0.9, "weight": 2,
                    },
                ],
            }
        ],
        "transit_summary": {
            "windows_found": 1, "has_slow_planet_contact": True,
            "next_contact": {
                "planet": "Jupiter", "natal_point": "cusp_11",
                "natal_longitude": 121.0, "estimated_date": "2027-02-01",
                "days_away": 140,
            },
            "framing": "A slow-planet contact window is active in the scanned span.",
        },
        "event_types": ["income-rise window", "financial-decision review window"],
        "cusp_sublords": {
            "primary_houses": {"2": "Venus", "11": "Venus"},
            "sublord_significations": {"Venus": [2, 6, 11]},
        },
    }


def test_synthetic_payload_has_exactly_the_required_keys():
    payload = build_payload(_synthetic_engine_output())
    assert set(payload) == set(PAYLOAD_KEYS)


def test_synthetic_payload_harvests_longitudes_and_drops_prose():
    payload = build_payload(_synthetic_engine_output())

    # Natal longitudes are harvested from the *natal point* a trigger contacts
    # (and from next_contact), not from the transit planet that does the
    # contacting. So Saturn-on-natal_jupiter contributes Jupiter@200, and the
    # cusp points contribute houses.
    assert payload["planets"] == {"Jupiter": 200.0}
    assert payload["houses"]["2"] == 211.0
    assert payload["houses"]["11"] == 121.0        # cusp_11 from next_contact

    # Dasha names only; transit windows reduced to dates + trigger planet names.
    assert payload["dasha_period"] == {
        "md_lord": "Jupiter", "ad_lord": "Jupiter", "pd_lord": "Mercury",
    }
    window = payload["transit_windows"][0]
    assert window == {
        "start_date": "2026-10-01", "end_date": "2026-10-12",
        "trigger_planets": ["Mars", "Saturn"],
    }
    assert payload["signal_strength"] == 70 and isinstance(payload["signal_strength"], int)

    # The engine's interpretive prose must never reach the payload.
    blob = " ".join(_string_leaves(payload))
    assert "reflective guidance" not in blob
    assert "not a guarantee" not in blob
    assert "directional" not in blob
    assert _synthetic_engine_output()["summary"] not in blob


# --------------------------------------------------------------------------- #
# Cross-engine: all three real domain outputs.
# --------------------------------------------------------------------------- #
@requires_swiss
def test_payload_has_required_keys_for_every_domain(engine_output):
    payload = build_payload(engine_output)
    assert set(payload) == set(PAYLOAD_KEYS)
    assert payload["domain"] == engine_output["domain"]
    assert set(payload["cusp_sublords"]) == {"primary_houses", "sublord_significations"}
    assert set(payload["dasha_period"]) == {"md_lord", "ad_lord", "pd_lord"}
    assert isinstance(payload["signal_strength"], int)
    assert payload["confidence"] in _CONFIDENCE_TIERS


@requires_swiss
def test_no_interpretive_text_in_payload_values(engine_output):
    """Every string leaf is a name, tier, date, house number or event label.

    Nothing free-text or interpretive (the engine's templated summary/caveat/
    framing prose) may survive into a payload value.
    """
    payload = build_payload(engine_output)
    domain = engine_output["domain"]
    allowed_events = set(payload["event_types"])

    for value in _string_leaves(payload):
        ok = (
            value in ALL_PLANETS
            or value == domain
            or value in _CONFIDENCE_TIERS
            or value in allowed_events
            or _ISO_DATE.fullmatch(value) is not None
            or _HOUSE_NUM.fullmatch(value) is not None
        )
        assert ok, f"unexpected free-text payload value: {value!r}"

    # And the engine's own prose is provably absent.
    blob = " ".join(_string_leaves(payload))
    assert engine_output["summary"] not in blob
    assert "reflective guidance" not in blob
