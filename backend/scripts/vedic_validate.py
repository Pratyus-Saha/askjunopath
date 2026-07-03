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

On-disk ``vedic_fixtures.json`` shape (a JSON ARRAY; vocabulary is translated by
``vedic_fixture_adapter``)::

    [
      {"id": "vedic_01",
       "input": {"date": "1995-08-15", "time": "10:30",
                  "gmt_offset": "+05:30" | null, "place": "Kolkata",
                  "lat": 22.5726, "lon": 88.3639},
       "lagna": {"lon_dms": "9Li42'52.88\"", "sign": "Li", "nakshatra": "Swat",
                  "pada": 1, "d9_sign": "Sg", "d10_sign": "Cp"},
       "planets": {"Sun": {"lon_dms": "28Cn07'32.20\"", "sign": "Cn",
                            "nakshatra": "Asre", "pada": 4, "house": 10,
                            "d9_sign": "Pi", "d10_sign": "Aq"}, ...},
       "houses": {"1": {"sign": "Li", "planets": ["As", "Ra"]}, ...},
       "dasha_at_birth": {"MD": {"lord": "Merc", "start": "1985-01-30 05:11:57",
                                  "end": "2002-01-30 08:23:30"},
                          "AD"/"PD"/"SD": ... (lord may be null)}},
      ...
    ]

Signs are 2-letter abbrevs, nakshatras short, longitude is a DMS string,
``gmt_offset`` a signed string or null (resolved from ``place`` when null), and
dasha keys are MD/AD/PD/SD with abbreviated lords and naive local timestamps.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
# Allow running as a bare script: backend root (for app.*) and tests/ (adapter).
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_BACKEND / "tests"))

from app.engines.vedic_engine import compute_vedic_chart  # noqa: E402
from vedic_fixture_adapter import (  # noqa: E402
    FIELD_A_ORDER,
    FIXTURE_PATH,
    INDIA_CHARTS,
    check_field_a,
    load_fixtures,
    run_chart,
)

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
        entry = fixtures[chart_id]
        inp = entry["input"]
        fails = check_field_a(entry, run_chart(entry))
        status = "PASS" if not fails else "FAIL"
        header = f"  {chart_id:10s} {status}  (UT{inp['gmt_offset']:+.2f}h {inp['place']})"
        print(header + ("" if not fails
                        else "\n               :: " + "\n               :: ".join(fails)))
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
        fixtures = load_fixtures()
        run_field_a(fixtures)
        print()
        for chart_id in FIELD_A_ORDER:
            if chart_id in fixtures:
                entry = fixtures[chart_id]
                print_field_b(f"{chart_id} ({entry['input']['place']})", run_chart(entry))
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
