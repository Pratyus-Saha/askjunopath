# PROJECT_CONTEXT.md
**Read this first in every agent session. Then read AGENTS.md, then your task's spec doc.**
**Last updated: June 12, 2026 (Day 2 morning, post-Day-1 verification). Maintainer: founder. Agents never edit this file.**

> **CONTRACT SYNC ADDENDUM (2026-06-16).** Some point-in-time figures in the body below predate the KP work. Current truth, which wins where it conflicts:
> - Canonical chart object is **schema v1.2** (v1.0 froze D001, v1.1 added metadata D021, v1.2 added KP blocks + removed legacy cusp KP fields D022).
> - **Engine/cache version is `1.4.0`** (`metadata.engine_version`); the v1.2.0 figures in §4/§8 are the Day-1 snapshot.
> - **KP JHora validation is complete and merged** (5 charts × 21 objects; 94 passed, 2 warnings on the relevant slice). Public KP is `planets[].kp.{star_lord, sub_lord}` and `houses[].kp.{star_lord, sub_lord}`.
> - **Next task: `house_engine`** (T4.3, `agent/codex/house-engine`) — occupancy via cusp spans (`docs/houses.md`).
> - **Significators are RESERVED / not populated in v1.2** pending D023.

---

## 1. What AskJunoPath Is

AskJunoPath is a consumer astrology interpretation platform built on Vedic/KP (Krishnamurti Paddhati) astrology. India-first market, globally usable. Web only.

The product promise, in one sentence: a stranger enters birth details and receives an interpretation that names their **actual mahadasha lord**, their **actual cusp sublord**, a **date window under 30 days**, a **confidence tier**, and **expandable planetary logic on screen**, and reports it felt specific to them rather than generic horoscope text.

The differentiator: no consumer product combines KP sublord logic, planetary strength scoring, and retrieval-grounded synthesis of expert references with the reasoning shown on screen. Competitors hide the logic. AskJunoPath shows it.

The architectural law that everything follows: **a deterministic Python engine computes every number; an LLM only explains numbers it is handed. The LLM never calculates and never invents.** If you are an agent and your task seems to require the LLM to compute a position, a date, a score, or a planetary relationship, the task is mis-specified: stop and ask.

---

## 2. The Pipeline (how a prediction is made)

```
birth input (date, time, city, approximate_time flag)
  → geocode + IANA timezone resolution (server-side)
  → ephemeris_engine      sidereal positions, Placidus cusps, ascendant,
                          speed/retro/combustion (Swiss Ephemeris, pyswisseph)
  → nakshatra_engine      nakshatra, pada, navamsa mapping
  → kp_engine             star lord / sub lord / sub-sub lord per planet,
                          cusp sublords, 249-table lookups
  → house_engine          occupants and owners via CUSP SPANS (never by sign),
                          A/B/C/D significator ladder
  → dasha_engine          Vimshottari MD/AD/PD, dated to the day
  → strength_engine       V1 score 0-100, components, STRONG/MODERATE/WEAK tier
  → divisional_engine     D9 and D10 placements + flags
  → transit_engine        90-day windows, ≥2 triggers, ≤30 days each
  → prediction_scoring    domain rule packs (YAML) → raw score → confidence tier
  → rag_retriever         top-4 expert chunks from Qdrant, hard domain filter
  → gemini_synthesizer    structured JSON in, validated JSON out, template fallback
  → frontend              prediction card with all logic expandable
```

Everything above the synthesizer is deterministic and fixture-tested. One canonical `chart.json` object (schema **v1.2**; v1.0 froze the contract and additive bumps followed) is computed once per birth input, stored in Supabase, and read by every downstream stage. Engines never recompute each other's outputs.

Domains in scope: **career, finance, relationship**. Health is excluded from interpretation scope entirely, permanently.

---

## 3. Canonical Backend Paths (corrected June 11; every agent obeys these)

The repo's real layout uses an `app/` segment. The plan documents written before Day 1 say `backend/engines/`; the repo says `backend/app/engines/`. **The repo wins.** Where any plan doc, prompt, or spec references `backend/engines/` or `backend/api/`, translate to the paths below.

```txt
Trusted astrology engines:   backend/app/engines/
Chart route:                 backend/app/routers/chart.py
FastAPI app:                 backend/app/main.py
Schemas:                     backend/schemas/  +  schemas/chart.json
DEPRECATED, never extend:    backend/app/core/chart_engine.py
```

Rules:

```txt
Do not create backend/engines/. The app/ segment is canonical.
Do not use backend/app/core/chart_engine.py for new astrology math.
All new astrology engines live under backend/app/engines/.
```

---

## 4. Live Architecture (deployed and verified as of June 11 night)

| Layer | Tech | Where | Status |
|---|---|---|---|
| Frontend | Next.js (app router) | Vercel, deployed via CLI (`vercel --prod` from `frontend/`) | LIVE: `/` and `/chart` |
| Backend | FastAPI, Python 3.11, port 8000 | Azure Container Apps, app `askjunopath-backend`, env `askjunopath-env`, rg `askjunopath-rg`, region `centralindia` | LIVE: `/health`, `/chart/generate` |
| Image registry | Docker → GHCR | `ghcr.io/pratyus-saha/askjunopath-backend` (public package), tags `vX.Y.Z` | **v1.2.1 in production** |
| Database | Supabase Postgres | project `uiiisvsfankomdcndqao` | LIVE: `user_charts` with chart caching (MISS → HIT verified in prod) |
| Vector store | Qdrant | stands up June 19 | not built |
| LLM | Gemini API | synthesis layer, June 21 | not built |
| Auth | temporary `X-User-Id` header | dies June 21, replaced by Supabase Auth JWT + RLS | temporary |
| Payments | Razorpay payment links + manual entitlement flip | upgrade modal June 21 | not built |

Live backend base URL: `https://askjunopath-backend.kindtree-c857c99f.centralindia.azurecontainerapps.io`

**Version truth (these intentionally differ):**

```txt
Production Docker image tag:    v1.2.1   (bumps per deploy)
App/chart engine version:       1.2.0    (bumps per code/contract change)
```

Production `/health` must show:

```txt
version: 1.2.0
app_env: production
ephemeris: ok, 3 .se1 files at /app/ephe
database: ok
```

Frontend env: `NEXT_PUBLIC_API_URL` only. **No secrets in Vercel, ever.** Service-role keys live only in Azure Container Apps secrets. No secret of any kind appears in this repo or this file.

**Correctness status, updated after Day 1.** The Day 1 retrofit landed: the trusted ephemeris engine (`backend/app/engines/ephemeris_engine.py`) is validated against 5 JHora reference charts, Placidus cusps exist, Swiss `.se1` files are confirmed inside the production image, `/health` asserts them, and `/chart/generate` runs the trusted engine with honest version metadata. The ephemeris BASELINE is now trusted. Everything downstream of it (nakshatra, KP, houses, significators, dasha, divisionals, strengths, transits, predictions) is still null or empty in chart output and remains UNBUILT, not merely unvalidated. Do not treat a populated-looking chart response as complete; check which fields are null.

---

## 5. Docker and Environment Rules (born from the Day 1 version bug)

On Day 1, `.env` was being copied into the Docker image and Pydantic BaseSettings silently loaded stale values from it, so production reported version 1.0.0 after the code said 1.2.0. The rules below exist because of that incident. Never "fix" a config issue by putting `.env` back into the image.

```txt
Never copy .env into Docker images. The image must not contain /app/.env.
backend/.dockerignore excludes .env and .env.*
Production env vars come from Azure Container App secrets/runtime env only.
Local Docker testing may use:  --env-file backend\.env  (runtime only)
```

Swiss Ephemeris files DO ship in the image, deliberately:

```txt
/app/ephe/seas_18.se1
/app/ephe/semo_18.se1
/app/ephe/sepl_18.se1
ENV SE_EPHE_PATH=/app/ephe
```

The `.se1` files are not committed to git but ARE included in the Docker build context. `.dockerignore` must keep allowing them while excluding `.env*`.

Local development ephemeris path: `C:\Users\assas\swisseph\ephe` via `set SE_EPHE_PATH=C:\Users\assas\swisseph\ephe`.

---

## 6. Source-of-Truth Map (where every kind of truth lives)

| Truth | File | Notes |
|---|---|---|
| Execution plan and calendar | `docs/execution-plan-v2.md` | Jun 11 → Jun 22, day pages, gates, cuts |
| Master plan (engine internals, "Section N" references) | `docs/junopath_mvp_plan_jun22.md` | Sections 5-27 remain authoritative for specs |
| Agent rules and lanes | `AGENTS.md` (Codex/Antigravity), `CLAUDE.md` (pointer for Claude Code) | one rulebook |
| Active tasks and file ownership | `TASKBOARD.md` | one file appears in one active task only |
| Locked decisions | `DECISIONS.md` | D001-D009 so far; additions need a dated entry |
| Data contract | `schemas/chart.json` + `backend/schemas/models.py` + `docs/chart-schema.md` | v1.0 frozen June 11; additive changes only, with version bump |
| **Nakshatra/pada/navamsa convention** | `docs/nakshatra.md` | **source of truth for index base, boundary rule, arc-second math, lord table, navamsa formula; KP and dasha boundary logic inherit it** |
| Engine specs | `docs/<engine>.md` (ephemeris, chart-schema, health, nakshatra exist; others created the morning of their build day) | specs win over chat, always |
| Test truth | `tests/fixtures/**` | Jagannatha Hora exports, hand-worked ladders, golden scores |
| Reference software settings | `docs/reference-settings.png` | JHora: KP-Newcomb, Placidus, true node |
| Handoff notes | `HANDOFF.md` / `docs/handoffs/` | every finished task writes one |
| Known bugs | `BUGS.md` | |

The standing rule: when a clarifying question gets answered, the answer is written into the relevant doc FIRST, then echoed in chat. Chat is ephemeral; agents reset between sessions; only files persist.

---

## 7. Locked Astrology Settings (never change these, in any file, for any reason)

| Setting | Value |
|---|---|
| Zodiac | Sidereal |
| Ayanamsa | KP-Newcomb / Krishnamurti (`swe.SIDM_KRISHNAMURTI`) |
| Nodes | True node only; Ketu = Rahu + 180° mod 360 |
| House system | Placidus (`swe.houses_ex`, sidereal flag) |
| Dasha system | Vimshottari, year = 365.25 days, dated to the day |
| Reference judge | Jagannatha Hora, configured per `docs/reference-settings.png` (Drik Siddhanta, KP/Krishnamoorthy ayanamsa, unequal cusps, true/geometric positions) |
| Tolerances | planets ≤ 5 arc-sec, cusps ≤ 0.01°, ascendant exact sign, dasha dates ±1 day |

A consistent few-arc-minute offset on every planet means the ayanamsa is wrong. Rahu alone off by up to 1.5° means mean node leaked in. Positions close-but-off means Moshier fallback (missing `.se1` files at `SE_EPHE_PATH`); `/health` now asserts the files exist precisely to catch this. These three failure signatures are worth memorizing; they cover most of what can silently go wrong.

---

## 8. Engine Inventory and Status (paths corrected; status as of June 12 morning)

| Engine | File | Status | Validated by |
|---|---|---|---|
| Ephemeris | `backend/app/engines/ephemeris_engine.py` | **DONE Jun 11** | 5 JHora charts green (target grows to 25 by Jun 13) |
| Nakshatra/pada | `backend/app/engines/nakshatra_engine.py` | builds Jun 12 | 330 boundary fixtures |
| KP planet level | `backend/app/engines/kp_engine.py` | Jun 13 | 249-table assertions + 25-chart exact match |
| KP cusp + significators | `kp_engine.py` + `house_engine.py` | Jun 14 | 10-chart cusp match + hand-worked ladders |
| Dasha | `backend/app/engines/dasha_engine.py` | Jun 15 | 10-chart dates ±1 day |
| Strength V1 | `backend/app/engines/strength_engine.py` | Jun 16 | component tests + rank-order assertions |
| Divisional D9/D10 | `backend/app/engines/divisional_engine.py` | Jun 16 | 4 hand parity cases |
| Scoring | `backend/app/engines/prediction_scoring.py` + `rules/*.yaml` | Jun 17 | 6 hand-scored golden fixtures ±8 |
| Transits | `backend/app/engines/transit_engine.py` | Jun 18 | property tests, 50 charts |
| RAG | `scripts/ingest.py` + `rag_retriever.py` | Jun 19-20 | precision@4 ≥ 0.7 gate |
| Synthesis | `backend/app/engines/gemini_synthesizer.py` | Jun 21 | 5 mocked paths + Section 25 checklist |

One writer per file. The owner column in TASKBOARD.md decides who that writer is today.

Day 1 verified outcomes, banked: schema v1.0 available; trusted ephemeris engine deployed; production health honest; `.se1` files confirmed in production; chart route wired to the trusted engine; `metadata.engine_version = 1.2.0`; Supabase cache MISS → HIT verified; git main clean.

---

## 9. Frontend Inventory and the Antigravity Lane

Frontend is Next.js on Vercel. Design tokens: navy background, Cormorant Garamond display, DM Sans body, gold accent `#C9A96E` ("Precision Mysticism").

Components arrive one per day via the Antigravity lane (Jun 12 → Jun 21): type-gen pipeline, landing page, birth input extension, chart summary, DashaTimeline, planetary details, feedback + analytics, PredictionCard, logic-expansion sheet + feedback page, upgrade modal + login. June 22 is wiring only.

Three frontend laws:
1. **Types are generated, never hand-written.** `scripts/gen_types.sh` produces `frontend/src/types/chart.ts` from `schemas/chart.json` (Decision D009). Editing the generated file is a rule violation.
2. **Components build against committed fixtures** (`frontend/src/fixtures/*.json`), gated by `NEXT_PUBLIC_USE_FIXTURE`. No live API calls from component lanes during the sprint.
3. **The disclaimer renders on every prediction surface.** Interpretations use probabilistic phrasing (tiers, windows, percentages), never deterministic promises, and the health domain never appears.

---

## 10. Data Conventions

- Canonical chart object: `chart.json` **v1.2** (current; v1.0 was the original freeze), embedded `schema_version`, stored in `user_charts.chart_json` (the column is named `chart_json`, not `chart`; this bit once). Caching key: `chart_fingerprint` per user. Cache rows predating June 11 validation are untrusted and flushed if the Day 1 diff shows drift.
- Nakshatra index is **1-based in API output** (1 = Ashwini, 27 = Revati). Internal code may be 0-based; the schema wins at the boundary. Pada 1-4. Longitudes `[0, 360)`, 4-decimal serialization. Full convention, boundary rule (lower inclusive, upper exclusive; exact 13°20'00" belongs to the next nakshatra), integer arc-second math, and the lord table: `docs/nakshatra.md`.
- **Nakshatra schema shapes, frozen:** `planets[].nakshatra` is a `NakshatraBlock` or null, with exactly these keys and nothing else (`additionalProperties: false`): `name, index, lord, degree_in_nakshatra, pada, degree_in_pada, navamsa_sign`. `houses[].cusp_nakshatra` is a **name string** or null, never an object. Public cusp KP data now lives in `houses[].kp.{star_lord, sub_lord}` (schema v1.2, D022); the legacy separate fields `cusp_star_lord` / `cusp_sub_lord` / `cusp_sub_sub_lord` were **REMOVED in v1.2** and must not be re-added.
- Confidence tiers: 85-100 HIGH, 65-84 MEDIUM, 45-64 SPECULATIVE, <45 weak signal (no forced prediction).
- Strength tiers: 70+ STRONG, 45-69 MODERATE, <45 WEAK.
- Significator levels: A (in star of occupants), B (occupants), C (in star of owner), D (owner).
- Later tables arrive on schedule per master plan Section 19: `predictions`, `prediction_events`, `prediction_feedback`, `analytics_events`, `engine_logs`, `rag_chunks`. Migrations are Codex's lane, additive, reviewed before merge.
- Ports: backend 8000 everywhere. Deploy rituals: `scripts/deploy_backend.sh` (build → tag → GHCR → Container App → /health) and `scripts/deploy_frontend.sh` (`vercel --prod`).

---

## 11. Build Order and Standing Hard Rules

The engine order never changes:

```txt
nakshatra + pada
-> chart output integration
-> KP sublord table (planet level)
-> house occupation (cusp spans)
-> cusp sublords + significators
-> dasha
-> strength / divisionals
-> transits -> scoring -> RAG -> synthesis
```

Do not start prediction synthesis until nakshatra, KP, house occupation, significators, and dasha are correct and validated against Jagannatha Hora.

Standing hard rules, in force every day of the sprint:

```txt
No Docker builds, GHCR pushes, or Azure deploys unless the full local
test suite is green first.
Do not edit schemas/chart.json during engine work; additive changes only,
with founder approval and a version bump.
Do not use backend/app/core/chart_engine.py for new math.
Do not create backend/engines/.
Do not bake .env into Docker images.
Do not implement KP, dasha, predictions, or significators until all 330
nakshatra boundary fixtures are green (docs/nakshatra.md, Day 2 gate).
```

---

## 12. MVP Priorities, Ranked

1. Correct ephemeris and KP math (the foundation; wrong here poisons everything)
2. Dasha engine to PD level, dated to the day
3. Career prediction pipeline done properly (finance/relationship reuse the machinery with different rule packs)
4. Strict, validated synthesis JSON with a template fallback that has been watched firing
5. Prediction card with expandable logic and feedback buttons
6. Soft launch June 22 to 10 real users

## 13. Do Not Build (until post-launch, some never)

Full Shadbala, Ashtakavarga, horary, ruling planets, matchmaking, multi-language, native apps, chat interface, automated subscription billing, calendar polish, D2/D7/D12/D4/D16/D24/D30/D60 divisionals, health-domain interpretation (never). If a task drifts toward any of these, stop and ask.

---

## 14. Mini-Glossary (for agents without astrology context)

- **Nakshatra**: one of 27 lunar mansions, each 13°20' of the zodiac, each ruled by a planet (its "lord"). Subdivided into 4 **padas** of 3°20'.
- **KP sublord chain**: each point in the zodiac has a star lord (nakshatra lord), a sub lord, and a sub-sub lord, from a fixed 249-row proportional table. The **cusp sublord** (the sublord at a house cusp's exact degree) is the heart of KP prediction.
- **Cusp**: the starting degree of a house under Placidus. House membership of a planet is decided by cusp SPANS, never by which sign the planet sits in.
- **Significator ladder**: the A/B/C/D ranking of which planets can deliver a house's results.
- **Vimshottari dasha**: a 120-year planetary period cycle; MD (mahadasha) → AD (antardasha) → PD (pratyantardasha) nesting tells WHEN promised events fire.
- **Ayanamsa**: the sidereal-vs-tropical offset. Get it wrong and every position shifts together.
- **Combustion**: a planet too close to the Sun, weakening it; orb varies per planet.
- **D9/D10 (navamsa/dasamsa)**: harmonic divisional charts; D9 refines dignity and relationships, D10 refines career.

---

## 15. The One-Line Operating System

Specs before code. Fixtures before implementation. One writer per file. Nothing merges red. Reference software is the judge. Agents write code, docs share knowledge, tests decide truth, the founder merges.