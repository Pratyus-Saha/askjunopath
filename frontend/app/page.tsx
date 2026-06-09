import Link from "next/link";

export default function Home() {
  return (
    <main className="relative flex flex-col items-center justify-center min-h-screen px-6 py-12 text-center overflow-hidden">
      {/* Background radial highlight */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none -z-10" />

      <div className="max-w-3xl mx-auto space-y-8 z-10">
        {/* Sleek pill badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-indigo-500/30 bg-indigo-950/40 text-xs font-medium tracking-widest text-indigo-300 uppercase shadow-inner">
          ✨ Vedic Astrological Engine
        </div>

        {/* Hero Headline */}
        <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight leading-tight bg-clip-text text-transparent bg-gradient-to-b from-slate-50 via-slate-100 to-indigo-300">
          Ask Better Questions.<br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400">
            Get Precise Astrological Timing.
          </span>
        </h1>

        {/* Subheadline */}
        <p className="text-base sm:text-lg md:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
          AskJunoPath combines KP astrology, planetary math, and AI to show clear timing logic behind life events.
        </p>

        {/* Call to Action button */}
        <div className="pt-6">
          <Link
            href="/chart"
            className="inline-flex items-center justify-center px-8 py-4 rounded-xl text-base font-semibold text-slate-50 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 transition-all duration-300 shadow-xl shadow-indigo-500/20 hover:shadow-indigo-500/40 border border-indigo-400/20 hover:-translate-y-0.5 active:translate-y-0"
          >
            Generate Your Chart
          </Link>
        </div>
      </div>

      {/* Footer Branding */}
      <div className="absolute bottom-6 text-xs text-slate-600 tracking-widest font-mono uppercase">
        AskJunoPath © 2026
      </div>
    </main>
  );
}
