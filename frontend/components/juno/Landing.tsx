"use client";
import Link from "next/link";


import { useEffect, useState } from "react";
import { Starfield } from "@/components/juno/Starfield";
import { Navbar } from "@/components/juno/Navbar";
import { JourneyRail } from "@/components/juno/JourneyRail";
import { ChartWheel, PLANETS } from "@/components/juno/ChartWheel";
import { Reading } from "@/components/juno/Reading";
import { Reveal } from "@/components/juno/Reveal";
import { Astrolabe } from "@/components/juno/Astrolabe";

const DESCRIPTION =
  "JunoPath computes your birth chart to the arc-second and explains the reasoning behind every line. A precise instrument, not a horoscope.";


export default function Landing() {
  return (
    <main className="relative min-h-screen overflow-x-clip">
      <Starfield />
      <div className="fixed top-0 left-0 right-0 z-[60] pointer-events-none">
        <div className="mx-auto flex h-[60px] max-w-[1240px] items-center justify-end px-6 md:px-10">
          <div className="pointer-events-auto mr-[170px] md:mr-[190px]">
            <Link 
              href="/login" 
              className="text-[13px] font-sans tracking-wide px-4 py-1.5 rounded transition-colors shadow-lg"
              style={{ backgroundColor: "var(--navy)", color: "#C9A96E", border: "1px solid rgba(199, 154, 78, 0.4)" }}
            >
              Sign In
            </Link>
          </div>
        </div>
      </div>
      <Navbar />
      <JourneyRail />
      <Hero />
      <Instrument />
      <Method />
      <AIRole />
      <Evidence />
      <ReadingSection />
      <FAQ />
      <Try />
      <Footer />
    </main>
  );
}

/* --------------------------------- HERO --------------------------------- */

function Hero() {
  return (
    <section
      id="hero"
      className="relative isolate min-h-[100svh] pt-[140px] pb-28 px-6 md:px-10 flex items-center"
    >
      <Astrolabe />
      <div className="hero-glow" aria-hidden />
      <div className="relative mx-auto w-full max-w-[1100px] text-center">
        <p className="hero-rise kicker" data-d="1" style={{ color: "var(--gold-bright)" }}>
          <span>YOUR ASCENDANT — LIBRA 27°18′</span>
          <span className="mx-3 text-muted-dark">·</span>
          <span className="text-ivory">COMPUTED, NOT GUESSED</span>
        </p>

        <h1
          className="hero-rise font-serif text-ivory mt-10 text-[48px] sm:text-[68px] md:text-[92px] leading-[1.02] tracking-[-0.02em]"
          data-d="2"
        >
          Read the exact sky
          <br />
          you were born under.
        </h1>

        <p
          className="hero-rise mx-auto mt-10 max-w-[680px] text-[16px] md:text-[18px] leading-[1.65] text-muted-dark"
          data-d="3"
        >
          <span className="text-ivory">AI-powered astrology, built on precise chart computation.</span>{" "}
          Your chart is calculated in code and validated against reference software,
          then explained with transparent AI reasoning — placement, evidence, and
          stated confidence on every line.
        </p>

        <div className="hero-rise mt-12 flex flex-wrap items-center justify-center gap-6" data-d="4">
          <Link
            href="/login"
            className="btn-juno btn-juno-light inline-flex items-center justify-center"
            style={{ background: "var(--ivory)", color: "var(--ink)" }}
          >
            Generate your chart
          </Link>
          <button
            className="link-gold text-[13.5px] font-mono tracking-[0.06em]"
            onClick={() => document.getElementById("reading")?.scrollIntoView({ behavior: "smooth" })}
          >
            See how a reading is built →
          </button>
        </div>

        <p
          className="hero-rise mt-20 kicker"
          data-d="5"
          style={{ color: "var(--gold)", opacity: 0.85 }}
        >
          KP-NEWCOMB · TRUE NODE · PLACIDUS · VALIDATED AGAINST REFERENCE SOFTWARE
        </p>
      </div>
    </section>
  );
}

/* ------------------------------ INSTRUMENT ------------------------------ */

function Instrument() {
  return (
    <section id="basics" className="relative">
      <div className="mx-auto max-w-[1300px] px-6 md:px-10 py-28 md:py-40">
        <Reveal>
          <div className="text-center kicker text-gold">
            01 · THE INSTRUMENT &nbsp;·&nbsp; AN AUDITABLE CHART
          </div>
        </Reveal>

        <Reveal delay={1}>
          <div className="mt-10 text-center max-w-[760px] mx-auto">
            <h2 className="font-serif text-ivory text-[40px] md:text-[58px] leading-[1.06] tracking-[-0.015em]">
              A precision instrument,
              <br />
              not a decorative wheel.
            </h2>
            <p className="mt-6 text-[15.5px] md:text-[17px] leading-[1.7] text-muted-dark">
              Four concentric layers — zodiac, degree, house, planet — wrapped
              around a live intelligence hub. Hover any planet to read its
              placement and see its aspects light up.
            </p>
          </div>
        </Reveal>

        <div className="mt-16 grid gap-10 lg:gap-14 lg:grid-cols-[300px_1fr_300px] items-center">
          <Reveal delay={1}>
            <ChartLegend />
          </Reveal>
          <Reveal delay={2}>
            <ChartWheel size={680} showTable={false} />
          </Reveal>
          <Reveal delay={3}>
            <SkyModelPanel />
          </Reveal>
        </div>

        <Reveal delay={3}>
          <div className="mt-20 pt-10 border-t" style={{ borderColor: "rgba(199,154,78,0.18)" }}>
            <div className="kicker text-gold-bright">POSITIONS · COMPUTED, NOT GUESSED</div>
            <div className="mt-6 grid lg:grid-cols-[1fr_1.2fr] gap-10 items-start">
              <p className="font-serif text-ivory text-[24px] md:text-[30px] leading-[1.3] max-w-[460px]">
                Every position the wheel renders is a value the engine produced
                — and that you can read in the table.
              </p>
              <PlanetTable />
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

function ChartLegend() {
  const layers = [
    { k: "01", t: "Zodiac band",  s: "Sign glyphs + 30° sectors" },
    { k: "02", t: "Degree ring",  s: "1° ticks · cardinal markers" },
    { k: "03", t: "House band",   s: "Placidus · 1–12 cusps" },
    { k: "04", t: "Planet orbit", s: "Bodies + nodes + ASC" },
    { k: "05", t: "Intel. hub",   s: "Live chart summary" },
  ];
  const aspects = [
    { c: "rgba(226,192,121,0.9)",  l: "Conjunction · 0°" },
    { c: "rgba(226,192,121,0.75)", l: "Opposition · 180°" },
    { c: "rgba(111,138,114,0.85)", l: "Trine · 120°" },
    { c: "rgba(178,106,76,0.85)",  l: "Square · 90°", d: true },
    { c: "rgba(244,236,221,0.7)",  l: "Sextile · 60°", d: true },
  ];
  return (
    <div className="space-y-8">
      <div>
        <div className="kicker text-gold">LAYERS</div>
        <div className="mt-4 space-y-2 font-mono text-[12px]">
          {layers.map((L) => (
            <div key={L.k} className="flex items-baseline gap-3 text-ivory">
              <span className="text-gold-bright tabular-nums w-6">{L.k}</span>
              <span className="text-ivory-warm w-[110px]">{L.t}</span>
              <span className="text-muted-dark text-[11px] tracking-[0.06em]">{L.s}</span>
            </div>
          ))}
        </div>
      </div>
      <div>
        <div className="kicker text-gold">ASPECTS · ON HOVER</div>
        <div className="mt-4 space-y-2 font-mono text-[11.5px]">
          {aspects.map((a) => (
            <div key={a.l} className="flex items-center gap-3 text-muted-dark">
              <svg width="28" height="6" className="shrink-0">
                <line x1="0" y1="3" x2="28" y2="3" stroke={a.c}
                  strokeWidth="1.4" strokeDasharray={a.d ? "3 3" : undefined} />
              </svg>
              <span className="tracking-[0.08em]">{a.l}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SkyModelPanel() {
  const steps = [
    { t: "Birth data processed",     m: "lat · lon · UT" },
    { t: "Chart calculated",         m: "Placidus · KP" },
    { t: "Significators identified", m: "rulers · sublords" },
    { t: "Timing systems evaluated", m: "Vimshottari dasha" },
    { t: "AI explanation generated", m: "with evidence" },
  ];
  return (
    <div className="sky-model">
      <div className="kicker text-gold-bright">COMPUTED SKY MODEL</div>
      <div className="mt-2 font-serif text-ivory text-[22px] leading-[1.25]">
        A precision
        <br />
        workflow.
      </div>
      <div className="mt-5">
        {steps.map((s) => (
          <div key={s.t} className="sm-row">
            <span className="sm-dot" aria-hidden />
            <span className="font-mono text-[12px] tracking-[0.06em] text-ivory">{s.t}</span>
            <span className="font-mono text-[10.5px] tracking-[0.18em] uppercase text-muted-dark">{s.m}</span>
          </div>
        ))}
      </div>
      <div className="mt-5 pt-4 border-t" style={{ borderColor: "rgba(199,154,78,0.18)" }}>
        <div className="flex items-center gap-2">
          <span className="hub-pulse inline-block w-1.5 h-1.5 rounded-full" style={{ background: "var(--gold-bright)" }} />
          <span className="font-mono text-[10.5px] tracking-[0.2em] uppercase text-gold-bright">
            AI reading ready
          </span>
        </div>
      </div>
    </div>
  );
}

function PlanetTable() {
  return (
    <div className="font-mono text-[13px]">
      <div className="grid grid-cols-[28px_56px_1fr_auto] gap-x-6 py-2 text-[10.5px] tracking-[0.18em] uppercase text-muted-dark">
        <span></span>
        <span></span>
        <span>Sign</span>
        <span className="text-right">Degree</span>
      </div>
      <div className="h-px hairline-gold" />
      {PLANETS.map((p) => (
        <div
          key={p.key}
          className="grid grid-cols-[28px_56px_1fr_auto] gap-x-6 items-baseline py-3 border-b transition-colors hover:bg-[rgba(226,192,121,0.05)] cursor-default"
          style={{ borderColor: "rgba(199,154,78,0.18)" }}
        >
          <span className="text-gold-bright text-[15px] leading-none">{p.glyph}</span>
          <span className="text-gold tracking-[0.16em]">{p.label}</span>
          <span className="text-ivory tracking-[0.12em]">{["ARIES","TAURUS","GEMINI","CANCER","LEO","VIRGO","LIBRA","SCORPIO","SAGITTARIUS","CAPRICORN","AQUARIUS","PISCES"][p.signIdx]}</span>
          <span className="text-ivory-warm tabular-nums">
            {String(p.deg).padStart(2, "0")}°{String(p.min).padStart(2, "0")}′
          </span>
        </div>
      ))}
    </div>
  );
}

/* -------------------------------- METHOD -------------------------------- */

function Method() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const el = document.getElementById("method");
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            // animate plotting 0 → 3
            let i = 0;
            const tick = () => {
              i++;
              setStep(i);
              if (i < 3) setTimeout(tick, 650);
            };
            setTimeout(tick, 400);
            io.disconnect();
          }
        }
      },
      { threshold: 0.2 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const steps = [
    {
      n: "1",
      title: "Birth input becomes precise sky coordinates.",
      body: "Date, time, and place are converted to exact ecliptic longitudes for every planet and house cusp — to the arc-second.",
      foot: "INPUT → EPHEMERIS → LONGITUDES",
    },
    {
      n: "2",
      title: "Engine computes chart, houses, dashas, key placements.",
      body: "Positions are produced in code with KP-Newcomb and Placidus, then cross-checked against reference astrology software.",
      foot: "COMPUTE → VERIFY → DASHAS",
    },
    {
      n: "3",
      title: "AI explains the interpretation with evidence and confidence.",
      body: "AI structures and explains the reading on top of the deterministic math — naming the placement and stating how sure the system is.",
      foot: "SCORING → SYNTHESIS → EXPLAIN",
    },
  ];

  return (
    <section id="method" className="bg-ivory text-ink relative">
      <div className="mx-auto max-w-[1240px] px-6 md:px-10 py-28 md:py-40">
        <Reveal>
          <div className="kicker" style={{ color: "var(--gold)" }}>
            02 · HOW A READING IS BUILT
          </div>
        </Reveal>
        <Reveal delay={1}>
          <div className="mt-10 flex items-end justify-between flex-wrap gap-6">
            <h2
              className="font-serif text-[40px] md:text-[58px] leading-[1.05] max-w-[820px]"
              style={{ color: "var(--ink)" }}
            >
              From birth time
              <br /> to reasoned reading.
            </h2>
            <div className="font-mono text-[11px] tracking-[0.18em] uppercase text-ink/55 max-w-[280px]">
              Three stages. The math is deterministic.
              The explanation is AI-structured.
            </div>
          </div>
        </Reveal>

        <div className="mt-16 grid gap-6 md:grid-cols-3">
          {steps.map((s, i) => (
            <Reveal key={s.n} delay={((i + 1) as 1 | 2 | 3)}>
              <article className="juno-card-light h-full flex flex-col">
                <div className="flex items-center justify-between">
                  <div className="font-mono text-[56px] leading-none" style={{ color: "var(--gold)" }}>
                    {s.n}
                  </div>
                  <div className="kicker text-ink/40">STEP {s.n}/3</div>
                </div>
                <h3 className="mt-8 font-serif text-[22px] md:text-[26px] leading-[1.22]" style={{ color: "var(--ink)" }}>
                  {s.title}
                </h3>
                <p className="mt-4 text-[14.5px] leading-[1.65] text-ink/75 flex-1">{s.body}</p>
                <div className="mt-7 pt-4 border-t font-mono text-[10.5px] tracking-[0.18em] uppercase text-ink/55"
                  style={{ borderColor: "rgba(20,32,46,0.12)" }}>
                  {s.foot}
                </div>
              </article>
            </Reveal>
          ))}
        </div>

        <Reveal delay={3}>
          <div className="mt-16 pt-12 border-t grid gap-10 lg:grid-cols-[1fr_1.4fr] items-start" style={{ borderColor: "rgba(20,32,46,0.12)" }}>
            <div>
              <div className="kicker text-ink/55">LIVE COMPUTE · PLACING POSITIONS</div>
              <p className="mt-5 font-serif text-[26px] leading-[1.3] text-ink max-w-[420px]">
                As the engine computes, the wheel fills in.
                You see math becoming geometry.
              </p>
              <div className="mt-6 font-mono text-[11px] tracking-[0.16em] uppercase text-ink/55">
                {step === 0 && "AWAITING INPUT…"}
                {step === 1 && "PLACED · SUN"}
                {step === 2 && "PLACED · SUN, MOO"}
                {step >= 3 && "PLACED · SUN, MOO, MER"}
              </div>
            </div>
            <div className="font-mono text-[11.5px] tracking-[0.14em] uppercase text-ink/70 grid grid-cols-2 sm:grid-cols-3 gap-px bg-ink/10 border border-ink/10">
              {[
                ["EPHEMERIS", step >= 1 ? "LOADED" : "—"],
                ["LONGITUDES", step >= 1 ? "RESOLVED" : "—"],
                ["HOUSES", step >= 2 ? "PLACIDUS" : "—"],
                ["DASHAS", step >= 2 ? "VIMSHOTTARI" : "—"],
                ["ASPECTS", step >= 3 ? "MAPPED" : "—"],
                ["AI READING", step >= 3 ? "READY" : "QUEUED"],
              ].map(([k, v]) => (
                <div key={k} className="bg-ivory p-5">
                  <div className="text-ink/45 text-[10px] tracking-[0.22em]">{k}</div>
                  <div className="mt-2 text-ink text-[13px] tracking-[0.12em]">{v}</div>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* ------------------------------- EVIDENCE ------------------------------- */

function Evidence() {
  const items = [
    { tag: "CALCULATED", line: "Chart positions computed in code.", body: "Every planet, cusp, dasha and sublord is produced from a deterministic ephemeris — not invented, not approximated." },
    { tag: "VERIFIED",   line: "Reference software validation.",    body: "Positions are cross-checked against established astrology software wherever a reference is available." },
    { tag: "EXPLAINED",  line: "Every line shows its placement.",    body: "Each reading sentence names the chart placement that produced it. You can audit the chain end-to-end." },
    { tag: "AI-ASSISTED",line: "AI structures, doesn't invent math.",body: "AI organizes the interpretation and writes it in plain language. It does not generate the underlying chart values." },
    { tag: "HONEST",     line: "Confidence and limits stated.",     body: "Every reading carries a confidence tier and the things that would lower it. We don't hide uncertainty." },
  ];
  return (
    <section id="evidence" className="relative">
      <div className="mx-auto max-w-[1240px] px-6 md:px-10 py-28 md:py-44">
        <Reveal>
          <div className="kicker text-gold">03 · WHAT WE CLAIM, AND WHAT WE DO NOT</div>
        </Reveal>

        <div className="mt-12 grid gap-16 lg:gap-24 lg:grid-cols-[1fr_1.25fr] items-start">
          <Reveal delay={1}>
            <div className="lg:sticky lg:top-24">
              <h2 className="font-serif text-ivory text-[44px] md:text-[64px] leading-[1.02] tracking-[-0.015em]">
                Built for skeptics,
                <br />
                useful to practitioners.
              </h2>
              <p className="mt-8 text-muted-dark text-[15.5px] leading-[1.75] max-w-[440px]">
                We claim the math is exact and the reasoning is auditable. We
                don&apos;t claim to know your future. Trust is earned with evidence,
                not asserted with confidence.
              </p>
              <div className="mt-10 h-px hairline-gold" />
              <div className="mt-6 kicker text-gold-bright">FIVE LINES, PLAINLY STATED</div>
            </div>
          </Reveal>

          <Reveal delay={2}>
            <div>
              {items.map((e) => (
                <div key={e.tag} className="juno-row-dark">
                  <div className="kicker text-gold-bright pt-1">{e.tag}</div>
                  <div>
                    <div className="font-serif text-ivory text-[22px] md:text-[26px] leading-[1.25]">
                      {e.line}
                    </div>
                    <p className="mt-3 text-muted-dark text-[14px] leading-[1.65] max-w-[480px]">
                      {e.body}
                    </p>
                  </div>
                  <div className="kicker text-muted-dark opacity-60 pt-2 hidden md:block">·</div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}

/* -------------------------------- AI ROLE ------------------------------- */

function AIRole() {
  const rows = [
    { side: "AI does", v: "Structures the reading in plain language.", c: "var(--ivory)" },
    { side: "AI does", v: "Names the placement behind each line.", c: "var(--ivory)" },
    { side: "AI does", v: "States a confidence tier and what would change it.", c: "var(--ivory)" },
    { side: "AI does NOT", v: "Generate or estimate chart positions.", c: "var(--clay)" },
    { side: "AI does NOT", v: "Promise outcomes, dates, or health predictions.", c: "var(--clay)" },
    { side: "AI does NOT", v: "Hide where the reasoning is weak.", c: "var(--clay)" },
  ];
  return (
    <section id="ai-role" className="relative">
      <div className="mx-auto max-w-[1240px] px-6 md:px-10 py-28 md:py-40">
        <div className="grid gap-16 lg:gap-24 lg:grid-cols-[1fr_1.15fr] items-start">
          <Reveal>
            <div className="kicker text-gold">02·5 · WHAT THE AI ACTUALLY DOES</div>
            <h2 className="mt-8 font-serif text-ivory text-[40px] md:text-[58px] leading-[1.05] tracking-[-0.015em]">
              AI-powered,
              <br />
              but never AI-fabricated.
            </h2>
            <p className="mt-8 text-muted-dark text-[15.5px] leading-[1.75] max-w-[460px]">
              The chart math is computed deterministically in code. The AI&apos;s
              job is to read that data, explain it, and tell you how confident
              the reasoning is. The numbers are never improvised.
            </p>
          </Reveal>

          <Reveal delay={2}>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {rows.map((r, i) => (
                <div
                  key={i}
                  className="group p-5 transition-all duration-500"
                  style={{
                    border: "1px solid rgba(199,154,78,0.18)",
                    background: "rgba(20,38,58,0.35)",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.borderColor = "rgba(226,192,121,0.6)";
                    (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.borderColor = "rgba(199,154,78,0.18)";
                    (e.currentTarget as HTMLElement).style.transform = "translateY(0)";
                  }}
                >
                  <div className="kicker" style={{ color: r.c }}>{r.side}</div>
                  <div className="mt-3 font-serif text-ivory text-[18px] leading-[1.3]">
                    {r.v}
                  </div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}

/* -------------------------------- READING ------------------------------- */

function ReadingSection() {
  return (
    <section id="reading" className="bg-ivory text-ink">
      <div className="mx-auto max-w-[1240px] px-6 md:px-10 py-28 md:py-40">
        <Reveal>
          <div className="kicker" style={{ color: "var(--gold)" }}>
            04 · SEE A READING, WITH ITS LOGIC
          </div>
        </Reveal>
        <Reveal delay={1}>
          <h2
            className="mt-10 font-serif text-[40px] md:text-[58px] leading-[1.05] max-w-[820px]"
            style={{ color: "var(--ink)" }}
          >
            A reading, explained.
          </h2>
        </Reveal>
        <Reveal delay={2}>
          <div className="mt-16">
            <Reading />
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* ---------------------------------- TRY --------------------------------- */

/* ---------------------------------- FAQ --------------------------------- */

const FAQS = [
  {
    q: "How is JunoPath different from a horoscope app?",
    a: "JunoPath does not generate generic zodiac content. Every reading is built from your exact birth date, time, and location, using computed chart positions, house structure, timing systems, and astrological relationships. The goal is explanation, not entertainment.",
    tag: "POSITIONING",
  },
  {
    q: "What does the AI actually do?",
    a: "The chart itself is calculated mathematically. AI helps organize, explain, and present the reasoning in a way that is easier to understand. AI explains the interpretation. AI does not invent the chart.",
    tag: "AI ROLE",
  },
  {
    q: "Do I need my exact birth time?",
    a: "Birth time significantly improves accuracy because it affects houses, angles, and timing systems. If birth time is unavailable, JunoPath clearly indicates which insights are less reliable rather than pretending certainty.",
    tag: "INPUT",
  },
  {
    q: "How are predictions generated?",
    a: "Predictions are derived from chart placements, significators, timing systems, planetary relationships, and supporting astrological factors. Each prediction is linked to underlying evidence and confidence.",
    tag: "METHOD",
  },
  {
    q: "Can I see why a conclusion was reached?",
    a: "Yes. JunoPath is designed to show supporting placements, reasoning chains, confidence indicators, and explanatory context behind each reading. Transparency is a core product principle.",
    tag: "TRANSPARENCY",
  },
  {
    q: "Does JunoPath guarantee outcomes?",
    a: "No. Astrology provides signals, tendencies, and timing indicators. JunoPath communicates confidence and limitations openly and avoids deterministic claims.",
    tag: "HONESTY",
  },
  {
    q: "Is this for beginners or experienced astrologers?",
    a: "Both. Beginners receive plain-language explanations. Experienced practitioners can explore the underlying astrological reasoning and supporting factors.",
    tag: "AUDIENCE",
  },
  {
    q: "What will I receive after generating a chart?",
    a: "A structured report that may include Birth Chart Foundation, Planet Analysis, Career Intelligence, Relationship Analysis, Dasha Timeline, and Evidence & Confidence.",
    tag: "DELIVERABLE",
  },
];

function FAQ() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <section id="faq" className="relative">
      <div className="mx-auto max-w-[1240px] px-6 md:px-10 py-28 md:py-40">
        <div className="grid gap-16 lg:gap-24 lg:grid-cols-[1fr_1.4fr] items-start">
          <Reveal>
            <div className="lg:sticky lg:top-24">
              <div className="kicker text-gold">04·5 · COMMON QUESTIONS</div>
              <h2 className="mt-8 font-serif text-ivory text-[40px] md:text-[58px] leading-[1.05] tracking-[-0.015em]">
                Questions people ask
                <br />
                before their first reading.
              </h2>
              <p className="mt-8 text-muted-dark text-[15.5px] leading-[1.75] max-w-[440px]">
                JunoPath combines chart computation, astrological logic, and
                AI-assisted explanation. These are the questions we hear most
                often.
              </p>
              <div className="mt-10 h-px hairline-gold" />
              <div className="mt-6 kicker text-gold-bright">
                EIGHT QUESTIONS · ANSWERED PLAINLY
              </div>
            </div>
          </Reveal>

          <Reveal delay={2}>
            <ol className="border-t" style={{ borderColor: "rgba(199,154,78,0.18)" }}>
              {FAQS.map((item, i) => {
                const isOpen = open === i;
                return (
                  <li
                    key={item.q}
                    className="border-b"
                    style={{ borderColor: "rgba(199,154,78,0.18)" }}
                  >
                    <button
                      onClick={() => setOpen(isOpen ? null : i)}
                      aria-expanded={isOpen}
                      className="faq-row w-full text-left grid grid-cols-[44px_1fr_auto] items-baseline gap-5 py-7 md:py-8"
                    >
                      <span className="font-mono text-[12px] tracking-[0.18em] text-gold-bright tabular-nums">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="font-serif text-ivory text-[20px] md:text-[26px] leading-[1.25] tracking-[-0.005em]">
                        {item.q}
                      </span>
                      <span
                        className="font-mono text-[18px] text-gold-bright transition-transform duration-500"
                        style={{ transform: isOpen ? "rotate(45deg)" : "rotate(0deg)" }}
                        aria-hidden
                      >
                        +
                      </span>
                    </button>
                    <div
                      className="grid transition-[grid-template-rows] duration-500 ease-out"
                      style={{ gridTemplateRows: isOpen ? "1fr" : "0fr" }}
                    >
                      <div className="overflow-hidden">
                        <div className="pl-[64px] pr-10 pb-8 grid gap-6 md:grid-cols-[1fr_auto] items-start">
                          <p className="text-muted-dark text-[15px] leading-[1.75] max-w-[620px]">
                            {item.a}
                          </p>
                          <div className="kicker text-gold opacity-80 whitespace-nowrap">
                            {item.tag}
                          </div>
                        </div>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ol>
          </Reveal>
        </div>
      </div>
    </section>
  );
}


function Try() {
  return (
    <section id="try" className="relative">
      <div className="mx-auto max-w-[1100px] px-6 md:px-10 py-40 md:py-56 text-center">
        <Reveal>
          <div className="kicker text-gold">05 · READ YOUR OWN SKY</div>
        </Reveal>
        <Reveal delay={1}>
          <h2 className="mt-10 font-serif text-ivory text-[44px] md:text-[72px] leading-[1.06] tracking-[-0.015em]">
            See your chart, and
            <br className="hidden md:block" /> the reasoning behind every line.
          </h2>
        </Reveal>
        <Reveal delay={2}>
          <div className="mt-14">
            <button className="btn-juno">Generate your chart</button>
          </div>
        </Reveal>
        <Reveal delay={3}>
          <p className="mt-10 kicker text-gold" style={{ opacity: 0.85 }}>
            NO FEAR · NO URGENCY · NO UPSELL · CONFIDENCE AND LIMITS STATED OPENLY
          </p>
        </Reveal>
      </div>
    </section>
  );
}

/* --------------------------------- FOOTER -------------------------------- */

function Footer() {
  return (
    <footer className="relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none flex items-end justify-end opacity-50">
        <svg viewBox="0 0 600 600" className="w-[680px] h-[680px] -mr-32 -mb-40">
          <g className="orbit-spin" style={{ transformOrigin: "300px 300px" }}>
            <circle cx="300" cy="300" r="280" fill="none" stroke="rgba(199,154,78,0.25)" strokeWidth="0.6" />
            <circle cx="300" cy="300" r="220" fill="none" stroke="rgba(199,154,78,0.16)" strokeWidth="0.5" />
            {Array.from({ length: 48 }).map((_, i) => {
              const a = (i * 7.5 * Math.PI) / 180;
              const x1 = 300 + 274 * Math.cos(a);
              const y1 = 300 + 274 * Math.sin(a);
              const x2 = 300 + 280 * Math.cos(a);
              const y2 = 300 + 280 * Math.sin(a);
              return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(199,154,78,0.35)" strokeWidth={i % 6 === 0 ? 0.9 : 0.45} />;
            })}
            <circle cx="580" cy="300" r="4" fill="var(--gold-bright)" />
            <circle cx="300" cy="80" r="2.5" fill="var(--gold)" />
          </g>
          <ellipse cx="300" cy="300" rx="160" ry="40" fill="none" stroke="rgba(199,154,78,0.25)" strokeWidth="0.6" />
          <ellipse cx="300" cy="300" rx="40" ry="160" fill="none" stroke="rgba(199,154,78,0.25)" strokeWidth="0.6" />
          <circle cx="300" cy="300" r="4" fill="var(--gold-bright)" />
        </svg>
      </div>

      <div className="relative mx-auto max-w-[1240px] px-6 md:px-10 pt-24 pb-16">
        <div className="h-px hairline-gold" />
        <div className="pt-16 grid gap-12 md:grid-cols-[1.4fr_1fr] items-end">
          <div>
            <div className="kicker text-gold">A PRECISION INSTRUMENT FOR THE SKY</div>
            <div className="mt-6 font-serif text-ivory text-[80px] md:text-[140px] leading-[0.92] tracking-[-0.03em]">
              JunoPath
            </div>
            <p className="mt-6 max-w-[480px] text-muted-dark text-[14.5px] leading-[1.7]">
              AI-powered astrology, built on precise chart computation.
              Computed placements, structured interpretation, stated confidence.
            </p>
            <div className="mt-8">
              <button className="btn-juno" onClick={() => document.getElementById("try")?.scrollIntoView({ behavior: "smooth" })}>
                Generate your chart
              </button>
            </div>
          </div>
          <nav className="grid grid-cols-2 gap-x-8 gap-y-3 text-[14px] md:justify-self-end">
            {[
              ["Methodology", "#method"],
              ["The reading", "#reading"],
              ["What we claim", "#evidence"],
              ["AI role", "#ai-role"],
              ["Privacy", "#"],
              ["Contact", "#"],
            ].map(([label, href]) => (
              <a
                key={label}
                href={href}
                className="group inline-flex items-center gap-2 text-muted-dark hover:text-gold-bright transition-colors"
              >
                <span className="h-px w-3 bg-current opacity-40 transition-all duration-500 group-hover:w-6 group-hover:opacity-100" />
                <span>{label}</span>
              </a>
            ))}
          </nav>
        </div>

        <div className="mt-20 pt-8 border-t flex flex-col md:flex-row md:items-center md:justify-between gap-4"
          style={{ borderColor: "rgba(199,154,78,0.18)" }}>
          <div className="kicker text-muted-dark">© JUNOPATH · {new Date().getFullYear()} · COMPUTED, NOT GUESSED</div>
          <div className="kicker text-gold opacity-80">KP-NEWCOMB · TRUE NODE · PLACIDUS</div>
        </div>
      </div>
    </footer>
  );
}
