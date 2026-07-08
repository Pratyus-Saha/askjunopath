# Prediction Page Card Spec — v1

**Task:** 1.2 (Phase 1, Week 1) · **Date:** 2026-07-08 · **Status:** Draft for founder review
**Builds:** Task 1.3 (Antigravity rebuilds career/finance/relationship pages per this spec)
**Data source:** existing `/predict/{domain}` response. No backend changes required for v1 scope.

---

## 1. Purpose and principles

Replace the current wall-of-sentences prediction page with scannable cards. A first-time visitor must be able to answer, within 10 seconds of landing: **what's coming, when, and how strongly the chart supports it.**

Principles (locked):
1. **Timing is the product.** Time-window cards are the spine. Everything else supports them.
2. **Human terms first, astronomy on expand.** Card titles use event language ("Advancement window"), never planet lists. Planets, sub-lords, and degrees live inside the expand.
3. **Honest numbers.** The meter shows **factor count** (real converging factors), not a smoothed percentage. Signal strength % appears in the header only, always with its "not a probability" caption.
4. **Warnings are preparation, not doom.** Caution content is always phrased as an action to take or avoid, never as fear.
5. **Every output labeled by source** (KP · Placidus · Newcomb), per locked decision 2.

---

## 2. Page layout (top to bottom, per domain page)

```
[Disclaimer banner — unchanged]
[Domain title — unchanged]
1. Ninety-day timeline strip
2. Signal header (tier word + signal % + caption)
3. Window cards (one per transit window, sorted by start date)
4. Caution card (conditional: caution_flag === true)
5. Current period card (dasha stack)
6. "How this was computed" (existing collapsed section — unchanged)
```

---

## 3. Component specs

### 3.1 Ninety-day timeline strip

A horizontal bar spanning `as_of` → `as_of + 90 days`.

- **Bands:** one colored band per transit window, positioned by `start_date`/`end_date`. Color by dominant event type: advancement = green family, steady-progress = amber family, disruption caution = red family. Use existing design tokens; do not introduce new hues.
- **Today marker:** thin vertical line + "Today" label at `as_of`.
- **Dasha underlay:** a subtle shaded region for the current pratyantardasha window (`pratyantardasha_window`), labeled with the PD lord on hover/tap.
- **Interaction:** tap/click a band → smooth-scroll to that window's card.
- **Empty state:** if `transit_windows` is empty, show the strip with only the today marker and the line "No strong contact windows in the next 90 days — the next estimated contact is {transit_summary.next_contact.estimated_date}."
- **Month labels** along the bottom axis (Jul · Aug · Sep · Oct).
- Mobile: strip is full-width, min height 56px, bands min 8px wide (clamp very short windows so they stay tappable).

Data: `transit_windows[].start_date/end_date`, `event_types`, `current_dasha_stack.pratyantardasha_window`, `transit_summary.next_contact`.

### 3.2 Signal header

- **Tier word** as the existing pill (HIGH / MEDIUM / LOW — render from `confidence`, uppercase for display only; engine emits lowercase).
- **Signal %** (`signal_strength`) in the existing large mono type.
- **Caption (mandatory, verbatim):** "Signal strength measures how many independent KP factors point the same way. It is not a probability that the event happens."
- No meter here — the discrete meter lives on window cards (3.3). Keeping one number + one caption up top prevents two competing "scores."

### 3.3 Window card (the spine)

One card per `transit_windows[]` entry. Collapsed state shows exactly four things:

```
┌──────────────────────────────────────────────┐
│ [event-type icon] Advancement window          │
│ Sep 8 – Sep 19, 2026                          │
│ ● ● ● ● ● ● ● (7 factors converge)            │
│ Peak: Sep 15–16 — Venus contacts your        │
│ 10th-house cusp (twice)               [▼]     │
└──────────────────────────────────────────────┘
```

- **Title:** derived from the window's dominant event type, mapped to human phrasing:
  - career-advancement window → "Advancement window"
  - steady-progress window → "Steady-progress window"
  - career-disruption caution → "Watch-out window" (also triggers red styling; see 3.4 for whether it renders here or as the caution card)
  - finance/relationship analogues follow the same pattern from their `event_types`.
  - Mapping ambiguity: if a window matches multiple event types, use the highest-score interpretation; if none map, fall back to "Contact window."
- **Date line:** human format ("Sep 8 – Sep 19, 2026"), not ISO.
- **Discrete meter:** one filled dot per trigger in `triggers[]` (`trigger_count`), capped at 10 dots; if >10, render 10 dots + "×N". Label: "{trigger_count} factors converge." This is the roadmap's "factor count on expand" promoted to the collapsed state — it's the honest number and it's short.
- **Peak line:** computed client-side from `triggers[]`: the contact_date (or consecutive date pair) with the highest summed `weight`; tie-break by smallest `angular_diff_deg`. Copy pattern: "Peak: {date(s)} — {planet} contacts your {natal_point, humanized} ({n} times if >1)."
  - Humanize natal points: `cusp_10` → "10th-house cusp", `natal_jupiter` → "natal Jupiter", etc.
- **Expand (▼) reveals:**
  - `window_score` with label "Window score" and a one-line definition ("Sum of weighted planetary contacts in this window").
  - Trigger table: date · planet · contact point (humanized) · weight, one row per trigger, sorted by date. **Planet names deduplicated nowhere here — this is the one place per-contact rows are correct.**
  - `pd_overlap === true` → badge: "Overlaps your current dasha sub-period" (this is a strength signal; show it).
  - Source label: "KP · transit scan".
- **No planet-name string in the collapsed state at all.** The deduped planet list (1.1b fix) remains only as a fallback if event-type mapping fails.

### 3.4 Caution card (conditional)

Rendered once per page when `caution_flag === true` OR any window's dominant event type is a disruption caution. If the caution is window-specific, this card replaces that window's normal card styling (red family) rather than duplicating it.

```
┌──────────────────────────────────────────────┐
│ ⚠ Watch-out: Oct 3 – Oct 5                    │
│ Change or friction is possible around work    │
│ in this window. If you can, avoid signing     │
│ or committing to major decisions here.        │
│ ● ● (2 factors)                        [▼]    │
└──────────────────────────────────────────────┘
```

- Copy rules (enforced in review, not code): must contain one concrete avoid/prepare action; must not use fear vocabulary (danger, loss, failure, beware); must keep hedged framing ("possible", "may").
- Expand: same trigger table as 3.3 plus the challenge-house explanation drawn from `career_themes` labels (e.g., "instability/sudden-change (house 8)").

### 3.5 Current period card (dasha)

One compact card, replacing the current inline paragraph:

- Three rows: Mahadasha / Antardasha / Pratyantardasha, each with lord name + end date (already the pattern on the Dasha tab — reuse that component).
- One support line derived from `dasha_timing`: "{n} of 3 period lords support this domain right now" (count of `md_supports/ad_supports/pd_supports` that are true).
- Link: "Full timeline →" to the Dasha tab.

### 3.6 Narrative text (Gemini synthesis)

The synthesis paragraphs do not disappear — they move **below the cards** under a heading "Reading" and render at most the first 2 synthesis blocks by default with "Read full analysis" expanding the rest. Cards are for scanning; prose is for depth. The planet-chip rows under each paragraph are removed (the cards now carry that information).

---

## 4. Copy rules (apply to all card text)

- Hedged verbs only: may, suggests, indicates. Never: will, guaranteed, definitely.
- No trading/market vocabulary on finance cards (mirrors engine's banned-words rule).
- Dates always human-formatted with year on first occurrence per card.
- Jargon terms rendered in cards (dasha, sub-lord, cusp) must be the tappable-definition pattern — v1 may ship with plain text, but the spec reserves the tap target (task 2.4 dependency).

---

## 5. Phase 2 sections (design for, do not build in 1.3)

- **5.1 "Since your last visit" card:** diff of window scores and next-contact estimate vs. the user's previous fetch. Requires storing a per-user last-payload snapshot (one Supabase column beside the existing chart cache). Slot: directly under the timeline strip.
- **5.2 "Ask this window" prompts:** 2–3 tappable scoped questions per window card routing to a window-scoped Gemini synthesis endpoint with existing guardrails. Slot: footer of each window card. Backend dependency: new scoped-synthesis route.

Both slots should exist in the component structure as empty/hidden regions so Phase 2 adds content without re-layout.

---

## 6. Acceptance criteria (task 1.3 exit)

1. All three domain pages render the six-section layout in §2 from live API data with no console errors.
2. Timeline strip bands match window dates exactly and scroll to the right card on tap.
3. Every window card shows title, human dates, dot meter with factor count, and a computed peak line matching a hand-check of the triggers array for at least one chart.
4. Caution card appears iff `caution_flag` or a disruption-type window exists, with action-phrased copy.
5. No collapsed card surface contains a raw planet list, ISO date, or unlabeled score.
6. Empty transit-windows state renders per §3.1.
7. Lighthouse mobile usability unchanged or better vs. current page.

## 7. Out of scope for 1.3

Feedback buttons (task 2.2), guided walkthrough (2.4), inline definitions (2.4), Phase 2 cards (§5), any engine/API change, Dasha tab changes.
