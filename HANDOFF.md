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
