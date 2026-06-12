"""Nakshatra, pada, lord, and navamsa helpers.

Spec: docs/nakshatra.md. Inputs are sidereal absolute longitudes in decimal
degrees. Boundary math is integer arc-seconds; floats appear only in output
degree fields.
"""

from __future__ import annotations

FULL_ZODIAC_ARCSEC = 1_296_000
NAKSHATRA_ARCSEC = 48_000
PADA_ARCSEC = 12_000

NAKSHATRAS = [
    ("Ashwini", "Ketu"),
    ("Bharani", "Venus"),
    ("Krittika", "Sun"),
    ("Rohini", "Moon"),
    ("Mrigashira", "Mars"),
    ("Ardra", "Rahu"),
    ("Punarvasu", "Jupiter"),
    ("Pushya", "Saturn"),
    ("Ashlesha", "Mercury"),
    ("Magha", "Ketu"),
    ("Purva Phalguni", "Venus"),
    ("Uttara Phalguni", "Sun"),
    ("Hasta", "Moon"),
    ("Chitra", "Mars"),
    ("Swati", "Rahu"),
    ("Vishakha", "Jupiter"),
    ("Anuradha", "Saturn"),
    ("Jyeshtha", "Mercury"),
    ("Mula", "Ketu"),
    ("Purva Ashadha", "Venus"),
    ("Uttara Ashadha", "Sun"),
    ("Shravana", "Moon"),
    ("Dhanishta", "Mars"),
    ("Shatabhisha", "Rahu"),
    ("Purva Bhadrapada", "Jupiter"),
    ("Uttara Bhadrapada", "Saturn"),
    ("Revati", "Mercury"),
]

SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

NAKSHATRA_BLOCK_KEYS = {
    "name",
    "index",
    "lord",
    "degree_in_nakshatra",
    "pada",
    "degree_in_pada",
    "navamsa_sign",
}


def _arcsec(longitude: float) -> int:
    return round((longitude % 360.0) * 3600.0) % FULL_ZODIAC_ARCSEC


def _nakshatra_zero_based(arcsec: int) -> int:
    return arcsec // NAKSHATRA_ARCSEC


def _nakshatra_offset(arcsec: int) -> int:
    return arcsec % NAKSHATRA_ARCSEC


def nakshatra_index(longitude: float) -> int:
    """Return the API nakshatra index, 1-based: Ashwini=1, Revati=27."""
    return _nakshatra_zero_based(_arcsec(longitude)) + 1


def nakshatra_name(longitude: float) -> str:
    return NAKSHATRAS[nakshatra_index(longitude) - 1][0]


def nakshatra_lord(longitude: float) -> str:
    return NAKSHATRAS[nakshatra_index(longitude) - 1][1]


def degree_in_nakshatra(longitude: float) -> float:
    return _nakshatra_offset(_arcsec(longitude)) / 3600.0


def pada(longitude: float) -> int:
    offset = _nakshatra_offset(_arcsec(longitude))
    return (offset // PADA_ARCSEC) + 1


def degree_in_pada(longitude: float) -> float:
    offset = _nakshatra_offset(_arcsec(longitude))
    return (offset % PADA_ARCSEC) / 3600.0


def navamsa_sign(longitude: float) -> str:
    arcsec = _arcsec(longitude)
    navamsa_sign_index = (arcsec // PADA_ARCSEC) % 12
    return SIGNS[navamsa_sign_index]


def nakshatra_block(longitude: float) -> dict:
    return {
        "name": nakshatra_name(longitude),
        "index": nakshatra_index(longitude),
        "lord": nakshatra_lord(longitude),
        "degree_in_nakshatra": degree_in_nakshatra(longitude),
        "pada": pada(longitude),
        "degree_in_pada": degree_in_pada(longitude),
        "navamsa_sign": navamsa_sign(longitude),
    }
