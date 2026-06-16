# House Occupation Specification (JHora bhava spans)
**Spec doc for the house_engine. Read order: docs/PROJECT_CONTEXT.md → AGENTS.md → this doc, before code.**
**Created: 2026-06-16 (contract sync). Corrected 2026-06-16 to JHora bhava-span parity (D024). Source of truth for how a planet is assigned to a house.**

---

## 1. The rule (authoritative, never paraphrase loosely)

Public house membership is assigned by **JHora bhava spans**, never by sign and
**never by the cusp-to-next-cusp rule** that an earlier draft of this doc used.

A house is the span **around** its cusp. The cusp sits **inside** the house, not
at its start boundary:

- `start_H = midpoint(prev_cusp, cusp_H)`
- `end_H   = midpoint(cusp_H, next_cusp)`
- **House H = [start_H, end_H)**

Boundary formulas (modular across 360° / 0° Aries):

```
start_H = (cusp_H - ((cusp_H - prev_cusp) % 360) / 2) % 360
end_H   = (cusp_H + ((next_cusp - cusp_H) % 360) / 2) % 360
```

- `prev_cusp` is `cusp_{H-1}` (for house 1 this wraps to `cusp_12`); `next_cusp`
  is `cusp_{H+1}` (for house 12 this wraps to `cusp_1`).
- Because `end_H == start_{H+1} == midpoint(cusp_H, cusp_{H+1})`, the twelve
  spans tile the circle exactly: no gap, no overlap, every planet in exactly one
  house.
- **Start boundary is inclusive; end boundary is exclusive** — the same
  half-open convention the nakshatra and KP engines use. A planet exactly on
  `start_H` is in house `H`; a planet exactly on `end_H` is in house `H+1`.
- **Never** assign a planet to a house by zodiac sign or whole-sign logic. The
  sign a planet sits in is irrelevant to house membership under Placidus.

### Worked evidence (User 1 Kolkata, 1998-08-14 06:45)

JHora's "House Start / Cusp / End / Planets in it" table lists the 1st house as
Start = 2 Leo 50′, Cusp = 17 Leo 25′, End = 1 Virgo 28′, **Planets in it = As,
Rahu**. Rahu sits before the 1st cusp but after the 1st-house start, so it lands
in house 1 — not house 12. The cusp-to-next-cusp rule put Rahu in house 12 and
failed JHora parity; the bhava-span rule above reproduces JHora's column.

## 2. The cusp-to-next-cusp rule is NOT used for occupation

The earlier `House H = [cusp_H, cusp_{H+1})` rule (cusp as the start boundary)
is **superseded for public occupation** (D024). It does **not** decide
`house_occupied` or `occupants`.

It remains valid only for **KP cusp star/sub-lord lookup**: `houses[].kp.star_lord`
and `houses[].kp.sub_lord` are computed from the **cusp longitude** itself, owned
by the KP engine, and are unchanged by this doc. Cusp longitude → KP sub lord is a
point lookup, not a span-membership question.

## 3. Why bhava spans, not signs, and not cusp-to-next-cusp

Under Placidus (our locked house system, D002), cusps are unequal and do not line
up with sign boundaries, so whole-sign assignment silently misplaces planets. The
cusp is the **most sensitive point** of a house, not its edge; JHora therefore
centres each house on its cusp and bounds it by the midpoints to the neighbouring
cusps. KP prediction depends on matching JHora's occupancy, so this rule is
load-bearing.

## 4. What the engine fills

The house_engine populates two already-existing v1.2 schema fields (no schema bump):

- `planets[].house_occupied` — the integer house `1..12` the planet falls in, by
  bhava span.
- `houses[].occupants` — the list of `PlanetName` whose `house_occupied` equals
  that house.

These are mutually consistent: `planet.house_occupied == h` iff
`planet.name in houses[h-1].occupants`.

## 5. Out of scope for the house_engine

- **No significators.** `houses[].significators`, `planets[].significator_of_houses`,
  and `planets[].significator_levels` are RESERVED and NOT populated in v1.2 (D023).
- **No KP block changes.** `planets[].kp` / `houses[].kp` are owned by the KP
  integration; the house_engine does not touch them and does not change the
  cusp-longitude KP lookup.
- **No schema bump.** `house_occupied` and `occupants` already exist in the v1.2
  contract.
- **No prediction logic.**

## 6. Required test coverage

- Interior case: a planet comfortably inside a bhava span (e.g. on the cusp itself)
  maps to that house.
- Wraparound: a house whose span crosses 0° Aries correctly contains planets on
  both sides of 0°.
- Start boundary inclusive: a planet exactly on `start_H` is in house `H`.
- End boundary exclusive: a planet exactly on `end_H` is in house `H+1`.
- Cusp is interior: a planet before the cusp but after the bhava start still
  belongs to that house (the JHora insight; mirrors User 1 Kolkata Rahu).
- All 9 planets assigned exactly once; `houses[].occupants` is the inverse of
  `planets[].house_occupied`.
- User 1 Kolkata regression matches JHora's "Planets in it" column:
  Rahu→1, Ketu→7, Jupiter→8, Moon→9, Saturn→9, Mars→11, Sun→12, Mercury→12,
  Venus→12.
