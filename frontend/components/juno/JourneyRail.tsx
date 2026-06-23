"use client";

import { useEffect, useState } from "react";

export const JOURNEY = [
  { id: "hero",     n: "01", caption: "01 — first, what a chart even is" },
  { id: "basics",   n: "02", caption: "02 — what your chart actually is" },
  { id: "method",   n: "03", caption: "03 — how a reading is built" },
  { id: "evidence", n: "04", caption: "04 — what we claim, and what we do not" },
  { id: "reading",  n: "05", caption: "05 — see a reading, with its logic" },
];

export function JourneyRail() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const sections = JOURNEY.map((j) => document.getElementById(j.id));
    const onScroll = () => {
      const y = window.scrollY + window.innerHeight * 0.35;
      let idx = 0;
      sections.forEach((s, i) => {
        if (s && s.offsetTop <= y) idx = i;
      });
      setActive(idx);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, []);

  const go = (id: string) =>
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  const fillPct = JOURNEY.length > 1 ? (active / (JOURNEY.length - 1)) * 100 : 0;

  return (
    <>
      {/* Desktop rail */}
      <aside
        className="hidden xl:block fixed left-4 top-1/2 -translate-y-1/2 z-30 opacity-70 hover:opacity-100 transition-opacity duration-500"
        aria-label="Page sections"
      >
        <div className="relative flex flex-col items-start" style={{ height: 320 }}>
          {/* base line */}
          <div className="absolute left-[7px] top-2 bottom-2 w-px" style={{ backgroundColor: "rgba(199, 154, 78, 0.18)" }} />
          {/* fill */}
          <div
            className="rail-line-fill absolute left-[7px] top-2 w-px"
            style={{ backgroundColor: "var(--gold)", height: `calc(${fillPct}% - 4px)` }}
          />
          {JOURNEY.map((j, i) => (
            <button
              key={j.id}
              onClick={() => go(j.id)}
              className="group relative flex items-center gap-4 py-3"
              style={{ flex: 1 }}
            >
              <span
                className={`rail-node block h-[14px] w-[14px] rounded-full border ${
                  i === active ? "is-active" : i < active ? "is-visited" : ""
                }`}
                style={{
                  backgroundColor: i <= active ? undefined : "var(--navy-deep)",
                  borderColor: i < active ? "var(--gold)" : i === active ? undefined : "rgba(174, 185, 198, 0.35)",
                }}
              />
              <span
                className={`kicker whitespace-nowrap transition-colors ${
                  i === active ? "text-gold-bright" : "text-muted-dark group-hover:text-ivory"
                }`}
              >
                {j.n}
              </span>
              <span
                className={`hidden 2xl:inline text-[11px] whitespace-nowrap transition-opacity ${
                  i === active ? "text-ivory opacity-100" : "opacity-0 group-hover:opacity-70 text-muted-dark"
                }`}
              >
                {j.caption.replace(/^\d+ — /, "")}
              </span>
            </button>
          ))}
        </div>
      </aside>

      {/* Mobile top progress bar */}
      <div className="xl:hidden fixed top-[60px] left-0 right-0 z-40 h-[2px]" style={{ backgroundColor: "rgba(199, 154, 78, 0.15)" }}>
        <div
          className="h-full transition-all duration-500"
          style={{ width: `${fillPct}%`, backgroundColor: "var(--gold)" }}
        />
      </div>
    </>
  );
}