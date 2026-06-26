"use client";

import { useState } from "react";
import Link from "next/link";
import AuthGuard from "@/components/AuthGuard";

import { supabase } from "@/lib/supabase";
import type { ChartData } from "../../src/types/chart";
import sampleFixture from "../../src/fixtures/chart.sample.json";

type ChartResponse = {
  cache_status: string;
  chart_id: string;
  chart_fingerprint: string;
  chart: ChartData;
};

export default function ChartPage() {
  // Form input states with requested Day 1 defaults
  const [birthDate, setBirthDate] = useState("1998-04-21");
  const [birthTime, setBirthTime] = useState("14:35");
  const [birthCity, setBirthCity] = useState("Kolkata");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<ChartResponse | null>(null);
  const [showRawJson, setShowRawJson] = useState(false);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const useFixture = process.env.NEXT_PUBLIC_USE_FIXTURE === "1";

    if (useFixture) {
      setTimeout(() => {
        setChartData({
          cache_status: "HIT",
          chart_id: "fixture_01_sample",
          chart_fingerprint: "static_fixture",
          chart: sampleFixture as ChartData
        });
        setLoading(false);
      }, 500);
      return;
    }
    
    try {
      // Auth swap (D006): identity comes from the Supabase session JWT.
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) {
        setError("Please sign in to generate a chart");
        return;
      }

      const response = await fetch(`${apiUrl}/chart/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          birth_date: birthDate,
          birth_time: birthTime,
          birth_city: birthCity,
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${response.status}`);
      }

      const data: ChartResponse = await response.json();
      setChartData(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An unexpected error occurred. Is the backend API running?");
    } finally {
      setLoading(false);
    }
  };

  const formatDegrees = (deg: number) => {
    const d = Math.floor(deg);
    const m = Math.floor((deg - d) * 60);
    return `${d}° ${m}'`;
  };

  return (
    <AuthGuard>
      <main className="min-h-screen px-4 py-8 md:px-8 max-w-7xl mx-auto space-y-8">
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <Link href="/" className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
          AskJunoPath
        </Link>
        <span className="text-xs text-slate-500 font-mono">MVP Scaffold</span>
      </div>

      {/* Main Content Split Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Side: Form inputs card */}
        <div className="lg:col-span-1 bg-slate-900/40 backdrop-blur-md rounded-2xl border border-slate-800 p-6 space-y-6">
          <div>
            <h2 className="text-xl font-semibold text-slate-200">Birth Details</h2>
            <p className="text-xs text-slate-500 mt-1">Enter your birth parameters to calculate the chart</p>
          </div>

          <form onSubmit={handleGenerate} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Birth Date</label>
              <input
                type="date"
                required
                value={birthDate}
                onChange={(e) => setBirthDate(e.target.value)}
                className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition text-slate-100"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Birth Time (24h)</label>
              <input
                type="time"
                required
                value={birthTime}
                onChange={(e) => setBirthTime(e.target.value)}
                className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition text-slate-100"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Birth City</label>
              <input
                type="text"
                required
                placeholder="e.g. Kolkata"
                value={birthCity}
                onChange={(e) => setBirthCity(e.target.value)}
                className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition text-slate-100 placeholder-slate-600"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-slate-100 font-semibold py-3.5 rounded-xl shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.01]"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Calculating...
                </span>
              ) : "Generate Chart"}
            </button>
          </form>

          {error && (
            <div className="bg-red-950/30 border border-red-800/50 rounded-xl p-4 text-sm text-red-300">
              <span className="font-semibold block mb-1">Calculation Error</span>
              {error}
            </div>
          )}
        </div>

        {/* Right Side: Results visualizer */}
        <div className="lg:col-span-2 space-y-6">
          {chartData ? (
            <div className="bg-slate-900/20 rounded-2xl border border-slate-800 p-6 space-y-6">
              
              {/* Cache status and metadata header */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-4">
                <div>
                  <h3 className="text-xl font-bold text-slate-100">Astrological Profile</h3>
                  <p className="text-xs text-slate-400 mt-1 font-mono">
                    ID: {chartData.chart_id}
                  </p>
                </div>
                
                {/* Cache Badge */}
                <div>
                  {chartData.cache_status === "HIT" ? (
                    <div className="inline-flex flex-col items-end">
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        Cache HIT
                      </span>
                      <span className="text-[10px] text-emerald-500 mt-1 font-medium">Loaded saved chart</span>
                    </div>
                  ) : (
                    <div className="inline-flex flex-col items-end">
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">
                        <span className="w-2 h-2 rounded-full bg-purple-400" />
                        Cache MISS
                      </span>
                      <span className="text-[10px] text-purple-500 mt-1 font-medium">Generated new chart</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Calculations Metadata Grid */}
              {(() => {
                const meta = chartData.chart.metadata;
                return (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-950/50 p-4 rounded-xl border border-slate-800/50 text-xs">
                    <div>
                      <span className="text-slate-500 block mb-1">Birth Location</span>
                      <span className="text-slate-300 font-semibold truncate block">{meta?.birth_city || "-"}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block mb-1">Coordinates</span>
                      <span className="text-slate-300 font-semibold font-mono block">
                        {meta?.latitude?.toFixed(4) || "0.0000"}°, {meta?.longitude?.toFixed(4) || "0.0000"}°
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block mb-1">Ayanamsa (KP)</span>
                      <span className="text-slate-300 font-semibold block">{meta?.ayanamsa ? formatDegrees(meta.ayanamsa) : "-"}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block mb-1">Timezone</span>
                      <span className="text-slate-300 font-semibold block">{meta?.timezone || "-"}</span>
                    </div>
                  </div>
                );
              })()}

              {/* Ascendant lagna display */}
              <div className="bg-indigo-950/20 border border-indigo-500/20 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <span className="text-xs text-indigo-300 uppercase tracking-widest block font-medium">Ascendant (Lagna)</span>
                  <span className="text-2xl font-black text-slate-100 mt-1 block">
                    {chartData.chart.ascendant.sign} <span className="text-indigo-400 text-lg font-normal">({formatDegrees(chartData.chart.ascendant.sign_degree)})</span>
                  </span>
                </div>
                <div className="text-right text-xs">
                  <span className="text-slate-500 block">Nakshatra / Lord</span>
                  <span className="text-indigo-300 font-semibold mt-1 block">
                    -
                  </span>
                </div>
              </div>

              {/* Planets Positions Table */}
              <div>
                <h4 className="text-sm font-bold text-slate-300 mb-3 uppercase tracking-wider">Planetary Positions</h4>
                <div className="overflow-x-auto border border-slate-800 rounded-xl">
                  <table className="w-full text-left border-collapse text-xs md:text-sm">
                    <thead>
                      <tr className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-mono">
                        <th className="py-3.5 px-4 font-medium">Planet</th>
                        <th className="py-3.5 px-4 font-medium">Sidereal Longitude</th>
                        <th className="py-3.5 px-4 font-medium">Zodiac Sign</th>
                        <th className="py-3.5 px-4 font-medium">Nakshatra</th>
                        <th className="py-3.5 px-4 font-medium">Lord</th>
                        <th className="py-3.5 px-4 font-medium">KP Star/Sub</th>
                        <th className="py-3.5 px-4 font-medium text-center">Retro</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {chartData.chart.planets.map((planet) => (
                        <tr key={planet.name} className="hover:bg-slate-800/10 transition-colors">
                          <td className="py-3.5 px-4 font-bold text-slate-200">{planet.name}</td>
                          <td className="py-3.5 px-4 font-mono text-slate-300">
                            {formatDegrees(planet.longitude)}
                          </td>
                          <td className="py-3.5 px-4 text-slate-300">
                            {planet.sign} <span className="text-slate-500 text-[10px] ml-1">({formatDegrees(planet.sign_degree)})</span>
                          </td>
                          <td className="py-3.5 px-4 text-slate-300">{planet.nakshatra?.name || "-"}</td>
                          <td className="py-3.5 px-4 text-slate-400 font-medium">{planet.nakshatra?.lord || "-"}</td>
                          <td className="py-3.5 px-4 text-slate-400 font-medium">
                            {planet.kp ? `${planet.kp.star_lord} / ${planet.kp.sub_lord}` : "-"}
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            {planet.retrograde ? (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                RETRO
                              </span>
                            ) : (
                              <span className="text-slate-600">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Collapsible raw JSON */}
              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => setShowRawJson(!showRawJson)}
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold focus:outline-none flex items-center gap-1.5"
                >
                  <span>{showRawJson ? "▼ Hide" : "▶ Show"} Raw Astrological Data JSON</span>
                </button>
                {showRawJson && (
                  <pre className="bg-slate-950 border border-slate-800 rounded-xl p-4 mt-3 text-[10px] font-mono overflow-auto max-h-[300px] text-slate-400">
                    {JSON.stringify(chartData, null, 2)}
                  </pre>
                )}
              </div>

            </div>
          ) : (
            <div className="h-full min-h-[350px] border border-dashed border-slate-800 rounded-2xl flex flex-col items-center justify-center text-center p-8 text-slate-600">
              <svg className="w-12 h-12 text-slate-800 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              <h3 className="text-base font-semibold text-slate-500">No Chart Loaded</h3>
              <p className="text-xs text-slate-600 max-w-sm mt-1">
                Enter your birth details in the sidebar and click Generate Chart to calculate your alignments.
              </p>
            </div>
          )}
        </div>

      </div>
    </main>
    </AuthGuard>
  );
}
