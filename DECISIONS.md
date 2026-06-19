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
**Date:** 2026-06-15 · **Status:** CLOSED
**Decision:** add an optional `metadata` object to schemas/chart.json, bump schema to
v1.1, regenerate frontend ChartData per D009 in the same PR. Keep metadata optional for
backward safety. Execute BEFORE any KP schema expansion.
**Reason:** chart_engine_version, cache_status, and calculation_mode are trust signals
that belong in the contract, not in a temporary frontend wrapper.
**Outcome:** Closed 2026-06-15 on `agent/codex/schema-metadata-v1-1`. Schema v1.1 legalizes optional strict chart metadata with birth input, geocode, ayanamsa, and engine version fields; frontend ChartData was regenerated from the schema.
**Revisit:** next additive metadata field or KP schema expansion.

## D022 — KP output shape for MVP

**Status:** IMPLEMENTED in schema v1.2
**Date:** 2026-06-16

### Decision

For the MVP, KP output will use a minimal self-contained `kp` object on both planets and houses:

```json
"kp": {
  "star_lord": "Sun",
  "sub_lord": "Venus"
}
```

This shape will be used later during chart integration for:

* `planets[].kp`
* `houses[].kp`

### Reasoning

The MVP needs KP star-lord and sub-lord visibility without over-expanding the schema too early. A two-field object is enough to support meaningful KP-based chart reading while keeping the response shape easy to validate, easy to render, and easy to extend later.

Although `planets[].nakshatra.lord` already represents the star lord, the `kp` object will repeat `star_lord` intentionally so the KP block remains self-contained and readable.

### Deferred fields

The following fields may exist internally inside the lookup engine or tests, but will not be added to the public chart schema yet:

* `sub_index`
* `sub_start_longitude`
* `sub_end_longitude`
* `degree_in_sub`
* `sub_sub_lord`
* KP significators
* KP ruling planets
* KP prediction fields

### Schema versioning

The KP table generator and lookup engine do not change the public chart response shape.

Therefore:

* KP table generator: no schema bump.
* KP lookup engine: no schema bump if it remains internal.
* KP chart integration: bump schema from `1.1` to `1.2`.

### Guardrail

Agents must not invent additional public KP fields during table generation or lookup work. Schema v1.2 should happen only when KP is integrated into chart output.

### Outcome

Implemented 2026-06-16 on `agent/codex/kp-chart-integration`: schema v1.2 adds required strict `kp` blocks to `planets[]` and `houses[]`, with only `star_lord` and `sub_lord`. Public chart assembly copies only those two fields from the internal lookup result, and chart/cache version `1.4.0` plus route schema validation prevent stale pre-v1.2 cached charts from being returned.

## D023 — Significator public-output conflict resolution for v1.2

**Date:** 2026-06-16 · **Status:** LOCKED

### Title

Significator public-output conflict resolution for v1.2.

### Decision

* **D022 remains governing for now.** It deferred public KP significators; that deferral stands.
* Significators are **reserved** in the current model/schema but **must not be populated in public chart output in v1.2**.
* **No agent may invent new public significator fields.**
* The existing fields `houses[].significators`, `planets[].significator_of_houses`, and `planets[].significator_levels` — which are present in `backend/app/schemas/models.py` and `schemas/chart.json` — are **reserved placeholders** until a later founder decision explicitly permits population.
* The only future-compatible public shape under consideration is the existing **A/B/C/D ladder** already in the schema:
  * `houses[].significators.A_in_star_of_occupants`
  * `houses[].significators.B_occupants`
  * `houses[].significators.C_in_star_of_owner`
  * `houses[].significators.D_owner`
  * `planets[].significator_of_houses`
  * `planets[].significator_levels` as a house → `"A" | "B" | "C" | "D"` map
* Do **not** implement the alternative traceable shape (`star_lord_occupies` / `planet_occupies` / `star_lord_owns` / `planet_owns`): it would collide with the existing contract and require schema changes.
* **T4.1** (manual, hand-worked ladders) must happen before any significator engine.
* **T4.2** significator implementation is **Claude Code's lane, not Codex.**
* **Codex may implement `house_engine` only** (T4.3: occupancy via cusp spans, no significators).

### Rationale

* D022 deferred public KP significators, while the schema/model currently contain reserved significator fields — a governance conflict that had to be pinned before anyone implements significators.
* This decision prevents public API drift while preserving forward compatibility (the A/B/C/D ladder already exists, so adopting it later is not a breaking rename).
* It blocks accidental population of significators before manual validation (T4.1) and a future founder go-ahead.

### Revisit

When the founder explicitly authorizes public significator population, after T4.1 hand-worked ladders exist and validate. That entry will supersede this deferral, not the A/B/C/D shape.

## D024 — House occupation uses JHora bhava spans for public occupants

**Date:** 2026-06-16 · **Status:** LOCKED

### Decision

* **Supersede the previous cusp-to-next-cusp house-membership rule** for `planets[].house_occupied` and `houses[].occupants`. The earlier rule (`House H = [cusp_H, cusp_{H+1})`, cusp as the start boundary) passed deterministic tests but failed JHora house-occupation parity.
* Public house occupation must match JHora's "House Start / Cusp / End / Planets in it" table.
* New rule:
  * House H starts at `midpoint(prev_cusp, cusp_H)`.
  * House H ends at `midpoint(cusp_H, next_cusp)`.
  * `cusp_H` is **inside** the house, not the start boundary.
  * Start boundary is **inclusive**; end boundary is **exclusive**.
  * Modular arithmetic across 360° / 0° Aries throughout.
* Boundary formula:
  * `start_H = (cusp_H - ((cusp_H - prev_cusp) % 360) / 2) % 360`
  * `end_H   = (cusp_H + ((next_cusp - cusp_H) % 360) / 2) % 360`
  * Adjacent houses share a boundary exactly (`end_H == start_{H+1}`), so the twelve spans tile the circle with no gap or overlap.

### Evidence

* User 1 Kolkata (1998-08-14 06:45, Kolkata): JHora's 1st house is Start = 2 Leo 50′ 37.27″, Cusp = 17 Leo 25′ 31.92″, End = 1 Virgo 28′ 40.60″, **Planets in it = As, Rahu**. Rahu lies between the 1st-house start and end but before the 1st cusp, so JHora places it in house 1. The old cusp-to-next-cusp rule put Rahu in house 12 — wrong for the public fields.
* Full expected 9-planet occupation for this chart: Rahu→1, Ketu→7, Jupiter→8, Moon→9, Saturn→9, Mars→11, Sun→12, Mercury→12, Venus→12. (JHora also lists Pluto→4 and Uranus/Neptune→6, but public output carries only the 9 classical planets.)

### Scope boundary

* This change affects **only** `house_occupied` and `occupants`.
* **KP cusp star/sub-lord lookup is unchanged.** `houses[].kp.star_lord` / `houses[].kp.sub_lord` are still computed from the **cusp longitude** itself; the cusp-to-next-cusp arc and the cusp point lookup remain valid for KP and must not be changed.
* **No schema bump** — `house_occupied` / `occupants` already exist in v1.2.
* **No significator population** — D023 deferral stands.

### Binds

`backend/app/engines/house_engine.py`, `backend/app/routers/chart.py` (assembly wiring), `docs/houses.md`, TASKBOARD.md T4.3, the User 1 Kolkata regression in `tests/test_chart_integration.py`.

### Revisit

Never for the bhava-span rule itself; the midpoint formula is JHora's definition. Re-examine only if a JHora comparison surfaces an occupancy mismatch on a validated chart.

## D025 — Base KP significator ladder excludes node agency in v1

**Date:** 2026-06-17 · **Status:** LOCKED

### Decision

* **T4.2 implements only the base structural A/B/C/D ladder.** It is an internal engine (`backend/app/engines/significator_engine.py`), validated against the T4.1 hand-worked ladders, and is **not** exposed in the public chart response.
* Rahu and Ketu are treated as **normal planet names** for star-lord matching and as possible occupants.
* This v1 ladder does **not** implement full node agency through sign lord, conjunction, aspect, or representation.
* This is a deliberate internal-only simplification for deterministic fixture validation.
* **Full node agency must be restored before serious prediction/timing launch.**
* Public chart significator fields remain **unpopulated under D023**.

### Base A/B/C/D definition (house-centric)

* **A** = planets whose KP star lord is one of the direct occupants of the house.
* **B** = direct occupants of the house.
* **C** = planets whose KP star lord is the house owner / `cusp_sign_lord`.
* **D** = the house owner / `cusp_sign_lord`.

Planet-centric equivalence (the transpose of the same relation): a planet signifies the houses occupied by its star lord (A), occupied by itself (B), owned by its star lord (C), owned by itself (D).

### Scope (deliberately narrow)

* Include the 9 classical planets only: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu. Outer planets, the Lagna, and house cusps are ignored.
* House owner source is `houses[].cusp_sign_lord`; direct occupants source is `houses[].occupants` (JHora bhava spans, D024); star lord source is `planets[].kp.star_lord`.
* No node sign-lord agency, no conjunction agency, no aspect agency, no sub-lord filtering, no prediction interpretation, no API exposure.

### Evidence

User 1 Kolkata was cross-checked against JHora fallback source tables (Houses tab / D024 occupants, the KP star/sub table, and the "Planets occupying each planet's nakshatra" clipboard table). The real pipeline (ephemeris → KP → bhava-span house occupation → ladder) reproduces all 36 expected house rows across User 1 Kolkata, User 2 Mumbai, and User 5 Siliguri exactly. The fixture `tests/fixtures/jhora/t41_significator_ladders_expected.json` is the judge (AGENTS.md Rule 8).

### Binds

`backend/app/engines/significator_engine.py`, `tests/test_significator_engine.py`, `tests/fixtures/jhora/t41_significator_ladders_expected.json`, TASKBOARD.md T4.2.

### Revisit

When the founder authorizes restoring full node agency (sign lord, conjunction, aspect, representation) and/or lifts D023 to populate the public A/B/C/D ladder. That entry supersedes this simplification, not the base A/B/C/D shape.

## D026 — Node agency precedes career prediction

KP node agency v2 must be built and JHora-validated before `prediction-career-v1`.

Rahu/Ketu are dominant KP significator agents. They can borrow or represent meaning through sign lord, star lord, conjunction, and aspect relationships. Building the career predictor on the current node-blind base ladder would create incomplete prediction inputs and likely force a full predictor re-tune once node agency lands.

Therefore the revised order is:

1. Internal Vimshottari Dasha engine
2. Node agency v2 via `agent/claude/significator-nodes-v2`
3. JHora actual 4-level significator validation
4. `prediction-career-v1`

This supersedes the earlier plan where node agency v2 was deferred until after the first career prediction vertical.

## D027 — Dasha year is true tropical solar years (refines D002's 365.25 placeholder); engine internal-only

**Date:** 2026-06-17 · **Status:** LOCKED

### Decision

* The internal Vimshottari dasha engine (`backend/app/engines/dasha_engine.py`, T5.1) uses **true tropical solar years**, matching the founder's JHora export ("Using true tropical solar years", "Started from Moon"). It is **internal only**: it returns a `DashaTimeline` object and populates **no** public field. `chart.dashas` stays **`null`** under D023. No schema bump (`schema_version` stays `1.2`), no engine version bump (`chart_engine_version` stays `1.4.0`); the chart router does not call it.
* **True tropical solar years are not a fixed-day constant.** A dasha boundary at cumulative time `T` years from the back-projected birth-mahadasha start is the instant the **true/geometric tropical Sun** (Swiss `FLG_SWIEPH | FLG_SPEED | FLG_TRUEPOS`, **no** `FLG_SIDEREAL`) has advanced `T × 360°` of tropical longitude. The Sun's varying speed makes each solar year a slightly different length; the per-mahadasha implied year across the User 1 fixture ranges 365.2415–365.2451 days (cycle mean 365.24278). `MEAN_TROPICAL_YEAR_DAYS = 365.2425` is locked **only** as the transit-solver seed / reference value, never as a period length.
* **This refines the D002 placeholder.** D002 / AGENTS.md §4 / PROJECT_CONTEXT §7 recorded the dasha year as "365.25 days." That was a placeholder; the founder's JHora reference uses true tropical solar years. D027 supersedes the **dasha-year value** in D002 only — every other D002 setting (sidereal, KP-Newcomb ayanamsa, true node, Placidus, JHora as judge) is unchanged. A fixed 365.25 is off by ~60h at PD level on the fixture and must not be used.
* **Birth mahadasha** lord is the Moon's nakshatra lord, read from the existing chart Moon nakshatra block (the Moon is never recomputed). Birth balance = `MD_years × (NAK_SPAN − moon_degree_in_nakshatra) / NAK_SPAN`, `NAK_SPAN = 13.333333333333334°`.
* **Boundaries** are start-inclusive / end-exclusive (an exact boundary belongs to the new period); MD/AD/PD nest proportionally (`MD_years × AD_years / 120`, then `× PD_years / 120`). Output rendered in the birth timezone (Asia/Kolkata for User 1).

### Evidence

User 1 Kolkata (1998-08-14 06:45, Kolkata): the real pipeline (ephemeris → chart Moon block → dasha) reproduces JHora's entire ladder — 9 mahadashas (1992→2112), the Venus and Moon antardasha sets, the Venus/Moon and Moon/Ketu pratyantardasha sets, and the three 2026-06-17 `current_stack` cases — within **~3.8h** (gate: 6h). The residual is the irreducible anchor offset from our Swiss Moon differing from JHora's by ~1″. A fixed-constant-year model (365.25 / 365.24219 / 365.2425) is off by 54–60h at PD level and fails the same tolerance, and the `current_stack` noon case (Moon/Ketu/**Rahu**) only resolves correctly under the Sun-transit model — so the PD tests prove the convention. Fixture `tests/fixtures/jhora/dasha_expected.json` is the judge (AGENTS.md Rule 8); no expected value was adjusted.

### Binds

`backend/app/engines/dasha_engine.py`, `tests/test_dasha_engine.py`, `tests/fixtures/jhora/dasha_expected.json`, `docs/dasha.md`, TASKBOARD.md T5.1. Downstream: D026 (node agency v2 → 4-level significator validation → career prediction) consumes this timeline internally; public exposure waits on a future founder decision lifting D023.

### Revisit

When the founder authorizes public dasha exposure (lifts D023 for the reserved `DashaBlock` shape) and/or adds Sookshma/Prana levels or the User 2 / User 5 dasha fixtures. Never for the true-tropical-solar convention itself — it is JHora's setting and the fixture is the judge.

## D028 — Node agency v2 implemented with AstroSage external comparison; JHora final significator parity pending

**Date:** 2026-06-17 · **Status:** ACTIVE

### Decision

* The internal significator engine (`backend/app/engines/significator_engine.py`) gains a **separate node-aware layer** on top of the unchanged node-blind A/B/C/D base ladder (D025). The base ladder behavior is preserved byte-for-byte and remains the T4.1-fixture judge.
* **Node agency model.** Rahu/Ketu own no sign and act as **agents** for the classical planets they represent, resolved through three deterministic channels: **sign lord** (the dispositor of the node's sign), **conjunction** (classical planets in the same sign), and **aspect** (classical planets casting Parashari sign-based graha drishti onto the node's sign — every planet the 7th, Mars also 4th/8th, Jupiter 5th/9th, Saturn 3rd/10th). The node's **star lord** is already represented by the base ladder, so it is not double-counted.
* **Bidirectional, single-pass.** The node gains the full **node-blind** significations of each agent; reciprocally each agent gains the house the node occupies (nodes own no house). Borrowing reads node-blind significations only, so the pass is order-independent and free of node-to-node feedback; **only the seven classical planets are ever agents** (a node never borrows from a node).
* **Internal only.** Like the base ladder, the node-aware layer returns plain objects, reads the chart read-only, and populates **no** public chart field. `houses[].significators`, `planets[].significator_of_houses`, and `planets[].significator_levels` stay reserved/unpopulated under **D023**. The chart router does not call it. **No `schema_version` change** (stays `1.2`), **no `chart_engine_version` change** (stays `1.4.0`), router output unchanged.
* **AstroSage is an external compatibility reference ONLY, never a judge.** The final planet-to-house / house-to-planet significator table at `tests/fixtures/external/astrosage_user1_significators.json` is from **AstroSage, not JHora**. It is marked `external_reference_only: true`, `is_judge: false`, carries no authority under AGENTS.md Rule 8, and must not be tuned-to: the deterministic rules are implemented for their own sake, then compared. No exact-match was forced.
* **JHora final significator table remains UNAVAILABLE.** JHora's final 4-level (nakshatra / sub / prati-sub / sookshma / praana) significator table and its reverse "Planet Bodies occupying this planet" tables are not available for this chart. **No node-aware output may claim JHora significator parity** until that table exists.

### Evidence

User 1 Kolkata (1998-08-14 06:45): Rahu (Leo, dispositor Sun, house 1) → agent {Sun}; Ketu (Aquarius, dispositor Saturn, house 7) → agents {Saturn, Mars} (Mars's 8th-sign aspect Cancer→Aquarius). The bidirectional rule makes Mars signify house 7. Comparison against AstroSage: **3 of 9 planets match exactly with no tuning (Sun, Mercury, Mars)**; the other six differ, with the nodes diverging most — AstroSage represents both nodes against houses {6,12} while our JHora-bhava occupation (D024) places Rahu in 1 and Ketu in 7, so the node divergence is rooted in a house-placement/convention difference, not the agency rules. The node-blind base ladder still reproduces all 36 T4.1 fixture rows exactly.

### Binds

`backend/app/engines/significator_engine.py`, `tests/test_significator_engine.py`, `tests/fixtures/external/astrosage_user1_significators.json`, `docs/kp-significators.md`, TASKBOARD.md (node agency v2). Consumes/relates to D023 (reserved public fields), D024 (bhava-span occupation), D025 (node-blind base ladder), D026 (node agency precedes career prediction).

### Revisit

When the founder supplies the JHora final 4-level significator table (the real judge). That entry supersedes the AstroSage-comparison-only status, validates or corrects the agency model against JHora, and is the gate for `prediction-career-v1` (D026). Also revisit if the founder authorizes lifting D023 to populate the public A/B/C/D ladder.

## D029 — Internal career prediction v1 is a deterministic evidence scaffold, not a validated predictor

**Date:** 2026-06-17 · **Status:** ACTIVE

### Decision

* The first prediction vertical (`backend/app/engines/prediction_career_engine.py`, `compute_career_prediction(chart, *, as_of)`) is built **internal-first and evidence-first**. Like the significator (D028) and dasha (D027) engines it consumes, it is **internal only**: reads the chart read-only, mutates nothing, is **not** imported by the chart router, populates **no** public field (`chart.dashas` stays `null`, reserved significator fields stay empty under D023), and bumps **no** `schema_version` (1.2) / `chart_engine_version` (1.4.0).
* **Rule/evidence-first, not LLM-first.** The engine produces a structured object; the `summary` is **templated** from the evidence. **No LLM call.** A future narrative layer (separate branch) may wrap the structured output, but the deterministic engine is the source of truth.
* **Model = promise + timing.** *Promise*: for each career house (2 income, 6 service, 10 profession, 11 gains) read the **cusp sub-lord** and the houses it signifies (node-aware, D028); a career house is "promised" when its cusp sub-lord signifies any career house, with the 10th cusp sub-lord as the headline. *Timing*: the current Vimshottari MD/AD/PD lords (D027) and the houses they signify; a career house is "activated" when a current dasha lord signifies it. Supporting houses {1,3,5,9} and challenging houses {8,12} are classified the same way. Every emitted factor cites a real planet and significations taken **verbatim** from the node-aware engine (a test forbids fabrication).
* **Confidence is a transparent heuristic, capped at `medium` in v1.** The engine never claims `high` while the significator foundation is not JHora-validated; `confidence_basis` exposes the raw counts and the cap. Timing is **dasha-period level only** (no transit engine yet — no day-level event dates).
* **Language is safe.** Hedged wording only ("may", "suggests", "indicates", "reflective guidance"); no guaranteed-outcome / job / marriage / wealth claims (enforced by a banned-phrase test); a fixed caveat states it is directional, not definitive, and not financial/medical/legal/professional advice.
* **Validation gap stated, not hidden.** The significators are **AstroSage-compared only (D028), not JHora-validated** — the JHora final significator table is unavailable, and there is **no JHora career oracle**. v1 is therefore a deterministic *evidence scaffold*, **not** a validated predictor. The tests assert mechanics (shape, evidence integrity, timing-depends-on-`as_of`, hedged language, no mutation, public API unchanged), **not** astrological correctness.
* **Founder golden fixtures (≠ JHora oracle), 2026-06-18.** `tests/fixtures/career/career_{supportive,mixed_change,weak_no_signal}_v1.json` + `tests/test_prediction_career_golden.py` add three founder-reviewable career archetypes spanning the tier band (raw `high`→capped `medium`, `medium`, `low`). They carry the engine's **own** deterministic output (reviewed by the founder for reasonableness), **not** JHora ground truth — so they anchor documented v1 *behaviour* + the *safety contract* (no invented planets/houses/dates, no unsafe certainty, confidence capped at `medium`, internal-only), **not** astrological correctness. A JHora career oracle and heuristic tuning still wait on the D026 gate. No production logic changed (the fixtures match current output). See `docs/prediction-career.md` § "Founder golden fixtures".

### Evidence

User 1 Kolkata as of 2026-06-17 12:00 IST: 10th cusp sub-lord **Saturn** signifies [6,7,9] (hits career house 6 → salaried-service signature); current stack **Moon ▸ Ketu ▸ Rahu** activates all four career houses {2,6,10,11} with 8/12 noise; confidence `medium` (raw `high` capped). The PD flips Mars→Rahu exactly on 2026-06-17, so the midnight stack activates {6,10,11} (no 2) — proving timing depends on `as_of`. `tests/test_prediction_career_engine.py` 15 passed; required slice 191 passed; full suite 985 passed.

### Branch / merge order

Built on `agent/claude/prediction-career-v1`, **stacked on `agent/claude/significator-nodes-v2`** (it needs `compute_node_aware_significators`, D028, which is not yet merged) and on the already-merged dasha engine (D027). Founder merge order: **nodes-v2 (D028) → career-v1 (D029)**.

### Binds

`backend/app/engines/prediction_career_engine.py`, `tests/test_prediction_career_engine.py`, `tests/test_prediction_career_golden.py`, `tests/fixtures/career/career_*.json`, `docs/prediction-career.md`, TASKBOARD.md. Consumes D027 (dasha), D028 (node-aware significators); gated by D026 (node agency + JHora 4-level significator validation precede career). 

### Revisit

When (a) a founder golden career fixture exists (hand-scored, mirroring T4.1/T7.1) and/or the JHora final significator table lands (D026) — then correctness validation and heuristic tuning happen and the `medium` cap can be revisited; and (b) the founder authorizes public exposure via a **separate** versioned `POST /predict/career` endpoint (never folded into `/chart/generate`). A narrative LLM layer and the feedback loop are later, separate branches.

## D030 — Internal Career Prediction API wrapper

**Date:** 2026-06-18
**Status:** Accepted
**Owner:** Founder
**Scope:** Backend internal/dev surface only

### Decision

Add an internal-only backend API wrapper for Career Prediction V1 at:

```text
POST /internal/predict/career
```

This route exists only as a development/internal testing surface for the deterministic Career Prediction V1 engine. It is not a public prediction endpoint, not a frontend feature, and not part of `/chart/generate`.

The route accepts an inline `chart` payload and a timezone-aware `as_of`, then calls `compute_career_prediction` without changing engine logic. The response wraps the deterministic output with an internal-only envelope:

```text
internal_only: true
caveat: route-level internal/dev-only warning
as_of: resolved timezone-aware timestamp
prediction: verbatim compute_career_prediction output
```

### Guardrails

The route must remain fail-closed.

Environment gate:

```text
allowed: development, dev, local, test
blocked: production, staging, unknown/anything else
```

Blocked environments return `404`, not `401` or `403`, so the route does not reveal its existence.

Token gate:

```text
INTERNAL_CAREER_API_TOKEN
X-Internal-Career-Token
```

If `INTERNAL_CAREER_API_TOKEN` is set, the request must include the matching `X-Internal-Career-Token` header. Missing or incorrect tokens return `404`. Token comparison should use constant-time comparison. If the token is unset, local/dev/test access is allowed for developer testing.

The environment gate wins: production/staging/unknown must return `404` even with a correct token.

### Request behavior

For v1, the route supports inline chart input only.

```text
chart: required inline ChartData-compatible object
as_of: optional timezone-aware ISO timestamp
chart_id: recognized but unsupported in v1
```

Rules:

```text
- valid timezone-aware as_of → accepted
- missing as_of → safely derived as current UTC timestamp
- naive as_of → rejected with 422
- invalid as_of → rejected with 422
- chart_id → rejected with 400 "unsupported in internal v1"
```

No database chart loading is added in this decision. `chart_id` support is explicitly deferred.

### Non-goals

This decision does not allow:

```text
- public /predict/career
- frontend Career Prediction UI
- exposing Career V1 inside /chart/generate
- Gemini/LLM synthesis
- confidence-cap changes
- schema_version or chart_engine_version bump
- mutation of chart.dashas
- population of reserved significator fields
- db.py changes
- canonical schema changes
- frontend type generation
```

### Rationale

Career Prediction V1 is currently an internal deterministic evidence scaffold. It has passed internal safety/evidence checks, but it is not a validated public predictor. The internal API wrapper provides a safe backend test surface without turning the engine into a user-facing product.

The route is intentionally placed under `/internal` instead of `/predict/career` so the future public prediction API surface remains reserved for a separate founder-approved decision.

### Validation

The implementation must be validated by tests covering:

```text
- internal route returns Career V1 output
- route output matches direct compute_career_prediction output
- public /chart/generate does not expose career prediction
- chart.dashas remains null
- reserved significator fields remain empty
- no unsafe certainty language
- no invented planets, houses, or dates
- valid timezone-aware as_of accepted
- naive/invalid as_of rejected
- missing as_of derives UTC now
- chart_id returns 400 unsupported
- dev/local/test environments can access the route
- production/staging/unknown environments return 404
- missing/wrong token returns 404 when token is configured
- correct token returns 200 only in allowed environments
- production returns 404 even with correct token
```

Observed validation at merge time:

```text
tests/test_internal_predict_career.py: 37 passed
full suite: 935 passed, 115 skipped, 0 failed
```

The skipped tests are pre-existing Swiss-ephemeris-gated tests.

### Files / binds

This decision binds:

```text
backend/app/routers/internal.py
backend/app/main.py
tests/test_internal_predict_career.py
docs/prediction-career.md
HANDOFF.md
TASKBOARD.md
```

Related decisions:

```text
D023 — reserved significator fields remain unpopulated
D026 — JHora final significator validation gate
D027 — internal Vimshottari dasha engine
D028 — node-aware KP significator agency
D029 — Career Prediction V1 internal evidence engine
```

### Future work

A public Career Prediction API or UI requires a separate decision. Before public exposure, founder review and stronger correctness validation are required. The internal route may later support `chart_id` only after a deliberate storage/read contract is designed and tested.

## D031 (2026-06-19) - Landing-page beige-and-navy editorial theme

Landing-page theme set to a premium beige-and-navy editorial two-tone:
beige base (#F6EFE3), near-black text on light, dark navy structure and contrast sections
(#0D1B2A), ivory cards, antique gold accent (#B88A44), with sage (#647A67) and clay
(#A7654B) as semantic-only secondaries. Replaces the prior dark navy background token.
Reason: stronger premium and trust positioning, differentiates from the dark-mystical
category. Tokens in docs/frontend/landing-design-system.md section 2. Scope: landing page.
Chart and prediction surfaces revisit theme separately.
