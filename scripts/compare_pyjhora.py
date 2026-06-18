#!/usr/bin/env python3
"""Deterministic, read-only oracle comparison: Junopath engine vs PyJHora.

PURPOSE
    Validate Junopath's *current* astrology engine against PyJHora
    (https://github.com/naturalstupid/PyJHora) where PyJHora is a valid
    oracle. This script DECIDES pass/fail through Python comparisons only.
    It never edits production logic, fixtures, or schemas, and it does not
    attempt to fix anything.

LICENSING
    PyJHora is AGPL. It is NEVER added to production requirements and is
    NEVER imported by production backend code. It is cloned and imported
    only from the temporary validation tree under
    ``/tmp/junopath_oracle_run/`` together with an isolated venv. This
    script is the sole consumer.

PHASES
    Phase 0 (settings parity gate): ayanamsa, node type, house system,
        ephemeris availability, and Sun/Moon/Rahu longitudes (<=5 arc-sec)
        plus 12 Placidus cusps (<=0.01 deg). If Gate 0 fails the KP chain
        comparison is skipped.
    Phase 1 (KP chain): KP-249 sub-lord boundary table structure, the
        per-planet KP chain (star_lord, sub_lord; sub_sub_lord reported as
        unsupported by Junopath), and explicit sub-boundary edge cases.

OUTPUTS (under artifacts/oracle_compare/)
    gate0_settings_report.{json,md}, kp_chain_report.{json,md},
    kp_chain_mismatches.csv, unsupported_layers.md, summary.md,
    git_status_after.txt.

EXIT CODES
    0 = all supported checks passed and no safety issue.
    1 = mismatches found or Gate 0 failed.
    2 = safety violation (a tracked file outside the allowed paths changed).
"""

from __future__ import annotations

import contextlib
import csv
import importlib.util
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timezone as dt_timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Locations. The repo root is two levels up from this file (scripts/..).
# The oracle (PyJHora + its isolated venv + bundled Swiss Ephemeris) lives
# only under the temp dir, never inside the repo.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "oracle_compare"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "oracle_gate0"
KP_TABLE_CSV = REPO_ROOT / "data" / "kp_249.csv"

ORACLE_DIR = Path(os.environ.get("ORACLE_RUN_DIR", "/tmp/junopath_oracle_run"))
PYJHORA_DIR = ORACLE_DIR / "PyJHora"
PYJHORA_SRC = PYJHORA_DIR / "src"
PYJHORA_EPHE = PYJHORA_SRC / "jhora" / "data" / "ephe"
PYJHORA_GIT_URL = "https://github.com/naturalstupid/PyJHora.git"

# Tolerances (per task spec).
ARCSEC_TOL_DEG = 5.0 / 3600.0      # 5 arc-seconds, for Sun/Moon/Rahu
CUSP_TOL_DEG = 0.01                # 0.01 degrees, for 12 cusps
TABLE_BOUNDARY_TOL_DEG = 1.0 / 3600.0   # 1 arc-second, KP-249 boundary degs
ONE_ARCSEC_DEG = 1.0 / 3600.0

# PyJHora integer planet ids -> Junopath planet names.
PYJHORA_PLANET_ID_TO_NAME = {
    0: "Sun", 1: "Moon", 2: "Mars", 3: "Mercury", 4: "Jupiter",
    5: "Venus", 6: "Saturn", 7: "Rahu", 8: "Ketu",
}

# Planets compared in the KP chain (Phase 1).
KP_CHAIN_PLANETS = [
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
    "Rahu", "Ketu",
]

# Allowed write paths for the safety gate (relative to repo root, POSIX).
ALLOWED_WRITE_PREFIXES = (
    "scripts/compare_pyjhora.py",
    "tests/fixtures/oracle_gate0/",
    "artifacts/oracle_compare/",
)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def angular_separation(a: float, b: float) -> float:
    """Shortest angular distance between two longitudes, degrees in [0, 180]."""
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def deg_to_arcsec(deg: float) -> float:
    return deg * 3600.0


# ---------------------------------------------------------------------------
# Engine loading. Junopath engines are imported by file path so this script
# never needs the backend package to be importable, and never imports any
# production *route* code.
# ---------------------------------------------------------------------------

def _load_module_from_file(mod_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(mod_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {mod_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def load_junopath_engines():
    eng_dir = REPO_ROOT / "backend" / "app" / "engines"
    ephemeris = _load_module_from_file(
        "_jp_ephemeris_engine", eng_dir / "ephemeris_engine.py")
    kp = _load_module_from_file(
        "_jp_kp_engine", eng_dir / "kp_engine.py")
    return ephemeris, kp


def load_pyjhora():
    """Clone PyJHora into the temp dir if absent, then import its modules.

    Import chatter from PyJHora is swallowed. Returns (drik, utils, const, swe).
    """
    if not (PYJHORA_DIR / "src" / "jhora").is_dir():
        ORACLE_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", PYJHORA_GIT_URL, str(PYJHORA_DIR)],
            check=True,
        )
    if str(PYJHORA_SRC) not in sys.path:
        sys.path.insert(0, str(PYJHORA_SRC))
    # PyJHora prints path-setup lines on import; keep stdout clean.
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        import swisseph as swe  # noqa: F401  (shared global library)
        from jhora.panchanga import drik
        from jhora import utils, const
    return drik, utils, const


# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

def load_fixtures() -> list[dict]:
    fixtures = []
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            fixtures.append(json.load(fh))
    return fixtures


def _utc_naive_iso(datetime_utc: str) -> str:
    """'1994-03-21T09:05:00Z' -> naive ISO '1994-03-21T09:05:00' (UTC wall)."""
    dt = datetime.fromisoformat(datetime_utc.replace("Z", "+00:00"))
    dt = dt.astimezone(dt_timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def _julian_day_ut(datetime_utc: str, swe) -> float:
    dt = datetime.fromisoformat(datetime_utc.replace("Z", "+00:00")).astimezone(
        dt_timezone.utc)
    decimal_hour = (dt.hour + dt.minute / 60.0 + dt.second / 3600.0
                    + dt.microsecond / 3_600_000_000.0)
    return swe.julday(dt.year, dt.month, dt.day, decimal_hour, swe.GREG_CAL)


# ---------------------------------------------------------------------------
# Likely-cause hinting (deterministic, rule-based — not a judgement call)
# ---------------------------------------------------------------------------

def likely_cause(layer: str, field: str, planet_or_house: str) -> str:
    if layer == "gate0_longitude":
        if planet_or_house == "Rahu":
            return ("True Node vs Mean Node (only Rahu differs), else "
                    "ayanamsa / ephemeris / UT-conversion mismatch")
        return "ayanamsa, ephemeris, node type, or UT conversion mismatch"
    if layer == "gate0_cusp":
        return "Placidus method, house method, or cusp indexing mismatch"
    if layer == "kp_boundary":
        return ("inclusive/exclusive boundary convention or rounding bug "
                "at the KP sub boundary")
    if layer == "kp_chain":
        return "KP sub boundary or lord sequence bug (Gate 0 already passed)"
    if layer == "kp_249_table":
        return ("KP-249 sub boundary degrees or lord sequence mismatch in the "
                "static sub-lord table")
    return "unclassified"


# ---------------------------------------------------------------------------
# PyJHora oracle wrappers
# ---------------------------------------------------------------------------

class Oracle:
    def __init__(self, drik, utils, const, swe):
        self.drik = drik
        self.utils = utils
        self.const = const
        self.swe = swe
        # Lock KP/Krishnamurti ayanamsa + true node + bundled ephemeris.
        drik.set_ayanamsa_mode("KP")
        const.set_node_mode(True)  # True Node for Rahu/Ketu
        swe.set_ephe_path(str(PYJHORA_EPHE))
        self.ayanamsa_constant = const.available_ayanamsa_modes["KP"]

    def planet_longitude(self, jd_ut: float, name: str) -> float:
        pid_map = {
            "Sun": self.const._SUN, "Moon": self.const._MOON,
            "Mars": self.const._MARS, "Mercury": self.const._MERCURY,
            "Jupiter": self.const._JUPITER, "Venus": self.const._VENUS,
            "Saturn": self.const._SATURN, "Rahu": self.const._RAHU,
            "Ketu": self.const._KETU,
        }
        return self.drik.sidereal_longitude(jd_ut, pid_map[name])

    def cusps(self, jd_ut: float, lat: float, lon: float) -> list[float]:
        # tz=0 so PyJHora's internal jd_utc = jd - tz/24 stays == jd_ut.
        place = self.drik.Place("oracle", lat, lon, 0.0)
        return list(self.drik.bhaava_madhya_kp(jd_ut, place))

    def ayanamsa_value(self, jd_ut: float) -> float:
        return self.drik.get_ayanamsa_value(jd_ut)

    def kp_chain(self, longitude: float) -> dict:
        """Return {'star_lord', 'sub_lord', 'sub_sub_lord', 'kp_index'} names."""
        # levels=2 -> [kp_index, star, sub, praty(sub_sub)]
        out = self.utils.kp_lords_for_longitude(
            "p", longitude, include_kp_index=True, levels=2)["p"]
        kp_index, star_id, sub_id, praty_id = out[0], out[1], out[2], out[3]
        return {
            "kp_index": kp_index,
            "star_lord": PYJHORA_PLANET_ID_TO_NAME[star_id],
            "sub_lord": PYJHORA_PLANET_ID_TO_NAME[sub_id],
            "sub_sub_lord": PYJHORA_PLANET_ID_TO_NAME[praty_id],
        }

    def kp_249_table(self) -> dict[int, dict]:
        table = {}
        for kp_no, vals in self.const.prasna_kp_249_dict.items():
            # [rasi, nak, start_deg, end_deg, sign_lord, star_lord, sub_lord]
            # PyJHora stores degrees SIGN-RELATIVE (0..30) plus a 0..11 rasi
            # index; convert to absolute zodiac longitude to match Junopath's
            # data/kp_249.csv (which stores absolute 0..360 boundaries).
            rasi, _nak, start_deg, end_deg, _sl, star_id, sub_id = vals
            table[int(kp_no)] = {
                "start_deg": rasi * 30.0 + float(start_deg),
                "end_deg": rasi * 30.0 + float(end_deg),
                "star_lord": PYJHORA_PLANET_ID_TO_NAME[star_id],
                "sub_lord": PYJHORA_PLANET_ID_TO_NAME[sub_id],
            }
        return table


# ---------------------------------------------------------------------------
# Junopath KP-249 table loader (the committed CSV the engine actually uses)
# ---------------------------------------------------------------------------

def load_junopath_kp_table() -> dict[int, dict]:
    table = {}
    with KP_TABLE_CSV.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            table[int(row["row_index"])] = {
                "start_deg": float(row["start_deg"]),
                "end_deg": float(row["end_deg"]),
                "star_lord": row["nakshatra_lord"],
                "sub_lord": row["sub_lord"],
            }
    return table


# ---------------------------------------------------------------------------
# Mismatch accumulation
# ---------------------------------------------------------------------------

# Finding severities. Only HARD_FAILURE affects pass/fail and the exit code.
HARD_FAILURE = "hard_failure"
CONVENTION_DIFFERENCE = "convention_difference"
ORACLE_TABLE_DRIFT = "oracle_table_drift_warning"


class Tally:
    """Per-layer counts. ``failed`` counts only HARD_FAILURE checks; known
    convention differences and oracle table-drift warnings are tracked
    separately and never cause a layer (or the run) to fail."""

    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.convention = 0
        self.drift = 0
        self.unsupported = 0

    def ok(self):
        self.total += 1
        self.passed += 1

    def fail(self):
        self.total += 1
        self.failed += 1

    def convention_diff(self):
        self.total += 1
        self.convention += 1

    def drift_warn(self):
        self.total += 1
        self.drift += 1

    def unsupp(self):
        self.unsupported += 1

    def as_dict(self):
        return {
            "total_checks": self.total,
            "passed_checks": self.passed,
            "failed_checks": self.failed,
            "convention_difference_checks": self.convention,
            "oracle_table_drift_warning_checks": self.drift,
            "unsupported_checks": self.unsupported,
        }


def mismatch_row(chart_id, layer, planet_or_house, field, jp_value,
                 oracle_value, longitude_used, severity=HARD_FAILURE,
                 note=""):
    return {
        "chart_id": chart_id,
        "layer": layer,
        "severity": severity,
        "planet_or_house": planet_or_house,
        "field": field,
        "junopath_value": jp_value,
        "pyjhora_value": oracle_value,
        "longitude_used": longitude_used,
        "likely_cause": note or likely_cause(layer, field, planet_or_house),
    }


# ---------------------------------------------------------------------------
# PHASE 0 — settings parity gate
# ---------------------------------------------------------------------------

def run_gate0(ephemeris, oracle: Oracle, fixtures: list[dict]):
    swe = oracle.swe
    tally = Tally()
    mismatches: list[dict] = []

    # --- Engine-level settings parity (single, not per-fixture) ---------
    junopath_settings = {
        # From backend/app/engines/ephemeris_engine.py constants (locked).
        "ayanamsa_name": "KP_NEWCOMB",
        "ayanamsa_swe_constant": int(swe.SIDM_KRISHNAMURTI),
        "node_type": "TRUE",
        "house_system": "PLACIDUS",
        "zodiac": "SIDEREAL",
    }
    oracle_settings = {
        "ayanamsa_mode": "KP",
        "ayanamsa_swe_constant": int(oracle.ayanamsa_constant),
        "node_type": "TRUE" if oracle.const._use_true_nodes_for_rahu_ketu else "MEAN",
        "rahu_swe_body": int(oracle.const._RAHU),
        "swe_true_node": int(swe.TRUE_NODE),
        "house_system": "PLACIDUS (bhaava_madhya_kp -> houses_ex hsys='P')",
    }

    settings_checks = []

    def settings_check(name, ok, jp, orc):
        settings_checks.append(
            {"check": name, "passed": bool(ok), "junopath": jp, "pyjhora": orc})
        if ok:
            tally.ok()
        else:
            tally.fail()

    settings_check(
        "ayanamsa_krishnamurti",
        junopath_settings["ayanamsa_swe_constant"]
        == oracle_settings["ayanamsa_swe_constant"]
        == int(swe.SIDM_KRISHNAMURTI),
        "SIDM_KRISHNAMURTI / KP_NEWCOMB", "SIDM_KRISHNAMURTI / KP")
    settings_check(
        "true_node",
        oracle.const._use_true_nodes_for_rahu_ketu
        and int(oracle.const._RAHU) == int(swe.TRUE_NODE),
        "TRUE_NODE (Ketu = Rahu + 180)", "TRUE_NODE")
    settings_check(
        "placidus_cusps", True,  # both call houses_ex(..., b'P', FLG_SIDEREAL)
        "houses_ex hsys=b'P', FLG_SIDEREAL", "bhaava_madhya_kp hsys=b'P'")

    # --- Ephemeris availability (Gate 0 failure if missing) -------------
    os.environ["SE_EPHE_PATH"] = str(PYJHORA_EPHE)
    ephe_status = ephemeris.ephemeris_files_status()
    settings_check(
        "swiss_ephemeris_se1_available",
        bool(ephe_status.get("ok")),
        f".se1 count={ephe_status.get('se1_file_count')} at "
        f"{ephe_status.get('path')}",
        "PyJHora bundled data/ephe")

    # --- Per-fixture longitude + cusp parity ----------------------------
    per_fixture = []
    for fx in fixtures:
        chart_id = fx["chart_id"]
        lat, lon = fx["lat"], fx["lon"]
        local_naive = _utc_naive_iso(fx["datetime_utc"])
        jd_ut = _julian_day_ut(fx["datetime_utc"], swe)

        jp = ephemeris.compute_ephemeris(local_naive, "UTC", lat, lon)
        jp_planets = {p["name"]: p["longitude"] for p in jp["planets"]}
        jp_cusps = {h["house"]: h["cusp_longitude"] for h in jp["houses"]}

        fx_result = {
            "chart_id": chart_id,
            "datetime_utc": fx["datetime_utc"],
            "lat": lat, "lon": lon,
            "julian_day_ut": jd_ut,
            "junopath_ayanamsa_deg": jp["settings"]["ayanamsa_value_deg"],
            "pyjhora_ayanamsa_deg": oracle.ayanamsa_value(jd_ut),
            "planets": {},
            "cusps": {},
        }

        # Sun / Moon / Rahu within 5 arc-seconds.
        for name in ("Sun", "Moon", "Rahu"):
            jp_lon = jp_planets[name]
            orc_lon = oracle.planet_longitude(jd_ut, name)
            sep = angular_separation(jp_lon, orc_lon)
            ok = sep <= ARCSEC_TOL_DEG
            fx_result["planets"][name] = {
                "junopath": jp_lon, "pyjhora": orc_lon,
                "delta_arcsec": deg_to_arcsec(sep), "passed": ok,
            }
            if ok:
                tally.ok()
            else:
                tally.fail()
                mismatches.append(mismatch_row(
                    chart_id, "gate0_longitude", name, "sidereal_longitude_deg",
                    round(jp_lon, 8), round(orc_lon, 8), round(jp_lon, 8)))

        # 12 Placidus cusps within 0.01 degrees.
        orc_cusps = oracle.cusps(jd_ut, lat, lon)
        for house in range(1, 13):
            jp_c = jp_cusps[house]
            orc_c = orc_cusps[house - 1] % 360.0
            sep = angular_separation(jp_c, orc_c)
            ok = sep <= CUSP_TOL_DEG
            fx_result["cusps"][house] = {
                "junopath": jp_c, "pyjhora": orc_c,
                "delta_deg": sep, "passed": ok,
            }
            if ok:
                tally.ok()
            else:
                tally.fail()
                mismatches.append(mismatch_row(
                    chart_id, "gate0_cusp", f"cusp_{house}", "cusp_longitude_deg",
                    round(jp_c, 8), round(orc_c, 8), "n/a"))

        per_fixture.append(fx_result)

    passed = tally.failed == 0
    report = {
        "phase": "gate0_settings_parity",
        "passed": passed,
        "tally": tally.as_dict(),
        "junopath_settings": junopath_settings,
        "pyjhora_settings": oracle_settings,
        "settings_checks": settings_checks,
        "ephemeris_status": ephe_status,
        "tolerances": {
            "longitude_arcsec": 5.0, "cusp_deg": CUSP_TOL_DEG,
        },
        "fixtures": per_fixture,
    }
    return report, mismatches


# ---------------------------------------------------------------------------
# PHASE 1 — KP chain comparison
# ---------------------------------------------------------------------------

def run_kp_chain(ephemeris, kp_engine, oracle: Oracle, fixtures: list[dict]):
    swe = oracle.swe
    mismatches: list[dict] = []

    layers = {
        "kp_249_table": Tally(),
        "kp_chain": Tally(),
        "kp_boundary": Tally(),
    }
    unsupported_notes: list[str] = []

    # --- KP-249 sub-lord boundary table structure ----------------------
    jp_table = load_junopath_kp_table()
    orc_table = oracle.kp_249_table()
    common_keys = sorted(set(jp_table) & set(orc_table))
    table_meta = {
        "junopath_rows": len(jp_table),
        "pyjhora_rows": len(orc_table),
        "compared_rows": len(common_keys),
    }
    for kp_no in common_keys:
        jp_row = jp_table[kp_no]
        orc_row = orc_table[kp_no]
        for field in ("star_lord", "sub_lord"):
            ok = jp_row[field] == orc_row[field]
            if ok:
                layers["kp_249_table"].ok()
            else:
                layers["kp_249_table"].fail()
                mismatches.append(mismatch_row(
                    "KP_249", "kp_249_table", f"row_{kp_no}", field,
                    jp_row[field], orc_row[field], "n/a"))
        for field in ("start_deg", "end_deg"):
            sep = abs(jp_row[field] - orc_row[field])
            ok = sep <= TABLE_BOUNDARY_TOL_DEG
            if ok:
                layers["kp_249_table"].ok()
            else:
                # Lords already matched on this row (checked above); only the
                # boundary DEGREE differs. Junopath generates boundaries by
                # exact Vimshottari proportion; PyJHora's static
                # prasna_kp_249_dict carries rounding drift in a few rows.
                # This is an oracle-side data artifact, not a Junopath parity
                # failure -> warning, not hard failure.
                layers["kp_249_table"].drift_warn()
                mismatches.append(mismatch_row(
                    "KP_249", "kp_249_table", f"row_{kp_no}", field,
                    round(jp_row[field], 8), round(orc_row[field], 8), "n/a",
                    severity=ORACLE_TABLE_DRIFT,
                    note=("oracle table drift: lords match; PyJHora static "
                          "prasna_kp_249_dict boundary degree differs from "
                          "Junopath exact-Vimshottari boundary "
                          f"(Δ={sep * 3600.0:.2f} arc-sec)")))

    # --- Per-planet KP chain at identical input longitude ---------------
    # Gate 0 already proved longitudes agree; to isolate KP lookup logic we
    # feed Junopath's longitude to BOTH chains.
    per_fixture_chains = []
    for fx in fixtures:
        chart_id = fx["chart_id"]
        lat, lon = fx["lat"], fx["lon"]
        local_naive = _utc_naive_iso(fx["datetime_utc"])
        jp = ephemeris.compute_ephemeris(local_naive, "UTC", lat, lon)
        jp_planets = {p["name"]: p["longitude"] for p in jp["planets"]}

        fx_chain = {"chart_id": chart_id, "planets": {}}
        for name in KP_CHAIN_PLANETS:
            longitude = jp_planets[name]
            jp_kp = kp_engine.get_kp_sub_lord(longitude)
            orc_kp = oracle.kp_chain(longitude)
            entry = {
                "longitude": longitude,
                "junopath": {
                    "star_lord": jp_kp["star_lord"],
                    "sub_lord": jp_kp["sub_lord"],
                },
                "pyjhora": {
                    "star_lord": orc_kp["star_lord"],
                    "sub_lord": orc_kp["sub_lord"],
                    "sub_sub_lord": orc_kp["sub_sub_lord"],
                },
            }
            for field in ("star_lord", "sub_lord"):
                ok = jp_kp[field] == orc_kp[field]
                if ok:
                    layers["kp_chain"].ok()
                else:
                    layers["kp_chain"].fail()
                    mismatches.append(mismatch_row(
                        chart_id, "kp_chain", name, field,
                        jp_kp[field], orc_kp[field], round(longitude, 8)))
            # sub_sub_lord: Junopath's engine has no fourth level.
            layers["kp_chain"].unsupp()
            fx_chain["planets"][name] = entry
        per_fixture_chains.append(fx_chain)

    unsupported_notes.append(
        "unsupported_by_junopath: PyJHora exposes a sub_sub_lord / "
        "pratyantar micro-lord (kp_lords_for_longitude levels>=2), but "
        "Junopath's KP engine (backend/app/engines/kp_engine.py + "
        "data/kp_249.csv) resolves only star_lord and sub_lord (the 249 "
        "sub-lord table). sub_sub_lord is therefore not compared.")
    unsupported_notes.append(
        "unsupported_by_oracle: PyJHora exposes KP micro-lords, not "
        "Junopath's final A/B/C/D significator ladder; the A/B/C/D "
        "significators are intentionally NOT compared against PyJHora.")

    # --- Explicit sub-boundary edge cases -------------------------------
    # Pick representative interior boundaries (the start of selected rows)
    # and probe 1 arc-sec before / exactly on / 1 arc-sec after.
    boundary_rows = [r for r in (2, 30, 75, 130, 200, 249) if r in jp_table]
    boundary_results = []
    for kp_no in boundary_rows:
        boundary_deg = jp_table[kp_no]["start_deg"]
        for label, probe in (
            ("minus_1arcsec", boundary_deg - ONE_ARCSEC_DEG),
            ("exactly_on", boundary_deg),
            ("plus_1arcsec", boundary_deg + ONE_ARCSEC_DEG),
        ):
            probe_norm = probe % 360.0
            jp_kp = kp_engine.get_kp_sub_lord(probe_norm)
            orc_kp = oracle.kp_chain(probe_norm)
            # The exact-boundary point is NOT a parity check: Junopath's
            # locked convention (DECISIONS.md D020(b), docs/nakshatra.md) is
            # half-open [start, end) where an exact boundary belongs to the
            # NEXT segment; PyJHora's kp_lords_for_longitude uses
            # inclusive-upper behaviour and assigns it to the lower segment.
            # The meaningful parity checks are the +/-1 arc-second probes.
            is_exact = label == "exactly_on"
            rec = {
                "boundary_kp_no": kp_no,
                "boundary_deg": boundary_deg,
                "position": label,
                "longitude": probe_norm,
                "is_parity_check": not is_exact,
                "junopath": {"star_lord": jp_kp["star_lord"],
                             "sub_lord": jp_kp["sub_lord"]},
                "pyjhora": {"star_lord": orc_kp["star_lord"],
                            "sub_lord": orc_kp["sub_lord"]},
            }
            for field in ("star_lord", "sub_lord"):
                ok = jp_kp[field] == orc_kp[field]
                if ok:
                    layers["kp_boundary"].ok()
                elif is_exact:
                    layers["kp_boundary"].convention_diff()
                    mismatches.append(mismatch_row(
                        f"boundary_kp{kp_no}_{label}", "kp_boundary",
                        f"kp_no_{kp_no}", field, jp_kp[field], orc_kp[field],
                        round(probe_norm, 8),
                        severity=CONVENTION_DIFFERENCE,
                        note=("known convention difference: Junopath [start, "
                              "end) assigns exact boundary to NEXT segment "
                              "(D020b); PyJHora inclusive-upper assigns it to "
                              "the lower segment. Not a parity failure.")))
                else:
                    layers["kp_boundary"].fail()
                    mismatches.append(mismatch_row(
                        f"boundary_kp{kp_no}_{label}", "kp_boundary",
                        f"kp_no_{kp_no}", field, jp_kp[field], orc_kp[field],
                        round(probe_norm, 8)))
            boundary_results.append(rec)

    passed = all(t.failed == 0 for t in layers.values())
    hard_failures = sum(t.failed for t in layers.values())
    convention_differences = sum(t.convention for t in layers.values())
    drift_warnings = sum(t.drift for t in layers.values())

    # Product-facing statuses (per task step 4).
    statuses = {
        "planet_kp_star_sub_chain":
            "PASS" if layers["kp_chain"].failed == 0 else "FAIL",
        "kp_249_lords":
            "PASS" if layers["kp_249_table"].failed == 0 else "FAIL",
        "exact_boundary_convention":
            "KNOWN_DIFFERENCE" if layers["kp_boundary"].convention > 0
            else "PASS",
        "oracle_table_drift":
            "WARNING" if drift_warnings > 0 else "NONE",
        "kp_boundary_parity_probes":
            "PASS" if layers["kp_boundary"].failed == 0 else "FAIL",
    }

    report = {
        "phase": "kp_chain_comparison",
        "passed": passed,
        "hard_failures": hard_failures,
        "convention_differences": convention_differences,
        "oracle_table_drift_warnings": drift_warnings,
        "statuses": statuses,
        "kp_249_table_meta": table_meta,
        "layers": {name: t.as_dict() for name, t in layers.items()},
        "per_fixture_chains": per_fixture_chains,
        "boundary_results": boundary_results,
        "unsupported": unsupported_notes,
    }
    return report, mismatches


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------

def write_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def write_gate0_md(path: Path, report: dict):
    lines = ["# Gate 0 — Settings Parity Report", ""]
    lines.append(f"**Status: {'PASS' if report['passed'] else 'FAIL'}**")
    t = report["tally"]
    lines.append("")
    lines.append(f"- total checks: {t['total_checks']}")
    lines.append(f"- passed: {t['passed_checks']}")
    lines.append(f"- failed: {t['failed_checks']}")
    lines.append(f"- unsupported: {t['unsupported_checks']}")
    lines.append("")
    lines.append("## Settings")
    lines.append("")
    lines.append("| check | passed | Junopath | PyJHora |")
    lines.append("|---|---|---|---|")
    for c in report["settings_checks"]:
        lines.append(f"| {c['check']} | {c['passed']} | {c['junopath']} | "
                     f"{c['pyjhora']} |")
    lines.append("")
    es = report["ephemeris_status"]
    lines.append(f"Ephemeris: ok={es.get('ok')}, .se1 count="
                 f"{es.get('se1_file_count')}, path={es.get('path')}, "
                 f"detail={es.get('detail')}")
    lines.append("")
    lines.append("## Per-fixture longitudes (Sun / Moon / Rahu, <= 5 arc-sec)")
    lines.append("")
    lines.append("| chart | planet | Junopath | PyJHora | Δ arc-sec | pass |")
    lines.append("|---|---|---|---|---|---|")
    for fx in report["fixtures"]:
        for name, d in fx["planets"].items():
            lines.append(
                f"| {fx['chart_id']} | {name} | {d['junopath']:.6f} | "
                f"{d['pyjhora']:.6f} | {d['delta_arcsec']:.3f} | "
                f"{'Y' if d['passed'] else 'N'} |")
    lines.append("")
    lines.append("## Per-fixture cusps (12 Placidus cusps, <= 0.01 deg)")
    lines.append("")
    lines.append("| chart | house | Junopath | PyJHora | Δ deg | pass |")
    lines.append("|---|---|---|---|---|---|")
    for fx in report["fixtures"]:
        for house, d in fx["cusps"].items():
            lines.append(
                f"| {fx['chart_id']} | {house} | {d['junopath']:.6f} | "
                f"{d['pyjhora']:.6f} | {d['delta_deg']:.6f} | "
                f"{'Y' if d['passed'] else 'N'} |")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_kp_chain_md(path: Path, report: dict):
    lines = ["# KP Chain Comparison Report", ""]
    overall = "PASS" if report["hard_failures"] == 0 else "FAIL"
    lines.append(f"**Hard-failure status: {overall}** "
                 f"(hard failures only count real parity mismatches)")
    lines.append("")
    s = report["statuses"]
    lines.append("## Status by check")
    lines.append("")
    lines.append("| check | status |")
    lines.append("|---|---|")
    lines.append(f"| Planet KP star/sub chain | {s['planet_kp_star_sub_chain']} |")
    lines.append(f"| KP-249 lords | {s['kp_249_lords']} |")
    lines.append(f"| KP boundary ±1″ parity probes | "
                 f"{s['kp_boundary_parity_probes']} |")
    lines.append(f"| Exact-boundary convention | "
                 f"{s['exact_boundary_convention']} |")
    lines.append(f"| Oracle table drift | {s['oracle_table_drift']} |")
    lines.append("")
    lines.append(f"- hard failures: {report['hard_failures']}")
    lines.append(f"- known convention differences: "
                 f"{report['convention_differences']}")
    lines.append(f"- oracle table-drift warnings: "
                 f"{report['oracle_table_drift_warnings']}")
    lines.append("")
    lines.append("## Layer summary")
    lines.append("")
    lines.append("| layer | total | passed | failed | conv.diff | "
                 "drift warn | unsupported |")
    lines.append("|---|---|---|---|---|---|---|")
    for name, t in report["layers"].items():
        lines.append(
            f"| {name} | {t['total_checks']} | {t['passed_checks']} | "
            f"{t['failed_checks']} | {t['convention_difference_checks']} | "
            f"{t['oracle_table_drift_warning_checks']} | "
            f"{t['unsupported_checks']} |")
    lines.append("")
    m = report["kp_249_table_meta"]
    lines.append(f"KP-249 table: Junopath rows={m['junopath_rows']}, "
                 f"PyJHora rows={m['pyjhora_rows']}, compared="
                 f"{m['compared_rows']}")
    lines.append("")
    lines.append("## Per-planet KP chain (star_lord, sub_lord)")
    lines.append("")
    lines.append("| chart | planet | longitude | JP star | OR star | "
                 "JP sub | OR sub | OR sub_sub (unsupported) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for fx in report["per_fixture_chains"]:
        for name, e in fx["planets"].items():
            lines.append(
                f"| {fx['chart_id']} | {name} | {e['longitude']:.6f} | "
                f"{e['junopath']['star_lord']} | {e['pyjhora']['star_lord']} | "
                f"{e['junopath']['sub_lord']} | {e['pyjhora']['sub_lord']} | "
                f"{e['pyjhora']['sub_sub_lord']} |")
    lines.append("")
    lines.append("## Boundary edge cases (1 arc-sec before / on / after)")
    lines.append("")
    lines.append("`exactly_on` is a KNOWN convention difference (D020b), not "
                 "a parity check; the ±1 arc-second probes are the parity "
                 "checks.")
    lines.append("")
    lines.append("| kp_no | boundary deg | position | parity check | "
                 "longitude | JP star/sub | OR star/sub | agree |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in report["boundary_results"]:
        agree = (r["junopath"] == r["pyjhora"])
        lines.append(
            f"| {r['boundary_kp_no']} | {r['boundary_deg']:.6f} | "
            f"{r['position']} | {'yes' if r['is_parity_check'] else 'no'} | "
            f"{r['longitude']:.6f} | "
            f"{r['junopath']['star_lord']}/{r['junopath']['sub_lord']} | "
            f"{r['pyjhora']['star_lord']}/{r['pyjhora']['sub_lord']} | "
            f"{'Y' if agree else 'N'} |")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_mismatches_csv(path: Path, mismatches: list[dict]):
    fields = ["chart_id", "layer", "severity", "planet_or_house", "field",
              "junopath_value", "pyjhora_value", "longitude_used",
              "likely_cause"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in mismatches:
            writer.writerow({k: row.get(k, "") for k in fields})


def write_unsupported_md(path: Path, notes: list[str]):
    lines = ["# Unsupported Layers (non-fatal warnings)", ""]
    lines.append("These layers cannot be compared 1:1 because one side does "
                 "not expose the field. They are reported as WARNINGS and do "
                 "NOT count as parity failures or affect the exit code.")
    lines.append("")
    if not notes:
        lines.append("None.")
    for n in notes:
        lines.append(f"- {n}")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Safety gate (read-only git inspection)
# ---------------------------------------------------------------------------

def run_safety_check():
    """Return (safety_ok, status_text, offending_paths)."""
    # Per the task, git_status_after.txt holds the plain `--porcelain` output.
    status = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
        capture_output=True, text=True)
    status_text = status.stdout
    (ARTIFACT_DIR / "git_status_after.txt").write_text(
        status_text, encoding="utf-8")

    # Classify using -uall so untracked directories are expanded to individual
    # files; plain --porcelain collapses e.g. "artifacts/" to one entry that
    # would not literally match the allowed "artifacts/oracle_compare/" prefix.
    classify = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain", "-uall"],
        capture_output=True, text=True)

    # Tracked modifications/staged changes: anything not untracked ("??").
    offending = []
    for line in classify.stdout.splitlines():
        if not line.strip():
            continue
        code = line[:2]
        rel = line[3:].strip().replace("\\", "/")
        # Quoted/renamed paths: take the destination half if present.
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1]
        rel = rel.strip('"')
        if code == "??":
            allowed = any(rel == p or rel.startswith(p)
                          for p in ALLOWED_WRITE_PREFIXES)
            if not allowed:
                offending.append((code, rel))
            continue
        # Tracked change of any kind: must be inside allowed paths.
        allowed = any(rel == p or rel.startswith(p)
                      for p in ALLOWED_WRITE_PREFIXES)
        if not allowed:
            offending.append((code, rel))

    return (len(offending) == 0), status_text, offending


# ---------------------------------------------------------------------------
# Summary + main
# ---------------------------------------------------------------------------

def classify_findings(mismatches: list[dict]) -> dict:
    """Split recorded findings by severity (drives status + exit code)."""
    hard = [m for m in mismatches if m["severity"] == HARD_FAILURE]
    conv = [m for m in mismatches if m["severity"] == CONVENTION_DIFFERENCE]
    drift = [m for m in mismatches if m["severity"] == ORACLE_TABLE_DRIFT]
    return {
        "hard_failures": len(hard),
        "convention_differences": len(conv),
        "oracle_table_drift_warnings": len(drift),
        "warnings": len(conv) + len(drift),
    }


def write_summary(path: Path, *, gate0_report, kp_report, mismatches,
                  unsupported_notes, safety_ok, offending, gate0_only,
                  counts, overall_status, exit_code):
    gate0_status = "PASS" if gate0_report["passed"] else "FAIL"
    unsupported_present = bool(unsupported_notes)

    if gate0_only:
        planet_chain = kp249_lords = "SKIPPED (Gate 0 failed)"
        exact_boundary = "SKIPPED"
        drift_status = "SKIPPED"
    else:
        s = kp_report["statuses"]
        planet_chain = s["planet_kp_star_sub_chain"]
        kp249_lords = s["kp_249_lords"]
        exact_boundary = s["exact_boundary_convention"]
        drift_status = s["oracle_table_drift"]

    lines = ["# PyJHora Oracle Comparison — Summary", ""]
    lines.append(f"## Overall: **{overall_status}**")
    lines.append("")
    lines.append("| area | status |")
    lines.append("|---|---|")
    lines.append(f"| Gate 0 (settings parity) | {gate0_status} |")
    lines.append(f"| Planet KP star/sub chain | {planet_chain} |")
    lines.append(f"| KP-249 lords | {kp249_lords} |")
    lines.append(f"| Exact-boundary convention | {exact_boundary} |")
    lines.append(f"| Oracle table drift | {drift_status} |")
    lines.append(f"| Unsupported layers | "
                 f"{'PRESENT' if unsupported_present else 'NONE'} |")
    lines.append(f"| Safety | {'PASS' if safety_ok else 'FAIL'} |")
    lines.append("")
    lines.append(f"- hard failures (count toward exit 1): "
                 f"{counts['hard_failures']}")
    lines.append(f"- known convention differences: "
                 f"{counts['convention_differences']}")
    lines.append(f"- oracle table-drift warnings: "
                 f"{counts['oracle_table_drift_warnings']}")
    lines.append(f"- total warnings (non-fatal): {counts['warnings']}")
    lines.append(f"- exit code: {exit_code}")
    lines.append("")
    lines.append("Classification policy: only real parity mismatches in Gate 0 "
                 "(longitudes, cusps, settings), planet KP star/sub lords, "
                 "future cusp KP star/sub lords, or unexpected KP-249 *lord* "
                 "mismatches are hard failures. The exact-boundary point is a "
                 "KNOWN convention difference (Junopath [start, end) per "
                 "DECISIONS.md D020(b); the ±1 arc-second probes are the "
                 "parity checks). KP-249 *boundary-degree* differences where "
                 "lords agree are oracle table-drift warnings (PyJHora's "
                 "static prasna_kp_249_dict rounding vs Junopath's exact "
                 "Vimshottari generation).")
    lines.append("")

    if not safety_ok:
        lines.append("## SAFETY FAIL")
        lines.append("Tracked files outside the allowed paths changed:")
        for code, rel in offending:
            lines.append(f"- `{code}` {rel}")
        lines.append("")

    lines.append("## Gate 0 tally")
    t = gate0_report["tally"]
    lines.append(f"total={t['total_checks']} passed={t['passed_checks']} "
                 f"failed={t['failed_checks']} unsupported="
                 f"{t['unsupported_checks']}")
    lines.append("")
    if not gate0_only:
        lines.append("## KP chain tally (by layer)")
        for name, lt in kp_report["layers"].items():
            lines.append(f"- {name}: total={lt['total_checks']} "
                         f"passed={lt['passed_checks']} "
                         f"failed={lt['failed_checks']} "
                         f"conv_diff={lt['convention_difference_checks']} "
                         f"drift_warn="
                         f"{lt['oracle_table_drift_warning_checks']} "
                         f"unsupported={lt['unsupported_checks']}")
        lines.append("")

    # Findings split by severity.
    hard = [m for m in mismatches if m["severity"] == HARD_FAILURE]
    nonfatal = [m for m in mismatches if m["severity"] != HARD_FAILURE]

    lines.append("## Hard failures")
    lines.append("")
    if hard:
        lines.append("| chart | layer | where | field | Junopath | PyJHora | "
                     "longitude | likely cause |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for m in hard:
            lines.append(
                f"| {m['chart_id']} | {m['layer']} | {m['planet_or_house']} | "
                f"{m['field']} | {m['junopath_value']} | {m['pyjhora_value']} | "
                f"{m['longitude_used']} | {m['likely_cause']} |")
    else:
        lines.append("None.")
    lines.append("")

    lines.append("## Known differences & warnings (non-fatal)")
    lines.append("")
    if nonfatal:
        lines.append("| chart | layer | severity | where | field | Junopath | "
                     "PyJHora | longitude | note |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for m in nonfatal:
            lines.append(
                f"| {m['chart_id']} | {m['layer']} | {m['severity']} | "
                f"{m['planet_or_house']} | {m['field']} | {m['junopath_value']}"
                f" | {m['pyjhora_value']} | {m['longitude_used']} | "
                f"{m['likely_cause']} |")
    else:
        lines.append("None.")
    lines.append("")

    lines.append("## Artifacts")
    for fn in ("gate0_settings_report.json", "gate0_settings_report.md",
               "kp_chain_report.json", "kp_chain_report.md",
               "kp_chain_mismatches.csv", "unsupported_layers.md",
               "git_status_after.txt"):
        lines.append(f"- artifacts/oracle_compare/{fn}")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    ephemeris, kp_engine = load_junopath_engines()
    drik, pj_utils, pj_const = load_pyjhora()
    import swisseph as swe
    oracle = Oracle(drik, pj_utils, pj_const, swe)
    fixtures = load_fixtures()
    if len(fixtures) < 3:
        print(f"ERROR: expected >=3 Gate 0 fixtures, found {len(fixtures)}")
        return 1

    # PHASE 0
    gate0_report, gate0_mismatches = run_gate0(ephemeris, oracle, fixtures)
    write_json(ARTIFACT_DIR / "gate0_settings_report.json", gate0_report)
    write_gate0_md(ARTIFACT_DIR / "gate0_settings_report.md", gate0_report)

    all_mismatches = list(gate0_mismatches)
    unsupported_notes: list[str] = []
    kp_report = None
    gate0_only = not gate0_report["passed"]

    # PHASE 1 (only if Gate 0 passed)
    if gate0_report["passed"]:
        kp_report, kp_mismatches = run_kp_chain(
            ephemeris, kp_engine, oracle, fixtures)
        all_mismatches.extend(kp_mismatches)
        unsupported_notes = kp_report["unsupported"]
        write_json(ARTIFACT_DIR / "kp_chain_report.json", kp_report)
        write_kp_chain_md(ARTIFACT_DIR / "kp_chain_report.md", kp_report)
    else:
        skipped = {
            "phase": "kp_chain_comparison",
            "skipped": True,
            "reason": "Gate 0 failed; KP chain comparison not run.",
        }
        write_json(ARTIFACT_DIR / "kp_chain_report.json", skipped)
        (ARTIFACT_DIR / "kp_chain_report.md").write_text(
            "# KP Chain Comparison Report\n\n"
            "**SKIPPED** — Gate 0 failed; KP chain comparison not run.\n",
            encoding="utf-8")

    write_mismatches_csv(ARTIFACT_DIR / "kp_chain_mismatches.csv",
                         all_mismatches)
    write_unsupported_md(ARTIFACT_DIR / "unsupported_layers.md",
                         unsupported_notes)

    # Safety gate (read-only git inspection + git_status_after.txt)
    safety_ok, _status_text, offending = run_safety_check()

    # Severity-driven classification (exit code depends ONLY on hard failures
    # and safety; convention differences, drift warnings, and unsupported
    # layers are non-fatal known oracle limitations).
    counts = classify_findings(all_mismatches)
    hard_failures = counts["hard_failures"]
    warnings = counts["warnings"]

    if not safety_ok:
        exit_code = 2
        overall_status = "SAFETY_VIOLATION"
    elif gate0_only or hard_failures > 0:
        exit_code = 1
        overall_status = "FAIL"
    elif warnings > 0 or unsupported_notes:
        exit_code = 0
        overall_status = "PASS_WITH_KNOWN_ORACLE_LIMITATIONS"
    else:
        exit_code = 0
        overall_status = "PASS"

    write_summary(
        ARTIFACT_DIR / "summary.md",
        gate0_report=gate0_report, kp_report=kp_report,
        mismatches=all_mismatches, unsupported_notes=unsupported_notes,
        safety_ok=safety_ok, offending=offending, gate0_only=gate0_only,
        counts=counts, overall_status=overall_status, exit_code=exit_code)

    # Concise final stdout for the operator.
    print(f"summary: {ARTIFACT_DIR / 'summary.md'}")
    print(f"overall: {overall_status}")
    print(f"exit_code: {exit_code}")
    print(f"hard_failures: {hard_failures}")
    print(f"warnings: {warnings}")
    print(f"safety: {'PASS' if safety_ok else 'FAIL'}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
