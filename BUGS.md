# BUGS.md

## BUG-001: Rahu-only JHora tolerance mismatch
**Status:** Open · **Severity:** Medium · **Area:** Ephemeris validation · **Discovered:** Day 2 validation

**Blocked work:** No. This does not block nakshatra integration, chart integration, frontend type generation, or Day 2 closeout. Nakshatra, chart integration, Moon validation 10/10, and all frontend work passed. This is Rahu-only.

### Summary

The backend test suite has Rahu-only failures in `tests/test_ephemeris.py` — small arcsecond-level mismatches against JHora reference values. Everything else in Day 2 passed: nakshatra engine tests, chart integration tests, Moon validation, frontend type generation, frontend lint, frontend build, and local browser-to-backend chart generation.

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

### Evidence

- Deltas of 7-17 arcsec are consistent with a TRUE node, not a MEAN node (a mean node would show ~1.5°, roughly 5000 arcsec).
- The local chart response/settings show `node_type: TRUE`, but the literal Swiss Ephemeris node body/flag has NOT yet been verified at the source level — that still needs focused verification. The TRUE-vs-MEAN read above is inferred from delta magnitude, not confirmed in code.
- Ketu is derived as Rahu + 180°.
- The mismatch is limited to Rahu-specific assertions. This is not a nakshatra issue.
- Moon validation passed 10/10 after correcting one manual JHora input-time mistake.
- Local Siliguri V10 chart generation matched JHora Moon nakshatra and pada: Uttara Ashadha, pada 3.
- Browser-to-backend `/chart/generate` is verified and working.

### Hypothesis (unproven)

A JHora-vs-pyswisseph true-node convention difference, or a Rahu-specific tolerance policy question. Not yet proven; needs focused diagnosis before any code or fixture change.

### Do not do

- Do not loosen Rahu tolerance casually.
- Do not edit JHora fixture values without source-backed evidence.
- Do not mix this fix with KP work.
- Do not change ephemeris math outside a dedicated branch with before/after evidence.
- Do not treat this as a nakshatra bug.

### Recommended next step

Read-only diagnosis on a separate branch, scheduled AFTER KP. Confirm the exact Swiss Ephemeris node body/flag in use and compare against JHora node settings, then decide between a code fix, a fixture correction, or a documented tolerance change.

- Diagnosis branch: `agent/claude/rahu-diagnosis`
- Implementation branch (only if needed): `agent/codex/rahu-ephemeris-fix`
