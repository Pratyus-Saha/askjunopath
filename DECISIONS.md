# DECISIONS.md
**The decision register. Founder-only writes; every agent reads it at session start (after PROJECT_CONTEXT.md and AGENTS.md).**

How this file works: a decision gets an entry when it resolves an ambiguity, changes a plan, or pins a convention that more than one file depends on. Entries are never deleted; a reversed decision gets `Status: SUPERSEDED by Dxxx` and a new entry. If an agent's task conflicts with an entry here, the entry wins and the agent stops and asks. Each entry names its revisit trigger so "locked" never silently means "forgotten."

---

## D001 — Chart schema starts at v1.0 and freezes June 11
**Date:** 2026-06-11 · **Status:** LOCKED
**Decision:** `schemas/chart.json` v1.0 is tagged tonight. After the tag: no renames, no removals; new fields are additive and bump the version; `schema_version` is embedded in every stored chart.
**Reason:** engines, API, frontend fixtures, generated types, and the Gemini synthesis payload all consume one contract. A casual rename breaks four layers at once.
**Binds:** `backend/schemas/models.py`, `docs/chart-schema.md`, every engine, `scripts/gen_types.sh`.
**Revisit:** never for the freeze rule itself; version bumps follow the rule.

## D002 — Astrology settings locked
**Date:** 2026-06-11 · **Status:** LOCKED
**Decision:** Sidereal zodiac; KP-Newcomb/Krishnamurti ayanamsa (`swe.SIDM_KRISHNAMURTI`); true node only (Ketu = Rahu + 180°); Placidus houses; Vimshottari dasha with year = 365.25 days; Jagannatha Hora configured per `docs/reference-settings.png` is the judge.
**Reason:** KP sublord accuracy depends on the exact ayanamsa and node setting; a mismatch invalidates every validation at once.
**Binds:** every engine, every fixture, every validation block.
**Revisit:** never. Any task proposing a different setting is mis-specified.

## D003 — Agent workflow: worktrees, lanes, founder merges
**Date:** 2026-06-11 · **Status:** LOCKED
**Decision:** four Git worktrees (`-main` founder, `-claude`, `-codex`, `-antigravity`); one branch per task (`agent/<tool>/<topic>`); one writer per file (TASKBOARD.md is the registry); agents open PRs and stop; the founder is the only merge authority; merge order Codex contracts → Claude engines → Antigravity components.
**Reason:** prevents file conflicts, keeps main stable, makes agent damage structurally bounded.
**Binds:** AGENTS.md, TASKBOARD.md, daily workflow.
**Revisit:** post-launch if a second human joins.

## D004 — Frontend host is Vercel, deployed via CLI
**Date:** 2026-06-11 · **Status:** LOCKED for the sprint
**Decision:** the Next.js frontend lives on Vercel, deployed with `vercel --prod` from `frontend/`. The master plan's Azure Static Web Apps references are void. The broken Vercel UI import flow is not retried during the sprint.
**Reason:** Vercel CLI deployment is proven working as of June 10; the UI import produced 404s twice; migrating hosts mid-sprint buys nothing.
**Binds:** `scripts/deploy_frontend.sh`, CORS allowlist (D-/API contract §1), frontend CI (GitHub Action, since Vercel deploys are manual).
**Revisit:** week 1 post-launch — connect the Vercel project to Git properly for PR preview deployments; custom domain at the same time.

## D005 — Keep `user_charts` and the `chart_json` column
**Date:** 2026-06-11 · **Status:** LOCKED for the sprint
**Decision:** the existing Supabase table `user_charts` (with `chart_json`, `chart_fingerprint`, `user_id`, birth fields) stays as-is. The chart.json v1.0 object is stored inside `chart_json` with `schema_version` embedded. No table renames mid-sprint. Master plan Section 19's OTHER tables (`predictions`, `prediction_events`, `prediction_feedback`, `rag_chunks`, `engine_logs`, `analytics_events`, `subscriptions`, `users`) are created on their scheduled days under their planned names.
**Reason:** the table works, the cache works, and a rename risks the only proven persistence path for zero benefit.
**Binds:** Codex migrations, backend chart handlers, RLS policies (June 21).
**Revisit:** post-launch consolidation pass, only if the dual naming (`user_charts` vs the plan's `charts`) causes real confusion.

## D006 — Auth: temporary header until June 21, then Supabase JWT + RLS
**Date:** 2026-06-11 · **Status:** ACTIVE, self-terminating
**Decision:** `X-User-Id` header stands in for auth through June 20. All handlers read identity via one helper (`get_current_user()`). On June 21: Supabase Auth magic-link on the frontend, JWT verification on every authed route, RLS on `user_charts` and `predictions`, the header path DELETED (not disabled). Ownership failures return 404, never 403.
**Reason:** auth before the engines exist is sequencing waste; auth after real users arrive is negligence. June 21 is the last responsible day.
**Binds:** every authed endpoint, the Antigravity login lane (T11.4), the launch gate.
**Revisit:** the deletion is verified at the June 22 gate (other-user chart_id → 404, tested).

## D007 — Backend port is 8000 everywhere
**Date:** 2026-06-11 · **Status:** LOCKED
**Decision:** local, Docker, and Azure all run uvicorn on 0.0.0.0:8000. Port 7860 is dead.
**Reason:** 7860 hit Windows socket permission errors on June 10; one port everywhere removes a whole class of config drift.
**Binds:** Dockerfile, deploy scripts, local dev docs.

## D008 — Deploy rituals are scripted, not remembered
**Date:** 2026-06-11 · **Status:** LOCKED
**Decision:** backend deploy = `scripts/deploy_backend.sh` (build image → tag `vX.Y.Z` → push GHCR → update Container App → hit `/health`). Frontend deploy = `scripts/deploy_frontend.sh` (`vercel --prod`, then load `/chart` on a phone). Image tags are semantic and monotonic; rollback = previous Container Apps revision / previous Vercel deployment, each tested once before launch day.
**Reason:** a deploy performed from memory under launch pressure is where outages come from.
**Binds:** Codex task T3.5, the Day 12 checklist.
**Revisit:** see D019 for the tag-reuse ban added June 12.

## D009 — Frontend types are generated from the schema, never hand-written
**Date:** 2026-06-11 · **Status:** LOCKED, permanent
**Decision:** `scripts/gen_types.sh` produces `frontend/src/types/chart.ts` from `schemas/chart.json` (json-schema-to-typescript) with a DO-NOT-EDIT header. Regenerating types is part of every schema version bump, in the same PR.
**Reason:** this is the mechanism that makes a field unable to exist in one layer and not the other, for the life of the product.
**Binds:** Antigravity lane T2.5, every future schema bump.
**Revisit:** never; extend the same pattern to `frontend/src/types/api.ts` when practical.

## D010 — Engine-first order retained; the June-10 handoff re-plan is rejected
**Date:** 2026-06-11 · **Status:** LOCKED
**Decision:** the build order stays ephemeris → nakshatra → KP → dasha → strength → scoring → transits → RAG → synthesis → wiring. The handoff document's proposal (predictions Day 2, Gemini Day 3, "houses/dashas/KP if missing" Day 4) is rejected in full. Predictions ship June 21, after every number they cite is validated.
**Reason:** the product's must-prove statement names the user's actual mahadasha lord and actual cusp sublord. Predictions before correct math are confidently wrong, and wrong is invisible until a stranger screenshots it. Infrastructure being live does not make math correct.
**Binds:** the entire v2 calendar.
**Revisit:** never.

## D011 — Antigravity ramps early, under hard guardrails
**Date:** 2026-06-11 · **Status:** ACTIVE
**Decision:** Antigravity runs one frontend lane per day from June 12 (two on June 20), per the backlog in `docs/execution-plan-v2.md` §8, instead of idling until Day 10. Guardrails: fixtures only behind `NEXT_PUBLIC_USE_FIXTURE`; lane skipped if its fixture is missing by 09:00; one component per lane; never edits generated types; PR reviewed in a capped 30-minute slot at 21:00; the lane pauses before validation time is ever spent on it.
**Reason:** the old plan built the entire prediction UI on launch morning; the ramp converts June 22 into a wiring day.
**Binds:** TASKBOARD.md Antigravity rows, AGENTS.md §2.3.
**Revisit:** any day a lane PR costs more than 30 review minutes twice in a row → drop to a lane every second day.

## D012 — Pinned schema conventions (the ambiguities, resolved once)
**Date:** 2026-06-11 · **Status:** LOCKED with v1.0
**Decision:** (a) nakshatra index is 1-based, 1 = Ashwini, 27 = Revati; (b) `rag_alignment.status` ∈ `aligned | partial | contradicted | no_data`; (c) pydantic models use `extra="forbid"` everywhere; (d) schema backstops lat to ±66°; (e) ambiguous DST local times resolve with `fold=0` (earlier offset); (f) node retrograde flag derives from speed sign like every body; (g) longitudes serialize to 4 decimals.
**Reason:** each of these was silent in the master plan; left unpinned, every engine and every agent re-decides them differently.
**Binds:** chart-schema.md, ephemeris.md, nakshatra/kp/rag engines, generated types.
**Revisit:** changing any of these is a schema version bump by definition. The nakshatra conventions in (a) are extended, not changed, by D020.

## D013 — Pre-validation cached charts are untrusted
**Date:** 2026-06-11 · **Status:** ACTIVE until executed
**Decision:** every `user_charts` row created before the June 11 fixture suite goes green is suspect. Tonight's procedure: re-run one cached chart's input through the validated engine and diff longitudes. Any drift → flush all pre-fix rows (they regenerate on demand; cache MISS is the designed behavior).
**Reason:** if production ran Moshier fallback or an unverified ayanamsa, cached charts preserve wrong numbers forever and serve them as HITs.
**Binds:** Day 1 task T1.5.
**Revisit:** closes tonight; record the outcome here.
**Outcome (required before Day 2 validation):** Flush all pre-June-11 rows, then replace this sentence with: `Closed Jun 12: all pre-fix rows flushed, 2 rows.` Do not trust any HIT served from a pre-June-11 row until this line is closed.

## D014 — Launch slip rule
**Date:** 2026-06-11 · **Status:** LOCKED
**Decision:** the launch gate runs June 22 at 14:00 against master plan Section 24 verbatim. Pass → soft launch by 18:00, public push the same evening or June 23 morning. Fail → fix and re-gate, public slips exactly one honest day. A gate failure is announced (to yourself, in the scorecard), never silently absorbed by shipping anyway.
**Reason:** the only launch failure that compounds is the silent one.
**Binds:** Day 12, the scorecard.

## D015 — Branch protection: minimal, deliberately
**Date:** 2026-06-11 · **Status:** LOCKED for the sprint
**Decision:** GitHub branch protection on main enables ONLY "do not allow force pushes." No required-PR rule, no required status checks. Local `pytest -q` plus the allowed-files guard is the merge gate; CI is the backstop, not the gatekeeper.
**Reason:** the solo merge flow (local merge in `-main`, test, push) would deadlock against a required-PR rule; the founder is the review.
**Binds:** the daily merge mechanics.
**Revisit:** the day a second human gets write access, flip to required PRs the same hour.

## D016 — GHCR image stays public; consequences accepted and bounded
**Date:** 2026-06-11 · **Status:** ACTIVE
**Decision:** `ghcr.io/pratyus-saha/askjunopath-backend` remains a public package so Azure pulls without registry credentials. Bound consequences: NOTHING sensitive is ever baked into the image (no .env, no keys, no service-role anything; secrets live exclusively in Container Apps configuration); the ephemeris data files in the image are fine (public data); image contents are reviewed once before launch.
**Reason:** the June 10 `DENIED` pull failures cost hours; the public-package fix is stable and the secret-hygiene rule makes it safe.
**Binds:** Dockerfile, AGENTS.md §5, the Day 12 checklist.
**Revisit:** week 2 post-launch — move to a private package with managed identity, at leisure, not under deadline.

## D017 — Canonical engine path is `backend/app/engines/`; the old chart engine is deprecated
**Date:** 2026-06-12 · **Status:** LOCKED
**Decision:** the repo's real layout includes the `app/` segment. `backend/engines/` is never created. Where plan docs, specs, or pasted prompts reference `backend/engines/` or `backend/api/`, agents translate to `backend/app/engines/` and `backend/app/routers/` and note the translation in the PR description (AGENTS.md Rule 14). `backend/app/core/chart_engine.py` is DEPRECATED: read-only history, never imported, extended, or used as a reference for new astrology math. The trusted ephemeris engine is `backend/app/engines/ephemeris_engine.py`.
**Reason:** Day 1 work landed in the real repo layout; documents written before Day 1 assumed a flatter one. The repo wins. Without a standing translation rule, every pasted "Section N" prompt re-creates the wrong directory and splits the engine codebase in two.
**Binds:** AGENTS.md Rule 14 and §2.1/§2.2, TASKBOARD.md file-ownership column, every engine task prompt for the rest of the sprint.
**Revisit:** never for the path; delete `backend/app/core/chart_engine.py` entirely in week 1 post-launch once nothing references it.

## D018 — `.env` never enters Docker images (operationalizes D016's secret-hygiene rule)
**Date:** 2026-06-11 (decided under fire) · documented 2026-06-12 · **Status:** LOCKED
**Decision:** `backend/.dockerignore` excludes `.env` and `.env.*`, and those exclusions are never weakened. Production environment variables come from Azure Container App secrets/runtime env only. Local Docker testing may pass `--env-file backend\.env` at runtime only. The Swiss Ephemeris `.se1` files are the deliberate exception in the other direction: not committed to git, but baked into the image at `/app/ephe` with `ENV SE_EPHE_PATH=/app/ephe`, and `/health` asserts their presence.
**Reason:** on June 11, `.env` baked into the image caused Pydantic BaseSettings to load stale values, so production reported version 1.0.0 after the code said 1.2.0. The asymmetry (.env out, .se1 in) is stated explicitly so a future "tighten the dockerignore" pass cannot strip the ephemeris files and silently degrade every chart to Moshier fallback.
**Binds:** Dockerfile, `backend/.dockerignore`, AGENTS.md §2.2 Docker rules, D016's image-content review before launch.
**Revisit:** never for the .env rule; the .se1 exception is re-examined only if ephemeris files move to a mounted volume post-launch.

## D019 — Image tags are never reused; tag and app version diverge intentionally (extends D008)
**Date:** 2026-06-11 (decided under fire) · documented 2026-06-12 · **Status:** LOCKED
**Decision:** every deploy gets a unique, new, monotonic tag. Re-pushing to an existing tag is banned. The Docker image tag bumps per deploy; the app/chart engine version bumps per code or contract change. They will usually differ, and seeing them differ is correct, not a bug. Current state at time of writing: production image `v1.2.1`, app/chart engine version `1.2.0`.
**Reason:** on June 11, Azure continued serving old behavior from the reused `v1.2.0-meta` tag; the fix was pushing the unique tag `v1.2.1` to force a fresh revision pull. Separately, recording the tag-vs-version divergence here prevents a future agent from filing "image says v1.2.1 but /health says 1.2.0" as a phantom bug.
**Binds:** D008's deploy ritual, `scripts/deploy_backend.sh` (the script must generate or demand a fresh tag and refuse a reused one), the Day 12 checklist.
**Revisit:** never.

## D020 — Nakshatra convention frozen (extends D012(a))
**Date:** 2026-06-12 · **Status:** LOCKED
**Decision:** the full convention lives in `docs/nakshatra.md`, the source of truth for all nakshatra, pada, navamsa, KP, and dasha boundary logic. The load-bearing points: (a) API index 1-based per D012(a); internal code may be 0-based, schema wins at the boundary. (b) Boundary rule: lower bound inclusive, upper exclusive; an exact boundary belongs to the NEXT segment (exactly 13°20'00" is Bharani pada 1). (c) All boundary math in integer arc-seconds, converted once at engine entry via `arcsec = round((L % 360) * 3600) % 1296000`; floats only at the output layer. (d) `planets[].nakshatra` is a `NakshatraBlock` with exactly seven keys (name, index, lord, degree_in_nakshatra, pada, degree_in_pada, navamsa_sign) or null; `houses[].cusp_nakshatra` is a name STRING or null, never an object. (e) Navamsa: `floor(L × 9 / 30) % 12` from normalized sidereal absolute longitude, signs from Aries. (f) The founder-supplied 330-row fixture file (`tests/fixtures/nakshatra/boundaries_330.json`) is the judge; code conforms to it, never the reverse.
**Amended Jun 12, same day:** wrap-around modulo added after a rounding overflow edge case was found in review.
**Reason:** the KP 249 table (Day 3), house work (Day 4), and the dasha engine (Day 5) all inherit this convention. Changing it after today means regenerating every downstream fixture, which is why it freezes now and not later.
**Binds:** `docs/nakshatra.md`, `backend/app/engines/nakshatra_engine.py`, the KP generator, dasha_engine, TASKBOARD.md T2.1/T2.2/T2.4.
**Revisit:** never for the boundary rule and shapes; the `round` vs `floor` arc-second conversion may be revisited only if a JHora comparison surfaces a sub-arc-second classification mismatch, and any change is a schema-adjacent event requiring full fixture regeneration.

## D021 — Metadata contract: legalize in schema v1.1
**Date:** 2026-06-15 · **Status:** DECIDED, implementation pending
**Decision:** add an optional `metadata` object to schemas/chart.json, bump schema to
v1.1, regenerate frontend ChartData per D009 in the same PR. Keep metadata optional for
backward safety. Execute BEFORE any KP schema expansion.
**Reason:** chart_engine_version, cache_status, and calculation_mode are trust signals
that belong in the contract, not in a temporary frontend wrapper.
**Revisit:** closes when schema v1.1 ships.
