"""JHora KP validation for public chart KP star/sub lord output.

The source fixture is the founder-supplied raw Jagannatha Hora export at
tests/fixtures/jhora/kp_validation_5charts_raw.txt. The structured JSON keeps
only the requested inputs and Body/Cusp table expectations:
9 planets plus 12 house cusps, with expected Nakshatra lord -> kp.star_lord
and Sub lord -> kp.sub_lord.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

import pytest  # noqa: E402

from app.engines.ephemeris_engine import compute_ephemeris  # noqa: E402
from app.routers.chart import _build_chart_payload  # noqa: E402
from app.schemas.models import BirthDataRequest  # noqa: E402

FIXTURE_PATH = (
    ROOT / "tests" / "fixtures" / "jhora" / "kp_validation_5charts_expected.json"
)
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
PLANET_NAMES = [
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
    "Rahu",
    "Ketu",
]


def _iso_date(date_text: str) -> str:
    return datetime.strptime(date_text, "%d %B %Y").date().isoformat()


def _route_time(time_text: str) -> str:
    return time_text[:5]


def _chart_for(fixture_chart: dict) -> dict:
    chart_input = fixture_chart["input"]
    request_data = BirthDataRequest(
        birth_date=_iso_date(chart_input["date"]),
        birth_time=_route_time(chart_input["time"]),
        birth_city=chart_input["place"],
    )
    ephemeris = compute_ephemeris(
        datetime_local=f"{request_data.birth_date}T{chart_input['time']}",
        timezone=chart_input["iana_timezone"],
        lat=chart_input["latitude"],
        lon=chart_input["longitude"],
    )
    return _build_chart_payload(
        ephemeris=ephemeris,
        place_label=chart_input["place"],
        request_data=request_data,
        geo_lat=chart_input["latitude"],
        geo_lon=chart_input["longitude"],
        timezone_str=chart_input["iana_timezone"],
    )


@pytest.mark.parametrize(
    "fixture_chart", FIXTURE["charts"], ids=[c["chart_id"] for c in FIXTURE["charts"]]
)
def test_planet_kp_star_and_sub_lords_match_jhora(fixture_chart):
    chart = _chart_for(fixture_chart)
    actual_by_name = {planet["name"]: planet["kp"] for planet in chart["planets"]}

    assert set(actual_by_name) == set(PLANET_NAMES)
    for planet_name in PLANET_NAMES:
        assert actual_by_name[planet_name] == (
            fixture_chart["expected"]["planets"][planet_name]
        ), f"{fixture_chart['chart_id']} {planet_name}"


@pytest.mark.parametrize(
    "fixture_chart", FIXTURE["charts"], ids=[c["chart_id"] for c in FIXTURE["charts"]]
)
def test_house_kp_star_and_sub_lords_match_jhora(fixture_chart):
    chart = _chart_for(fixture_chart)
    actual_by_house = {
        str(house["house"]): house["kp"]
        for house in chart["houses"]
    }

    assert set(actual_by_house) == {str(i) for i in range(1, 13)}
    for house_number in range(1, 13):
        house_key = str(house_number)
        assert actual_by_house[house_key] == (
            fixture_chart["expected"]["houses"][house_key]
        ), f"{fixture_chart['chart_id']} house {house_key}"
