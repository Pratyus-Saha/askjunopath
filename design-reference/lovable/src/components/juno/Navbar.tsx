import { useEffect, useState } from "react";

const links = [
  { id: "method", label: "How it works" },
  { id: "evidence", label: "Why trust this" },
  { id: "reading", label: "The reading" },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const go = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <header
      className="fixed top-0 left-0 right-0 z-50 transition-all duration-500"
      style={{
        height: 60,
        backgroundColor: scrolled ? "rgba(8, 19, 31, 0.72)" : "transparent",
        backdropFilter: scrolled ? "blur(14px) saturate(140%)" : "none",
        borderBottom: scrolled ? "1px solid rgba(199, 154, 78, 0.35)" : "1px solid transparent",
      }}
    >
      <div className="mx-auto flex h-full max-w-[1240px] items-center justify-between px-6 md:px-10">
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="font-serif text-[22px] tracking-wide text-ivory hover:text-gold-bright transition-colors"
          aria-label="JunoPath home"
        >
          JunoPath
        </button>

        <nav className="hidden md:flex items-center gap-9">
          {links.map((l) => (
            <button
              key={l.id}
              onClick={() => go(l.id)}
              className="text-[13px] tracking-wide text-muted-dark hover:text-ivory transition-colors"
            >
              {l.label}
            </button>
          ))}
        </nav>

        <button onClick={() => go("try")} className="btn-juno btn-juno-compact">
          Generate your chart
        </button>
      </div>
    </header>
  );
}