# KP significators

The source of truth for the internal KP significator engine
(`backend/app/engines/significator_engine.py`). Two layers live here:

1. the **node-blind base A/B/C/D ladder** (D025), and
2. **node agency v2** (D028), a separate node-aware layer built on top of it.

Both layers are **internal only**. They return plain Python objects, read the
chart payload read-only, and populate **no** public chart field. The reserved
fields `houses[].significators`, `planets[].significator_of_houses`, and
`planets[].significator_levels` stay unpopulated under **D023**, the chart router
does not call either layer, and nothing here bumps `schema_version` (still `1.2`)
or `chart_engine_version` (still `1.4.0`).

---

## 1. Node-blind base ladder (D025, unchanged baseline)

`compute_house_significator_ladders(planets, houses)` returns
`{house: {"A", "B", "C", "D"}}`, house-centric:

| Level | House-centric meaning |
|-------|-----------------------|
| **A** | planets whose KP **star lord** is one of the house's **direct occupants** |
| **B** | the **direct occupants** of the house |
| **C** | planets whose KP **star lord** is the **house owner** (`cusp_sign_lord`) |
| **D** | the **house owner** (`cusp_sign_lord`) |

Sources: owner = `houses[].cusp_sign_lord`; occupants = `houses[].occupants`
(JHora bhava spans, D024); star lord = `planets[].kp.star_lord`. Scope: the 9
classical planets only; outer planets, Lagna, and cusps are ignored. In the base
ladder **Rahu/Ketu are plain names** — used for star-lord matching and as
possible occupants, with **no** node agency. This baseline is preserved
byte-for-byte and remains the T4.1-fixture judge
(`tests/fixtures/jhora/t41_significator_ladders_expected.json`).

### Planet-centric transpose

`compute_planet_significators(planets, houses)` returns
`{planet: [sorted houses]}`. A planet signifies a house iff it appears at any of
A/B/C/D for that house. Equivalently a planet signifies the houses occupied by
its star lord (A), occupied by itself (B), owned by its star lord (C), and owned
by itself (D). This transpose is the **baseline** the node-aware layer extends.

---

## 2. Node agency v2 (D028, new — node-aware layer)

In KP, Rahu and Ketu own no sign; they act as **agents** that represent other
planets. `compute_node_aware_significators(planets, houses)` layers this on top
of the node-blind transpose and returns a `NodeAwareSignificators` with:

- `planet_to_houses` — node-aware planet → sorted houses (9 planets);
- `node_blind_planet_to_houses` — the D025 baseline, for traceability;
- `house_to_planets` — the inverse of `planet_to_houses` (houses 1..12);
- `node_agency` — per-node agent resolution (`NodeAgency`).

### Agent resolution — three deterministic channels

For each node, `compute_node_agency(planets)` resolves the classical planets it
represents:

| Channel | Rule | Field read |
|---------|------|-----------|
| **Sign lord** | the dispositor of the node's sign | `planets[].sign_lord` |
| **Conjunction** | classical planets in the **same sign** (rashi) as the node | `planets[].sign` |
| **Aspect** | classical planets casting **Parashari graha drishti** onto the node's sign | `planets[].sign` |

Graha drishti is sign-based and 1-indexed inclusive: every planet aspects the
**7th** sign; **Mars** also the **4th/8th**; **Jupiter** the **5th/9th**;
**Saturn** the **3rd/10th**. The node's **star lord is already represented by the
base ladder** (its A/C-level houses), so it is not added again.

`agents` is the canonical-ordered union of the three channels. **Only the seven
classical planets are ever agents** — a node never borrows from another node
(the nodes' mutual 7th-sign aspect is deliberately ignored), which keeps the
computation free of node-to-node feedback.

### Bidirectional, single-pass

- the **node gains** the full **node-blind** significations of each agent, and
- reciprocally **each agent gains the house the node occupies** (`house_occupied`;
  nodes own no house).

Borrowing reads **node-blind** significations only, so the pass is single-step,
order-independent, and bounded (no transitive chaining). The seven classical
planets' baseline is otherwise unchanged.

---

## 3. Worked example — User 1 Kolkata (1998-08-14 06:45, Kolkata)

Node geometry from the live chart:

| Node | Sign | Sign lord | House | Star lord | Agents (channel) |
|------|------|-----------|-------|-----------|------------------|
| Rahu | Leo | Sun | 1 | Ketu | **Sun** (sign lord) |
| Ketu | Aquarius | Saturn | 7 | Rahu | **Saturn** (sign lord), **Mars** (aspect: Mars's 8th-sign drishti Cancer→Aquarius) |

| Planet | Node-blind houses | Node-aware houses | Node-agency effect |
|--------|-------------------|-------------------|--------------------|
| Sun | 1, 2, 11, 12 | 1, 2, 11, 12 | agent of Rahu; gains Rahu's house 1 (already had it) |
| Moon | 3, 9, 10, 12 | 3, 9, 10, 12 | — |
| Mars | 4, 5, 8, 9, 11 | 4, 5, **7**, 8, 9, 11 | agent of Ketu; **gains Ketu's house 7** |
| Mercury | 2, 11, 12 | 2, 11, 12 | — |
| Jupiter | 5, 8 | 5, 8 | — |
| Venus | 3, 6, 7, 9, 10, 12 | 3, 6, 7, 9, 10, 12 | — |
| Saturn | 6, 7, 9 | 6, 7, 9 | agent of Ketu; gains house 7 (already had it) |
| Rahu | 1, 7 | 1, 2, 7, 11, 12 | borrows Sun's node-blind houses |
| Ketu | 1, 7 | 1, 4, 5, 6, 7, 8, 9, 11 | borrows Saturn's + Mars's node-blind houses |

---

## 4. AstroSage comparison — external reference only

`compare_significators_to_reference(result, reference)` compares the node-aware
output against an external table and reports per-planet matches plus
`only_ours` / `only_reference` differences. The bundled reference is
`tests/fixtures/external/astrosage_user1_significators.json`.

> **AstroSage is an external compatibility reference ONLY — not the judge.**
> It is **not** JHora and **not** a founder-hand-worked fixture, so it carries no
> authority under AGENTS.md Rule 8. It is marked `external_reference_only: true`,
> `is_judge: false`. Differences are reported, never tuned away. We do **not**
> match it byte-for-byte and do **not** claim parity with it.

Result for User 1 Kolkata: **3 of 9 planets match exactly without any tuning —
Sun, Mercury, Mars** (Mars matches only because node agency adds house 7). The
other six differ:

- **Moon** (+11), **Jupiter** (+7), **Venus** (8,11 vs 9,12), **Saturn** (8 vs 9)
  — these track to AstroSage's different house occupation (its Saturn/Venus
  appear to sit in different bhavas), i.e. a **house-system/convention**
  difference, not an agency-rule difference.
- **Rahu** and **Ketu** diverge the most: AstroSage represents **both** nodes
  against houses **{6, 12}**, while our JHora-bhava occupation (D024) places Rahu
  in house 1 and Ketu in house 7. The node divergence is therefore rooted in a
  **house-placement difference**, reinforcing that AstroSage is reference-only.

### JHora final significator table is UNAVAILABLE

The JHora final 4-level (nakshatra / sub / prati-sub / sookshma / praana)
significator table — including JHora's reverse "Planet Bodies occupying this
planet" tables — is **not available** for this chart. Until it exists, **no
node-aware output may claim JHora significator parity.** The node-blind base
ladder remains validated against the T4.1 hand-worked fixture; the node-aware
layer is validated against its own deterministic rules (per-channel unit tests +
the worked example above) and is compared — not judged — against AstroSage.

---

## 5. Guarantees (tested)

- the node-blind base ladder fixture (36 rows) still passes unchanged;
- node-aware output is a **separate object**; the chart payload is **not
  mutated** and no public significator field is populated;
- the AstroSage fixture is stored as `external_reference_only` / `is_judge:false`
  and is self-consistent (its two directions invert);
- the comparison report surfaces matches **and** differences honestly;
- the public chart contract is unchanged: `schema_version` stays `1.2`,
  `chart_engine_version` stays `1.4.0`, the router output is untouched.

See `tests/test_significator_engine.py` and DECISIONS.md **D028** (and D023,
D024, D025, D026).
