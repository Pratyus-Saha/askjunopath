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
## <Task ID> — <branch> — <YYYY-MM-DD HH:MM> — <agent>
**Built:** one or two sentences, plain language.
**Files changed:** list (must match the allowed list; the guard script output goes here if it flagged anything).
**Tests run:** exact command + result (e.g., `pytest tests/test_ephemeris.py -q` → 14 passed, 2 skipped PENDING_JHORA).
**Known issues / deferred:** list, or "none".
**Next agent should read:** files, or "n/a".
**Tempted but did not:** anything you wanted to change outside scope (this line catches scope pressure before it becomes scope creep).
**Question (only if BLOCKED):** one specific question, then stop.
```

---

# Entries

## T1.3/T1.1 (Option B: TRUEPOS) — agent/claude/day1-jhora-fixtures — 2026-06-11 19:45 — Claude Code
**Built:** executed the founder's **Option B ruling** on the apparent-vs-true finding (entry below): JHora Drik + KP/Krishnamoorthy stays the judge; the engine now matches its TRUE/geometric output. (1) `docs/ephemeris.md` §2 and §5 amended — `swe.FLG_TRUEPOS` is mandatory on every position call, with the failure signature documented. (2) `_CALC_FLAGS` in `backend/app/engines/ephemeris_engine.py` now includes `swe.FLG_TRUEPOS` (one-line change plus comment). (3) `fixture_05_southern.json` expected values replaced with the founder's corrected re-export (+11:00 East of GMT; the first export had the timezone sign flipped). Fixtures 1–4 values untouched. No fixture carries `PENDING_JHORA` anymore; all have fully populated expectations.
**Files changed:** `backend/app/engines/ephemeris_engine.py`, `docs/ephemeris.md`, `tests/fixtures/charts/fixture_01..05` (01–04 from the previous entry's working-tree state, 05 re-exported), `HANDOFF.md`. Uncommitted — Rule 9, suite not fully green yet.
**Tests run:**
- `uv run --with-requirements backend/requirements.txt --with pytest python -m pytest tests/test_ephemeris.py -q` → **8 failed, 80 passed**.
- Full Day 1 suite (schema + health + ephemeris) → **8 failed, 102 passed**.
**Result of TRUEPOS:** Sun now matches to ≤0.85", Moon to ≤2.04", every other planet ≤~1" — on ALL five charts. All 60 cusps within 16.7" (tolerance 36"), all five ascendant signs exact. The corrected fixture_05 confirms the earlier timezone-sign diagnosis (asc Aries, cusp 1 diff 12"). **fixture_02 passes 100%.**
**Remaining failure — Rahu/Ketu ONLY, exactly as anticipated:**
| fixture | engine Rahu | JHora Rahu | diff |
|---|---|---|---|
| 01_india | 211.703178 | 211.705150 | 7.10" |
| 02_us_dst | 23.090011 | 23.090036 | 0.09" PASS |
| 03_midnight | 81.744515 | 81.746425 | 6.88" |
| 04_pre1990 | 114.800041 | 114.803239 | 11.51" |
| 05_southern | 276.046652 | 276.051369 | 16.98" |
(Ketu identical by construction.) The 8 failures are `test_jhora_planet_longitudes` + `test_jhora_rahu_explicit` on fixtures 01/03/04/05, all driven solely by the node. Node model NOT changed, tolerance NOT changed, per instruction.
**Likely cause / next step:** this machine has **no `.se1` files** — all computation runs on the Moshier fallback. The osculating (true) node is highly sensitive to lunar ephemeris precision, so Moshier's small lunar error can plausibly produce exactly this 0–17" chart-dependent node scatter. **Re-run after real Swiss `.se1` files are installed at `SE_EPHE_PATH` (T1.2 left `/app/ephe` empty too) before considering any node-model investigation.** If the residual persists with real files, compare JHora's node option (true node settings) against `swe.TRUE_NODE` — founder decision, not an agent guess.
**Next agent should read:** this entry, `backend/app/engines/ephemeris_engine.py` (`_CALC_FLAGS`), `docs/ephemeris.md` §§2, 5, `tests/fixtures/charts/*.json`.
**Tempted but did not:** download `.se1` files (no authorized location in the repo; Dockerfile/ephe baking is Codex's lane); widen the 5" tolerance for nodes; special-case the node calculation.

## T1.3/T1.1 (JHora fixtures) — agent/claude/day1-jhora-fixtures — 2026-06-11 18:30 — Claude Code — **BLOCKED**
**Built:** all five `tests/fixtures/charts/*.json` filled with the founder's JHora exports (Drik Siddhanta, KP/Krishnamoorthy ayanamsa, JHora house Start/Cusp/End table). `status: PENDING_JHORA` removed, `source` updated, `input` blocks untouched. The 20 pending comparisons now execute. JHora values were NOT adjusted to match engine output (Rule 8); failures are reported exactly.
**Files changed:** the five fixture JSONs + `HANDOFF.md`. **Uncommitted** — Rule 9 says commit only when tests pass, and the comparison tests currently fail pending the founder's ruling below.
**Tests run:**
- `uv run --with-requirements backend/requirements.txt --with pytest python -m pytest tests/test_ephemeris.py -q` → **11 failed, 77 passed**.
- Full Day 1 suite (`tests/test_schema_roundtrip.py tests/test_health.py tests/test_ephemeris.py`) → **11 failed, 99 passed** (schema + health fully green; failures are exclusively JHora comparisons).
**Failure analysis (two distinct root causes, both diagnosed):**
1. **Fixtures 1–4 — engine computes APPARENT positions, JHora exports TRUE (geometric) positions.** All cusps pass (≤17 arc-sec), all ascendant signs pass, and the **Moon passes on every chart (≤1.3 arc-sec)** — so ayanamsa, timezone handling, and Placidus math all match. But Sun is off by ~20 arc-sec on every chart (the annual-aberration signature) and the other planets by 7–47 arc-sec with retrograde-dependent sign. Diagnostic recomputation with `swe.FLG_TRUEPOS` (no light-time/aberration) makes **every planet on fixtures 1 and 4 pass at ≤2 arc-sec**. JHora's Drik Siddhanta exports true geometric positions; the Swiss default is apparent. The fix is a one-flag engine change (`_CALC_FLAGS |= swe.FLG_TRUEPOS`), but the engine file is outside this task's allowed list and docs/ephemeris.md §5 currently specifies plain `FLG_SWIEPH | FLG_SIDEREAL | FLG_SPEED`.
2. **Fixture_05 (Sydney) — the JHora chart was cast with the timezone sign flipped.** Engine UTC is 1990-11-23T06:20Z (17:20 AEDT = UTC+11). The JHora export matches the engine recomputed at **1990-11-24T04:20Z** — i.e. 17:20 with an 11-hour WEST offset — with exactly the same residual pattern as fixtures 1–4 (asc Pisces, cusps ≤12.3 arc-sec, Moon 0.86 arc-sec). The fixture_05 export is invalid for the stated input and must be re-cast in JHora with the east offset (+11:00 AEDT; mind JHora's east/west sign convention) and re-exported.
3. **Open residual: Rahu/Ketu off by 7–17 arc-sec even under TRUEPOS** (passes only fixture_02 at 0.09 arc-sec; the true node oscillates). May shrink with real `.se1` files — local runs are on Moshier fallback (no `.se1` on this machine) and the osculating node is sensitive to lunar ephemeris precision — or may be a JHora node-model difference. Re-test after files land before concluding.
**Known issues / deferred:** changes uncommitted pending the ruling; `docs/reference-settings.png` not provided, not added; no engine, route, schema, Dockerfile, or frontend changes.
**Next agent should read:** this entry, `tests/fixtures/charts/*.json` (working tree), `backend/app/engines/ephemeris_engine.py` (`_CALC_FLAGS`), `docs/ephemeris.md` §§5, 9, 11.
**Tempted but did not:** add `FLG_TRUEPOS` to the engine (outside allowed list, spec change required); "fix" fixture_05's expected values myself (founder owns expectation values).
**Question (BLOCKED):** true vs apparent positions — which is the product convention? Option A: set JHora to apparent/observed positions and re-export all 5 charts (engine unchanged). Option B: amend docs/ephemeris.md §5 to add `FLG_TRUEPOS` and authorize the one-line engine change in a follow-up task (JHora stays as configured). Either way, fixture_05 must be re-cast with the correct +11:00 east offset. D002 names JHora as the judge, which suggests Option B, but the spec edit is yours to make.

## T1.1 (correction) — agent/claude/day1-ephemeris — 2026-06-11 17:10 — Claude Code
**Built:** path correction to the T1.1 entry below, after the Codex contract merge. The running backend uses the `backend/app/` package, so the ephemeris engine moved from `backend/engines/ephemeris_engine.py` to **`backend/app/engines/ephemeris_engine.py`** (git mv, content unchanged), with a new `backend/app/engines/__init__.py`. This is the namespace the upgraded `/health` in `backend/app/main.py` actually resolves in the container (`app.engines.ephemeris_engine` under WORKDIR /app); verified by importing from `backend/` and calling `ephemeris_files_ok()` — returns False locally because `SE_EPHE_PATH` is unset on the dev machine, which is the correct degraded behavior (the Dockerfile sets `/app/ephe` for prod but `.se1` files are still not baked in; see T1.2 known issues).
**Files changed:** `backend/engines/ephemeris_engine.py` → `backend/app/engines/ephemeris_engine.py` (renamed, content unchanged), `backend/app/engines/__init__.py` (new), `tests/test_ephemeris.py` (import path only), `HANDOFF.md`. Nothing else; old `backend/engines/` directory removed.
**Tests run:** `uv run --with-requirements backend/requirements.txt --with pytest python -m pytest tests/test_ephemeris.py -q` → **68 passed, 20 skipped** (unchanged; all 20 skips remain the JHora comparison tests, reason `PENDING_JHORA_VALUES`).
**Known issues / deferred:** the chart route is NOT wired to the new engine yet — `/chart/generate` still calls `backend/app/core/chart_engine.py` (with its Alcabitius `b'B'` bug, see the T1.1 entry below); wiring is a separate task, not started here. Where the T1.1 entry below says `backend/engines/...`, read `backend/app/engines/...`.
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
## T1.1 — agent/claude/day1-ephemeris — 2026-06-11 16:00 — Claude Code
**Built:** `backend/engines/ephemeris_engine.py` as the single trusted Day 1 chart-math source per docs/ephemeris.md: KP-Newcomb sidereal positions for the 9 fixed bodies, TRUE_NODE Rahu with derived Ketu, Placidus sidereal cusps + ascendant via `swe.houses_ex`, combustion flags per the spec §6 orb table, single local→UTC conversion via zoneinfo at the engine boundary, structured errors (`LAT_UNSUPPORTED`, `INVALID_TIMEZONE`, `INVALID_COORDINATES`, `INVALID_DATETIME`), and `ephemeris_files_ok()` / `ephemeris_files_status()` for /health.
**Files changed:** `backend/engines/ephemeris_engine.py` (new), `tests/test_ephemeris.py` (new), `tests/fixtures/charts/fixture_01_india.json` … `fixture_05_southern.json` (new, all `PENDING_JHORA`), `HANDOFF.md`. Nothing outside the allowed list (`git diff --name-only` verified; `scripts/check_allowed_files.py` does not exist yet, so the git check stands in).
**Existing chart code found and reused:** `backend/app/core/chart_engine.py` already had SIDM_KRISHNAMURTI, TRUE_NODE Rahu, Ketu = Rahu+180, and the sign tables — those conventions were kept. Its tropical-minus-ayanamsa arithmetic was replaced with `FLG_SIDEREAL`, and its house call had a real bug: it passes `b'B'` (**Alcabitius**) to `swe.houses_ex` while the comment claims Placidus, and never returns cusps. The new engine uses `b'P'`. Timezone conversion pattern from `backend/app/utils/geocode.py:convert_local_to_utc` was sound (single conversion) and now lives inside the engine per spec §4.
**What was implemented:** everything in docs/ephemeris.md §§2–7 plus the file guard: locked init order (set_ephe_path → set_sid_mode before any calc, re-applied at every entry); 9 planets in fixed order with longitude/sign/sign_lord/sign_degree/retrograde/speed; combustion per the §6 orb table (rules ARE clearly defined there, so combust is computed, not stubbed false — Sun/Rahu/Ketu never combust, Mercury/Venus use tighter retro orbs); 12 normalized Placidus cusps (pyswisseph 2.10.3.2 verified in REPL: `houses_ex` returns `(cusps, ascmc)` with cusps as a 0-indexed 12-tuple, ascmc[0] = ascendant = cusp 1); fold=0 for ambiguous DST times per D012(e); `|lat| > 66` → structured `LatUnsupportedError`; `ephemeris_files_status()` checks env var → path → `.se1` presence → a Swiss-vs-Moshier probe (retflag carries FLG_MOSEPH on silent fallback) and never raises.
**What was intentionally NOT implemented:** nakshatra/pada, KP sublords, house occupancy, dashas, strength, divisional, transits (later engines own those chart.json fields); pydantic `EphemerisResult` (backend/schemas/models.py is Codex's T1.2 and does not exist yet — engine returns plain dicts whose keys match chart.json v1.0 field names 1:1, so the spec §10 schema round-trip test is deferred to after T1.2 merges); 4-decimal rounding (serialization layer's job; engine keeps full precision); API wiring of the new engine (the live `/chart/generate` still calls the old `chart_engine.py`).
**Tests run:** `python -m pytest tests/test_ephemeris.py -q` → **68 passed, 20 skipped** (all 20 skips are the 4 JHora comparison tests × 5 fixtures, reason `PENDING_JHORA_VALUES`). Pytest ran from a local gitignored `.venv` with the pinned `pyswisseph==2.10.3.2` (pytest is not in requirements.txt and was not added, per Rule 5).
**Pending JHora fixture status:** all 5 fixtures in `tests/fixtures/charts/` carry `"status": "PENDING_JHORA"` with null expectations. When T1.3 supplies real values, replace `expected.planets` / `expected.cusps` / `expected.ascendant_sign` and remove the status field; the comparison tests pick them up automatically (5 arc-sec planets, 0.01° cusps, exact ascendant sign).
**Known issues / deferred:**
- **No `.se1` files exist on this machine** — local computation runs on Moshier fallback. `julian_day_ut` for the spec's worked example matches exactly (2449432.87847), but the Moon may sit outside 5 arc-sec of JHora until real Swiss files are at `SE_EPHE_PATH`. The Dockerfile `/app/ephe` bake is Codex's T1.2; afternoon validation needs the files locally too.
- `ephemeris_files_ok()` correctly returns False in this environment (`SE_EPHE_PATH` unset). /health should report degraded, not failing.
- Old `backend/app/core/chart_engine.py` is still the production path with the Alcabitius bug and no ephe-path guard — every cached chart it produced is suspect (supports D013 flush).
**Next agent should read:** `backend/engines/ephemeris_engine.py` (docstrings state shapes and conventions), `tests/test_ephemeris.py` (the harness), `tests/fixtures/charts/*.json` (fill expectations here), `docs/ephemeris.md` §§9–10 (tolerances).
**Tempted but did not:** fix the `b'B'` Alcabitius bug in `backend/app/core/chart_engine.py` (outside allowed list; flagged above instead); add a root `conftest.py` for sys.path (not in allowed list — the test file bootstraps its own path); add pytest to `requirements.txt`.

## T0.0 — (no branch, pre-sprint state) — 2026-06-11 08:30 — founder
**Built:** seed entry recording the June 10 state so every agent session inherits the same truth. Backend (FastAPI) live on Azure Container Apps with `/health` (minimal 3-field version) and `/chart/generate` (body: birth_date, birth_time, birth_city; header `X-User-Id`); Supabase `user_charts` caching proven MISS→HIT; image `ghcr.io/pratyus-saha/askjunopath-backend:v1.0.0` (public package); Next.js frontend live on Vercel via CLI with `/` and `/chart`.
**Files changed:** n/a (state record).
**Tests run:** none exist yet; that is the point of today.
**Known issues / deferred:**
- Chart math UNVALIDATED against reference software; treat all existing chart output as untrusted (PROJECT_CONTEXT.md §3).
- Placidus cusps and houses NOT computed anywhere yet.
- `SE_EPHE_PATH` / `.se1` files never mentioned in the June 10 work; production may be running Moshier-fallback ephemeris. First check of today's afternoon block (TASKBOARD T1.5, DECISIONS D013).
- `user_charts` rows created before today's validation are suspect; diff-then-flush procedure pending (D013).
- A GitHub PAT was exposed in a terminal screenshot on June 10; revocation is task T1.0 and must be confirmed in the next entry.
- Supabase column is `chart_json`, not `chart` (already fixed once; do not regress).
- CORS unhardened; rate limits absent; both scheduled June 21.
**Next agent should read:** docs/PROJECT_CONTEXT.md, AGENTS.md, then your task's spec doc per TASKBOARD.md.
**Tempted but did not:** n/a.
