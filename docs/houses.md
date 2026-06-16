# House Occupation Specification (cusp spans)
**Spec doc for the house_engine. Owner task: T4.3 (`agent/codex/house-engine`). Read order: docs/PROJECT_CONTEXT.md → AGENTS.md → this doc, before code.**
**Created: 2026-06-16 (contract sync). Source of truth for how a planet is assigned to a house.**

---

## 1. The rule (authoritative, never paraphrase loosely)

House membership is assigned by **cusp spans**, never by sign.

- A house spans from its own cusp to the next cusp:
  **House H = [cusp_H, cusp_{H+1})**
- The cusp is the **start** of the house, not the midpoint.
- Wraparound across 360° / 0° Aries is handled with modular arithmetic. A planet is in house `H` iff:

  ```
  (planet_long - cusp_H) % 360  <  (cusp_{H+1} - cusp_H) % 360
  ```

- A planet exactly **on a cusp** belongs to the house **beginning** at that cusp (lower bound inclusive, upper bound exclusive — same half-open convention the nakshatra and KP engines use).
- **Never** assign a planet to a house by zodiac sign or whole-sign logic. The sign a planet sits in is irrelevant to house membership under Placidus.

For house 12, `cusp_{H+1}` is `cusp_1` (wraps back to the ascendant cusp); the modular form above already covers this.

## 2. Why cusp spans, not signs

Under Placidus (our locked house system, D002), house cusps are unequal and do not line up with sign boundaries. A planet can sit in Virgo while the 10th cusp falls at 8° Virgo and the 11th at 5° Libra — so a Virgo planet at 3° Virgo is in the 9th house, not the 10th. Whole-sign/sign-based assignment would silently misplace it. KP prediction depends on correct house occupancy, so this rule is load-bearing.

## 3. What the engine fills

The house_engine populates two already-existing v1.2 schema fields (no schema bump):

- `planets[].house_occupied` — the integer house `1..12` the planet falls in, by cusp span.
- `houses[].occupants` — the list of `PlanetName` whose `house_occupied` equals that house.

These are mutually consistent: `planet.house_occupied == h` iff `planet.name in houses[h-1].occupants`.

## 4. Out of scope for the house_engine

- **No significators.** `houses[].significators`, `planets[].significator_of_houses`, and `planets[].significator_levels` are RESERVED and NOT populated in v1.2 (D023).
- **No KP block changes.** `planets[].kp` / `houses[].kp` are owned by the KP integration; the house_engine does not touch them.
- **No schema bump.** `house_occupied` and `occupants` already exist in the v1.2 contract.
- **No prediction logic.**

## 5. Required test coverage

- Interior case: a planet comfortably inside a house span maps to that house.
- Wraparound: a house whose span crosses 0° Aries (e.g. cusp_H near 350°, cusp_{H+1} near 10°) correctly contains planets on both sides of 0°.
- Planet exactly on a cusp (within the 0.01° cusp tolerance): assigned to the house that STARTS at that cusp, not the previous one.
- All 9 planets assigned exactly once; `houses[].occupants` is the inverse of `planets[].house_occupied`.
- Never sign-based: a fixture where sign membership and cusp-span membership disagree must follow cusp spans.
