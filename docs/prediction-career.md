# Career prediction v1 (internal)

Source of truth for `backend/app/engines/prediction_career_engine.py` (D029).

This is the **first prediction vertical**. It is an **internal, deterministic,
evidence-first** engine. It is **not** an LLM call, **not** wired into the public
chart router, and exposes **nothing**: `chart.dashas` stays `null`, the reserved
significator fields stay empty (D023), and no schema/engine version moves
(`schema_version` `1.2`, `chart_engine_version` `1.4.0`).

```
compute_career_prediction(chart, *, as_of: datetime) -> dict
```

`as_of` must be timezone-aware (it indexes the dasha timeline). The input chart
is read-only.

---

## Model — promise + timing

KP separates whether a thing is *promised* by the chart from *when* it activates.

### Promise (chart-level, time-independent)

For each career house the engine reads its **cusp sub-lord** (`houses[].kp.sub_lord`)
and the houses that sub-lord signifies in the **node-aware** significator engine
(D028). A career house is "promised" when its cusp sub-lord signifies any career
house. The **10th cusp sub-lord** is the headline (nature/source of profession).

| Career house | Meaning |
|---|---|
| 2 | income / resources |
| 6 | job / service / competition |
| 10 | profession / status |
| 11 | gains / network |

### Timing (time-dependent, via `as_of`)

The current Vimshottari **mahadasha / antardasha / pratyantardasha** lords
(internal dasha engine, D027) and the houses they signify. A career house is
**activated** when a current dasha lord signifies it. Supporting houses
(1 self, 3 effort/skills, 5 intelligence/education, 9 fortune/mentors) and
challenging houses (8 instability/breaks, 12 loss/foreign/remote/isolation) are
classified the same way.

### Evidence

Every factor cites a real planet and the houses it signifies — taken **verbatim**
from the node-aware significator engine (a test asserts `evidence[].signifies ==
significators.planet_to_houses[evidence[].source]`, so nothing is fabricated).
`supporting_factors` are evidence items with career-house hits; `blocking_factors`
are items with 8/12 hits.

### Confidence (transparent, capped)

A coarse, documented heuristic: `career_signal` = number of distinct career houses
the current stack activates; `challenge_signal` = distinct 8/12 houses hit. Raw
tier is `high` (≥3 career, ≤1 challenge) / `medium` (≥2 career) / `low`. **v1 caps
the published confidence at `medium`** — the engine never claims `high` while the
significator foundation is not JHora-validated. `confidence_basis` exposes the raw
counts and the cap so the tier is auditable, not a black box.

### Output shape

`version`, `as_of`, `summary` (templated, hedged), `promise`,
`career_house_activation` (per career house: activated? by which lords? promised?),
`current_dasha_stack` (lords + AD/PD date windows), `dasha_support` (per level),
`supporting_factors`, `blocking_factors`, `career_themes`, `timing_interpretation`
(dasha-period level, no transit precision), `confidence`, `confidence_basis`,
`evidence`, `caveat`.

---

## Worked example — User 1 Kolkata, as of 2026-06-17 12:00 IST

- **Promise.** 10th cusp sub-lord **Saturn** → signifies [6, 7, 9] → hits career
  house **6**, a *salaried-service / employment* signature. 11th cusp sub-lord
  **Sun** → [1, 2, 11, 12] → hits 2 and 11 (income + gains). 2nd cusp sub-lord
  **Jupiter** → [5, 8] → no career hit.
- **Timing.** Current stack **Moon ▸ Ketu ▸ Rahu**. Moon signifies 10
  (profession) + 12; Ketu signifies 6, 11 + 8; Rahu signifies 2, 11 + 12. All
  four career houses {2, 6, 10, 11} are activated, with 8/12 noise.
- **Confidence:** `medium` (career_signal 4, challenge_signal 2 → raw `high`
  capped to `medium`).
- **Summary (verbatim, templated — no LLM):**

  > As of 2026-06-17, the active Vimshottari stack is Moon (mahadasha) > Ketu
  > (antardasha) > Rahu (pratyantardasha). This may activate career houses
  > 2, 6, 10, 11. The 10th-cusp sub-lord Saturn signifies houses [6, 7, 9], which
  > suggests salaried service alongside some independent or partnership work.
  > Activation of house(s) 8, 12 indicates instability/sudden-change/breaks,
  > loss/foreign/remote/isolation/expenses, so supportive periods may also carry
  > change, expense, or remote/behind-the-scenes work. This is reflective
  > guidance, not a guarantee of any specific outcome.

The pratyantardasha flips **Mars → Rahu** exactly on 2026-06-17, so the same chart
at midnight activates {6, 10, 11} (no house 2) — timing genuinely depends on
`as_of`.

---

## Validation status — read this before trusting numbers

> **v1 is a deterministic evidence *scaffold*, not a validated predictor.**

- The significator foundation is **AstroSage-compared only (3/9 exact), not
  JHora-validated** (D028). The JHora final 4-level significator table is
  unavailable. Career output inherits that gap.
- The node-agency model (D028) is one KP school; node-driven career results are
  model-dependent.
- Timing is **dasha-period level only** — there is no transit engine in v1, so no
  day-level event dates.
- There is still **no JHora career oracle** — nothing asserts the prediction is
  astrologically *correct*. The career golden fixtures below lock *behaviour* and
  *safety*, not correctness.

**Before any tuning or user exposure:** the JHora final significator table lands
(D026 gate) so correctness can be validated and the `medium` cap revisited. Public
exposure would be a **separate** `POST /predict/career` endpoint, never
`/chart/generate`.

---

## Founder golden fixtures — NOT JHora oracle fixtures

`tests/fixtures/career/career_*.json` (consumed by
`tests/test_prediction_career_golden.py`) are **founder golden fixtures**. Keep the
distinction sharp:

| | JHora **oracle** fixture | Founder **golden** fixture |
|---|---|---|
| Examples | `tests/fixtures/jhora/*`, `tests/fixtures/nakshatra/boundaries_330.json` | `tests/fixtures/career/career_*.json` |
| Source of values | Jagannatha Hora export | the engine's **own** deterministic output |
| Role | **judge** of astrological correctness; the engine conforms to it (AGENTS.md Rule 8) | **anchor** of documented v1 *behaviour* + *safety*, reviewed by the founder for *reasonableness* |
| Asserts correctness? | yes | **no** — there is no JHora career oracle yet |

The three fixtures cover one archetype each, so the documented tier band is exercised
end to end:

| Fixture | Profile | Chart ref | Career / challenge signal | Raw tier → published |
|---|---|---|---|---|
| `career_supportive_v1` | clearly supportive | `fixture_02_us_dst` | 3 / 1 | `high` → **`medium`** (cap in action) |
| `career_mixed_change_v1` | mixed / change | `fixture_04_pre1990` | 4 / 2 (houses 8 + 12) | `medium` → **`medium`** |
| `career_weak_no_signal_v1` | weak / no clear signal | `fixture_03_midnight` | 1 / 1 | `low` → **`low`** |

Each fixture records the founder-reviewable promise + timing reading (current
MD/AD/PD, the 10th and 2/6/10/11 cusp sub-lords, promise-side and timing-side career
houses, challenge houses, expected tier band and themes) plus an explicit
`must_not_claim` list and `safe_language` contract, and a `founder_review` block
(`status: pending` until the founder signs off).

`test_prediction_career_golden.py` asserts the **safety contract** the engine must
never break, independent of any astrology being "right": no invented planets (9
classical grahas only, never Pluto/Neptune/Uranus), no invented houses (1..12), no
invented dates (only `as_of` + the dasha-derived AD/PD windows — no day-level event
dates), no unsafe certainty language, confidence **capped at `medium`** (never
`high`), outputs **internal-only** (chart not mutated, `chart.dashas` stays `null`,
reserved significator fields stay empty), and the per-profile tier/theme constraints.

Charts are rebuilt from the **golden (JHora-validated) longitudes/cusps** of the
referenced `tests/fixtures/charts/*` fixtures, so the build is Swiss-independent;
each `as_of` sits well inside its MD/AD/PD periods so the active stack is identical
under Swiss or Moshier Sun timing, and the tests never assert exact boundary dates.

`test_prediction_career_engine.py` continues to assert the lower-level deterministic
mechanics (shape, evidence integrity, timing-depends-on-`as_of`, no mutation, public
API unchanged).

See `tests/test_prediction_career_golden.py`,
`tests/test_prediction_career_engine.py`, DECISIONS.md **D029** (and D023, D026,
D027, D028).
