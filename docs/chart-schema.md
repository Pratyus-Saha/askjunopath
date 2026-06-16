# Chart Schema Specification: chart.json (current: v1.2)
**Files:** `schemas/chart.json` (the contract) + `backend/app/schemas/models.py` (pydantic v2 enforcement)
**Spec version history:** v1.0 froze Day 1 (D001); v1.1 added optional `metadata` (D021); **v1.2 is current** — adds required `kp` blocks on `planets[]`/`houses[]` and removes the legacy `houses[].cusp_*` KP fields (D022). After each freeze, changes are additive only and bump the version (Rule 5).
**Owner tool:** Codex, branch `codex/schemas` only. Never touches main directly. Claude Pro attacks this spec before each freeze; you patch, then tag.
**Source:** Master plan Sections 5, 11, 13, 14, 19, 20; playbook Day 1 and Rule 5.

> **v1.2 CONTRACT SYNC (2026-06-16).** This doc was reconciled with the shipped schema v1.2. The body below still carries the original v1.0 narrative for history; where it conflicts with the points here, **these points win**:
> - `schema_version` is `"1.2"`. Engine/cache output carries `metadata.engine_version = "1.4.0"`.
> - Public KP shape is exactly `planets[].kp.{star_lord, sub_lord}` and `houses[].kp.{star_lord, sub_lord}`. There is **no** `sub_sub_lord` in public output.
> - The legacy public house fields `houses[].cusp_star_lord`, `houses[].cusp_sub_lord`, `houses[].cusp_sub_sub_lord` are **REMOVED** from the contract (deleted in schema v1.2; see HANDOFF `remove-legacy-cusp-kp-fields`). Where they still appear below they are marked REMOVED and kept only as historical context — they are NOT the current public contract.
> - `planets[].house_occupied` and `houses[].occupants` already exist in v1.2 (present since v1.0) and are filled by the house_engine via CUSP SPANS (`docs/houses.md`). Populating them is NOT a schema bump.
> - Significator fields (`houses[].significators`, `planets[].significator_of_houses`, `planets[].significator_levels`) exist in the model/schema but are **RESERVED / NOT POPULATED in v1.2**, pending decision D023. No agent populates them in public output yet.

---

## 1. Purpose and the Freeze Rule

One canonical `chart.json` object is computed once per birth input, stored in `charts.chart_data` (JSONB, Supabase), and passed to every downstream engine. Engines never recompute ephemeris values; they read this object. Every layer (engines, API, frontend fixtures, Gemini synthesis payload) consumes this single contract.

After v1.0 is tagged tonight:

- Field renames: forbidden. A casual rename on Day 6 breaks four layers at once.
- Field removals: forbidden.
- New fields: allowed, with a version bump (1.0 → 1.1) and updated models.
- `schema_version` is embedded in every stored chart so old charts can be migrated.

Pydantic models use `model_config = ConfigDict(extra="forbid")`. A typo'd field name from any AI agent fails loudly at the boundary instead of silently dropping data.

---

## 2. Ownership Map (who writes what, and when)

This table prevents agents from filling fields they do not own. Fields owned by later engines are `Optional[...] = None` (or empty lists/dicts) so a Day 1 chart validates with stubs and `scripts/e2e_check.py` can run from tonight.

| Block / field | Written by | Day |
|---|---|---|
| `birth.*`, `settings.*` | ephemeris_engine | 1 |
| `planets[].name/longitude/sign/sign_lord/sign_degree/retrograde/combust/speed_deg_per_day` | ephemeris_engine | 1 |
| `houses[].cusp_longitude/cusp_sign/cusp_sign_lord` + ascendant | ephemeris_engine | 1 |
| `planets[].nakshatra`, `houses[].cusp_nakshatra` | nakshatra_engine | 2 |
| `planets[].kp` (`star_lord`, `sub_lord`), `houses[].kp` (`star_lord`, `sub_lord`) | kp_engine | 3 — integrated into chart output in v1.2 (D022) |
| ~~`houses[].cusp_star_lord`, `houses[].cusp_sub_lord`, `houses[].cusp_sub_sub_lord`~~ | **REMOVED in v1.2** — replaced by `houses[].kp` | — |
| `planets[].house_occupied`, `houses[].occupants` | house_engine (CUSP SPANS, never by sign; `docs/houses.md`) | 4 — already in schema since v1.0, no bump to populate |
| `houses[].significators`, `planets[].significator_of_houses/significator_levels` | **RESERVED — not populated in v1.2 (D023)**; future owner kp_engine + house_engine | deferred |
| `dashas` | dasha_engine | 5 |
| `strengths` | strength_engine | 6 |
| `divisional` | divisional_engine | 6 |
| `transits` | transit_engine | 8 |
| `prediction_features` | feature builder + prediction_scoring | 7 to 9 |

---

## 3. Top-Level Shape

```json
{
  "schema_version": "1.2",
  "birth": {
    "datetime_local": "1994-03-21T14:35:00",
    "datetime_utc": "1994-03-21T09:05:00Z",
    "timezone": "Asia/Kolkata",
    "lat": 28.4595, "lon": 77.0266,
    "place_label": "Gurugram, India",
    "approximate_time": false,
    "julian_day_ut": 2449432.87847
  },
  "settings": {
    "ayanamsa": "KP_NEWCOMB",
    "ayanamsa_value_deg": 23.7261,
    "node_type": "TRUE",
    "house_system": "PLACIDUS",
    "zodiac": "SIDEREAL"
  },
  "ascendant": { "longitude": 98.2331, "sign": "Cancer", "sign_degree": 8.2331 },
  "planets": [],
  "houses": [],
  "dashas": null,
  "strengths": [],
  "divisional": { "d9": null, "d10": null },
  "transits": { "computed_at": null, "windows": [] },
  "prediction_features": { "career": null, "finance": null, "relationship": null }
}
```

Field constraints:

| Field | Type / constraint |
|---|---|
| `schema_version` | `Literal["1.2"]` (current; v1.0/v1.1 are superseded) |
| `birth.datetime_local` | ISO 8601 naive local datetime string |
| `birth.datetime_utc` | ISO 8601 UTC with `Z` suffix |
| `birth.timezone` | IANA zone string, required and non-empty. The API resolves it server-side from lat/lon when the client omits it (Section 20); by the time a chart object exists, timezone is always present. A chart with a missing timezone is invalid. |
| `birth.lat` | `float, ge=-66.0, le=66.0`. Placidus is undefined beyond this; the API rejects with 400 LAT_UNSUPPORTED before a chart is ever constructed, and the schema enforces it as a backstop. |
| `birth.lon` | `float, ge=-180.0, le=180.0` |
| `birth.approximate_time` | `bool`, required. Persists the birth-input toggle; softens cusp-dependent language downstream (Section 17). One of the five pre-freeze patches. |
| `birth.julian_day_ut` | `float, gt=0` |
| `settings.ayanamsa` | `Literal["KP_NEWCOMB"]` |
| `settings.node_type` | `Literal["TRUE"]` |
| `settings.house_system` | `Literal["PLACIDUS"]` |
| `settings.zodiac` | `Literal["SIDEREAL"]` |
| `settings.ayanamsa_value_deg` | `float, ge=20.0, le=30.0` (sanity band) |

Shared scalar conventions, used everywhere below:

- `PlanetName = Literal["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]`
- `SignName = Literal["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]`
- Any `longitude`: `float, ge=0, lt=360`, serialized to 4 decimals
- Any `sign_degree`: `float, ge=0, lt=30`
- Any house number: `int, ge=1, le=12`
- Dates inside dasha/transit objects: `YYYY-MM-DD` strings
- Pre-1950 births are valid input (one of the five pre-freeze scenarios); no schema change needed, but the ephemeris `.se1` file coverage must span the date, which `/health` and the ephemeris guard already verify.

---

## 4. Planet Object (one per Sun..Saturn, Rahu, Ketu; list length exactly 9, fixed order)

```json
{
  "name": "Saturn",
  "longitude": 322.4517,
  "sign": "Aquarius", "sign_lord": "Saturn",
  "sign_degree": 22.4517,
  "house_occupied": 10,
  "retrograde": false,
  "combust": false,
  "speed_deg_per_day": 0.0712,
  "nakshatra": { "name": "Purva Bhadrapada", "index": 25, "lord": "Jupiter",
                 "degree_in_nakshatra": 8.7184, "pada": 3,
                 "degree_in_pada": 2.0517, "navamsa_sign": "Libra" },
  "kp": { "star_lord": "Jupiter", "sub_lord": "Venus" },
  "significator_of_houses": [3, 6, 10, 11],
  "significator_levels": { "10": "A", "6": "B", "3": "C", "11": "D" }
}
```

Constraints beyond the shared conventions:

- `house_occupied`: `Optional[int 1..12] = None` until Day 4. Assigned via cusp spans only.
- `speed_deg_per_day`: `float` (negative when retrograde; no range clamp, the Moon exceeds 15°/day at perigee).
- `nakshatra`: `Optional[NakshatraBlock] = None` until Day 2.
  - `index`: `int, ge=1, le=27`, **1-based** (1 = Ashwini, 25 = Purva Bhadrapada, matching the example above). Day 2's engine consumes this convention; do not let it re-decide.
  - `pada`: `int, ge=1, le=4`
  - `degree_in_nakshatra`: `float, ge=0, lt=13.333334` (13°20')
  - `degree_in_pada`: `float, ge=0, lt=3.333334` (3°20')
  - `lord`: `PlanetName`; `navamsa_sign`: `SignName`
- `kp`: `KpBlock`, **required in v1.2**. Exactly two keys, `star_lord` and `sub_lord`, both `PlanetName`. (Earlier v1.0 drafts showed a third `sub_sub_lord`; it is NOT in the public contract — sub-sub lord stays internal to the lookup engine per D022.)
- `significator_of_houses`: `list[int 1..12]`, default `[]`, sorted ascending, no duplicates (validator). **RESERVED — not populated in public output in v1.2 (D023).**
- `significator_levels`: `dict[str, Literal["A","B","C","D"]]`, default `{}`. Keys are stringified house numbers and must be a subset of `significator_of_houses` (validator). **RESERVED — not populated in public output in v1.2 (D023).**

---

## 5. House Object (one per cusp, list length exactly 12, ordered 1 to 12)

```json
{
  "house": 10,
  "cusp_longitude": 158.2342,
  "cusp_sign": "Virgo", "cusp_sign_lord": "Mercury",
  "cusp_nakshatra": "Hasta",
  "kp": { "star_lord": "Moon", "sub_lord": "Venus" },
  "occupants": ["Saturn"],
  "significators": {
    "A_in_star_of_occupants": ["Mercury", "Ketu"],
    "B_occupants": ["Saturn"],
    "C_in_star_of_owner": ["Sun"],
    "D_owner": ["Mercury"]
  }
}
```

- `cusp_nakshatra`: name STRING or null. (`cusp_star_lord` was **REMOVED in v1.2**; the cusp star lord is now exposed as `houses[].kp.star_lord`.)
- ~~`cusp_sub_lord`, `cusp_sub_sub_lord`~~: **REMOVED in v1.2.** Public cusp KP is now `houses[].kp.{star_lord, sub_lord}`. The internal lookup engine may still compute a sub-sub lord, but it is not in the public contract (D022).
- `kp`: `KpBlock`, **required in v1.2**. Exactly `star_lord` and `sub_lord`, both `PlanetName`, copied from the internal KP lookup at the cusp longitude.
- `occupants`: `list[PlanetName]`, default `[]`, filled Day 4 via CUSP SPANS only (`docs/houses.md`). Already in the schema since v1.0; populating it is not a schema bump.
- `significators`: `Optional[SignificatorLadder] = None`. All four levels are `list[PlanetName]` with default `[]`. The A/B/C/D level names are part of the contract; the scorer and synthesis payload will read them once populated. **RESERVED — not populated in public output in v1.2 (D023).**

---

## 6. Dasha Object

```json
{
  "system": "VIMSHOTTARI",
  "birth_balance": { "lord": "Venus", "years_remaining": 11.42 },
  "current": {
    "mahadasha": { "lord": "Venus", "start": "2008-04-12", "end": "2028-04-12" },
    "antardasha": { "lord": "Saturn", "start": "2025-08-03", "end": "2028-04-12" },
    "pratyantardasha": { "lord": "Mercury", "start": "2026-05-21", "end": "2026-10-29" }
  },
  "upcoming_md_ad": [ { "md": "Venus", "ad": "Mercury", "start": "...", "end": "..." } ],
  "upcoming_pd": [ { "md": "Venus", "ad": "Saturn", "pd": "Ketu", "start": "...", "end": "..." } ]
}
```

- `system`: `Literal["VIMSHOTTARI"]`
- `birth_balance.years_remaining`: `float, ge=0, le=20` (Venus, the longest MD, is 20 years)
- Every period object: `lord/md/ad/pd` are `PlanetName`; `start` strictly before `end` (validator); dates stored to the day, never the month (PD periods can run 9 to 10 days, Section 9)
- `upcoming_md_ad`: max length 5
- `upcoming_pd`: max length 30 (the Day 5 pre-decided cut shrinks the populated count to 10; the schema cap stays 30 so the restore is non-breaking)

---

## 7. Strength Object (one per planet, list length 9 when populated)

```json
{
  "planet": "Saturn",
  "v1_score": 64,
  "components": { "dignity": 12, "house_placement": 6, "dig_bala": 0,
                  "retrograde": 0, "combustion": 0, "aspects_net": -4, "base": 50 },
  "tier": "MODERATE",
  "notes": ["own sign Aquarius", "aspected by Mars"],
  "derived": false
}
```

- `v1_score`: `int, ge=0, le=100`
- `components`: fixed keys exactly `dignity, house_placement, dig_bala, retrograde, combustion, aspects_net, base`, all `int`. `extra="forbid"` on this sub-model too; a new component in V2 is a version bump.
- `tier`: `Literal["STRONG","MODERATE","WEAK"]` (70+ / 45 to 69 / below 45, Section 10)
- `derived`: `bool`, default `false`; `true` for Rahu/Ketu (scored via dispositor, Section 10)
- `notes`: `list[str]`, default `[]`

---

## 8. Divisional Block (populated Day 6; shape frozen now)

```json
{
  "d9": {
    "placements": { "Sun": "Leo", "Moon": "Libra", "...": "..." },
    "flags": { "vargottama": ["Saturn"], "debilitated_in_d9": ["Venus"] }
  },
  "d10": {
    "placements": { "Sun": "Aries", "...": "..." },
    "flags": { "tenth_lord_well_placed": false, "tenth_lord_in_dusthana": false }
  }
}
```

- `placements`: `dict[PlanetName, SignName]`, all 9 planets when populated.
- D9 flags carry the scorer's hooks: vargottama (+4) and D9 debilitation (−4) per Section 11. D10 flags carry the career modifier hooks (+3 / −3). Flags exist in the schema even when the Day 6 cut ships D10 at weight 0; the flag still flows, the scorer ignores it (playbook Day 6 cut).
- No schema slots for D2, D7, D12, D4, D16, D24, D30, D60 beyond this generic object. Postponed entirely (Section 11).

---

## 9. Transits Block (populated Day 8; shape frozen now)

```json
{
  "computed_at": "2026-06-18T07:30:00Z",
  "windows": [
    { "domain": "career",
      "start": "2026-07-12", "end": "2026-07-28",
      "triggers": ["Saturn trine natal 10th cusp", "Sun transits star of Venus"],
      "window_score": 0.74 }
  ]
}
```

- `computed_at`: `Optional` ISO 8601 UTC; null until Day 8.
- Per window: `domain` is `Literal["career","finance","relationship"]`; `start` < `end`; span 7 to 30 days inclusive (validator, matching Section 14's hard cap); `triggers`: `list[str]`, min length 1; `window_score`: `float, ge=0, le=1`.
- Max 3 windows per domain (validator).

---

## 10. Prediction Feature Object (one per domain; input to scorer and to Gemini)

```json
{
  "domain": "career",
  "primary_cusp_sub_lord": "Venus",
  "cusp_sub_lord_signifies": [2, 10, 11],
  "event_promise": true,
  "active_dasha_lords": ["Venus", "Saturn", "Mercury"],
  "dasha_support": { "Venus": [2, 10, 11], "Saturn": [6, 10], "Mercury": [3, 11] },
  "supporting_significators": ["Venus", "Saturn", "Mercury"],
  "blocking_significators": ["Mars"],
  "blocking_houses_hit": [5],
  "relevant_strengths": { "Venus": 71, "Saturn": 64, "Mercury": 58 },
  "transit_windows": [ { "start": "2026-07-12", "end": "2026-07-28",
                         "triggers": ["Saturn trine natal 10th cusp", "Sun transits star of Venus"],
                         "window_score": 0.74 } ],
  "rag_alignment": { "status": "aligned", "chunk_ids": ["kp_0231", "kp_0417"] },
  "raw_score": 78, "confidence_tier": "MEDIUM", "probability_pct": 68
}
```

- `domain`: `Literal["career","finance","relationship"]`
- `cusp_sub_lord_signifies`, `blocking_houses_hit`: `list[int 1..12]`
- `dasha_support`, `relevant_strengths`: `dict[PlanetName, ...]`
- `raw_score`: `int, ge=0, le=100`
- `confidence_tier`: `Literal["HIGH","MEDIUM","SPECULATIVE","WEAK_SIGNAL"]` (85 to 100 / 65 to 84 / 45 to 64 / below 45, Section 13). Boundary semantics: 84 is MEDIUM, 85 is HIGH; the scorer's boundary tests enforce both sides.
- `probability_pct`: `int, ge=0, le=100`
- `rag_alignment.status`: `Literal["aligned","partial","contradicted","no_data"]`. Only "aligned" appears in the master plan example; the other three values are pinned here as the convention so Day 9/10 code does not invent its own strings. If you want different names, change them BEFORE tonight's freeze.
- This exact object is also what the Gemini synthesizer receives (Section 16's allowed-entities check derives from it), so field names here are user-facing in the indirect sense that the validator compares LLM output tokens against them.

---

## 11. Pydantic Requirements (what Codex must generate)

1. pydantic v2, one model per object above, shared `PlanetName`/`SignName` Literals, `ConfigDict(extra="forbid")` on every model.
2. Range/enum constraints exactly as specified; cross-field validators for: start < end on every dated period, significator_levels keys ⊆ significator_of_houses, sorted-unique house lists, window span 7 to 30 days, max 3 windows per domain, planets list length 9 in fixed order, houses list length 12 ordered.
3. Progressive population: every Day 2+ field `Optional` with the defaults shown in Section 3, so a Day 1 chart (ephemeris fields only) validates and `scripts/e2e_check.py` runs tonight printing stub markers.
4. A `ChartData.model_json_schema()` export written to `schemas/chart.json`; that file is the tagged artifact.

---

## 12. Required Tests (Day 1 gate: round-trip without loss)

`tests/test_schema_roundtrip.py`:

1. Each of the 5 example objects from this doc (planet, house, dasha, strength, prediction feature) parses, serializes with `model_dump_json()`, and re-parses with zero loss (deep equality).
2. The full top-level example (Section 3) round-trips, including all null/empty stub blocks.
3. Rejection tests, one each: `longitude: 361`, unknown planet name `"Pluto"`, `lat: 70.0`, missing `timezone`, missing `approximate_time`, a typo'd extra field (`"longitude_deg"`), `pada: 5`, `confidence_tier: "LOW"`, a 35-day transit window, 4 windows in one domain, `upcoming_md_ad` with 6 entries.
4. A Day 1 partial chart (planets carrying only ephemeris-owned fields, everything later-owned null) validates cleanly.

Definition of done: pytest green on all of the above, PR opened from `codex/schemas`, no merge until tests pass locally (Rule 4).

---

## 13. The Five Pre-Freeze Adversarial Scenarios (Claude Pro review, resolved)

These are the playbook's five schema-breaking scenarios and how v1.0 answers each. Re-run the Claude Pro attack anyway before tagging; if it finds a sixth, patch and document it here.

| Scenario | Resolution in v1.0 |
|---|---|
| Missing or unparseable timezone | API resolves from lat/lon before chart creation; schema requires non-empty IANA string, so no chart exists without one |
| lat beyond 66° | Rejected at API with 400 LAT_UNSUPPORTED; schema backstop `ge=-66, le=66` |
| Birth time known only approximately | `birth.approximate_time: bool` required; downstream language softening keys off it |
| Ascendant at 29°59' of a sign | No schema change; 4-decimal serialization plus the ephemeris exact-sign acceptance covers it; one of the 25 reference charts sits within 1° of a boundary on purpose |
| Pre-1950 birth date | Valid input; ephemeris file coverage verified by `/health` and the engine guard, not by the schema |

---

## 14. Non-Goals

No database DDL (Section 19 owns table shapes; `charts.chart_data` just stores this object). No API request/response envelopes (Section 20). No synthesis output schema (Section 16, Day 9). No frontend prop types. No health-check payload (docs/health.md).
