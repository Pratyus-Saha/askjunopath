import { useState } from "react";

export function Reading() {
  const [tab, setTab] = useState<"plain" | "logic">("plain");
  const [openLimits, setOpenLimits] = useState(false);
  return (
    <div
      className="mx-auto max-w-[920px] bg-ivory text-ink p-8 md:p-14 relative"
      style={{ border: "1px solid rgba(20,32,46,0.18)" }}
    >
      {/* Top meta */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="kicker text-gold">
          SAMPLE READING · CAREER · 10TH CUSP
        </div>
        <div className="flex items-center gap-3">
          <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink/55">Confidence</span>
          <span
            className="inline-flex items-center px-2.5 py-0.5 font-mono text-[10.5px] tracking-[0.18em]"
            style={{ border: "1px solid var(--sage)", color: "var(--sage)" }}
          >
            MEDIUM · TIER
          </span>
        </div>
      </div>

      <p
        className="font-serif mt-8 text-[28px] md:text-[36px] leading-[1.22]"
        style={{ color: "var(--ink)" }}
      >
        Career movement is more likely to arrive through people and
        relationships than through credentials alone — with a more active window
        in the second half of the year.
      </p>

      {/* Tabs */}
      <div
        className="mt-10 inline-flex items-stretch"
        style={{ border: "1px solid rgba(20,32,46,0.18)" }}
        role="tablist"
      >
        {([
          ["plain", "Plain language"],
          ["logic", "Astrological logic"],
        ] as const).map(([k, label]) => (
          <button
            key={k}
            role="tab"
            aria-selected={tab === k}
            onClick={() => setTab(k)}
            className="px-5 py-2.5 font-mono text-[11px] tracking-[0.16em] uppercase transition-colors"
            style={{
              background: tab === k ? "var(--ink)" : "transparent",
              color: tab === k ? "var(--ivory)" : "var(--ink)",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab panels */}
      <div className="mt-7 min-h-[210px]">
        {tab === "plain" ? (
          <div className="space-y-5">
            <div>
              <div className="kicker text-ink/55">WHAT IT MEANS</div>
              <p className="mt-2 font-serif text-[19px] leading-[1.6] text-ink">
                Career growth this year is more likely to come through
                relationships, introductions and trusted contacts than through
                applying cold. Lean into people you already know — the timing
                opens up around mid-year.
              </p>
            </div>
            <div>
              <div className="kicker text-ink/55">WHY YOU CAN TRUST THIS LINE</div>
              <p className="mt-2 text-[14.5px] leading-[1.7] text-ink/75">
                Every reading sentence is tied to a placement in your chart.
                Open the <em>Astrological logic</em> tab to see exactly which
                placement produced this statement.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            <div>
              <div className="kicker text-ink/55">PLACEMENT</div>
              <div className="mt-2 font-mono text-[12.5px] tracking-[0.14em] text-ink">
                10TH HOUSE CUSP · SUBLORD VENUS · SIGNIFIES 2, 11
              </div>
            </div>
            <div>
              <div className="kicker text-ink/55">WHY THIS WAS INFERRED</div>
              <p
                className="mt-2 border-l-2 pl-5 font-serif text-[17px] leading-[1.6] text-ink"
                style={{ borderColor: "var(--gold)" }}
              >
                Venus is the sublord of the 10th cusp (career) and also
                signifies the 2nd and 11th houses (income, gain, networks).
                Connection-driven gain therefore dominates the career
                significator. The active Venus–Moon period (dasha) opens the
                window in the second half of the year.
              </p>
            </div>
            <div>
              <div className="kicker text-ink/55">CHAIN</div>
              <div className="mt-2 font-mono text-[11.5px] tracking-[0.16em] text-ink/75">
                10TH CUSP → SUBLORD(VEN) → SIGNIFIES&nbsp;2,&nbsp;11 → DASHA(VEN-MOO)
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Limits expander */}
      <button
        onClick={() => setOpenLimits((o) => !o)}
        className="mt-10 inline-flex items-center gap-2 font-mono text-[11.5px] tracking-[0.16em] uppercase text-ink/70 hover:text-[color:var(--gold)] transition-colors"
        aria-expanded={openLimits}
      >
        <span>{openLimits ? "Hide what could lower this confidence" : "What could lower this confidence"}</span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
          style={{ transform: openLimits ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.4s cubic-bezier(0.22,1,0.36,1)" }}>
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      <div style={{ display: "grid", gridTemplateRows: openLimits ? "1fr" : "0fr", transition: "grid-template-rows 0.5s cubic-bezier(0.22,1,0.36,1)" }}>
        <div style={{ overflow: "hidden" }}>
          <ul className="mt-4 space-y-2 text-[13.5px] leading-[1.7] text-ink/75 list-disc pl-5">
            <li>Inexact birth time would shift the 10th cusp and the sublord chain.</li>
            <li>Competing transits to the 10th lord could narrow or move the window.</li>
            <li>This is one of several active significators — not the only signal.</li>
          </ul>
        </div>
      </div>

      <div className="mt-10 h-px hairline-gold" />

      <p className="mt-6 text-[13px] leading-[1.6] text-ink/65">
        This is a sample of the format, not your reading. A reading is a
        structured way to think — not a forecast of fixed events. We state our
        confidence, show our reasoning, and we may be wrong.
      </p>
    </div>
  );
}