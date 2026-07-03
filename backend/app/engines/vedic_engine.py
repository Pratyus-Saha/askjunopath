"""Vedic (Parashari) calculation engine — a SEPARATE fork beside the KP engine.

This module is downstream-of-ayanamsa and is fully forked from the KP path. It
shares ONLY the Swiss Ephemeris tropical layer (raw pyswisseph + bundled .se1
files) and the time->Julian-Day helper (``_julian_day_ut``). It never imports or
mutates KP-specific code, and never touches ``ephemeris_engine``'s sidereal
mode, node choice, or house system.

Locked settings (task spec)
---------------------------
* Ayanamsa: Lahiri (``swe.SIDM_LAHIRI``).
* Houses: whole-sign, Swiss Ephemeris system ``'W'``. House 1 = Lagna's rasi;
  a planet's house = its rasi counted from the Lagna rasi.
* Nodes: MEAN (``swe.MEAN_NODE``); Ketu = Rahu + 180 deg.
* Dasha: Vimshottari, seeded from the Moon (see ``vedic_dasha``).

Outputs (exactly, nothing more): planet placements (sign/degree/nakshatra/pada),
Lagna, whole-sign house occupancy, D-9 & D-10 varga signs, current 4-level
Vimshottari path, dignity, graha drishti, and a settings block.

Field-B caveat: dignity and graha drishti are COMPUTED, not JHora-validated (no
ground truth exists in the fixtures). They are pending a manual textbook check.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone as dt_timezone

import swisseph as swe

# Shared time->Julian-Day helper (the ONLY import from the KP layer).
from app.engines.ephemeris_engine import _julian_day_ut
from app.engines.vedic_dasha import compute_current_dasha

# ---------------------------------------------------------------------------
# Fixed zodiac tables (forked copy; the KP engine is untouched)
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

# (name, nakshatra lord) — 27 nakshatras, Ashwini = index 1.
NAKSHATRAS = [
    ("Ashwini", "Ketu"), ("Bharani", "Venus"), ("Krittika", "Sun"),
    ("Rohini", "Moon"), ("Mrigashira", "Mars"), ("Ardra", "Rahu"),
    ("Punarvasu", "Jupiter"), ("Pushya", "Saturn"), ("Ashlesha", "Mercury"),
    ("Magha", "Ketu"), ("Purva Phalguni", "Venus"), ("Uttara Phalguni", "Sun"),
    ("Hasta", "Moon"), ("Chitra", "Mars"), ("Swati", "Rahu"),
    ("Vishakha", "Jupiter"), ("Anuradha", "Saturn"), ("Jyeshtha", "Mercury"),
    ("Mula", "Ketu"), ("Purva Ashadha", "Venus"), ("Uttara Ashadha", "Sun"),
    ("Shravana", "Moon"), ("Dhanishta", "Mars"), ("Shatabhisha", "Rahu"),
    ("Purva Bhadrapada", "Jupiter"), ("Uttara Bhadrapada", "Saturn"),
    ("Revati", "Mercury"),
]

# Fixed output order. Rahu is MEAN_NODE on this path; Ketu is derived.
PLANET_ORDER = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
    "Rahu", "Ketu",
]

_SWE_BODY_IDS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE,  # MEAN node on the Vedic path (never TRUE_NODE).
}

# Sidereal, true/geometric (Drik) positions — matches the JHora oracle the KP
# engine already validated against. FLG_TRUEPOS is flagged for reconfirmation
# once vedic_fixtures.json exists (it is a per-planet, not constant, effect).
_CALC_FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_TRUEPOS

# Arc-second grid (exact boundary math; floats only in output degree fields).
FULL_ZODIAC_ARCSEC = 1_296_000
NAKSHATRA_ARCSEC = 48_000   # 13 deg 20 min
PADA_ARCSEC = 12_000        # 3 deg 20 min

SETTINGS = {"ayanamsa": "lahiri", "houses": "whole_sign", "nodes": "mean"}


# ---------------------------------------------------------------------------
# Dignity tables (standard Parashari). Fields 6 — COMPUTED, not JHora-validated.
# ---------------------------------------------------------------------------

# Exaltation SIGN + deep-exaltation degree (a planet anywhere in its exaltation
# sign is reported "exalted"; the degree is the point of maximum exaltation).
EXALTATION = {
    "Sun": ("Aries", 10.0),
    "Moon": ("Taurus", 3.0),
    "Mars": ("Capricorn", 28.0),
    "Mercury": ("Virgo", 15.0),
    "Jupiter": ("Cancer", 5.0),
    "Venus": ("Pisces", 27.0),
    "Saturn": ("Libra", 20.0),
}

# Debilitation sign = the 7th sign from exaltation.
DEBILITATION = {
    planet: SIGNS[(SIGNS.index(sign) + 6) % 12]
    for planet, (sign, _deg) in EXALTATION.items()
}

OWN_SIGNS = {
    "Sun": ["Leo"],
    "Moon": ["Cancer"],
    "Mars": ["Aries", "Scorpio"],
    "Mercury": ["Gemini", "Virgo"],
    "Jupiter": ["Sagittarius", "Pisces"],
    "Venus": ["Taurus", "Libra"],
    "Saturn": ["Capricorn", "Aquarius"],
}

# Moolatrikona: (sign, low_deg_inclusive, high_deg_exclusive). The Moon boundary
# (Taurus 4 deg) varies by text (3 vs 4) — documented for the field-B check.
MOOLATRIKONA = {
    "Sun": ("Leo", 0.0, 20.0),
    "Moon": ("Taurus", 4.0, 30.0),
    "Mars": ("Aries", 0.0, 12.0),
    "Mercury": ("Virgo", 15.0, 20.0),
    "Jupiter": ("Sagittarius", 0.0, 10.0),
    "Venus": ("Libra", 0.0, 15.0),
    "Saturn": ("Aquarius", 0.0, 20.0),
}

# Classical natural (naisargika) relationship table, BPHS. Friends/enemies are
# listed; every other classical planet is neutral. Rahu/Ketu are intentionally
# absent (not in the classical table). "great friend"/"great enemy" are
# Panchadha/COMPOUND categories requiring the temporal relationship the spec
# defers, so they are never emitted in v1.
NATURAL_FRIENDS = {
    "Sun": {"Moon", "Mars", "Jupiter"},
    "Moon": {"Sun", "Mercury"},
    "Mars": {"Sun", "Moon", "Jupiter"},
    "Mercury": {"Sun", "Venus"},
    "Jupiter": {"Sun", "Moon", "Mars"},
    "Venus": {"Mercury", "Saturn"},
    "Saturn": {"Mercury", "Venus"},
}
NATURAL_ENEMIES = {
    "Sun": {"Venus", "Saturn"},
    "Moon": set(),
    "Mars": {"Mercury"},
    "Mercury": {"Moon"},
    "Jupiter": {"Mercury", "Venus"},
    "Venus": {"Sun", "Moon"},
    "Saturn": {"Sun", "Moon", "Mars"},
}

# Graha drishti: extra house-offsets each planet aspects, beyond the universal
# 7th (offset 6). Offsets are "N-th house from self", counted inclusively, so
# the k-th house from house H is offset (k-1). Rahu/Ketu cast no aspects here.
_ASPECT_OFFSETS = {
    "Mars": (3, 6, 7),      # 4th, 7th, 8th
    "Jupiter": (4, 6, 8),   # 5th, 7th, 9th
    "Saturn": (2, 6, 9),    # 3rd, 7th, 10th
}
_DEFAULT_ASPECT_OFFSETS = (6,)   # 7th only
_NO_ASPECT = frozenset({"Rahu", "Ketu"})


# ---------------------------------------------------------------------------
# Swiss ephemeris init + time (fork; shares only _julian_day_ut)
# ---------------------------------------------------------------------------

def _initialize_swe() -> None:
    """Apply the Vedic Swiss Ephemeris config: ephe path + Lahiri sidereal mode.

    Re-applied at every entry so a preceding KP call (Krishnamurti) cannot leak
    its sidereal mode into this path, and vice versa.
    """
    ephe_path = os.environ.get("SE_EPHE_PATH")
    swe.set_ephe_path(ephe_path if ephe_path else None)
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0.0, 0.0)


def _fixed_offset_tz(gmt_offset_hours: float) -> dt_timezone:
    return dt_timezone(timedelta(hours=gmt_offset_hours))


def _local_naive_to_aware(datetime_local: str,
                          gmt_offset_hours: float) -> datetime:
    """Parse a naive local ISO datetime and attach a FIXED offset.

    The harness uses a fixed gmt_offset (not IANA tz lookup) so engine
    correctness is decoupled from geocoding/timezone resolution.
    """
    parsed = datetime.fromisoformat(datetime_local)
    if parsed.tzinfo is not None:
        raise ValueError("datetime_local must be naive; gmt_offset supplies the zone")
    return parsed.replace(tzinfo=_fixed_offset_tz(gmt_offset_hours))


# ---------------------------------------------------------------------------
# Geometry / placement helpers
# ---------------------------------------------------------------------------

def _norm(longitude: float) -> float:
    return longitude % 360.0


def _arcsec(longitude: float) -> int:
    return round(_norm(longitude) * 3600.0) % FULL_ZODIAC_ARCSEC


def sign_index(longitude: float) -> int:
    """0-based sign index (Aries = 0)."""
    return int(_norm(longitude) // 30.0) % 12


def nakshatra_of(longitude: float) -> tuple[int, str, str]:
    """(1-based index, name, lord) for a sidereal longitude."""
    idx0 = _arcsec(longitude) // NAKSHATRA_ARCSEC
    name, lord = NAKSHATRAS[idx0]
    return idx0 + 1, name, lord


def pada_of(longitude: float) -> int:
    """1-based pada (quarter) within the nakshatra."""
    offset = _arcsec(longitude) % NAKSHATRA_ARCSEC
    return (offset // PADA_ARCSEC) + 1


def degree_in_nakshatra(longitude: float) -> float:
    return (_arcsec(longitude) % NAKSHATRA_ARCSEC) / 3600.0


def _degree_in_nakshatra_precise(longitude: float) -> float:
    """Full-precision degrees into the nakshatra (NO arc-second rounding).

    Used ONLY for the Vimshottari balance-at-birth. The balance amplifies
    sub-arc-second Moon precision by the mahadasha length (~1.4 min per MD-year
    per 0.1"), so it must not consume the arc-second-rounded
    ``degree_in_nakshatra`` (which stays rounded for readable display).
    """
    return _norm(longitude) % (NAKSHATRA_ARCSEC / 3600.0)


def _placement(longitude: float) -> dict:
    """Common placement block: sign/degree/nakshatra/pada + varga signs."""
    lon = _norm(longitude)
    s_idx = sign_index(lon)
    nak_idx, nak_name, nak_lord = nakshatra_of(lon)
    return {
        "longitude": lon,
        "sign": SIGNS[s_idx],
        "sign_index": s_idx,
        "degree": lon - s_idx * 30.0,
        "nakshatra": nak_name,
        "nakshatra_index": nak_idx,
        "nakshatra_lord": nak_lord,
        "pada": pada_of(lon),
        "d9_sign": SIGNS[varga_sign_index(lon, 9)],
        "d10_sign": SIGNS[varga_sign_index(lon, 10)],
    }


# ---------------------------------------------------------------------------
# Varga (divisional) — ONE function parameterized by divisor (Parashari)
# ---------------------------------------------------------------------------

def _varga_seed(divisor: int, sign: int) -> tuple[int, int]:
    """Return ``(start_sign, step)`` for the Parashari counting of a varga.

    The divisional sign is ``(start + step * part) % 12``; ``step`` is +1
    (forward) or -1 (reverse). Only the divisors in v1 scope are implemented
    (D-1, D-9, D-10).
    """
    if divisor == 1:                       # Rasi (D-1)
        return sign, 1
    if divisor == 9:                       # Navamsa (D-9): always forward
        modality = sign % 3
        if modality == 0:                  # movable -> from itself
            return sign, 1
        if modality == 1:                  # fixed   -> from the 9th
            return (sign + 8) % 12, 1
        return (sign + 4) % 12, 1          # dual    -> from the 5th
    if divisor == 10:                      # Dashamsha (D-10)
        if sign % 2 == 0:                  # odd sign (1-based) -> from itself, forward
            return sign, 1
        # Even sign -> from the 9th sign counting in REVERSE. Equivalent to
        # (sign + 4 - part) % 12; verified 16/16 against the JHora fixtures.
        # (The naive forward even->9th does NOT match JHora here.)
        return (sign + 4) % 12, -1
    raise NotImplementedError(
        f"varga D-{divisor} is outside v1 scope (only D-1, D-9, D-10)"
    )


def varga_sign_index(longitude: float, divisor: int) -> int:
    """0-based divisional sign index for a sidereal longitude (Parashari)."""
    if divisor < 1:
        raise ValueError("divisor must be >= 1")
    lon = _norm(longitude)
    sign = sign_index(lon)
    deg_in_sign = lon - sign * 30.0
    part = int(deg_in_sign * divisor / 30.0)   # 0-based part within the sign
    if part >= divisor:                         # guard the 30.0 boundary
        part = divisor - 1
    start, step = _varga_seed(divisor, sign)
    return (start + step * part) % 12


# ---------------------------------------------------------------------------
# Whole-sign houses (field 3)
# ---------------------------------------------------------------------------

def whole_sign_house(planet_sign_index: int, lagna_sign_index: int) -> int:
    """1-based whole-sign house: the planet's rasi counted from the Lagna rasi."""
    return ((planet_sign_index - lagna_sign_index) % 12) + 1


# ---------------------------------------------------------------------------
# Dignity (field 6) — COMPUTED, not JHora-validated
# ---------------------------------------------------------------------------

def natural_relation(planet: str, other: str) -> str:
    """Natural (naisargika) relation of ``planet`` to ``other``: friend/neutral/enemy."""
    if other in NATURAL_FRIENDS.get(planet, set()):
        return "friend"
    if other in NATURAL_ENEMIES.get(planet, set()):
        return "enemy"
    return "neutral"


def dignity_of(planet: str, sign: str, degree: float) -> str:
    """Standard Parashari dignity for a planet in ``sign`` at ``degree`` (0-30).

    Priority: exalted > debilitated > moolatrikona > own_sign > natural relation
    to the dispositor (friend/neutral/enemy). Rahu/Ketu have no classical
    naisargika dignity -> "not_applicable". "great friend"/"great enemy" are
    compound categories deferred in v1 and are never returned.
    """
    if planet not in EXALTATION:            # Rahu / Ketu
        return "not_applicable"
    if sign == EXALTATION[planet][0]:
        return "exalted"
    if sign == DEBILITATION[planet]:
        return "debilitated"
    mt_sign, mt_lo, mt_hi = MOOLATRIKONA[planet]
    if sign == mt_sign and mt_lo <= degree < mt_hi:
        return "moolatrikona"
    if sign in OWN_SIGNS[planet]:
        return "own_sign"
    return natural_relation(planet, SIGN_LORDS[sign])


# ---------------------------------------------------------------------------
# Graha drishti (field 7) — COMPUTED, not JHora-validated
# ---------------------------------------------------------------------------

def aspected_houses(planet: str, house: int) -> list[int]:
    """1-based house numbers a planet in ``house`` aspects (house-based drishti)."""
    if planet in _NO_ASPECT:
        return []
    offsets = _ASPECT_OFFSETS.get(planet, _DEFAULT_ASPECT_OFFSETS)
    return [((house - 1 + off) % 12) + 1 for off in offsets]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def compute_vedic_chart(
    *,
    datetime_local: str,
    gmt_offset: float,
    lat: float,
    lon: float,
    target_date: str | None = None,
) -> dict:
    """Compute the full Vedic (Parashari) result for one birth.

    Args:
        datetime_local: naive ISO-8601 local birth datetime, e.g.
            "1990-01-01T14:35:00".
        gmt_offset: fixed UT offset in hours (e.g. 5.5 for India). Used for
            time->UT directly, decoupling correctness from tz lookup.
        lat: decimal degrees, north positive.
        lon: decimal degrees, east positive.
        target_date: naive ISO-8601 local datetime at which to evaluate the
            running dasha. Defaults to the birth datetime.

    Returns a dict with keys: settings, lagna, planets, houses, dasha.
    """
    _initialize_swe()

    birth_aware = _local_naive_to_aware(datetime_local, gmt_offset)
    jd_ut = _julian_day_ut(birth_aware.astimezone(dt_timezone.utc))

    # Ascendant + whole-sign cusps via Swiss Ephemeris system 'W'.
    _cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b'W', swe.FLG_SIDEREAL)
    lagna_lon = _norm(ascmc[0])
    lagna_sign_idx = sign_index(lagna_lon)

    lagna = {**_placement(lagna_lon), "house": 1}

    # Planets (9): sidereal longitudes; Ketu derived from Rahu.
    planets: list[dict] = []
    rahu_lon = None
    for name in PLANET_ORDER:
        if name == "Ketu":
            longitude = _norm(rahu_lon + 180.0)
        else:
            xx, _ret = swe.calc_ut(jd_ut, _SWE_BODY_IDS[name], _CALC_FLAGS)
            longitude = _norm(xx[0])
            if name == "Rahu":
                rahu_lon = longitude
        placement = _placement(longitude)
        house = whole_sign_house(placement["sign_index"], lagna_sign_idx)
        planet = {
            "name": name,
            **placement,
            "house": house,
            "dignity": dignity_of(name, placement["sign"], placement["degree"]),
            "aspects_houses": aspected_houses(name, house),
        }
        planets.append(planet)

    # Whole-sign house occupancy (field 3): 12 houses, planet names in each.
    houses = {h: [] for h in range(1, 13)}
    for planet in planets:
        houses[planet["house"]].append(planet["name"])

    # Current 4-level Vimshottari path (field 5).
    moon = next(p for p in planets if p["name"] == "Moon")
    target_aware = (
        _local_naive_to_aware(target_date, gmt_offset)
        if target_date is not None else birth_aware
    )
    dasha = compute_current_dasha(
        moon_longitude=moon["longitude"],
        moon_nakshatra_lord=moon["nakshatra_lord"],
        moon_degree_in_nakshatra=_degree_in_nakshatra_precise(moon["longitude"]),
        birth=birth_aware,
        target=target_aware,
    )

    return {
        "settings": dict(SETTINGS),
        "lagna": lagna,
        "planets": planets,
        "houses": houses,
        "dasha": dasha,
    }
