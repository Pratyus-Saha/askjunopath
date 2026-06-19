\# JunoPath Landing Page Spec



Commit as `docs/frontend/landing-spec.md`. Pairs with `landing-design-system.md` (tokens, two-tone surfaces, motion) and `landing-interactions.md` (the wheel tooltip, the sample-reading reveal, the confidence explainer).



\## Voice and surface notes



Voice is editorial, precise, calm, and trustworthy. Short sentences next to longer ones. No fear, no urgency, no guarantees, no supernatural mechanism claims. Confidence is shown as a tier, never a raw percentage. No em dashes. The page reads like a serious instrument explaining itself, not a horoscope app.



Each section names its surface from the design system's two-tone rhythm (2.1b). Light sections use the beige base with near-black text; navy sections use the dark surface with light text. The alternation is what gives the page weight and stops it reading as a flat beige wall.



\## C1. Page order and surfaces



1\. Sticky nav, over the hero (light). Links: How it works, Why trust this, and the primary CTA.

2\. Hero (light). Headline, subheadline, primary and secondary CTA, and the engraved sky wheel rendered in navy and gold on beige.

3\. What your chart actually is (light).

4\. How it works (light, ivory cards for the three steps).

5\. Why trust the math (navy surface). The dark section gives this its gravity.

6\. A reading, explained (light, on an ivory card).

7\. Generate your chart CTA block (navy surface, gold CTA).

8\. Footer (navy surface). Plain links, no urgency.



\## C2. Guided copy



\### Nav CTA

Generate your chart



\### Hero headline

Your birth chart, computed exactly. Explained in plain words.



\### Hero subheadline

We calculate your chart in code, the same math an astronomer would check, and show you the reasoning behind every reading. No vague lines. No fear. Just the chart, and what it means, with our confidence stated openly.



\### Primary CTA

Generate your chart



\### Secondary CTA

See how it works



\### What your chart actually is

A birth chart is a snapshot of the sky at the exact moment and place you were born. JunoPath measures the positions to the degree, then explains the interpretation one step at a time. You are never asked to believe a black box. You watch the reasoning happen.



\### How it works

1\. Enter birth date, time, and place.

&#x20;  Exact time sets the houses and the timing. Without it, time-dependent results are limited, and we tell you which ones.

2\. The engine computes the chart in code and checks it against reference software.

&#x20;  The same positions a precise astrology tool would produce, shown in plain language.

3\. You get the chart and the reading, with the placement behind every line.

&#x20;  You can see why each interpretation was made, and decide for yourself what to do with it.



\### Why trust the math

Most astrology asks you to take its word. JunoPath shows its work. We calculate chart positions in code and validate them against established reference software, so the numbers are not guesswork. Every interpretation points back to the placement it came from. We state our confidence openly, and our aim is to publish how those predictions hold up over time, so trust is earned rather than assumed. The math can be exact while the reading stays careful: a lens for thinking, not a promise about the future.



\### A reading, explained

This is the shape of every line JunoPath writes. It is an example of the format, not your reading.



Placement: 10th house cusp sublord, Venus.

Reading: Career movement is more likely to arrive through people and relationships than through credentials alone, with a more active window in the second half of the year.

Confidence: MEDIUM.

The logic: Venus, as the 10th cusp sublord, also signifies the houses of income and gain, which points the career theme toward connection-driven roles. The current period lords activate that link.

Disclaimer: A reading is a structured way to think about your life, not a forecast of fixed events. We state our confidence and we may be wrong.



> Note for build: replace this example with a real, clearly labelled engine output line once one exists. Keep it framed as an example of the format and never as the visitor's personal reading.



\### Generate your chart CTA block

Enter your details and see your chart, with the logic behind every line.



\## C3. Zodiac wheel spec



The wheel is the signature visual and the proof the instrument is real and current. It renders as an engraving on beige, not a glowing dark dial.



\- Pure inline SVG. Crisp at any size.

\- Rendered in navy hairlines with gold (`--color-gold`) for the ring outline and degree ticks, planet glyphs in navy. It sits on the light hero surface.

\- Renders entirely from `frontend/src/fixtures/sky\_now.json`. Reads positions and places glyphs. Computes no astrology in the browser. Does not modify fixture values.

\- Required per-planet fields read from the fixture: sign, degree within sign, and decimal longitude. If a required field is missing, stop and ask.

\- Shows the zodiac ring, twelve sign divisions, degree ticks, and planet glyphs at their longitudes. No houses, because the current sky has no birth location to anchor them.

\- Shows the current sky only. The label states this plainly. It never implies this is the visitor's personal reading.

\- Interactive per `landing-interactions.md` section 2.1: a glyph reveals a small popover with that body's current sign and degree in DM Mono plus one short fixed line on what the body represents. The position comes from the fixture; the meaning line is static educational copy, the same for everyone, not computed and not personalised.

\- DM Mono readout beside or below the wheel, in `--color-text`, listing each body, for example `Moon 18°24' Scorpio`. Show the decimal longitude too if present in the fixture.

\- Motion: static geometry, no spin (a spin would misrepresent the sky). Allowed life is a one-time ink draw-in on entry, compositor-only, and a faint gold accent on the ring. Honor prefers-reduced-motion.

\- Responsive: sizes to `min(92vw, 440px)`, never overflows, under the hero text on small screens with the readout stacked below, beside the readout from the md breakpoint.

