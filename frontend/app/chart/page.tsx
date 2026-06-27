"use client";

import { useState } from "react";
import Link from "next/link";
import AuthGuard from "@/components/AuthGuard";
import { supabase } from "@/lib/supabase";

type ChartResponse = {
  cache_status?: string;
  chart_id: string;
  chart_fingerprint?: string;
  chart: {
    metadata: {
      birth_city?: string;
      latitude: number;
      longitude: number;
      timezone?: string;
      ayanamsa?: number;
    };
    ascendant: {
      sign: string;
      sign_degree: number;
    };
    planets: Array<{
      name: string;
      longitude: number;
      sign: string;
      sign_degree: number;
      house_occupied?: number;
      nakshatra?: {
        name: string;
        lord: string;
      };
      kp?: {
        star_lord: string;
        sub_lord: string;
      };
      retrograde: boolean;
    }>;
    houses: Array<{
      house: number;
      cusp_longitude: number;
      cusp_sign: string;
      kp?: {
        star_lord: string;
        sub_lord: string;
      };
    }>;
    dasha?: {
      current?: {
        mahadasha?: { lord: string };
        antardasha?: { lord: string };
        pratyantardasha?: { lord: string };
      };
    };
  };
};

export default function ChartPage() {
  const [name, setName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [birthTime, setBirthTime] = useState("");
  const [birthCity, setBirthCity] = useState("");
  const [lat, setLat] = useState<number | "">("");
  const [lon, setLon] = useState<number | "">("");
  const [approxTime, setApproxTime] = useState(false);

  const [locating, setLocating] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<ChartResponse | null>(null);

  const handleCityBlur = async () => {
    if (!birthCity.trim()) return;
    setLocating(true);
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(
          birthCity
        )}&format=json&limit=1`,
        {
          headers: {
            "User-Agent": "AskJunoPath/1.0",
          },
        }
      );
      if (!res.ok) throw new Error("Geocoding failed");
      const data = await res.json();
      if (data && data.length > 0) {
        setLat(parseFloat(data[0].lat));
        setLon(parseFloat(data[0].lon));
      } else {
        // Did not find city
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLocating(false);
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!birthDate || !birthTime || !birthCity || lat === "" || lon === "") {
      setError("Please fill in all required fields, including latitude and longitude.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) {
        setError("Please sign in to generate a chart");
        return;
      }

      const [year, month, day] = birthDate.split("-").map(Number);
      const [hour, minute] = birthTime.split(":").map(Number);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      
      const payload = {
        birth_date: birthDate,
        birth_time: birthTime,
        birth_city: birthCity,
        latitude: Number(lat),
        longitude: Number(lon),
      };

      const response = await fetch(`${apiUrl}/chart/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${response.status}`);
      }

      const data: ChartResponse = await response.json();
      setChartData(data);

      // Persist the chart so the predict pages (career/finance/relationship)
      // can read it from localStorage and POST it to /predict/{domain}.
      try {
        localStorage.setItem("junopath_chart", JSON.stringify(data.chart));
      } catch (storageErr) {
        console.error("Failed to persist chart to localStorage", storageErr);
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An unexpected error occurred while generating the chart.");
    } finally {
      setLoading(false);
    }
  };

  const formatDegrees = (deg: number) => {
    if (deg === undefined || deg === null) return "-";
    const d = Math.floor(deg);
    const m = Math.floor((deg - d) * 60);
    return `${d}° ${m}'`;
  };

  return (
    <AuthGuard>
      <main className="min-h-screen bg-navy p-4 md:p-8">
        <div className="max-w-7xl mx-auto space-y-8">
          
          <div className="flex items-center justify-between border-b border-gold-soft pb-4">
            <Link href="/" className="text-xl font-serif text-gold-bright">
              AskJunoPath
            </Link>
            <span className="text-xs text-muted-dark font-mono uppercase tracking-widest">Chart Generation</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            
            {/* Form */}
            <div className="lg:col-span-4 space-y-6">
              <div className="bg-navy-raised border border-gold-soft rounded-md p-6 relative overflow-hidden shadow-2xl">
                <div className="absolute top-0 left-0 w-full h-1 bg-gold"></div>
                <h2 className="text-xl font-serif text-ivory-warm mb-1">Birth Data</h2>
                <p className="text-sm text-muted-dark mb-6">Enter details to calculate chart alignments.</p>

                <form onSubmit={handleGenerate} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-muted-dark uppercase tracking-wider mb-1">Full Name (Optional)</label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. Jane Doe"
                      className="w-full bg-navy border border-gold-soft rounded px-3 py-2.5 text-sm text-ivory placeholder:text-muted-dark/50 focus:outline-none focus:border-gold transition-colors"
                      disabled={loading}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-muted-dark uppercase tracking-wider mb-1">Date *</label>
                      <input
                        type="date"
                        required
                        value={birthDate}
                        onChange={(e) => setBirthDate(e.target.value)}
                        className="w-full bg-navy border border-gold-soft rounded px-3 py-2.5 text-sm text-ivory focus:outline-none focus:border-gold transition-colors"
                        disabled={loading}
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-muted-dark uppercase tracking-wider mb-1">Time (24h) *</label>
                      <input
                        type="time"
                        required
                        value={birthTime}
                        onChange={(e) => setBirthTime(e.target.value)}
                        className="w-full bg-navy border border-gold-soft rounded px-3 py-2.5 text-sm text-ivory focus:outline-none focus:border-gold transition-colors"
                        disabled={loading}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-muted-dark uppercase tracking-wider mb-1">City *</label>
                    <div className="relative">
                      <input
                        type="text"
                        required
                        value={birthCity}
                        onChange={(e) => setBirthCity(e.target.value)}
                        onBlur={handleCityBlur}
                        placeholder="e.g. New York"
                        className="w-full bg-navy border border-gold-soft rounded px-3 py-2.5 text-sm text-ivory placeholder:text-muted-dark/50 focus:outline-none focus:border-gold transition-colors"
                        disabled={loading}
                      />
                      {locating && (
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 text-xs text-gold">
                          <svg className="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          Locating...
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-muted-dark uppercase tracking-wider mb-1">Latitude *</label>
                      <input
                        type="number"
                        step="any"
                        required
                        value={lat}
                        onChange={(e) => setLat(e.target.value === "" ? "" : Number(e.target.value))}
                        className="w-full bg-navy border border-gold-soft rounded px-3 py-2.5 text-sm text-ivory focus:outline-none focus:border-gold transition-colors"
                        disabled={loading}
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-muted-dark uppercase tracking-wider mb-1">Longitude *</label>
                      <input
                        type="number"
                        step="any"
                        required
                        value={lon}
                        onChange={(e) => setLon(e.target.value === "" ? "" : Number(e.target.value))}
                        className="w-full bg-navy border border-gold-soft rounded px-3 py-2.5 text-sm text-ivory focus:outline-none focus:border-gold transition-colors"
                        disabled={loading}
                      />
                    </div>
                  </div>

                  <div className="flex items-start gap-2 pt-2">
                    <input
                      type="checkbox"
                      id="approxTime"
                      checked={approxTime}
                      onChange={(e) => setApproxTime(e.target.checked)}
                      className="mt-1 h-4 w-4 bg-navy border-gold-soft text-gold focus:ring-gold rounded"
                      disabled={loading}
                    />
                    <label htmlFor="approxTime" className="text-xs text-muted-dark cursor-pointer">
                      Approximate time?
                      {approxTime && <span className="block text-clay mt-0.5">Results may vary with approximate time.</span>}
                    </label>
                  </div>

                  <div className="pt-4">
                    <button
                      type="submit"
                      disabled={loading}
                      className="btn-juno w-full"
                    >
                      {loading ? (
                        <span className="flex items-center justify-center gap-2">
                          <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          Calculating...
                        </span>
                      ) : (
                        "Generate Chart"
                      )}
                    </button>
                  </div>
                  
                  {error && (
                    <div className="text-clay text-sm text-center bg-clay/10 py-2 px-3 rounded border border-clay/20 mt-4">
                      {error}
                    </div>
                  )}
                </form>
              </div>
            </div>

            {/* Results */}
            <div className="lg:col-span-8 space-y-6">
              {chartData ? (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                  
                  {/* Action Buttons */}
                  <div className="flex flex-wrap gap-3">
                    <Link href="/predict/career" className="btn-juno btn-juno-compact">Career Reading</Link>
                    <Link href="/predict/finance" className="btn-juno btn-juno-compact">Finance Reading</Link>
                    <Link href="/predict/relationship" className="btn-juno btn-juno-compact">Relationship Reading</Link>
                  </div>

                  <div className="bg-navy-raised border border-gold-soft rounded-md p-6 shadow-xl">
                    <h2 className="text-xl font-serif text-ivory-warm mb-6 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-gold inline-block"></span>
                      Your Chart
                    </h2>

                    {/* Ascendant */}
                    <div className="mb-8 p-4 bg-navy border border-ink-soft rounded">
                      <h3 className="text-xs font-mono uppercase tracking-widest text-muted-dark mb-3">Ascendant</h3>
                      <div className="flex flex-wrap items-baseline gap-2 text-sm">
                        <span className="text-lg font-serif text-gold-bright">{chartData.chart.ascendant.sign}</span>
                        <span className="text-muted-dark font-mono text-xs">{formatDegrees(chartData.chart.ascendant.sign_degree)}</span>
                      </div>
                    </div>

                    {/* Dasha */}
                    {chartData.chart.dasha?.current && (
                      <div className="mb-8 p-4 bg-navy border border-ink-soft rounded">
                        <h3 className="text-xs font-mono uppercase tracking-widest text-muted-dark mb-3">Current Dasha</h3>
                        <div className="flex flex-wrap gap-4 text-sm">
                          <div className="flex items-center gap-2">
                            <span className="text-muted-dark">MD:</span>
                            <span className="text-ivory font-medium">{chartData.chart.dasha.current.mahadasha?.lord || "-"}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-muted-dark">AD:</span>
                            <span className="text-ivory font-medium">{chartData.chart.dasha.current.antardasha?.lord || "-"}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-muted-dark">PD:</span>
                            <span className="text-ivory font-medium">{chartData.chart.dasha.current.pratyantardasha?.lord || "-"}</span>
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                      {/* Planets Table */}
                      <div>
                        <h3 className="text-xs font-mono uppercase tracking-widest text-muted-dark mb-3">Planetary Positions</h3>
                        <div className="overflow-x-auto">
                          <table className="w-full text-left text-sm whitespace-nowrap">
                            <thead>
                              <tr className="border-b border-gold-soft/50 text-muted-dark font-medium">
                                <th className="pb-2 font-normal">Planet</th>
                                <th className="pb-2 font-normal">Sign</th>
                                <th className="pb-2 font-normal">Longitude</th>
                                <th className="pb-2 font-normal">Nakshatra</th>
                                <th className="pb-2 font-normal text-right">House</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-ink-soft">
                              {chartData.chart.planets.map((planet) => (
                                <tr key={planet.name} className="hover:bg-navy transition-colors">
                                  <td className="py-2.5 text-ivory">{planet.name}</td>
                                  <td className="py-2.5 text-ivory">{planet.sign}</td>
                                  <td className="py-2.5 text-muted-dark font-mono text-xs">{formatDegrees(planet.longitude)}</td>
                                  <td className="py-2.5 text-muted-dark">{planet.nakshatra?.name || "-"}</td>
                                  <td className="py-2.5 text-right text-gold-bright font-medium">{planet.house_occupied || "-"}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>

                      {/* Houses Table */}
                      <div>
                        <h3 className="text-xs font-mono uppercase tracking-widest text-muted-dark mb-3">House Cusps</h3>
                        <div className="overflow-x-auto">
                          <table className="w-full text-left text-sm whitespace-nowrap">
                            <thead>
                              <tr className="border-b border-gold-soft/50 text-muted-dark font-medium">
                                <th className="pb-2 font-normal">House</th>
                                <th className="pb-2 font-normal">Sign</th>
                                <th className="pb-2 font-normal">Cusp</th>
                                <th className="pb-2 font-normal text-right">Sublord</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-ink-soft">
                              {chartData.chart.houses.map((house) => (
                                <tr key={house.house} className="hover:bg-navy transition-colors">
                                  <td className="py-2.5 text-ivory">H{house.house}</td>
                                  <td className="py-2.5 text-ivory">{house.cusp_sign}</td>
                                  <td className="py-2.5 text-muted-dark font-mono text-xs">{formatDegrees(house.cusp_longitude)}</td>
                                  <td className="py-2.5 text-right text-gold-bright font-medium">{house.kp?.sub_lord || "-"}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                    
                  </div>
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center p-12 border border-dashed border-ink-soft rounded-md bg-navy-raised/50">
                  
                  {/* Disabled reading buttons state */}
                  <div className="flex flex-wrap justify-center gap-3 mb-10 opacity-40 pointer-events-none">
                    <button className="btn-juno btn-juno-compact">Career Reading</button>
                    <button className="btn-juno btn-juno-compact">Finance Reading</button>
                    <button className="btn-juno btn-juno-compact">Relationship Reading</button>
                  </div>
                  
                  <div className="w-12 h-12 rounded-full border border-gold-soft flex items-center justify-center mb-4 text-gold-soft">
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-serif text-ivory mb-2">No Chart Generated</h3>
                  <p className="text-sm text-muted-dark max-w-md text-center">
                    Enter your birth details and generate a chart to view your planetary alignments and unlock deep readings.
                  </p>
                </div>
              )}
            </div>

          </div>
        </div>
      </main>
    </AuthGuard>
  );
}

