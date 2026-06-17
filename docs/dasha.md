# Vimshottari Dasha Engine Specification

**Spec doc for `backend/app/engines/dasha_engine.py`. Read order: docs/PROJECT_CONTEXT.md → AGENTS.md → docs/nakshatra.md → this doc, before code.**
**Created: 2026-06-17. Status: FROZEN. Source of truth for how Vimshottari mahadasha / antardasha / pratyantardasha boundaries are computed. Internal only (D023/D027): the public `chart.dashas` field stays `null`.**

This document is a deterministic engineering contract, not an astrology primer. If it conflicts with the code, this doc and the fixture win and the code is corrected (AGENTS.md Rules 2, 7, 8). If it conflicts with `schemas/chart.json`, the schema wins — but this engine adds **no** public field, so that cannot arise here.

---

## 1. Internal-only status (load-bearing)

- The dasha engine is **internal**. It returns a plain `DashaTimeline` object and **never** writes to the public chart payload.
- `chart.dashas` (the public `DashaBlock | None` field) stays **`null`** in v1.2. This task does **not** populate it (D023 keeps reserved fields unpopulated; D027 makes the dasha engine internal-only).
- No schema bump. No `schema_version` change (stays `1.2`). No `chart_engine_version` change (stays `1.4.0`). The chart router does not import or call this engine.
- Consumers (future strength/scoring/prediction engines, node agency v2 per D026) call `compute_dasha(...)` / `compute_dasha_from_chart(...)` directly and read the timeline; nothing reaches the public API until a later founder decision lifts D023.

## 2. Vimshottari order and year durations

The lord sequence is the Vimshottari cycle — the same nakshatra-lord cycle frozen in `docs/nakshatra.md`, declared once there and reused here:

```
Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury
```

Year durations per lord (whole years):

| Lord | Years |
| --- | ---: |
| Ketu | 7 |
| Venus | 20 |
| Sun | 6 |
| Moon | 10 |
| Mars | 7 |
| Rahu | 18 |
| Jupiter | 16 |
| Saturn | 19 |
| Mercury | 17 |
| **Total** | **120** |

The full cycle is **120 years** = nine mahadashas, each lord appearing exactly once. A timeline built from any birth lord rotates this sequence to start at that lord (e.g. from Venus: Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury, Ketu).

## 3. "Started from Moon": the birth mahadasha and balance

JHora's screenshot setting is **"Started from Moon"**. The birth mahadasha lord is the **Moon's nakshatra lord**, read **from the existing chart Moon nakshatra block** (`planets[Moon].nakshatra.lord`). The Moon is **never recomputed** by this engine; it consumes the value the nakshatra engine already produced (single source of truth, AGENTS.md §4 timezone/single-conversion discipline applied to the Moon).

The **balance** of the birth mahadasha (how much of it remains at birth) uses the Moon's position within its nakshatra:

```
NAK_SPAN            = 13 deg 20 min = 13.333333333333334 deg
remaining_fraction  = (NAK_SPAN - moon_degree_in_nakshatra) / NAK_SPAN
birth_balance_years = MD_years * remaining_fraction
elapsed_years       = MD_years - birth_balance_years
```

`moon_degree_in_nakshatra` is the chart's `planets[Moon].nakshatra.degree_in_nakshatra`. `MD_years` is the birth lord's duration from the table above.

The **anchor** (the back-projected start of the birth mahadasha) is the instant the Sun was `elapsed_years` true tropical solar years *before* birth (see §4). Everything else cascades forward from the anchor.

## 4. "True tropical solar years": the year convention (the heart of this engine)

JHora's screenshot setting is **"Using true tropical solar years"**. This is **not** a fixed-day constant. A dasha boundary at cumulative time `T` years from the anchor is the instant the **true / geometric tropical Sun** has advanced exactly `T × 360°` of tropical longitude from its longitude at the anchor.

Because the Sun's apparent speed varies over the year (faster near perihelion in early January, slower near aphelion in early July), each "solar year" has a slightly different length. That variation is the whole point of *true* tropical solar years, and it is why a single constant cannot reproduce JHora's table.

**Sun computation (locked):**

```
SUN_CALC_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_TRUEPOS
```

- `FLG_TRUEPOS` — true/geometric position, matching the ephemeris engine's locked Drik convention (no aberration). Verified against the fixture: with `FLG_TRUEPOS` every boundary's Sun longitude equals `anchor + T×360°` to ≲0.5″; the apparent (non-TRUEPOS) Sun carries a small systematic offset.
- **No `FLG_SIDEREAL`** — longitudes are **tropical**. The sidereal KP-Newcomb ayanamsa used everywhere else is deliberately *not* applied here; "tropical solar years" means tropical Sun.
- The same Swiss `.se1` files (`SE_EPHE_PATH`) as the ephemeris engine. On a Moshier fallback the numbers drift slightly; the parity tests therefore guard on `ephemeris_files_ok()` and skip loudly, mirroring the KP/significator gates.

**Boundary solver.** Each boundary is found by Newton's method on the Julian day: seed `jd ≈ anchor_jd + (T × 360 / 360) × MEAN_TROPICAL_YEAR_DAYS`, then iterate `jd -= signed_residual / sun_speed` until the tropical Sun longitude equals `anchor_lon + T×360°` (mod 360). The seed lands within ~2 days of the target, so the mod-360 residual never crosses a revolution and convergence is unambiguous.

### The exact constant

```
MEAN_TROPICAL_YEAR_DAYS = 365.2425   # days
```

This is the **mean** tropical year. It is used **only** to seed the Sun-transit solver and as a documented reference value. **It is never used as a period length.** The actual period lengths come from real Sun transits. For reference, the per-mahadasha implied year length across the User 1 fixture ranges from **365.2415** (Moon MD) to **365.2451** (Mars MD) days, averaging **365.24278** over the full cycle — a spread of ~5 min/yr that no fixed constant can absorb. The astronomical mean tropical year (≈365.24219 days) and the Gregorian mean (365.2425) are both within this band; we lock the Gregorian value as the seed because it is exact, standard, and closest to the cycle mean.

> **Supersedes the D002 placeholder.** D002 / AGENTS.md §4 / PROJECT_CONTEXT §7 record "year = 365.25 days" as the original dasha-year placeholder. The founder's JHora export uses true tropical solar years, not 365.25; D027 refines D002's dasha-year accordingly. 365.25 (Julian) is off by ~60h at PD level on this chart and must not be used.

## 5. MD / AD / PD proportional nesting

Antardashas subdivide their mahadasha; pratyantardashas subdivide their antardasha — both in proportion to the sub-lord's Vimshottari years, and both starting with the **parent lord** then proceeding in Vimshottari order:

```
MD span (years) = MD_years
AD span (years) = MD_years * AD_years / 120
PD span (years) = AD_span_years * PD_years / 120
              = MD_years * AD_years * PD_years / (120 * 120)
```

- A mahadasha's antardashas run in order `vimshottari_order_from(MD_lord)`; the first antardasha is the MD lord's own.
- An antardasha's pratyantardashas run in order `vimshottari_order_from(AD_lord)`; the first is the AD lord's own.
- A full timeline is **9 MD × 9 AD × 9 PD = 9 / 81 / 729** periods spanning the 120-year cycle from the anchor.

Spans are measured as **cumulative years from the anchor** and converted to instants by the §4 transit solver. The end of each period uses the identical cumulative value as the start of the next, so:

- **Continuity** — `period.end == next_period.start` exactly (same cumulative float → same solved instant).
- **Exact nesting** — every AD lies inside its MD and tiles it (`AD[0].start == MD.start`, `AD[-1].end == MD.end`); every PD lies inside its AD and tiles it.

## 6. Boundary rule: start-inclusive, end-exclusive

The same half-open convention as the nakshatra, KP, and house engines:

- A period owns `[start, end)`. At an **exact boundary timestamp the new (next) period starts**.
- `current_stack(t)` returns the (MD, AD, PD) whose `start ≤ t < end`. Querying exactly at an internal boundary returns the new period; one microsecond earlier returns the old one.
- Example (User 1): the Moon/Ketu Mars→Rahu boundary is JHora `2026-06-17 11:09:11`. The pratyantardasha **at** that exact instant is **Rahu** (end-exclusive: Mars has ended, Rahu has begun).

## 7. Timezone convention

- The transit math runs on a **continuous time scale** (Julian Day / UTC). Boundaries are then **rendered in the birth timezone** for display and fixture comparison.
- The User 1 fixture is **Asia/Kolkata**; all expected timestamps are Asia/Kolkata local civil time, to the second, exactly as JHora displays them. India observes no DST, so the local↔continuous mapping is a constant +05:30 and is exact.
- For zones with DST, the continuous scale is the defined convention (dasha spans are physical durations; the single local↔UTC conversion happens at the engine boundary via `zoneinfo`, `fold=0` for ambiguous local times, consistent with the ephemeris engine and D012(e)). `compute_dasha` requires a **timezone-aware** birth datetime and renders output in that zone.

## 8. JHora User 1 fixture (the judge)

```
tests/fixtures/jhora/dasha_expected.json
```

- **Birth:** 1998-08-14 06:45:00, Kolkata, India (22.5725, 88.363889), Asia/Kolkata.
- **Moon nakshatra:** Bharani; **nakshatra lord:** Venus → **birth mahadasha: Venus**.
- **Birth stack:** Venus / Moon / Venus.
- Full 9-mahadasha ladder (1992→2112), the Venus and Moon antardasha sets, the Venus/Moon and Moon/Ketu pratyantardasha sets, and three `current_stack` cases (midnight, noon, exact boundary on 2026-06-17).
- Expected values come from JHora and are the judge (AGENTS.md Rule 8). The engine conforms to them; no expected value is ever edited to match code.

### Tolerance and how the PD tests prove the convention

```
tolerance = 6 hours (21600 s) for every MD / AD / PD start and end
```

- The engine reproduces **every** fixture row within **~3.8 hours** on this chart. The residual is the **irreducible anchor offset**: our Swiss-ephemeris Moon differs from the Moon JHora used by ~**1 arc-second**, which shifts the whole back-projected ladder by ~3.5 h (and the §4 transit residual adds ≲0.3 h by 2026). This is well inside the founder's operational ±1-day dasha standard (PROJECT_CONTEXT §7) and inside the 6 h gate.
- A **fixed-constant-year** model — 365.25, 365.24219, or 365.2425 — anchored from the same Moon balance is off by **54–60 hours** at the deep 2026 pratyantardashas and **fails** the 6 h tolerance. The PD-level parity tests, plus an explicit constant-model-fails test, therefore **prove** that the true-tropical-solar (Sun-transit) convention is necessary: no constant reproduces JHora's table, and the `current_stack` noon case (Moon/Ketu/**Rahu**) only resolves correctly under the transit model.

## 9. Engine API (internal)

`backend/app/engines/dasha_engine.py`, pure functions plus frozen dataclasses, no DB/HTTP, no import of the deprecated `chart_engine.py`:

```
VIMSHOTTARI_ORDER, DASHA_YEARS, TOTAL_DASHA_YEARS, NAKSHATRA_SPAN_DEG,
MEAN_TROPICAL_YEAR_DAYS, SUN_CALC_FLAGS              # locked constants
vimshottari_order_from(lord) -> list[str]
birth_balance(moon_nakshatra_lord, moon_degree_in_nakshatra) -> (lord, years_remaining)
compute_dasha(*, moon_nakshatra_lord, moon_degree_in_nakshatra, birth) -> DashaTimeline
compute_dasha_from_chart(chart) -> DashaTimeline    # reads the Moon block + birth; read-only
DashaPeriod(level, lords, start, end)               # .lord, .contains(t)
DashaTimeline(...)                                   # .current_stack(t), .current_lords(t)
```

`compute_dasha_from_chart` reads only `planets[Moon].nakshatra.{lord, degree_in_nakshatra}` and `birth.{datetime_local, timezone}`. The chart payload is **read-only**: the engine mutates nothing and populates no public field.

## 10. Required test coverage

`tests/test_dasha_engine.py` asserts: (1) Vimshottari order and rotation; (2) the 120-year cycle (sum, 9 MD, full-cycle span); (3) birth MD lord = Moon nakshatra lord; (4) birth stack = Venus/Moon/Venus; (5/6/7) MD/AD/PD dates within the 6 h tolerance of JHora; (8) `current_stack` at midnight / noon / exact boundary; (9) continuity (`end == next.start`); (10) ADs tile their MD; (11) PDs tile their AD; (12) the engine does not mutate the input chart; (13) the public chart payload leaves `dashas` null. Plus: the locked convention constants, the fixture's non-constant year length, and the constant-model-fails proof. Parity tests skip loudly without `.se1` files.

## 11. Future TODOs (out of scope for this task)

- **Sookshma (5th level)** and Prana (6th) sub-periods — extend the same nesting/transit machinery one or two levels deeper; add JHora sookshma fixtures.
- **User 2 (Mumbai) and User 5 (Siliguri) fixtures** — add their JHora dasha exports to `dasha_expected.json` and parametrize the parity tests, matching the significator fixture's three-chart coverage. Confirms the ~3.8 h residual scales only with each chart's Moon-vs-JHora arc-second difference.
- **Node-aware prediction integration** — wire the timeline into the career predictor *after* node agency v2 (D026: node agency precedes career prediction). The active MD/AD/PD lords become dasha inputs to scoring/timing; only then is a founder decision on lifting D023 (public dasha exposure) revisited.
- **Public exposure** — if/when D023 is lifted, map `DashaTimeline` onto the existing reserved `DashaBlock` shape (`birth_balance`, `current`, `upcoming_md_ad ≤ 5`, `upcoming_pd ≤ 30`), dated to the day, in a schema-versioned PR. The reserved shape already exists in `schemas/chart.json`; adopting it later is additive, not a rename.
