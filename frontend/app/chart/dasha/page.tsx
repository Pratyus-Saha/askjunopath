"use client";

import React, { useEffect, useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import fixture from "@/src/fixtures/dasha_timeline.json";
import Link from "next/link";
import { useRouter } from "next/navigation";

type DashaPeriod = {
  level: "MD" | "AD" | "PD"
  lords: string[]
  start: string
  end: string
}

type DashaTimeline = {
  birth: string
  birth_balance_lord: string
  birth_balance_years: number
  mahadashas: DashaPeriod[]
  antardashas: DashaPeriod[]
  pratyantardashas: DashaPeriod[]
}

function formatYMD(isoString: string) {
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return "-";
  return d.toISOString().split("T")[0];
}

function formatYear(isoString: string) {
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return "-";
  return d.getFullYear().toString();
}

function formatMMMYYYY(isoString: string) {
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return "-";
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

function computeYears(start: string, end: string) {
  const s = new Date(start).getTime();
  const e = new Date(end).getTime();
  return Math.round((e - s) / (1000 * 60 * 60 * 24 * 365.2425));
}

export default function DashaTimelinePage() {
  const router = useRouter();
  const [timeline, setTimeline] = useState<DashaTimeline | null>(null);

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_USE_FIXTURE === "true") {
      setTimeline(fixture as DashaTimeline);
    } else {
      const raw = sessionStorage.getItem("ajp.chart.v1");
      if (!raw) {
        router.replace("/chart");
        return;
      }
      try {
        const { chart } = JSON.parse(raw);
        const dashaData = chart?.dasha?.timeline || chart?.dasha || fixture;
        setTimeline(dashaData as DashaTimeline);
      } catch (err) {
        router.replace("/chart");
      }
    }
  }, [router]);

  if (!timeline) {
    return (
      <AuthGuard>
        <main className="min-h-screen bg-[var(--navy)] p-4 md:p-8 flex items-center justify-center font-[family-name:var(--font-sans)]">
          <div className="text-[var(--gold)] animate-pulse">Loading timeline...</div>
        </main>
      </AuthGuard>
    );
  }

  const now = new Date();
  const getActivePeriod = (periods: DashaPeriod[]) => 
    periods.find(p => new Date(p.start) <= now && new Date(p.end) > now);

  const activeMD = getActivePeriod(timeline.mahadashas);
  const activeAD = getActivePeriod(timeline.antardashas);
  const activePD = getActivePeriod(timeline.pratyantardashas);

  const activeADIndex = timeline.antardashas.findIndex(p => new Date(p.start) <= now && new Date(p.end) > now);
  const upcomingADs = activeADIndex !== -1 
    ? timeline.antardashas.slice(activeADIndex + 1, activeADIndex + 6)
    : [];

  const activeMDADs = activeMD 
    ? timeline.antardashas.filter(p => new Date(p.start) >= new Date(activeMD.start) && new Date(p.end) <= new Date(activeMD.end))
    : [];

  return (
    <AuthGuard>
      <main className="min-h-screen bg-[var(--navy)] p-4 md:p-8 font-[family-name:var(--font-sans)] text-[var(--ivory-soft)]">
        <div className="max-w-3xl mx-auto space-y-8">
          
          <h1 className="text-3xl md:text-4xl text-[var(--ivory)] font-[family-name:var(--font-serif)]">
            Vimshottari Dasha Timeline
          </h1>

          {/* Current dasha stack block */}
          {activeMD && activeAD && activePD && (
            <div className="bg-[var(--navy-raised)] p-4 md:p-6 rounded-md space-y-3">
              <div className="flex flex-col md:flex-row md:items-center gap-1 md:gap-4">
                <span className="text-[var(--muted-on-dark)] w-36">Mahadasha:</span>
                <span className="text-[var(--gold)] font-medium text-lg">{activeMD.lords[activeMD.lords.length - 1]}</span>
                <span className="text-[var(--muted-on-dark)] md:ml-auto">
                  (ends <span className="font-[family-name:var(--font-mono)]">{formatYMD(activeMD.end)}</span>)
                </span>
              </div>
              <div className="flex flex-col md:flex-row md:items-center gap-1 md:gap-4">
                <span className="text-[var(--muted-on-dark)] w-36">Antardasha:</span>
                <span className="text-[var(--gold)] font-medium text-lg">{activeAD.lords[activeAD.lords.length - 1]}</span>
                <span className="text-[var(--muted-on-dark)] md:ml-auto">
                  (ends <span className="font-[family-name:var(--font-mono)]">{formatYMD(activeAD.end)}</span>)
                </span>
              </div>
              <div className="flex flex-col md:flex-row md:items-center gap-1 md:gap-4">
                <span className="text-[var(--muted-on-dark)] w-36">Pratyantardasha:</span>
                <span className="text-[var(--gold)] font-medium text-lg">{activePD.lords[activePD.lords.length - 1]}</span>
                <span className="text-[var(--muted-on-dark)] md:ml-auto">
                  (ends <span className="font-[family-name:var(--font-mono)]">{formatYMD(activePD.end)}</span>)
                </span>
              </div>
            </div>
          )}

          {/* Mahadasha timeline */}
          <div className="space-y-4">
            {timeline.mahadashas.map((md, idx) => {
              const isActive = activeMD && md.lords[md.lords.length - 1] === activeMD.lords[activeMD.lords.length - 1];
              
              return (
                <div key={idx} className="flex flex-col">
                  <div className={`p-4 rounded-md flex flex-col md:flex-row justify-between md:items-center transition-colors ${
                    isActive ? "bg-[var(--navy-raised)] border-l-[3px] border-[var(--gold)]" : "border-l-[3px] border-transparent"
                  }`}>
                    <div className="flex flex-col">
                      <span className="font-[family-name:var(--font-serif)] text-2xl text-[var(--ivory)]">{md.lords[md.lords.length - 1]}</span>
                      <span className="font-[family-name:var(--font-mono)] text-sm text-[var(--muted-on-dark)] mt-1">
                        {formatYear(md.start)} — {formatYear(md.end)}
                      </span>
                    </div>
                    <div className="text-[var(--muted-on-dark)] text-sm mt-2 md:mt-0">
                      {computeYears(md.start, md.end)} years
                    </div>
                  </div>

                  {/* Antardasha expansion for active MD */}
                  {isActive && activeMDADs.length > 0 && (
                    <div className="mt-2 ml-4 pl-4 border-l border-[var(--border)] space-y-3 py-2">
                      {activeMDADs.map((ad, i) => {
                        const isAdActive = activeAD && ad.lords.join() === activeAD.lords.join();
                        return (
                          <div key={i} className={`flex justify-between items-center text-sm ${isAdActive ? "text-[var(--gold)] font-medium" : "text-[var(--ivory-soft)]"}`}>
                            <span>{ad.lords[ad.lords.length - 1]}</span>
                            <span className="font-[family-name:var(--font-mono)] text-xs opacity-80">
                              {formatMMMYYYY(ad.start)} — {formatMMMYYYY(ad.end)}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Next 5 upcoming periods */}
          {upcomingADs.length > 0 && (
            <div className="pt-8 mt-8 border-t border-[var(--border)]">
              <h2 className="text-xl font-[family-name:var(--font-serif)] text-[var(--ivory)] mb-4">Upcoming Periods</h2>
              <div className="space-y-3">
                {upcomingADs.map((ad, idx) => (
                  <div key={idx} className="flex justify-between items-center p-4 bg-[var(--navy-raised)] rounded-md">
                    <span className="text-[var(--ivory-soft)] font-medium">
                      {ad.lords.join(" / ")}
                    </span>
                    <span className="font-[family-name:var(--font-mono)] text-sm text-[var(--muted-on-dark)]">
                      {formatYMD(ad.start)} — {formatYMD(ad.end)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Navigation link */}
          <div className="pt-8">
            <Link href="/chart" className="text-[var(--muted-on-dark)] hover:text-[var(--ivory-soft)] transition-colors text-sm">
              ← Back to Chart
            </Link>
          </div>

        </div>
      </main>
    </AuthGuard>
  );
}
