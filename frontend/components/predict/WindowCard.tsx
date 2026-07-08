"use client";
import React, { useState } from "react";

interface Trigger {
  planet: string;
  natal_point: string;
  contact_date: string;
  angular_diff_deg?: number;
  weight: number;
}

interface WindowCardProps {
  idx: number;
  windowData: {
    start_date: string;
    end_date: string;
    domain: string;
    window_score: number;
    trigger_count: number;
    pd_overlap?: boolean;
    triggers: Trigger[];
  };
  eventType: "advancement" | "steady-progress" | "caution";
  engineOutput: any;
}

function humanizeNatalPoint(point: string): string {
  if (point.startsWith("natal_")) {
    const p = point.replace("natal_", "");
    return p.charAt(0).toUpperCase() + p.slice(1);
  }
  if (point.startsWith("cusp_")) {
    const num = parseInt(point.replace("cusp_", ""), 10);
    const ordinals: Record<number, string> = { 1: "1st", 2: "2nd", 3: "3rd" };
    const ordinal = ordinals[num] || `${num}th`;
    return `${ordinal}-house cusp`;
  }
  return point;
}

function formatHumanDates(d1Str: string, d2Str?: string) {
  const d1 = new Date(d1Str);
  const m1 = d1.toLocaleString("en-US", { month: "short" });
  const day1 = d1.getDate();
  const y1 = d1.getFullYear();

  if (!d2Str) {
    return `${m1} ${day1}, ${y1}`;
  }
  
  const d2 = new Date(d2Str);
  const m2 = d2.toLocaleString("en-US", { month: "short" });
  const day2 = d2.getDate();
  const y2 = d2.getFullYear();

  if (y1 !== y2) {
    return `${m1} ${day1}, ${y1} – ${m2} ${day2}, ${y2}`;
  }
  if (m1 !== m2) {
    return `${m1} ${day1} – ${m2} ${day2}, ${y1}`;
  }
  return `${m1} ${day1}–${day2}, ${y1}`;
}

function computePeak(triggers: Trigger[]) {
  if (!triggers || triggers.length === 0) return null;
  const sorted = [...triggers].sort((a, b) => new Date(a.contact_date).getTime() - new Date(b.contact_date).getTime());
  
  let bestEntry: any = null;
  let bestWeight = -1;
  let bestDiff = Infinity;
  let bestCount = 1;

  for (let i = 0; i < sorted.length; i++) {
    const t1 = sorted[i];
    if (t1.weight > bestWeight || (t1.weight === bestWeight && (t1.angular_diff_deg || Infinity) < bestDiff)) {
      bestWeight = t1.weight;
      bestDiff = t1.angular_diff_deg || Infinity;
      bestEntry = { ...t1, dates: [t1.contact_date] };
      bestCount = 1;
    }
    
    const totalCount = sorted.filter(t => t.planet === t1.planet && t.natal_point === t1.natal_point).length;

    if (i < sorted.length - 1) {
      const t2 = sorted[i + 1];
      if (t1.planet === t2.planet && t1.natal_point === t2.natal_point) {
        const d1 = new Date(t1.contact_date);
        const d2 = new Date(t2.contact_date);
        const diffDays = (d2.getTime() - d1.getTime()) / (1000 * 3600 * 24);
        if (diffDays <= 1.5) {
          const sumWeight = t1.weight + t2.weight;
          const minDiff = Math.min(t1.angular_diff_deg || Infinity, t2.angular_diff_deg || Infinity);
          if (sumWeight > bestWeight || (sumWeight === bestWeight && minDiff < bestDiff)) {
            bestWeight = sumWeight;
            bestDiff = minDiff;
            bestEntry = { ...t1, dates: [t1.contact_date, t2.contact_date] };
            bestCount = totalCount;
          }
        }
      }
    }
  }
  
  if (!bestEntry) return null;

  return {
    planet: bestEntry.planet,
    natal_point: humanizeNatalPoint(bestEntry.natal_point),
    dates: bestEntry.dates,
    count: bestCount
  };
}

function getCautionAction(domain: string) {
  if (domain === "finance") return "making large investments or financial commitments";
  if (domain === "relationship") return "initiating major relationship changes or difficult conversations";
  return "signing or committing to major decisions";
}

function getCautionThemePhrase(engineOutput: any, domain: string) {
  const themes: string[] = engineOutput[`${domain}_themes`] || [];
  const challenging = themes.find(t => t.includes("instability") || t.includes("loss") || t.includes("friction") || t.includes("expense") || t.includes("delay"));
  if (challenging) {
    return challenging.split("(")[0].trim();
  }
  return `your ${domain}`;
}

export default function WindowCard({ idx, windowData, eventType, engineOutput }: WindowCardProps) {
  const [expanded, setExpanded] = useState(false);

  const isCaution = eventType === "caution";
  const title = isCaution ? "Watch-out window" : eventType === "advancement" ? "Advancement window" : "Steady-progress window";
  const dateStr = formatHumanDates(windowData.start_date, windowData.end_date);
  const peak = computePeak(windowData.triggers);
  const peakDateStr = peak ? formatHumanDates(peak.dates[0], peak.dates[1]) : "";
  const peakLine = peak ? `Peak: ${peakDateStr} — ${peak.planet} contacts your ${peak.natal_point}${peak.count > 1 ? ` (${peak.count}x)` : ""}` : "";

  const dotsCount = Math.min(windowData.trigger_count, 10);
  const hasMore = windowData.trigger_count > 10;
  
  const themePhrase = getCautionThemePhrase(engineOutput, windowData.domain);
  const cautionAction = getCautionAction(windowData.domain);
  
  // Sorted triggers for the expanded view
  const sortedTriggers = [...(windowData.triggers || [])].sort((a, b) => new Date(a.contact_date).getTime() - new Date(b.contact_date).getTime());

  if (isCaution) {
    return (
      <div id={`window-${idx}`} className="bg-[var(--clay)]/10 border border-[var(--clay)]/30 rounded-md p-4 transition-all">
        <div className="flex justify-between items-start cursor-pointer" onClick={() => setExpanded(!expanded)}>
          <div className="space-y-2">
            <div className="font-medium text-[var(--ivory)] flex items-center gap-2">
              <span className="text-[var(--clay)]">⚠</span> Watch-out: {dateStr}
            </div>
            <div className="text-sm text-[var(--ivory-soft)] leading-relaxed">
              Change or friction is possible around {themePhrase} in this window. If you can, avoid {cautionAction} in this window.
            </div>
            <div className="flex items-center gap-2 text-sm text-[var(--muted-on-dark)] pt-1">
              <div className="flex gap-1">
                {Array.from({ length: dotsCount }).map((_, i) => (
                  <div key={i} className="w-2 h-2 rounded-full bg-[var(--clay)]" />
                ))}
              </div>
              <span>({windowData.trigger_count} factors)</span>
            </div>
          </div>
          <div className="text-[var(--muted-on-dark)] p-1">
            {expanded ? "▲" : "▼"}
          </div>
        </div>

        {expanded && (
          <div className="mt-4 pt-4 border-t border-[var(--clay)]/20 space-y-4">
            <div>
              <div className="text-sm text-[var(--ivory)]">Window score: {windowData.window_score}</div>
              <div className="text-xs text-[var(--muted-on-dark)]">Sum of weighted planetary contacts in this window</div>
            </div>
            <div className="space-y-1">
              {sortedTriggers.map((t, i) => (
                <div key={i} className="text-xs font-[family-name:var(--font-mono)] text-[var(--ivory-soft)] grid grid-cols-[80px_1fr_auto] gap-2">
                  <span>{formatHumanDates(t.contact_date)}</span>
                  <span>{t.planet} → {humanizeNatalPoint(t.natal_point)}</span>
                  <span className="text-[var(--muted-on-dark)]">wt {t.weight}</span>
                </div>
              ))}
            </div>
            <div className="text-xs text-[var(--clay)]">
              Challenge house(s) involved in this window.
            </div>
            {windowData.pd_overlap && (
              <div className="text-xs px-2 py-1 bg-[var(--clay)]/20 text-[var(--clay)] rounded inline-block">
                Overlaps your current dasha sub-period
              </div>
            )}
            <div className="text-xs text-[var(--muted-on-dark)] font-[family-name:var(--font-mono)] mt-2">
              KP · transit scan
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div id={`window-${idx}`} className="bg-[var(--navy-raised)] border border-[var(--border)] rounded-md p-4 transition-all">
      <div className="flex justify-between items-start cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="space-y-2">
          <div className="font-medium text-[var(--ivory)] flex items-center gap-2">
            {eventType === "advancement" ? <span className="text-[var(--sage)]">✦</span> : <span className="text-[var(--gold)]">❖</span>}
            {title}
          </div>
          <div className="text-sm font-[family-name:var(--font-mono)] text-[var(--gold)]">
            {dateStr}
          </div>
          <div className="flex items-center gap-2 text-sm text-[var(--muted-on-dark)]">
            <div className="flex gap-1">
              {Array.from({ length: dotsCount }).map((_, i) => (
                <div key={i} className={`w-2 h-2 rounded-full ${eventType === "advancement" ? "bg-[var(--sage)]" : "bg-[var(--gold)]"}`} />
              ))}
              {hasMore && <span className="text-xs leading-none self-center ml-1">×N</span>}
            </div>
            <span>({windowData.trigger_count} factors converge)</span>
          </div>
          {peakLine && (
            <div className="text-sm text-[var(--ivory-soft)]">
              {peakLine}
            </div>
          )}
        </div>
        <div className="text-[var(--muted-on-dark)] p-1">
          {expanded ? "▲" : "▼"}
        </div>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-[var(--border)] space-y-4">
          <div>
            <div className="text-sm text-[var(--ivory)]">Window score: {windowData.window_score}</div>
            <div className="text-xs text-[var(--muted-on-dark)]">Sum of weighted planetary contacts in this window</div>
          </div>
          <div className="space-y-1">
            {sortedTriggers.map((t, i) => (
              <div key={i} className="text-xs font-[family-name:var(--font-mono)] text-[var(--ivory-soft)] grid grid-cols-[80px_1fr_auto] gap-2 border-b border-[var(--border)]/30 py-1 last:border-0">
                <span>{formatHumanDates(t.contact_date)}</span>
                <span>{t.planet} → {humanizeNatalPoint(t.natal_point)}</span>
                <span className="text-[var(--muted-on-dark)]">wt {t.weight}</span>
              </div>
            ))}
          </div>
          {windowData.pd_overlap && (
            <div className="text-xs px-2 py-1 bg-[var(--sage)]/20 text-[var(--sage)] rounded inline-block">
              Overlaps your current dasha sub-period
            </div>
          )}
          <div className="text-xs text-[var(--muted-on-dark)] font-[family-name:var(--font-mono)] mt-2">
            KP · transit scan
          </div>
        </div>
      )}
    </div>
  );
}
