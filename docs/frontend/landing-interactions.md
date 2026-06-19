\# JunoPath Landing Page: Interaction Design and Build Spec



Commit as `docs/frontend/landing-interactions.md`. One of the three canonical docs for the landing lane, alongside `landing-design-system.md` (tokens, two-tone surfaces, motion) and `landing-spec.md` (page order, guided copy, wheel spec). The landing lane uses these three docs, not the earlier internal-beta cockpit plan.



Scope: landing page only. No chart form, no engine dependency beyond current planetary positions in a committed fixture.



\---



\## 1. The one rule: every element earns its place



Before any element ships, it answers one question: what does this help the visitor understand or trust? If the answer is "it looks nice," it does not ship. A precision instrument earns trust through restraint. The page feels calm, then rewards attention with a few interactions that show how the product thinks.



\### In (value-driven, build these)



\- The interactive live sky wheel: positions you can inspect.

\- The sample reading with a "Show the logic" reveal: the transparency thesis made tactile.

\- The confidence tier explainer: teaches the honesty model.

\- Restrained micro-interactions: reveal-on-scroll, hover lift, one ambient bloom, one CTA shimmer.



\### Out (junk, do not build)



\- Testimonial carousels, logo walls, or fake social proof.

\- Particle fields, cursor-follow effects, animated mesh gradients, floating shapes.

\- Parallax on every section. Only the hero background parallaxes, gently.

\- Scroll-jacking, pinned full-screen scroll sequences, snap that fights the user.

\- Autoplaying anything. Counters that re-run on every scroll. Decorative loaders.

\- More than one ambient loop. Gold used as a large fill. Sage or clay used as decoration.

\- Any animation that moves layout. Any motion that cannot be turned off.



When unsure whether something is value or junk, it is junk. Cut it.



\---



\## 2. Interaction spec



Each interaction lists behavior, states, mobile, keyboard and accessibility, reduced motion, and data source. Build all states, not just the happy path. That completeness is what separates a product from a demo.



\### 2.1 Interactive sky wheel (the centerpiece)



\*\*Behavior.\*\* The wheel shows planets at their current longitudes, rendered as a navy and gold engraving on the beige hero. A planet glyph is interactive: pointing at it or focusing it reveals a small popover with the body's current sign and degree in DM Mono, plus one short plain-language line on what that body represents.



\*\*States.\*\* idle, hover, focus, active (pinned on tap), dismissed. On desktop, hover shows the popover; moving away hides it. On tap or click, the popover pins until another planet is chosen, the user taps elsewhere, or Escape is pressed.



\*\*Appearance.\*\* The popover is an ivory card (`--color-surface`) with `--color-text`, a `--color-border` hairline, and the sign and degree in DM Mono with a gold (`--color-gold`) accent. It reads like a small data card, not a tooltip bubble.



\*\*Mobile.\*\* No hover. Tap a glyph to pin its popover, tap elsewhere or a close affordance to dismiss. Glyph tap targets are at least 44px even though the glyph itself is small; use an invisible padded hit area.



\*\*Keyboard and accessibility.\*\* Each glyph is focusable in reading order (Sun first, per the fixed planet order). Enter or Space pins the popover. Escape dismisses. The popover is an ARIA tooltip or a labelled region tied to the glyph. The whole wheel has a text alternative listing positions, so a screen reader user gets the same facts as the readout.



\*\*Reduced motion.\*\* The popover appears with opacity only, no slide. No glow.



\*\*Data source.\*\* Positions (sign, degree, longitude) come only from `frontend/src/fixtures/sky\_now.json`. The one-line meaning of each planet is fixed educational copy written once in the component, the same for every visitor, not engine output. The component computes nothing and invents no positions.



\### 2.2 Sample reading with "Show the logic" reveal



\*\*Behavior.\*\* The "A reading, explained" section shows one line in the product's format: a placement, a plain-language reading, and a confidence tier. A control labelled "Show the logic" expands the planetary reasoning beneath it, then collapses again. This is the single best proof of the product on the page, so it is the most polished interaction.



\*\*States.\*\* collapsed (default), expanding, expanded, collapsing. Smooth open via the grid-template-rows 0fr to 1fr technique or a transform and opacity reveal. Never animate height directly. The control is a real button with `aria-expanded` reflecting state.



\*\*Appearance.\*\* The reading sits on an ivory card on the light surface, navy text, the confidence tier as a chip (see 2.3), the logic in `--color-text-soft` once revealed.



\*\*Mobile.\*\* Full width, comfortable tap target, the expanded logic reflows to single column.



\*\*Reduced motion.\*\* Toggles instantly between collapsed and expanded with no transition.



\*\*Data source.\*\* Static example copy from `landing-spec.md` section C2, clearly framed as an example of the format. Not a live reading and not engine output.



\### 2.3 Confidence tier explainer



\*\*Behavior.\*\* The confidence chip (for example MEDIUM) is interactive. Pointing at or focusing it reveals a short popover that lists the tiers as ranges and states plainly that JunoPath aims to publish how its predictions hold up over time. Teaches the honesty model in one touch.



\*\*States.\*\* idle, hover or focus open, dismissed on Escape or blur. Same pin-on-tap pattern as the wheel on mobile.



\*\*Appearance.\*\* Tier chips may use the semantic secondaries for quiet coding: sage (`--color-sage`) for steadier tiers, clay (`--color-clay`) for speculative, gold for the chip outline. This is the only sanctioned use of sage and clay on this page, and it is semantic, not decorative.



\*\*Accessibility.\*\* Focusable, ARIA tooltip, Escape to close.



\*\*Reduced motion.\*\* Opacity only.



\*\*Content rule.\*\* Tiers shown as labels and ranges only. No raw probability percentage anywhere, because you cannot calibrate one yet.



\### 2.4 Micro-interactions



\- Reveal on scroll: content blocks fade and rise once on entry, staggered, per design-system section 4.

\- Hover and focus lift on buttons and cards: `translateY(-2px)` and a hairline brighten, `--dur-fast`.

\- Primary CTA: a slow gold edge shimmer, opacity-based, paused under reduced motion.

\- Mono numerals in the readout may settle to their value once on first reveal (a short count from a near value to the real one), off under reduced motion. Optional and subtle. If it adds any jank, cut it.



That is the entire interaction set. Nothing else.



\---



\## 3. FE-1 prompt (paste-ready)



```

Task: FE-1. Build the JunoPath landing page: shell, design system, all sections, guided copy, and the value-driven interactions that do not involve the wheel.

Branch: agent/antigravity/landing-shell



Read order before coding: docs/PROJECT\_CONTEXT.md, AGENTS.md, docs/frontend/landing-design-system.md, docs/frontend/landing-interactions.md, then docs/frontend/landing-spec.md (C1 structure and surfaces, C2 copy). Then code.



Build the full landing page per the design-system document, the interaction spec, and the page spec. This page is marketing, education, and a live-sky slot. It contains NO birth-details form and NO chart result. The primary CTA routes to /chart; if /chart is absent, it routes to an honest private-beta state. Never render a fabricated chart.



Theme and tokens: implement the design-system section 2 tokens as CSS custom properties exactly as named (--color-bg, --color-surface, --color-navy, --color-text, --color-gold, etc.). Beige base (--color-bg) with near-black text (--color-text) on light, ivory cards (--color-surface), full navy surfaces (--color-navy) with --color-text-on-dark for the contrast sections, Cormorant Garamond display, DM Sans body, DM Mono for all numbers, gold (--color-gold) as the only decorative accent. Sage and clay are semantic-only, used solely for confidence-tier coding per interactions 2.3, never as decoration. Each section component takes a surface="light" | "navy" prop and pulls the matching text, border, and accent tints from the tokens. No component hardcodes a hex value.



Sections, surfaces, and copy: build the page order and surface assignment in landing-spec C1 (hero, explainer, how-it-works, sample-reading on light; trust panel, CTA block, footer on navy) and use the C2 copy verbatim. Include the Disclaimer component on the sample-reading surface. Confidence shows as a tier label, never a raw percentage. Leave a hero mounting slot for the ZodiacWheel and readout (FE-2 fills it).



Interactions per landing-interactions.md, with all states:

\- 2.2 sample reading "Show the logic" reveal: a real button with aria-expanded, smooth open via grid-template-rows 0fr to 1fr (never animate height), collapsed by default, instant toggle under reduced motion. Content is the static example from landing-spec C2, framed as an example of the format.

\- 2.3 confidence tier explainer: the chip opens a small accessible popover listing tiers as ranges and the calibration intent. Hover or focus on desktop, tap to pin on mobile, Escape to close, opacity-only under reduced motion. Tier coding may use sage and clay. No raw percentage.

\- 2.4 micro-interactions: scroll reveals (CSS view() timeline with IntersectionObserver fallback), hover and focus lift, one ambient bloom, one CTA shimmer. Animate only transform and opacity. No JavaScript scroll handler that reads layout. Honor prefers-reduced-motion by disabling all motion.



Do not build anything in the interactions "Out" list. No carousels, particle fields, cursor effects, scroll-jacking, extra ambient loops, decorative sage or clay, or layout-moving animation.



Responsive (design-system section 3): mobile-first, verified from 320px up, single column at base, fluid type, 44px tap targets, focus-trapped mobile menu, no horizontal scroll at any width.



Performance: hero is pure CSS and inline SVG, paints before any script, LCP under 2.0s on mid-range Android over 4G, CLS under 0.05, inline SVG icons only, fonts self-hosted or preconnected with font-display swap and Cormorant Garamond subset, dimensions reserved everywhere.



Tests (AGENTS.md): the reveal button flips aria-expanded and shows and hides the logic; the confidence popover opens, pins, and closes on Escape; reduced-motion disables transitions; reveals are keyboard reachable. Add a one-screen component contract (props, states, dependencies) per new component under docs/frontend/components/.



Hard rules: fixtures only, no live API, no LLM, no astrology computation in the browser, probabilistic phrasing only, no deterministic promises, no health domain, no fear or urgency, no new dependencies without asking.



Allowed files: frontend/app/\*\* (landing route, layout, global token CSS), frontend/src/components/\*\* (all components except ZodiacWheel and readout), docs/frontend/components/\*.md contracts. Run python scripts/check\_allowed\_files.py before the PR.



Done when: npm run lint \&\& npm test \&\& npm run build is green and untampered, only allowed files changed, PR opened (not merged), HANDOFF.md updated. STOP and ask on spec ambiguity, a needed file outside the list, an urge to add a chart form, or an urge to add a dependency.

```



\---



\## 4. FE-2 prompt (paste-ready)



```

Task: FE-2. Build the interactive ZodiacWheel and SkyReadout, mounted in the FE-1 hero slot.

Branch: agent/antigravity/zodiac-wheel



Read order before coding: docs/PROJECT\_CONTEXT.md, AGENTS.md, docs/frontend/landing-design-system.md (2, 3, 4), docs/frontend/landing-interactions.md (2.1), docs/frontend/landing-spec.md (C3). Then code.



Build ZodiacWheel as pure inline SVG, rendered as an engraving on beige: the zodiac ring and twelve sign divisions as thin navy hairlines (--color-navy), gold (--color-gold) for the ring outline and degree ticks, and planet glyphs in navy at their longitudes. The hero sits on the light surface, so the wheel is navy and gold on beige, not a glowing dark wheel. It renders entirely from frontend/src/fixtures/sky\_now.json, which exists and is the contract. Read positions, place glyphs, compute nothing, modify nothing. If a needed field is missing, STOP and ask.



Make each glyph interactive per landing-interactions.md 2.1, with all states: idle, hover, focus, active (pinned on tap), dismissed. Pointing or focusing a glyph reveals a popover, styled as an ivory card (--color-surface) with --color-text and a --color-border hairline, showing the body's current sign and degree in DM Mono with a gold accent, plus one short fixed plain-language line on what the body represents. The position comes from the fixture. The meaning line is static educational copy written once in the component, identical for every visitor, not from the fixture and not computed. Desktop hover shows, tap pins, Escape and outside tap dismiss. Mobile is tap to pin. Glyphs are keyboard focusable in the fixed planet order (Sun first), Enter or Space pins, Escape closes. Provide a text alternative listing all positions for screen readers.



Build SkyReadout: a DM Mono list in --color-text of each body with its sign and degree, showing both decimal longitude and sign-degree form if both are in the fixture. Label the unit plainly as the current sky, computed live, never a personal reading. No houses.



Mount both in the hero slot. Responsive per design-system section 3: wheel sizes to min(92vw, 440px), never overflows, under the hero text on base with the readout below, side by side from md, readout reflows stacked at base and two columns from sm.



Motion: the wheel is static geometry with real glyph positions and does not spin, because that would misrepresent the sky. Allowed life is a one-time ink draw-in on entry (stroke or opacity reveal, compositor-only) and a faint gold accent on the ring. Popovers appear with opacity only under reduced motion. Crisp at any size.



Tests: a glyph popover opens on focus and pins on activate and closes on Escape; keyboard reaches every glyph; the screen-reader text alternative lists all positions; nothing renders from outside the fixture. Add a component contract for ZodiacWheel and SkyReadout.



Hard rules: fixtures only, no live API, no LLM, no computation, no new dependencies without asking. Build the popover by hand; do not add a tooltip library.



Allowed files: frontend/src/components/\*\* (ZodiacWheel, SkyReadout, popover), the hero file from FE-1 only to mount them, docs/frontend/components/\*.md contracts. Run python scripts/check\_allowed\_files.py before the PR.



Done when: tests green, only allowed files changed, PR opened, HANDOFF.md updated. STOP and ask on any ambiguity or missing fixture field.

```



\---



\## 5. QA additions for interactions



Run alongside the responsive, motion, performance, theme, and honesty checks in the design-system doc.



\- Sample-reading reveal: opens and closes smoothly, button shows correct aria-expanded, keyboard operable, instant under reduced motion.

\- Wheel popover: hover on desktop, tap-to-pin on mobile, Escape and outside-tap dismiss, every glyph reachable by keyboard in planet order, screen-reader alternative present and correct, styled as an ivory card.

\- Confidence explainer: opens on hover and focus, closes on Escape, shows tiers as ranges only with no percentage, sage and clay used only for tier coding.

\- Junk check: none of the "Out" list appears. Gold is the only decorative accent, one ambient loop, no layout-moving animation, no library added for tooltips or motion.

\- Fixture check: every position shown traces to sky\_now.json; no position is computed or invented; planet meanings are fixed copy, not fixture-derived.

