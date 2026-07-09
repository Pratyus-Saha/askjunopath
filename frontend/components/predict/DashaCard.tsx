"use client";
import React from "react";
import Link from "next/link";

interface DashaCardProps {
  currentStack?: {
    mahadasha?: string;
    antardasha?: string;
    pratyantardasha?: string;
    mahadasha_window?: [string, string];
    antardasha_window?: [string, string];
    pratyantardasha_window?: [string, string];
  };
  dashaTiming?: {
    md_supports?: boolean;
    ad_supports?: boolean;
    pd_supports?: boolean;
  };
}

export default function DashaCard({ currentStack, dashaTiming }: DashaCardProps) {
  if (!currentStack || !dashaTiming) return null;

  const mdSupports = dashaTiming.md_supports ? 1 : 0;
  const adSupports = dashaTiming.ad_supports ? 1 : 0;
  const pdSupports = dashaTiming.pd_supports ? 1 : 0;
  const supportCount = mdSupports + adSupports + pdSupports;

  const renderRow = (label: string, lord: string | undefined, window?: [string, string]) => (
    <div className="flex flex-col md:flex-row md:items-center gap-1 md:gap-4 pb-3 border-b border-[var(--border)]/30 last:border-0 last:pb-0">
      <span className="text-[var(--muted-on-dark)] w-36">{label}:</span>
      <span className="text-[var(--gold)] font-medium text-lg">{lord || "-"}</span>
      <span className="text-[var(--muted-on-dark)] md:ml-auto">
        {window ? (
          <>
            (ends <span className="font-[family-name:var(--font-mono)]">{window[1]}</span>)
          </>
        ) : null}
      </span>
    </div>
  );

  return (
    <div className="bg-[var(--navy-raised)] p-6 rounded-md border border-[var(--border)] mt-8 space-y-4">
      <div className="flex justify-between items-center mb-4 border-b border-[var(--border)]/50 pb-2">
        <h3 className="text-xl font-[family-name:var(--font-serif)] text-[var(--ivory)]">Current Period (Dasha)</h3>
        <Link href="/chart/dasha" className="text-sm text-[var(--gold)] hover:text-[var(--gold-bright)] transition-colors">
          Full timeline &rarr;
        </Link>
      </div>

      <div className="space-y-4">
        {renderRow("Mahadasha", currentStack.mahadasha, currentStack.mahadasha_window)}
        {renderRow("Antardasha", currentStack.antardasha, currentStack.antardasha_window)}
        {renderRow("Pratyantardasha", currentStack.pratyantardasha, currentStack.pratyantardasha_window)}
      </div>

      <div className="mt-4 pt-3 border-t border-[var(--border)]/50 text-[var(--ivory-soft)]">
        <span className="font-medium text-[var(--gold)]">{supportCount}</span> of 3 period lords support this domain right now.
      </div>
    </div>
  );
}
