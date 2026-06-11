"""Day 1 ephemeris engine tests (docs/ephemeris.md section 10).

JHora comparison tests skip with reason PENDING_JHORA_VALUES until the
founder exports real expectations into tests/fixtures/charts/*.json
(TASKBOARD T1.3). Everything else must pass unconditionally.
"""

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from backend.engines.ephemeris_engine import (  # noqa: E402
    COMBUSTION_ORBS,
    PLANET_ORDER,
    SIGNS,
    EphemerisError,
    InvalidCoordinatesError,
    InvalidDatetimeError,
    InvalidTimezoneError,
    LatUnsupportedError,
    angular_separation,
    compute_ephemeris,
    ephemeris_files_ok,
    ephemeris_files_status,
    is_combust,
)

FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "charts"

PLANET_TOLERANCE_DEG = 5.0 / 3600.0  # 5 arc-seconds
CUSP_TOLERANCE_DEG = 0.01


def load_fixtures():
    fixtures = []
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            fixtures.append(json.load(f))
    return fixtures


FIXTURES = load_fixtures()
FIXTURE_IDS = [f["chart_id"] for f in FIXTURES]

# One computation per fixture for the whole session; the engine is pure.
_CHART_CACHE = {}


def chart_for(fixture):
    chart_id = fixture["chart_id"]
    if chart_id not in _CHART_CACHE:
        _CHART_CACHE[chart_id] = compute_ephemeris(**fixture["input"])
    return _CHART_CACHE[chart_id]


def expected_or_skip(fixture, key):
    """Return fixture['expected'][key] or skip the test as pending."""
    expected = fixture.get("expected") or {}
    value = expected.get(key)
    if fixture.get("status") == "PENDING_JHORA" or value in (None, {}, []):
        pytest.skip("PENDING_JHORA_VALUES")
    return value


# ---------------------------------------------------------------------------
# 1. Basic output shape (never skipped)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture", FIXTURES, ids=FIXTURE_IDS)
def test_exactly_nine_planets_in_fixed_order(fixture):
    planets = chart_for(fixture)["planets"]
    assert len(planets) == 9
    assert [p["name"] for p in planets] == PLANET_ORDER


@pytest.mark.parametrize("fixture", FIXTURES, ids=FIXTURE_IDS)
def test_planet_objects_carry_engine_owned_fields(fixture):
    expected_keys = {
        "name", "longitude", "sign", "sign_lord", "sign_degree",
        "retrograde", "combust", "speed_deg_per_day",
    }
    for planet in chart_for(fixture)["planets"]:
        assert set(planet.keys()) == expected_keys, planet["name"]
        assert planet["sign"] in SIGNS
        assert isinstance(planet["retrograde"], bool)
        assert isinstance(planet["combust"], bool)


@pytest.mark.parametrize("fixture", FIXTURES, ids=FIXTURE_IDS)
def test_twelve_cusps_ordered(fixture):
    houses = chart_for(fixture)["houses"]
    assert len(houses) == 12
    assert [h["house"] for h in houses] == list(range(1, 13))


@pytest.mark.parametrize("fixture", FIXTURES, ids=FIXTURE_IDS)
def test_planet_longitudes_normalized(fixture):
    for planet in chart_for(fixture)["planets"]:
        assert 0.0 <= planet["longitude"] < 360.0, planet["name"]
        assert 0.0 <= planet["sign_degree"] < 30.0, planet["name"]


@pytest.mark.parametrize("fixture", FIXTURES, ids=FIXTURE_IDS)
def test_cusp_longitudes_normalized(fixture):
    for house in chart_for(fixture)["houses"]:
        assert 0.0 <= house["cusp_longitude"] < 360.0, house["house"]


@pytest.mark.parametrize("fixture", FIXTURES, ids=FIXTURE_IDS)
def test_cusp_1_equals_ascendant(fixture):
    chart = chart_for(fixture)
    cusp_1 = chart["houses"][0]["cusp_longitude"]
    asc = chart["ascendant"]["longitude"]
    assert abs(cusp_1 - asc) < 1e-6


@pytest.mark.parametrize("fixture", FIXTURES, ids=FIXTURE_IDS)
def test_settings_block_locked_values(fixture):
    settings = chart_for(fixture)["settings"]
    assert settings["ayanamsa"] == "KP_NEWCOMB"
    assert settings["node_type"] == "TRUE"
    assert settings["house_system"] == "PLACIDUS"
    assert settings["zodiac"] == "SIDEREAL"
    # Sanity band per docs/chart-schema.md section 3.
    assert 20.0 <= settings["ayanamsa_value_deg"] <= 30.0


def test_determinism():
    fixture = FIXTURES[0]
    first = compute_ephemeris(**fixture["input"])
    second = compute_ephemeris(**fixture["input"])
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


# ---------------------------------------------------------------------------
# 2. Rahu / Ketu (never skipped)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture", FIXTURES, ids=FIXTURE_IDS)
def test_ketu_exactly_opposite_rahu(fixture):
    planets = {p["name"]: p for p in chart_for(fixture)["planets"]}
    rahu, ketu = planets["Rahu"], planets["Ketu"]
    assert abs(ketu["longitude"] - (rahu["longitude"] + 180.0) % 360.0) < 1e-9
    assert ketu["speed_deg_per_day"] == rahu["speed_deg_per_day"]
    assert ketu["retrograde"] == rahu["retrograde"]


def test_rahu_is_true_node_not_mean_node():
    """Regression guard: the engine's Rahu must equal a direct TRUE_NODE
    call at the same Julian day (mean node can sit up to 1.5 deg away)."""
    import swisseph as swe

    chart = chart_for(FIXTURES[0])
    jd_ut = chart["birth"]["julian_day_ut"]
    swe.set_sid_mode(swe.SIDM_KRISHNAMURTI, 0.0, 0.0)
    xx, _ = swe.calc_ut(
        jd_ut, swe.TRUE_NODE,
        swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED,
    )
    rahu = next(p for p in chart["planets"] if p["name"] == "Rahu")
    assert abs(rahu["longitude"] - xx[0] % 360.0) < 1e-9


# ---------------------------------------------------------------------------
# 3. Latitude guard (never skipped)
# ---------------------------------------------------------------------------

BASE_INPUT = FIXTURES[0]["input"]


@pytest.mark.parametrize("lat", [70.0, -70.0, 66.01, 89.9])
def test_high_latitude_raises_lat_unsupported(lat):
    with pytest.raises(LatUnsupportedError) as excinfo:
        compute_ephemeris(
            datetime_local=BASE_INPUT["datetime_local"],
            timezone=BASE_INPUT["timezone"],
            lat=lat,
            lon=BASE_INPUT["lon"],
        )
    assert excinfo.value.code == "LAT_UNSUPPORTED"
    # Structured error, not a raw trace: it serializes to a dict.
    assert excinfo.value.to_dict()["error"] == "LAT_UNSUPPORTED"


def test_latitude_66_boundary_is_supported():
    chart = compute_ephemeris(
        datetime_local=BASE_INPUT["datetime_local"],
        timezone=BASE_INPUT["timezone"],
        lat=66.0,
        lon=BASE_INPUT["lon"],
    )
    assert len(chart["houses"]) == 12


@pytest.mark.parametrize(
    "lat,lon", [(95.0, 77.0), (-95.0, 77.0), (28.0, 200.0), (28.0, -181.0)]
)
def test_out_of_range_coordinates_raise_structured_error(lat, lon):
    with pytest.raises(InvalidCoordinatesError) as excinfo:
        compute_ephemeris(
            datetime_local=BASE_INPUT["datetime_local"],
            timezone=BASE_INPUT["timezone"],
            lat=lat,
            lon=lon,
        )
    assert excinfo.value.code == "INVALID_COORDINATES"


# ---------------------------------------------------------------------------
# 4. Ephemeris file guard (never skipped, never crashes)
# ---------------------------------------------------------------------------

def test_missing_se_ephe_path_returns_false_not_crash(monkeypatch):
    monkeypatch.delenv("SE_EPHE_PATH", raising=False)
    status = ephemeris_files_status()
    assert status["ok"] is False
    assert status["env_var_set"] is False
    assert ephemeris_files_ok() is False


def test_invalid_se_ephe_path_returns_false_not_crash(monkeypatch):
    monkeypatch.setenv("SE_EPHE_PATH", r"C:\definitely\not\a\real\path")
    status = ephemeris_files_status()
    assert status["ok"] is False
    assert status["env_var_set"] is True
    assert status["path_exists"] is False
    assert ephemeris_files_ok() is False


def test_dir_without_se1_files_returns_false(monkeypatch, tmp_path):
    monkeypatch.setenv("SE_EPHE_PATH", str(tmp_path))
    status = ephemeris_files_status()
    assert status["ok"] is False
    assert status["path_exists"] is True
    assert status["se1_file_count"] == 0


def test_se1_file_layer_detected(monkeypatch, tmp_path):
    """A .se1 file present passes the file-layer checks. The overall ok
    additionally requires the Swiss probe (a dummy file cannot satisfy
    it), so only the layered fields are asserted here."""
    (tmp_path / "sepl_18.se1").write_bytes(b"\x00" * 16)
    monkeypatch.setenv("SE_EPHE_PATH", str(tmp_path))
    status = ephemeris_files_status()
    assert status["env_var_set"] is True
    assert status["path_exists"] is True
    assert status["se1_file_count"] == 1
    assert isinstance(status["ok"], bool)  # reached the probe, no crash


# ---------------------------------------------------------------------------
# 5. Timezone handling (never skipped)
# ---------------------------------------------------------------------------

def test_dst_conversion_single_step():
    """New York noon in July is EDT (UTC-4): 12:00 local -> 16:00Z. A
    double conversion would land on 20:00Z; no conversion on 12:00Z."""
    chart = compute_ephemeris(
        datetime_local="2000-07-15T12:00:00",
        timezone="America/New_York",
        lat=40.7128,
        lon=-74.006,
    )
    assert chart["birth"]["datetime_utc"] == "2000-07-15T16:00:00Z"


def test_ist_conversion_single_step():
    """Asia/Kolkata is UTC+5:30 with no DST: 14:35 local -> 09:05Z."""
    chart = chart_for(FIXTURES[0])
    assert chart["birth"]["datetime_utc"] == "1994-03-21T09:05:00Z"


def test_same_instant_two_zones_identical_chart():
    """05:30 IST and 00:00 UTC are the same instant; Julian day and every
    longitude must match exactly. Catches any zone-dependent double
    conversion."""
    kolkata = compute_ephemeris(
        datetime_local="2020-01-01T05:30:00",
        timezone="Asia/Kolkata",
        lat=28.4595,
        lon=77.0266,
    )
    utc = compute_ephemeris(
        datetime_local="2020-01-01T00:00:00",
        timezone="UTC",
        lat=28.4595,
        lon=77.0266,
    )
    assert kolkata["birth"]["julian_day_ut"] == utc["birth"]["julian_day_ut"]
    assert kolkata["birth"]["datetime_utc"] == utc["birth"]["datetime_utc"]
    for p_k, p_u in zip(kolkata["planets"], utc["planets"]):
        assert p_k["longitude"] == p_u["longitude"], p_k["name"]


def test_midnight_birth_rolls_back_utc_date():
    """00:10 IST on Jan 1 is 18:40Z on Dec 31 of the previous year."""
    chart = chart_for(FIXTURES[2])
    assert chart["birth"]["datetime_utc"] == "2000-12-31T18:40:00Z"
    # Julian day for 18:40 UT is past the .5 day boundary of Dec 31.
    assert chart["birth"]["julian_day_ut"] == pytest.approx(
        2451910.277777778, abs=1e-6
    )


def test_unknown_timezone_raises_structured_error():
    with pytest.raises(InvalidTimezoneError) as excinfo:
        compute_ephemeris(
            datetime_local="1994-03-21T14:35:00",
            timezone="Asia/NotAZone",
            lat=28.4595,
            lon=77.0266,
        )
    assert excinfo.value.code == "INVALID_TIMEZONE"


def test_timezone_never_assumed_aware_input_rejected():
    """The engine refuses datetimes that carry their own offset; the IANA
    zone argument is the only source of zone truth (no India default)."""
    with pytest.raises(InvalidDatetimeError) as excinfo:
        compute_ephemeris(
            datetime_local="1994-03-21T14:35:00+05:30",
            timezone="Asia/Kolkata",
            lat=28.4595,
            lon=77.0266,
        )
    assert excinfo.value.code == "INVALID_DATETIME"


# ---------------------------------------------------------------------------
# 6. Combustion units (orb table is defined in docs/ephemeris.md section 6)
# ---------------------------------------------------------------------------

def test_retro_mercury_13_deg_not_combust():
    # Retro orb 12 < separation 13 -> NOT combust (spec's explicit case).
    assert is_combust("Mercury", 113.0, 100.0, retrograde=True) is False


def test_direct_mercury_13_deg_combust():
    # Direct orb 14 >= separation 13 -> combust.
    assert is_combust("Mercury", 113.0, 100.0, retrograde=False) is True


def test_sun_never_combust():
    assert is_combust("Sun", 100.0, 100.0, retrograde=False) is False


@pytest.mark.parametrize("node", ["Rahu", "Ketu"])
def test_nodes_never_combust(node):
    assert is_combust(node, 100.0, 100.0, retrograde=False) is False
    assert is_combust(node, 100.0, 100.0, retrograde=True) is False


def test_separation_across_zero_boundary():
    # Sun at 358, planet at 5: separation is 7, not 353.
    assert angular_separation(5.0, 358.0) == pytest.approx(7.0)
    # Moon orb 12 -> combust at 7 deg separation across the boundary.
    assert is_combust("Moon", 5.0, 358.0, retrograde=False) is True


def test_combust_flags_present_in_chart_output():
    planets = {p["name"]: p for p in chart_for(FIXTURES[0])["planets"]}
    assert planets["Sun"]["combust"] is False
    assert planets["Rahu"]["combust"] is False
    assert planets["Ketu"]["combust"] is False
    for name, planet in planets.items():
        if name in COMBUSTION_ORBS:
            sun_lon = planets["Sun"]["longitude"]
            orb = COMBUSTION_ORBS[name][1 if planet["retrograde"] else 0]
            expected = angular_separation(planet["longitude"], sun_lon) <= orb
            assert planet["combust"] is expected, name


# ---------------------------------------------------------------------------
# 7. JHora fixture comparisons (skip ONLY these while values are pending)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture", FIXTURES, ids=FIXTURE_IDS)
def test_jhora_planet_longitudes(fixture):
    expected_planets = expected_or_skip(fixture, "planets")
    planets = {p["name"]: p for p in chart_for(fixture)["planets"]}
    for name, expected_lon in expected_planets.items():
        actual = planets[name]["longitude"]
        assert angular_separation(actual, expected_lon) <= PLANET_TOLERANCE_DEG, (
            f"{name}: engine {actual:.6f} vs JHora {expected_lon:.6f}"
        )


@pytest.mark.parametrize("fixture", FIXTURES, ids=FIXTURE_IDS)
def test_jhora_rahu_explicit(fixture):
    """Explicit Rahu assertion guarding mean-node regression even if the
    loop test above were ever weakened (docs/ephemeris.md sec 10 test 2)."""
    expected_planets = expected_or_skip(fixture, "planets")
    if "Rahu" not in expected_planets:
        pytest.skip("PENDING_JHORA_VALUES")
    rahu = next(p for p in chart_for(fixture)["planets"] if p["name"] == "Rahu")
    assert angular_separation(
        rahu["longitude"], expected_planets["Rahu"]
    ) <= PLANET_TOLERANCE_DEG


@pytest.mark.parametrize("fixture", FIXTURES, ids=FIXTURE_IDS)
def test_jhora_cusp_longitudes(fixture):
    expected_cusps = expected_or_skip(fixture, "cusps")
    houses = {h["house"]: h for h in chart_for(fixture)["houses"]}
    for house_number, expected_lon in expected_cusps.items():
        actual = houses[int(house_number)]["cusp_longitude"]
        assert angular_separation(actual, expected_lon) <= CUSP_TOLERANCE_DEG, (
            f"cusp {house_number}: engine {actual:.6f} vs JHora {expected_lon:.6f}"
        )


@pytest.mark.parametrize("fixture", FIXTURES, ids=FIXTURE_IDS)
def test_jhora_ascendant_sign_exact(fixture):
    expected_sign = expected_or_skip(fixture, "ascendant_sign")
    assert chart_for(fixture)["ascendant"]["sign"] == expected_sign
