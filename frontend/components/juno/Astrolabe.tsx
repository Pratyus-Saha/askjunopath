"use client";

import { useEffect, useState } from "react";

/**
 * Subtle astrolabe / orbital ring backdrop for the hero.
 * Pure SVG, slow rotation, parallax on scroll. Restrained gold strokes.
 */
export function Astrolabe() {
  const [y, setY] = useState(0);
  useEffect(() => {
    const onScroll = () => setY(window.scrollY);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const SIGNS = ["ARI", "TAU", "GEM", "CAN", "LEO", "VIR", "LIB", "SCO", "SAG", "CAP", "AQU", "PIS"];

  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 flex items-center justify-center overflow-hidden"
      style={{ transform: `translateY(${y * -0.08}px)` }}
    >
      <svg
        viewBox="0 0 1000 1000"
        className="w-[140vmin] h-[140vmin] max-w-none opacity-[0.55]"
        style={{ minWidth: 900 }}
      >
        <defs>
          <radialGradient id="astroGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(226,192,121,0.10)" />
            <stop offset="55%" stopColor="rgba(226,192,121,0.03)" />
            <stop offset="100%" stopColor="rgba(226,192,121,0)" />
          </radialGradient>
        </defs>

        <circle cx="500" cy="500" r="480" fill="url(#astroGlow)" />

        {/* outermost slow ring */}
        <g style={{ transformOrigin: "500px 500px", animation: "ring-rotate 480s linear infinite" }}>
          <circle cx="500" cy="500" r="470" fill="none" stroke="rgba(199,154,78,0.32)" strokeWidth="0.6" />
          <circle cx="500" cy="500" r="462" fill="none" stroke="rgba(199,154,78,0.18)" strokeWidth="0.4" />
          {Array.from({ length: 72 }).map((_, i) => {
            const a = (i * 5 * Math.PI) / 180;
            const x1 = 500 + 462 * Math.cos(a);
            const y1 = 500 + 462 * Math.sin(a);
            const x2 = 500 + 470 * Math.cos(a);
            const y2 = 500 + 470 * Math.sin(a);
            return (
              <line
                key={i}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke="rgba(199,154,78,0.45)"
                strokeWidth={i % 6 === 0 ? 1 : 0.5}
              />
            );
          })}
        </g>

        {/* sign labels ring — counter-rotating very slowly */}
        <g style={{ transformOrigin: "500px 500px", animation: "ring-rotate-rev 720s linear infinite" }}>
          <circle cx="500" cy="500" r="430" fill="none" stroke="rgba(199,154,78,0.22)" strokeWidth="0.5" />
          {SIGNS.map((s, i) => {
            const a = ((i * 30 + 15) * Math.PI) / 180;
            const x = 500 + 446 * Math.cos(a);
            const y = 500 + 446 * Math.sin(a);
            return (
              <text
                key={s}
                x={x}
                y={y}
                fill="rgba(226,192,121,0.55)"
                fontFamily="DM Mono, monospace"
                fontSize="13"
                textAnchor="middle"
                dominantBaseline="middle"
                letterSpacing="0.18em"
              >
                {s}
              </text>
            );
          })}
          {Array.from({ length: 12 }).map((_, i) => {
            const a = (i * 30 * Math.PI) / 180;
            const x1 = 500 + 430 * Math.cos(a);
            const y1 = 500 + 430 * Math.sin(a);
            const x2 = 500 + 462 * Math.cos(a);
            const y2 = 500 + 462 * Math.sin(a);
            return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(199,154,78,0.35)" strokeWidth="0.6" />;
          })}
        </g>

        {/* mid ring */}
        <g style={{ transformOrigin: "500px 500px", animation: "ring-rotate 360s linear infinite" }}>
          <circle cx="500" cy="500" r="360" fill="none" stroke="rgba(199,154,78,0.20)" strokeWidth="0.5" />
          <circle cx="500" cy="500" r="300" fill="none" stroke="rgba(199,154,78,0.14)" strokeWidth="0.4" />
          {Array.from({ length: 36 }).map((_, i) => {
            const a = (i * 10 * Math.PI) / 180;
            const x1 = 500 + 300 * Math.cos(a);
            const y1 = 500 + 300 * Math.sin(a);
            const x2 = 500 + 360 * Math.cos(a);
            const y2 = 500 + 360 * Math.sin(a);
            return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(199,154,78,0.16)" strokeWidth="0.4" />;
          })}
        </g>

        {/* inner armillary cross */}
        <g stroke="rgba(199,154,78,0.30)" strokeWidth="0.6" fill="none">
          <ellipse cx="500" cy="500" rx="220" ry="60" />
          <ellipse cx="500" cy="500" rx="60" ry="220" />
          <circle cx="500" cy="500" r="220" />
          <circle cx="500" cy="500" r="6" fill="rgba(226,192,121,0.65)" stroke="none" />
        </g>
      </svg>
    </div>
  );
}