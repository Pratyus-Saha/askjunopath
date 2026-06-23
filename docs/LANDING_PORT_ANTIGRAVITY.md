# LANDING_PORT_ANTIGRAVITY.md

Port the JunoPath landing page from the Lovable reference app (`sky-logic-map`,
TanStack Start) into the Next.js repo, framework wiring only, design unchanged.

> Written for an amnesiac agent session. Every path, transform, and cut is
> pre-decided. Do not improvise. If a step contradicts what you see in the repo,
> stop and report rather than guessing.

---

## 0. Source of truth and what was verified

Source repo: `github.com/theclericstore/sky-logic-map` (read-only reference).
Live render to diff against: `https://sky-logic-map.lovable.app/`.

Verified facts the plan depends on (confirmed by reading the source):

1. The landing imports **zero** `ui/*` components, **zero** Radix, **zero** npm
   libraries. Only React plus the seven `juno/*` components plus CSS.
2. Brand colors (`text-gold`, `text-ivory`, `bg-ivory`, `border-gold`, etc.) are
   **plain CSS classes** in `styles.css` pointing at `:root` hex variables. They
   are not Tailwind theme colors. They do not depend on Tailwind v4.
3. Every `juno/*` component and every section in `index.tsx` uses client APIs
   (`useState`, `useEffect`, `useRef`, `window`, `canvas`, `IntersectionObserver`).
   All of them become Next.js client components.
4. The only Tailwind-v4-specific CSS is lines 1-63 of `styles.css`
   (`@import "tailwindcss"`, `@source`, `@import "tw-animate-css"`,
   `@custom-variant`, `@theme inline`). The landing does not need any of it.

Result: no new dependencies, and the target's existing Tailwind setup stays
untouched. You append a design layer of vanilla CSS and copy components.

## 0.1 Path and Tailwind confirmation (FOUNDER, 2 minutes, do first)

The target paths below are inferred from the codebase audit, not direct access.
Confirm before any lane runs:

```bash
cd C:\Users\assas\askjunopath
ls frontend/app           # expect: page.tsx (boilerplate), chart/, layout.tsx
ls frontend/src           # expect: components/, types/, fixtures/
cat frontend/package.json | findstr tailwind   # note the version
cat frontend/app/layout.tsx                     # note where global CSS imports
```

If the frontend lives at repo root instead of `frontend/`, adjust every
`frontend/` prefix below. If `app/` does not exist (Pages Router, not App
Router), stop and report. The whole brief assumes App Router.

The Tailwind version does not change the plan because the design layer is vanilla
CSS. It only changes one debug note (see 5. Debug order, row "font utilities").

---

## 1. Global constraints (apply to every task)

- No new npm dependencies. None are needed. If you think you need one, stop and report.
- One lane touches one file set. Lanes do not edit each other's files.
- Every ported component file starts with `"use client";` as line 1.
- Copy design code verbatim. Change imports and routing only. Do not restyle,
  rename classes, reorder sections, or "improve" copy.
- Writing in any new copy follows house rules: no em dashes, plain direct
  sentences. You are not writing new copy here, so this rarely applies.
- Commit per task with the message shown. Keep the branch building.

## 1.1 Files to NEVER port (Lovable / TanStack only)

These exist in the source and must not be copied:

```
src/router.tsx
src/routeTree.gen.ts
src/routes/__root.tsx
src/routes/sitemap[.]xml.ts
src/server.ts
src/start.ts
src/lib/lovable-error-reporting.ts
src/lib/error-capture.ts
src/lib/error-page.ts
src/components/ui/*           (landing uses none of them)
the QueryClient / QueryClientProvider wiring from __root.tsx
the first 63 lines of src/styles.css (v4 header + @theme inline)
```

## 1.2 Source to target file map

| Source (sky-logic-map) | Target (askjunopath) | Lane |
|---|---|---|
| `src/styles.css` lines 64-582 (design layer) | append into `frontend/app/globals.css` | foundation |
| Google Fonts link (from `__root.tsx`) | `frontend/app/layout.tsx` head | foundation |
| `src/lib/utils.ts` (the `cn` helper) | `frontend/src/lib/utils.ts` (skip if it already exists) | foundation |
| `src/components/juno/Starfield.tsx` | `frontend/src/components/juno/Starfield.tsx` | page |
| `src/components/juno/Navbar.tsx` | `frontend/src/components/juno/Navbar.tsx` | page |
| `src/components/juno/JourneyRail.tsx` | `frontend/src/components/juno/JourneyRail.tsx` | page |
| `src/components/juno/ChartWheel.tsx` | `frontend/src/components/juno/ChartWheel.tsx` | page |
| `src/components/juno/Reading.tsx` | `frontend/src/components/juno/Reading.tsx` | page |
| `src/components/juno/Reveal.tsx` | `frontend/src/components/juno/Reveal.tsx` | page |
| `src/components/juno/Astrolabe.tsx` | `frontend/src/components/juno/Astrolabe.tsx` | page |
| body of `src/routes/index.tsx` (all sections) | `frontend/src/components/juno/Landing.tsx` | page |
| head/meta from `index.tsx` | `frontend/app/page.tsx` `metadata` export | page |

---

## LANE A: port-foundation

Owns: `frontend/app/globals.css`, `frontend/app/layout.tsx`,
`frontend/src/lib/utils.ts`.

Goal: the design system loads. A blank page renders deep navy background, ivory
text, and the three fonts, with all custom classes available.

### A1. Confirm the `cn` helper exists

```bash
cat frontend/src/lib/utils.ts 2>/dev/null || echo MISSING
```

If MISSING, copy from source `src/lib/utils.ts` verbatim. It is the standard
shadcn `cn` (clsx + tailwind-merge). `clsx` and `tailwind-merge` are already in
most Next setups; confirm with `findstr` in package.json. If absent, stop and
report (this is the one place a dependency might be missing).

### A2. Append the design layer to globals.css

Open source `src/styles.css`. Copy **lines 64 through 582** (start at `:root {`,
take everything to end of file). Append to `frontend/app/globals.css` **after**
the existing `@tailwind`/`@import "tailwindcss"` directives so the custom classes
win the cascade.

Two edits to the copied block:

1. The `@layer base` block has `* { border-color: var(--color-border); }`.
   Change `var(--color-border)` to `var(--border)`. The `--color-*` names only
   exist through the v4 `@theme` block, which you are not copying.
2. You may drop the `.dark { ... }` block (lines ~119-153). The landing is
   dark-by-default through `:root` and never toggles a `.dark` class. Keeping it
   is harmless; dropping it is cleaner. Either is fine.

Do not copy lines 1-63.

### A3. Load the three fonts in layout.tsx

Add to `frontend/app/layout.tsx`. The CSS references the literal family names
`"Cormorant Garamond"`, `"DM Sans"`, `"DM Mono"`, so a plain stylesheet link is
the lowest-risk path and keeps the CSS variables working unchanged:

```tsx
// inside the <head> of the root layout, or via a <link> element
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
<link
  rel="stylesheet"
  href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;500&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@300;400;500&display=swap"
/>
```

If the existing layout already imports `globals.css`, leave that import. If not,
add `import "./globals.css";` at the top of layout.tsx.

(Optional, post-launch: switch to `next/font/google` to remove the render-blocking
link. Do not do this now; it changes the family names to hashed values and means
rewiring the CSS variables. Out of scope.)

### A4. Foundation gate

```bash
cd frontend && npm run dev
```

Temporarily put `<div className="min-h-screen bg-navy"><h1 className="font-serif text-ivory text-6xl p-10">JunoPath</h1><p className="kicker text-gold p-10">COMPUTED, NOT GUESSED</p></div>` in `app/page.tsx`.

Pass when: background is deep navy (#0B1A2B), the heading is ivory in a serif
face (Cormorant Garamond), and `.kicker` renders as small gold uppercase mono
with wide tracking. Revert the temporary page after checking.

```bash
git add frontend/app/globals.css frontend/app/layout.tsx frontend/src/lib/utils.ts
git commit -m "feat(landing): port JunoPath design layer, fonts, cn helper"
```

---

## LANE B: port-page

Owns: `frontend/src/components/juno/*`, `frontend/app/page.tsx`.
Depends on Lane A being merged (needs the CSS classes to render correctly).

Goal: the full landing renders and matches the live Lovable site.

### B1. Port the seven juno components

For each of the seven files in the map, copy the source file to the target path,
then apply exactly two transforms:

1. Add `"use client";` as line 1 (blank line after it).
2. Leave every other line, including all `@/` imports, unchanged. The `@/` alias
   already resolves in the target (it resolves `frontend/src/`). Confirm with one
   build; if `@/components/juno/...` fails to resolve, check `tsconfig.json`
   `paths` and report rather than rewriting imports.

No other edits. These components use only React and `window`/`canvas`/observers,
all of which run fine in a client component.

Port order (no inter-dependencies except that `Landing` imports all of them):
Starfield, Navbar, JourneyRail, ChartWheel, Reading, Reveal, Astrolabe.

Commit after the seven compile:

```bash
git add frontend/src/components/juno/
git commit -m "feat(landing): port seven juno components as client components"
```

### B2. Create Landing.tsx from the index.tsx body

Source `src/routes/index.tsx` has all sections defined inline (Hero, Instrument,
ChartLegend, SkyModelPanel, PlanetTable, Method, Evidence, AIRole,
ReadingSection, FAQ, Try, Footer) plus the `Index()` component that composes them.

Create `frontend/src/components/juno/Landing.tsx`:

1. Line 1: `"use client";`
2. Copy everything from `index.tsx` **except**:
   - the `import { createFileRoute } from "@tanstack/react-router";` line (delete it)
   - the `export const Route = createFileRoute("/")({ ... });` block (delete the
     whole block, including its `head` meta; that meta moves to page.tsx in B3)
3. Keep all the `@/components/juno/...` imports and the `useEffect`/`useState`
   imports from react.
4. Rename the composer: change `function Index() {` to
   `export default function Landing() {`. Keep its body exactly.
5. Every other section function stays as a plain `function Hero()` etc. in the
   same file. Do not split them out now.

### B3. Create page.tsx

Replace `frontend/app/page.tsx` with:

```tsx
import type { Metadata } from "next";
import Landing from "@/components/juno/Landing";

const DESCRIPTION =
  "JunoPath computes your birth chart to the arc-second and explains the reasoning behind every line. A precise instrument, not a horoscope.";

export const metadata: Metadata = {
  title: "JunoPath — The exact sky you were born under",
  description: DESCRIPTION,
  openGraph: {
    title: "JunoPath — Astrology, computed and explained",
    description: DESCRIPTION,
  },
};

export default function Page() {
  return <Landing />;
}
```

Note: the source `og:image` points at a Lovable R2 URL. Leave it out for now.
Replacing it with a JunoPath-owned asset is a separate post-port task, not a
blocker.

### B4. Page gate

```bash
cd frontend && npm run build && npm run dev
```

Pass when the page renders top to bottom with no console errors: Starfield
canvas behind everything, Navbar, the left JourneyRail, the hero with staggered
rise-in, the ChartWheel in the Instrument section, the Method section on ivory
background, Evidence, AIRole, the Reading tabs, the FAQ accordion expanding, the
Try CTA, and the Footer with the rotating orbit SVG. Anchor buttons
("Generate your chart", nav links) scroll smoothly to their sections.

```bash
git add frontend/src/components/juno/Landing.tsx frontend/app/page.tsx
git commit -m "feat(landing): compose JunoPath landing page in Next App Router"
```

---

## LANE C: port-qa

Owns: a fix list and small corrective commits. Runs after B merges.

### C1. Side-by-side visual diff

Open the live reference `https://sky-logic-map.lovable.app/` next to the local
build. Walk every section. Record any pixel-level divergence: spacing, font
weight, color, animation timing. Most divergences trace to one of: the design CSS
imported before Tailwind instead of after (cascade), a missing font weight, or a
dropped CSS block. Fix the cause, not the symptom.

### C2. Reduced motion

Set OS "reduce motion" on. The starfield parallax, hero rise, ring rotation, and
hub pulse must quiet down (the source CSS has `prefers-reduced-motion` blocks at
lines ~314 and ~419). Confirm they take effect.

### C3. Mobile

Test at 375px and 768px widths. The hero type scales (`text-[48px] sm:text-[68px]
md:text-[92px]`), the three-column Instrument grid collapses, the JourneyRail
behavior on narrow screens is acceptable. Note anything broken; fix only layout,
never redesign.

### C4. Build and lint

```bash
cd frontend && npm run build && npm run lint
```

Pass when build is clean and lint has no new errors from ported files. React 19
to React 18 note: if any ported component uses a React 19 only API, the build
will flag it. The landing components use only stable hooks, so this should be
clean. If lint complains about `useEffect` deps in the ported files, leave them
as-is (matching source) unless the build fails.

```bash
git add -A && git commit -m "fix(landing): qa corrections for parity, mobile, reduced-motion"
```

---

## 5. Debug order (symptom, likely cause, fix)

| Symptom | Likely cause | Fix |
|---|---|---|
| Page is unstyled / white background | design layer imported before Tailwind, or globals.css not imported in layout | move the appended block after Tailwind directives; confirm `import "./globals.css"` in layout |
| Serif text shows as default sans | font link not loaded, or Tailwind's own `.font-serif` utility winning over the custom class | confirm the Google Fonts link is in the layout head; ensure the design CSS sits after Tailwind so the unlayered `.font-serif` wins |
| `text-gold` / `bg-ivory` have no effect | the `:root` palette block (styles.css 64+) was not copied, or copied above the class definitions | copy the full design layer 64-582 as one block |
| `@/components/juno/...` fails to resolve | `tsconfig.json` paths alias points elsewhere in target | check `compilerOptions.paths`; report, do not rewrite imports |
| Hydration mismatch warning | a juno component missing `"use client"` | add it as line 1 |
| `Footer` year or animations error on server | client API touched during SSR | confirm `"use client"` present; these run only after mount |
| A dead `animate-*` utility | it came from `tw-animate-css`, which you skipped | the landing does not use any; if one appears, replace with the equivalent custom keyframe class already in the design layer |
| `* { border-color }` build error | left as `var(--color-border)` | change to `var(--border)` |

---

## 6. Pre-decided cuts (do not reopen mid-lane)

- No `next/font` migration now. Stylesheet link only.
- No og:image now. Lovable R2 URL stays dropped until a JunoPath asset exists.
- No section extraction. All sections live in one `Landing.tsx`. Splitting into
  per-section files is a later refactor, not part of this port.
- No `ui/*` components. The landing needs none. Do not port them "just in case."
- No copy edits. The reference text ships as written.
- No new routes. This lane delivers `/` only. The chart page and predict page are
  separate work.

## 7. Done definition

All three lane gates pass, the local build matches the live Lovable site section
by section, mobile and reduced-motion behave, and `npm run build` is clean on
main. At that point `/` is the JunoPath landing, and the boilerplate Next page is
gone.
