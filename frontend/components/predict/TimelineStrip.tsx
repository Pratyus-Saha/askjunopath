"use client";
import React, { useMemo } from "react";

interface TimelineStripProps {
  asOf?: string;
  transitWindows?: Array<{
    start_date: string;
    end_date: string;
    type?: string;
  }>;
  eventTypes?: string[];
  pdWindow?: [string, string];
  pdLord?: string;
  nextContactDate?: string;
}

export default function TimelineStrip({
  asOf,
  transitWindows = [],
  pdWindow,
  pdLord,
  nextContactDate,
}: TimelineStripProps) {
  const asOfDate = asOf ? new Date(asOf) : new Date();
  const isValidDate = !isNaN(asOfDate.getTime());
  const endDate = new Date(asOfDate.getTime() + 90 * 24 * 60 * 60 * 1000);
  const totalMs = endDate.getTime() - asOfDate.getTime();
  const getPercent = (dateStr: string) => {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return 0;
    const pos = (d.getTime() - asOfDate.getTime()) / totalMs;
    return Math.max(0, Math.min(1, pos)) * 100;
  };
  const monthLabels = useMemo(() => {
    if (!isValidDate) return [];
    const labels = [];
    const curr = new Date(asOfDate);
    curr.setDate(1);
    curr.setMonth(curr.getMonth() + 1);
    curr.setHours(0, 0, 0, 0);
    while (curr <= endDate) {
      labels.push({
        label: curr.toLocaleString("en-US", { month: "short" }),
        pos: getPercent(curr.toISOString()),
      });
      curr.setMonth(curr.getMonth() + 1);
    }
    return labels;
  }, [asOfDate, endDate, isValidDate]);

  if (!isValidDate) {
    return null;
  }
  
  const getEventColor = (eventType?: string) => {
    if (!eventType) return "bg-[var(--gold)]";
    const lower = eventType.toLowerCase();
    if (lower.includes("advancement")) return "bg-[var(--sage)]";
    if (lower.includes("disruption") || lower.includes("caution")) return "bg-[var(--clay)]";
    if (lower.includes("progress")) return "bg-[var(--gold)]";
    return "bg-[var(--gold)]";
  };

  if (transitWindows.length === 0) {
    return (
      <div className="w-full mb-8 mt-4">
        <div className="relative w-full h-14 bg-[var(--navy-raised)] border border-[var(--border)] rounded-md mb-2">
          <div className="absolute top-0 bottom-0 left-0 w-px bg-[var(--gold)] z-10" />
          <div className="absolute top-[-20px] left-0 text-xs font-[family-name:var(--font-mono)] text-[var(--gold)]">
            Today
          </div>
          {monthLabels.map((m, idx) => (
            <div key={idx} className="absolute bottom-0 text-[10px] text-[var(--muted-on-dark)] translate-y-full -translate-x-1/2 pt-1" style={{ left: `${m.pos}%` }}>
              {m.label}
            </div>
          ))}
        </div>
        <p className="text-sm text-[var(--muted-on-dark)] mt-6">
          No strong contact windows in the next 90 days — the next estimated contact is {nextContactDate || "unknown"}.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full mb-8 mt-4">
      <div className="relative w-full h-14 bg-[var(--navy-raised)] border border-[var(--border)] rounded-md mb-2">
        {pdWindow && pdWindow.length === 2 && (
          <div 
            className="absolute top-0 bottom-0 bg-[var(--navy-deep)]/60 border-l border-r border-[var(--border)]/30 group"
            style={{
              left: `${getPercent(pdWindow[0])}%`,
              width: `${Math.max(0, getPercent(pdWindow[1]) - getPercent(pdWindow[0]))}%`
            }}
          >
             <div className="hidden group-hover:block absolute -top-8 left-1/2 -translate-x-1/2 bg-[var(--ink)] border border-[var(--border)] px-2 py-1 text-xs rounded text-[var(--ivory)] whitespace-nowrap z-20">
               {pdLord} PD
             </div>
          </div>
        )}

        {transitWindows.map((win, idx) => {
          const left = getPercent(win.start_date);
          let right = getPercent(win.end_date);
          if (right - left < 1) {
             right = left + 1;
          }
          let width = right - left;
          
          return (
            <div
              key={idx}
              onClick={() => {
                const el = document.getElementById(`window-${idx}`);
                if (el) el.scrollIntoView({ behavior: "smooth" });
              }}
              className={`absolute top-2 bottom-2 rounded cursor-pointer min-w-[8px] hover:opacity-80 transition-opacity z-10 ${getEventColor(win.type)}`}
              style={{
                left: `${left}%`,
                width: `${width}%`,
              }}
            />
          );
        })}

        <div className="absolute top-0 bottom-0 left-0 w-px bg-[var(--gold)] z-20" />
        <div className="absolute top-[-20px] left-0 text-xs font-[family-name:var(--font-mono)] text-[var(--gold)]">
          Today
        </div>

        {monthLabels.map((m, idx) => (
          <div key={idx} className="absolute bottom-0 text-[10px] text-[var(--muted-on-dark)] translate-y-full -translate-x-1/2 pt-1" style={{ left: `${m.pos}%` }}>
            {m.label}
          </div>
        ))}
      </div>
    </div>
  );
}
