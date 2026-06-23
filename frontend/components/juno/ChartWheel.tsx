"use client";

import { useMemo, useState } from "react";

const SIGNS = ["ARI", "TAU", "GEM", "CAN", "LEO", "VIR", "LIB", "SCO", "SAG", "CAP", "AQU", "PIS"];
const SIGN_LABELS = ["Ari","Tau","Gem","Can","Leo","Vir","Lib","Sco","Sag","Cap","Aqu","Pis"];
// Append U+FE0E (text variation selector) to force monochrome text rendering
// instead of the colored emoji fallback that ships on some systems.
const SIGN_GLYPHS = ["♈\uFE0E","♉\uFE0E","♊\uFE0E","♋\uFE0E","♌\uFE0E","♍\uFE0E","♎\uFE0E","♏\uFE0E","♐\uFE0E","♑\uFE0E","♒\uFE0E","♓\uFE0E"];
const FULL_SIGNS = ["ARIES","TAURUS","GEMINI","CANCER","LEO","VIRGO","LIBRA","SCORPIO","SAGITTARIUS","CAPRICORN","AQUARIUS","PISCES"];
const SIGN_PROPER = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"];
const ELEMENT_NAMES = ["Fire","Earth","Air","Water"];
const ELEMENT_OF = [0,1,2,3,0,1,2,3,0,1,2,3];
// 0=Cardinal,1=Fixed,2=Mutable
const MODALITY_NAMES = ["Cardinal","Fixed","Mutable"];
const MODALITY_OF = [0,1,2,0,1,2,0,1,2,0,1,2];

const ASC_LON = 180 + 27 + 18 / 60; // Libra 27°18'

type Planet = {
  key: string;
  glyph: string;
  label: string;
  name: string;
  signIdx: number;
  deg: number;
  min: number;
  house: number;
};

export const PLANETS: Planet[] = [
  { key: "asc", glyph: "Asc", label: "ASC", name: "Ascendant", signIdx: 6,  deg: 27, min: 18, house: 1 },
  { key: "sun", glyph: "☉",   label: "SUN", name: "Sun",       signIdx: 0,  deg: 2,  min: 41, house: 7 },
  { key: "moo", glyph: "☽",   label: "MOO", name: "Moon",      signIdx: 1,  deg: 18, min: 24, house: 8 },
  { key: "mer", glyph: "☿",   label: "MER", name: "Mercury",   signIdx: 11, deg: 9,  min: 57, house: 6 },
  { key: "ven", glyph: "♀",   label: "VEN", name: "Venus",     signIdx: 10, deg: 14, min: 6 , house: 5 },
  { key: "mar", glyph: "♂",   label: "MAR", name: "Mars",      signIdx: 3,  deg: 5,  min: 33, house: 10 },
  { key: "jup", glyph: "♃",   label: "JUP", name: "Jupiter",   signIdx: 5,  deg: 11, min: 12, house: 12 },
  { key: "sat", glyph: "♄",   label: "SAT", name: "Saturn",    signIdx: 8,  deg: 9,  min: 48, house: 3 },
];

const lonOf = (p: Planet) => p.signIdx * 30 + p.deg + p.min / 60;

type Aspect = { name: string; angle: number; orb: number; color: string; dash?: string };
const ASPECTS: Aspect[] = [
  { name: "Conjunction", angle: 0,   orb: 7, color: "rgba(226,192,121,0.85)" },
  { name: "Opposition",  angle: 180, orb: 7, color: "rgba(226,192,121,0.75)" },
  { name: "Trine",       angle: 120, orb: 6, color: "rgba(111,138,114,0.7)"  },
  { name: "Square",      angle: 90,  orb: 6, color: "rgba(178,106,76,0.7)", dash: "3 3" },
  { name: "Sextile",     angle: 60,  orb: 4, color: "rgba(244,236,221,0.55)", dash: "2 4" },
];

function aspectBetween(a: Planet, b: Planet): Aspect | null {
  let d = Math.abs(lonOf(a) - lonOf(b)) % 360;
  if (d > 180) d = 360 - d;
  for (const A of ASPECTS) {
    if (Math.abs(d - A.angle) <= A.orb) return A;
  }
  return null;
}

// Map ecliptic longitude → screen angle (degrees, math convention, 0 = +x, CCW positive).
// ASC sits at screen 180° (9 o'clock).
const screenAngleDeg = (lon: number) => (180 - (lon - ASC_LON) + 720) % 360;

const polar = (cx: number, cy: number, r: number, deg: number) => {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy - r * Math.sin(rad) };
};

type Props = {
  size?: number;
  showTable?: boolean;
  buildSequence?: boolean; // for the method section mini wheel
  step?: number;
  compact?: boolean; // hide center hub for tiny render
};

export function ChartWheel({ size = 560, showTable = true, buildSequence = false, step = 99, compact = false }: Props) {
  const [hover, setHover] = useState<string | null>(null);
  const [signHover, setSignHover] = useState<number | null>(null);
  const cx = size / 2;
  const cy = size / 2;
  // Multi-layer geometry
  const rZodiacOuter = size * 0.485;     // outer edge
  const rZodiacInner = size * 0.415;     // inner edge of sign band
  const rDegOuter    = size * 0.413;
  const rDegInner    = size * 0.378;     // degree-tick band
  const rHouseEdge   = size * 0.376;     // outer edge of house band
  const rHouseInner  = size * 0.255;     // inner edge of house band
  const rPlanet      = size * 0.225;     // planet badge orbit
  const rHub         = size * 0.165;     // center intelligence hub

  // House cusps every 30° starting at ASC (screen 180°), going CCW.
  const houseCusps = useMemo(
    () => Array.from({ length: 12 }, (_, i) => (180 + i * 30) % 360),
    [],
  );

  // Sign sectors mapped from ecliptic longitudes via screenAngleDeg
  const signSectors = useMemo(
    () =>
      SIGNS.map((label, i) => {
        const startLon = i * 30;
        const midLon = startLon + 15;
        return {
          label,
          startAngle: screenAngleDeg(startLon),
          midAngle: screenAngleDeg(midLon),
        };
      }),
    [],
  );

  const planetsOnWheel = PLANETS.filter((p) => p.key !== "asc");
  const ascPlanet = PLANETS[0];
  const ascAngle = screenAngleDeg(lonOf(ascPlanet));

  // Aspects originating from the hovered planet
  const activeAspects = useMemo(() => {
    if (!hover || hover === "asc") return [] as { a: Planet; b: Planet; asp: Aspect }[];
    const a = PLANETS.find((p) => p.key === hover);
    if (!a) return [];
    const out: { a: Planet; b: Planet; asp: Aspect }[] = [];
    for (const b of planetsOnWheel) {
      if (b.key === a.key) continue;
      const asp = aspectBetween(a, b);
      if (asp) out.push({ a, b, asp });
    }
    return out;
  }, [hover, planetsOnWheel]);

  const hoveredPlanet = hover ? PLANETS.find((p) => p.key === hover) ?? null : null;
  const hoveredSign = signHover !== null ? signHover : null;

  return (
    <div className={`grid gap-10 ${showTable ? "md:grid-cols-[1.4fr_1fr]" : ""} items-center`}>
      {/* WHEEL */}
      <div className="relative w-full chart-instrument">
        <svg
          viewBox={`0 0 ${size} ${size}`}
          className="w-full h-auto block"
          role="img"
          aria-label="Birth chart wheel"
        >
          <defs>
            <radialGradient id="wheelGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="rgba(226, 192, 121, 0.14)" />
              <stop offset="60%" stopColor="rgba(226, 192, 121, 0.04)" />
              <stop offset="100%" stopColor="rgba(226, 192, 121, 0)" />
            </radialGradient>
            <radialGradient id="hubGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="rgba(226,192,121,0.22)" />
              <stop offset="55%" stopColor="rgba(226,192,121,0.06)" />
              <stop offset="100%" stopColor="rgba(226,192,121,0)" />
            </radialGradient>
            <radialGradient id="signBand" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="rgba(20,38,58,0)" />
              <stop offset="80%" stopColor="rgba(20,38,58,0.55)" />
              <stop offset="100%" stopColor="rgba(8,19,31,0.85)" />
            </radialGradient>
          </defs>

          {/* Ambient glow */}
          <circle cx={cx} cy={cy} r={size * 0.49} fill="url(#wheelGlow)" />

          {/* Outer decorative rotating tick ring */}
          <g className="ring-rotate" style={{ transformOrigin: `${cx}px ${cy}px` }}>
            <circle cx={cx} cy={cy} r={rZodiacOuter + 10} fill="none" stroke="rgba(199,154,78,0.18)" strokeWidth={0.6} />
            {Array.from({ length: 72 }).map((_, i) => {
              const a = (i * 5 * Math.PI) / 180;
              const x1 = cx + (rZodiacOuter + 5) * Math.cos(a);
              const y1 = cy - (rZodiacOuter + 5) * Math.sin(a);
              const x2 = cx + (rZodiacOuter + 12) * Math.cos(a);
              const y2 = cy - (rZodiacOuter + 12) * Math.sin(a);
              return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(199,154,78,0.3)" strokeWidth={i % 6 === 0 ? 0.9 : 0.45} />;
            })}
          </g>

          {/* Cardinal cross markers (N/E/S/W ecliptic) */}
          {[0, 90, 180, 270].map((a) => {
            const p1 = polar(cx, cy, rZodiacOuter + 14, a);
            const p2 = polar(cx, cy, rZodiacOuter + 20, a);
            return <line key={a} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="var(--gold-bright)" strokeWidth={1.1} />;
          })}

          {/* LAYER 1 — Zodiac band */}
          <circle cx={cx} cy={cy} r={rZodiacOuter} fill="url(#signBand)" />
          <circle className="wheel-draw" cx={cx} cy={cy} r={rZodiacOuter} fill="none" stroke="rgba(199,154,78,0.55)" strokeWidth={1} />
          <circle cx={cx} cy={cy} r={rZodiacInner} fill="none" stroke="rgba(199,154,78,0.4)" strokeWidth={0.8} />
          {signSectors.map((s, i) => {
            const a = (s.startAngle * Math.PI) / 180;
            const p1 = { x: cx + rZodiacInner * Math.cos(a), y: cy - rZodiacInner * Math.sin(a) };
            const p2 = { x: cx + rZodiacOuter * Math.cos(a), y: cy - rZodiacOuter * Math.sin(a) };
            return <line key={i} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="rgba(199,154,78,0.42)" strokeWidth={0.7} />;
          })}
          {signSectors.map((s, i) => {
            const rGlyphR = rZodiacOuter - (rZodiacOuter - rZodiacInner) * 0.36;
            const rLabelR = rZodiacInner + (rZodiacOuter - rZodiacInner) * 0.22;
            const pg = polar(cx, cy, rGlyphR, s.midAngle);
            const pl = polar(cx, cy, rLabelR, s.midAngle);
            const active = signHover === i;
            const dim = signHover !== null && !active;
            return (
              <g
                key={s.label}
                onMouseEnter={() => setSignHover(i)}
                onMouseLeave={() => setSignHover(null)}
                style={{ cursor: "pointer", opacity: dim ? 0.4 : 1, transition: "opacity 0.25s ease" }}
              >
                {/* engraved shadow for emboss feel */}
                <text x={pg.x} y={pg.y + 0.7}
                  fill="rgba(8,19,31,0.9)"
                  fontFamily='"Cormorant Garamond", "Apple Symbols", "Segoe UI Symbol", "Noto Sans Symbols2", serif'
                  fontSize={size * 0.038}
                  textAnchor="middle" dominantBaseline="middle">
                  {SIGN_GLYPHS[i]}
                </text>
                <text x={pg.x} y={pg.y}
                  fill={active ? "var(--gold-bright)" : "rgba(199,154,78,0.78)"}
                  fontFamily='"Cormorant Garamond", "Apple Symbols", "Segoe UI Symbol", "Noto Sans Symbols2", serif'
                  fontSize={size * 0.038}
                  textAnchor="middle" dominantBaseline="middle"
                  style={{ transition: "fill 0.25s ease" }}>
                  {SIGN_GLYPHS[i]}
                </text>
                <text x={pl.x} y={pl.y}
                  fill={active ? "var(--ivory-soft)" : "rgba(244,236,221,0.55)"}
                  fontFamily='"Cormorant Garamond", Georgia, serif'
                  fontSize={size * 0.019}
                  textAnchor="middle" dominantBaseline="middle"
                  letterSpacing="0.22em"
                  fontStyle="italic"
                  style={{ transition: "fill 0.25s ease" }}>
                  {SIGN_LABELS[i]}
                </text>
                {/* invisible hit area covering the sign sector */}
                <circle cx={pg.x} cy={pg.y} r={size * 0.05} fill="transparent" />
              </g>
            );
          })}

          {/* LAYER 2 — Degree band */}
          <circle cx={cx} cy={cy} r={rDegOuter} fill="none" stroke="rgba(199,154,78,0.22)" strokeWidth={0.6} />
          <circle cx={cx} cy={cy} r={rDegInner} fill="none" stroke="rgba(199,154,78,0.22)" strokeWidth={0.6} />
          {Array.from({ length: 360 }).map((_, d) => {
            const a = (d * Math.PI) / 180;
            const long = (180 - d + ASC_LON + 720) % 360; // for opacity by cardinal
            const isCardinal = long % 30 === 0;
            const inner = d % 10 === 0 ? rDegInner : d % 5 === 0 ? rDegInner + 3 : rDegInner + 5;
            const outer = rDegOuter;
            const x1 = cx + inner * Math.cos(a);
            const y1 = cy - inner * Math.sin(a);
            const x2 = cx + outer * Math.cos(a);
            const y2 = cy - outer * Math.sin(a);
            const op = isCardinal ? 0.7 : d % 10 === 0 ? 0.45 : d % 5 === 0 ? 0.28 : 0.14;
            return <line key={d} x1={x1} y1={y1} x2={x2} y2={y2} stroke={`rgba(199,154,78,${op})`} strokeWidth={0.5} />;
          })}

          {/* LAYER 3 — House band */}
          <circle cx={cx} cy={cy} r={rHouseEdge} fill="rgba(20,38,58,0.25)" stroke="rgba(199,154,78,0.32)" strokeWidth={0.7} />
          <circle cx={cx} cy={cy} r={rHouseInner} fill="none" stroke="rgba(199,154,78,0.3)" strokeWidth={0.7} />
          {houseCusps.map((deg, i) => {
            const a = (deg * Math.PI) / 180;
            const p1 = { x: cx + rHouseInner * Math.cos(a), y: cy - rHouseInner * Math.sin(a) };
            const p2 = { x: cx + rHouseEdge * Math.cos(a), y: cy - rHouseEdge * Math.sin(a) };
            const isAxis = i % 3 === 0;
            return (
              <line key={i} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                stroke={isAxis ? "rgba(226,192,121,0.65)" : "rgba(199,154,78,0.28)"}
                strokeWidth={isAxis ? 0.9 : 0.5} />
            );
          })}
          {houseCusps.map((deg, i) => {
            const mid = (deg + 15) % 360;
            const p = polar(cx, cy, (rHouseEdge + rHouseInner) / 2, mid);
            return (
              <text key={i} x={p.x} y={p.y}
                fill="rgba(174,185,198,0.7)" fontFamily="DM Mono, monospace"
                fontSize={size * 0.018} textAnchor="middle" dominantBaseline="middle"
                letterSpacing="0.08em">
                {String(i + 1).padStart(2, "0")}
              </text>
            );
          })}

          {/* ASPECT LINES (only when a planet is hovered) */}
          <g pointerEvents="none">
            {activeAspects.map(({ a, b, asp }, idx) => {
              const p1 = polar(cx, cy, rHub + 2, screenAngleDeg(lonOf(a)));
              const p2 = polar(cx, cy, rHub + 2, screenAngleDeg(lonOf(b)));
              return (
                <line key={idx} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
                  stroke={asp.color} strokeWidth={0.9}
                  strokeDasharray={asp.dash} className="aspect-line" />
              );
            })}
          </g>

          {/* ASCENDANT EMPHASIS — gold horizon line + arrow */}
          <g>
            {(() => {
              const a = (ascAngle * Math.PI) / 180;
              const inP = polar(cx, cy, rHub - 4, ascAngle);
              const outP = polar(cx, cy, rZodiacOuter + 22, ascAngle);
              const arrowBase = polar(cx, cy, rZodiacOuter + 16, ascAngle);
              const labelP = polar(cx, cy, rZodiacOuter + 34, ascAngle);
              // arrow head
              const ah1 = polar(cx, cy, rZodiacOuter + 22, ascAngle + 2);
              const ah2 = polar(cx, cy, rZodiacOuter + 22, ascAngle - 2);
              return (
                <>
                  <line x1={inP.x} y1={inP.y} x2={outP.x} y2={outP.y}
                    stroke="var(--gold-bright)" strokeWidth={1.3} className="asc-line" />
                  <polyline
                    points={`${ah1.x},${ah1.y} ${outP.x},${outP.y} ${ah2.x},${ah2.y}`}
                    fill="none" stroke="var(--gold-bright)" strokeWidth={1.3}
                    strokeLinecap="round" strokeLinejoin="round"
                  />
                  <circle cx={arrowBase.x} cy={arrowBase.y} r={1.8} fill="var(--gold-bright)" />
                  <g>
                    <rect
                      x={labelP.x - size * 0.05}
                      y={labelP.y - size * 0.018}
                      width={size * 0.1}
                      height={size * 0.036}
                      fill="rgba(8,19,31,0.85)"
                      stroke="var(--gold-bright)"
                      strokeWidth={0.8}
                      rx={1}
                    />
                    <text x={labelP.x} y={labelP.y + 0.5}
                      fill="var(--gold-bright)" fontFamily="DM Mono, monospace"
                      fontSize={size * 0.018} textAnchor="middle" dominantBaseline="middle"
                      letterSpacing="0.18em">
                      ASC · 27°18′
                    </text>
                  </g>
                </>
              );
            })()}
          </g>

          {/* LAYER 4 — Planet badges */}
          {planetsOnWheel.map((p, i) => {
            if (buildSequence && i >= step) return null;
            const ang = screenAngleDeg(lonOf(p));
            const pos = polar(cx, cy, rPlanet, ang);
            const tick1 = polar(cx, cy, rHouseInner + 2, ang);
            const tick2 = polar(cx, cy, rHouseInner + 10, ang);
            const active = hover === p.key;
            const dim = hover !== null && !active;
            const badgeR = size * 0.032;
            return (
              <g
                key={p.key}
                className={`wheel-glyph planet-badge ${active ? "is-active" : ""} ${dim ? "is-dim" : ""}`}
                onMouseEnter={() => setHover(p.key)}
                onMouseLeave={() => setHover(null)}
                style={{ cursor: "pointer" }}
              >
                {/* connector tick to house band */}
                <line x1={tick1.x} y1={tick1.y} x2={tick2.x} y2={tick2.y}
                  stroke="rgba(226,192,121,0.55)" strokeWidth={0.8} />
                {/* outer glow ring */}
                <circle cx={pos.x} cy={pos.y} r={badgeR + 3}
                  fill="none" stroke="rgba(226,192,121,0.18)" strokeWidth={0.7}
                  className="planet-halo" />
                {/* badge */}
                <circle cx={pos.x} cy={pos.y} r={badgeR}
                  fill="var(--navy-deep)" stroke="rgba(226,192,121,0.7)" strokeWidth={1} />
                <text x={pos.x} y={pos.y + 0.5}
                  fill="var(--ivory-soft)" fontFamily="DM Mono, monospace"
                  fontSize={size * 0.032} textAnchor="middle" dominantBaseline="middle">
                  {p.glyph}
                </text>
                {/* hit area */}
                <circle cx={pos.x} cy={pos.y} r={badgeR + 8} fill="transparent" />
              </g>
            );
          })}

          {/* CENTER — Intelligence hub */}
          {!compact && (
            <g className="hub" pointerEvents="none">
              <circle cx={cx} cy={cy} r={rHub + 18} fill="url(#hubGlow)" />
              <circle cx={cx} cy={cy} r={rHub} fill="rgba(8,19,31,0.85)"
                stroke="rgba(226,192,121,0.45)" strokeWidth={0.8} />
              <circle cx={cx} cy={cy} r={rHub - 4} fill="none"
                stroke="rgba(199,154,78,0.18)" strokeWidth={0.5} />

              {/* Hub content: either summary or hovered planet detail */}
              {hoveredSign !== null ? (
                <>
                  <text x={cx} y={cy - rHub * 0.6} fill="var(--gold-bright)"
                    fontFamily="DM Mono, monospace" fontSize={size * 0.017}
                    textAnchor="middle" letterSpacing="0.24em">
                    ZODIAC SIGN
                  </text>
                  <line x1={cx - rHub * 0.55} y1={cy - rHub * 0.42}
                    x2={cx + rHub * 0.55} y2={cy - rHub * 0.42}
                    stroke="rgba(199,154,78,0.35)" strokeWidth={0.5} />
                  <text x={cx} y={cy - rHub * 0.12} fill="var(--ivory-soft)"
                    fontFamily="Cormorant Garamond, serif" fontSize={size * 0.062}
                    textAnchor="middle" dominantBaseline="middle" fontStyle="italic">
                    {SIGN_PROPER[hoveredSign]}
                  </text>
                  <line x1={cx - rHub * 0.4} y1={cy + rHub * 0.12}
                    x2={cx + rHub * 0.4} y2={cy + rHub * 0.12}
                    stroke="rgba(199,154,78,0.22)" strokeWidth={0.5} />
                  <text x={cx - rHub * 0.34} y={cy + rHub * 0.34} fill="rgba(174,185,198,0.7)"
                    fontFamily="DM Mono, monospace" fontSize={size * 0.0135}
                    textAnchor="middle" letterSpacing="0.18em">
                    ELEMENT
                  </text>
                  <text x={cx - rHub * 0.34} y={cy + rHub * 0.52} fill="var(--gold-bright)"
                    fontFamily="DM Mono, monospace" fontSize={size * 0.018}
                    textAnchor="middle" letterSpacing="0.1em">
                    {ELEMENT_NAMES[ELEMENT_OF[hoveredSign]].toUpperCase()}
                  </text>
                  <text x={cx + rHub * 0.34} y={cy + rHub * 0.34} fill="rgba(174,185,198,0.7)"
                    fontFamily="DM Mono, monospace" fontSize={size * 0.0135}
                    textAnchor="middle" letterSpacing="0.18em">
                    MODALITY
                  </text>
                  <text x={cx + rHub * 0.34} y={cy + rHub * 0.52} fill="var(--gold-bright)"
                    fontFamily="DM Mono, monospace" fontSize={size * 0.018}
                    textAnchor="middle" letterSpacing="0.1em">
                    {MODALITY_NAMES[MODALITY_OF[hoveredSign]].toUpperCase()}
                  </text>
                </>
              ) : hoveredPlanet ? (
                <>
                  <text x={cx} y={cy - rHub * 0.55} fill="var(--gold-bright)"
                    fontFamily="DM Mono, monospace" fontSize={size * 0.018}
                    textAnchor="middle" letterSpacing="0.22em">
                    {hoveredPlanet.label} · HOUSE {String(hoveredPlanet.house).padStart(2, "0")}
                  </text>
                  <text x={cx} y={cy - rHub * 0.18} fill="var(--ivory-soft)"
                    fontFamily="Cormorant Garamond, serif" fontSize={size * 0.06}
                    textAnchor="middle" dominantBaseline="middle">
                    {hoveredPlanet.name}
                  </text>
                  <text x={cx} y={cy + rHub * 0.22} fill="var(--ivory)"
                    fontFamily="DM Mono, monospace" fontSize={size * 0.022}
                    textAnchor="middle" letterSpacing="0.18em">
                    {FULL_SIGNS[hoveredPlanet.signIdx]}
                  </text>
                  <text x={cx} y={cy + rHub * 0.5} fill="var(--gold-bright)"
                    fontFamily="DM Mono, monospace" fontSize={size * 0.026}
                    textAnchor="middle" letterSpacing="0.1em">
                    {String(hoveredPlanet.deg).padStart(2, "0")}° {String(hoveredPlanet.min).padStart(2, "0")}′
                  </text>
                </>
              ) : (
                <>
                  <text x={cx} y={cy - rHub * 0.62} fill="var(--gold-bright)"
                    fontFamily="DM Mono, monospace" fontSize={size * 0.017}
                    textAnchor="middle" letterSpacing="0.24em">
                    CHART SUMMARY
                  </text>
                  <line x1={cx - rHub * 0.55} y1={cy - rHub * 0.45}
                    x2={cx + rHub * 0.55} y2={cy - rHub * 0.45}
                    stroke="rgba(199,154,78,0.35)" strokeWidth={0.5} />
                  <text x={cx} y={cy - rHub * 0.22} fill="var(--ivory-soft)"
                    fontFamily="Cormorant Garamond, serif" fontSize={size * 0.054}
                    textAnchor="middle" dominantBaseline="middle" fontStyle="italic">
                    Libra Ascendant
                  </text>
                  <text x={cx} y={cy + rHub * 0.05} fill="var(--gold-bright)"
                    fontFamily="DM Mono, monospace" fontSize={size * 0.022}
                    textAnchor="middle" letterSpacing="0.16em">
                    27°18′
                  </text>
                  <line x1={cx - rHub * 0.55} y1={cy + rHub * 0.22}
                    x2={cx + rHub * 0.55} y2={cy + rHub * 0.22}
                    stroke="rgba(199,154,78,0.25)" strokeWidth={0.5} />
                  {/* Stat grid */}
                  {([
                    ["MOON", "TAURUS"],
                    ["DASHA", "VEN / SUN"],
                    ["ELEMENT", "AIR"],
                    ["AI", "READY"],
                  ] as const).map(([k, v], i) => {
                    const col = i % 2;
                    const row = Math.floor(i / 2);
                    const x = cx + (col === 0 ? -rHub * 0.42 : rHub * 0.42);
                    const y = cy + rHub * 0.38 + row * (size * 0.032);
                    return (
                      <g key={k}>
                        <text x={x} y={y} fill="rgba(174,185,198,0.7)"
                          fontFamily="DM Mono, monospace" fontSize={size * 0.0135}
                          textAnchor="middle" letterSpacing="0.18em">
                          {k}
                        </text>
                        <text x={x} y={y + size * 0.018} fill="var(--ivory)"
                          fontFamily="DM Mono, monospace" fontSize={size * 0.016}
                          textAnchor="middle" letterSpacing="0.1em">
                          {v}
                        </text>
                      </g>
                    );
                  })}
                </>
              )}
              {/* live pulse dot */}
              <circle cx={cx} cy={cy + rHub - 6} r={size * 0.006}
                fill="var(--gold-bright)" className="hub-pulse" />
            </g>
          )}
        </svg>
      </div>

      {/* TABLE */}
      {showTable && (
        <div className="font-mono text-[13px] tracking-wider">
          <div className="kicker text-gold mb-4">POSITIONS · COMPUTED</div>
          <div className="space-y-3 border-l border-gold-soft pl-5">
            {PLANETS.map((p) => {
              const active = hover === p.key;
              const dim = hover !== null && !active;
              return (
                <button
                  key={p.key}
                  onMouseEnter={() => setHover(p.key)}
                  onMouseLeave={() => setHover(null)}
                  className={`pos-row flex w-full items-baseline justify-between gap-6 py-1 text-left ${
                    active ? "is-active" : ""
                  } ${dim ? "is-dim" : ""}`}
                  style={{ color: "inherit" }}
                >
                  <span className="text-ivory-warm w-12">{p.label}</span>
                  <span className="text-muted-dark flex-1">
                    {fullSign(p.signIdx)}
                  </span>
                  <span className="text-ivory-warm tabular-nums">
                    {String(p.deg).padStart(2, "0")}° {String(p.min).padStart(2, "0")}′
                  </span>
                </button>
              );
            })}
          </div>
          <div className="mt-6 kicker text-muted-dark">
            HOVER A ROW · GLYPH HIGHLIGHTS
          </div>
        </div>
      )}
    </div>
  );
}

const fullSign = (i: number) => FULL_SIGNS[i] ?? "";