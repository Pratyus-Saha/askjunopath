"""Route-level tests for the INTERNAL career prediction v1 wrapper.

The internal route (``POST /internal/predict/career``) exists ONLY so the backend
can exercise the deterministic Career V1 engine (D029) through an API-like path.
It is dev/internal-gated, NOT public:

* it is gated to non-production environments (``settings.environment``);
* it is never wired into ``/chart/generate`` and populates no public field;
* it bumps no ``schema_version`` / ``chart_engine_version``;
* it calls no LLM and keeps the engine's ``medium`` confidence cap;
* it returns the evidence-first object EXACTLY from ``compute_career_prediction``,
  wrapped in an envelope that carries an ``internal_only`` flag + caveat.

These tests assert the route contract, the gating, the no-invented-entity safety
contract, and that the PUBLIC chart route still exposes NO career data and keeps
``chart.dashas`` null + the reserved significator fields empty.

Charts are built through the same trusted path the engine tests use
(``_build_chart_payload`` over ``compute_ephemeris``); the output is compared to a
direct ``compute_career_prediction`` call on the same chart, so assertions hold
under Swiss *or* Moshier timing (no exact dasha lords/dates are asserted here).
"""

from __future__ import annotations

import copy
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

import json  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import main as app_main  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.engines.ephemeris_engine import compute_ephemeris  # noqa: E402
from app.engines.prediction_career_engine import compute_career_prediction  # noqa: E402
from app.routers import chart as chart_router  # noqa: E402
from app.schemas.models import BirthDataRequest  # noqa: E402

INTERNAL_PATH = "/internal/predict/career"

KOL = ZoneInfo("Asia/Kolkata")
AS_OF = datetime(2026, 6, 17, 12, 0, tzinfo=KOL)
AS_OF_ISO = AS_OF.isoformat()  # "2026-06-17T12:00:00+05:30"

USER1 = {
    "date": "1998-08-14",
    "time": "06:45:00",
    "place": "Kolkata, India",
    "latitude": 22.5725,
    "longitude": 88.363889,
    "iana_timezone": "Asia/Kolkata",
}

# Banned deterministic claims; the hedge words the output must use instead.
BANNED_PHRASES = (
    "will get",
    "guaranteed",
    "will definitely",
    "definitely",
    "you will fail",
    "must leave",
    "certainly",
    "100%",
    "promise you",
)
HEDGE_MARKERS = ("may", "suggest", "indicat", "reflective", "not a guarantee")

CLASSICAL_PLANETS = {
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
}
# Bodies that must NEVER appear in v1 output (KP/Vimshottari use 9 grahas only).
FORBIDDEN_BODIES = ["Pluto", "Neptune", "Uranus", "Chiron", "Lilith"]

DEV_ENVIRONMENTS = ["development", "dev", "local", "test"]
PROD_ENVIRONMENTS = ["production", "prod", "staging", "PRODUCTION", "", "anything-else"]


# --------------------------------------------------------------------------- #
# Chart + request helpers
# --------------------------------------------------------------------------- #
def _user1_chart() -> dict:
    """A full, schema-valid ChartData payload built through the trusted path.

    Works under Swiss or Moshier (positions differ, structure does not), so the
    route's ChartData validation always passes here.
    """
    req = BirthDataRequest(
        birth_date=USER1["date"], birth_time=USER1["time"][:5], birth_city=USER1["place"]
    )
    eph = compute_ephemeris(
        datetime_local=f"{USER1['date']}T{USER1['time']}",
        timezone=USER1["iana_timezone"],
        lat=USER1["latitude"],
        lon=USER1["longitude"],
    )
    return chart_router._build_chart_payload(
        ephemeris=eph,
        place_label=USER1["place"],
        request_data=req,
        geo_lat=USER1["latitude"],
        geo_lon=USER1["longitude"],
        timezone_str=USER1["iana_timezone"],
    )


@pytest.fixture
def client():
    return TestClient(app_main.app)


@pytest.fixture(autouse=True)
def _dev_environment(monkeypatch):
    """Default every test to an internal-enabled environment with NO token guard
    configured, unless a test overrides either."""
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.delenv("INTERNAL_CAREER_API_TOKEN", raising=False)


def _post(client, *, chart=None, chart_id=None, as_of=AS_OF_ISO, headers=None):
    body: dict = {}
    if chart is not None:
        body["chart"] = chart
    if chart_id is not None:
        body["chart_id"] = chart_id
    if as_of is not None:
        body["as_of"] = as_of
    return client.post(INTERNAL_PATH, json=body, headers=headers)


# --------------------------------------------------------------------------- #
# Entity-extraction helpers (no invented planets / houses / dates)
# --------------------------------------------------------------------------- #
def _all_strings(obj, out):
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _all_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _all_strings(v, out)


def _blob(obj) -> str:
    out: list[str] = []
    _all_strings(obj, out)
    return " ".join(out)


def _mentioned_planets(pred: dict) -> set[str]:
    blob = _blob(pred)
    return {p for p in CLASSICAL_PLANETS if re.search(rf"\b{p}\b", blob)}


def _structured_house_ints(pred: dict) -> set[int]:
    houses: set[int] = set()
    houses.update(pred["promise"]["tenth_cusp_sub_lord_signifies"])
    houses.update(pred["promise"]["promised_career_houses"])
    for info in pred["promise"]["career_house_cusp_sub_lords"].values():
        houses.update(info["signifies"])
    for level in pred["dasha_support"].values():
        houses.update(level["signifies"])
    for item in pred["evidence"]:
        houses.update(item["signifies"])
    houses.update(int(k) for k in pred["career_house_activation"])
    return houses


def _mentioned_dates(pred: dict) -> set[str]:
    return set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", _blob(pred)))


def _valid_dates(pred: dict) -> set[str]:
    stack = pred["current_dasha_stack"]
    return {
        pred["as_of"][:10],
        stack["antardasha_window"][0],
        stack["antardasha_window"][1],
        stack["pratyantardasha_window"][0],
        stack["pratyantardasha_window"][1],
    }


# --------------------------------------------------------------------------- #
# 1. The route returns Career V1 output, exactly from the engine.
# --------------------------------------------------------------------------- #
def test_internal_route_returns_career_v1_output(client):
    chart = _user1_chart()
    resp = _post(client, chart=chart)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert set(body) == {"internal_only", "caveat", "as_of", "prediction"}
    assert body["as_of"] == AS_OF_ISO

    pred = body["prediction"]
    assert pred["version"] == "career-v1"
    # Returned object is EXACTLY the deterministic engine output for this chart.
    expected = compute_career_prediction(chart, as_of=AS_OF)
    assert pred == expected


def test_internal_route_envelope_has_internal_only_flag_and_caveat(client):
    body = _post(client, chart=_user1_chart()).json()
    assert body["internal_only"] is True
    assert isinstance(body["caveat"], str) and body["caveat"].strip()
    assert "internal" in body["caveat"].lower()
    # The engine's own caveat is preserved inside the prediction.
    assert body["prediction"]["caveat"].strip()
    assert "not a guarantee" in body["prediction"]["caveat"].lower()


def test_internal_route_keeps_medium_confidence_cap(client):
    pred = _post(client, chart=_user1_chart()).json()["prediction"]
    assert pred["confidence"] in {"low", "medium"}
    assert pred["confidence"] != "high"
    assert "not validated" in pred["confidence_basis"]["note"].lower()


# --------------------------------------------------------------------------- #
# 2. as_of: required timezone-aware, or safely derived.
# --------------------------------------------------------------------------- #
def test_internal_route_omitted_as_of_is_safely_derived(client):
    resp = _post(client, chart=_user1_chart(), as_of=None)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    derived = datetime.fromisoformat(body["as_of"])
    assert derived.tzinfo is not None  # tz-aware
    assert body["prediction"]["as_of"] == body["as_of"]


def test_internal_route_rejects_naive_as_of(client):
    resp = _post(client, chart=_user1_chart(), as_of="2026-06-17T12:00:00")
    assert resp.status_code == 422, resp.text


def test_internal_route_rejects_unparseable_as_of(client):
    resp = _post(client, chart=_user1_chart(), as_of="not-a-datetime")
    assert resp.status_code == 422, resp.text


def test_internal_route_accepts_utc_z_as_of(client):
    resp = _post(client, chart=_user1_chart(), as_of="2026-06-17T06:30:00Z")
    assert resp.status_code == 200, resp.text
    assert datetime.fromisoformat(resp.json()["as_of"]).tzinfo is not None


# --------------------------------------------------------------------------- #
# 3. Chart input handling (inline only in v1; chart_id rejected clearly).
# --------------------------------------------------------------------------- #
def test_internal_route_requires_a_chart(client):
    resp = _post(client, as_of=AS_OF_ISO)  # neither chart nor chart_id
    assert resp.status_code == 422, resp.text


def test_internal_route_rejects_invalid_chart_shape(client):
    resp = _post(client, chart={"not": "a-chart"})
    assert resp.status_code == 422, resp.text


def test_internal_route_chart_id_is_unsupported_in_v1(client):
    resp = _post(client, chart_id="some-row-id")
    assert resp.status_code == 400, resp.text
    detail = json.dumps(resp.json()).lower()
    assert "chart_id" in detail
    assert "chart" in detail  # tells caller to pass an inline chart


# --------------------------------------------------------------------------- #
# 4. Internal/dev gating.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("env", DEV_ENVIRONMENTS)
def test_internal_route_available_in_dev_environments(client, monkeypatch, env):
    monkeypatch.setattr(settings, "environment", env)
    resp = _post(client, chart=_user1_chart())
    assert resp.status_code == 200, f"{env}: {resp.text}"


@pytest.mark.parametrize("env", PROD_ENVIRONMENTS)
def test_internal_route_hidden_outside_dev_environments(client, monkeypatch, env):
    monkeypatch.setattr(settings, "environment", env)
    # A fully valid body must still 404 — only the environment gate matters.
    resp = _post(client, chart=_user1_chart())
    assert resp.status_code == 404, f"{env}: {resp.text}"


# --------------------------------------------------------------------------- #
# 4b. Optional token guard (defense-in-depth), layered on top of the env gate.
#     Every failure is 404 (never 401/403) to hide route existence.
# --------------------------------------------------------------------------- #
INTERNAL_TOKEN = "s3cret-internal-career-token"


def test_no_token_configured_allows_dev_access_without_header(client, monkeypatch):
    monkeypatch.delenv("INTERNAL_CAREER_API_TOKEN", raising=False)
    resp = _post(client, chart=_user1_chart())  # no token header needed
    assert resp.status_code == 200, resp.text


def test_token_configured_missing_header_returns_404(client, monkeypatch):
    monkeypatch.setenv("INTERNAL_CAREER_API_TOKEN", INTERNAL_TOKEN)
    resp = _post(client, chart=_user1_chart())  # header absent
    assert resp.status_code == 404, resp.text


def test_token_configured_wrong_header_returns_404(client, monkeypatch):
    monkeypatch.setenv("INTERNAL_CAREER_API_TOKEN", INTERNAL_TOKEN)
    resp = _post(
        client,
        chart=_user1_chart(),
        headers={"X-Internal-Career-Token": "wrong-token"},
    )
    assert resp.status_code == 404, resp.text


def test_token_configured_correct_header_returns_200(client, monkeypatch):
    monkeypatch.setenv("INTERNAL_CAREER_API_TOKEN", INTERNAL_TOKEN)
    resp = _post(
        client,
        chart=_user1_chart(),
        headers={"X-Internal-Career-Token": INTERNAL_TOKEN},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["internal_only"] is True


@pytest.mark.parametrize("env", ["production", "staging", "prod"])
def test_production_returns_404_even_with_correct_token(client, monkeypatch, env):
    monkeypatch.setenv("INTERNAL_CAREER_API_TOKEN", INTERNAL_TOKEN)
    monkeypatch.setattr(settings, "environment", env)  # env gate wins over token
    resp = _post(
        client,
        chart=_user1_chart(),
        headers={"X-Internal-Career-Token": INTERNAL_TOKEN},
    )
    assert resp.status_code == 404, f"{env}: {resp.text}"


# --------------------------------------------------------------------------- #
# 5. Safety contract — no unsafe certainty, no invented entities.
# --------------------------------------------------------------------------- #
def test_internal_output_has_no_unsafe_certainty_phrases(client):
    body = _post(client, chart=_user1_chart()).json()
    pred = body["prediction"]
    prose = " ".join(
        [pred["summary"], pred["timing_interpretation"], pred["caveat"], body["caveat"]]
    ).lower()
    for banned in BANNED_PHRASES:
        assert banned not in prose, f"banned phrase leaked: {banned!r}"
    assert any(marker in prose for marker in HEDGE_MARKERS)


def test_internal_output_invents_no_planets(client):
    chart = _user1_chart()
    pred = _post(client, chart=chart).json()["prediction"]
    chart_planets = {p["name"] for p in chart["planets"]}
    for planet in _mentioned_planets(pred):
        assert planet in chart_planets, f"invented planet: {planet}"
    blob = _blob(pred)
    for body_name in FORBIDDEN_BODIES:
        assert not re.search(rf"\b{body_name}\b", blob), f"forbidden body: {body_name}"
    for item in pred["evidence"]:
        assert item["source"] in chart_planets, item


def test_internal_output_invents_no_houses(client):
    pred = _post(client, chart=_user1_chart()).json()["prediction"]
    for house in _structured_house_ints(pred):
        assert 1 <= house <= 12, f"invented house: {house}"


def test_internal_output_invents_no_dates(client):
    pred = _post(client, chart=_user1_chart()).json()["prediction"]
    valid = _valid_dates(pred)
    for date_text in _mentioned_dates(pred):
        assert date_text in valid, f"invented date {date_text} not in {sorted(valid)}"


# --------------------------------------------------------------------------- #
# 6. Internal-only: the route consumes a reserved-null chart and mutates nothing.
# --------------------------------------------------------------------------- #
def test_internal_route_does_not_mutate_input_chart(client):
    chart = _user1_chart()
    before = copy.deepcopy(chart)
    resp = _post(client, chart=chart)
    assert resp.status_code == 200, resp.text
    assert chart == before  # the caller's object is untouched


def test_internal_route_consumes_reserved_null_chart(client):
    """The chart the internal path operates on carries no public career data:
    dashas null, significator fields reserved/empty (D023)."""
    chart = _user1_chart()
    assert chart["dashas"] is None
    for planet in chart["planets"]:
        assert planet["significator_of_houses"] == []
        assert planet["significator_levels"] == {}
    for house in chart["houses"]:
        assert house["significators"] is None
    # And the response envelope never echoes a populated chart back.
    body = _post(client, chart=chart).json()
    assert "chart" not in body
    assert "dashas" not in body["prediction"]


# --------------------------------------------------------------------------- #
# 7. The PUBLIC chart route still exposes NO career data.
#    (Covers: public route unchanged, chart.dashas null, reserved sig fields.)
# --------------------------------------------------------------------------- #
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "charts" / "fixture_01_india.json"
FIXTURE_INPUT = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["input"]
PUBLIC_REQUEST_BODY = {
    "birth_date": "1994-03-21",
    "birth_time": "14:35",
    "birth_city": "Gurugram",
}
PUBLIC_HEADERS = {"X-User-Id": "internal-route-test-user"}
GEO_RESULT = {
    "latitude": FIXTURE_INPUT["lat"],
    "longitude": FIXTURE_INPUT["lon"],
    "timezone": FIXTURE_INPUT["timezone"],
    "display_name": "Gurugram, Haryana, India",
    "country": "India",
}

# Career-prediction field names that must NEVER surface in public chart output.
CAREER_LEAK_KEYS = {
    "career_house_activation",
    "current_dasha_stack",
    "dasha_support",
    "supporting_factors",
    "blocking_factors",
    "career_themes",
    "timing_interpretation",
    "confidence_basis",
    "promised_career_houses",
}


@pytest.fixture
def public_client(monkeypatch):
    async def fake_geocode(self, city_name: str) -> dict:
        return dict(GEO_RESULT)

    def fake_get_chart(user_id: str, fingerprint: str):
        return None

    def fake_save_chart(user_id, chart_fingerprint, birth_data, chart_data):
        return {"id": "internal-route-test-row-id"}

    monkeypatch.setattr(chart_router.GeocodingService, "geocode", fake_geocode)
    monkeypatch.setattr(chart_router, "get_chart_by_fingerprint", fake_get_chart)
    monkeypatch.setattr(chart_router, "save_chart", fake_save_chart)
    return TestClient(app_main.app)


def test_public_chart_route_exposes_no_career_prediction(public_client):
    resp = public_client.post(
        "/chart/generate", json=PUBLIC_REQUEST_BODY, headers=PUBLIC_HEADERS
    )
    assert resp.status_code == 200, resp.text
    chart = resp.json()["chart"]

    assert "career" not in chart
    assert "prediction" not in chart
    # prediction_features exists in the schema but its career slot stays empty.
    assert chart["prediction_features"]["career"] is None
    blob_keys = set(re.findall(r'"([a-z_]+)"', json.dumps(chart)))
    assert blob_keys.isdisjoint(CAREER_LEAK_KEYS), blob_keys & CAREER_LEAK_KEYS


def test_public_chart_route_keeps_dashas_null(public_client):
    resp = public_client.post(
        "/chart/generate", json=PUBLIC_REQUEST_BODY, headers=PUBLIC_HEADERS
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["chart"]["dashas"] is None


def test_public_chart_route_keeps_significator_fields_reserved(public_client):
    resp = public_client.post(
        "/chart/generate", json=PUBLIC_REQUEST_BODY, headers=PUBLIC_HEADERS
    )
    assert resp.status_code == 200, resp.text
    chart = resp.json()["chart"]
    for planet in chart["planets"]:
        assert planet["significator_of_houses"] == []
        assert planet["significator_levels"] == {}
    for house in chart["houses"]:
        assert house["significators"] is None


# --------------------------------------------------------------------------- #
# 8. No schema / engine version movement from the internal surface existing.
# --------------------------------------------------------------------------- #
def test_internal_surface_does_not_move_versions(client):
    assert settings.chart_engine_version == "1.4.0"
    chart = _post(client, chart=_user1_chart())
    assert chart.status_code == 200
    assert settings.chart_engine_version == "1.4.0"
    # The chart the route consumed is still schema v1.2.
    assert _user1_chart()["schema_version"] == "1.2"
