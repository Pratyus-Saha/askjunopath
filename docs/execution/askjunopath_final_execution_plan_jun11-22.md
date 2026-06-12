# AskJunoPath Final Execution Plan v2
## June 11 to June 22, 2026, then the post-launch system
### One founder. Four agent lanes. Infra already live. Math not yet trusted.

This plan supersedes the June 22 master plan's calendar while keeping its engineering core intact. It absorbs three facts the master plan did not know: the deployment pipeline is already live (Vercel frontend, Azure Container Apps backend via GHCR, Supabase caching proven MISS to HIT), the chart math is unvalidated, and Antigravity sat idle until Day 10 in the old plan. Section references like "Section 8" still point to the master plan (junopath_mvp_plan_jun22.md); the rules and specs there remain the source of truth for engine internals.

---

# 1. What Changed and Why

**Infra is banked.** Docker → GHCR → Azure Container Apps works. Vercel CLI deploys work (`vercel --prod` from `frontend/`; the broken UI import flow stays dead). Supabase persistence and chart caching work. The original plan's Day 1 infra blocks and roughly half of Days 11 to 12's deployment work are complete and never repeat.

**Correctness is not banked.** Zero charts validated against Jagannatha Hora. Ayanamsa configured but unverified. No Placidus cusps. No houses. No schema contract. No fixtures. The plausible live bug: if the Swiss `.se1` files were never baked into the Docker image with `SE_EPHE_PATH` set, the production backend is silently returning Moshier-fallback positions right now. Every cached row in `user_charts` inherits whatever today's validation finds.

**Frontend host is Vercel, permanently for this sprint.** The master plan said Azure Static Web Apps; reality says Vercel and it works. Decision recorded (D004 below). Consequences threaded through this plan: CLI deploys, `NEXT_PUBLIC_API_URL` as the only frontend env var, no secrets in Vercel ever, CORS allowlist on FastAPI for the Vercel domain (currently unhardened, fixed Day 11), frontend CI via GitHub Action since Vercel deploys are manual.

**Antigravity ramps from Day 2, not Day 10.** One frontend lane per day, against fixture JSON only, one component per lane, never touching backend. This spreads the old plan's brutal Day 12 frontend load across eight days and is the single biggest de-risking move available. The guardrail that makes it safe: Antigravity consumes only frozen contracts and committed fixtures, and you review its PR in a fixed 30-minute evening slot. If your review time runs out, the Antigravity lane pauses, never the validation blocks.

**The engine order does not change.** Ephemeris → nakshatra → KP → dasha → strength → scoring → transits → RAG → synthesis → frontend wiring. Predictions before correct math are confident lies, and the product's entire differentiator is math a stranger can verify.

---

# 2. Current State Ledger

| Area | Status | This plan's action |
|---|---|---|
| Vercel frontend (Next.js, `/` and `/chart`) | Live via CLI | Keep; Antigravity extends it daily |
| Azure backend (FastAPI, `/health`, `/chart/generate`) | Live | Harden math today; upgrade /health today |
| GHCR image v1.0.0, public package | Live | New tags per deploy (v1.1.0 today); revoke exposed PAT immediately |
| Supabase `user_charts` + cache | Working | Keep table; store chart.json v1.0 inside `chart_json` with embedded schema_version |
| Auth | Temp `X-User-Id` header | Keep through Jun 20; swap to Supabase Auth JWT Jun 21 |
| Ephemeris correctness | UNVERIFIED | Day 1 mission, today |
| Cusps/houses, KP, dasha, strength, scoring, transits, RAG, synthesis | Missing | Days 1 to 11 per calendar |
| CORS, rate limiting, monitoring | Missing | Days 11 to 12 |
| Payments | Missing | Razorpay payment links only; modal Day 11; real billing post-launch |

---

# 3. Operating Rules (the ten, plus three new)

Rules 1 to 10 from the playbook stand unchanged: spec before code; fixtures before implementation; one writer per file; nothing merges red; the schema freezes tonight; the e2e script runs every evening; reference software is the judge; reset AI context between engines; commit every 45 to 60 minutes; the 16:00 cut checkpoint is non-negotiable.

**Rule 11. Main is a live wire.** Pushes to main can reach production. After every merge-and-push, glance at GitHub Actions and, when the backend changed, the Azure revision status. Backend deploys are explicit (build, tag, push to GHCR, update Container App), so they stay controlled. Frontend deploys only when you run `vercel --prod`, never automatically.

**Rule 12. Antigravity builds against fixtures, full stop.** Every Antigravity lane prompt names exactly one fixture file and one component file. No live API calls from components during the sprint (wiring happens Days 11 to 12 under your eyes). If the fixture for a lane does not exist by 09:00, that lane is skipped for the day, not improvised.

**Rule 13. Secrets hygiene after the PAT exposure.** The leaked GitHub PAT gets revoked before any other work today. Service-role keys live only in Azure Container Apps secrets. Vercel carries only `NEXT_PUBLIC_*` vars. Any future credential that touches a terminal screenshot gets rotated the same day.

---

# 4. Tool Lanes (revised)

| Tool | Standing role | New in v2 | Never give it |
|---|---|---|---|
| Claude Code | Precision engines in-repo, tests, fix until green | Hardens existing chart code rather than greenfield | Scoring weights to invent; astrology rules from memory |
| Codex | Branch-only boilerplate: generators, pydantic, migrations, ingest, CI/Docker | Owns the schema retrofit + /health upgrade today | Subtle math invisible in review |
| Antigravity | Frontend lanes against fixture JSON, one component per lane; repo chores | Active from Day 2 with a daily lane (Section 8 backlog) | Backend anything; the KP engine or scorer, ever; live API calls |
| Claude Pro (chat) | Logic review, spec attacks, weight critique, Gemini prompt design, quality checklist | Reviews each Antigravity component spec before the lane starts | Large code files |
| Gemini Pro | Transcript tagging, rule-card formatting, synthesis prompt iteration | unchanged | Chart math |
| ChatGPT Plus | Second opinion, adversarial tests, launch copy | unchanged | A third implementation lane |

Worktree mapping (already set up): you in `askjunopath-main`, Claude Code in `askjunopath-claude`, Codex in `askjunopath-codex`, Antigravity in `askjunopath-antigravity`. One branch per task, named `agent/<tool>/<topic>`. Merge order on any day: Codex contracts first, Claude Code engines second, Antigravity components last.

---

# 5. Locked Decisions (append to DECISIONS.md)

- **D004 Frontend host:** Vercel, deployed via CLI from `frontend/`. Azure Static Web Apps references in the master plan are void. Revisit Git-integration and preview deployments post-launch only.
- **D005 Storage:** keep `user_charts` and the `chart_json` column. The chart.json v1.0 object lives inside `chart_json` with `schema_version` embedded. No table renames during the sprint. The master plan's Section 19 tables for predictions, feedback, analytics, engine_logs get created on their scheduled days under their planned names.
- **D006 Auth:** `X-User-Id` header survives until June 21, then Supabase Auth (email magic link) with JWT verification on the backend. RLS policies land with the swap.
- **D007 Backend port:** 8000 everywhere (local, Docker, Azure). 7860 is dead.
- **D008 Deploy ritual:** backend = build image, tag `vX.Y.Z`, push GHCR, update Container App, hit `/health`. Frontend = `vercel --prod` from `frontend/`, then load `/chart` on a phone. Both rituals scripted in `scripts/deploy_backend.sh` and `scripts/deploy_frontend.sh` by Day 3.
- **D009 Type sync:** TypeScript types for the frontend are GENERATED from `schemas/chart.json` (script in `scripts/gen_types.sh` using json-schema-to-typescript), never hand-written. This is the mechanism that keeps frontend and backend in sync for the rest of the product's life. Antigravity sets it up Day 2; regenerating types after any schema version bump is part of the bump itself.

---

# 6. The Calendar at a Glance

| Date | Day | Mission | Antigravity lane | Gate headline |
|---|---|---|---|---|
| Jun 11 Thu | 1 | Schema lock + ephemeris truth (retrofit) | none (setup day) | 5/5 charts vs JHora; schema v1.0 tagged; /health honest in prod |
| Jun 12 Fri | 2 | Nakshatra + pada; KP 249 generator starts | Type-gen pipeline + chart.sample.json + lint | 330 boundary fixtures green |
| Jun 13 Sat | 3 | KP planet level | Landing page (static) | 25/25 exact sublord match |
| Jun 14 Sun | 4 | KP cusp level + significators | Birth input extension (approximate_time, errors) | 12 cusp sublords exact on 10 charts; ladder fixtures green |
| Jun 15 Mon | 5 | Dasha engine | Chart summary page v1 | 10-chart MD/AD within 1 day |
| Jun 16 Tue | 6 | Strength V1 + D9/D10 | DashaTimeline (real dasha fixtures) | rank-order green; divisional populated |
| Jun 17 Wed | 7 | Rule packs + confidence scoring | Planetary details page | golden fixtures ±8 and tier-exact |
| Jun 18 Thu | 8 | Transit windows | Feedback buttons + analytics.ts + disclaimers | property tests on 50 charts green |
| Jun 19 Fri | 9 | RAG corpus + ingestion | PredictionCard v1 (Section 16 fixture) | 300+ chunks; spot check ≥90% |
| Jun 20 Sat | 10 | RAG quality gate + synthesis prompt | Logic-expansion sheet + feedback page | precision@4 ≥ 0.7, zero leaks |
| Jun 21 Sun | 11 | Synthesis + /predict e2e + auth swap + CORS | Upgrade modal + wiring prep | 3 domains live; failure drill witnessed; JWT auth on |
| Jun 22 Mon | 12 | Wire, mobile QA, launch gate, launch | All lanes converge on wiring | Launch gate at 14:00; soft launch evening; public same night or Jun 23 |

Every day still ends with `scripts/e2e_check.py` green on 3 charts at 19:00, stubs shrinking daily.

The daily rhythm is unchanged from the playbook: 08:30 plan (Claude Pro), 09:00 to 13:00 Build A, 13:30 validation (protected above everything), 14:30 to 18:30 Build B, 16:00 cut checkpoint, 19:00 integration, 21:00 nightly review with a hard stop at 21:30. One addition at 21:00: the 30-minute Antigravity PR review slot, and the deploy-status glance per Rule 11.

---

# 7. Day by Day

## Day 1. Thursday, June 11: Schema lock + ephemeris truth (retrofit edition)

**Mission:** by tonight, raw positions you trust to 5 arc-seconds from the SAME code path production runs, and a frozen contract. The infra exists; today makes it honest.

**Deliverables**

| Artifact | Acceptance |
|---|---|
| PAT revoked | Done before 09:30, confirmed in GitHub settings |
| `schemas/chart.json` v1.0 + `backend/schemas/models.py` | Pydantic round-trips all 5 example objects per docs/chart-schema.md |
| `backend/app/engines/ephemeris_engine.py` (hardened from existing code) | 5-chart fixture test green: planets within 5 arc-sec, cusps within 0.01°, ascendant exact sign |
| Placidus cusps via `swe.houses_ex` | NEW capability; was absent |
| `.se1` files baked into image at `/app/ephe`, `SE_EPHE_PATH` set | `/health` asserts file existence from inside the container |
| `/health` upgraded to Section 20 shape | Reports ephemeris/db sub-checks; degraded not failing when only an optional dep is down |
| 5 reference charts in `tests/fixtures/charts/` | Input + JHora expectations, settings per docs/reference-settings.png |
| Image v1.1.0 deployed to Azure | `/health` green in prod, including the ephemeris assertion |
| Stale-cache decision executed | One pre-fix cached chart diffed against validated output; if different, `user_charts` flushed |
| CI proven red | Break a test, push, see red, revert |

**Schedule.** 09:00 to 09:30: revoke PAT; commit docs/ephemeris.md, docs/chart-schema.md, docs/health.md; install JHora, set KP-Newcomb + Placidus + true node, screenshot to docs/reference-settings.png. 09:30 to 13:00: Claude Code hardens the engine (prompt below); Codex in `agent/codex/day1-schema-health` builds models + /health + Dockerfile fix (prompt below); you paste the schema into Claude Pro for the five-scenario attack, patch, tag v1.0. 13:30 to 14:30: export 5 charts from JHora, write fixture expectations. 14:30 to 18:30: make the 5-chart test pass (debug order below); merge Codex; build v1.1.0; push GHCR; update the Container App; hit prod /health; run the cache diff. 19:00: e2e stub. 21:00: nightly review (ChatGPT Plus); draft Day 2 prompts; export 5 more reference charts if energy allows.

**Claude Code prompt (fresh session in askjunopath-claude):**

```
Read AGENTS.md, docs/ephemeris.md, and schemas/chart.json. An earlier working
version of chart calculation exists in this repo. Your job is to harden it to
the spec, not extend it politely: refactor it into
backend/app/engines/ephemeris_engine.py per docs/ephemeris.md exactly. Where the
existing code conflicts with the spec, the spec wins; where the existing code
already matches, keep it.

You may edit only: backend/app/engines/ephemeris_engine.py, tests/test_ephemeris.py,
tests/fixtures/charts/*.json. Do not touch backend/app/routers/, frontend/, Dockerfile,
or schemas/.

Specific gaps to close (verify each against the current code first):
1. swe.set_sid_mode(swe.SIDM_KRISHNAMURTI, 0, 0) before every position call.
2. TRUE_NODE for Rahu; Ketu = Rahu + 180 mod 360.
3. Placidus sidereal cusps via swe.houses_ex (currently absent). Confirm the
   installed pyswisseph's cusp tuple indexing in a REPL before mapping.
4. Speed, retrograde, combustion flags per the orb table in the spec.
5. Single local-to-UT conversion via zoneinfo at the engine boundary.
6. LAT_UNSUPPORTED structured error for |lat| > 66.
7. ephemeris_files_ok() asserting .se1 files exist at SE_EPHE_PATH.

Tests per docs/ephemeris.md section 10, harness now, fixtures marked
PENDING_JHORA until I supply real values this afternoon. Run pytest, iterate
until green on everything except PENDING_JHORA, then stop and update HANDOFF.md.
```

**Codex prompt (branch agent/codex/day1-schema-health):**

```
Read AGENTS.md and docs/chart-schema.md. Produce, editing only these files:
backend/schemas/models.py, schemas/chart.json, backend/app/main.py,
Dockerfile, tests/test_schema_roundtrip.py, tests/test_health.py.

1. Pydantic v2 models per docs/chart-schema.md sections 3 to 11, including
   extra="forbid", all validators, and progressive-population Optionals.
   Export model_json_schema() to schemas/chart.json.
2. Upgrade /health per docs/health.md: status, version, ephemeris, db
   sub-checks under 1s timeouts; ephemeris check calls
   ephemeris_engine.ephemeris_files_ok(); degraded, never 500, when an
   optional dependency is down. Keep the existing response keys as a subset
   so nothing currently consuming /health breaks.
3. Fix the Dockerfile: bake Swiss ephemeris .se1 files into /app/ephe, set
   ENV SE_EPHE_PATH=/app/ephe, keep python:3.11-slim, port 8000, the
   existing healthcheck.
4. Tests per docs/chart-schema.md section 12 (round-trip + rejection list)
   and a /health test with a monkeypatched missing-ephe path.

Run pytest, iterate until green, open a PR, do not merge, update HANDOFF.md.
```

**Error traps (debug in this order)**

1. Silent Moshier fallback IN PROD, the likeliest live bug. First check of the afternoon: shell into the running container (or add a temp log line) and verify `.se1` files at SE_EPHE_PATH. If absent, every chart ever generated is suspect and the cache flush is mandatory.
2. Wrong ayanamsa: every planet off by consistent arc-minutes. Check set_sid_mode placement before anything else.
3. Mean node: Rahu off by up to 1.5°. The explicit Rahu fixture catches it.
4. Timezone double-conversion: the geocoding path (birth_city → lat/lon → timezone) must hand the IANA zone to the engine and let the engine convert once. Trace the DST fixture by hand.
5. Cusp tuple off-by-one from pyswisseph indexing. The REPL check in the prompt exists for this.

**Gate:** schema tagged v1.0; 5/5 charts green; /health green in prod with the ephemeris assertion; CI proven red; cache decision executed.
**16:00 cut:** the prod deploy slips to tomorrow 09:00 and repo cosmetics die. Never the 5-chart validation, never the Moshier check.

---

## Day 2. Friday, June 12: Nakshatra + pada engine; KP generator starts; Antigravity wakes

**Mission:** Section 7 complete with boundary behavior proven; the KP 249 generator drafted by evening; the frontend type-sync pipeline standing.

**Deliverables**

| Artifact | Acceptance |
|---|---|
| `backend/app/engines/nakshatra_engine.py` | All 330 boundary fixtures green (27 nakshatra edges × padas + 0° Aries + 29°59'59" Pisces) |
| Navamsa mapping | `floor(longitude_in_sign × 9 / 30) % 12` verified all 12 signs |
| Chart JSON carries nakshatra blocks | e2e shows nakshatra, lord, pada, degree-in-pada per planet and cusp |
| `scripts/generate_sublord_table.py` drafted (Codex, branch) | Structural assertions written; full verification is tomorrow |
| 10 more reference charts | Running total 15 of 25 |
| ANTIGRAVITY: `scripts/gen_types.sh` + `frontend/src/types/chart.ts` + `frontend/src/fixtures/chart.sample.json` | Types generated from schemas/chart.json, not hand-written; existing /chart page renders the typed fixture; ESLint passes |

**Schedule.** 09:00 to 13:00: Codex builds nakshatra_engine from the Section 7 prompt in `agent/codex/nakshatra`; you generate the 330-row boundary fixture file with a small script and spot-verify 10 rows against JHora; Antigravity lane runs the type-gen task (prompt pattern below). 13:30: Moon nakshatra/pada for 10 charts vs JHora; 3 boundary charts by hand. 14:30 to 18:30: Claude Code integrates nakshatra into chart assembly; Codex starts the 249 generator per the Section 8 prompt in `agent/codex/kp-table`; merge nakshatra after green. 19:00 e2e. 21:00: review Antigravity PR (30 min cap), nightly notes, draft Day 3 prompts.

**Antigravity prompt (the template every later lane copies):**

```
Read AGENTS.md and frontend/src/fixtures/chart.sample.json (create it from
schemas/chart.json's example object first).

You may edit only: scripts/gen_types.sh, frontend/src/types/chart.ts,
frontend/src/fixtures/chart.sample.json, frontend/app/chart/page.tsx,
frontend/.eslintrc.json.

Task: (1) create scripts/gen_types.sh that runs json-schema-to-typescript
against schemas/chart.json and writes frontend/src/types/chart.ts with a
DO-NOT-EDIT header; (2) commit the generated types; (3) refactor the existing
/chart page to type its state with ChartData and render from the fixture when
NEXT_PUBLIC_USE_FIXTURE=1; (4) add eslint config and fix violations in files
you own.

The live API response carries a top-level `metadata` key that is NOT in
`schemas/chart.json`. Type only schema fields as `ChartData`. Treat metadata
as a separate untyped passthrough, for example a `metadata?: unknown` field or
a wrapper type. Do not add metadata to the generated types or the schema.

Do not call the live API in any new code path. Do not edit backend/*.
Definition of done: npm run lint passes, npm run build passes, npm test
passes, PR opened, HANDOFF.md updated.
```

**Error traps:** float drift at 13°20' multiples (compare with a tolerance of 1e-6 on degree-in-nakshatra, exact on index/pada); apply `% 1296000` after rounding in the nakshatra engine; regression tests are required at `359.9999`, `359.99999`, `360.0`, and `-0.0001`; the 1-based nakshatra index convention from docs/chart-schema.md (1 = Ashwini), do not let the engine re-decide it; generated types drifting (the DO-NOT-EDIT header plus D009 is the defense).

**Gate:** 330 fixtures green; nakshatra blocks in e2e output; types pipeline merged.
**16:00 cut:** the KP generator draft slips to tomorrow 09:00 (it was a head start, not a commitment). Antigravity lane pauses if PR review would eat validation time. Never the boundary fixtures.

---

## Day 3. Saturday, June 13: KP engine, planet level

**Mission:** the 249 sublord table generated and verified; star/sub/sub-sub for any longitude; exact sublord match on 25 charts.

**Deliverables**

| Artifact | Acceptance |
|---|---|
| `scripts/generate_sublord_table.py` + committed CSV | Structural assertions: cumulative sub spans sum to 800' per nakshatra; sub sequence starts at the nakshatra lord; 249 rows exactly |
| `backend/app/engines/kp_engine.py` planet-level functions | star_lord/sub_lord/sub_sub_lord for any longitude; boundary triplets covered |
| Planets' kp blocks wired into chart JSON | e2e shows the full chain per planet |
| Final 10 reference charts | Total 25 of 25 |
| ANTIGRAVITY: landing page | Section 17 spec: hero with one static anonymized sample card, three-line how-it-works, CTA to /chart, disclaimer footer; loads under 2s on 4G; CTA above the fold at 360px; design tokens (navy, Cormorant Garamond, DM Sans, gold #C9A96E) |
| `scripts/deploy_backend.sh` + `scripts/deploy_frontend.sh` | Each runs the D008 ritual end to end |

**Schedule.** 09:00 to 13:00: Codex finishes the generator (Section 8 prompt); Claude Code builds kp_engine planet level + tests; Antigravity builds the landing page against a hand-written static card JSON (no API). 13:30: 25-chart planet sublord comparison vs JHora, EXACT match required, every discrepancy filed as a failing test first. 14:30 to 18:30: fix to 25/25; run the Section 8 review prompt in Claude Pro and file its findings as tests; merge lanes in order. 19:00 e2e. 21:00 review + Day 4 prompts.

**Error traps:** sub sequence not starting at the nakshatra lord (the classic KP bug; a structural assertion, not a spot check); off-by-one at nakshatra boundaries (test the exact 800' edges); landing page pulling live data (it must not; static JSON only).

**Gate:** structural assertions pass; 25/25 exact; review findings filed as tests; landing page builds clean.
**16:00 cut:** sub-sub lord DISPLAY (keep the computation); landing page polish beyond acceptance.

---

## Day 4. Sunday, June 14: KP cusp level + significators

**Mission:** cusp sublords and the A/B/C/D significator ladder with node agency. The differentiator's spine.

**Deliverables**

| Artifact | Acceptance |
|---|---|
| `cusp_kp_block` for all 12 cusps | 12 cusp sublords exact vs JHora on 10 charts |
| `backend/app/engines/house_engine.py` (Codex) | Occupant/owner maps via CUSP SPANS, wraparound fixtures green |
| `significators()` + houses array in chart JSON | 3 hand-built ladder fixtures green; node agency per Section 8 |
| `planets[].house_occupied`, `houses[].occupants` populated | Cusp-span assignment, never by sign |
| ANTIGRAVITY: birth input extension | approximate_time toggle persisting to the request; LAT_UNSUPPORTED and 422 errors rendered as friendly messages; loading state with 8s expectation; native pickers on mobile |

**Schedule.** 09:00 to 13:00: Claude Code builds cusp blocks + significators (Section 23 Day 4 prompt verbatim); Codex builds house_engine in branch; you hand-work the 3 significator ladder fixtures on paper (do this BEFORE the engine runs; Rule 2); Antigravity runs its lane. 13:30: 12 cusp sublords × 10 charts vs JHora; ladder vs your hand work. 14:30 to 18:30: fix, merge in order, wire `approximate_time` through to the chart object (the schema field exists since Day 1). 19:00 e2e. 21:00 review.

**Error traps:** house-of-planet by sign instead of cusp spans (the playbook's named Day 4 bug; the wraparound fixtures exist for this); a planet within 0.01° of a cusp (explicit fixture); frontend toggle defaulting to true (it must default false and be explicit).

**Gate:** houses array complete; ladder fixtures green; 10/10 cusp match; toggle persists end to end against a local backend run.
**16:00 cut:** significator strength tiers default to flat weights (restore Day 7). Antigravity error-state polish.

---

## Day 5. Monday, June 15: Dasha engine

**Mission:** Vimshottari to the pratyantardasha level, dated to the day, validated on 10 charts.

**Deliverables**

| Artifact | Acceptance |
|---|---|
| `backend/app/engines/dasha_engine.py` | Birth balance, MD/AD/PD recursion, current_stack(date), next 5 MD/AD, next 30 PD; year = 365.25 days everywhere |
| 10-chart date validation | MD/AD start dates within 1 day of JHora, PD within 2 |
| Edge fixtures | Moon at 0°00' and 13°19'59" of a nakshatra; balance under 30 days |
| Proportion invariant test | Inside any MD, the 9 AD lengths sum to the MD length within seconds |
| ANTIGRAVITY: chart summary page v1 | Ascendant + Moon nakshatra/pada header, planets table with nakshatra columns, "right now" dasha strip consuming a hand-written dasha fixture; renders at 360px |

**Schedule.** 09:00 to 13:00: Claude Code builds the engine (Section 23 Day 5 prompt); ChatGPT Plus generates adversarial date cases; Antigravity lane runs (its dasha fixture is hand-written from the schema this morning; tonight it gets replaced by real engine output). 13:30: 10 charts vs JHora dasha screens. 14:30 to 18:30: fix; verify YOUR OWN chart's current PD by eye; merge; regenerate the frontend dasha fixture from real engine output. 19:00 e2e now prints a real dasha stack. 21:00 review.

**Error traps:** balance convention inverted (elapsed vs remaining; the named Day 5 bug); calendar years leaking in next to 365.25 (drift that passes 3 charts and fails 7 by a day); timezone drift in DISPLAY (compute UT, render in user zone once at the edge; a consistent one-day offset means double conversion); dasha strip showing end dates off by one day (same display rule, frontend side).

**Gate:** 10-chart dates green; edge fixtures green; own PD verified; summary page renders real fixture.
**16:00 cut:** upcoming_pd list to next 10 (schema cap stays 30; restore post-launch).

---

## Day 6. Tuesday, June 16: Strength V1 + D9/D10

**Mission:** rank-order-honest strength scores and the two divisional charts the scorer consumes.

**Deliverables**

| Artifact | Acceptance |
|---|---|
| `backend/app/engines/strength_engine.py` | Score, components dict, tier, notes per Section 10; per-component unit tests green |
| Rank-order assertions | On 10 known charts, the obviously strong planet outranks the obviously weak one, every time |
| `backend/app/engines/divisional_engine.py` | D9 reuses the navamsa function; D10 odd/even offset verified on 4 hand cases covering both parities at low and high degrees |
| Vargottama + D9-debility flags in chart JSON | Present with weight hooks; scorer consumes tomorrow |
| ANTIGRAVITY: DashaTimeline component | Consumes real dasha fixture from yesterday; current MD/AD/PD highlighted; next periods listed; this replaces the old plan's Day 12 Lane 2 entirely |

**Schedule.** 09:00 to 13:00: Codex builds both engines from Sections 10 and 11 in `agent/codex/strength`; ChatGPT Plus generates rank-order test charts (sanity-check its answers before they become assertions); Antigravity lane runs. 13:30: rank-order run + 4 hand-verified D10 cases. 14:30 to 18:30: Claude Code integrates into chart assembly; tier chips render in the summary page from real data. 19:00 e2e. 21:00 review.

**Error traps:** over-tuning absolute scores (V1 is ordering and tiering; pushing a 68 to 71 is Day 7 work leaking early); Sun combust (never); retro Mercury/Venus tighter orbs (12°/8°); Rahu/Ketu via dispositor only, one unit test per node; D10 offset parity.

**Gate:** component + rank-order tests green; divisional block populated; chips rendering; timeline component merged.
**16:00 cut:** D10 modifier ships flag-only at weight 0 (flag still flows). Timeline animation polish.

---

## Day 7. Wednesday, June 17: Domain rule packs + confidence scoring

**Mission:** Sections 12 and 13 complete. The day your judgment matters most; hand scores come before the engine exists.

**Deliverables**

| Artifact | Acceptance |
|---|---|
| `rules/career.yaml`, `finance.yaml`, `relationship.yaml` | House groups per Section 12; nothing domain-specific hardcoded in Python |
| `backend/app/engines/prediction_scoring.py` | Weights: promise 25, dasha 20, kp 15, coverage 10, strength 10, transit 12, rag 8; promise-false cap 44; zero-transit cap 60; tiers 85+ HIGH, 65-84 MEDIUM, 45-64 SPECULATIVE, <45 weak signal |
| 6 hand-scored golden fixtures | Engine within ±8 of your hand score, always the same tier |
| Monotonicity + boundary tests | hypothesis property test; 44/45, 64/65, 84/85 both sides |
| Feature builder + weak-signal path | All-blocking chart produces the weak-signal object, never a forced prediction |
| `feedback_engine` skeleton + predictions/prediction_events/prediction_feedback migrations (Codex) | Per Section 19, merged after tests |
| ANTIGRAVITY: planetary details page (basic) | Per-planet card: position, nakshatra chain, KP chain, strength chip with components on tap; consumes chart fixture |

**Schedule.** 09:00 to 11:00: YOU hand-score 6 known charts for career on paper, before any engine code runs. 11:00 to 13:00: Claude Code implements the scorer (Section 13 prompt); Codex scaffolds YAML + migrations in `agent/codex/rules-db`; Antigravity lane runs. 13:30: golden fixture run + boundary tests. 14:30 to 17:00: paste scorer + weights + your 6 hand scores into Claude Pro; ask where the weights encode optimism instead of KP logic and which two charts would expose it; build those two charts as tests. 17:00 to 18:30: feature builder wiring; e2e outputs scored features for all 3 domains, transit fields stubbed. 19:00 e2e. 21:00 review.

**Error traps:** hope-coded weights (the named risk of the whole product; hand scores first, engine second, adversarial critique third); cap bypass (promise false with everything maxed must emit 44, dedicated test); tier off-by-one (84 is MEDIUM, 85 is HIGH); YAML drift (rename a house group in YAML and behavior must follow).

**Gate:** golden fixtures ±8 and tier-exact; monotonicity green; 3 domains end to end with transits stubbed; details page merged.
**16:00 cut:** finance and relationship YAML shrink to minimal house groups (full versions Day 9 morning). Career ships full. Details page strength-components tap interaction.

---

## Day 8. Thursday, June 18: Transit window engine

**Mission:** real, dated, defensible windows. Property-tested, not spot-checked.

**Deliverables**

| Artifact | Acceptance |
|---|---|
| `backend/app/engines/transit_engine.py` | 90-day scan, slow planets 3-day steps with refinement, Moon daily; trigger catalog per Section 14; ≥2-trigger rule; ≤30-day windows via orb tightening (1° → 0.75° → 0.5° then split); top-3 separated ≥7 days; PD-overlap ×1.3 |
| Property tests across 50 random charts | Every window ≥2 triggers, ≤30 days, top-3 separation; do not shrink to 5 charts for runtime |
| 3 hand-computed Jun-Aug 2026 contacts | Detected within 1 day |
| Scorer integration | Transit component consumes real windows; stubs removed |
| ANTIGRAVITY: feedback buttons component + `frontend/src/lib/analytics.ts` + disclaimer footer | Buttons fire analytics events to a mock sink; disclaimer renders on every prediction surface per the master plan's launch requirement |

**Schedule.** 09:00 to 09:45: hand-compute the 3 contacts against JHora's transit screen. 09:45 to 13:00: Claude Code builds the engine (Section 23 Day 8 prompt); Antigravity lane runs. 13:30: known-contact detection + property tests. 14:30 to 17:30: scorer merge; e2e prints dated windows. 17:30 to 18:30: open YOUR chart's career windows and read every trigger line; if any window feels trigger-thin, raise the floor now. 19:00 e2e. 21:00 review.

**Error traps:** windows over 30 days (the tightening loop must provably terminate); retrograde re-entry duplicates (merge rule collapses them; one fixture uses a retro loop on purpose); 3-day step skipping exact contacts (refinement pass narrows to the day); sub-2-trigger leakage (property test, not spot check).

**Gate:** property tests green on 50 charts; 3 contacts detected; scorer consuming real windows; your own windows read as mechanically justified.
**16:00 cut:** Moon peak days (windows ship without them; return week 1). Analytics event list trims to the core 8.

---

## Day 9. Friday, June 19: RAG corpus + ingestion

**Mission:** a clean, tagged corpus standing in Qdrant. You are an author first today; nobody else can write your rule cards.

**Deliverables**

| Artifact | Acceptance |
|---|---|
| 150+ rule cards, your own words | Career-weighted, all 3 domains covered; Section 15 metadata per card; NO paragraphs lifted from KP Readers or paywalled courses |
| 2-3 permitted transcripts ingested | Tagged via the Section 15 Gemini prompt; only sources you have rights to |
| `scripts/ingest.py` + `rag_chunks` table | Idempotent: content-hash chunk ids; second full run ingests 0 new rows |
| Qdrant collection | 768-dim (text-embedding-004), cosine, payload indexes on domain and houses, created by a committed script, never by hand in a console; 300+ chunks live |
| `rag_retriever.py` skeleton | Hard Qdrant payload filter on domain; sane top-4 for 5 ad-hoc feature queries |
| ANTIGRAVITY: PredictionCard v1 | All 9 card elements per Section 17 against a hand-built fixtures/synthesis_career.json conforming to the Section 16 output schema; confidence ring maps HIGH/MEDIUM/SPECULATIVE to tokens; logic expansion stubbed as a list |

**Schedule.** 09:00 to 12:30: rule cards in batches of 20 against a fixed template; each batch through Gemini Pro for formatting and metadata normalization ONLY; read every card once before it enters the source JSONL; target 100 by lunch. 12:30 to 13:00: Codex builds ingest.py in `agent/codex/ingest`; Claude Code stands up the retriever skeleton. 13:30: 30-card dry-run ingest. 14:30 to 17:00: finish to 150+; ingest all; tag transcripts. 17:00 to 18:00: spot check 30 random chunks, ≥90% tag accuracy, fix or delete every miss on the spot. 18:00 to 18:30: 5 ad-hoc retrievals from real Day 7 feature objects. 21:00: commit source JSONL; snapshot Qdrant; review card PR.

**Error traps:** copyright contamination (cards are your synthesis; clean beats big); tag drift from Gemini (it normalizes format, it does not invent house associations); duplicate chunks under different ids (content-hash + idempotency test); dimension/distance mismatch (the committed creation script is the defense); the card lane inventing fields not in Section 16's schema (the fixture is the contract; if the card needs a field the schema lacks, that is a question for you, not an improvisation).

**Gate:** 300+ chunks live; idempotent re-run proven; spot check ≥90%; 5 sane top-4s; card renders the fixture.
**16:00 cut:** transcripts (rule cards alone can pass tomorrow's gate). Never the spot check.

---

## Day 10. Saturday, June 20: RAG quality gate + synthesis prompt start

**Mission:** measured retrieval at or above the bar by mid-afternoon; a first Gemini prompt producing schema-valid JSON against real payloads by evening. The day the date extension was bought for.

**Deliverables**

| Artifact | Acceptance |
|---|---|
| 25 golden queries | Built from REAL feature objects out of the Day 7-8 pipeline, never synthetic; expected-relevant chunk ids labeled by you |
| Tag-overlap rerank + score floor | Tuned against the golden set |
| The gate, passed and recorded | precision@4 ≥ 0.7, zero cross-domain leaks, written to engine_logs |
| `rag_alignment` feeding the scorer | The 8-point component consumes real status |
| Synthesis payload builder + draft system prompt | Schema-valid JSON on ≥3 of 5 tries in Gemini Pro; every prompt version logged in docs/synthesis-prompt-log.md |
| ANTIGRAVITY (two lanes today): logic-expansion bottom sheet for the card; feedback page | Both against fixtures; mobile bottom-sheet behavior at 360px |

**Schedule.** 09:00 to 10:00: build and label the golden set. 10:00 to 12:30: Claude Code builds the eval runner + rerank; iterate floor and weights against the metric. 12:30 to 13:30: run the gate, then read ALL 25 top-4 sets yourself; the metric can pass while a chunk reads wrong. 13:30 to 14:30: Claude Pro retrieval-review loop on the 5 weakest queries. 14:30 to 16:00: buffer for gate fixes. 16:00: hard decision (cut below). 16:00 to 18:30: synthesis payload builder; iterate the system prompt on 5 real charts inside Gemini Pro (production model family). 21:00: review both Antigravity PRs.

**Error traps:** synthetic golden queries (they measure a corpus you do not have); soft domain filtering (domain must be a hard Qdrant payload filter; one relationship chunk in a career card costs more than the feature earns); Goodharting the floor (if the metric passes but top-4s read worse, you optimized the number); sunk-cost spiraling (the fallback is pre-authorized).

**Gate:** precision@4 ≥ 0.7, zero leaks, recorded; manual read clean; draft prompt 3-of-5 schema-valid.
**16:00 cut, two stages:** first shrink the corpus to rule cards only and re-run. If still failing at 17:00: RAG weight 0, alignment chip reads "chart-only", move fully to synthesis. The product still ships; RAG returns week 1.

---

## Day 11. Sunday, June 21: Synthesis layer + /predict end to end + auth swap + CORS

**Mission:** `POST /predict/{domain}` returns validated synthesis JSON for all three domains in production, the fallback has fired in front of your eyes, and the temporary auth dies.

**Deliverables**

| Artifact | Acceptance |
|---|---|
| `backend/app/engines/gemini_synthesizer.py` | Section 16 complete: response_mime_type JSON with schema; validators IN ORDER (pydantic parse → allowed-entities → tier/probability echo → banned-phrase scan → length caps); one retry with errors appended; then templates/prediction_fallback.j2 with synthesis_mode=template |
| Mocked-Gemini test suite | Five paths green: valid, invalid JSON, invented entity, banned phrase, double failure → template |
| `/predict/{domain}`, `/feedback` endpoints | Caching by (chart_id, domain) until valid_until; cached call < 300ms; tier-locked payloads (full text ABSENT from free finance/relationship JSON, not CSS-hidden); cost logging to engine_logs |
| Auth swap | Supabase Auth magic-link on the frontend; JWT verification on every authed route; RLS on user_charts and predictions; X-User-Id path deleted; hitting another user's chart_id returns 404 |
| CORS + rate limits | FastAPI allowlist = the Vercel production domain only; slowapi limits per Section 20 returning 429 |
| The failure drill | Break the Gemini key in config, hit /predict, watch the template card render, restore. An untested fallback is a rumor |
| 10-chart quality run | ≥8 of 10 career cards pass the Section 25 checklist in Claude Pro |
| ANTIGRAVITY: upgrade modal (payment-link or email-capture variant) + login screen for the auth swap | Against fixtures; Claude Code wires auth |

**Schedule.** 09:00 to 13:00: Claude Code implements the synthesizer (Section 23 Day 11 prompt) then the endpoints. 13:30: 10 charts × career through the Section 25 checklist. 14:30 to 16:00: fix prompt/validator issues; final polish in Gemini Pro. 16:00 to 17:00: auth swap + RLS + CORS (Claude Code; the frontend login screen comes from the Antigravity lane). 17:00 to 17:30: the failure drill. 17:30 to 18:30: deploy backend v1.2.0; run all three domains end to end in prod; verify cost lines. 21:00: review; draft tomorrow's wiring checklist.

**Error traps:** entity invention (Gemini naming a planet or date outside allowed_entities destroys the transparent-logic promise; reject, retry once with the violation named, then template; never soften this to raise the pass rate); validator order reversed (wastes the retry on misleading errors); cache poisoning (a template-mode response must cache cleanly and be replaced on force_refresh; one test covers template-then-refresh); RLS verified by actually requesting another user's chart (expect 404, not trust); CORS misconfigured to `*` (the allowlist is the point).

**Gate:** 3 domains live in prod; 5 mocked paths green; drill witnessed; ≥8/10 checklist; JWT auth on with RLS proven; costs logging.
**16:00 cut:** /predict/history moves to week 2; email-capture variant of the modal instead of payment links. The validator is never cut, never weakened. If the auth swap is fighting you at 17:30, it slips to tomorrow 09:00 with magic-link only, and X-User-Id dies tomorrow instead.

---

## Day 12. Monday, June 22: Wire, mobile QA, launch gate, launch

**Mission:** the full journey works on a 360px phone over mobile data in under 4 minutes, the gate passes at 14:00, and real humans use it tonight. Because Antigravity built components on Days 2 through 11, today is WIRING, not building. That is the payoff of the ramp.

**Deliverables**

| Artifact | Acceptance |
|---|---|
| All components wired to live API | PredictionCard, DashaTimeline, chart summary, planetary details, feedback page, upgrade modal: fixture flags off, live data on, NEXT_PUBLIC_USE_FIXTURE removed from prod |
| 8 analytics events verified arriving | chart_generated, prediction_viewed, logic_expanded, feedback_submitted, returned_after_3d, upgrade_clicked, marked_useful, marked_inaccurate |
| Mobile pass | 360px and 390px on a real device; pickers usable; thumb-reach on feedback buttons; logic expansion as bottom sheet |
| Deployment checklist (Section 21), full run | env vars in prod; /health all-green; 3 real charts end to end in prod; forced Gemini failure shows template; RLS 404 proven; 429s working; disclaimer on every prediction surface; analytics arriving; error tracking captures a test exception; payment link or email capture works; rollback = previous Container Apps revision pinned + previous Vercel deployment noted, each tested once |
| Launch gate at 14:00 | Section 24's good-enough-to-launch list, verbatim. Pass and post, or slip one honest day |
| Soft launch | 10 invites by 18:00 with a specific feedback ask |
| Public push | Same evening if the gate passed clean and the first soft-launch reactions are sane; otherwise the morning of June 23. Both outcomes are wins; only silent slippage is a loss |

**Schedule.** 09:00 to 12:00: wiring sprint, you + Claude Code; Antigravity on standby for component fixes only (no new components today). 12:00 to 13:00: mobile QA on a real phone over mobile data, full journey three times. 13:00 to 14:00: deployment checklist run. 14:00: THE GATE. 14:30 to 17:00: fix the gate's findings or polish copy (ChatGPT Plus drafted launch copy last night). 17:00 to 18:00: soft-launch invites with the feedback ask. Evening: watch engine_logs and analytics; decide the public push. 21:00: fill the final scorecard row either way.

**Error traps:** a component silently still reading its fixture (grep for USE_FIXTURE before the gate); CORS blocking the prod frontend after the Day 11 allowlist (test from the real Vercel domain, not localhost); cold-start latency on first impressions (min replicas 1 stays); launching to the public with a red checklist item because momentum feels good (the gate exists for exactly this moment).

**Gate:** the launch gate IS the gate.
**16:00 cut:** prediction calendar stays a list; D9 Pro view waits; upgrade modal becomes a static "Pro coming this week" note if payments friction appears. Never the disclaimer, never the RLS check, never the failure drill.

---

# 8. Antigravity Lane Backlog (the ramp, in one table)

One lane per day through Day 9, two on Day 10. Every lane: one component, one fixture, one spec source, PR-only, reviewed in the fixed 21:00 slot. If a fixture does not exist by 09:00, the lane skips, never improvises.

| Day | Lane | Fixture it consumes | Spec source | Old-plan day it relieves |
|---|---|---|---|---|
| 2 | Type-gen pipeline + chart.sample.json + lint | schemas/chart.json v1.0 | D009 | (new capability) |
| 3 | Landing page | static sample card JSON | Section 17 | 12 |
| 4 | Birth input extension | none (form logic) | Section 17 | 12 |
| 5 | Chart summary page v1 | chart + dasha fixtures | Section 17 | 12 |
| 6 | DashaTimeline | real dasha fixture | Section 17 / docs/timeline.md | 12 |
| 7 | Planetary details page | chart fixture | Section 17 | 12 |
| 8 | Feedback buttons + analytics.ts + disclaimers | mock event sink | Sections 17, 27 | 12 |
| 9 | PredictionCard v1 | fixtures/synthesis_career.json (Section 16 schema) | Section 17 / docs/card-spec.md | 12 |
| 10 | Logic-expansion sheet; feedback page | synthesis fixture | Section 17 | 12 |
| 11 | Upgrade modal; login screen | none | Sections 17, 18 | 12 |
| 12 | Standby: fixes only | live API | — | — |

Why this is safe where "Antigravity everywhere" is not: nothing here touches engines, scoring, or contracts; every input is a frozen schema or a committed fixture; and the one scarce resource it spends is your 30-minute nightly review, which is capped. The old plan's Day 12 had three parallel lanes building nine card elements, a timeline, and a feedback page from scratch on launch morning. This version makes launch day a wiring day.

---

# 9. Hard Gates (three, unchanged in spirit)

1. **KP gate, June 14 evening:** 25/25 planet sublords exact, 10/10 cusp sublord sets exact, ladder fixtures green. Nothing downstream is built on an unverified 249 table.
2. **RAG gate, June 20, 13:00:** precision@4 ≥ 0.7, zero domain leaks, full manual read. Pre-authorized fallback: RAG weight 0, chart-only chips, retrieval returns week 1.
3. **Launch gate, June 22, 14:00:** Section 24's list verbatim. Pass and post, or slip one honest day.

---

# 10. Post-Launch: the Scalable System (June 23 onward)

The sprint's discipline does not retire at launch; it becomes the operating system. Five permanent mechanisms keep everything in sync and regression-free as you add features:

1. **One contract, generated consumers.** chart.json owns truth. Backend validates with pydantic (extra=forbid); frontend types are GENERATED from the schema (D009). Adding a field = bump schema version, regenerate types, run the full fixture suite. A field can never exist in one layer and not another.
2. **The fixture suite is the permanent regression harness.** The 25 JHora charts, 330 boundary rows, 249-table assertions, golden scoring fixtures, transit property tests, and mocked-synthesis paths run in CI on every push forever. Any future "improvement" to an engine that shifts a sublord goes red before a user sees it.
3. **engine_logs + weekly calibration.** Synthesis fallback rate, cost per prediction, validation failures, and the prediction_feedback verdicts feed a weekly calibration report (the feedback_engine built Day 7). Strength V2 and scoring changes happen only when feedback data shows which signals correlate with "felt accurate". This is the rule that prevents unfalsifiable polish.
4. **Staged deploys.** Backend: new image tag → Container Apps revision → /health → traffic shift, previous revision pinned for instant rollback. Frontend: `vercel` (preview URL) → check → `vercel --prod`. Post-launch, connect the Vercel project to Git properly so every PR gets a preview deployment; that was not worth fighting mid-sprint, it is worth an hour in week 1.
5. **The worktree workflow continues.** One writer per file, spec before code, agents in lanes, you on main. New features enter as docs/<feature>.md first, exactly like engines did.

**Week 1 (Jun 23 to 29): listen and restore.** Triage soft/public-launch feedback daily; restore anything the 16:00 cuts dropped (RAG if cut, Moon peak days, /predict/history, upcoming_pd to 30); wire Razorpay payment links + manual entitlement flip if the email-capture variant shipped; uptime pinger on /health at 1-minute intervals; Sentry DSN live; first weekly calibration report; custom domain on Vercel.

**Weeks 2 to 3: depth on what users touched.** Prediction calendar view (list ships at launch); email follow-up after a window ends; D9 frontend view for Pro; finance/relationship rule packs to full depth with their own golden fixtures; planetary details polish; begin the post-window feedback loop (prediction_events.followup_due is already in the schema).

**Weeks 3 to 6: the V2 math, feedback-gated.** Full Shadbala, Ashtakavarga bindus for transit weighting, Ishta/Kashta, avasthas, vimsopaka, each behind the same fixture-first discipline, each only after calibration data justifies it. Real Razorpay subscription webhooks and a billing portal once paying-intent volume exists. Expert tier (Rs. 1,499) scoping starts here, not before.

**Permanently out until the above is done:** horary, ruling planets, matchmaking, multi-language, native apps, chat interface, health domain (excluded from interpretation scope, full stop).

---

# 11. Daily Scorecard (fill at 21:00, thirty seconds)

| Day | Date | Gate (Y/N) | Ref charts (cum.) | Open bugs | Cut executed | AG lane merged | Tomorrow's first task |
|---|---|---|---|---|---|---|---|
| 1 | Jun 11 | | /5 | | | n/a | |
| 2 | Jun 12 | | /15 | | | | |
| 3 | Jun 13 | | /25 | | | | |
| 4 | Jun 14 | | | | | | |
| 5 | Jun 15 | | | | | | |
| 6 | Jun 16 | | | | | | |
| 7 | Jun 17 | | | | | | |
| 8 | Jun 18 | | | | | | |
| 9 | Jun 19 | | | | | | |
| 10 | Jun 20 | | | | | | |
| 11 | Jun 21 | | | | | | |
| 12 | Jun 22 | | | | | | |

A closing note on pace, updated for what you proved on June 10. You already know you can ship infrastructure under pressure; eight debugging fights ended in a live product. The next four days ask for a different muscle: patience with validation that produces no visible features. Days 1 through 5 will feel slower than your deployment day. That is the design. The deployment day proved the pipes; these days prove the water. By June 18 the math is correct underneath you, the frontend has been quietly assembling itself in the Antigravity lane all along, and the last four days move fast because nothing beneath them is in doubt.
