"""Ephemeris engine: the single trusted source for Day 1 chart math.

Spec: docs/ephemeris.md v1.0 (frozen with chart.json v1.0).
Settings are locked per DECISIONS.md D002 and are NOT user-configurable:
sidereal zodiac, KP-Newcomb/Krishnamurti ayanamsa, true node (Ketu = Rahu
+ 180 deg), Placidus houses.

This module owns ONLY the ephemeris-level chart.json fields (birth.*,
settings.*, ascendant, planets[].<position fields>, houses[].<cusp fields>).
Nakshatra, KP, house occupancy, dasha, strength, divisional, and transit
fields belong to later engines and are never computed here.
"""

import os
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import swisseph as swe

from app.core.config import get_se_ephe_path

# ---------------------------------------------------------------------------
# Fixed tables (docs/ephemeris.md section 5)
# ---------------------------------------------------------------------------

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

SIGN_LORDS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

# Fixed output order; "Pluto" is a validation error per AGENTS.md section 4.
PLANET_ORDER = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
    "Rahu", "Ketu",
]

# Rahu uses TRUE_NODE per D002; MEAN_NODE is forbidden. Ketu is derived.
_SWE_BODY_IDS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
    "Rahu": swe.TRUE_NODE,
}

# Combustion orbs in degrees (docs/ephemeris.md section 6, master plan
# Section 10): {planet: (direct_orb, retrograde_orb)}. The Sun, Rahu and
# Ketu are never combust and are absent from this table on purpose.
COMBUSTION_ORBS = {
    "Moon": (12.0, 12.0),
    "Mars": (17.0, 17.0),
    "Mercury": (14.0, 12.0),
    "Jupiter": (11.0, 11.0),
    "Venus": (10.0, 8.0),
    "Saturn": (15.0, 15.0),
}

# Placidus is undefined near the poles (docs/ephemeris.md section 3).
MAX_SUPPORTED_ABS_LAT = 66.0

# FLG_TRUEPOS is mandatory: the JHora reference exports TRUE/geometric
# (Drik) positions, not apparent ones. Without it every planet sits
# arc-seconds off the 5 arc-sec gate (Sun ~20" of annual aberration)
# while the Moon stays nearly exact. Founder ruling 2026-06-11,
# docs/ephemeris.md section 5.
_CALC_FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED | swe.FLG_TRUEPOS


# ---------------------------------------------------------------------------
# Structured errors (the API layer maps codes to HTTP statuses; tests assert
# the code, never a stack trace)
# ---------------------------------------------------------------------------

class EphemerisError(Exception):
    """Base for all structured engine errors. Carries a stable `code`."""

    code = "EPHEMERIS_ERROR"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def to_dict(self) -> dict:
        return {"error": self.code, "message": self.message}


class LatUnsupportedError(EphemerisError):
    """|lat| > 66: Placidus house math is undefined near the poles."""

    code = "LAT_UNSUPPORTED"


class InvalidTimezoneError(EphemerisError):
    """The supplied string is not a known IANA timezone."""

    code = "INVALID_TIMEZONE"


class InvalidCoordinatesError(EphemerisError):
    """lat outside [-90, 90] or lon outside [-180, 180]."""

    code = "INVALID_COORDINATES"


class InvalidDatetimeError(EphemerisError):
    """datetime_local is not a parseable naive ISO 8601 local datetime."""

    code = "INVALID_DATETIME"


# ---------------------------------------------------------------------------
# Swiss Ephemeris initialization (call order matters: ephe path first, then
# sidereal mode, both BEFORE any calc_ut/houses_ex — docs/ephemeris.md sec 2)
# ---------------------------------------------------------------------------

def _initialize_swe() -> None:
    """(Re)apply the locked Swiss Ephemeris configuration.

    Runs at every engine entry rather than once at import: it is cheap, and
    it protects against any other code in the process having changed the
    sidereal mode or ephemeris path between calls.
    """
    # Always reset the path: passing None restores the library default.
    # Skipping this when the env var is unset would leave a stale path
    # behind if anything else in the process changed it (e.g. the file
    # guard's probe). The unset-variable fallback is the shared config
    # default, the same one transit_engine uses (audit finding #16).
    swe.set_ephe_path(get_se_ephe_path())
    # KP-Newcomb / Krishnamurti ayanamsa, locked per D002. Never Lahiri,
    # never user-configurable in this engine.
    swe.set_sid_mode(swe.SIDM_KRISHNAMURTI, 0.0, 0.0)


# ---------------------------------------------------------------------------
# Time handling (one conversion, at the engine boundary — spec section 4)
# ---------------------------------------------------------------------------

def _parse_local_naive(datetime_local: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(datetime_local)
    except (ValueError, TypeError) as exc:
        raise InvalidDatetimeError(
            f"datetime_local must be naive ISO 8601, got {datetime_local!r}"
        ) from exc
    if parsed.tzinfo is not None:
        raise InvalidDatetimeError(
            "datetime_local must be naive (no UTC offset); the IANA "
            "timezone argument supplies the zone"
        )
    return parsed


def _local_to_utc(datetime_local: str, tz_name: str) -> datetime:
    """Convert the naive local birth datetime to UTC, exactly once.

    Ambiguous local times (DST fold) resolve with fold=0, i.e. the earlier
    UTC offset, per DECISIONS.md D012(e). zoneinfo applies fold=0 by
    default; this comment records that it is a pinned convention, not an
    accident.
    """
    naive = _parse_local_naive(datetime_local)
    try:
        zone = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise InvalidTimezoneError(f"Unknown IANA timezone: {tz_name!r}") from exc
    local_aware = naive.replace(tzinfo=zone, fold=0)
    return local_aware.astimezone(dt_timezone.utc)


def _julian_day_ut(utc_dt: datetime) -> float:
    decimal_hour = (
        utc_dt.hour
        + utc_dt.minute / 60.0
        + utc_dt.second / 3600.0
        + utc_dt.microsecond / 3_600_000_000.0
    )
    return swe.julday(
        utc_dt.year, utc_dt.month, utc_dt.day, decimal_hour, swe.GREG_CAL
    )


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def normalize_longitude(longitude: float) -> float:
    return longitude % 360.0


def angular_separation(lon_a: float, lon_b: float) -> float:
    """Shortest angular distance between two longitudes, in [0, 180]."""
    d = abs(lon_a - lon_b) % 360.0
    return min(d, 360.0 - d)


def _sign_fields(longitude: float) -> dict:
    sign = SIGNS[int(longitude // 30.0) % 12]
    return {
        "sign": sign,
        "sign_lord": SIGN_LORDS[sign],
        "sign_degree": longitude % 30.0,
    }


def is_combust(planet_name: str, longitude: float, sun_longitude: float,
               retrograde: bool) -> bool:
    """Combustion per the fixed orb table. Sun/Rahu/Ketu: never combust.

    Mercury and Venus use their tighter orb when retrograde; all other
    orbs are direction-independent.
    """
    orbs = COMBUSTION_ORBS.get(planet_name)
    if orbs is None:
        return False
    orb = orbs[1] if retrograde else orbs[0]
    return angular_separation(longitude, sun_longitude) <= orb


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _validate_coordinates(lat: float, lon: float) -> None:
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        raise InvalidCoordinatesError(
            f"lat must be in [-90, 90] and lon in [-180, 180]; "
            f"got lat={lat}, lon={lon}"
        )
    if abs(lat) > MAX_SUPPORTED_ABS_LAT:
        raise LatUnsupportedError(
            f"Latitude {lat} is beyond +/-{MAX_SUPPORTED_ABS_LAT}; Placidus "
            f"houses are undefined at high latitudes"
        )


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def _compute_planets(jd_ut: float) -> list:
    planets = []
    rahu = None
    sun_longitude = None

    for name in PLANET_ORDER:
        if name == "Ketu":
            # Ketu is exactly opposite Rahu; speed and retrograde flag are
            # Rahu's (the true node oscillates; no special-casing beyond
            # the 180-degree offset). Spec section 5.
            longitude = normalize_longitude(rahu["longitude"] + 180.0)
            planet = {
                "name": "Ketu",
                "longitude": longitude,
                **_sign_fields(longitude),
                "retrograde": rahu["retrograde"],
                "combust": False,
                "speed_deg_per_day": rahu["speed_deg_per_day"],
            }
        else:
            xx, _retflag = swe.calc_ut(jd_ut, _SWE_BODY_IDS[name], _CALC_FLAGS)
            # calc_ut returns (xx, retflag); xx[0] = longitude, xx[3] =
            # longitudinal speed in deg/day (verified for pyswisseph
            # 2.10.3.2).
            longitude = normalize_longitude(xx[0])
            speed = xx[3]
            planet = {
                "name": name,
                "longitude": longitude,
                **_sign_fields(longitude),
                "retrograde": speed < 0.0,
                "combust": False,
                "speed_deg_per_day": speed,
            }
        if name == "Sun":
            sun_longitude = planet["longitude"]
        if name == "Rahu":
            rahu = planet
        planets.append(planet)

    # Combustion pass after all longitudes are known. is_combust returns
    # False for Sun/Rahu/Ketu by construction.
    for planet in planets:
        planet["combust"] = is_combust(
            planet["name"], planet["longitude"], sun_longitude,
            planet["retrograde"],
        )
    return planets


def _compute_houses(jd_ut: float, lat: float, lon: float) -> tuple:
    """Placidus sidereal cusps and ascendant.

    pyswisseph 2.10.3.2 return shape (verified in a REPL before mapping):
    houses_ex returns a 2-tuple (cusps, ascmc) where `cusps` is a plain
    12-tuple indexed 0..11 for houses 1..12 (NOT the C API's 1..12
    indexing), and `ascmc` is an 8-tuple with ascmc[0] = ascendant.
    Placidus invariant: cusps[0] == ascmc[0].
    """
    cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b'P', swe.FLG_SIDEREAL)

    houses = []
    for house_number, raw_cusp in enumerate(cusps, start=1):
        cusp_longitude = normalize_longitude(raw_cusp)
        sign_fields = _sign_fields(cusp_longitude)
        houses.append({
            "house": house_number,
            "cusp_longitude": cusp_longitude,
            "cusp_sign": sign_fields["sign"],
            "cusp_sign_lord": sign_fields["sign_lord"],
        })

    asc_longitude = normalize_longitude(ascmc[0])
    ascendant = {
        "longitude": asc_longitude,
        **{k: v for k, v in _sign_fields(asc_longitude).items()
           if k in ("sign", "sign_degree")},
    }
    return houses, ascendant


def compute_ephemeris(datetime_local: str, timezone: str, lat: float,
                      lon: float) -> dict:
    """Compute the ephemeris-owned portion of a chart.

    Args:
        datetime_local: naive ISO 8601 local birth time, e.g.
            "1994-03-21T14:35:00".
        timezone: IANA zone name, e.g. "Asia/Kolkata". Never assumed;
            always supplied by the caller.
        lat: decimal degrees, north positive.
        lon: decimal degrees, east positive.

    Returns a dict whose keys map 1:1 onto chart.json v1.0 field names
    (docs/chart-schema.md): birth, settings, ascendant, planets (9, fixed
    order), houses (12, ordered 1..12). Full float precision is kept here;
    rounding to 4 decimals happens at serialization, not in this engine.

    Raises structured EphemerisError subclasses, never bare exceptions,
    for all guarded input problems.
    """
    _validate_coordinates(lat, lon)

    # One local->UTC conversion, here, at the engine boundary. The UTC
    # datetime feeds swe.julday; local time never reaches Swiss Ephemeris.
    utc_dt = _local_to_utc(datetime_local, timezone)

    _initialize_swe()

    jd_ut = _julian_day_ut(utc_dt)
    ayanamsa_value = swe.get_ayanamsa_ut(jd_ut)

    planets = _compute_planets(jd_ut)
    houses, ascendant = _compute_houses(jd_ut, lat, lon)

    return {
        "birth": {
            "datetime_local": datetime_local,
            "datetime_utc": utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "timezone": timezone,
            "lat": lat,
            "lon": lon,
            "julian_day_ut": jd_ut,
        },
        "settings": {
            "ayanamsa": "KP_NEWCOMB",
            "ayanamsa_value_deg": ayanamsa_value,
            "node_type": "TRUE",
            "house_system": "PLACIDUS",
            "zodiac": "SIDEREAL",
        },
        "ascendant": ascendant,
        "planets": planets,
        "houses": houses,
    }


# ---------------------------------------------------------------------------
# Ephemeris file guard (docs/ephemeris.md section 2; consumed by /health)
# ---------------------------------------------------------------------------

def ephemeris_files_status() -> dict:
    """Structured ephemeris-file check. Never raises.

    Checks, in order: SE_EPHE_PATH is set; the path exists; at least one
    .se1 file is inside it; and a probe swe.calc_ut actually used the
    Swiss ephemeris rather than silently falling back to Moshier (the
    returned flag bits carry FLG_MOSEPH when fallback happened).
    """
    status = {
        "ok": False,
        "env_var_set": False,
        "path_exists": False,
        "se1_file_count": 0,
        "swieph_in_use": False,
        "path": None,
        "detail": "",
    }
    try:
        ephe_path = os.environ.get("SE_EPHE_PATH")
        if not ephe_path:
            status["detail"] = "SE_EPHE_PATH is not set"
            return status
        status["env_var_set"] = True
        status["path"] = ephe_path

        path = Path(ephe_path)
        if not path.is_dir():
            status["detail"] = f"SE_EPHE_PATH does not exist: {ephe_path}"
            return status
        status["path_exists"] = True

        se1_count = len(list(path.glob("*.se1")))
        status["se1_file_count"] = se1_count
        if se1_count == 0:
            status["detail"] = f"no .se1 files found in {ephe_path}"
            return status

        # Probe: ask for FLG_SWIEPH and inspect the flags actually used.
        # A clean swe state is needed so previously-opened files do not
        # mask a bad path.
        swe.close()
        swe.set_ephe_path(ephe_path)
        try:
            _xx, retflag = swe.calc_ut(
                swe.julday(2000, 1, 1, 12.0, swe.GREG_CAL),
                swe.SUN,
                swe.FLG_SWIEPH,
            )
            swieph_used = bool(retflag & swe.FLG_SWIEPH) and not bool(
                retflag & swe.FLG_MOSEPH
            )
        except Exception as exc:  # probe failure is a result, not a crash
            status["detail"] = f"probe calculation failed: {exc}"
            return status
        finally:
            # Restore the locked engine configuration regardless of the
            # probe outcome.
            _initialize_swe()

        status["swieph_in_use"] = swieph_used
        if not swieph_used:
            status["detail"] = (
                "Swiss ephemeris files present but calc fell back to "
                "Moshier; files may be unreadable or wrong for the date"
            )
            return status

        status["ok"] = True
        status["detail"] = f"{se1_count} .se1 file(s) at {ephe_path}"
        return status
    except Exception as exc:  # absolute backstop: /health must never 500
        status["detail"] = f"unexpected error during ephemeris check: {exc}"
        return status


def ephemeris_files_ok() -> bool:
    """Boolean wrapper for /health. True only when .se1 files exist at
    SE_EPHE_PATH and the Swiss ephemeris is actually being used."""
    return ephemeris_files_status()["ok"]
