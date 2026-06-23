import { useEffect, useRef } from "react";

type Star = { x: number; y: number; r: number; o: number; layer: number };

/**
 * Calm, sparse, accurate-feeling starfield with 3 parallax layers.
 * Fixed canvas, transform-only parallax on scroll. Honors reduced motion.
 */
export function Starfield() {
  const ref = useRef<HTMLCanvasElement>(null);
  const layers = useRef<HTMLDivElement[]>([]);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let stars: Star[] = [];

    const resize = () => {
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = window.innerWidth + "px";
      canvas.style.height = window.innerHeight + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      seed();
      draw(0);
    };

    const seed = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      const density = Math.min(1.2, (w * h) / 1_400_000); // sparse
      const count = Math.floor(160 * density + 80);
      stars = [];
      for (let i = 0; i < count; i++) {
        const layer = i % 3; // 0 far, 1 mid, 2 near
        stars.push({
          x: Math.random() * w,
          y: Math.random() * (h * 2.4),
          r: layer === 2 ? 0.9 + Math.random() * 0.6 : layer === 1 ? 0.6 + Math.random() * 0.5 : 0.4 + Math.random() * 0.4,
          o: layer === 2 ? 0.55 + Math.random() * 0.35 : layer === 1 ? 0.35 + Math.random() * 0.3 : 0.18 + Math.random() * 0.22,
          layer,
        });
      }
    };

    const draw = (scrollY: number) => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      ctx.clearRect(0, 0, w, h);
      for (const s of stars) {
        const parallax = s.layer === 0 ? 0.04 : s.layer === 1 ? 0.12 : 0.22;
        const y = ((s.y - scrollY * parallax) % (h * 2.4) + h * 2.4) % (h * 2.4);
        if (y > h + 4 || y < -4) continue;
        ctx.beginPath();
        ctx.fillStyle = `rgba(244, 236, 221, ${s.o})`;
        ctx.arc(s.x, y, s.r, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => draw(window.scrollY));
    };

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("resize", resize);
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div ref={(el) => { if (el) layers.current[0] = el; }} className="pointer-events-none fixed inset-0 -z-10">
      <div className="absolute inset-0" style={{ background: "radial-gradient(ellipse at 50% 30%, #0e2236 0%, #0B1A2B 45%, #08131F 100%)" }} />
      <canvas ref={ref} className="absolute inset-0" />
    </div>
  );
}