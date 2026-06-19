\# JunoPath Landing Page: Design System, Motion Rules, and Execution



Commit this as `docs/frontend/landing-design-system.md`. The FE-1 and FE-2 prompts point the agent here.

Date: 2026-06-19. Scope: the landing page only. No chart-generate form, no engine dependency, no schema dependency.



\---



\## 0. Scope guard (keep this surface frozen)



The landing page is marketing, education, and the live sky. It is not the chart experience. The moment a birth-details form that renders a result lands on this page, the page starts depending on the engine and the schema, and the no-rework property is gone. So:



\- The primary CTA routes to `/chart` (a separate, flagged surface built in another lane). It does not open a chart form here.

\- If `/chart` is not live yet, the CTA leads to an honest "private beta" state, never a fabricated chart.

\- This page reads no engine output except current planetary longitudes for the wheel, which come from a committed fixture.



Build it once, ship it, leave it alone while the engine validates.



\---



\## 1. Motion principle: lively but calm, fast on a cheap phone



Three rules decide every motion choice.



1\. \*\*Compositor-only.\*\* Animate `transform` and `opacity`, nothing else. Never animate `top`, `left`, `width`, `height`, `margin`, `padding`, or `background-position`. Those force layout or paint and cause the jank you are trying to avoid.

2\. \*\*No JavaScript scroll handlers.\*\* Parallax and reveals use CSS scroll-driven animations (`animation-timeline: scroll()` and `view()`) where supported, with an IntersectionObserver fallback that toggles a class. No code reads `scrollY` or `getBoundingClientRect` on scroll.

3\. \*\*Motion is a few deliberate moves, not everything.\*\* A faint warm bloom breathes near the hero. Content reveals once as it enters view. The hero background parallaxes gently. Hover and focus lift slightly. The wheel draws in once like ink on paper. That is the whole motion vocabulary. Resist adding more.



Reduced motion and small screens both dial this down, defined in sections 4 and 3.



\---



\## 2. Design tokens



Brand tokens: a premium beige editorial interface with dark navy structure, ivory cards, antique gold accents, and precise mono data. Cormorant Garamond display, DM Sans body, DM Mono data. Cream paper sections alternate with full navy sections for rhythm. \*\*This palette changes a token AGENTS.md section 2.3 currently fixes. Update AGENTS.md and add a DECISIONS.md entry before building, or the agent will hit a doc conflict (see the note at the end of this file).\*\*



\### 2.1 Color



```css

:root {

&#x20; /\* backgrounds and surfaces \*/

&#x20; --color-bg:             #F6EFE3; /\* page base, beige \*/

&#x20; --color-bg-soft:        #FBF7EF; /\* lighter paper section \*/

&#x20; --color-surface:        #FFFDF8; /\* ivory card \*/

&#x20; --color-surface-raised: #FFFFFF; /\* raised card \*/



&#x20; /\* navy structure (contrast sections, dark surfaces) \*/

&#x20; --color-navy:       #0D1B2A;

&#x20; --color-navy-soft:  #14263A;

&#x20; --color-navy-muted: #30445C;



&#x20; /\* text \*/

&#x20; --color-text:         #111827; /\* primary on light \*/

&#x20; --color-text-soft:    #3F4754; /\* secondary on light \*/

&#x20; --color-text-muted:   #6B7280; /\* tertiary on light \*/

&#x20; --color-text-on-dark: #F9F4EA; /\* text on navy \*/



&#x20; /\* borders and hairlines \*/

&#x20; --color-border:        #E4D6C2;

&#x20; --color-border-strong: #CBB89E;



&#x20; /\* accent (gold, primary decorative accent) \*/

&#x20; --color-gold:       #B88A44;

&#x20; --color-gold-soft:  #D8B878;

&#x20; --color-gold-faint: #F2E3C3;



&#x20; /\* secondaries, semantic use only \*/

&#x20; --color-sage: #647A67;

&#x20; --color-clay: #A7654B;

&#x20; --color-cream: #FFF8E9;



&#x20; /\* status \*/

&#x20; --color-success: #4F7A5A;

&#x20; --color-warning: #A7654B;

&#x20; --color-info:    #30445C;

}

```



\### 2.1a Usage rules (so the palette stays clean)



\- Light sections use `--color-bg` (or `--color-bg-soft`) with `--color-text` for body, `--color-text-soft` and `--color-text-muted` for support. Cards sit on `--color-surface`, raised cards on `--color-surface-raised`, separated by `--color-border` hairlines.

\- Navy sections use `--color-navy` (gradient to `--color-navy-soft`) with `--color-text-on-dark`. `--color-navy-muted` is for secondary text on navy.

\- Gold is the only decorative accent: 1px hairlines (`--color-border-strong` or `--color-gold` at low opacity), data numerals, dividers, the primary CTA edge. On light use `--color-gold` (it has enough depth at #B88A44 to read cleanly on beige). On navy, `--color-gold` or `--color-gold-soft`. Never a large gold fill.

\- `--color-sage` and `--color-clay` are reserved for semantic jobs only: confidence tiers, category coding, or state. Sage maps to steady or positive, clay to caution. They are never used as decoration. This keeps gold as the single visual accent.

\- Status colors (`--color-success`, `--color-warning`, `--color-info`) are for form and system states only.

\- Focus ring: `--color-gold` on light, `--color-gold-soft` on navy. Visible at all times.



\### 2.1b Two-tone section rhythm



The premium feel comes from alternating beige and navy sections, not one flat beige wall. The navy sections carry visual weight and remove the empty feeling. Assign surfaces like this:



\- Hero: light (`--color-bg`). The engraved wheel sits in navy and gold on beige.

\- What your chart actually is: light.

\- How it works: light, cards on `--color-surface`.

\- Why you can trust the math: navy surface, `--color-text-on-dark`. The dark section gives this gravity.

\- A reading, explained: light, with the navy sample text and an ivory card.

\- Generate your chart (CTA block): navy surface, gold CTA.

\- Footer: navy surface.



Each section component takes a `surface="light" | "navy"` prop and pulls the matching text, border, and accent tints. No component hardcodes a color.



\### 2.1c Texture



No starfield; it was a dark-theme device. Use a faint paper grain (a tiny tiling SVG noise at very low opacity) across light sections, plus a soft vignette at the page edges. On navy sections, a faint warm bloom near the wheel and headline, opacity-based, very subtle. No particles, no animated gradients.



\### 2.2 Fluid type scale (no media-query soup)



```css

:root {

&#x20; --font-display: "Cormorant Garamond", Georgia, serif;

&#x20; --font-ui:      "DM Sans", system-ui, sans-serif;

&#x20; --font-mono:    "DM Mono", ui-monospace, monospace;



&#x20; --fs-display-xl: clamp(2.5rem, 1.6rem + 4.2vw, 4.5rem);  /\* hero \*/

&#x20; --fs-display-l:  clamp(1.75rem, 1.3rem + 2.2vw, 2.75rem); /\* section titles \*/

&#x20; --fs-heading:    clamp(1.2rem, 1.05rem + 0.7vw, 1.5rem);

&#x20; --fs-body:       clamp(1rem, 0.97rem + 0.15vw, 1.125rem);

&#x20; --fs-small:      0.8125rem;

&#x20; --fs-mono:       clamp(0.875rem, 0.83rem + 0.2vw, 1rem);

}

```



Display weight light (300 to 400). Body line-height 1.6. Labels use `--fs-small`, DM Sans 500, uppercase, letter-spacing 0.04em. All numbers, degrees, dates, coordinates, and confidence values render in `--font-mono`.



\### 2.3 Spacing, radii, hairlines



```css

:root {

&#x20; --space-1: 4px;  --space-2: 8px;  --space-3: 12px; --space-4: 16px;

&#x20; --space-6: 24px; --space-8: 32px; --space-12: 48px; --space-16: 64px;

&#x20; --space-24: 96px; --space-32: 128px;



&#x20; --section-y: clamp(64px, 9vw, 128px); /\* vertical section padding \*/

&#x20; --content-max: 1200px;

&#x20; --gutter: clamp(20px, 5vw, 48px);



&#x20; --radius-sm: 8px; --radius-md: 14px; --radius-lg: 22px;

&#x20; --hairline-light: 1px solid var(--color-border);

&#x20; --hairline-navy:  1px solid color-mix(in srgb, var(--color-gold) 30%, transparent);

}

```



\### 2.4 Motion tokens



```css

:root {

&#x20; --ease-out:    cubic-bezier(0.16, 1, 0.3, 1);

&#x20; --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);

&#x20; --dur-fast: 180ms; --dur-base: 280ms; --dur-slow: 480ms;

&#x20; --stagger: 70ms;

}

```



\### 2.5 Breakpoints



Mobile-first. Design and test from 320px up.



```

base   : 320px and up (single column, the baseline you build for)

sm     : 480px

md     : 768px  (tablet, two-column readout allowed)

lg     : 1024px

xl     : 1280px (content caps at --content-max)

```



\---



\## 3. Responsive strategy (down to small phones)



\- Single column at base. Multi-column only from `md` up, and only where it helps (the mono readout, the how-it-works steps).

\- Fluid type via the clamp scale above, so text scales smoothly without per-breakpoint overrides. No text drops below readable size on small screens.

\- The zodiac wheel sizes to `min(92vw, 440px)` and never overflows. On base it sits under the hero text, full width, with the mono readout stacked below it. From `md`, wheel and readout can sit side by side.

\- The mono readout reflows: stacked rows at base, two columns from `sm`, beside the wheel from `md`. It wraps rather than shrinking the font.

\- Tap targets at least 44 by 44px. Nav collapses to a button that opens a focus-trapped menu, closes on Escape and on outside tap.

\- No horizontal scroll at any width. Test explicitly at 320, 360, 768, 1280.

\- Reserve dimensions for the wheel, images-free media slots, and font swap so nothing shifts (CLS under 0.05).



\---



\## 4. Motion and parallax system (the performant way)



\### 4.1 Section reveals



Content blocks start at `opacity: 0; transform: translateY(16px)` and animate to visible as they enter the viewport. Prefer CSS scroll-driven view timelines:



```css

@media (prefers-reduced-motion: no-preference) {

&#x20; .reveal {

&#x20;   animation: reveal-up linear both;

&#x20;   animation-timeline: view();

&#x20;   animation-range: entry 0% entry 40%;

&#x20; }

}

@keyframes reveal-up {

&#x20; from { opacity: 0; transform: translateY(16px); }

&#x20; to   { opacity: 1; transform: none; }

}

```



Fallback for browsers without scroll-driven animations: an IntersectionObserver that adds a `.is-visible` class which triggers the same transition. Stagger siblings by `--stagger`. Reveal each element once.



\### 4.2 Hero parallax



The hero has layered backgrounds: the cream gradient, a faint paper grain, and a soft warm bloom. On scroll the grain and bloom move at slightly different rates using a scroll-driven transform on each layer, compositor-only. Foreground text and the wheel do not parallax. Keep the translate range small (under 60px) so it reads as depth, not drift.



```css

@media (prefers-reduced-motion: no-preference) and (min-width: 768px) {

&#x20; .hero\_\_bloom {

&#x20;   animation: parallax-slow linear both;

&#x20;   animation-timeline: scroll(root);

&#x20; }

}

@keyframes parallax-slow { to { transform: translateY(-48px); } }

```



On screens under 768px, reduce the parallax range to near zero (under 16px) or disable it. Mobile parallax costs battery and stutters most, and the effect is barely visible on a small screen anyway.



\### 4.3 Ambient life



One faint warm bloom on the hero, 6 to 8 second ease-in-out on `opacity` between two close values. The paper grain is static, not animated. Nothing else loops. No continuous JavaScript animation.



\### 4.4 Micro-interactions



Buttons and cards lift on hover and focus via `transform: translateY(-2px)` and a hairline brighten, `--dur-fast`. Focus shows a visible ring, using `--color-gold` on light and `--color-gold-soft` on navy surfaces. The primary CTA may have a slow gold edge shimmer, opacity-based, that pauses on reduced motion.



\### 4.5 Reduced motion (mandatory)



```css

@media (prefers-reduced-motion: reduce) {

&#x20; \*, \*::before, \*::after {

&#x20;   animation: none !important;

&#x20;   transition: none !important;

&#x20; }

&#x20; .reveal { opacity: 1; transform: none; }

}

```



Everything shows in its final state. No parallax, no drift, no shimmer.



\---



\## 5. Component inventory



Each component is responsive per section 3 and uses only the tokens above.



\- `SiteNav`: sticky, transparent over the hero then gains a faint beige backdrop on scroll (opacity only). Mobile menu, focus-trapped.

\- `Hero`: display headline, subheadline, primary and secondary CTA, the wheel slot, layered beige-grain-and-bloom backgrounds.

\- `ZodiacWheel` and `SkyReadout`: built in FE-2, mounted in the hero slot.

\- `SectionBlock`: a reveal-on-scroll wrapper with title, body, and optional logic line in mono.

\- `StepCard`: numbered how-it-works step with a mono logic line.

\- `TrustPanel`: the deterministic-engine explanation.

\- `SampleReading`: the show-your-work format example, with a `ConfidenceChip` and the `Disclaimer` component.

\- `ConfidenceChip`: tier label in mono (HIGH, MEDIUM, SPECULATIVE). Tier only, never a raw percentage.

\- `Disclaimer`: renders on the sample-reading surface. Probabilistic, honest.

\- `CTABlock`: closing call to action routing to `/chart`.

\- `SiteFooter`: plain links, no urgency.



\---



\## 6. Step-by-step execution process



\*\*Before any prompt\*\*

1\. Commit this document as `docs/frontend/landing-design-system.md`.

2\. Confirm the guided copy in the prior frontend lane plan (Part C2) is the copy you want; it is reused here.

3\. For FE-2 only: generate `frontend/src/fixtures/sky\_now.json` from your engine (current planetary longitudes in the frozen schema shape) and commit it. FE-1 needs nothing from you.



\*\*FE-1: shell, design system, sections, copy, motion\*\*

4\. Run the FE-1 prompt (section 7). Antigravity builds the full page structure, implements the tokens as CSS variables, writes all sections with the guided copy, wires the reveal and parallax system, and leaves a mounting slot for the wheel.

5\. Review against this doc: tokens present as variables, fluid type working, reveals smooth, parallax compositor-only, reduced-motion honored, no horizontal scroll at 320px, CTA routes to `/chart` with the honest fallback, guard script passed. Merge.



\*\*Generate the wheel fixture (you)\*\*

6\. Produce and commit `sky\_now.json` from the engine if not done in step 3.



\*\*FE-2: zodiac wheel and sky readout\*\*

7\. Run the FE-2 prompt (section 8). Antigravity builds the SVG wheel and the mono readout, rendered only from the fixture, mounted in the hero slot.

8\. Review: wheel renders from fixture values, no houses, "current sky" label, readout reflows correctly across breakpoints, motion stays inside the rules. Merge.



\*\*QA pass\*\*

9\. Run the checklist in section 9 across 320, 360, 768, and 1280px, with reduced motion on and off, and against the performance budget.



\---



\## 7. FE-1 prompt (paste-ready)



```

Task: FE-1. Build the JunoPath landing page: shell, design system, all sections, guided copy, motion.

Branch: agent/antigravity/landing-shell



Read order before coding: docs/PROJECT\_CONTEXT.md, then AGENTS.md, then docs/frontend/landing-design-system.md, then docs/frontend/landing-spec.md (sections C1 and C2 for structure and copy). Then code.



Build the complete landing page per the design system document. This page is marketing, education, and a live-sky slot only. It contains NO birth-details form and NO chart result. The primary CTA routes to /chart; if /chart is not present, it routes to an honest "private beta" state. Never render a fabricated chart.



Design system: implement section 2 tokens as CSS custom properties exactly as given (color, usage rules 2.1a, two-tone rhythm 2.1b, paper texture 2.1c, fluid type, spacing, radii, hairlines, motion tokens, breakpoints). Use only these tokens by their names. Brand tokens are a beige base (--color-bg) with near-black text (--color-text) on light, ivory cards (--color-surface), full navy surfaces (--color-navy) with --color-text-on-dark for the contrast sections per 2.1b, Cormorant Garamond display, DM Sans body, DM Mono for all numbers, and gold (--color-gold) as the only decorative accent used for hairlines, numerals, dividers, and the primary CTA edge. Sage and clay are semantic-only (tiers, state), never decoration. Each section component takes a surface="light" | "navy" prop and pulls the matching text, border, and accent tints. No component hardcodes a hex value.



Sections and copy: build the structure in landing-spec C1 and use the guided copy in C2 verbatim. Apply the surface assignment in design-system 2.1b (hero, explainer, how-it-works, and sample-reading on light; trust panel, CTA block, and footer on navy). Include the Disclaimer component on the sample-reading surface. Confidence shows as a tier label (MEDIUM), never a raw percentage. Leave a mounting slot in the hero for the ZodiacWheel and SkyReadout, which FE-2 will fill. Do not build the wheel in this lane.



Responsive (section 3): mobile-first, build and verify from 320px up. Single column at base, multi-column only from md. Fluid type via the clamp scale, no text below readable size. Tap targets at least 44px. Nav collapses to a focus-trapped menu that closes on Escape and outside tap. No horizontal scroll at any width.



Motion (section 4): section reveals via CSS scroll-driven view() timelines with an IntersectionObserver fallback class. Hero background parallax (paper grain and warm bloom) via scroll() timeline, compositor-only, translate range under 60px desktop and near zero under 768px. One faint warm bloom as ambient life; the paper grain is static. Hover and focus lift via transform. Animate only transform and opacity. No JavaScript scroll handlers that read layout. Honor prefers-reduced-motion: reduce by disabling all motion and showing final states.



Performance (design system section covers it): hero is pure CSS and inline SVG and paints before any script, LCP under 2.0s on mid-range Android over 4G, CLS under 0.05. Inline SVG icons only, no icon fonts or libraries. Fonts self-hosted or preconnected, only the weights used, font-display swap, Cormorant Garamond subset to display weights. Reserve dimensions everywhere.



Hard rules: fixtures only, no live API calls, no LLM calls, no astrology computation in the browser. Probabilistic phrasing only, no deterministic promises, no health domain, no fear or urgency. No new dependencies without asking.



Allowed files: frontend/app/\*\* (the landing route and layout, plus global CSS for tokens), frontend/src/components/\*\* (the components in design-system section 5 except the wheel and readout). Run python scripts/check\_allowed\_files.py on your changed files before opening the PR.



Done when: npm run lint \&\& npm test \&\& npm run build is green and untampered, only allowed files changed, PR opened (not merged), HANDOFF.md updated. STOP and ask on any spec ambiguity, schema question, needed file outside the list, or any urge to add a chart form.

```



\---



\## 8. FE-2 prompt (paste-ready)



```

Task: FE-2. Build the ZodiacWheel and SkyReadout, mounted in the hero slot from FE-1.

Branch: agent/antigravity/zodiac-wheel



Read order before coding: docs/PROJECT\_CONTEXT.md, then AGENTS.md, then docs/frontend/landing-design-system.md (sections 1, 2, 3, 4), then docs/frontend/landing-spec.md (section C3). Then code.



Build ZodiacWheel as pure inline SVG, rendered as an engraving on beige: the zodiac ring and twelve sign divisions as thin navy hairlines (--color-navy), gold (--color-gold) for the ring outline and degree ticks, and planet glyphs in navy placed at their longitudes. The hero sits on the light surface, so the wheel is navy and gold on beige, not a glowing dark wheel. It renders entirely from the committed fixture frontend/src/fixtures/sky\_now.json, which already exists and is the contract. Read longitudes and place glyphs. Compute nothing. Do not modify the fixture values or its fields. If a needed field is missing, STOP and ask.



Build SkyReadout: a DM Mono list in --color-text of each body with its sign and degree, for example "Moon 18°24' Scorpio". Show both the decimal longitude and the sign-degree form if both are in the fixture. Label the whole unit plainly as the current sky, computed live. Never imply it is a reading for the visitor. No houses.



Mount both into the hero slot left by FE-1. Responsive per design-system section 3: the wheel sizes to min(92vw, 440px) and never overflows, sits under the hero text on base with the readout stacked below, and may sit beside the readout from md. The readout reflows stacked at base, two columns from sm. Type uses the clamp scale.



Motion per design-system section 4: the wheel is static geometry with real glyph positions; it does not spin, because that would misrepresent the sky. Allowed life is a one-time ink draw-in as it enters view (stroke or opacity reveal, compositor-only) and a very faint gold accent on the ring. Honor prefers-reduced-motion. The wheel must be crisp at any size.



Hard rules: fixtures only, no live API calls, no LLM calls, no computation. No new dependencies without asking.



Allowed files: frontend/src/components/\*\* (ZodiacWheel, SkyReadout), and the hero file from FE-1 only to mount them. Run python scripts/check\_allowed\_files.py before the PR.



Done when: npm run lint \&\& npm test \&\& npm run build is green, only allowed files changed, PR opened, HANDOFF.md updated. STOP and ask on any ambiguity or missing fixture field.

```



\---



\## 9. QA checklist (run before calling it done)



\*\*Responsive\*\*

\- No horizontal scroll at 320, 360, 768, 1280.

\- Wheel fits and readout reflows at each width.

\- Tap targets at least 44px, mobile menu traps focus and closes on Escape and outside tap.

\- Text readable at 320px, headline scales without breaking layout.



\*\*Motion\*\*

\- Reveals fire once, smoothly, staggered.

\- Hero parallax is subtle on desktop, near zero on mobile, and uses no scroll handler.

\- With prefers-reduced-motion on, all motion stops and content shows in final state.

\- No layout shift from any animation.



\*\*Performance\*\*

\- LCP under 2.0s on a mid-range Android profile over throttled 4G.

\- CLS under 0.05. Dimensions reserved, fonts swap without shift.

\- Only transform and opacity animate (check in devtools performance panel for layout or paint during scroll).

\- No icon fonts or libraries, inline SVG only.



\*\*Honesty\*\*

\- No birth-details form on the landing page.

\- CTA routes to /chart or an honest private-beta state, never a fake chart.

\- Confidence shown as tier, no raw percentage.

\- No deterministic promises, no health references, no fear or urgency.

\- Disclaimer present on the sample-reading surface.

\- The wheel is labeled as the current sky, not a personal reading.



\*\*Theme\*\*

\- Light sections are beige (--color-bg) with --color-text; navy sections use --color-text-on-dark. Contrast passes WCAG AA at both.

\- Gold (--color-gold) reads clearly on both beige and navy. No muddy gold. Gold is the only decorative accent.

\- Sage and clay appear only in semantic roles (tiers, state), never as decoration.

\- No starfield anywhere. Paper grain is faint and static. The wheel is navy and gold on beige, not a glowing dark wheel.

\- Two-tone rhythm matches 2.1b. No flat beige wall, no all-dark page. Ivory cards (--color-surface) sit on the beige base with --color-border hairlines.

```



\---



\## 10. Governance: unlock the color token before building



This palette changes a token AGENTS.md section 2.3 currently fixes as "navy background ... gold #C9A96E." Before running any lane, make these edits yourself so the docs agree:



1\. In AGENTS.md section 2.3, change the design-tokens line to: beige base (#F6EFE3), near-black text on light, dark navy structure and contrast surfaces (#0D1B2A), ivory cards, gold accent #B88A44 (with #D8B878 soft), sage #647A67 and clay #A7654B as semantic secondaries, Cormorant Garamond display, DM Sans body, DM Mono data.

2\. Add a DECISIONS.md entry, for example:



```

D0xx (2026-06-19): Landing-page theme set to a premium beige-and-navy editorial two-tone:

beige base (#F6EFE3), near-black text on light, dark navy structure and contrast sections

(#0D1B2A), ivory cards, antique gold accent (#B88A44), with sage (#647A67) and clay (#A7654B)

as semantic-only secondaries. Reason: stronger premium and trust positioning, differentiates

from the dark-mystical category. Tokens in docs/frontend/landing-design-system.md section 2.

Scope: landing page. Chart and prediction surfaces revisit theme separately.

```



3\. Confirm the scope: this decision covers the landing page. The chart and prediction surfaces can adopt the same theme later, but that is a separate decision so you do not silently restyle engine-facing UI before it exists.



Until these three are done, a compliant Antigravity reading AGENTS.md should stop and ask which palette wins. Doing them first keeps the lane moving.

