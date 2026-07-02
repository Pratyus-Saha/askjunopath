"""Vedic engine validation harness - prints the field-A and field-B tables.

Run from the backend directory:

    SE_EPHE_PATH="$(pwd)/ephe" python scripts/vedic_validate.py

Two DIFFERENT standards, never mixed (task spec):

* FIELD A (placements / houses / vargas / dasha) - JHora is the oracle. Needs
  ``tests/fixtures/vedic_fixtures.json``. India charts (vedic_01/_02/_05, +05:30)
  run FIRST; NYC (_03) and Sydney (_04) only after the India charts are green,
  to surface time-handling defects. Longitudes within <60"; sign/nakshatra/pada/
  house/D-9/D-10 exact; MD/AD/PD/SD lords + start/end to the minute.

* FIELD B (dignity / graha drishti) - NO ground truth in the fixtures. This
  harness only PRINTS a table (planet | sign | dignity | houses aspected) for
  human textbook review. These fields are "computed, pending manual spot-check",
  never "tested".

If the fixtures file is absent the harness reports BLOCKED for field A and the
5-chart field-B review (both need the fixture birth data), and runs a single
self-chosen SMOKE chart so the dignity/aspect logic can be eyeballed. It never
fabricates JHora values.

Expected ``vedic_fixtures.json`` schema (one entry per chart id)::

    {
      "vedic_01": {
        "name": "India A",
        "datetime_local": "1990-01-01T14:35:00",
        "gmt_offset": 5.5,
        "lat": 12.9716, "lon": 77.5946,
        "expected": {
          "lagna": {"sign": "...", "nakshatra": "...", "pada": 1,
                     "d9_sign": "...", "d10_sign": "...", "longitude": 27.6},
          "planets": {
            "Sun": {"longitude": 256.9, "sign": "...", "nakshatra": "...",
                     "pada": 2, "house": 9, "d9_sign": "...", "d10_sign": "..."},
            ...
          },
          "dasha_at_birth": {
            "maha":       {"lord": "...", "start": "ISO", "end": "ISO"},
            "antar":      {"lord": "...", "start": "ISO", "end": "ISO"},
            "pratyantar": {"lord": "...", "start": "ISO", "end": "ISO"},
            "sookshma":   {"lord": "...", "start": "ISO", "end": "ISO"}
          }
        }
      },
      ...
    }
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Allow running as a bare script from the backend dir.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engines.vedic_engine import compute_vedic_chart  # noqa: E402

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "vedic_fixtures.json"
)

# India first, then NYC, then Sydney (spec run order).
FIELD_A_ORDER = ["vedic_01", "vedic_02", "vedic_05", "vedic_03", "vedic_04"]
INDIA_CHARTS = {"vedic_01", "vedic_02", "vedic_05"}

_ARCSEC_TOL_DEG = 60.0 / 3600.0

# A self-chosen SMOKE chart - NOT a fixture, NOT validation.
SMOKE = dict(
    name="SMOKE (Bengaluru +05:30) - NOT a fixture, NOT validation",
    datetime_local="1990-01-01T14:35:00",
    gmt_offset=5.5,
    lat=12.9716,
    lon=77.5946,
    target_date="2026-07-02T12:00:00",
)


# ---------------------------------------------------------------------------
# Field A
# ---------------------------------------------------------------------------

def _check_field_a(fx: dict) -> list[str]:
    """Return a list of failure strings for one chart ([] == pass)."""
    result = compute_vedic_chart(
        datetime_local=fx["datetime_local"],
        gmt_offset=fx["gmt_offset"],
        lat=fx["lat"],
        lon=fx["lon"],
        target_date=fx["datetime_local"],
    )
    exp = fx["expected"]
    fails: list[str] = []
    planets = {p["name"]: p for p in result["planets"]}

    for name, ep in exp.get("planets", {}).items():
        gp = planets[name]
        if "longitude" in ep and abs(gp["longitude"] - ep["longitude"]) > _ARCSEC_TOL_DEG:
            delta_arcsec = abs(gp["longitude"] - ep["longitude"]) * 3600.0
            fails.append(f"{name}.longitude off by {delta_arcsec:.1f}\"")
        for field in ("sign", "nakshatra", "pada", "house", "d9_sign", "d10_sign"):
            if field in ep and gp[field] != ep[field]:
                fails.append(f"{name}.{field} {gp[field]!r}!={ep[field]!r}")

    for field, val in exp.get("lagna", {}).items():
        if field == "longitude":
            if abs(result["lagna"]["longitude"] - val) > _ARCSEC_TOL_DEG:
                fails.append("lagna.longitude off")
        elif result["lagna"][field] != val:
            fails.append(f"lagna.{field} {result['lagna'][field]!r}!={val!r}")

    exp_dasha = exp.get("dasha_at_birth")
    if exp_dasha:
        got = result["dasha"]
        for level in ("maha", "antar", "pratyantar", "sookshma"):
            if got[level]["lord"] != exp_dasha[level]["lord"]:
                fails.append(f"dasha.{level}.lord")
            for edge in ("start", "end"):
                g = datetime.fromisoformat(got[level][edge]).replace(second=0, microsecond=0)
                e = datetime.fromisoformat(exp_dasha[level][edge]).replace(second=0, microsecond=0)
                if g != e:
                    fails.append(f"dasha.{level}.{edge} (minute)")
    return fails


def run_field_a(fixtures: dict) -> None:
    print("=" * 72)
    print("FIELD A - placements / houses / vargas / dasha (JHora oracle)")
    print("=" * 72)
    india_ok = True
    for chart_id in FIELD_A_ORDER:
        if chart_id not in fixtures:
            print(f"  {chart_id:10s} MISSING from fixtures - skipped")
            continue
        if chart_id not in INDIA_CHARTS and not india_ok:
            print(f"  {chart_id:10s} DEFERRED - India charts not green yet")
            continue
        fails = _check_field_a(fixtures[chart_id])
        status = "PASS" if not fails else "FAIL"
        print(f"  {chart_id:10s} {status}"
              + ("" if not fails else "  :: " + "; ".join(fails)))
        if fails and chart_id in INDIA_CHARTS:
            india_ok = False


# ---------------------------------------------------------------------------
# Field B (print-only, human review)
# ---------------------------------------------------------------------------

def print_field_b(label: str, result: dict) -> None:
    print("-" * 72)
    print(f"FIELD B - dignity + graha drishti  [{label}]")
    print("  (COMPUTED, pending manual textbook spot-check - NOT JHora-validated)")
    print("-" * 72)
    print(f"  Lagna: {result['lagna']['sign']} {result['lagna']['degree']:.2f}")
    print(f"  {'planet':8s} {'sign':12s} {'deg':>6s}  {'house':>5s}  "
          f"{'dignity':14s} houses_aspected")
    for p in result["planets"]:
        print(f"  {p['name']:8s} {p['sign']:12s} {p['degree']:6.2f}  "
              f"{p['house']:5d}  {p['dignity']:14s} {p['aspects_houses']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if not os.environ.get("SE_EPHE_PATH"):
        ephe = Path(__file__).resolve().parent.parent / "ephe"
        if ephe.is_dir():
            os.environ["SE_EPHE_PATH"] = str(ephe)

    if FIXTURE_PATH.exists():
        fixtures = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        run_field_a(fixtures)
        print()
        for chart_id in FIELD_A_ORDER:
            if chart_id in fixtures:
                fx = fixtures[chart_id]
                result = compute_vedic_chart(
                    datetime_local=fx["datetime_local"], gmt_offset=fx["gmt_offset"],
                    lat=fx["lat"], lon=fx["lon"], target_date=fx["datetime_local"],
                )
                print_field_b(f"{chart_id} - {fx.get('name', '')}", result)
        return 0

    # Blocked path.
    print("=" * 72)
    print("FIELD A - BLOCKED ON FIXTURES")
    print("=" * 72)
    print(f"  {FIXTURE_PATH} does not exist.")
    print("  Per spec: functions are built; validation STOPS here. JHora values")
    print("  are never fabricated. Provide the 5 charts (vedic_01.._05) to run.")
    print()
    print("=" * 72)
    print("FIELD B - 5-chart review table BLOCKED (needs the fixture birth data)")
    print("=" * 72)
    print("  Running one self-chosen SMOKE chart so the logic can be eyeballed:")
    print()
    result = compute_vedic_chart(
        datetime_local=SMOKE["datetime_local"], gmt_offset=SMOKE["gmt_offset"],
        lat=SMOKE["lat"], lon=SMOKE["lon"], target_date=SMOKE["target_date"],
    )
    print_field_b(SMOKE["name"], result)
    print()
    d = result["dasha"]
    print("  Current dasha path (smoke):")
    for k in ("maha", "antar", "pratyantar", "sookshma"):
        print(f"    {k:11s} {d[k]['lord']:8s} {d[k]['start']} -> {d[k]['end']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
