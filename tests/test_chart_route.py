"""Route-level tests proving /chart/generate serves trusted engine output.

The route must compute exclusively via app.engines.ephemeris_engine (the
JHora-validated engine) and never touch the deprecated
app.core.chart_engine. Geocoding and Supabase are mocked; chart math is
not.
"""

from __future__ import annotations

import json
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
from app.core import chart_engine as old_chart_engine  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.fingerprint import generate_chart_fingerprint  # noqa: E402
from app.engines.ephemeris_engine import compute_ephemeris  # noqa: E402
from app.routers import chart as chart_router  # noqa: E402
from app.schemas.models import ChartData  # noqa: E402

# Route test input reuses the JHora-validated fixture_01 chart: the request
# carries date/time/city; the mocked geocoder pins the exact fixture
# coordinates and IANA zone so the engine input matches the fixture input.
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "charts" / "fixture_01_india.json"
FIXTURE_INPUT = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["input"]

REQUEST_BODY = {
    "birth_date": "1994-03-21",
    "birth_time": "14:35",
    "birth_city": "Gurugram",
}
HEADERS = {"X-User-Id": "route-test-user"}

GEO_RESULT = {
    "latitude": FIXTURE_INPUT["lat"],
    "longitude": FIXTURE_INPUT["lon"],
    "timezone": FIXTURE_INPUT["timezone"],
    "display_name": "Gurugram, Haryana, India",
    "country": "India",
}


@pytest.fixture
def saved_charts():
    return {}


@pytest.fixture
def client(monkeypatch, saved_charts):
    """TestClient with geocoding and Supabase mocked; engine math real."""

    async def fake_geocode(self, city_name: str) -> dict:
        return dict(GEO_RESULT)

    def fake_get_chart(user_id: str, fingerprint: str):
        saved_charts["lookup_fingerprint"] = fingerprint
        return None

    def fake_save_chart(user_id, chart_fingerprint, birth_data, chart_data):
        saved_charts["chart_fingerprint"] = chart_fingerprint
        saved_charts["birth_data"] = birth_data
        saved_charts["chart_data"] = chart_data
        return {"id": "route-test-row-id"}

    monkeypatch.setattr(chart_router.GeocodingService, "geocode", fake_geocode)
    monkeypatch.setattr(chart_router, "get_chart_by_fingerprint", fake_get_chart)
    monkeypatch.setattr(chart_router, "save_chart", fake_save_chart)
    return TestClient(app_main.app)


def trusted_engine_output() -> dict:
    return compute_ephemeris(**FIXTURE_INPUT)


# ---------------------------------------------------------------------------
# Trusted-engine wiring
# ---------------------------------------------------------------------------

def test_route_returns_trusted_engine_planets(client):
    response = client.post("/chart/generate", json=REQUEST_BODY, headers=HEADERS)
    assert response.status_code == 200
    chart = response.json()["chart"]
    expected = trusted_engine_output()

    assert [p["name"] for p in chart["planets"]] == [
        p["name"] for p in expected["planets"]
    ]
    for actual, exp in zip(chart["planets"], expected["planets"]):
        assert actual["longitude"] == pytest.approx(exp["longitude"], abs=1e-9), (
            actual["name"]
        )
        assert actual["retrograde"] == exp["retrograde"]
        assert actual["combust"] == exp["combust"]


def test_route_returns_trusted_placidus_cusps_and_ascendant(client):
    response = client.post("/chart/generate", json=REQUEST_BODY, headers=HEADERS)
    assert response.status_code == 200
    chart = response.json()["chart"]
    expected = trusted_engine_output()

    assert len(chart["houses"]) == 12
    for actual, exp in zip(chart["houses"], expected["houses"]):
        assert actual["house"] == exp["house"]
        assert actual["cusp_longitude"] == pytest.approx(
            exp["cusp_longitude"], abs=1e-9
        )
    assert chart["ascendant"]["longitude"] == pytest.approx(
        expected["ascendant"]["longitude"], abs=1e-9
    )
    assert chart["ascendant"]["sign"] == expected["ascendant"]["sign"]
    assert chart["settings"]["ayanamsa"] == "KP_NEWCOMB"
    assert chart["settings"]["node_type"] == "TRUE"
    assert chart["settings"]["house_system"] == "PLACIDUS"


def test_route_never_calls_old_chart_engine(client, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError(
            "deprecated app.core.chart_engine.generate_chart_data was called"
        )

    monkeypatch.setattr(old_chart_engine, "generate_chart_data", boom)
    response = client.post("/chart/generate", json=REQUEST_BODY, headers=HEADERS)
    assert response.status_code == 200
    # Old-engine output markers must be absent from the planet objects.
    for planet in response.json()["chart"]["planets"]:
        assert "tropical_longitude" not in planet
        assert "sidereal_longitude" not in planet
        assert "is_retrograde" not in planet


def test_chart_payload_is_schema_valid_chart_json(client):
    response = client.post("/chart/generate", json=REQUEST_BODY, headers=HEADERS)
    assert response.status_code == 200
    chart = dict(response.json()["chart"])
    chart.pop("metadata")  # the one documented non-schema key
    parsed = ChartData.model_validate(chart)
    assert parsed.schema_version == "1.0"
    assert parsed.birth.timezone == FIXTURE_INPUT["timezone"]
    assert parsed.birth.approximate_time is False


def test_legacy_metadata_block_for_db_and_scaffold_page(client, saved_charts):
    """save_chart() reads chart_data['metadata']['ayanamsa'/'engine_version']
    for its columns, and the Day 1 scaffold page calls .toFixed on
    metadata.latitude/longitude — these must stay numeric and present."""
    response = client.post("/chart/generate", json=REQUEST_BODY, headers=HEADERS)
    assert response.status_code == 200
    metadata = response.json()["chart"]["metadata"]
    assert isinstance(metadata["latitude"], float)
    assert isinstance(metadata["longitude"], float)
    assert isinstance(metadata["ayanamsa"], float)
    assert 20.0 <= metadata["ayanamsa"] <= 30.0
    assert metadata["engine_version"] == "1.3.0"
    assert metadata["engine_version"] == settings.chart_engine_version
    assert metadata["timezone"] == FIXTURE_INPUT["timezone"]
    # The stored object is the same payload the response carries.
    assert saved_charts["chart_data"] == response.json()["chart"]


def test_chart_fingerprint_uses_current_engine_version(client, saved_charts):
    response = client.post("/chart/generate", json=REQUEST_BODY, headers=HEADERS)
    assert response.status_code == 200

    expected = generate_chart_fingerprint(
        birth_date=REQUEST_BODY["birth_date"],
        birth_time=REQUEST_BODY["birth_time"],
        latitude=GEO_RESULT["latitude"],
        longitude=GEO_RESULT["longitude"],
        timezone=GEO_RESULT["timezone"],
        ayanamsa="krishnamurti",
        house_system="placidus",
        node_type="true_node",
        engine_version=settings.chart_engine_version,
    )
    assert response.json()["chart_fingerprint"] == expected
    assert saved_charts["lookup_fingerprint"] == expected
    assert saved_charts["chart_fingerprint"] == expected


def test_chart_fingerprint_changes_when_engine_version_changes():
    common = {
        "birth_date": REQUEST_BODY["birth_date"],
        "birth_time": REQUEST_BODY["birth_time"],
        "latitude": GEO_RESULT["latitude"],
        "longitude": GEO_RESULT["longitude"],
        "timezone": GEO_RESULT["timezone"],
        "ayanamsa": "krishnamurti",
        "house_system": "placidus",
        "node_type": "true_node",
    }

    current = generate_chart_fingerprint(**common, engine_version="1.3.0")
    next_version = generate_chart_fingerprint(**common, engine_version="1.2.1")

    assert current != next_version


# ---------------------------------------------------------------------------
# Contract preservation
# ---------------------------------------------------------------------------

def test_response_envelope_unchanged(client):
    response = client.post("/chart/generate", json=REQUEST_BODY, headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "cache_status", "chart_id", "chart_fingerprint", "chart",
    }
    assert body["cache_status"] == "MISS"
    assert body["chart_id"] == "route-test-row-id"


def test_missing_user_header_still_401(client):
    response = client.post("/chart/generate", json=REQUEST_BODY)
    assert response.status_code == 401


def test_cache_hit_returns_stored_chart_untouched(client, monkeypatch, saved_charts):
    sentinel = {"sentinel": True}

    def fake_hit(user_id, fingerprint):
        return {"id": "cached-row", "chart_json": sentinel}

    monkeypatch.setattr(chart_router, "get_chart_by_fingerprint", fake_hit)
    response = client.post("/chart/generate", json=REQUEST_BODY, headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["cache_status"] == "HIT"
    assert body["chart"] == sentinel
    assert "chart_data" not in saved_charts  # save path not reached


# ---------------------------------------------------------------------------
# Structured engine errors surface as structured HTTP errors
# ---------------------------------------------------------------------------

def test_high_latitude_maps_to_400_lat_unsupported(client, monkeypatch):
    async def polar_geocode(self, city_name: str) -> dict:
        return {**GEO_RESULT, "latitude": 70.0}

    monkeypatch.setattr(chart_router.GeocodingService, "geocode", polar_geocode)
    response = client.post("/chart/generate", json=REQUEST_BODY, headers=HEADERS)
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "LAT_UNSUPPORTED"


def test_unknown_timezone_maps_to_422(client, monkeypatch):
    async def bad_tz_geocode(self, city_name: str) -> dict:
        return {**GEO_RESULT, "timezone": "Asia/NotAZone"}

    monkeypatch.setattr(chart_router.GeocodingService, "geocode", bad_tz_geocode)
    response = client.post("/chart/generate", json=REQUEST_BODY, headers=HEADERS)
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "INVALID_TIMEZONE"
