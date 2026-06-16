# BUGS.md

## BUG-001: Rahu-only JHora tolerance mismatch
**Status:** Diagnosed · **Severity:** Medium · **Area:** Ephemeris validation · **Discovered:** Day 2 validation

**Blocked work:** No. This does not block nakshatra integration, chart integration, frontend type generation, or Day 2 closeout. Nakshatra, chart integration, Moon validation 10/10, and all frontend work passed. This is Rahu-only.

### Summary

The backend test suite produced Rahu-only failures in `tests/test_ephemeris.py` when `SE_EPHE_PATH` was unset. With Swiss `.se1` files loaded from `C:\Users\assas\swisseph\ephe`, the same Rahu/JHora assertions pass. The failures were therefore an environment/validation-gate problem, not a Rahu math bug.

Failing tests:
- `tests/test_ephemeris.py::test_jhora_planet_longitudes`
- `tests/test_ephemeris.py::test_jhora_rahu_explicit`

### Observed Rahu deltas vs the 5-arcsec tolerance

| Fixture | Approx delta |
|---|---|
| fixture_01_india | ~7.10 arcsec |
| fixture_03_midnight | ~6.88 arcsec |
| fixture_04_pre1990 | ~11.51 arcsec |
| fixture_05_southern | ~16.98 arcsec |

### Diagnosis

- Deltas of 7-17 arcsec are consistent with a TRUE node, not a MEAN node (a mean node would show ~1.5°, roughly 5000 arcsec).
- `test_rahu_is_true_node_not_mean_node` verifies the engine Rahu against a direct `swe.TRUE_NODE` call at the same Julian day.
- When `SE_EPHE_PATH` is unset, pyswisseph silently falls back to Moshier even when the code asks for `swe.FLG_SWIEPH`; node-only arcsecond scatter is the visible symptom.
- With `SE_EPHE_PATH=C:\Users\assas\swisseph\ephe` and `.se1` files available, the strict JHora comparison gate passes.
- Ketu is derived as Rahu + 180°.
- The mismatch is limited to Rahu-specific assertions. This is not a nakshatra issue.
- Moon validation passed 10/10 after correcting one manual JHora input-time mistake.
- Local Siliguri V10 chart generation matched JHora Moon nakshatra and pada: Uttara Ashadha, pada 3.
- Browser-to-backend `/chart/generate` is verified and working.

### Resolution

No ephemeris math fix, fixture edit, or tolerance loosening is needed. The strict JHora parity tests should run only when `ephemeris_files_ok()` confirms Swiss `.se1` files are present and actually in use; otherwise they should skip loudly with `SWISS_EPHE_REQUIRED`.

### Do not do

- Do not loosen Rahu tolerance casually.
- Do not edit JHora fixture values without source-backed evidence.
- Do not mix this fix with KP work.
- Do not change ephemeris math outside a dedicated branch with before/after evidence.
- Do not treat this as a nakshatra bug.

### Recommended next step

Keep the ephemeris guard in the JHora parity tests and ensure local/CI runs set `SE_EPHE_PATH` to the Swiss file directory before running the strict gate.
