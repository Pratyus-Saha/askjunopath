# Junopath MVP Execution Plan
## Build window: Wednesday, June 10 to Monday, June 22, 2026 (13 days, launch on Day 13)

**Owner:** Solo founder. **Stack:** Python/FastAPI + pyswisseph, Supabase Postgres, Qdrant, Gemini API, frontend already deployed on Azure Static Web Apps, backend on Azure Container Apps. **Tooling:** ChatGPT Plus, Claude Pro, Gemini Pro, Codex, Antigravity, Claude Code.

**What changed with the June 22 date:** The original 12-day plan compressed RAG into one day and gave KP one day. Both were the weakest links. The extended runway buys three things: KP gets two full days (it is the differentiator and the most error-prone math), RAG gets two full days plus a retrieval quality gate with golden queries, and June 21 becomes a soft-launch day with real users before the public push on June 22. Nothing else expands. Scope stays frozen.

---

# 1. Executive Summary

Junopath is a consumer astrology interpretation platform. A deterministic Python engine computes the chart: sidereal positions, nakshatra and pada, the KP star lord / sublord / sub-sub lord chain, Placidus cusp sublords, house significators, Vimshottari dasha periods to the pratyantardasha level, a V1 planetary strength score, D9/D10 placements, and 90-day transit windows. A scoring layer converts those features into domain scores and confidence tiers for career, finance, and relationships. Only then does an LLM touch the data. Gemini receives structured JSON plus retrieved expert passages and writes the explanation in plain language with probabilistic phrasing. The LLM never calculates and never invents.

**What the MVP must prove:** that a stranger can enter birth details and receive an interpretation that names their actual mahadasha lord, their actual cusp sublord, a date window under 30 days, a confidence tier, and expandable planetary logic, and that the person reports it felt specific to them rather than generic horoscope text.

**What makes it different:** no consumer product combines KP sublord logic, planetary strength scoring, and retrieval-grounded synthesis of expert references with the reasoning shown on screen. Competitors hide the logic. Junopath shows it.

**Realistic in 13 days:** one domain pipeline done properly (career), then finance and relationships reusing the same machinery with different rule packs. D1 plus D9/D10 backend support. RAG over a curated corpus of 300 to 800 chunks, not thousands. No payments integration beyond Razorpay payment links. No mobile app, web only.

**Not realistic in 13 days:** full Shadbala, Ashtakavarga, horary, ruling planets, multi-language, native apps, automated subscription billing.

---

# 2. Current State Analysis

| Area | Current Status | Problem | Required Next Step |
|---|---|---|---|
| Frontend | Deployed (Azure Static Web Apps), Precision Mysticism design system in place | Shows chart data only; no prediction surface, no logic expansion, no feedback UI | Add prediction page, prediction card component, dasha timeline, feedback buttons (Day 12) |
| Backend | Basic FastAPI service, container builds to ACR | No engine modularity; chart math and API mixed together | Lock module boundaries on Day 1; one file per engine |
| Chart generation | Planet positions working | Ayanamsa and node settings not locked; no reference validation | Set KP-Newcomb ayanamsa + True Node, pass 5-chart longitude check vs Jagannatha Hora (Day 1) |
| Nakshatra / pada | Missing | No pada, no degree-in-nakshatra, no navamsa mapping | Build nakshatra_engine.py with boundary tests (Day 2) |
| KP engine | Missing | No 249 table, no sublords, no cusp sublords, no significators | Two-day build: planet levels Day 3, cusp levels + significators Day 4 |
| Dasha engine | Missing | No MD/AD/PD, no birth balance | Build Day 5, validate against reference software on 10 charts |
| Prediction engine | Missing | No domain rules, no scoring, no windows | Domain rule packs + confidence scorer Day 7, transits Day 8 |
| RAG | Missing | No corpus, no ingestion, no retrieval, no quality measure | Corpus + Qdrant Day 9, retrieval tuning + golden-query gate Day 10 |
| LLM synthesis | Missing | No schema, no validator, no fallback | Strict JSON schema + Gemini prompt + pydantic validator Day 11 |
| Payments | Not built | Full Razorpay subscription flow would eat 2 to 3 days | Use Razorpay payment links + manual entitlement flip; build real billing after validation |
| Feedback capture | Missing | No way to learn if interpretations land | prediction_feedback table + card buttons (Days 7, 12) |
| Analytics | Missing | Cannot measure activation or retention | analytics_events table + 8 tracked events (Day 12) |
| Deployment | Frontend live; backend partially | No health endpoint, no logging discipline, no env checklist | /health, structured logs, env var checklist (Days 1, 12) |
| Testing | Ad hoc | No boundary tests, no reference comparison harness | pytest suite per engine + 25-chart golden file (built daily, gate on Day 13 morning) |

---

# 3. Product Positioning

**One-line positioning:** Junopath shows you the exact planetary logic behind every interpretation, with dates, confidence levels, and the KP reasoning on screen.

**Target users:** people aged 22 to 45 who already consult astrologers or astrology apps and are frustrated by vague output. They want timing, not personality flattery.

**First user segment:** Indian and diaspora users active in KP and Vedic astrology communities on Reddit, YouTube comment sections, and WhatsApp groups. They know what a sublord is. They will catch errors fast, which is exactly what a launch needs.

**User pain:** existing apps output the same Saturn-means-discipline text for everyone. Human astrologers give timing but no transparency, cost Rs. 1,500 to 5,000 per sitting, and require booking.

**Core promise:** every interpretation names the actual dasha lord, the actual sublord, a date window, and a confidence tier. You can expand the logic and check it yourself.

**MVP value proposition:** enter birth details, get your chart, your current dasha stack, and three timed windows per domain with the reasoning shown. Free tier proves specificity; Pro unlocks depth.

**Free vs Pro split (summary, full detail in Section 18):** Free shows the chart, current MD/AD, and one career window with logic. Pro at Rs. 499/month unlocks all three domains, all windows, the 90-day calendar, and D9/D10 views. Expert tier at Rs. 1,499/month is post-launch.

---

# 4. MVP Scope

**Must build before launch (June 22):**
- Ephemeris engine locked to KP-Newcomb ayanamsa, True Node, Placidus cusps
- Nakshatra + pada engine with boundary tests
- KP engine: 249 sublord table, planet star/sub/sub-sub lords, cusp sublords, 4-level house significators
- Vimshottari dasha engine: MD/AD/PD, birth balance, current stack, next periods
- Strength engine V1 (approximation, Section 10)
- D1, D9, D10 backend placements (D9/D10 used in scoring; D9/D10 frontend view is Pro)
- Domain rule packs: career, finance, relationship
- Confidence scoring engine with tiers
- 90-day transit window engine, 3 windows per domain, each under 30 days
- RAG: curated corpus, Qdrant retrieval with metadata filters, golden-query quality gate
- Gemini synthesis with strict JSON schema, validator, deterministic fallback
- Frontend: birth input (exists), chart summary, dasha timeline, prediction page with cards, feedback buttons
- prediction_feedback + analytics_events capture
- Disclaimers on every prediction surface

**Should build if time allows (only if a day finishes early):**
- Prediction calendar view (otherwise list view ships)
- Planetary details page polish (basic version ships regardless)
- Email follow-up after a window ends (otherwise in-app prompt only)
- Upgrade modal with payment link (a static "Pro coming this week" note is acceptable on Day 13)

**Do not build before launch:**
- Full Razorpay subscription webhooks and billing portal
- Full Shadbala, Ashtakavarga, Ishta/Kashta, avasthas
- D2, D7, D12, D4, D16, D24, D30, D60 anywhere in the product
- Horary, ruling planets, muhurta, matchmaking
- Chat interface of any kind
- Multi-language, PDF reports, native apps, social features, blog/SEO
- Health domain (excluded permanently from interpretation scope, not just MVP)

The cut rule: if a day runs more than 4 hours behind, drop the lowest item in that day's task list, never the validation step.

---

# 5. Core Astrological Data Model

One canonical `chart.json` object is computed once per birth input, stored in `charts.chart_data` (JSONB), and passed to every downstream engine. Engines never recompute ephemeris values; they read this object. Schema version is embedded so old charts can be migrated.

Top-level shape:

```json
{
  "schema_version": "1.0",
  "birth": {
    "datetime_local": "1994-03-21T14:35:00",
    "datetime_utc": "1994-03-21T09:05:00Z",
    "timezone": "Asia/Kolkata",
    "lat": 28.4595, "lon": 77.0266,
    "place_label": "Gurugram, India",
    "julian_day_ut": 2449432.87847
  },
  "settings": {
    "ayanamsa": "KP_NEWCOMB",
    "ayanamsa_value_deg": 23.7261,
    "node_type": "TRUE",
    "house_system": "PLACIDUS",
    "zodiac": "SIDEREAL"
  },
  "planets": [],
  "houses": [],
  "dashas": {},
  "strengths": [],
  "divisional": { "d9": {}, "d10": {} },
  "transits": { "computed_at": "...", "windows": [] },
  "prediction_features": { "career": {}, "finance": {}, "relationship": {} }
}
```

**1. Planet object** (one per Sun..Saturn, Rahu, Ketu):

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
  "kp": { "star_lord": "Jupiter", "sub_lord": "Venus", "sub_sub_lord": "Saturn" },
  "significator_of_houses": [3, 6, 10, 11],
  "significator_levels": { "10": "A", "6": "B", "3": "C", "11": "D" }
}
```

**2. House object** (one per cusp 1 to 12):

```json
{
  "house": 10,
  "cusp_longitude": 158.2342,
  "cusp_sign": "Virgo", "cusp_sign_lord": "Mercury",
  "cusp_nakshatra": "Hasta", "cusp_star_lord": "Moon",
  "cusp_sub_lord": "Venus", "cusp_sub_sub_lord": "Mercury",
  "occupants": ["Saturn"],
  "significators": {
    "A_in_star_of_occupants": ["Mercury", "Ketu"],
    "B_occupants": ["Saturn"],
    "C_in_star_of_owner": ["Sun"],
    "D_owner": ["Mercury"]
  }
}
```

**3. Dasha object:**

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

`upcoming_md_ad` holds the next 5 MD/AD pairs; `upcoming_pd` holds the next 30 PD periods.

**4. Strength object** (one per planet):

```json
{
  "planet": "Saturn",
  "v1_score": 64,
  "components": { "dignity": 12, "house_placement": 6, "dig_bala": 0,
                  "retrograde": 0, "combustion": 0, "aspects_net": -4, "base": 50 },
  "tier": "MODERATE",
  "notes": ["own sign Aquarius", "aspected by Mars"]
}
```

**5. Prediction feature object** (input to scorer and to the LLM, one per domain):

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

---

# 6. Astrology Engine Architecture

Each module is one file under `backend/engines/`, pure functions where possible, no module imports another's internals, all consume/extend the chart JSON. FastAPI routes live in `backend/api/` and only orchestrate.

| Module | Responsibility | Inputs | Outputs | Edge cases | Tests needed | Best build tool |
|---|---|---|---|---|---|---|
| ephemeris_engine.py | Julian day, sidereal longitudes, speed, retrograde, combustion, Placidus cusps via pyswisseph | birth datetime, lat/lon, settings | raw planet longitudes, cusp longitudes, ascendant | historical DST, lat > 66° (Placidus undefined: return error code), midnight births, leap seconds ignored | 5-chart longitude match vs Jagannatha Hora within 5 arc-sec; cusp match within 0.01° | Claude Code (precision matters) |
| nakshatra_engine.py | nakshatra, lord, pada, degree-in-nakshatra/pada, navamsa sign | longitude | nakshatra block per planet/cusp | exact 13°20' multiples, 0° Aries, 29°59'59" Pisces, float rounding at boundaries | 30 boundary fixtures, all 108 pada edges | Codex (table-driven) + Claude Pro review |
| kp_engine.py | 249 sublord table, star/sub/sub-sub lord for any longitude, cusp sublords, significator ladder | longitudes, occupants, owners | kp blocks, significator maps | subs straddling sign boundaries, nodes as agents, empty houses, planet exactly on sub boundary | cumulative sub spans sum to 800' per nakshatra; 25-chart exact sublord match vs reference | Claude Code build, Claude Pro logic review |
| house_engine.py | occupant mapping, owner mapping, house-of-planet via cusp spans | cusps, planet longitudes | occupants/owners per house | planet within 0.01° of a cusp, interception irrelevant in Placidus-KP but spans wrap 360° | wraparound fixtures, cusp-edge fixtures | Codex |
| dasha_engine.py | Vimshottari MD/AD/PD from Moon longitude, birth balance, current stack, future periods | Moon longitude, birth datetime | dasha object | balance at nakshatra start/end, periods spanning leap years, PD durations under 10 days | 10-chart date match vs reference within 1 day | Claude Code |
| strength_engine.py | V1 score per planet (Section 10) | planets, houses | strength objects | combust + own sign together, Rahu/Ketu (score via dispositor), exact exaltation degree | rank-order sanity on 10 known charts | Codex build, ChatGPT test-case generation |
| divisional_engine.py | D9 and D10 sign placements | longitudes | divisional block | D10 offset rule for odd/even signs, boundary degrees | formula fixtures for all 12 signs | Codex |
| transit_engine.py | 90-day scan, trigger detection, window merge/trim | natal chart, date range | windows per domain | retrograde re-entry creating duplicate triggers, Moon speed variation, windows overlapping month ends | known-transit fixtures (compute 3 by hand), max-length assertion ≤ 30 days | Claude Code |
| prediction_scoring.py | domain rule packs, confidence score, tier, probability | prediction features | scored feature object | promise true but zero transit triggers, all-blocking charts, score exactly on tier edge | weight unit tests, tier boundary tests, monotonicity test | Claude Code, Claude Pro review |
| rag_retriever.py | query build from features, Qdrant filtered search, tag-overlap rerank | feature object | top-4 chunks + alignment status | empty results, contradictory chunks, low-score floor | golden-query precision@4 ≥ 0.7 | Claude Code |
| gemini_synthesizer.py | prompt assembly, Gemini call, JSON parse, validation, retry, fallback | scored features, chunks | synthesis JSON | invalid JSON, banned phrase present, invented entity, timeout | schema validator tests, banned-phrase tests, fallback path test | Claude Code; prompt iterated in Gemini Pro |
| feedback_engine.py | store feedback, schedule post-window prompts, weekly calibration report | feedback rows | calibration summary | duplicate feedback, feedback after chart deletion | idempotency test, aggregation test | Codex |

Orchestration: `POST /chart/generate` runs ephemeris → nakshatra → kp → house → dasha → strength → divisional and persists. `POST /predict/{domain}` runs transit → scoring → rag → synthesis on the stored chart.

---

# 7. Nakshatra and Pada Engine

The zodiac splits into 27 nakshatras of 13°20' (800 arc-minutes) each. Each nakshatra splits into 4 padas of 3°20' (200 arc-minutes). Every pada maps to one navamsa sign. All of this is pure arithmetic on sidereal longitude, so it should be table-driven and exhaustively boundary-tested.

**Nakshatra table (index, name, lord):** 0 Ashwini-Ketu, 1 Bharani-Venus, 2 Krittika-Sun, 3 Rohini-Moon, 4 Mrigashira-Mars, 5 Ardra-Rahu, 6 Punarvasu-Jupiter, 7 Pushya-Saturn, 8 Ashlesha-Mercury, 9 Magha-Ketu, 10 Purva Phalguni-Venus, 11 Uttara Phalguni-Sun, 12 Hasta-Moon, 13 Chitra-Mars, 14 Swati-Rahu, 15 Vishakha-Jupiter, 16 Anuradha-Saturn, 17 Jyeshtha-Mercury, 18 Mula-Ketu, 19 Purva Ashadha-Venus, 20 Uttara Ashadha-Sun, 21 Shravana-Moon, 22 Dhanishta-Mars, 23 Shatabhisha-Rahu, 24 Purva Bhadrapada-Jupiter, 25 Uttara Bhadrapada-Saturn, 26 Revati-Mercury. The lord sequence is the Vimshottari cycle (Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury) repeated three times.

**Calculations** (longitude `L` in decimal degrees, sidereal, 0 ≤ L < 360):

- `nak_index = floor(L / 13.333333...)` then `lord = VIMSH_ORDER[nak_index % 9]`
- `degree_in_nakshatra = L - nak_index * (40/3)`
- `pada = floor(degree_in_nakshatra / (10/3)) + 1` (1 to 4)
- `degree_in_pada = degree_in_nakshatra - (pada - 1) * (10/3)`
- `navamsa_sign_index = floor(L * 9 / 30) % 12` (this single formula reproduces the classical movable/fixed/dual start rule; verify it on Taurus 0° → Capricorn and Gemini 0° → Libra)

Use `Fraction` or work in arc-seconds (integers) internally to kill float drift at boundaries; convert to float only at the output layer. Define the convention explicitly: a longitude exactly on a boundary belongs to the *next* segment (e.g., L = 13°20'00.000" is Bharani pada 1, not Ashwini pada 4). Document it; reference software follows the same convention.

**Sample output** is the `nakshatra` block inside the planet object in Section 5.

**Boundary testing:** generate fixtures at every multiple of 3°20' minus 1 arc-second, exactly on, and plus 1 arc-second (108 × 3 = 324 cases), plus 0°00'00" and 359°59'59". Assert nakshatra, lord, pada, and navamsa sign for each.

**Frontend display:** on the planetary details page show "Moon in Rohini (Moon's star), Pada 2, 7°41' into the nakshatra, Navamsa: Taurus." Pada and navamsa render as small chips in the design system's gold accent.

**Codex prompt:**

```
Create backend/engines/nakshatra_engine.py. Pure functions, no I/O.
Input: sidereal longitude in degrees (float). Work internally in integer
arc-seconds to avoid float boundary errors.
Functions: nakshatra_index(L), nakshatra_name(L), nakshatra_lord(L),
degree_in_nakshatra(L), pada(L), degree_in_pada(L), navamsa_sign(L),
and nakshatra_block(L) returning the dict matching this schema: [paste
planet.nakshatra JSON from Section 5].
Convention: exact boundary belongs to the next segment.
Constants: 27 nakshatra names in order; lord order
[Ketu,Venus,Sun,Moon,Mars,Rahu,Jupiter,Saturn,Mercury] repeating.
navamsa_sign_index = floor(L*9/30) % 12, signs from Aries.
Also create tests/test_nakshatra_engine.py with the 326 boundary fixtures
described above, parametrized with pytest.
```

---

# 8. KP Engine

This is the differentiator and the highest-risk math in the product. It gets two days (June 12 and 13). Every output must match a trusted reference exactly before anything downstream is built on it.

**Concepts, stated plainly:**

- **Star lord:** the lord of the nakshatra a planet (or cusp) sits in. Saturn at 8° Purva Bhadrapada has star lord Jupiter.
- **Sublord:** each nakshatra's 800' are divided into 9 unequal subs, proportional to Vimshottari years (Ketu 7 → 46'40", Venus 20 → 133'20", Sun 6 → 40'00", Moon 10 → 66'40", Mars 7 → 46'40", Rahu 18 → 120'00", Jupiter 16 → 106'40", Saturn 19 → 126'40", Mercury 17 → 113'20"; total 800'). The sub sequence *starts from the nakshatra's own lord* and proceeds in Vimshottari order. The sublord of a longitude is the lord of the sub it falls in.
- **Sub-sub lord:** apply the same proportional split recursively inside the sub, starting from the sub's lord.
- **Cusp sublord:** compute Placidus house cusps under KP-Newcomb ayanamsa, then take each cusp longitude's sublord. In KP, the cusp sublord decides whether a house's matters are promised.
- **House significator (4 levels, strongest first):** A: planets in the star of the house's occupants. B: the occupants themselves. C: planets in the star of the house's owner. D: the owner. Rahu and Ketu act as agents: they additionally signify through their star lord, their sign dispositor, and planets conjunct them.

**The 249 table:** 27 nakshatras × 9 subs = 243 subs, but some subs straddle sign boundaries; tabulated per sign the segments number 249. Do not hand-type this table. Generate it deterministically: walk the zodiac in arc-seconds, for each nakshatra start at its lord and lay down the 9 spans in Vimshottari order, split any span that crosses a 30° multiple, emit CSV rows (start_arcsec, end_arcsec, sign, nakshatra, star_lord, sub_lord). Assert: 249 rows, spans contiguous, total 1,296,000 arc-seconds, every nakshatra's spans sum to 48,000 arc-seconds.

**Ayanamsa and node:** `swe.set_sid_mode(swe.SIDM_KRISHNAMURTI, 0, 0)` and `swe.TRUE_NODE`. Lock these in `settings` and never make them user-configurable in MVP. A 6 arc-minute ayanamsa mismatch flips sublords near boundaries, which is the single most common way KP software disagrees.

**Event promise logic (used in Section 12):** a house's matters are promised when its cusp sublord is a significator of that house's favorable group (e.g., 10th cusp sublord signifying 2, 6, 10, or 11 promises career advancement). Promise is a boolean gate in scoring, not a guarantee in language.

**Significator strength tiers:** weight A = 1.0, B = 0.8, C = 0.6, D = 0.4 when aggregating; a planet appearing at multiple levels takes its highest level.

**Validation steps:**
1. Generate the 249 table; run the structural assertions above.
2. Take 25 birth charts (your own, family, public figures with verified data, plus edge times). Compute planet sublords and all 12 cusp sublords.
3. Compare against Jagannatha Hora (free, supports KP settings) and one online KP calculator. Require exact lord matches; investigate any cusp longitude differing by more than 0.01°.
4. Hand-verify 3 charts' significator ladders against a worked example from KP literature you own.

**Common failure cases:** wrong ayanamsa constant (Lahiri instead of Krishnamurti); sub sequence started from Ketu instead of the nakshatra lord; mean node instead of true; cusps computed tropically then crudely shifted; float drift at sub boundaries; forgetting node agency in significators; house-of-planet computed by sign instead of by cusp spans.

**Unit tests:** structural table tests; 50 random longitudes cross-checked against the generated table by independent arithmetic; boundary triplets at 20 sub edges; significator ladder fixtures for 3 hand-built houses; node-agency fixtures.

**Claude Pro review prompt:**

```
You are reviewing a KP astrology engine for correctness. Here is
kp_engine.py and the generated sublord table CSV (first 60 rows).
Check: (1) sub spans per nakshatra start at the nakshatra lord and
follow Vimshottari order with year-proportional widths summing to
48,000 arc-seconds; (2) sign-boundary splits produce 249 rows total;
(3) the significator ladder implements A/B/C/D as defined here:
[paste definitions]; (4) Rahu/Ketu agency is applied. List every
deviation with the exact line. Then give 10 adversarial longitudes
near boundaries I should add to tests, with expected star/sub/sub-sub.
```

**Codex implementation prompt:**

```
Create backend/engines/kp_engine.py plus scripts/generate_sublord_table.py.
generate_sublord_table.py: walk 0..1,296,000 arc-seconds; for each of 27
nakshatras (width 48,000 arc-sec) lay 9 subs starting from the nakshatra
lord in Vimshottari order [Ketu 7, Venus 20, Sun 6, Moon 10, Mars 7,
Rahu 18, Jupiter 16, Saturn 19, Mercury 17] with widths years/120*48000;
split spans crossing multiples of 108,000 arc-sec (sign edges); write
data/kp_sublord_249.csv. Assert 249 rows, contiguity, totals.
kp_engine.py: load CSV once; functions star_lord(L), sub_lord(L),
sub_sub_lord(L) (recursive split inside the sub, starting from sub lord),
cusp_kp_block(cusp_longitude), significators(house, occupants_map,
owners_map, planet_star_lords) implementing levels A/B/C/D and Rahu/Ketu
agency via star lord, dispositor, conjunctions within 3°.
Write tests/test_kp_engine.py covering the assertions and boundary
triplets described in comments I will paste.
```

---

# 9. Dasha Engine

Vimshottari runs on a 120-year cycle: Ketu 7, Venus 20, Sun 6, Moon 10, Mars 7, Rahu 18, Jupiter 16, Saturn 19, Mercury 17.

**Birth balance:** the Moon's nakshatra lord is the first mahadasha lord. Elapsed fraction = degree_in_nakshatra / 13°20'. Remaining years of the first MD = lord_years × (1 − elapsed_fraction). Example: Moon at 7°30' into Rohini (lord Moon, 10 years): elapsed 0.5625, balance 4.375 years from birth.

**Mahadasha:** lay the 9 lords from the birth lord onward, each for its full years, after the balance period. **Antardasha:** inside each MD, the 9 lords starting from the MD lord, each spanning MD_years × AD_years / 120. **Pratyantardasha:** same recursion inside each AD: AD_span × PD_years / 120. Use a year of 365.25 days consistently; document it, because reference tools differ by up to a day on this convention.

**Outputs:** birth balance; full MD list to age 100; the current MD/AD/PD stack for today; next 5 MD/AD pairs; next 30 PD periods with exact dates. PD periods can be as short as 9 to 10 days (e.g., Sun PD inside Sun AD inside Sun MD ≈ 10.95 days); store dates to the day, not the month.

**Dasha relevance by domain:** a dasha lord supports a domain when that lord is a significator (any A to D level) of the domain's favorable houses. The scorer (Section 13) weights MD lord 0.45, AD lord 0.35, PD lord 0.20. The PD lord is what makes windows feel timed rather than generic; the MD lord sets the multi-year theme the macro summary describes.

**How dashas shape interpretation:** the LLM must name the actual lords ("the running Venus mahadasha with Saturn antardasha") and tie each window to the PD active during it. If the AD lord blocks (signifies the domain's negative houses at level A or B), the interpretation must say the period is mixed; the scorer already subtracted for it, and the language must not contradict the math.

**Validation:** 10 charts vs reference software; MD/AD start dates within 1 day; PD within 2 days (rounding conventions). Edge fixtures: Moon at 0°00' and 13°19'59" of a nakshatra; a birth where the balance is under 30 days.

---

# 10. Planetary Strength Engine

**V1 ships in MVP.** It is an ordering heuristic, not Shadbala, and the docs must say so internally. Score = 50 base, clamped 0 to 100:

- Dignity: deep exaltation +20 (taper to +12 across the sign), debilitation −20 (taper −12), moolatrikona +15, own sign +12, great-friend/friend +6, neutral 0, enemy −6, great-enemy −10 (natural friendship table only in V1). Exaltation points: Sun 10° Aries, Moon 3° Taurus, Mars 28° Capricorn, Mercury 15° Virgo, Jupiter 5° Cancer, Venus 27° Pisces, Saturn 20° Libra.
- House placement: kendra (1,4,7,10) +6, trikona (5,9) +5, dusthana (6,8,12) −8, else 0.
- Dig bala (simplified): Jupiter/Mercury in 1st, Sun/Mars in 10th, Saturn in 7th, Moon/Venus in 4th: +8.
- Retrograde: +5 for Mars/Mercury/Jupiter/Venus/Saturn (chesta proxy); nodes excluded.
- Combustion (within orb of Sun: Moon 12°, Mars 17°, Mercury 14° / 12° retro, Jupiter 11°, Venus 10° / 8° retro, Saturn 15°): −15.
- Aspects (graha drishti, 3° orb on the aspected point): from Jupiter +5; from Saturn, Mars, or a node −4 each.
- Rahu/Ketu: score = 0.7 × dispositor score + 0.3 × star lord score, flagged `derived: true`.

Tiers: 70+ STRONG, 45 to 69 MODERATE, below 45 WEAK. WEAK significators trigger softer language and a score penalty (Section 13). Validate by rank order: on 10 known charts, an exalted unafflicted planet must outrank a debilitated combust one; do not chase absolute numbers.

**V2 waits (post-launch, weeks 3 to 6):** full six-fold Shadbala, Ashtakavarga bindus for transit weighting, Ishta/Kashta phala, avasthas, composite varga strength (vimsopaka). Build V2 only after feedback data shows which strength signals correlate with "felt accurate" ratings; otherwise it is unfalsifiable polish.

---

# 11. Divisional Chart Strategy

- **D1 (rasi):** the product. Everything runs on it.
- **D9 (navamsa):** MVP, backend-on. Already free from the pada mapping. Used in scoring: a domain planet in the same sign in D1 and D9 (vargottama) gets +4 strength; a relationship significator debilitated in D9 gets −4. Frontend D9 view is a Pro screen if Day 12 has slack, otherwise week 2.
- **D10 (dasamsa):** MVP, backend-only. Tenth-of-a-sign divisions; odd signs count from the sign itself, even signs from the 9th sign onward. Used only as a career modifier: 10th lord well placed in D10 +3, in D10 dusthana −3. No frontend.
- **D2, D7, D12, D4, D16, D24, D30, D60:** postponed entirely. None in backend, none in UI, no schema slots beyond the generic `divisional` object. Each adds interpretive surface without adding to the three launch domains, and D60 in particular is hypersensitive to birth-time error your users cannot certify.

Rule: a divisional chart enters the product only when a domain rule consumes it.

---

# 12. Domain Interpretation Logic

Shared machinery, three rule packs. Each pack defines house groups, then the scorer (Section 13) and transit engine (Section 14) do the rest. Language is always probabilistic; these rules produce *indications*, and every output carries its confidence tier.

## Career

- Relevant house: 10 (status, role). Supporting: 2 (income), 6 (service, daily work), 11 (gains, recognition). Secondary support: 9 (fortune, mentors).
- Blocking: 5 (12th from 6th: leaving a role), 9 (12th from 10th: status change), 12 (loss, exit), 8 (obstruction). The 1-5-9-12 cluster together indicates job *change* rather than growth.
- Dasha logic: MD/AD/PD lords signifying {2,6,10,11} support; signifying {1,5,9,12} at level A/B flag change/exit.
- KP logic: promise gate = 10th cusp sublord signifies any of {2,6,10,11}. If the 10th cusp sublord signifies {5,9,12} more strongly, frame outputs around transition, not advancement.
- Transit triggers: Saturn or Jupiter aspecting/conjunct the 10th cusp or its sublord's natal position; Sun or the PD lord transiting the star of a career significator; Moon transit refines peak days.
- Event types: responsibility growth, role change, recognition window, workload expansion, new-opportunity window, friction-with-authority caution.
- Positive indicators: promise true; ≥2 dasha lords supporting; supporting significators STRONG; clustered transit triggers.
- Negative indicators: AD lord signifying 5/9/12 at level A; 10th occupants WEAK and afflicted; Saturn transit square the 10th cusp during the window.
- Example interpretation candidate: "Responsibility growth is moderately indicated between July 12 and 28. Your running Venus mahadasha and Saturn antardasha both connect to the 10th and 11th houses through KP significators, and Saturn's transit contacts your 10th cusp sublord's position in this span. Saturn tends to add structure and delay rather than sudden recognition, so this window favors expanded scope or serious project ownership. Confidence: MEDIUM (68%)."

## Finance

- Relevant houses: 2 (holdings, income), 11 (inflow, gains). Supporting: 6 (recovery of dues, loans received), 10 (earned income).
- Blocking: 12 (outflow), 8 (others' money, dues, shocks), 5 (speculative drain when afflicted).
- Dasha logic: lords signifying {2,11} (with 6/10 as amplifiers) support inflow; lords signifying {5,8,12} at A/B indicate outflow-heavy spans.
- KP logic: promise gate = 2nd or 11th cusp sublord signifying {2,6,10,11}. 8th/12th-dominant sublords shift framing to caution-and-review.
- Transit triggers: Jupiter contacting the 2nd/11th cusps or their sublords' positions; PD lord transiting stars of 2/11 significators; Venus transits as minor amplifiers.
- Event types: income-rise window, large-expense caution span, dues-recovery window, financial-decision review window.
- Hard rule: never name instruments, returns, or actions ("invest", "buy", "exit"). Frame as "a span where money decisions deserve slower review" or "inflow indications strengthen." This is a product boundary, enforced in the synthesis validator.
- Example candidate: "Inflow indications strengthen between August 3 and 19. The Mercury pratyantardasha lord signifies your 2nd and 11th houses at the strongest KP level, and Jupiter's transit contacts the 11th cusp in this span. The 12th-house link through Saturn suggests parallel outflows, so the net effect reads as improved but not free-flowing. Confidence: MEDIUM (61%). This is reflective guidance, not financial advice."

## Relationship

- Relevant house: 7 (partnership). Supporting: 2 (family bond), 5 (romance), 11 (companionship, fulfillment of desire).
- Blocking (separative, standard KP): 1, 6, 10; plus 12 for distance/withdrawal when dominant.
- Dasha logic: lords signifying {2,7,11} support commitment; {5,7,11} support new connection; {1,6,10} at A/B indicate strain or distance.
- KP logic: promise gate = 7th cusp sublord signifying any of {2,7,11}. Venus's condition (strength tier, D9 placement) modulates tone.
- Transit triggers: Venus or Jupiter contacting the 7th cusp or its sublord's position; PD lord through stars of 7th significators; Mars contacts mark friction days inside a window.
- Event types: new-connection window, commitment-deepening window, reconciliation window, strain caution, important-conversation window.
- Positive indicators: promise true, Venus MODERATE+, 7th sublord unafflicted, ≥2 lords supporting. Negative: separative cluster at level A/B, Venus combust, Saturn square the 7th cusp in-window.
- Example candidate: "A connection-supportive span shows between July 1 and 14. The Venus mahadasha ties to your 7th and 11th houses, and Venus transits the star of your 7th cusp sublord during this window. With Saturn also a 6th-house significator, the same span may surface a pending disagreement; the chart supports honest conversation more than smooth sailing. Confidence: SPECULATIVE (52%)."

Each pack lives in `backend/rules/{domain}.yaml`: house groups, weights, event-type templates, banned framings. The scorer reads YAML; adding a domain later means adding a file, not code.

---

# 13. Confidence Scoring Engine

One function turns a prediction feature object into a score, a tier, and a probability. Weights live in YAML so calibration never requires a deploy. These numbers are internal confidence estimates of indication strength. They are not outcome guarantees, and the UI copy must say so.

**Components (max 100 before penalties):**

| Component | Max | Source |
|---|---|---|
| Event promise (cusp sublord gate) | 25 | kp_engine |
| Dasha support (MD .45 / AD .35 / PD .20) | 20 | dasha + significators |
| KP sublord support quality (level A=1.0 … D=0.4) | 15 | kp_engine |
| House significator coverage (favorable houses covered by active lords) | 10 | kp_engine |
| Planetary strength of supporting lords (avg tier) | 10 | strength_engine |
| Transit trigger quality (count, tightness, slow-planet involvement) | 12 | transit_engine |
| RAG alignment (aligned +8 / mixed +3 / none 0) | 8 | rag_retriever |
| **Penalties:** blocking lords at A/B −5 to −12; WEAK supporting lords −4; promise false caps total at 44; zero transit triggers caps at 60 | | |

**Tiers (per spec):** 85 to 100 HIGH; 65 to 84 MEDIUM; 45 to 64 SPECULATIVE; below 45 weak signal, never rendered as a prediction card (it may appear as one neutral line in the macro summary: "no strong career indication in this 90-day span").

**Probability mapping (linear within tier):** HIGH → 75 + (score−85)/15×20, giving 75 to 95%. MEDIUM → 55 + (score−65)/19×20. SPECULATIVE → 40 + (score−45)/19×15. Probabilities round to whole numbers and are clamped to the tier range.

**Pseudocode:**

```python
def score_domain(f: PredictionFeatures, w: Weights) -> ScoredFeatures:
    s  = w.promise * (1.0 if f.event_promise else 0.0)
    s += w.dasha * dasha_support_ratio(f)          # 0..1 weighted MD/AD/PD
    s += w.kp * best_level_quality(f)              # A..D mapped 1.0..0.4
    s += w.coverage * house_coverage(f)            # favorable houses hit / total
    s += w.strength * avg_strength_norm(f)         # mean v1/100 of supporters
    s += w.transit * transit_quality(f)            # 0..1 from window scores
    s += w.rag * rag_factor(f.rag_alignment)       # 1.0 / 0.375 / 0.0
    s -= blocking_penalty(f) + weak_lord_penalty(f)
    if not f.event_promise: s = min(s, 44)
    if not f.transit_windows: s = min(s, 60)
    raw = clamp(round(s), 0, 100)
    tier = tier_for(raw)                           # HIGH/MEDIUM/SPECULATIVE/WEAK
    prob = prob_for(raw, tier)
    return ScoredFeatures(**f.dict(), raw_score=raw,
                          confidence_tier=tier, probability_pct=prob)
```

**JSON output:** the prediction feature object in Section 5 with `raw_score`, `confidence_tier`, `probability_pct` filled.

**Tests needed:** weight sum sanity (max achievable = 100); tier boundaries at 44/45, 64/65, 84/85; monotonicity (adding a supporting lord never lowers the score); promise-false cap; zero-transit cap; penalty stacking floor at 0; golden fixtures for 6 hand-scored charts (2 per domain) reviewed once in Claude Pro.

**Codex implementation prompt:**

```
Create backend/engines/prediction_scoring.py implementing the pseudocode
in docs/scoring.md [paste the block above plus the component table].
Weights load from backend/rules/weights.yaml with these defaults:
promise 25, dasha 20, kp 15, coverage 10, strength 10, transit 12, rag 8.
Implement tier_for and prob_for exactly per the ranges given. All helpers
pure and unit-testable. Create tests/test_prediction_scoring.py covering:
tier boundary values 44,45,64,65,84,85; monotonicity property test with
hypothesis; promise-false cap; zero-transit cap; penalties floor at 0.
```

---

# 14. Transit Window Engine

A 90-day scan from today, producing at most 3 windows per domain, each 7 to 30 days, each justified by named triggers.

**Trigger catalog (planet → meaning → orb on natal points):**

- Moon: day-level timing refinement only; never creates a window alone. Orb 3°, contacts last hours.
- Jupiter: supportive/expansion contacts to domain cusps and significator positions. Orb 1°.
- Saturn: structure, delay, consolidation contacts. Orb 1°. A Saturn trigger shifts window framing toward "structured/slow" wording.
- Venus: relationship and inflow amplifier. Orb 1.5°.
- Mars: action, friction, conflict marker; inside relationship windows it flags friction days. Orb 1.5°.
- Rahu/Ketu: slow drift; treat station-like exact contacts to cusps as sudden-change markers. Orb 1°.
- Sun/Mercury: minor amplifiers via star-level transits (below).

**Natal contact points per domain:** the domain's primary and supporting cusps; natal positions of the cusp sublord and top significators; and star-level transits: any current dasha lord (MD/AD/PD) entering the *nakshatra* of a domain significator counts as a trigger for its whole stay in that star (capped at 30 days).

**Window construction:**
1. Scan day-by-day (slow planets can step 3 days, Moon daily) and emit raw trigger intervals.
2. Keep only intervals involving a current dasha lord, the domain cusp sublord, or Jupiter/Saturn. This kills broad useless windows: a random Venus trine to a random planet does not qualify.
3. Merge overlapping intervals; require ≥2 independent triggers for a window to surface (1 trigger allowed only if it is the PD lord on the primary cusp sublord's star).
4. Trim: if a merged window exceeds 30 days, tighten orbs stepwise (1° → 0.75° → 0.5°) until ≤30, else split at the trigger-density minimum. Target median length 10 to 18 days.
5. Score each window: Σ trigger weights (slow planet 3, dasha-lord star transit 3, Venus/Mars 2, Sun/Mercury 1) × tightness × PD-overlap bonus (×1.3 when the window sits inside a supporting PD).
6. Return top 3 with ≥7 days separation; attach Moon-refined peak days (up to 3 dates) inside each.

**Connection to dasha and KP:** windows do not exist independently; each carries `dasha_context` (which PD is running) and `kp_context` (which sublord/star is being triggered), and the scorer's transit component reads window scores. A window outside any supporting dasha period is rendered with explicitly weaker language by rule.

**Tests:** hand-compute 3 known transit contacts for June to August 2026 and assert detection; assert no window exceeds 30 days across 50 random charts; assert ≥2-trigger rule; assert separation rule.

---

# 15. RAG Knowledge Base

This is the area your date extension funds, so it gets a quality bar, not just a pipeline. Goal for June 22: 300 to 800 high-precision chunks with clean metadata and a measured retrieval score, not thousands of noisy ones. Small and curated beats large and scraped.

**Source types, in priority order:**
1. Self-authored rule cards: your own condensed KP rules written as one claim per card ("When the 10th cusp sublord signifies 2-6-10-11 during a supporting dasha, role advancement is indicated; Saturn involvement colors it as slow/structured"). Highest precision, zero copyright risk, fastest to produce. Target 150 to 250 of these; this is a writing task you are uniquely able to do fast.
2. YouTube transcripts from KP/Vedic creators, ideally ones you are already approaching for review outreach; ask permission, which doubles as a relationship-builder. Tag each chunk with creator attribution.
3. Licensed or public-domain Jyotisha material and your own lecture notes.
4. Community Q&A you author from recurring Reddit questions.

**Copyright note:** do not bulk-ingest copyrighted KP books (the KP Readers are copyrighted). Summarize rules in your own words as rule cards instead. Cleaner legally, and rule cards retrieve better than book prose anyway.

**Chunking strategy:** one claim per chunk, 120 to 350 tokens. For transcripts: segment by topic shift (Gemini does this well), then rewrite each segment into rule-card form rather than storing raw speech. Raw transcript chunks retrieve poorly; rewritten cards retrieve precisely. Store the raw source span reference for traceability.

**Metadata JSON (Qdrant payload):**

```json
{
  "chunk_id": "kp_0231",
  "text": "When the 10th cusp sublord signifies houses 2, 6, 10 or 11 ...",
  "tradition": "KP",
  "domain": ["career"],
  "planets": ["Saturn", "Venus"],
  "houses": [2, 6, 10, 11],
  "dasha_lords": ["Saturn"],
  "event_types": ["role_advancement"],
  "polarity": "supportive",
  "source": { "type": "rule_card", "author": "Junopath", "ref": "RC-031" },
  "quality": 0.9,
  "ingested_at": "2026-06-18"
}
```

**Qdrant collection design:** collection `astro_chunks`; vectors 768-dim (Gemini `text-embedding-004`), cosine distance, HNSW defaults; payload indexes (keyword/integer) on `domain`, `houses`, `planets`, `dasha_lords`, `tradition`, `polarity`. Qdrant Cloud free tier covers this corpus comfortably.

**Retrieval query format:** queries are built from the *feature object*, never from raw user text. Template: `"KP {domain} indication: {primary} cusp sublord {X} signifying houses {list}; dasha {MD}-{AD}-{PD}; transit {trigger summary}"`. Filter: `domain` must match; `should`-boost on overlap with active dasha lords and favorable houses. Fetch top 12 by vector score with filters, then tag-overlap rerank: rerank_score = 0.55 × vector + 0.25 × house overlap + 0.20 × planet/dasha overlap; keep top 4; drop anything below a floor (start 0.55, tune on Day 10). No LLM reranker in MVP.

**How RAG influences interpretation:** retrieved chunks (a) set `rag_alignment` (aligned / mixed / none) feeding the scorer's 8 points, (b) give the LLM tradition-grounded phrasing and the `expert_alignment` field on the card, and (c) supply at most one paraphrased expert framing per window. RAG never overrides chart math: if chunks contradict the deterministic score, alignment = mixed, the score stands, and the card shows "expert sources are mixed on this combination." The math is auditable and chart-specific; retrieved text is general commentary. Inverting that hierarchy would reintroduce exactly the hallucination class the architecture exists to prevent.

**Quality gate (Day 10, blocks Day 11):** 25 golden queries built from real feature objects, each with hand-labeled relevant chunk IDs. Require precision@4 ≥ 0.7 and zero cross-domain leaks. Below the bar: fix tags and floors, or shrink the corpus to curated cards only. A smaller aligned corpus passes; a bigger noisy one does not.

**Gemini Pro prompt, transcript tagging:**

```
You will receive a transcript segment from a KP astrology lecture.
Rewrite it as 1-3 rule cards. Each card: a single testable claim in
under 60 words, neutral tone, probabilistic phrasing. Then output JSON
array matching this schema exactly: [paste metadata JSON]. Rules:
only tag planets/houses/dasha_lords explicitly stated; polarity is
supportive/blocking/neutral; if the segment contains no rule, output [].
Do not invent astrology. Output JSON only.
```

**Codex prompt, ingestion pipeline:**

```
Create backend/rag/ingest.py: read data/rag_sources/*.jsonl (fields:
text, source). For each item call Gemini for rule-card extraction using
prompts/tagging.txt, validate against schemas/chunk.json (pydantic),
embed text with text-embedding-004, upsert to Qdrant collection
astro_chunks with payload = metadata. Idempotent via chunk_id hash of
(source.ref + text). CLI: --dry-run, --limit N, --reembed. Log a one-line
summary per item. Create tests with a mocked Gemini/Qdrant client.
```

**Claude prompt, retrieval quality review:**

```
Here are 25 golden queries with retrieved top-4 chunks and my relevance
labels [paste]. For each miss, classify the cause: bad tags, chunk too
broad, query template weak, floor too high, corpus gap. Then propose:
(1) the 5 highest-impact tag fixes, (2) one query-template change,
(3) which chunks to delete outright. Be specific; quote chunk_ids.
```

---

# 16. LLM Synthesis Layer

Model: Gemini Flash (current generation) via API with `response_mime_type: application/json` and a response schema; Flash keeps per-prediction cost low and latency under ~6s. Pro-tier model is a manual fallback if Flash quality disappoints on Day 11, decided by side-by-side on 10 charts.

**The LLM receives:** the scored feature object, the dasha stack with names and dates, KP context strings, the 3 transit windows, the top-4 chunks, the domain rule pack's event-type templates, and an `allowed_entities` list (every planet, lord, house, and date the validator will accept).

**The LLM returns (strict schema):**

```json
{
  "domain": "career",
  "macro_summary": "string, <=80 words, names the MD and AD lords",
  "windows": [
    {
      "start": "2026-07-12", "end": "2026-07-28",
      "headline": "string <=12 words",
      "event_description": "string <=70 words",
      "confidence_tier": "HIGH|MEDIUM|SPECULATIVE",
      "probability_pct": 68,
      "dasha_context": "string naming MD/AD/PD lords",
      "kp_context": "string naming cusp sublord and signified houses",
      "planetary_logic": ["3-6 short factual strings"],
      "expert_alignment": { "status": "aligned|mixed|none", "refs": ["kp_0231"] },
      "reflection": "string <=40 words, an action of self-review, never an instruction to act in the world",
      "risks": "string <=40 words"
    }
  ],
  "feedback_question": "string <=20 words",
  "disclaimer": "For self-reflection and planning. Not medical, legal, or financial advice."
}
```

Exactly 3 windows when the engine supplies 3; fewer only if the engine supplied fewer. `confidence_tier` and `probability_pct` must echo the scorer's values verbatim.

**Gemini system prompt (production, abridged):**

```
You are the explanation layer of Junopath, an astrology interpretation
product. You receive pre-computed chart facts. You NEVER calculate,
NEVER add astrological facts, NEVER change dates, scores, tiers, or
probabilities. Every planet, lord, house, and date you mention must
appear in ALLOWED_ENTITIES. Use probabilistic language: "indicates",
"suggests", "shows a stronger possibility", "the chart supports",
"the signal is weaker". Forbidden: "you will definitely", "certainly",
"guaranteed", "this will happen", "destiny", any medical, legal,
investment, or trading suggestion, any instruction to buy, sell, quit,
or confront. If inputs conflict, present the tension plainly. If
rag_alignment is "mixed" or "none", say expert sources are mixed or
that this reading rests on chart logic alone. Write at a 9th-grade
reading level. Output only JSON matching the provided schema.
```

**Hallucination prevention and validation (post-generation, code not prompt):**
1. `json.loads` + pydantic schema parse.
2. Entity check: every capitalized planet/lord/house token and every date in the output must be in `allowed_entities`; windows must match engine windows exactly.
3. Tier/probability echo check against scorer output.
4. Banned-phrase scan (case-insensitive list incl. the four forbidden phrases, "definitely", "will happen", "invest", "buy", "sell", "quit your", "leave him/her", "diagnos", "lawsuit", "medication").
5. Length limits per field.

**Fallback behavior:** on any failure, retry once with the validator errors appended to the prompt. On second failure, render the deterministic template (Jinja2 over the scored features: same card, machine-phrased), set `synthesis_mode: "template"`, and log to `engine_logs`. The product never errors out to the user because Gemini had a bad minute, and the template path is also your offline regression baseline.

---

# 17. Frontend Product Experience

Design language is already set (deep cosmic navy, Cormorant Garamond display, DM Sans body, gold #C9A96E accents). Build nothing decorative on Day 12; reuse existing tokens and components.

## Landing Page
- Purpose: state the promise (timed, transparent, KP-grounded interpretations) and route to birth input in one click.
- Components: hero with one real anonymized prediction card as the visual, three-line "how it works" (calculate → score → explain), CTA, disclaimer footer.
- Data: one static sample card JSON.
- Mobile: card stacks under hero; CTA pinned.
- Acceptance: loads under 2s on 4G; CTA above the fold on a 360px screen; disclaimer visible without scrolling past one screen.

## Birth Input Page (exists, extend)
- Purpose: capture date, time, place with timezone resolved automatically.
- Components: date/time pickers, place autocomplete → lat/lon, "time accuracy" toggle (exact / approximate), submit.
- Data: geocoding + timezonefinder on backend.
- Mobile: native pickers; one field per row.
- Acceptance: an approximate-time flag persists to the chart and softens cusp-dependent language; invalid future dates blocked; generation completes or errors visibly within 8s.

## Chart Summary Page
- Purpose: orient the user in 20 seconds: ascendant, Moon nakshatra/pada, current MD/AD/PD, three domain entry tiles.
- Components: chart wheel (existing), "right now" dasha strip, domain tiles with score-tier chips, "view planetary details" link.
- Data: chart JSON + dasha current stack + domain tier summaries.
- Mobile: wheel collapses to a toggle; dasha strip first.
- Acceptance: MD/AD/PD lords and end dates render correctly for 10 test charts; tiles deep-link to the prediction page with domain preselected.

## Planetary Details Page
- Purpose: the transparency surface for chart geeks; doubles as trust-builder.
- Components: per-planet rows: sign, house, nakshatra + pada chips, KP star/sub/sub-sub lords, strength bar with component tooltip, significator houses.
- Data: planets + strengths arrays.
- Mobile: accordion per planet.
- Acceptance: every value matches backend JSON exactly (rendered from API, never recomputed client-side).

## Dasha Timeline
- Purpose: show the running periods and the next changes.
- Components: horizontal MD bar with AD segments, "today" marker, expandable PD list (next 10), per-period lord chips.
- Data: dasha object.
- Mobile: vertical timeline.
- Acceptance: today marker accurate; PD dates match engine to the day.

## Prediction Page (the core screen)
- Purpose: deliver the three windows for a domain with full logic.
- Components: domain switcher, macro summary block, three prediction cards, weak-signal line when applicable, disclaimer.
- Prediction card must include: event description; confidence ring (tier color + %); date window; dasha badge ("Venus MD · Saturn AD"); KP sublord badge ("10th CSL: Venus → 2,10,11"); expert alignment chip (aligned / mixed / chart-only); expandable planetary logic (the 3-6 strings + window triggers); actionable reflection; feedback buttons (useful / not useful / too vague) with optional one-line comment.
- Data: synthesis JSON + scored features.
- Mobile: cards full-width; logic expansion as bottom sheet; feedback buttons thumb-reachable.
- Acceptance: card renders all 9 elements from one JSON; expanding logic fires `logic_expanded` event; tier ring color maps HIGH/MEDIUM/SPECULATIVE consistently; SPECULATIVE cards visually quieter than HIGH.

## Prediction Calendar (should-build)
- Purpose: 90-day strip with windows as colored spans across domains.
- Components: month strip, span bars, tap → card.
- Data: windows arrays.
- Mobile: vertical month list.
- Acceptance: spans match card dates exactly; overlapping domains stack.

## Feedback Page
- Purpose: post-window check-in ("Your July 12-28 career window ended. Did anything in this area shift?").
- Components: ended-window list, three-option response, optional text, thank-you state.
- Data: prediction_events where end < today and no feedback.
- Mobile: single column.
- Acceptance: response writes one prediction_feedback row; answered items leave the list.

## Upgrade Modal
- Purpose: convert at the moment of blur (locked domains/windows).
- Components: blurred-content backdrop, Free vs Pro table, Rs. 499/month with 7-day trial note, Razorpay payment-link button, "not now".
- Data: static + payment link URL.
- Mobile: full-screen sheet.
- Acceptance: fires `upgrade_clicked`; dismissal never blocks free content; if payments are deferred, button reads "Pro opens this week, leave your email" with a working capture.

---

# 18. Free vs Pro Strategy

**Free tier:** full chart generation, chart summary, planetary details, dasha timeline (MD/AD visible, PD list truncated to next 3), career domain with window #1 fully visible; windows #2 and #3 show headline + date range with body blurred; finance and relationship tiles visible with tier chips but cards locked.

**Pro, Rs. 499/month (7-day trial):** all three domains, all windows, full PD list, prediction calendar, D9/D10 views when shipped, monthly regeneration of the 90-day scan, full logic expansion everywhere.

**Future Expert tier, Rs. 1,499/month (post-launch):** PDF yearly report, priority "ask about this window" written responses, early features. Do not design it now.

**What is blurred vs hidden:** blur, never hide. Blurred cards with visible headlines and confidence rings demonstrate that depth exists; hidden content demonstrates nothing.

**Payments timing:** do not build subscription infrastructure before June 22. Ship a Razorpay payment link + a `subscriptions` row flipped manually within an hour of payment (you are solo; at launch volume this is minutes per day). If even the link feels like drag on Day 12, ship the email-capture variant and open payments in week 2. The launch question is "does anyone feel this is specific enough to want more," and that gets answered without a billing system. Build real Razorpay subscriptions + webhooks only after ≥10 people pay or 50 click upgrade.

---

# 19. Database Schema

Supabase Postgres. RLS on for all user-facing tables; backend writes via service role; policy pattern `user_id = auth.uid()` for select/insert where noted.

**users** — id uuid pk (= auth.users.id), email text, display_name text, tier text default 'free', created_at timestamptz, last_seen_at timestamptz. Index: email unique. RLS: user reads/updates own row, no deletes from client.

**charts** — id uuid pk, user_id uuid fk→users, birth jsonb, settings jsonb, chart_data jsonb (full chart object), schema_version text, approximate_time bool, created_at. Indexes: (user_id, created_at desc); GIN on chart_data optional, skip for MVP. RLS: owner-only select/insert; updates server-only.

**predictions** — id uuid pk, chart_id uuid fk, domain text check in ('career','finance','relationship'), scored_features jsonb, synthesis jsonb, synthesis_mode text ('llm'|'template'), model text, raw_score int, confidence_tier text, generated_at timestamptz, valid_until date. Indexes: (chart_id, domain, generated_at desc). RLS: owner via chart join, select only.

**prediction_events** — id uuid pk, prediction_id uuid fk, window_start date, window_end date, headline text, probability_pct int, followup_due date (= window_end + 1), followup_done bool default false. Index: (followup_due) where followup_done = false. RLS: owner select.

**prediction_feedback** — id uuid pk, prediction_event_id uuid fk, user_id uuid, verdict text check in ('useful','not_useful','too_vague','happened','partly','did_not'), comment text, created_at. Unique (prediction_event_id, user_id, verdict_phase). RLS: owner insert/select.

**rag_chunks** — chunk_id text pk, text text, metadata jsonb, embedding_synced bool, quality numeric, created_at. (Vectors live in Qdrant; this is the source of truth + re-embed queue.) Index: GIN on metadata. RLS: service-role only.

**subscriptions** — id uuid pk, user_id uuid fk, tier text, status text ('trial','active','expired','manual'), payment_ref text, started_at, expires_at. Index: (user_id, status). RLS: owner select; writes server-only.

**engine_logs** — id bigserial pk, scope text (engine name), chart_id uuid null, level text, payload jsonb, created_at. Index: (scope, created_at desc). 30-day retention via scheduled delete. RLS: service-role only.

**analytics_events** — id bigserial pk, user_id uuid null, event text, props jsonb, created_at. Index: (event, created_at desc). RLS: insert via anon allowed for client events with event-name allowlist enforced in API; select service-role only.

---

# 20. API Design

FastAPI, JWT from Supabase Auth on every authed route, JSON errors `{ "error": { "code", "message" } }`. Rate limits via slowapi keyed on user id (IP for anon).

**POST /chart/generate** — Auth: required. Body: `{ datetime_local, timezone?, lat, lon, place_label, approximate_time }` (timezone resolved server-side from lat/lon when omitted). 200: `{ chart_id, chart: <chart JSON> }`. Errors: 422 invalid input; 400 LAT_UNSUPPORTED (|lat| > 66°, Placidus undefined); 409 duplicate identical birth for user (returns existing chart_id); 500 EPHEMERIS_FAIL logged. Rate: 10/hr. Acceptance: p95 < 2s warm; identical input is idempotent; engine_logs row written on failure.

**GET /chart/{chart_id}** — Auth: owner. 200: chart row. 404 if not owner (no 403 leak). Rate: 120/hr. Acceptance: never recomputes; serves stored JSON.

**POST /predict/{domain}** — Auth: owner of `chart_id` in body. Body: `{ chart_id, force_refresh?: bool }`. Runs transit → scoring → RAG → synthesis; caches by (chart_id, domain) until `valid_until` (generated_at + 30 days) unless force_refresh (Pro only). 200: `{ prediction_id, synthesis, scored_features, synthesis_mode }`. Errors: 402 TIER_LOCKED for free users on finance/relationship full output (returns blurred-safe payload instead: headlines, dates, tiers only); 503 SYNTHESIS_UNAVAILABLE only if template fallback also fails (should be near-impossible). Rate: 6/hr free, 20/hr Pro. Acceptance: cached second call < 300ms; synthesis_mode recorded; weak-signal domains return `windows: []` + macro line, never an error.

**GET /predict/history/{chart_id}** — Auth: owner. Query: domain?, limit (default 10). 200: list of predictions with events. Rate: 60/hr. Acceptance: ordered desc; includes feedback status per event.

**POST /prediction/{prediction_id}/feedback** — Auth: owner. Body: `{ prediction_event_id, verdict, comment? }`. 200: `{ ok: true }`. Errors: 409 duplicate phase. Rate: 60/hr. Acceptance: idempotent per phase; fires analytics event server-side.

**GET /users/me** — Auth: required. 200: `{ id, email, tier, charts_count, subscription }`. Rate: 120/hr.

**POST /rag/ingest** — Auth: admin token (env-var match), never user JWT. Body: `{ items: [{text, source}], dry_run }`. 200: `{ ingested, skipped, errors[] }`. Rate: none (admin). Acceptance: idempotent on chunk_id hash; dry_run writes nothing.

**GET /health** — Auth: none. 200: `{ status, version, ephemeris: ok, db: ok, qdrant: ok, gemini: ok|degraded }` with sub-checks under 1s timeouts. Acceptance: returns degraded rather than failing when only Gemini is down.

---

# 21. Infrastructure and Deployment

Keep what is already provisioned; do not migrate anything before June 22.

- **Frontend:** Azure Static Web Apps (live). Deploy from main via existing GitHub Action.
- **Backend:** FastAPI container → Azure Container Registry → Azure Container Apps. Min replicas 1 (cold starts kill first impressions), max 3, 0.5 vCPU / 1 GiB to start. Swiss ephemeris data files baked into the image at /app/ephe; set `SE_EPHE_PATH`.
- **Database/Auth:** Supabase (Postgres + Auth + RLS). Free tier is fine through launch week.
- **Vectors:** Qdrant Cloud free tier (1 GiB), one collection.
- **LLM/Embeddings:** Gemini API. Log token counts and cost per call into engine_logs; alert yourself in the nightly review if cost/prediction drifts above your budget line.
- **Env vars (Container Apps secrets):** SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_JWT_SECRET, GEMINI_API_KEY, QDRANT_URL, QDRANT_API_KEY, ADMIN_INGEST_TOKEN, SE_EPHE_PATH, APP_ENV, SENTRY_DSN (optional).
- **Logging:** structured JSON to stdout → Container Apps Log Analytics; engine_logs table for domain-level events (synthesis fallbacks, validation failures, cost).
- **Monitoring:** /health wired to a free uptime pinger at 1-min intervals; nightly query of engine_logs error counts.
- **Backups:** Supabase automated backups + a weekly `pg_dump` to Azure Blob Storage; export Qdrant snapshot after each ingest day; rag source JSONL files committed to the repo.
- **Deployment checklist (run June 21 evening and June 22 morning):** env vars present in prod; /health all-green; 3 real charts generated end-to-end in prod; one forced Gemini failure shows template fallback; RLS verified by hitting another user's chart_id (expect 404); rate limits return 429; disclaimer renders on prediction page; analytics events arriving; error tracking capturing a test exception; payment link or email capture working; rollback = previous Container Apps revision pinned and tested once.

---

# 22. Tool Allocation Plan

| Tool | Role | Best Tasks | Do Not Use For | Example Prompt |
|---|---|---|---|---|
| Claude Code | Primary implementation agent inside the repo | Engines with precision math (ephemeris, KP, dasha, scoring, transits), refactors, wiring tests into CI, multi-file changes with tests run locally | Long open-ended ideation; producing astrology rules from memory without your review | "Implement dasha_engine.py per docs/dasha.md; run pytest; fix until green; do not change the schema." |
| Codex | Parallel boilerplate generator | Table generators (249 CSV), pydantic schemas, CRUD endpoints, ingestion pipeline, fixtures, YAML rule-pack scaffolds | Subtle math you have not specified line-by-line; anything touching scoring weights | Section 8 implementation prompt |
| Antigravity (Mission Control) | Parallel agent lanes | Frontend card/timeline components in one lane while backend continues in another; repo-wide chores (lint, type hints); Day 11-12 integration branches | The KP engine or scorer (keep single-threaded human review on the differentiator) | "Lane 1: build PredictionCard per docs/card-spec.md against fixtures/synthesis.json. Lane 2: DashaTimeline per docs/timeline.md. Open PRs separately." |
| Claude Pro (chat) | Logic validator and reviewer | KP rule review, scoring-weight critique, adversarial test cases, prompt design for Gemini, reviewing interpretation samples against the quality checklist | Generating large code files (that is Claude Code's job in-repo) | Section 8 review prompt |
| Gemini Pro | Production-model twin | Transcript tagging, rule-card rewriting, synthesis prompt iteration (same model family as prod), JSON-schema adherence testing | Chart math of any kind; final code review | Section 15 tagging prompt |
| ChatGPT Plus | Second opinion + test generation | Independent review of scoring logic, edge-case brainstorming, launch copy drafts, quick library questions | Being a third implementation lane (context fragmentation costs more than it saves) | "Here is prediction_scoring.py and its spec. Find cases where tier output contradicts the spec. Respond as a failing-test list." |

**Daily workflow (IST):**
- 08:30 Morning planning (Claude Pro): paste yesterday's nightly notes + today's roadmap block; get a task-ordered plan with risks; adjust, freeze.
- 09:00–13:00 Build block A (Claude Code on the day's engine; Codex in parallel on that day's boilerplate; Antigravity lane on frontend backlog from Day 10 onward).
- 13:30 Logic validation (Claude Pro + reference software): run the day's outputs against Jagannatha Hora / hand calcs; file discrepancies as failing tests before fixing.
- 14:30–18:30 Build block B (fix discrepancies first, then continue; merge Codex/Antigravity PRs only after their tests pass locally).
- 19:00 Integration check: run the end-to-end script (birth → chart → predict career) on 3 charts; eyeball one card.
- 21:00 Nightly review (ChatGPT Plus or Claude Pro, alternate): paste diffs summary + open issues; produce tomorrow's prompt drafts and the cut-list candidate if behind. 30 minutes, hard stop.

---

# 23. Execution Roadmap: June 10 to June 22 (13 days)

The extra day versus the old 12-day plan goes to KP (now two days) and RAG (now two days), with June 21 as soft launch. Every day ends with the integration script green on 3 charts.

**Day 1 — Wed Jun 10: Repo audit, schema lock, ephemeris hardening**
- Goal: frozen contracts; trustworthy raw positions.
- Tasks: audit repo into engines/api/rules layout; commit `schemas/chart.json` v1.0 (Section 5) + pydantic models; ephemeris_engine: SIDM_KRISHNAMURTI, TRUE_NODE, Placidus via `swe.houses_ex`, combustion/retro flags, SE_EPHE_PATH in Docker; /health.
- Tools: Claude Code (engine), Codex (pydantic models + /health), Claude Pro (schema review).
- Prompt: "Refactor backend into engines/, api/, rules/, schemas/ per this tree [paste]. Then implement ephemeris_engine.py per docs/ephemeris.md: KP-Newcomb ayanamsa, true node, Placidus sidereal cusps, speed and retrograde, combustion orbs [paste table]. Add tests comparing 5 fixture charts to expected longitudes I provide."
- Manual validation: 5 charts vs Jagannatha Hora (same ayanamsa setting): planets within 5 arc-sec, cusps within 0.01°, ascendant exact sign/degree.
- Done: schema committed; 5-chart fixture test green; /health green in prod container.
- Risk: ayanamsa mismatch silently poisoning everything downstream. Cut if behind: repo cosmetics; not the validation.

**Day 2 — Thu Jun 11: Nakshatra + pada engine**
- Goal: Section 7 complete.
- Tasks: nakshatra_engine.py, navamsa mapping, 326 boundary fixtures, wire into chart JSON, planetary-details API fields.
- Tools: Codex (build from Section 7 prompt), Claude Pro (boundary-convention review), Claude Code (integration).
- Prompt: Section 7 Codex prompt.
- Manual validation: Moon nakshatra/pada for 10 charts vs reference; 3 boundary charts by hand.
- Done: 326 fixtures green; chart JSON carries full nakshatra blocks.
- Risk: float drift at boundaries. Cut: nothing; this day is small by design, spillover buffer for Day 1.

**Day 3 — Fri Jun 12: KP engine, planet level**
- Goal: 249 table generated and verified; star/sub/sub-sub for any longitude.
- Tasks: generate_sublord_table.py + assertions; kp_engine planet-level functions; boundary triplets; wire planets' kp blocks.
- Tools: Codex (generator per Section 8 prompt), Claude Code (engine + tests), Claude Pro (Section 8 review prompt).
- Manual validation: 25-chart planet sublord comparison vs reference: exact match required.
- Done: structural assertions pass; 25/25 exact; review prompt findings filed as tests.
- Risk: sub sequence not starting at nakshatra lord (classic bug). Cut: sub-sub lord display (keep computation).

**Day 4 — Sat Jun 13: KP engine, cusp level + significators**
- Goal: cusp sublords and the A/B/C/D ladder with node agency.
- Tasks: cusp_kp_block for 12 cusps; house_engine occupant/owner maps with cusp-span house assignment; significators(); houses array in chart JSON.
- Tools: Claude Code (build), Claude Pro (3 hand-built ladder fixtures review), Codex (house_engine).
- Prompt: "Implement significators() in kp_engine.py per this definition [paste Section 8 ladder + node agency]. Build the 3 fixtures in tests/fixtures/significators/ I describe here [paste hand-worked houses] and make them pass."
- Manual validation: all 12 cusp sublords vs reference on 10 charts, exact; ladder for 3 charts vs your hand work.
- Done: houses array complete; fixtures green; 10/10 cusp match.
- Risk: house-of-planet by sign instead of cusp spans. Cut: significator strength tiers default to flat weights (restore Day 7).

**Day 5 — Sun Jun 14: Dasha engine**
- Goal: Section 9 complete.
- Tasks: dasha_engine.py (balance, MD/AD/PD recursion, current stack, next 5 MD/AD, next 30 PD); dasha timeline API field; edge fixtures.
- Tools: Claude Code (build + tests), ChatGPT Plus (adversarial date cases), reference software.
- Prompt: "Implement dasha_engine.py per docs/dasha.md [paste Section 9]. Year = 365.25 days. Provide current_stack(date) and upcoming lists. Tests: 10 fixture charts with expected MD/AD dates [paste from reference runs], balance edge cases at nakshatra start/end."
- Manual validation: 10 charts vs reference, MD/AD within 1 day, PD within 2.
- Done: fixtures green; chart JSON dashas block complete; your own chart's current PD verified by eye.
- Risk: balance convention off by elapsed-vs-remaining inversion. Cut: upcoming_pd list to next 10 (restore later).

**Day 6 — Mon Jun 15: Strength V1 + D9/D10**
- Goal: Sections 10 and 11 MVP scope.
- Tasks: strength_engine.py with component breakdown; divisional_engine.py D9 (reuse navamsa) + D10; vargottama/D9-debility modifiers exposed as flags for the scorer.
- Tools: Codex (both engines from specs), ChatGPT Plus (rank-order test charts), Claude Code (integration).
- Prompt: "Implement strength_engine.py per this component table [paste Section 10]. Return score, components dict, tier, notes. Rahu/Ketu derived rule as specified. Tests: per-component unit tests + rank-order assertions for these 10 charts [paste]."
- Manual validation: rank-order sanity on 10 charts; D10 odd/even offset verified for 4 hand cases.
- Done: strengths array + divisional block populated; tier chips render from real data in a scratch page.
- Risk: over-tuning absolute scores. Cut: D10 modifier (flag only, weight 0) if the day slips.

**Day 7 — Tue Jun 16: Domain rule packs + confidence scoring**
- Goal: Sections 12 and 13 complete; scored features for all three domains.
- Tasks: rules/{career,finance,relationship}.yaml; prediction_scoring.py per Section 13; feature-builder assembling the Section 5 feature object; weak-signal path; feedback_engine skeleton + prediction tables migration.
- Tools: Claude Code (scorer per Section 13 Codex prompt, then review), Claude Pro (weight critique + 6 hand-scored golden fixtures), Codex (YAML scaffolds + migrations).
- Manual validation: score 6 known charts by hand against engine output; tier boundaries; one all-blocking chart lands in weak signal.
- Done: scorer tests green incl. monotonicity; 3 domains produce scored features end-to-end (transit fields stubbed empty).
- Risk: weights encoding your hopes instead of KP logic; the Claude Pro critique is the check. Cut: finance/relationship YAML to minimal house groups (event-type templates Day 9 morning).

**Day 8 — Wed Jun 17: Transit window engine**
- Goal: Section 14 complete; real windows feeding the scorer.
- Tasks: transit_engine.py (scan, trigger catalog, merge/trim, ≥2-trigger rule, scoring, Moon peak days); connect to scorer's transit component; window fixtures.
- Tools: Claude Code (build), ChatGPT Plus (verify 3 hand-computed Jun–Aug 2026 contacts), Claude Pro (window-quality eyeball on 5 charts).
- Prompt: "Implement transit_engine.py per docs/transits.md [paste Section 14]. Slow planets step 3 days, Moon daily. Enforce: ≥2 triggers, ≤30-day windows via orb tightening, top-3 with 7-day separation, PD-overlap bonus. Tests: detection of these 3 known contacts [paste], plus property tests for the three constraints across 50 random charts."
- Manual validation: for your own chart, do the 3 career windows feel mechanically justified when you read the triggers? If any window is trigger-thin, raise the floor.
- Done: constraint property tests green; scorer consumes real windows; end-to-end produces dated, scored features.
- Risk: windows too broad → generic product. Cut: Moon peak days (ship windows without them).

**Day 9 — Thu Jun 18: RAG corpus + ingestion**
- Goal: corpus standing in Qdrant with clean metadata.
- Tasks: write 150+ rule cards (yes, by hand, batched through Gemini for formatting); ingest 2-3 permitted transcripts via the tagging prompt; ingest.py per Section 15; rag_chunks table; Qdrant collection + payload indexes; first retrieval smoke tests.
- Tools: Gemini Pro (tagging/rewriting), Codex (ingest.py per Section 15 prompt), Claude Code (rag_retriever.py skeleton), you (rule-card authorship; nobody else can do this part).
- Manual validation: spot-check 30 random chunks for tag accuracy ≥ 90%; delete or fix misses immediately.
- Done: 300+ chunks live; ingest idempotent; retrieval returns sane top-4 for 5 ad-hoc feature queries.
- Risk: corpus too thin in finance/relationship. Cut: transcripts (rule cards alone can pass the gate); never cut tag spot-checks.

**Day 10 — Fri Jun 19: RAG quality gate + synthesis prompt start**
- Goal: measured retrieval ≥ bar; Gemini prompt drafted against real payloads.
- Tasks: build 25 golden queries from real feature objects; tag-overlap rerank + floor tuning; run gate (precision@4 ≥ 0.7, zero domain leaks); Claude retrieval-review loop (Section 15 prompt); afternoon: assemble synthesis payload builder + first Gemini prompt iterations on 5 charts in Gemini Pro.
- Tools: Claude Code (rerank + eval harness), Claude Pro (review loop), Gemini Pro (prompt iteration).
- Manual validation: read all 25 golden top-4 sets yourself once; the metric can pass while a chunk reads wrong.
- Done: gate passing and recorded in engine_logs; rag_alignment feeding scorer; draft system prompt producing schema-valid JSON on 3 of 5 tries (validator finishes tomorrow).
- Risk: gate fails late in the day. Cut: shrink corpus to rule cards and re-run; if still failing, ship rag weight = 0 and alignment chip = "chart-only" (the product still works; RAG returns post-launch week 1). This is the pre-authorized fallback the date extension exists to avoid, so spend the morning well.

**Day 11 — Sat Jun 20: Synthesis layer + prediction API end-to-end**
- Goal: `POST /predict/{domain}` returns validated synthesis JSON for all 3 domains.
- Tasks: gemini_synthesizer.py (Section 16: schema, system prompt, entity/echo/banned-phrase validators, retry, Jinja2 template fallback); prediction caching + valid_until; /predict, /predict/history, /feedback endpoints; tier-locked blurred payloads; cost logging.
- Tools: Claude Code (everything), Gemini Pro (final prompt polish), Claude Pro (run 10 outputs through the Section 25 checklist).
- Prompt: "Implement gemini_synthesizer.py per docs/synthesis.md [paste Section 16]. response_mime_type application/json with schema. Post-validate: pydantic parse, allowed-entities check, tier/probability echo check, banned-phrase scan [paste list], field length caps. One retry with errors appended, then render templates/prediction_fallback.j2 and set synthesis_mode=template. Tests: mocked-Gemini paths for valid, invalid-JSON, invented-entity, banned-phrase, double-failure."
- Manual validation: 10 charts × career through the Section 25 checklist; ≥8 must pass; forced-failure path shows the template card.
- Done: 3 domains end-to-end in prod; validator tests green; one deliberately broken Gemini key run produces a template card, not an error.
- Risk: Gemini drifting outside allowed entities. Cut: /predict/history (week 2); never the validator.

**Day 12 — Sun Jun 21: Frontend prediction experience + soft launch**
- Goal: the product is usable on a phone; 10 humans use it.
- Tasks: prediction page + card (all 9 elements), dasha timeline, chart summary tiles, feedback page, upgrade modal (link or email-capture variant), analytics events (8 from Section 27), mobile pass at 360px, deployment checklist first run; evening: send to 10 friends/community contacts with the feedback ask.
- Tools: Antigravity lanes (card / timeline / feedback page in parallel against fixture JSON), Claude Code (API wiring + fixes), you (mobile QA on a real device).
- Prompt (Antigravity Lane 1): "Build PredictionCard per docs/card-spec.md [paste Section 17 card list] using existing design tokens (navy bg, Cormorant display, DM Sans, gold #C9A96E). Consume fixtures/synthesis_career.json. Confidence ring maps HIGH/MEDIUM/SPECULATIVE to [tokens]. Logic expansion = bottom sheet on mobile. Emit logic_expanded and feedback events via analytics.ts."
- Manual validation: full journey on your phone over mobile data: signup → birth input → chart → career prediction → expand logic → feedback. Time it; under 4 minutes or find the friction.
- Done: journey clean on mobile; events arriving; 10 soft-launch invites sent; checklist items all green except final-day ones.
- Risk: integration burning the day. Cut order: calendar view → planetary-details polish → D9 view → upgrade modal becomes static note. Never cut: card, feedback buttons, disclaimer.

**Day 13 — Mon Jun 22: Validation sweep + public launch**
- Goal: gate, then ship.
- Tasks (AM): act on overnight soft-launch feedback (copy/clarity fixes only, no engine changes); run full test suite + 25-chart astrology comparison one final time; Section 25 checklist on 6 fresh charts (2/domain); deployment checklist second run. (Midday): publish Reddit value-posts where mods approved, X thread, WhatsApp/Discord messages (Section 26). (PM): respond to every comment; DM early users; watch engine_logs and costs; log Day-1 metrics at 23:00.
- Tools: you (posting, replying), Claude Pro (triage feedback into bug / copy / scope buckets), Claude Code (hotfixes only with tests).
- Manual validation: the launch gate in Section 24 ("good enough to launch"). If it fails at 10:00, launch moves to June 23 and you say so publicly in the communities you warmed up; a one-day honest slip costs less than a wrong-sublord screenshot.
- Done: live, posted, first 50 charts watched, zero validator-bypass outputs in logs.
- Risk: a public chart exposing a calc bug. Mitigation: the 25-chart gate this morning plus instant rollback to the pinned revision.

---

# 24. Testing and Validation Plan

**Calculation tests:** per-engine pytest suites built the same day as each engine (Days 1-8), run on every commit. Coverage target is meaningless here; fixture correctness is the target.

**Boundary tests:** the 326 nakshatra/pada fixtures; sub-boundary triplets; cusp-edge planet placement; Moon at nakshatra extremes for dasha balance; 0° Aries and 29°59'59" Pisces everywhere.

**Reference software comparison (the astrology gate, run Days 1, 3, 4, 5 and re-run Day 13 AM):**
- Planet longitudes: 25 charts vs Jagannatha Hora (KP settings), within 5 arc-seconds.
- Nakshatra and pada: exact on all 25.
- KP sublords (planets and all 12 cusps): exact lord match on all 25; cusp longitude within 0.01°.
- Dasha: MD/AD dates within 1 day, PD within 2, on 10 charts.
- Cusp comparison: ascendant exact sign and within 0.01°.
- Chart set must include: 2 births near midnight, 2 near sign-boundary ascendants, 1 southern hemisphere, 1 western timezone with DST, 1 pre-1990 birth.

**API tests:** auth, ownership 404s, rate limits, idempotency, tier-locked payload shape, cache behavior, /health degradation.

**Interpretation quality tests:** validator unit tests (entity, echo, banned phrases, lengths); 10-chart Section 25 checklist pass ≥ 8/10 on Day 11 and 6 fresh charts on Day 13; template-fallback render snapshot test.

**UI tests:** card renders all 9 elements from fixture JSON; blurred-state rendering; feedback round-trip; manual journey script (Day 12).

**Mobile tests:** 360px and 390px widths, real device over mobile data, bottom-sheet logic expansion, thumb reach on feedback buttons, input pickers.

**Load tests:** modest by design: 20 concurrent /chart/generate and 10 concurrent /predict for 5 minutes (locust); p95 targets 2s / 8s (first prediction, LLM-bound); no 5xx. Launch volume will not exceed this; do not spend more than an hour.

**User feedback tests:** soft-launch cohort (Day 12 evening) must produce ≥6 completed journeys and ≥4 feedback submissions before public launch; if specificity complaints dominate, Day 13 AM is copy-and-threshold tuning, not posting.

**"Good enough to launch" means:** all 25 reference charts pass the astrology gate exactly as specified; the 6-chart interpretation checklist passes ≥ 5/6; p95 chart generation < 2s warm; template fallback verified in prod; mobile journey under 4 minutes; disclaimer on every prediction surface; RLS ownership test passes. Anything less, slip a day.

---

# 25. Interpretation Quality Checklist

Reject (and log) any output where:

- [ ] It does not name the actual running mahadasha and antardasha lords.
- [ ] It does not name the actual cusp sublord for the domain.
- [ ] Any window lacks explicit start and end dates.
- [ ] Any window exceeds 30 days.
- [ ] The text would read as true for a random stranger (the swap test: paste it next to a different chart's output; if you cannot tell which belongs to which, reject).
- [ ] It uses certainty language or anything on the banned list.
- [ ] It calls a WEAK-tier supporting planet strong, or ignores a flagged affliction.
- [ ] Its tone contradicts the deterministic tier (enthusiastic SPECULATIVE, hedged HIGH).
- [ ] The reflection is missing, or is a worldly instruction rather than self-review.
- [ ] It reads like sun-sign horoscope filler ("good things are coming", "stay positive").

Automated checks cover items 1-4, 6, and 8 (validator). Items 5, 7, 9, 10 are your read on Days 11 and 13, ten minutes per batch.

---

# 26. Launch Plan

**Channels and sequencing:** soft launch June 21 evening (10 direct contacts). Public June 22: Reddit first (where mods pre-approved; message mods on June 19, not launch morning), then an X thread, then WhatsApp/Discord astrology groups, then DMs to the mid-sized KP/Vedic creators already on your outreach list, offering a free Pro-unlock code for an honest review.

**Reddit (value-post format, not a promo):** title like "I built a KP engine that shows its sublord logic on every prediction. Tear my chart's output apart." Body: one real anonymized card screenshot, two sentences on the deterministic-first architecture, the link, and an explicit ask: "KP practitioners: check the cusp sublords against your software and tell me where I am wrong." Communities that allow tool posts only with mod approval get the approval first; communities that ban promotion get a comment-only presence.

**X thread (6 posts):** the bad-vs-better output comparison from this document's brief; one card screenshot; one logic-expansion screenshot; the "LLM is not the prediction engine" principle in one line; the link; an ask for KP folks to audit.

**WhatsApp/Discord message:** two sentences, one screenshot, link, "free, takes 3 minutes, want your honest read on whether the career window feels specific to you."

**DM to early users (within 24h of their first chart):** "Saw you generated a chart, thank you. One question: did the career window feel specific to you or could it apply to anyone? Brutal honesty helps most." Nothing else; no feature pitch.

**Feedback questions (everywhere):** Did it feel specific to you? Was the logic expansion understandable? Did the sublords match your software (for practitioners)? What would you pay for the locked parts?

**Targets:** Day 1 (Jun 22): 50 charts, 25 predictions viewed, 10 feedback submissions, 0 calculation-error reports. Day 3 (Jun 24): 150 charts, 30% logic-expansion rate, 30 feedback submissions, 5 user conversations completed, first calibration look. Day 7 (Jun 28): 400 charts, 15% of Day-1 users returned, 20 upgrade clicks or 10 paid unlocks, "felt specific" ≥ 55% of feedback.

**Metrics to track from minute one:** the eight events in Section 27 plus calc-error reports and cost per prediction.

**Turning feedback into changes:** every comment lands in one of three buckets within 24h: bug (fix same day), specificity (tune thresholds/copy, batch every 2 days), scope request (week-2+ list, reply honestly with "not before validation"). Practitioner sublord disputes get top priority always; one confirmed mismatch reopens the Day-13 gate.

---

# 27. Metrics and Feedback Loop

**MVP metrics (analytics_events names):** `chart_generated`, `prediction_viewed`, `logic_expanded`, `feedback_submitted`, `returned_after_3d` (computed nightly from last_seen), `upgrade_clicked`, `marked_useful`, `marked_inaccurate`. North-star pairing for the MVP: logic_expanded / prediction_viewed (do people care how it works) and marked_useful / feedback_submitted (does it land).

**Asking in the moment:** every card carries useful / not useful / too vague; one tap, optional comment. No modal interruptions.

**Asking after a window ends:** nightly job marks `prediction_events` with followup_due ≤ today; on the user's next visit a quiet banner asks "Your Jul 12-28 career window ended. Did anything in this area shift?" with happened / partly / did not. Email follow-up is week 2 if the should-build slot never opened.

**Storage:** all of it in prediction_feedback with verdict phases (in-moment vs post-window), joined to the prediction's tier and score.

**Improving scoring over time:** a weekly calibration query: for each tier, the share of post-window "happened/partly" responses. With launch-scale N treat it as directional only; adjust one weight at a time in weights.yaml, log every change to engine_logs with a reason, and never tune on in-moment "useful" alone (it measures writing, not indication quality). Real calibration starts when post-window N per tier exceeds ~30, likely week 4+.

---

# 28. Biggest Risks and Mitigation

| Risk | Failure mode | How to detect | How to reduce | What to cut if behind |
|---|---|---|---|---|
| Astrology calculation mismatch | One wrong sublord screenshot ends trust with the exact community you need | 25-chart reference gate; practitioner audits invited at launch | Lock ayanamsa/node Day 1; exact-match gates Days 3-4; re-gate Day 13 AM | Never cut validation; cut features instead |
| Generic outputs | "Felt specific" < 40%; silence | Swap test; feedback verdicts | Promise gate, ≥2-trigger rule, weak-signal suppression, Section 25 checklist | Cut a domain (ship career-only) before loosening thresholds |
| Too much scope | Days 11-12 collapse | Daily done-criteria misses two days running | Frozen scope; per-day cut lists pre-written | Calendar view, D9 UI, history endpoint, email follow-ups |
| LLM hallucination | Invented planets/dates erode the transparency claim | Validator rejection counts in engine_logs | Allowed-entities check, echo check, retry-then-template | Tighten to template-mode for a domain if rejects > 10% |
| No user trust | Charts generated, predictions ignored | logic_expanded rate < 10% | Logic shown by default on first card; practitioner audit invitations; honest tiers | Soften marketing claims, never the disclaimer |
| Bad mobile experience | Drop-off before first card on phones | Journey timing; event funnel by viewport | Day 12 real-device pass; bottom sheets; pinned CTAs | Desktop polish |
| Slow backend | p95 prediction > 12s, abandonment | Latency logs; uptime pinger | Min replica 1; chart caching; Flash model; precompute career on chart creation | Pre-compute only on Pro |
| Payment friction | Launch energy spent on billing bugs | Any payment task exceeding 2 hours | Payment links + manual flips; email-capture fallback | The payment link itself (capture emails, charge week 2) |
| Legal/ethical concerns | Advice-like output in finance/relationships; user harm complaints | Banned-phrase logs; manual batch reads | Forbidden-phrase validator, reflection-not-instruction rule, no health domain, disclaimers, probabilistic language everywhere | Nothing here is cuttable; this list is load-bearing |
| Poor RAG data quality | Mixed/wrong expert chips contradict the math | Day 10 gate; tag spot-check rate | Rule-card-first corpus; small and curated; precision@4 gate; RAG never overrides math | RAG weight to 0 and ship chart-only chips (pre-authorized fallback) |

---

# 29. Final Build Priorities

**Top 5 to build first:** 1) Ephemeris + KP correctness with the exact-match gate (Days 1, 3, 4). 2) Dasha engine to PD level (Day 5). 3) Domain rules + confidence scorer with the weak-signal floor (Day 7). 4) Synthesis with the strict schema, validator, and template fallback (Day 11). 5) The prediction card with logic expansion and feedback buttons (Day 12).

**Top 5 not to waste time on:** full Razorpay billing; Shadbala/Ashtakavarga; any varga beyond D9/D10; calendar view and visual polish before the card works; ChatGPT-vs-Claude-vs-Gemini benchmarking debates (the allocation table is decided; revisit after launch).

**Next 3 actions today (Wednesday, June 10):**
1. Commit `schemas/chart.json` v1.0 and its pydantic models; everything downstream codes against this contract.
2. Set SIDM_KRISHNAMURTI + TRUE_NODE + Placidus in ephemeris_engine and pass the 5-chart longitude check against Jagannatha Hora before dark.
3. Run the Section 8 Codex prompt to generate `kp_sublord_249.csv` with its structural assertions, so Day 3 starts on verified data, not generation.

**The one quality bar:** generate a chart for someone you have never discussed astrology with. If the career card names their real MD/AD lords and 10th cusp sublord, gives a window under 30 days with visible triggers, and they say "this feels like it is about me," the MVP is worth launching. If it reads like it could be anyone's, it is not, regardless of how much of this document got built.

---

*Product boundary, restated once: Junopath is for self-reflection, planning, and astrological interpretation. Probabilistic language always. No certainty claims, no medical, legal, investment, or high-stakes financial advice, ever, in any tier.*
