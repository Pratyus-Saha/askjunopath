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

