# Ephemeris Engine Specification
**File:** `backend/app/engines/ephemeris_engine.py`
**Spec version:** 1.0 (frozen with chart.json v1.0; changes after Day 1 are additive only)
**Owner tool:** Claude Code only. No other agent edits this file.
**Source:** Master plan Sections 5, 6, 10, 20, 21; playbook Day 1.

---

## 1. Purpose and Scope

Compute trustworthy raw sidereal positions from birth input. This engine is the foundation layer: every downstream engine (nakshatra, KP, house, dasha, strength, divisional, transit) reads its output from chart.json and never recomputes ephemeris values.

**This engine OWNS these chart.json fields:**

- `birth.datetime_utc`, `birth.julian_day_ut`
- `settings.ayanamsa_value_deg`
- Per planet: `name`, `longitude`, `sign`, `sign_lord`, `sign_degree`, `retrograde`, `combust`, `speed_deg_per_day`
- Per house: `cusp_longitude`, `cusp_sign`, `cusp_sign_lord`
- Ascendant longitude, sign, and degree

**This engine MUST NOT compute** (later engines fill these): `nakshatra` block (Day 2), `kp` block and `cusp_sub_lord` (Days 3 to 4), `house_occupied` and `occupants` and `significator_*` (Day 4 house_engine via cusp spans), `dashas` (Day 5), `strengths` (Day 6), `divisional` (Day 6), `transits` (Day 8). Leave those fields absent or null per the pydantic models. Do not guess house occupancy from signs.

All functions pure where possible. No module imports another engine's internals. No new dependencies beyond `pyswisseph` and the standard library (`zoneinfo`, `datetime`) without asking.

---

## 2. Fixed Settings (non-negotiable)

| Setting | Value | pyswisseph call |
|---|---|---|
| Zodiac | Sidereal | `swe.FLG_SIDEREAL` on every position call |
| Position type | TRUE / geometric (Drik) | `swe.FLG_TRUEPOS` on every position call |
| Ayanamsa | KP-Newcomb (Krishnamurti) | `swe.set_sid_mode(swe.SIDM_KRISHNAMURTI, 0, 0)` |
| Nodes | True node only | `swe.TRUE_NODE`. Never `swe.MEAN_NODE` |
| House system | Placidus | `swe.houses_ex(..., b'P', ...)` |
| Ephemeris files | Swiss `.se1` files at `SE_EPHE_PATH` | `swe.set_ephe_path(os.environ["SE_EPHE_PATH"])` |
| Calendar | Gregorian | `swe.GREG_CAL` |
| Leap seconds | Ignored | per Section 6 edge-case column |

**Call order matters.** At module init or engine entry: (1) `swe.set_ephe_path(...)`, (2) `swe.set_sid_mode(swe.SIDM_KRISHNAMURTI, 0, 0)`. Both BEFORE any `swe.calc_ut` or `swe.houses_ex` call. The first debugging move for any consistent arc-minute offset across all planets is verifying this placement (playbook error trap #1).

**Ephemeris file guard.** If the `.se1` files are missing, pyswisseph silently falls back to the built-in Moshier ephemeris and returns slightly different numbers (playbook error trap #4). The engine exposes `ephemeris_files_ok() -> bool` that asserts the required `.se1` files physically exist at `SE_EPHE_PATH` AND that a test position call with `swe.FLG_SWIEPH` succeeds without fallback. `/health` (built by Codex per docs/health.md) calls this function; the Docker test calls `/health` from inside the container.

**Production file packaging.** Do not commit Swiss `.se1` files to git by default. For backend image builds, copy the founder-approved local ephemeris files into `backend/ephe/` before running `docker build` from `backend/`; `.gitignore` keeps that directory out of commits. `backend/Dockerfile` copies `ephe/*.se1` into `/app/ephe` and sets `SE_EPHE_PATH=/app/ephe`, so a production image build fails loudly if the local build context does not include the files.

---

## 3. Inputs

```python
def compute_ephemeris(
    datetime_local: str,   # ISO 8601 naive local time, e.g. "1994-03-21T14:35:00"
    timezone: str,         # IANA zone, e.g. "Asia/Kolkata", "America/New_York"
    lat: float,            # decimal degrees, north positive
    lon: float,            # decimal degrees, east positive
) -> EphemerisResult:      # pydantic model from backend/schemas/models.py
```

Input validation (raise structured errors, never bare exceptions):

- `|lat| > 66.0` → raise `LatUnsupportedError`, which the API layer maps to HTTP 400 with error code `LAT_UNSUPPORTED` (Placidus is undefined near the poles; Section 20). The test asserts the error code, not a stack trace.
- Unknown IANA zone → `InvalidTimezoneError` (API maps to 422).
- `lat` outside [-90, 90] or `lon` outside [-180, 180] → 422.

---

## 4. Time Handling (one conversion, at the edge)

The single most damaging Day 1 bug class. One hour of error moves the Moon roughly half a degree; padas shift, sublords flip, nothing downstream can recover (curriculum, Build Day 1).

1. Parse `datetime_local` as a naive datetime.
2. Localize it with `zoneinfo.ZoneInfo(timezone)`. The IANA database handles historical offsets and DST, including pre-1990 and US DST births.
3. Convert to UTC exactly once, here, at the engine boundary. Store as `birth.datetime_utc` (ISO 8601 with `Z`).
4. Compute Julian Day from the UTC components:
   `jd_ut = swe.julday(year, month, day, hour + minute/60 + second/3600, swe.GREG_CAL)`
5. Store as `birth.julian_day_ut`.

**Never** pass local time to `swe.julday`. **Never** convert timezone twice. One fixture is a US birth under DST specifically to catch this (playbook error trap #3). Midnight births are an explicit edge case: a birth at 00:10 local can fall on the previous UTC date; the conversion above handles it, and one fixture covers it.

Ambiguous or non-existent local times (DST fold/gap): resolve with `fold=0` (earlier offset). Document this choice in a code comment; it is a convention, not a guess.

---

## 5. Planet Positions

Bodies, in this fixed output order:
`Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu`

For Sun through Saturn:

```python
flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED | swe.FLG_TRUEPOS
xx, retflag = swe.calc_ut(jd_ut, body_id, flags)
longitude = xx[0] % 360.0     # normalize to [0, 360)
speed_deg_per_day = xx[3]
retrograde = speed_deg_per_day < 0
```

**`FLG_TRUEPOS` is mandatory** (founder ruling, 2026-06-11, Option B of the
Day 1 apparent-vs-true finding). Jagannatha Hora's Drik Siddhanta export is
TRUE/geometric positions, not apparent positions; the Swiss Ephemeris default
(apparent, with light-time and annual aberration) sits ~20 arc-sec off on the
Sun and 7–47 arc-sec off on other planets, far outside the 5 arc-sec gate.
Dropping this flag reintroduces exactly that signature: every planet off by
arc-seconds with the Moon nearly exact (its aberration is ~0.7").

For the nodes:

- **Rahu** = `swe.calc_ut(jd_ut, swe.TRUE_NODE, flags)`. The fixtures assert Rahu's longitude explicitly because the mean node can sit up to 1.5° away and would otherwise hide (playbook error trap #2).
- **Ketu**: `longitude = (rahu_longitude + 180.0) % 360.0`. `speed_deg_per_day` = Rahu's speed. `retrograde` = same flag as Rahu (the true node oscillates; derive the flag from speed sign exactly like every other body, no special casing).

Derived per planet:

- `sign`: `SIGNS[int(longitude // 30)]` where `SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]`
- `sign_degree`: `longitude % 30.0`
- `sign_lord`: from the fixed table
  Aries→Mars, Taurus→Venus, Gemini→Mercury, Cancer→Moon, Leo→Sun, Virgo→Mercury, Libra→Venus, Scorpio→Mars, Sagittarius→Jupiter, Capricorn→Saturn, Aquarius→Saturn, Pisces→Jupiter

Also record `settings.ayanamsa_value_deg = swe.get_ayanamsa_ut(jd_ut)` rounded to 4 decimals, so every stored chart carries the ayanamsa it was computed with.

Precision rule: keep full float precision internally; round only at serialization to 4 decimal places for longitudes (matches the Section 5 examples, e.g. `322.4517`). Tests compare against full-precision values with tolerances, not against rounded strings.

---

## 6. Combustion Flags

A planet is combust when its angular separation from the Sun is within its orb. Angular separation:

```python
d = abs(planet_lon - sun_lon) % 360.0
separation = min(d, 360.0 - d)
```

Orb table (master plan Section 10):

| Planet | Orb | Retrograde orb |
|---|---|---|
| Moon | 12° | 12° |
| Mars | 17° | 17° |
| Mercury | 14° | 12° when retrograde |
| Jupiter | 11° | 11° |
| Venus | 10° | 8° when retrograde |
| Saturn | 15° | 15° |

Rules:

- The Sun is never combust (`combust = false` always).
- Rahu and Ketu are never combust (`combust = false` always; they are shadow points).
- Mercury and Venus use their tighter orb when their own `retrograde` flag is true. A unit test covers retro Mercury at 13° separation (combust at direct orb 14°, not combust at retro orb 12°: expected result NOT combust).
- Combustion does not modify any other field here; the strength engine (Day 6) consumes the flag.

---

## 7. Cusps and Ascendant

```python
cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b'P', flags=swe.FLG_SIDEREAL)
```

- `swe.set_sid_mode` must already be in effect, otherwise cusps come back tropical while planets are sidereal and nothing matches.
- Verify the pyswisseph version's return shape: `cusps` is the 12 house cusps (confirm whether indexing is 0-based 0..11 or 1-based 1..12 in the installed version with a quick REPL check before writing the mapping; do not assume).
- House objects 1 to 12 get `cusp_longitude` (normalized [0, 360), 4-decimal serialization), `cusp_sign`, `cusp_sign_lord` (same sign/lord tables as planets).
- Ascendant = `ascmc[0]`, sidereal. Expose `ascendant: { longitude, sign, sign_degree }`. The fixture acceptance requires the ascendant's sign to match JHora exactly, with one reference chart deliberately within 1° of a sign boundary across the 25-chart set.
- Cusp 1 must equal the ascendant longitude (Placidus invariant). Add an assertion test: `abs(cusps[house_1] - asc) < 1e-6` after normalization.

---

## 8. Output Shape

Returns an `EphemerisResult` that validates against `backend/schemas/models.py` (chart.json v1.0, Section 5). Do not modify the schema; if the schema seems wrong, stop and ask. Example of the engine-owned planet subset:

```json
{
  "name": "Saturn",
  "longitude": 322.4517,
  "sign": "Aquarius",
  "sign_lord": "Saturn",
  "sign_degree": 22.4517,
  "retrograde": false,
  "combust": false,
  "speed_deg_per_day": 0.0712
}
```

And the birth/settings blocks it fills:

```json
{
  "birth": {
    "datetime_local": "1994-03-21T14:35:00",
    "datetime_utc": "1994-03-21T09:05:00Z",
    "timezone": "Asia/Kolkata",
    "lat": 28.4595, "lon": 77.0266,
    "julian_day_ut": 2449432.87847
  },
  "settings": {
    "ayanamsa": "KP_NEWCOMB",
    "ayanamsa_value_deg": 23.7261,
    "node_type": "TRUE",
    "house_system": "PLACIDUS",
    "zodiac": "SIDEREAL"
  }
}
```

---

## 9. Acceptance Tolerances (the Day 1 gate)

Validated against Jagannatha Hora configured exactly as `docs/reference-settings.png`: KP-Newcomb (Krishnamurti) ayanamsa, Placidus houses, true node. A settings mismatch in JHora invalidates all comparisons at once; check the screenshot before filing any discrepancy.

| Quantity | Tolerance |
|---|---|
| All 9 planet longitudes | within 5 arc-seconds (0.001389°) of JHora |
| All 12 cusp longitudes | within 0.01° of JHora |
| Ascendant | exact sign match, degree within 0.01° |

When the code and JHora disagree: file a failing test that encodes the JHora value FIRST, then debug until green (Rule 7). Never adjust the expectation to match the output.

---

## 10. Fixture Format and Required Tests

Fixtures live in `tests/fixtures/charts/`, one JSON file per chart:

```json
{
  "chart_id": "fixture_01",
  "source": "Jagannatha Hora 8.x, settings per docs/reference-settings.png, exported 2026-06-11",
  "input": {
    "datetime_local": "1994-03-21T14:35:00",
    "timezone": "Asia/Kolkata",
    "lat": 28.4595,
    "lon": 77.0266
  },
  "expected": {
    "planets": { "Sun": 336.6342, "Moon": 102.4811, "Mars": 318.9050,
                 "Mercury": 320.1175, "Jupiter": 215.7433, "Venus": 351.2086,
                 "Saturn": 322.4517, "Rahu": 217.8814, "Ketu": 37.8814 },
    "cusps": { "1": 98.2331, "2": 124.5512, "3": 152.0190, "4": 181.4421,
               "5": 212.8870, "6": 245.1109, "7": 278.2331, "8": 304.5512,
               "9": 332.0190, "10": 1.4421, "11": 32.8870, "12": 65.1109 },
    "ascendant_sign": "Cancer"
  }
}
```

The numeric values above are FORMAT EXAMPLES ONLY. Real expectations come from JHora exports during the 13:30 validation block. Until they arrive, mark each fixture `"status": "PENDING_JHORA"` and have the test harness skip those with a visible warning, not a silent pass.

**Test list for `tests/test_ephemeris.py`:**

1. **5-chart longitude match.** Every planet in every fixture within 5 arc-sec; every cusp within 0.01°; ascendant exact sign. Parametrized over fixture files.
2. **Explicit Rahu assertion** per fixture (guards mean-node regression even if the loop test were weakened later).
3. **DST fixture.** One US birth under daylight saving (e.g., a July birth in `America/New_York`). Asserts `datetime_utc` and the Moon longitude.
4. **Midnight fixture.** A birth between 00:00 and 00:30 local where the UTC date differs from the local date. Asserts `julian_day_ut`.
5. **LAT_UNSUPPORTED.** `lat = 70.0` raises the structured error with code `LAT_UNSUPPORTED`; asserts the code.
6. **Ephemeris files guard.** `ephemeris_files_ok()` returns true in the dev environment; a second test monkeypatches `SE_EPHE_PATH` to an empty dir and asserts it returns false.
7. **Determinism.** Calling `compute_ephemeris` twice with identical input yields byte-identical serialized output.
8. **Normalization invariants.** All longitudes in `[0, 360)`; all `sign_degree` in `[0, 30)`; Ketu = (Rahu + 180) mod 360 to 1e-9; cusp 1 equals ascendant.
9. **Combustion units.** Retro-Mercury 13° separation → not combust; direct Mercury 13° → combust; Sun → never; Rahu/Ketu → never; separation math across the 0° boundary (Sun at 358°, planet at 5°: separation 7°).
10. **Schema round-trip.** Engine output parses into the pydantic models and re-serializes without loss.

Definition of done: `pytest` green on all of the above except fixtures still marked PENDING_JHORA, then stop.

---

## 11. Known Failure Modes (debug in this order)

| # | Symptom | Cause | First move |
|---|---|---|---|
| 1 | Every planet off by a consistent few arc-minutes | Wrong or missing ayanamsa mode | Verify `swe.set_sid_mode(swe.SIDM_KRISHNAMURTI, 0, 0)` runs before every calc, including in test setup |
| 2 | Rahu off by up to 1.5°, everything else fine | Mean node used | Confirm `swe.TRUE_NODE` |
| 3 | All positions off by a clean fraction of a degree, Moon worst | Local time reached `swe.julday`, or double tz conversion | Hand-trace the DST fixture: local → IANA → UTC → JD |
| 4 | Positions close but consistently slightly different from JHora | Silent Moshier fallback | `ephemeris_files_ok()`; check `SE_EPHE_PATH` inside the container, not just on the host |
| 5 | Cusps wrong, planets right | `houses_ex` called without the sidereal flag, or before `set_sid_mode` | Check flag and call order |
| 6 | Crash or garbage cusps on one input | High latitude reached Placidus | Input guard must reject before any swe call |

---

## 12. Non-Goals

No nakshatra/pada math. No sublords. No house occupancy. No dashas. No strength. No divisional charts. No transits. No caching layer. No async. No API routes (orchestration lives in `backend/app/routers/`). Anything not listed in Section 1's OWNS list is out of scope for this file.
