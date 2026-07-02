"""Read + normalize ``tests/fixtures/vedic_fixtures.json`` for the field-A harness.

The fixtures are JHora-verified and their on-disk shape is authoritative: a JSON
ARRAY of chart objects, each ::

    {"id": "vedic_01",
     "input": {"date","time","gmt_offset","place","lat","lon"},
     "lagna": {"lon_dms","sign","nakshatra","pada","d9_sign","d10_sign"},
     "planets": {"Sun": {"lon_dms","sign","nakshatra","pada","house",
                          "d9_sign","d10_sign"}, ...},
     "houses": {"1": {"sign","planets":[...]}, ...},
     "dasha_at_birth": {"MD": {"lord","start","end"}, "AD"/"PD"/"SD": ...}}

This module is the ONLY place that knows the file's vocabulary — 2-letter sign
abbreviations, short nakshatra abbreviations, DMS longitude strings, string /
null ``gmt_offset``, and abbreviated dasha lords. It translates each entry into
the engine's vocabulary so the harness can compare directly. It NEVER mutates
the file (values are read-only).
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.engines.vedic_engine import SIGNS, compute_vedic_chart

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "vedic_fixtures.json"

# India first (vedic_01/_02/_05, +05:30), then NYC, then Sydney (spec run order).
FIELD_A_ORDER = ["vedic_01", "vedic_02", "vedic_05", "vedic_03", "vedic_04"]
INDIA_CHARTS = {"vedic_01", "vedic_02", "vedic_05"}

ARCSEC_TOL_DEG = 60.0 / 3600.0  # target < 60"

# --- Fixture vocabulary -> engine vocabulary (verified against each lon_dms) ---

SIGN_ABBR = {
    "Ar": "Aries", "Ta": "Taurus", "Ge": "Gemini", "Cn": "Cancer",
    "Le": "Leo", "Vi": "Virgo", "Li": "Libra", "Sc": "Scorpio",
    "Sg": "Sagittarius", "Cp": "Capricorn", "Aq": "Aquarius", "Pi": "Pisces",
}

NAK_ABBR = {
    "Aswi": "Ashwini", "Bhar": "Bharani", "Krit": "Krittika", "Rohi": "Rohini",
    "Mrig": "Mrigashira", "Ardr": "Ardra", "Puna": "Punarvasu", "Push": "Pushya",
    "Asre": "Ashlesha", "Magh": "Magha", "PPha": "Purva Phalguni",
    "UPha": "Uttara Phalguni", "Hast": "Hasta", "Chit": "Chitra", "Swat": "Swati",
    "Visa": "Vishakha", "Anu": "Anuradha", "Jye": "Jyeshtha", "Mula": "Mula",
    "PSha": "Purva Ashadha", "USha": "Uttara Ashadha", "Srav": "Shravana",
    "Dhan": "Dhanishta", "Sata": "Shatabhisha", "PBha": "Purva Bhadrapada",
    "UBha": "Uttara Bhadrapada", "Reva": "Revati",
}

LORD_ABBR = {
    "Sun": "Sun", "Moon": "Moon", "Mars": "Mars", "Merc": "Mercury",
    "Jup": "Jupiter", "Ven": "Venus", "Sat": "Saturn", "Rah": "Rahu",
    "Ket": "Ketu",
}

# The fixture omits gmt_offset for some charts (null). It is resolved from the
# birth place via IANA at the birth instant so the offset stays FIXED per chart
# (the resolved value is surfaced in the harness output for attribution).
PLACE_TZ = {
    "Kolkata": "Asia/Kolkata", "Delhi": "Asia/Kolkata", "Mumbai": "Asia/Kolkata",
    "New York City": "America/New_York", "Sydney": "Australia/Sydney",
}

# Engine dasha keys, in level order, keyed by the fixture's level names.
DASHA_LEVEL_MAP = {"MD": "maha", "AD": "antar", "PD": "pratyantar", "SD": "sookshma"}

_DMS_RE = re.compile(r"^\s*(\d+)([A-Za-z]{2})(\d+)'([\d.]+)\"\s*$")
_OFFSET_RE = re.compile(r"^\s*([+-])(\d{1,2}):(\d{2})\s*$")


def parse_dms(lon_dms: str) -> float:
    """`"9Li42'52.88\""` -> absolute sidereal longitude in decimal degrees."""
    m = _DMS_RE.match(lon_dms)
    if not m:
        raise ValueError(f"unparseable lon_dms: {lon_dms!r}")
    deg_in_sign, sign_abbr, arcmin, arcsec = m.groups()
    base = SIGNS.index(SIGN_ABBR[sign_abbr]) * 30.0
    return base + int(deg_in_sign) + int(arcmin) / 60.0 + float(arcsec) / 3600.0


def resolve_offset_hours(gmt_offset, place: str, datetime_local: str) -> float:
    """Return the FIXED UT offset in hours for a chart.

    Uses the fixture's explicit ``gmt_offset`` string when present; otherwise
    resolves it from the birth ``place`` (IANA) at the birth instant, so charts
    with a null offset (Delhi/NYC/Sydney) still get a single fixed offset.
    """
    if isinstance(gmt_offset, str):
        m = _OFFSET_RE.match(gmt_offset)
        if not m:
            raise ValueError(f"unparseable gmt_offset: {gmt_offset!r}")
        sign, hh, mm = m.groups()
        hours = int(hh) + int(mm) / 60.0
        return hours if sign == "+" else -hours
    if gmt_offset is None:
        tz_name = PLACE_TZ.get(place)
        if tz_name is None:
            raise ValueError(f"no timezone known for place {place!r}")
        naive = datetime.fromisoformat(datetime_local)
        off = naive.replace(tzinfo=ZoneInfo(tz_name)).utcoffset()
        return off.total_seconds() / 3600.0
    raise ValueError(f"unexpected gmt_offset type: {gmt_offset!r}")


def _adapt_placement(blk: dict) -> dict:
    """Translate one lagna/planet block into engine vocabulary."""
    return {
        "longitude": parse_dms(blk["lon_dms"]),
        "sign": SIGN_ABBR[blk["sign"]],
        "nakshatra": NAK_ABBR[blk["nakshatra"]],
        "pada": blk["pada"],
        "house": blk.get("house"),
        "d9_sign": SIGN_ABBR[blk["d9_sign"]],
        "d10_sign": SIGN_ABBR[blk["d10_sign"]],
    }


def load_fixtures() -> dict[str, dict]:
    """Return the fixtures as ``{id: adapted_entry}`` in engine vocabulary.

    Each adapted entry has ``input`` (datetime_local, gmt_offset float, lat, lon,
    place), ``lagna``, ``planets`` (by name), and ``dasha`` (only the levels the
    fixture actually populates — AD/PD/SD are null for some charts).
    """
    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    adapted: dict[str, dict] = {}
    for entry in raw:
        inp = entry["input"]
        datetime_local = f"{inp['date']}T{inp['time']}:00"
        gmt_offset = resolve_offset_hours(inp["gmt_offset"], inp["place"], datetime_local)

        dasha: dict[str, dict] = {}
        for level, block in entry["dasha_at_birth"].items():
            if block.get("lord") is None:
                continue  # AD/PD/SD not provided for this chart
            dasha[level] = {
                "lord": LORD_ABBR[block["lord"]],
                "start": block["start"],
                "end": block["end"],
            }

        adapted[entry["id"]] = {
            "id": entry["id"],
            "input": {
                "datetime_local": datetime_local,
                "gmt_offset": gmt_offset,
                "lat": inp["lat"],
                "lon": inp["lon"],
                "place": inp["place"],
            },
            "lagna": _adapt_placement(entry["lagna"]),
            "planets": {name: _adapt_placement(blk) for name, blk in entry["planets"].items()},
            "dasha": dasha,
        }
    return adapted


def run_chart(entry: dict) -> dict:
    """Compute the engine result for an adapted entry (dasha evaluated at birth)."""
    inp = entry["input"]
    return compute_vedic_chart(
        datetime_local=inp["datetime_local"],
        gmt_offset=inp["gmt_offset"],
        lat=inp["lat"],
        lon=inp["lon"],
        target_date=inp["datetime_local"],  # dasha_at_birth
    )


def _to_minute(iso_or_naive: str) -> datetime:
    """Parse an engine ISO (offset-aware, birth-zone) or a fixture naive
    datetime to a tz-naive wall-clock value truncated to the minute."""
    dt = datetime.fromisoformat(iso_or_naive.replace(" ", "T"))
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)  # engine already renders in the birth zone
    return dt.replace(second=0, microsecond=0)


def check_field_a(entry: dict, result: dict) -> list[str]:
    """Compare one chart to its JHora expectations. Returns [] on pass.

    Longitudes within <60"; sign/nakshatra/pada/house/D-9/D-10 exact; MD/AD/PD/SD
    lords + start/end to the minute (only the levels the fixture provides).
    """
    fails: list[str] = []
    planets = {p["name"]: p for p in result["planets"]}

    def compare_block(label: str, got: dict, exp: dict) -> None:
        if abs(got["longitude"] - exp["longitude"]) > ARCSEC_TOL_DEG:
            off = abs(got["longitude"] - exp["longitude"]) * 3600.0
            fails.append(f'{label}.longitude off by {off:.1f}"')
        for field in ("sign", "nakshatra", "pada", "house", "d9_sign", "d10_sign"):
            if exp.get(field) is not None and got.get(field) != exp[field]:
                fails.append(f"{label}.{field} {got.get(field)!r}!={exp[field]!r}")

    compare_block("lagna", result["lagna"], entry["lagna"])
    for name, exp in entry["planets"].items():
        compare_block(name, planets[name], exp)

    got_dasha = result["dasha"]
    for level, exp in entry["dasha"].items():
        got = got_dasha[DASHA_LEVEL_MAP[level]]
        if got["lord"] != exp["lord"]:
            fails.append(f"dasha.{level}.lord {got['lord']!r}!={exp['lord']!r}")
        for edge in ("start", "end"):
            if _to_minute(got[edge]) != _to_minute(exp[edge]):
                fails.append(
                    f"dasha.{level}.{edge} {_to_minute(got[edge])}!={_to_minute(exp[edge])}"
                )
    return fails
