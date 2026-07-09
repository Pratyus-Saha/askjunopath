"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import AuthGuard from "@/components/AuthGuard";
import ConfidenceChip from "@/components/ui/ConfidenceChip";
import Disclaimer from "@/components/ui/Disclaimer";
import TimelineStrip from "@/components/predict/TimelineStrip";
import WindowCard from "@/components/predict/WindowCard";
import DashaCard from "@/components/predict/DashaCard";
import { getWindowEventType } from "@/lib/predict/eventType";
import { supabase } from "@/lib/supabase";
import fixture from "@/src/fixtures/synthesis_relationship.json";

type PredictionResult = {
  domain: string;
  engine_output: {
    as_of?: string;
    current_dasha_stack?: {
      mahadasha?: string;
      antardasha?: string;
      pratyantardasha?: string;
      mahadasha_window?: [string, string];
      antardasha_window?: [string, string];
      pratyantardasha_window?: [string, string];
    };
    promise_met: boolean;
    confidence: "high" | "medium" | "low";
    signal_strength: number;
    caution_flag: boolean;
    dasha_timing: {
      md_lord?: string;
      ad_lord?: string;
      pd_lord?: string;
      md_supports?: boolean;
      ad_supports?: boolean;
      pd_supports?: boolean;
      timing_interpretation?: string;
    };
    transit_windows: Array<{
      start_date: string;
      end_date: string;
      domain: string;
      window_score: number;
      trigger_count: number;
      triggers: Array<{
        planet: string;
        natal_point: string;
        contact_date: string;
      }>;
    }>;
    transit_summary: {
      framing: string;
      next_contact?: {
        estimated_date: string;
      };
    };
    event_types: string[];
    summary: string;
    cusp_sublords: Record<string, { sub_lord: string; signifies: number[] }>;
  };
  synthesis: Array<{
    text: string;
    references: string[];
  }>;
  fallback_used: boolean;
  disclaimer: string;
};

const tierMap: Record<string, "HIGH" | "MEDIUM" | "SPECULATIVE"> = {
  high: "HIGH",
  medium: "MEDIUM",
  low: "SPECULATIVE",
};

export default function RelationshipPredictionPage() {
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [needsChart, setNeedsChart] = useState(false);
  const [showFullSynthesis, setShowFullSynthesis] = useState(false);

  useEffect(() => {
    async function fetchPrediction() {
      setLoading(true);
      setError(null);
      setNeedsChart(false);
      try {
        if (process.env.NEXT_PUBLIC_USE_FIXTURE === "true") {
          setResult(fixture as unknown as PredictionResult);
        } else {
          const stored = sessionStorage.getItem("ajp.chart.v1");
          if (!stored) {
            setNeedsChart(true);
            return;
          }
          const parsed = JSON.parse(stored);
          const chart = parsed.chart;

          const { data: { session } } = await supabase.auth.getSession();
          if (!session) {
            throw new Error("You must be logged in to view predictions.");
          }

          const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
          const res = await fetch(`${apiUrl}/predict/relationship`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${session.access_token}`,
            },
            body: JSON.stringify({ chart }),
          });

          if (!res.ok) {
            throw new Error(`Failed to fetch prediction: ${res.statusText}`);
          }

          const data = await res.json();
          setResult(data as PredictionResult);
        }
      } catch (err: any) {
        setError(err.message || "An error occurred");
      } finally {
        setLoading(false);
      }
    }

    fetchPrediction();
  }, []);

  const resolvedWindows = React.useMemo(() => {
    if (!result?.engine_output?.transit_windows) return [];
    return result.engine_output.transit_windows.map(w => ({
      ...w,
      type: getWindowEventType(w, result.engine_output)
    }));
  }, [result]);

  return (
    <AuthGuard>
      <main className="min-h-screen bg-[var(--navy)] p-4 md:p-8 font-[family-name:var(--font-sans)] text-[var(--ivory-soft)]">
        <div className="max-w-4xl mx-auto space-y-8">
          
          <Disclaimer text={result?.disclaimer} />

          {loading ? (
            <div className="flex justify-center py-12">
              <svg className="animate-spin h-8 w-8 text-gold" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            </div>
          ) : needsChart ? (
            <div className="py-12 text-center space-y-4">
              <p className="text-[var(--ivory)]">Please generate your chart first</p>
              <Link
                href="/chart"
                className="inline-block px-4 py-2 bg-[var(--navy-raised)] border border-[var(--border)] rounded hover:bg-[var(--navy-deep)] transition-colors text-[var(--gold)]"
              >
                Go to chart
              </Link>
            </div>
          ) : error ? (
            <div className="text-[var(--clay)] py-8 text-center space-y-4">
              <p>{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-[var(--navy-raised)] border border-[var(--border)] rounded hover:bg-[var(--navy-deep)] transition-colors text-[var(--ivory)]"
              >
                Retry
              </button>
            </div>
          ) : result ? (
            <>
              <h1 className="text-3xl md:text-4xl text-[var(--ivory)] font-[family-name:var(--font-serif)]">
                Relationship Prediction
              </h1>

              <TimelineStrip 
                asOf={result.engine_output.as_of}
                transitWindows={resolvedWindows}
                pdWindow={result.engine_output.current_dasha_stack?.pratyantardasha_window}
                pdLord={result.engine_output.current_dasha_stack?.pratyantardasha}
                nextContactDate={result.engine_output.transit_summary?.next_contact?.estimated_date}
              />

              <div>
                <ConfidenceChip tier={tierMap[result.engine_output.confidence]} />
              </div>

              <div className="flex flex-col md:flex-row md:items-baseline gap-2">
                <span className="text-2xl font-[family-name:var(--font-mono)]">{result.engine_output.signal_strength}%</span>
                <span className="text-sm text-[var(--muted-on-dark)]">
                  Signal strength measures how many independent KP factors point the same way. It is not a probability that the event happens.
                </span>
              </div>

              {result.engine_output.caution_flag && (
                <div className="text-[var(--clay)] font-medium p-4 border border-[var(--clay)]/30 rounded-md bg-[var(--clay)]/5">
                  One or more challenge houses are activated in this period.
                </div>
              )}

              {result.engine_output.transit_summary && result.engine_output.transit_summary.framing && (
                <div className="bg-[var(--navy-raised)] p-6 rounded-md border border-[var(--border)]">
                  <h3 className="text-lg font-[family-name:var(--font-serif)] text-[var(--ivory)] mb-2">Transit Overview</h3>
                  <p className="text-[var(--ivory-soft)]">{result.engine_output.transit_summary.framing}</p>
                </div>
              )}

              {resolvedWindows.length > 0 && (
                <div className="space-y-4 mt-8">
                  <h3 className="text-xl font-[family-name:var(--font-serif)] text-[var(--ivory)]">Active Transit Windows</h3>
                  <div className="grid gap-4">
                    {resolvedWindows.map((window, idx) => (
                      <WindowCard
                        key={idx}
                        idx={idx}
                        windowData={window as any}
                        eventType={window.type as any}
                        engineOutput={result.engine_output}
                      />
                    ))}
                  </div>
                </div>
              )}

              <DashaCard
                currentStack={result.engine_output.current_dasha_stack}
                dashaTiming={result.engine_output.dasha_timing}
              />

              <div className="mt-8 space-y-4">
                <h2 className="text-2xl font-[family-name:var(--font-serif)] text-[var(--ivory)]">Reading</h2>
                <div className="space-y-4">
                  {result.synthesis.slice(0, showFullSynthesis ? undefined : 2).map((item, idx) => (
                    <div key={idx}>
                      <p className="leading-relaxed text-[var(--ivory-soft)]">{item.text}</p>
                    </div>
                  ))}
                </div>
                {result.synthesis.length > 2 && !showFullSynthesis && (
                  <button onClick={() => setShowFullSynthesis(true)} className="text-[var(--gold)] text-sm hover:underline mt-2">
                    Read full analysis &rarr;
                  </button>
                )}
              </div>

              <details className="group border border-[var(--border)] rounded-md mt-8">
                <summary className="p-4 cursor-pointer font-medium hover:bg-[var(--navy-raised)] transition-colors text-[var(--ivory)]">
                  How this was computed
                </summary>
                <div className="p-4 bg-[var(--navy-deep)] overflow-auto border-t border-[var(--border)]">
                  <pre className="text-xs font-[family-name:var(--font-mono)] text-[var(--muted-on-dark)] whitespace-pre-wrap">
                    {JSON.stringify(result.engine_output, null, 2)}
                  </pre>
                </div>
              </details>

            </>
          ) : null}

        </div>
      </main>
    </AuthGuard>
  );
}
