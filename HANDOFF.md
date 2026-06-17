# HANDOFF.md
**The append-only handoff log. Every agent writes an entry here BEFORE stopping; the founder reads at merge time and at the 21:00 sweep.**

How this file works:

- **Newest entry at the top**, directly under this header block.
- **Agents append entries; they never edit or delete existing ones.** A correction is a new entry referencing the old.
- **One entry per task**, written even when the task failed or was blocked. A blocked entry containing one specific question is a successful handoff; the founder answers in the relevant spec doc, then replies "updated <doc>, follow it."
- **Division of labor with the other files:** TASKBOARD.md holds STATUS (the founder syncs it from entries here). DECISIONS.md holds RULINGS. This file holds the NARRATIVE: what was built, what was found, what the next session needs to know. An agent session starts amnesiac; this log is its memory of yesterday.
- **Never in this file:** secret values, tokens, keys, connection strings. If you found a credential somewhere it should not be, write one line ("credential found in <file>") without reproducing it.
- **Archive policy:** after a task's branch merges and its day's gate passes, the founder may move its entry to `docs/handoffs/` to keep this file short. Entries from the current and previous day always stay here.

---

## Entry template (copy exactly)

```md
## <Task ID> â€” <branch> â€” <YYYY-MM-DD HH:MM> â€” <agent>
**Built:** one or two sentences, plain language.
**Files changed:** list (must match the allowed list; the guard script output goes here if it flagged anything).
**Tests run:** exact command + result (e.g., `pytest tests/test_ephemeris.py -q` â†’ 14 passed, 2 skipped PENDING_JHORA).
**Known issues / deferred:** list, or "none".
**Next agent should read:** files, or "n/a".
**Tempted but did not:** anything you wanted to change outside scope (this line catches scope pressure before it becomes scope creep).
**Question (only if BLOCKED):** one specific question, then stop.
```

---

# Entries

## T5.1-dasha — agent/claude/dasha-engine — 2026-06-17 — Claude Code
**Built:** the **internal Vimshottari dasha engine** `backend/app/engines/dasha_engine.py`. `compute_dasha(*, moon_nakshatra_lord, moon_degree_in_nakshatra, birth)` and `compute_dasha_from_chart(chart)` return a `DashaTimeline` of 9 mahadashas / 81 antardashas / 729 pratyantardashas with `current_stack(t)` / `current_lords(t)` (start-inclusive, end-exclusive). Birth MD lord = the **chart Moon nakshatra block's lord** (Moon never recomputed); balance = `MD_years × (NAK_SPAN − moon_degree_in_nakshatra)/NAK_SPAN`, `NAK_SPAN = 13.333333333333334°`. MD/AD/PD nest proportionally.
**Convention (the crux):** JHora's screenshots say "Using true tropical solar years" + "Started from Moon". I proved (exploration, then locked in tests) that this is **not** a fixed-day constant: each dasha boundary at cumulative time `T` years is the instant the **true/geometric tropical Sun** (`swe.FLG_SWIEPH|FLG_SPEED|FLG_TRUEPOS`, **no** `FLG_SIDEREAL`) has advanced `T×360°` of tropical longitude from the back-projected birth-MD start. The Sun's varying speed makes per-MD year length range 365.2415–365.2451 days. `MEAN_TROPICAL_YEAR_DAYS = 365.2425` is locked **only** as the Newton-solver seed / reference, never as a period length. This **refines D002's 365.25 placeholder** → new decision **D027**.
**Why / evidence:** real pipeline (ephemeris → chart Moon block → dasha) reproduces JHora's entire User 1 Kolkata ladder — 9 MDs (1992→2112), Venus+Moon AD sets, Venus/Moon + Moon/Ketu PD sets, and the 3 current_stack cases (2026-06-17 midnight→Mars, noon→Rahu, exact boundary 11:09:11→Rahu) — within **~3.8h** (gate **6h**). The residual is the irreducible anchor offset from our Swiss Moon differing from JHora's by ~1″. Birth stack = Venus/Moon/Venus exactly. A fixed-constant year (365.25 / 365.24219 / 365.2425) is off **54–60h** at PD level and **fails** the 6h tolerance, and the current_stack noon case only resolves correctly under the transit model — that gap is the explicit "prove the convention" test. Fixture `tests/fixtures/jhora/dasha_expected.json` is the judge (Rule 8); no expected value was adjusted.
**Public API untouched (verified):** `chart.dashas` stays `null` — the chart router does not import or call this engine; `git grep -n "dashas" backend/app/routers/chart.py backend/app/engines tests` shows only test assertions that it is `None`. No `schema_version` change (still `1.2`), no `chart_engine_version` change (still `1.4.0`). `git status --short` shows only the new files below.
**Files changed:**
- `backend/app/engines/dasha_engine.py` (new)
- `tests/test_dasha_engine.py` (new, 73 tests)
- `tests/fixtures/jhora/dasha_expected.json` (new)
- `docs/dasha.md` (new)
- `DECISIONS.md` (D027)
- `TASKBOARD.md` (Day 5 out-of-band note)
- `HANDOFF.md`
**Tests run:**
- `set SE_EPHE_PATH=C:\Users\assas\swisseph\ephe` then `uv run --with-requirements backend\requirements.txt --with pytest python -m pytest tests\test_dasha_engine.py tests\test_significator_engine.py tests\test_house_engine.py tests\test_chart_integration.py tests\test_chart_route.py tests\test_kp_jhora_validation.py tests\test_kp_engine.py tests\test_kp_table.py tests\test_schema_roundtrip.py tests\test_health.py -q` → **198 passed, 2 warnings** (pre-existing starlette/supabase deprecations).
- `tests\test_dasha_engine.py` alone → **73 passed**. Parity tests guard on `ephemeris_files_ok()` and skip loudly (`SWISS_EPHE_REQUIRED`) on a possible Moshier fallback; the pure tests (order, balance, locked constants, constant-fails proof from the fixture) need no ephemeris.
**Known issues / deferred:** Public dasha exposure stays deferred (D023): `chart.dashas` null, no schema/version bump. Tolerance is **6h** against User 1 (well inside the founder's ±1-day operational standard); the ~3.8h residual is the Moon-vs-JHora arc-second anchor offset, not a math error. Only the User 1 fixture exists; User 2 Mumbai / User 5 Siliguri dasha fixtures, and Sookshma/Prana levels, are TODOs in `docs/dasha.md`. The engine depends on the same Swiss `.se1` files as the ephemeris engine (for the tropical Sun); CI/local must keep `SE_EPHE_PATH` set. `scripts/check_allowed_files.py` is still absent in this worktree, so `git status --short` / `git diff --stat` stand in. No push performed per prompt.
**Next agent should read:** `docs/dasha.md`, `DECISIONS.md` D027 (+ D002, D026), `backend/app/engines/dasha_engine.py`, `tests/test_dasha_engine.py`, `tests/fixtures/jhora/dasha_expected.json`. Node agency v2 (D026) then consumes this timeline internally before career prediction.
**Tempted but did not:** populate `chart.dashas` or any public field; touch `schemas/chart.json` / `backend/app/schemas/models.py` / `backend/app/routers/chart.py` / `ephemeris_engine.py` / `nakshatra_engine.py` / `kp_engine.py` / `house_engine.py` / `significator_engine.py`; bump `schema_version` or `chart_engine_version`; use a fixed 365.25/365.24219 constant for period lengths; add node agency, Sookshma, or prediction logic.

## T4.2-base-ladder — agent/claude/significator-ladder — 2026-06-17 — Claude Code
**Built:** the internal **base KP A/B/C/D significator ladder engine** `backend/app/engines/significator_engine.py`. `compute_house_significator_ladders(planets, houses)` returns `{house_number: {"A": [...], "B": [...], "C": [...], "D": [...]}}`, every list filtered to the 9 classical planets, deduplicated, and ordered canonically (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu). House-centric rule (D025): **A** = planets whose KP star lord is a direct occupant; **B** = direct occupants; **C** = planets whose KP star lord is the owner; **D** = the owner. Owner source is `houses[].cusp_sign_lord`, occupants source is `houses[].occupants` (D024 bhava spans), star lord source is `planets[].kp.star_lord`. Base ladder only — Rahu/Ketu are plain names for star-lord matching and possible occupants; **no** node sign-lord/conjunction/aspect agency, **no** sub-lord filtering, **no** prediction logic, **no** API exposure. Reads the chart only; does not mutate input and populates no public field.
**Why / evidence:** User 1 Kolkata was cross-checked against JHora (Houses tab / D024 occupants, KP star/sub table, "Planets occupying each planet's nakshatra" clipboard). The real pipeline (ephemeris → KP → bhava-span occupation → ladder) reproduces **all 36 expected house rows** (User 1 Kolkata, User 2 Mumbai, User 5 Siliguri) exactly, owner/occupants/A/B/C/D. Fixture is the judge (AGENTS.md Rule 8); no expected value was adjusted to match output.
**Pre-check:** `git grep -n "cusp_sign_lord" backend/app schemas tests docs` → present in `backend/app/schemas/models.py` (HouseBlock), `backend/app/engines/ephemeris_engine.py`, `schemas/chart.json`, `tests/test_schema_roundtrip.py`, and docs. Used as the house-owner source; no schema field added.
**Files changed:**
- `backend/app/engines/significator_engine.py` (new)
- `tests/test_significator_engine.py` (new, 16 tests)
- `tests/fixtures/jhora/t41_significator_ladders_expected.json` (new, 36 rows)
- `DECISIONS.md` (D025)
- `TASKBOARD.md` (Day 4 out-of-band note)
- `HANDOFF.md`
**Tests run:**
- `set SE_EPHE_PATH=C:\Users\assas\swisseph\ephe` then `uv run --with-requirements backend\requirements.txt --with pytest python -m pytest tests\test_significator_engine.py tests\test_house_engine.py tests\test_chart_integration.py tests\test_chart_route.py tests\test_kp_jhora_validation.py tests\test_kp_engine.py tests\test_kp_table.py tests\test_schema_roundtrip.py tests\test_health.py -q` → **125 passed, 2 warnings**.
- Parity tests guard on `ephemeris_files_ok()` and skip loudly (`SWISS_EPHE_REQUIRED`) if the run may be Moshier fallback; the hand-built unit tests need no ephemeris.
**Known issues / deferred:** Public significator fields remain RESERVED/unpopulated (D023): `houses[].significators` null, `planets[].significator_of_houses` `[]`, `planets[].significator_levels` `{}` — asserted by the existing integration test and by a new no-mutation test. No schema bump, no `engine_version`/`schema_version` change. The cusp-sublord half of T4.2 and **full node agency** (sign lord, conjunction, aspect, representation) are NOT implemented — they must be restored before serious prediction/timing launch (D025). `scripts/check_allowed_files.py` is absent in this worktree (as in prior entries), so `git status --short` / `git diff --stat` stand in. No push per prompt.
**Next agent should read:** `backend/app/engines/significator_engine.py`, `DECISIONS.md` D025 + D023 + D024, `tests/fixtures/jhora/t41_significator_ladders_expected.json`, `tests/test_significator_engine.py`.
**Tempted but did not:** populate any public significator field, add node sign-lord/conjunction/aspect agency, apply sub-lord filtering, touch `schemas/chart.json` / `backend/app/schemas/models.py` / `backend/app/routers/chart.py` / `kp_engine.py` / `house_engine.py` / `ephemeris_engine.py`, bump schema or engine version, or add prediction/interpretation logic.

## T4.3-correction — agent/claude/house-bhava-rule — 2026-06-16 — Claude Code
**Built:** Corrected public house occupation to match JHora's "House Start / Cusp / End / Planets in it" table (D024). Replaced the cusp-to-next-cusp membership rule (`House H = [cusp_H, cusp_{H+1})`) in `house_engine` with JHora **bhava midpoint spans**: `start_H = midpoint(prev_cusp, cusp_H)`, `end_H = midpoint(cusp_H, next_cusp)`, start inclusive / end exclusive, cusp interior, modular across 0° Aries. Affects only `planets[].house_occupied` and `houses[].occupants`; the KP cusp star/sub-lord lookup (from cusp longitude) is untouched.
**Why / evidence:** The old rule put Rahu in house 12 for User 1 Kolkata (1998-08-14 06:45, Kolkata). JHora's table shows the 1st house as Start 2 Leo 50′, Cusp 17 Leo 25′, End 1 Virgo 28′, **Planets in it = As, Rahu** — Rahu lies after the 1st-house start but before the 1st cusp, so it belongs to house 1. The bhava-span rule reproduces JHora's column exactly.
**Final User 1 Kolkata occupation (verified, matches JHora "Planets in it"):** Rahu→1, Ketu→7, Jupiter→8, Moon→9, Saturn→9, Mars→11, Sun→12, Mercury→12, Venus→12. (JHora also lists Pluto→4, Uranus/Neptune→6; our public output carries only the 9 classical planets, so those are not asserted.)
**Files changed:**
- `backend/app/engines/house_engine.py` (bhava-span membership; `chart.py` needed no change — it already calls the engine helpers)
- `tests/test_house_engine.py` (unit tests rewritten for bhava spans: interior, wraparound across 0°, start inclusive, end exclusive, cusp-interior, all-9-once, consistency)
- `tests/test_chart_integration.py` (renamed derivation test to bhava spans; added live User 1 Kolkata regression)
- `docs/houses.md`, `DECISIONS.md` (D024), `TASKBOARD.md`, `HANDOFF.md`
**Tests run:**
- `set SE_EPHE_PATH=C:\Users\assas\swisseph\ephe` then `uv run --with-requirements backend\requirements.txt --with pytest python -m pytest tests\test_house_engine.py tests\test_chart_integration.py tests\test_chart_route.py tests\test_kp_jhora_validation.py tests\test_kp_engine.py tests\test_kp_table.py tests\test_schema_roundtrip.py tests\test_health.py -q` → **109 passed, 2 warnings**.
**Known issues / deferred:** Significators stay RESERVED/unpopulated (D023). No legacy cusp KP fields re-added. No schema/version bump. This correction blocks T4.1/T4.2 until merged (significators read occupation). No push performed per prompt.
**Next agent should read:** `docs/houses.md`, `DECISIONS.md` D024, `backend/app/engines/house_engine.py`, `tests/test_chart_integration.py`.
**Tempted but did not:** change the KP cusp star/sub-lord lookup, populate significators, add owner logic, touch schema/model files, bump schema or engine version, or alter ephemeris/nakshatra/KP math.

## T4.3 — agent/codex/house-engine — 2026-06-16 16:57 — Codex
**Built:** Added `house_engine` cusp-span occupation helpers and wired `/chart/generate` so every public planet gets `house_occupied` and every house gets the inverse `occupants` list. Significator placeholders remain unpopulated, and KP/nakshatra/ephemeris math was left untouched.
**Files changed:**
- `backend/app/engines/house_engine.py`
- `backend/app/routers/chart.py`
- `tests/test_house_engine.py`
- `tests/test_chart_integration.py`
- `HANDOFF.md`
**Tests run:**
- `$env:SE_EPHE_PATH='C:\Users\assas\swisseph\ephe'; uv run --with-requirements backend\requirements.txt --with pytest python -m pytest tests\test_house_engine.py tests\test_chart_integration.py tests\test_chart_route.py tests\test_kp_jhora_validation.py tests\test_kp_engine.py tests\test_kp_table.py tests\test_schema_roundtrip.py tests\test_health.py -q` -> 108 passed, 2 warnings.
- `git diff --check` -> passed; Git printed CRLF normalization warnings only.
- `Test-Path scripts\check_allowed_files.py` -> False; allowed-files guard script is absent in this worktree.
**Known issues / deferred:** allowed-files guard script is absent; `git status --short` and `git diff --stat` were used to verify only allowed files changed. No push performed per prompt.
**Next agent should read:** `backend/app/engines/house_engine.py`, `backend/app/routers/chart.py`, `tests/test_house_engine.py`, `tests/test_chart_integration.py`, `docs/houses.md`, D023.
**Tempted but did not:** populate significators, add owners or KP ladder logic, change KP public shape, touch schemas/model files, bump schema/version, adjust ephemeris/nakshatra math, or add prediction logic.

## docs-contract-sync — docs/house-significator-contract-sync — 2026-06-16 — Claude Code
**Built:** Documentation-only contract sync so the next agent reads one consistent source of truth. No product/engine/schema code touched.
**Current state (authoritative as of this entry):**
- **KP JHora validation is merged.** 5 JHora charts × (9 planets + 12 houses) = 21 objects each, 105 object validations; relevant slice passed 94, 2 warnings.
- **Public KP contract validated and frozen** at `planets[].kp.{star_lord, sub_lord}` and `houses[].kp.{star_lord, sub_lord}` (schema v1.2, D022). No `sub_sub_lord` in public output.
- **Legacy public cusp KP fields removed:** `houses[].cusp_star_lord` / `cusp_sub_lord` / `cusp_sub_sub_lord` are gone from model + schema + generated frontend type.
- Schema is **v1.2**; engine/cache version is **1.4.0**. `chart-schema.md` has been synced to v1.2 (banner + inline fixes).
- `docs/houses.md` created with the **cusp-span** house-boundary rule (House H = `[cusp_H, cusp_{H+1})`, modular wraparound, planet-on-cusp belongs to the house starting there, never by sign).
- Significators are **RESERVED / NOT POPULATED in v1.2** pending **D023** (added this pass): D022 still governs, no agent invents public significator fields, the existing A/B/C/D ladder is the only future-compatible shape, T4.2 (significators) is Claude's lane, T4.3 (`house_engine`) is Codex's lane.
**Next task:** `agent/codex/house-engine` (T4.3) — fill `planets[].house_occupied` + `houses[].occupants` via cusp spans, wired into chart output; no schema bump, no significators, no KP changes, no prediction logic. Acceptance is spelled out in TASKBOARD.md under Day 4.
**Before significators:** complete T4.1 manual hand-worked ladders and obtain an explicit founder decision lifting D023.
**Files changed:** `docs/chart-schema.md`, `docs/houses.md` (new), `TASKBOARD.md`, `DECISIONS.md` (D023), `AGENTS.md`, `docs/PROJECT_CONTEXT.md`, `HANDOFF.md`.
**Tests run:** none — docs only. Verified with `git grep` that legacy cusp fields appear only as REMOVED notes in the edited docs, no midpoint-to-midpoint house language exists, T4.3 branch is `agent/codex/house-engine` and includes `chart.py` + `test_chart_integration.py`, and D023 blocks public significator population.
**Known issues / deferred:** out-of-scope docs still carry legacy/planned cusp KP references and were NOT edited (not in this task's allowed-files list): `docs/nakshatra.md` (lines ~123-125), `docs/ephemeris.md` (line ~21, lists `cusp_sub_lord` as a later-engine field), `docs/execution/junopath_mvp_plan_jun22.md` (house example). Recommend a follow-up sync task for those.
**Next agent should read:** `DECISIONS.md` D022 + D023, `docs/chart-schema.md` (v1.2 banner), `docs/houses.md`, TASKBOARD.md T4.3 acceptance.
**Tempted but did not:** edit schema/model/router/tests/frontend (verified schema and model already agree at v1.2, so no change needed); edit the out-of-scope docs listed above; touch T4.2's scope beyond marking the removed legacy cusp fields.

## remove-legacy-cusp-kp-fields — agent/codex/remove-legacy-cusp-kp-fields — 2026-06-16 14:05 — Codex
**Built:** Removed the stale public `houses[]` legacy cusp KP placeholder fields (`cusp_star_lord`, `cusp_sub_lord`, `cusp_sub_sub_lord`) from the Pydantic model, JSON schema, and generated frontend chart type. Public house KP remains only at `houses[].kp.star_lord` and `houses[].kp.sub_lord`, per D022/schema v1.2.
**Files changed:**
- `backend/app/routers/chart.py`
- `backend/app/schemas/models.py`
- `schemas/chart.json`
- `frontend/src/types/chart.ts`
- `tests/test_chart_integration.py`
- `tests/test_chart_route.py`
- `tests/test_schema_roundtrip.py`
- `HANDOFF.md`
**Tests run:**
- `$env:SE_EPHE_PATH='C:\Users\assas\swisseph\ephe'; uv run --with-requirements backend\requirements.txt --with pytest python -m pytest tests\test_kp_engine.py tests\test_kp_table.py tests\test_chart_route.py tests\test_chart_integration.py tests\test_schema_roundtrip.py tests\test_health.py -q` -> 84 passed, 2 warnings.
- `npm.cmd run lint` from `frontend/` -> passed, no ESLint warnings or errors.
- `npm.cmd run build` from `frontend/` -> passed.
- `git diff --check` -> passed.
**Known issues / deferred:** none.
**Next agent should read:** `DECISIONS.md` D022, `backend/app/schemas/models.py`, `schemas/chart.json`, and the updated schema/route tests.
**Tempted but did not:** change KP lookup internals, add sub-sub lord to the public contract, edit `data/kp_249.csv`, change ephemeris/nakshatra math, bump schema or engine version, or touch prediction/significator fields.

## KP-chart-integration — agent/codex/kp-chart-integration — 2026-06-16 13:12 — Codex
**Built:** Integrated the internal KP sub-lord lookup into public chart output with the D022 MVP shape. Schema v1.2 now requires strict `kp` blocks on `planets[]` and `houses[]`, `/chart/generate` copies only `star_lord` and `sub_lord` from the internal lookup result, chart/cache version bumped to `1.4.0`, and stale cached charts that fail current v1.2 validation are recomputed instead of returned.
**Files changed:**
- `backend/app/core/config.py`
- `backend/app/routers/chart.py`
- `backend/app/schemas/models.py`
- `schemas/chart.json`
- `tests/test_chart_route.py`
- `tests/test_chart_integration.py`
- `tests/test_schema_roundtrip.py`
- `tests/test_health.py`
- `frontend/src/fixtures/chart.sample.json`
- `frontend/src/types/chart.ts`
- `frontend/app/chart/page.tsx`
- `DECISIONS.md`
- `TASKBOARD.md`
- `HANDOFF.md`
**Tests run:**
- `uv run --with-requirements backend\requirements.txt python -c "import json; from pathlib import Path; import sys; sys.path.insert(0, 'backend'); from app.schemas.models import ChartData; Path('schemas/chart.json').write_text(json.dumps(ChartData.model_json_schema(), indent=2) + '\n', encoding='utf-8')"` -> passed after escalation for uv cache access.
- `uv run --with-requirements backend\requirements.txt python -c "import json, sys; from pathlib import Path; sys.path.insert(0, 'backend'); from app.engines.kp_engine import get_kp_sub_lord; data=json.loads(Path('frontend/src/fixtures/chart.sample.json').read_text(encoding='utf-8')); rows=[]; [rows.append(('planet', p['name'], p['longitude'], {k: get_kp_sub_lord(p['longitude'])[k] for k in ('star_lord','sub_lord')})) for p in data['planets']]; [rows.append(('house', h['house'], h['cusp_longitude'], {k: get_kp_sub_lord(h['cusp_longitude'])[k] for k in ('star_lord','sub_lord')})) for h in data['houses']]; print(json.dumps(rows, indent=2))"` -> passed after escalation; used only to derive sample fixture `kp` values.
- `& 'C:\Program Files\Git\bin\bash.exe' -lc './scripts/gen_types.sh'` -> Type generation complete after escalation for npm cache/registry access.
- `$env:SE_EPHE_PATH='C:\Users\assas\swisseph\ephe'; uv run --with-requirements backend\requirements.txt --with pytest python -m pytest tests\test_kp_engine.py tests\test_kp_table.py tests\test_chart_route.py tests\test_chart_integration.py tests\test_schema_roundtrip.py tests\test_health.py -q` -> 81 passed, 2 warnings.
- `npm.cmd run lint` in `frontend/` -> no ESLint warnings or errors. Plain `npm run lint` was blocked by the local PowerShell execution policy for `npm.ps1`, so `npm.cmd` was used.
- `npm.cmd run build` in `frontend/` -> compiled successfully.
- `git diff --check` -> passed; Git printed CRLF normalization warnings only.
- `Test-Path scripts/check_allowed_files.py` -> False; allowed-files guard script is absent in this worktree.
- `git status --short --branch` -> branch `agent/codex/kp-chart-integration`, modified files listed above, no untracked files.
**Known issues / deferred:** none for this integration. KP values are mechanically from the internal table and still need external KP JHora validation.
**Next agent should read:** `backend/app/routers/chart.py`, `backend/app/schemas/models.py`, `schemas/chart.json`, `tests/test_chart_route.py`, `tests/test_chart_integration.py`, D022. Next step: KP JHora validation.
**Tempted but did not:** add KP significators, ruling planets, prediction/event logic, interpretation text, sub-sub lord to the public block, modify `data/kp_249.csv`, or change ephemeris/nakshatra math.

## KP-lookup — agent/claude/kp-lookup-engine — 2026-06-16 — Claude Code
**Built:** the internal KP sub-lord lookup engine `backend/app/engines/kp_engine.py`, reading the committed `data/kp_249.csv`. `get_kp_sub_lord(longitude_deg)` normalises the longitude into `[0, 360)`, converts once to integer arc-seconds with the same discipline as the nakshatra engine (`arcsec = round((L % 360) * 3600) % 1_296_000`), then resolves the containing CSV row via `bisect` over the contiguous start bounds. Returns `star_lord` (nakshatra/star lord), `sub_lord`, `sub_index`, `sub_start_longitude`, `sub_end_longitude`, `degree_in_sub`, plus internal extras (`nakshatra_index`, `nakshatra_name`, `row_index`, `longitude`, `arcsec`). No public schema, no `planets[].kp`/`houses[].kp`, no chart integration, no prediction/significator/ruling-planet logic, no ephemeris or table changes.
**Boundary rule:** each row covers the half-open interval `[start_arcsec, end_arcsec)` — lower bound inclusive, upper exclusive. A longitude exactly on a boundary belongs to the row that STARTS at that boundary. Because the arc-second conversion takes `% 1_296_000`, the max reachable value is `1_295_999` and `360°` (and tiny negatives) wrap to `0` → row 1; nothing ever maps to the final row's exclusive end `1_296_000`, so there is no off-by-one at the table end.
**`sub_start_longitude` / `sub_end_longitude` semantics (assumption):** these are the matched CSV row's bounds. Where a logical sub-lord span is split at a 30° sign boundary into two rows (e.g. rows 22–23, Krittika/Rahu/sub_index 4), the returned bounds are the per-row bounds, not the merged logical span. This is the interpretation that makes "lookup result agrees with the CSV row containing the longitude" exact.
**Files changed:**
- `backend/app/engines/kp_engine.py` (new)
- `tests/test_kp_engine.py` (new, 13 tests)
- `HANDOFF.md`
- `TASKBOARD.md`
**Tests run:**
- `uv run --with-requirements backend\requirements.txt --with pytest python -m pytest tests\test_kp_engine.py tests\test_kp_table.py -q` -> 20 passed (13 engine + 7 table).
- `git diff --check` -> clean (no output).
- `git status` -> branch `agent/claude/kp-lookup-engine`; only the two new files untracked before commit.
**Tests cover:** `0° Aries`; exact sub-boundary (belongs to upper row); just-before / just-after a boundary; `359.99999°` (wraps to 0); `360°` wraps to 0; tiny negative wraps; large/±360 normalisation; a longitude where sub_lord ≠ star_lord cross-checked by hand from `data/kp_249.csv` (1.0° → Ketu / Venus); every row's interior midpoint agrees with its CSV row; no off-by-one at every row start/last-arcsec/end; required-keys presence; `degree_in_sub` offset invariant.
**Known issues / deferred:** none. `scripts/check_allowed_files.py` is absent in this worktree (as noted in prior entries), so `git status`/`git diff --check` stand in for the allowed-files guard.
**Next agent should read:** `backend/app/engines/kp_engine.py`, `tests/test_kp_engine.py`, D022. T3.2 (`agent/claude/kp-planet`) can consume this lookup when wiring KP into chart output (schema bump to v1.2 happens there, not here).
**Tempted but did not:** add `planets[].kp`/`houses[].kp`, touch `schemas/chart.json`, bump the schema version, compute sub-sub lord, add significators/ruling planets/prediction logic, or modify `data/kp_249.csv`/`scripts/gen_kp_table.py`/ephemeris math.

## T3.1 — agent/codex/kp-table — 2026-06-16 11:53 — Codex
**Built:** Added a deterministic KP 249 sub-lord table generator and committed CSV data. The base 243 Vimshottari sub-lord intervals are split at the six 30-degree sign boundaries that fall strictly inside a sub-lord span, producing 249 rows without changing sub-lord lengths.
**Files changed:**
- `scripts/gen_kp_table.py`
- `data/kp_249.csv`
- `tests/test_kp_table.py`
- `docs/nakshatra.md`
- `TASKBOARD.md`
- `HANDOFF.md`
**Tests run:**
- `uv run --with-requirements backend\requirements.txt --with pytest python -m pytest tests\test_kp_table.py -q` -> 7 passed.
- `uv run --with-requirements backend\requirements.txt python scripts\gen_kp_table.py --check` -> passed.
- `git diff --check` -> passed; Git printed CRLF normalization warnings for `HANDOFF.md`, `TASKBOARD.md`, and `docs/nakshatra.md`.
- `git status --short --branch` -> branch `agent/codex/kp-table`, expected modified/new KP files only before commit.
- `Test-Path scripts\check_allowed_files.py` -> False; allowed-files guard script is absent in this worktree.
**Known issues / deferred:** no schema, chart integration, KP lookup engine, prediction logic, significators, ruling planets, or frontend work was added.
**Next agent should read:** `scripts/gen_kp_table.py`, `data/kp_249.csv`, `tests/test_kp_table.py`, `docs/nakshatra.md`.
**Tempted but did not:** add `planets[].kp`/`houses[].kp` integration, change the existing schema KP shape, build a lookup engine, or touch ephemeris/nakshatra math.

## BUG-001 — agent/codex/jhora-gate-ephe-guard — 2026-06-16 11:26 — Codex
**Built:** Hardened the strict JHora parity tests so they first require active Swiss `.se1` files via `ephemeris_files_ok()` and skip loudly with `SWISS_EPHE_REQUIRED` when the run may be Moshier fallback. Updated BUG-001 and the ephemeris spec to record the diagnosed cause: unset `SE_EPHE_PATH`, no math fix, fixture edit, or tolerance loosening required.
**Files changed:**
- `tests/test_ephemeris.py`
- `BUGS.md`
- `docs/ephemeris.md`
- `HANDOFF.md`
**Tests run:**
- `$env:SE_EPHE_PATH='C:\Users\assas\swisseph\ephe'; uv run --with-requirements backend\requirements.txt --with pytest python -m pytest tests\test_ephemeris.py -q` -> 88 passed.
- `Remove-Item Env:SE_EPHE_PATH -ErrorAction SilentlyContinue; uv run --with-requirements backend\requirements.txt --with pytest python -m pytest tests\test_ephemeris.py -q -rs` -> 68 passed, 20 skipped with `SWISS_EPHE_REQUIRED: JHora parity tests require .se1 files; current run may be Moshier fallback.`
- `Test-Path scripts\check_allowed_files.py` -> False; allowed-files guard script is absent in this worktree.
**Known issues / deferred:** Local and CI strict JHora runs must keep setting `SE_EPHE_PATH` to the Swiss file directory. No ephemeris math issue remains for BUG-001.
**Next agent should read:** `tests/test_ephemeris.py`, `BUGS.md`, `docs/ephemeris.md`. Next step: KP generator.
**Tempted but did not:** change ephemeris math, fixture values, tolerances, KP, schema metadata D021, frontend, or prediction logic.

## D021 — agent/codex/schema-metadata-v1-1 — 2026-06-15 20:01 — Codex
**Built:** Legalized optional chart response metadata in schema v1.1, keeping the object strict and extra-forbidden. Regenerated frontend ChartData and removed the temporary metadata wrapper in the chart page while preserving the live response envelope.
**Files changed:**
- `schemas/chart.json`
- `backend/app/schemas/models.py`
- `backend/app/routers/chart.py`
- `tests/test_schema_roundtrip.py`
- `tests/test_chart_route.py`
- `tests/test_chart_integration.py`
- `frontend/src/types/chart.ts`
- `frontend/src/fixtures/chart.sample.json`
- `frontend/app/chart/page.tsx`
- `DECISIONS.md`
- `TASKBOARD.md`
- `HANDOFF.md`
**Tests run:**
- `& 'C:\Program Files\Git\bin\bash.exe' -lc './scripts/gen_types.sh'` -> Type generation complete. Earlier `bash scripts/gen_types.sh` hit the WSL stub, direct Git Bash lacked `mkdir` until run as a login shell, and the first sandboxed `npx` attempt hit npm cache/registry permissions.
- `$env:SE_EPHE_PATH='C:\Users\assas\swisseph\ephe'; uv run --with-requirements backend\requirements.txt --with pytest python -m pytest tests\test_chart_route.py tests\test_chart_integration.py tests\test_health.py -q` -> 33 passed, 2 warnings.
- `uv run --with-requirements backend\requirements.txt --with pytest python -m pytest tests\test_schema_roundtrip.py -q` -> 20 passed.
- `npm.cmd run lint` -> no ESLint warnings or errors.
- `npm.cmd run build` -> compiled successfully.
- `git diff --name-only` -> relevant schema/router/frontend/docs/test files only. `scripts/check_allowed_files.py` is absent in this worktree.
**Known issues / deferred:** BUG-001 Rahu-only tolerance remains open and untouched.
**Next agent should read:** `schemas/chart.json`, `backend/app/schemas/models.py`, `frontend/src/types/chart.ts`, `tests/test_schema_roundtrip.py`.
**Tempted but did not:** touch ephemeris math, nakshatra engine, KP, prediction fields, deployment config, `.env` files, or frontend dependency versions.

## Day 2 final closeout
Completed: T2.1 nakshatra engine, T2.2 boundaries_330.json generator, T2.3 chart
integration, T2.5 frontend ChartData typegen — all merged. chart_engine_version 1.3.0.
Gate suite 696 passed, 2 warnings. Moon 10/10. Frontend lint/build passed. Local
/chart/generate and browser fetch verified. V10 Siliguri Moon = Uttara Ashadha pada 3.
Non-blockers: Rahu tolerance = BUG-001; D021 pending implementation; production may lag local main.
Next: implement D021 (optional metadata in schema v1.1) and regenerate ChartData; then KP generator; Rahu diagnosis on a separate branch, not inside KP.

## T2.5 — agent/antigravity/typegen — 2026-06-12 13:15 — Antigravity
**Built:** Generated frontend TypeScript types (ChartData) from schemas/chart.json using a new scripts/gen_types.sh script invoking json-schema-to-typescript. Updated rontend/app/chart/page.tsx to strictly consume these generated types instead of ad-hoc interfaces. The temporary metadata key is wrapped as unknown in a local ChartResponse type, ensuring compilation without polluting the core contract. Added a fully populated fixture matching the new schema at rontend/src/fixtures/chart.sample.json, which renders under NEXT_PUBLIC_USE_FIXTURE=1.
**Files changed:**
- scripts/gen_types.sh
- rontend/src/types/chart.ts
- rontend/src/fixtures/chart.sample.json
- rontend/app/chart/page.tsx
- rontend/package.json
- rontend/package-lock.json
**Tests run:** 
pm run lint && npm run build (in frontend dir) -> compiled successfully. (No 
pm test script available in frontend/package.json).
**Known issues / deferred:** none.
**Next agent should read:** rontend/src/types/chart.ts
**Tempted but did not:** I was tempted to add metadata directly to ChartData in the TypeScript interface or edit the JSON schema, but adhered strictly to D009 and D021 to wrap it at the response boundary instead.


## T2.3 â€” agent/claude/nakshatra-integration â€” 2026-06-12 â€” Claude Code
**Built:** wired the merged nakshatra engine into chart output. `_build_chart_payload` in the chart router now fills `planets[].nakshatra` with `nakshatra_block(planet.longitude)` (exactly the seven approved keys: name, index, lord, degree_in_nakshatra, pada, degree_in_pada, navamsa_sign) and `houses[].cusp_nakshatra` with `nakshatra_name(cusp_longitude)` â€” a name STRING, never an object â€” before `ChartData` validation, so the frozen v1.0 contract (`extra="forbid"`) guards the shape on every response. New integration tests prove the e2e shape on all five Day 1 fixture inputs, including Moon nakshatra name/pada/lord hand-derived from each fixture's JHora-expected Moon longitude via the docs/nakshatra.md arc-second convention (independent of the engine; every Moon sits >900 arc-sec from the nearest pada boundary, so the 5 arc-sec ephemeris tolerance cannot flip an expectation). No ephemeris glue was needed: `backend/app/engines/ephemeris_engine.py` is untouched. KP, house occupancy, significators, dasha, strength, divisional, transit, and prediction fields remain at their Day 1 null/empty defaults, asserted by test. Cache behavior unchanged (HIT path still returns the stored chart untouched; only the MISS computation path gained the fill). The temporary `metadata` key (D021) was neither removed, extended, nor newly depended on.
**Files changed:**
- `backend/app/routers/chart.py` (nakshatra fill in `_build_chart_payload` + docstring accuracy)
- `tests/test_chart_integration.py` (new, 16 tests)
- `HANDOFF.md`
**Tests run:**
- `$env:SE_EPHE_PATH='C:\Users\assas\swisseph\ephe'; uv run --with-requirements backend/requirements.txt --with pytest python -m pytest tests/test_nakshatra_engine.py tests/test_chart_route.py tests/test_chart_integration.py -q` -> **696 passed**.
- `$env:SE_EPHE_PATH='C:\Users\assas\swisseph\ephe'; uv run --with-requirements backend/requirements.txt --with pytest python -m pytest tests -q` -> **807 passed** (full suite, no pre-existing failures; was 791 before this task, +16 new).
- `git status --short` / `git diff --name-only` -> only the three files above; `scripts/check_allowed_files.py` is still absent in this worktree, so the git check stands in (same as every prior entry).
**Known issues / deferred:** (1) `settings.chart_engine_version` stays `1.2.0` â€” `backend/app/core/config.py` is outside this task's allowed list. Consequence: `user_charts` rows cached under fingerprint version 1.2.0 since the Day 1 deploy carry null nakshatra fields and will keep serving as HITs without them. Founder call at merge/deploy time: flush those rows or bump the engine version (which rotates every fingerprint), mirroring the D013/T1.5 precedent. (2) Branch pushed to origin, but the `gh` CLI is not installed in this environment, so the PR could not be opened from here â€” create it at https://github.com/Pratyus-Saha/askjunopath/pull/new/agent/claude/nakshatra-integration (base `main`).
**Next agent should read:** `backend/app/routers/chart.py` (`_build_chart_payload`), `tests/test_chart_integration.py`, `docs/nakshatra.md`. T2.4 (KP table merge) is gated on this task being green plus Moon validation.
**Tempted but did not:** bump `chart_engine_version` in `backend/app/core/config.py` (outside allowed list; founder owns the flush-vs-bump call); fill `cusp_star_lord` even though it is trivially `nakshatra_lord(cusp_longitude)` (Day 4 / T4.2 owns the cusp KP fields); touch `backend/app/engines/ephemeris_engine.py` (no assembly glue required); fold `metadata` into the schema (D021, closes Jun 13).

## T2.2/T2.1-nakshatra â€” agent/codex/nakshatra â€” 2026-06-12 16:28 â€” Codex
**Built:** generated the independent 330-row nakshatra/pada boundary fixture from the frozen `docs/nakshatra.md` rules, then implemented the pure integer-arcsecond nakshatra engine against that fixture. Added fixture-driven tests for all rows, rounding wraparound regressions, the 359Â°59'59" Revati case, navamsa spot checks, and exact seven-key `NakshatraBlock` shape.
**Files changed:**
- `scripts/gen_nakshatra_fixtures.py`
- `tests/fixtures/nakshatra/boundaries_330.json`
- `backend/app/engines/nakshatra_engine.py`
- `tests/test_nakshatra_engine.py`
- `HANDOFF.md`
**Tests run:**
- `python scripts\gen_nakshatra_fixtures.py` -> blocked by local shell: `python` is not on PATH.
- `pytest tests\test_nakshatra_engine.py -q` -> blocked by local shell: `pytest` is not on PATH.
- `C:\Users\assas\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts\gen_nakshatra_fixtures.py` -> passed.
- `uv run --with pytest python -m pytest tests\test_nakshatra_engine.py -q` -> 668 passed.
- `uv run --with-requirements backend\requirements.txt --with pytest python -m pytest tests\test_nakshatra_engine.py -q` -> 668 passed.
- `git status --short --branch` -> only approved new paths plus this handoff; branch `agent/codex/nakshatra`.
- `rg -n "[ \t]+$" scripts\gen_nakshatra_fixtures.py tests\fixtures\nakshatra\boundaries_330.json backend\app\engines\nakshatra_engine.py tests\test_nakshatra_engine.py HANDOFF.md` -> no trailing whitespace matches.
**Known issues / deferred:** no code issues. `scripts/check_allowed_files.py` is absent in this worktree, so the exact allowed-files guard could not be run without adding an out-of-scope file.
**Next agent should read:** `docs/nakshatra.md`, `backend/app/engines/nakshatra_engine.py`, `tests/test_nakshatra_engine.py`.
**Tempted but did not:** wire chart integration, touch `schemas/chart.json`, edit `backend/app/engines/__init__.py`, or add the missing allowed-files guard script.

## T1.6-version-metadata - agent/codex/version-metadata-v1-2 - 2026-06-12 12:27 - Codex
**Built:** moved backend/chart engine version metadata to the existing single source `settings.chart_engine_version`, bumped its default to `1.2.0`, and made `/health.version` plus FastAPI app metadata read from that setting. Added route tests proving chart `metadata.engine_version` is `1.2.0`, route fingerprints are generated with the current engine version, and changing the engine version changes the fingerprint.
**Files changed:**
- `backend/app/core/config.py`
- `backend/app/main.py`
- `docs/health.md`
- `tests/test_chart_route.py`
- `tests/test_health.py`
- `HANDOFF.md`
**Tests run:**
- `$env:SE_EPHE_PATH='C:\Users\assas\swisseph\ephe'; uv run --with-requirements backend/requirements.txt --with pytest python -m pytest tests/test_health.py tests/test_chart_route.py -q` -> 17 passed, 2 warnings.
- `$env:SE_EPHE_PATH='C:\Users\assas\swisseph\ephe'; uv run --with-requirements backend/requirements.txt --with pytest python -m pytest tests -q` -> 123 passed, 2 warnings.
- `git diff --name-only` -> approved files only.
**Known issues / deferred:** no Docker build or Azure deployment performed. After merge, rebuild/redeploy the backend image so production `/health.version` and chart `metadata.engine_version` report `1.2.0`; because fingerprints include `settings.chart_engine_version`, this version bump creates a new cache key for fresh chart generation.
**Next agent should read:** `backend/app/core/config.py`, `backend/app/main.py`, `backend/app/routers/chart.py`, `tests/test_chart_route.py`, `docs/health.md`.
**Tempted but did not:** edit `backend/app/core/fingerprint.py` to change its default argument because the route already passes the explicit setting and that file was not approved; touch ephemeris math, fixtures, Dockerfile, env files, or deployment scripts.

## T1.5-wire â€” agent/claude/day1-wire-chart-route â€” 2026-06-11 21:15 â€” Claude Code
**Built:** `/chart/generate` now computes exclusively via the trusted `app.engines.ephemeris_engine` (JHora-validated: KP-Newcomb sidereal, TRUE_NODE, FLG_TRUEPOS, Placidus cusps). The deprecated `app.core.chart_engine` is no longer called on any route; a DEPRECATED header documenting its defects (Alcabitius `b'B'` bug, no cusps, no ephe-path guard, apparent positions) was added to it, logic untouched. The route hands the engine naive local time + IANA zone â€” the single localâ†’UTC conversion stays inside the engine; the route's old `convert_local_to_utc` call is gone (no double conversion possible). Engine structured errors now map to structured HTTP errors: `LAT_UNSUPPORTED` â†’ 400, `INVALID_TIMEZONE`/`INVALID_COORDINATES`/`INVALID_DATETIME` â†’ 422.
**Route file note:** the task's approved list named `backend/app/main.py`, but the actual `/chart/generate` implementation lives in `backend/app/routers/chart.py` â€” actual repo layout wins (per the Day 1 path-correction precedent), so that router is the file rewired. `main.py` needed no change.
**Payload shape:** the response `chart` (and the stored `chart_json`) is now the canonical chart.json v1.0 object, validated through `ChartData` before serialization (`schema_version`, `birth` incl. `place_label` + `approximate_time: false` stub, `settings`, `ascendant`, 9 `planets`, 12 `houses`, later-engine blocks at their defaults) **plus one documented non-schema key `metadata`** carrying the legacy keys â€” required because `app.core.db.save_chart()` (not in scope) reads `chart_data["metadata"]["ayanamsa"]`/`["engine_version"]` for its columns, and the Day 1 scaffold `/chart` page calls `.toFixed()` on `metadata.latitude/longitude`. Re-validating a stored chart against `ChartData` requires popping `metadata` first; folding it into the schema (or removing it after the page rebuild) is a 1.1 decision.
**Frontend impact:** the response envelope (`cache_status`/`chart_id`/`chart_fingerprint`/`chart`) is unchanged and the scaffold page's crash sites (metadata numerics) are preserved, so the page loads â€” but its planet table reads old keys (`sidereal_longitude`, name-keyed dict) and will render index-labeled rows with NaN degrees until T2.5 rebuilds `/chart` from the typed schema. Known, accepted for one day; the scaffold predates validation anyway.
**Tests run (with `SE_EPHE_PATH=C:\Users\assas\swisseph\ephe`):**
- `uv run --with-requirements backend/requirements.txt --with pytest python -m pytest tests/test_schema_roundtrip.py tests/test_health.py tests/test_ephemeris.py -q` â†’ **111 passed**.
- `... tests/test_chart_route.py -q` â†’ **10 passed** (new): trusted planet longitudes/cusps/ascendant match `compute_ephemeris` output to 1e-9 on the fixture_01 input; old engine monkeypatched-to-raise proves it is never called; payload (minus `metadata`) parses through `ChartData`; envelope, 401, cache-HIT passthrough preserved; 400 LAT_UNSUPPORTED and 422 INVALID_TIMEZONE asserted. Geocoding and Supabase mocked; chart math real.
- `... tests/ -q` â†’ **121 passed** (everything).
**Cache flush â€” YES, required:** pre-fix `user_charts` rows were computed by the deprecated engine AND stored in the old payload shape, while the fingerprint inputs (incl. `engine_version` "1.0.0") are unchanged â€” so old rows will cache-HIT and serve stale wrong charts in the old shape. Execute D013: flush all rows predating this merge (they regenerate on demand), or alternatively set `CHART_ENGINE_VERSION` env to e.g. `1.1.0` in Azure so old fingerprints simply never match again (config reads it via pydantic-settings; no code change). Flush is the cleaner, already-mandated path.
**Files changed:** `backend/app/routers/chart.py` (rewired), `backend/app/core/chart_engine.py` (deprecation header only), `tests/test_chart_route.py` (new), `HANDOFF.md`. main.py, Dockerfile, schemas, engine math, fixture expected values: untouched.
**Known issues / deferred:** Azure deploy intentionally NOT run (stop condition); scaffold page planet table degraded until T2.5; `backend/scripts/test_chart.py` still imports the deprecated module (standalone script, not a route â€” retire it with the module).
**Next agent should read:** `backend/app/routers/chart.py`, `tests/test_chart_route.py`, this entry (cache-flush section) before the v1.1.0 image build.
**Tempted but did not:** edit `app/core/db.py` to drop the `metadata` coupling (not in scope); bump `chart_engine_version` default in `config.py` (founder's call between flush vs version bump); delete `app/core/chart_engine.py` outright (scripts still reference it).

## T1.2-prod-health - agent/codex/day1-ephe-prod-health - 2026-06-11 20:01 - Codex
**Built:** tightened `/health` to call `app.engines.ephemeris_engine.ephemeris_files_ok`, report the configured `SE_EPHE_PATH` and `.se1` count, and degrade safely when files are absent. Updated Docker packaging so production images copy local build-context Swiss `.se1` files from `backend/ephe/` into `/app/ephe`, with `SE_EPHE_PATH=/app/ephe`.
**Deployment decision:** do not commit Swiss `.se1` binaries to git. Use a deploy-time local copy: place founder-approved files in git-ignored `backend/ephe/`, then build the backend image from `backend/`; Dockerfile now fails loudly if `ephe/*.se1` is missing.
**Remaining production command steps:**
- From repo root: `New-Item -ItemType Directory -Force backend/ephe`
- Copy local ephemeris files: `Copy-Item C:\Users\assas\swisseph\ephe\*.se1 backend\ephe\`
- From `backend/`: build/tag/push the backend image using the normal GHCR deploy ritual.
- After Azure revision update, hit `/health` and confirm `checks.ephemeris.status == "ok"` and the detail shows `.se1 file(s) at /app/ephe`.
**Files changed:**
- `.gitignore`
- `backend/Dockerfile`
- `backend/app/main.py`
- `docs/ephemeris.md`
- `docs/health.md`
- `tests/test_health.py`
- `HANDOFF.md`
**Tests run:**
- `uv run --with-requirements backend/requirements.txt --with pytest python -m pytest tests/test_health.py -q` -> 5 passed, 2 warnings.
- `$env:SE_EPHE_PATH='C:\Users\assas\swisseph\ephe'; uv run --with-requirements backend/requirements.txt --with pytest python -m pytest tests/test_schema_roundtrip.py tests/test_health.py tests/test_ephemeris.py -q` -> 111 passed, 2 warnings.
**Known issues / deferred:** deployment to Azure was intentionally not run. `backend/ephe/` is ignored, so production builds require the explicit local copy step before `docker build`.
**Next agent should read:** `backend/Dockerfile`, `docs/ephemeris.md`, `docs/health.md`, `backend/app/main.py`, this handoff entry.
**Tempted but did not:** commit `.se1` files, edit `backend/app/engines/ephemeris_engine.py`, change fixture values, wire the chart route, or touch deployment scripts.

## T1.3/T1.1 (Option B: TRUEPOS) â€” agent/claude/day1-jhora-fixtures â€” 2026-06-11 19:45 â€” Claude Code
**Built:** executed the founder's **Option B ruling** on the apparent-vs-true finding (entry below): JHora Drik + KP/Krishnamoorthy stays the judge; the engine now matches its TRUE/geometric output. (1) `docs/ephemeris.md` Â§2 and Â§5 amended â€” `swe.FLG_TRUEPOS` is mandatory on every position call, with the failure signature documented. (2) `_CALC_FLAGS` in `backend/app/engines/ephemeris_engine.py` now includes `swe.FLG_TRUEPOS` (one-line change plus comment). (3) `fixture_05_southern.json` expected values replaced with the founder's corrected re-export (+11:00 East of GMT; the first export had the timezone sign flipped). Fixtures 1â€“4 values untouched. No fixture carries `PENDING_JHORA` anymore; all have fully populated expectations.
**Files changed:** `backend/app/engines/ephemeris_engine.py`, `docs/ephemeris.md`, `tests/fixtures/charts/fixture_01..05` (01â€“04 from the previous entry's working-tree state, 05 re-exported), `HANDOFF.md`. Uncommitted â€” Rule 9, suite not fully green yet.
**Tests run:**
- `uv run --with-requirements backend/requirements.txt --with pytest python -m pytest tests/test_ephemeris.py -q` â†’ **8 failed, 80 passed**.
- Full Day 1 suite (schema + health + ephemeris) â†’ **8 failed, 102 passed**.
**Result of TRUEPOS:** Sun now matches to â‰¤0.85", Moon to â‰¤2.04", every other planet â‰¤~1" â€” on ALL five charts. All 60 cusps within 16.7" (tolerance 36"), all five ascendant signs exact. The corrected fixture_05 confirms the earlier timezone-sign diagnosis (asc Aries, cusp 1 diff 12"). **fixture_02 passes 100%.**
**Remaining failure â€” Rahu/Ketu ONLY, exactly as anticipated:**
| fixture | engine Rahu | JHora Rahu | diff |
|---|---|---|---|
| 01_india | 211.703178 | 211.705150 | 7.10" |
| 02_us_dst | 23.090011 | 23.090036 | 0.09" PASS |
| 03_midnight | 81.744515 | 81.746425 | 6.88" |
| 04_pre1990 | 114.800041 | 114.803239 | 11.51" |
| 05_southern | 276.046652 | 276.051369 | 16.98" |
(Ketu identical by construction.) The 8 failures are `test_jhora_planet_longitudes` + `test_jhora_rahu_explicit` on fixtures 01/03/04/05, all driven solely by the node. Node model NOT changed, tolerance NOT changed, per instruction.
**Likely cause / next step:** this machine has **no `.se1` files** â€” all computation runs on the Moshier fallback. The osculating (true) node is highly sensitive to lunar ephemeris precision, so Moshier's small lunar error can plausibly produce exactly this 0â€“17" chart-dependent node scatter. **Re-run after real Swiss `.se1` files are installed at `SE_EPHE_PATH` (T1.2 left `/app/ephe` empty too) before considering any node-model investigation.** If the residual persists with real files, compare JHora's node option (true node settings) against `swe.TRUE_NODE` â€” founder decision, not an agent guess.
**Next agent should read:** this entry, `backend/app/engines/ephemeris_engine.py` (`_CALC_FLAGS`), `docs/ephemeris.md` Â§Â§2, 5, `tests/fixtures/charts/*.json`.
**Tempted but did not:** download `.se1` files (no authorized location in the repo; Dockerfile/ephe baking is Codex's lane); widen the 5" tolerance for nodes; special-case the node calculation.

## T1.3/T1.1 (JHora fixtures) â€” agent/claude/day1-jhora-fixtures â€” 2026-06-11 18:30 â€” Claude Code â€” **BLOCKED**
**Built:** all five `tests/fixtures/charts/*.json` filled with the founder's JHora exports (Drik Siddhanta, KP/Krishnamoorthy ayanamsa, JHora house Start/Cusp/End table). `status: PENDING_JHORA` removed, `source` updated, `input` blocks untouched. The 20 pending comparisons now execute. JHora values were NOT adjusted to match engine output (Rule 8); failures are reported exactly.
**Files changed:** the five fixture JSONs + `HANDOFF.md`. **Uncommitted** â€” Rule 9 says commit only when tests pass, and the comparison tests currently fail pending the founder's ruling below.
**Tests run:**
- `uv run --with-requirements backend/requirements.txt --with pytest python -m pytest tests/test_ephemeris.py -q` â†’ **11 failed, 77 passed**.
- Full Day 1 suite (`tests/test_schema_roundtrip.py tests/test_health.py tests/test_ephemeris.py`) â†’ **11 failed, 99 passed** (schema + health fully green; failures are exclusively JHora comparisons).
**Failure analysis (two distinct root causes, both diagnosed):**
1. **Fixtures 1â€“4 â€” engine computes APPARENT positions, JHora exports TRUE (geometric) positions.** All cusps pass (â‰¤17 arc-sec), all ascendant signs pass, and the **Moon passes on every chart (â‰¤1.3 arc-sec)** â€” so ayanamsa, timezone handling, and Placidus math all match. But Sun is off by ~20 arc-sec on every chart (the annual-aberration signature) and the other planets by 7â€“47 arc-sec with retrograde-dependent sign. Diagnostic recomputation with `swe.FLG_TRUEPOS` (no light-time/aberration) makes **every planet on fixtures 1 and 4 pass at â‰¤2 arc-sec**. JHora's Drik Siddhanta exports true geometric positions; the Swiss default is apparent. The fix is a one-flag engine change (`_CALC_FLAGS |= swe.FLG_TRUEPOS`), but the engine file is outside this task's allowed list and docs/ephemeris.md Â§5 currently specifies plain `FLG_SWIEPH | FLG_SIDEREAL | FLG_SPEED`.
2. **Fixture_05 (Sydney) â€” the JHora chart was cast with the timezone sign flipped.** Engine UTC is 1990-11-23T06:20Z (17:20 AEDT = UTC+11). The JHora export matches the engine recomputed at **1990-11-24T04:20Z** â€” i.e. 17:20 with an 11-hour WEST offset â€” with exactly the same residual pattern as fixtures 1â€“4 (asc Pisces, cusps â‰¤12.3 arc-sec, Moon 0.86 arc-sec). The fixture_05 export is invalid for the stated input and must be re-cast in JHora with the east offset (+11:00 AEDT; mind JHora's east/west sign convention) and re-exported.
3. **Open residual: Rahu/Ketu off by 7â€“17 arc-sec even under TRUEPOS** (passes only fixture_02 at 0.09 arc-sec; the true node oscillates). May shrink with real `.se1` files â€” local runs are on Moshier fallback (no `.se1` on this machine) and the osculating node is sensitive to lunar ephemeris precision â€” or may be a JHora node-model difference. Re-test after files land before concluding.
**Known issues / deferred:** changes uncommitted pending the ruling; `docs/reference-settings.png` not provided, not added; no engine, route, schema, Dockerfile, or frontend changes.
**Next agent should read:** this entry, `tests/fixtures/charts/*.json` (working tree), `backend/app/engines/ephemeris_engine.py` (`_CALC_FLAGS`), `docs/ephemeris.md` Â§Â§5, 9, 11.
**Tempted but did not:** add `FLG_TRUEPOS` to the engine (outside allowed list, spec change required); "fix" fixture_05's expected values myself (founder owns expectation values).
**Question (BLOCKED):** true vs apparent positions â€” which is the product convention? Option A: set JHora to apparent/observed positions and re-export all 5 charts (engine unchanged). Option B: amend docs/ephemeris.md Â§5 to add `FLG_TRUEPOS` and authorize the one-line engine change in a follow-up task (JHora stays as configured). Either way, fixture_05 must be re-cast with the correct +11:00 east offset. D002 names JHora as the judge, which suggests Option B, but the spec edit is yours to make.

## T1.1 (correction) â€” agent/claude/day1-ephemeris â€” 2026-06-11 17:10 â€” Claude Code
**Built:** path correction to the T1.1 entry below, after the Codex contract merge. The running backend uses the `backend/app/` package, so the ephemeris engine moved from `backend/engines/ephemeris_engine.py` to **`backend/app/engines/ephemeris_engine.py`** (git mv, content unchanged), with a new `backend/app/engines/__init__.py`. This is the namespace the upgraded `/health` in `backend/app/main.py` actually resolves in the container (`app.engines.ephemeris_engine` under WORKDIR /app); verified by importing from `backend/` and calling `ephemeris_files_ok()` â€” returns False locally because `SE_EPHE_PATH` is unset on the dev machine, which is the correct degraded behavior (the Dockerfile sets `/app/ephe` for prod but `.se1` files are still not baked in; see T1.2 known issues).
**Files changed:** `backend/engines/ephemeris_engine.py` â†’ `backend/app/engines/ephemeris_engine.py` (renamed, content unchanged), `backend/app/engines/__init__.py` (new), `tests/test_ephemeris.py` (import path only), `HANDOFF.md`. Nothing else; old `backend/engines/` directory removed.
**Tests run:** `uv run --with-requirements backend/requirements.txt --with pytest python -m pytest tests/test_ephemeris.py -q` â†’ **68 passed, 20 skipped** (unchanged; all 20 skips remain the JHora comparison tests, reason `PENDING_JHORA_VALUES`).
**Known issues / deferred:** the chart route is NOT wired to the new engine yet â€” `/chart/generate` still calls `backend/app/core/chart_engine.py` (with its Alcabitius `b'B'` bug, see the T1.1 entry below); wiring is a separate task, not started here. Where the T1.1 entry below says `backend/engines/...`, read `backend/app/engines/...`.
**Next agent should read:** `backend/app/engines/ephemeris_engine.py`, `tests/test_ephemeris.py`, the original T1.1 entry below for full implementation detail.
**Tempted but did not:** wire `backend/app/routers/chart.py` to the new engine; trim the now-redundant fallback names in `backend/app/main.py`'s ephemeris import-probe list.

## T1.2 - agent/codex/day1-schema-health - 2026-06-11 16:27 - Codex
**Built:** Day 1 chart contract in `backend/app/schemas/models.py`, generated `schemas/chart.json`, upgraded inline `/health` with ephemeris/database subchecks, documented `docs/health.md`, set Docker ephemeris env/path, and added focused schema + health tests.
**Repo structure discovered:** FastAPI entrypoint is `backend/app/main.py`; schemas live under `backend/app/schemas/`; Dockerfile is `backend/Dockerfile`; existing health was inline in `main.py`; no root `schemas/` folder existed before this task.
**Files changed:**
- `backend/app/schemas/models.py`
- `schemas/chart.json`
- `backend/app/main.py`
- `backend/Dockerfile`
- `tests/test_schema_roundtrip.py`
- `tests/test_health.py`
- `docs/health.md`
- `HANDOFF.md`
**Tests run:**
- `uv run --with-requirements backend/requirements.txt --with pytest python -m pytest tests/test_schema_roundtrip.py tests/test_health.py -q` -> 22 passed, 2 warnings. Used `uv` because `python` is not on PATH and the bundled Python lacked pytest/FastAPI/Supabase.
- `git diff --name-only` -> tracked changes in `backend/Dockerfile`, `backend/app/main.py`, `backend/app/schemas/models.py`; `git status --short` also shows approved new `docs/health.md`, `schemas/chart.json`, and tests.
**Known issues / deferred:**
- No `.se1` files were found in the repo, so `backend/Dockerfile` creates `/app/ephe` and sets `SE_EPHE_PATH=/app/ephe` but does not copy ephemeris files.
- `backend.engines.ephemeris_engine` / `app.engines.ephemeris_engine` does not exist yet; `/health` degrades safely for ephemeris until the engine lane provides `ephemeris_files_ok`.
- Database health intentionally avoids real Supabase credentials or network calls; it reports initialized/skipped/degraded from the existing app client pattern.
**Intentionally not built:** ephemeris math, KP, dasha, scoring, frontend wiring, RAG, Supabase DDL/client changes, deployment scripts, or any engine files.
**Next agent should read:** `docs/chart-schema.md`, `docs/health.md`, `backend/app/schemas/models.py`, `backend/app/main.py`, `backend/Dockerfile`.
**Tempted but did not:** change `backend/app/core/config.py` to make imports friendlier without env vars; move health into a new router; add a root Dockerfile; add real `.se1` files; touch `backend/app/core/chart_engine.py`.
## T1.1 â€” agent/claude/day1-ephemeris â€” 2026-06-11 16:00 â€” Claude Code
**Built:** `backend/engines/ephemeris_engine.py` as the single trusted Day 1 chart-math source per docs/ephemeris.md: KP-Newcomb sidereal positions for the 9 fixed bodies, TRUE_NODE Rahu with derived Ketu, Placidus sidereal cusps + ascendant via `swe.houses_ex`, combustion flags per the spec Â§6 orb table, single localâ†’UTC conversion via zoneinfo at the engine boundary, structured errors (`LAT_UNSUPPORTED`, `INVALID_TIMEZONE`, `INVALID_COORDINATES`, `INVALID_DATETIME`), and `ephemeris_files_ok()` / `ephemeris_files_status()` for /health.
**Files changed:** `backend/engines/ephemeris_engine.py` (new), `tests/test_ephemeris.py` (new), `tests/fixtures/charts/fixture_01_india.json` â€¦ `fixture_05_southern.json` (new, all `PENDING_JHORA`), `HANDOFF.md`. Nothing outside the allowed list (`git diff --name-only` verified; `scripts/check_allowed_files.py` does not exist yet, so the git check stands in).
**Existing chart code found and reused:** `backend/app/core/chart_engine.py` already had SIDM_KRISHNAMURTI, TRUE_NODE Rahu, Ketu = Rahu+180, and the sign tables â€” those conventions were kept. Its tropical-minus-ayanamsa arithmetic was replaced with `FLG_SIDEREAL`, and its house call had a real bug: it passes `b'B'` (**Alcabitius**) to `swe.houses_ex` while the comment claims Placidus, and never returns cusps. The new engine uses `b'P'`. Timezone conversion pattern from `backend/app/utils/geocode.py:convert_local_to_utc` was sound (single conversion) and now lives inside the engine per spec Â§4.
**What was implemented:** everything in docs/ephemeris.md Â§Â§2â€“7 plus the file guard: locked init order (set_ephe_path â†’ set_sid_mode before any calc, re-applied at every entry); 9 planets in fixed order with longitude/sign/sign_lord/sign_degree/retrograde/speed; combustion per the Â§6 orb table (rules ARE clearly defined there, so combust is computed, not stubbed false â€” Sun/Rahu/Ketu never combust, Mercury/Venus use tighter retro orbs); 12 normalized Placidus cusps (pyswisseph 2.10.3.2 verified in REPL: `houses_ex` returns `(cusps, ascmc)` with cusps as a 0-indexed 12-tuple, ascmc[0] = ascendant = cusp 1); fold=0 for ambiguous DST times per D012(e); `|lat| > 66` â†’ structured `LatUnsupportedError`; `ephemeris_files_status()` checks env var â†’ path â†’ `.se1` presence â†’ a Swiss-vs-Moshier probe (retflag carries FLG_MOSEPH on silent fallback) and never raises.
**What was intentionally NOT implemented:** nakshatra/pada, KP sublords, house occupancy, dashas, strength, divisional, transits (later engines own those chart.json fields); pydantic `EphemerisResult` (backend/schemas/models.py is Codex's T1.2 and does not exist yet â€” engine returns plain dicts whose keys match chart.json v1.0 field names 1:1, so the spec Â§10 schema round-trip test is deferred to after T1.2 merges); 4-decimal rounding (serialization layer's job; engine keeps full precision); API wiring of the new engine (the live `/chart/generate` still calls the old `chart_engine.py`).
**Tests run:** `python -m pytest tests/test_ephemeris.py -q` â†’ **68 passed, 20 skipped** (all 20 skips are the 4 JHora comparison tests Ã— 5 fixtures, reason `PENDING_JHORA_VALUES`). Pytest ran from a local gitignored `.venv` with the pinned `pyswisseph==2.10.3.2` (pytest is not in requirements.txt and was not added, per Rule 5).
**Pending JHora fixture status:** all 5 fixtures in `tests/fixtures/charts/` carry `"status": "PENDING_JHORA"` with null expectations. When T1.3 supplies real values, replace `expected.planets` / `expected.cusps` / `expected.ascendant_sign` and remove the status field; the comparison tests pick them up automatically (5 arc-sec planets, 0.01Â° cusps, exact ascendant sign).
**Known issues / deferred:**
- **No `.se1` files exist on this machine** â€” local computation runs on Moshier fallback. `julian_day_ut` for the spec's worked example matches exactly (2449432.87847), but the Moon may sit outside 5 arc-sec of JHora until real Swiss files are at `SE_EPHE_PATH`. The Dockerfile `/app/ephe` bake is Codex's T1.2; afternoon validation needs the files locally too.
- `ephemeris_files_ok()` correctly returns False in this environment (`SE_EPHE_PATH` unset). /health should report degraded, not failing.
- Old `backend/app/core/chart_engine.py` is still the production path with the Alcabitius bug and no ephe-path guard â€” every cached chart it produced is suspect (supports D013 flush).
**Next agent should read:** `backend/engines/ephemeris_engine.py` (docstrings state shapes and conventions), `tests/test_ephemeris.py` (the harness), `tests/fixtures/charts/*.json` (fill expectations here), `docs/ephemeris.md` Â§Â§9â€“10 (tolerances).
**Tempted but did not:** fix the `b'B'` Alcabitius bug in `backend/app/core/chart_engine.py` (outside allowed list; flagged above instead); add a root `conftest.py` for sys.path (not in allowed list â€” the test file bootstraps its own path); add pytest to `requirements.txt`.

## T0.0 â€” (no branch, pre-sprint state) â€” 2026-06-11 08:30 â€” founder
**Built:** seed entry recording the June 10 state so every agent session inherits the same truth. Backend (FastAPI) live on Azure Container Apps with `/health` (minimal 3-field version) and `/chart/generate` (body: birth_date, birth_time, birth_city; header `X-User-Id`); Supabase `user_charts` caching proven MISSâ†’HIT; image `ghcr.io/pratyus-saha/askjunopath-backend:v1.0.0` (public package); Next.js frontend live on Vercel via CLI with `/` and `/chart`.
**Files changed:** n/a (state record).
**Tests run:** none exist yet; that is the point of today.
**Known issues / deferred:**
- Chart math UNVALIDATED against reference software; treat all existing chart output as untrusted (PROJECT_CONTEXT.md Â§3).
- Placidus cusps and houses NOT computed anywhere yet.
- `SE_EPHE_PATH` / `.se1` files never mentioned in the June 10 work; production may be running Moshier-fallback ephemeris. First check of today's afternoon block (TASKBOARD T1.5, DECISIONS D013).
- `user_charts` rows created before today's validation are suspect; diff-then-flush procedure pending (D013).
- A GitHub PAT was exposed in a terminal screenshot on June 10; revocation is task T1.0 and must be confirmed in the next entry.
- Supabase column is `chart_json`, not `chart` (already fixed once; do not regress).
- CORS unhardened; rate limits absent; both scheduled June 21.
**Next agent should read:** docs/PROJECT_CONTEXT.md, AGENTS.md, then your task's spec doc per TASKBOARD.md.
**Tempted but did not:** n/a.

