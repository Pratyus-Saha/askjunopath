"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

export default function PredictLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [isMounted, setIsMounted] = useState(false);
  const [isValid, setIsValid] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    try {
      const stored = sessionStorage.getItem("ajp.chart.v1");
      if (!stored) {
        router.replace("/chart");
        return;
      }
      JSON.parse(stored); // validate JSON
      setIsValid(true);
    } catch (e) {
      router.replace("/chart");
    }
  }, [router]);

  if (!isMounted || !isValid) {
    return null; // Don't render blank state that could crash, just render nothing while redirecting
  }

  return (
    <div className="min-h-screen bg-[var(--navy)]">
      <div className="border-b border-[var(--gold-soft)] bg-[var(--navy-raised)]">
        <div className="max-w-4xl mx-auto px-4 md:px-8 py-3 flex items-center justify-between">
          <button
            onClick={() => router.push("/chart")}
            className="text-[var(--gold)] text-sm hover:text-[var(--gold-bright)] transition-colors flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Chart
          </button>

          <nav className="flex space-x-1 border border-[var(--gold-soft)] rounded-md p-1 bg-[var(--navy-deep)]">
            <Link
              href="/predict/career"
              className={`px-3 py-1.5 text-sm rounded transition-colors ${
                pathname === "/predict/career"
                  ? "bg-[var(--gold)] text-[var(--navy-deep)] font-medium"
                  : "text-[var(--muted-on-dark)] hover:text-[var(--ivory-soft)]"
              }`}
            >
              Career
            </Link>
            <Link
              href="/predict/finance"
              className={`px-3 py-1.5 text-sm rounded transition-colors ${
                pathname === "/predict/finance"
                  ? "bg-[var(--gold)] text-[var(--navy-deep)] font-medium"
                  : "text-[var(--muted-on-dark)] hover:text-[var(--ivory-soft)]"
              }`}
            >
              Finance
            </Link>
            <Link
              href="/predict/relationship"
              className={`px-3 py-1.5 text-sm rounded transition-colors ${
                pathname === "/predict/relationship"
                  ? "bg-[var(--gold)] text-[var(--navy-deep)] font-medium"
                  : "text-[var(--muted-on-dark)] hover:text-[var(--ivory-soft)]"
              }`}
            >
              Relationship
            </Link>
            <Link
              href="/chart/dasha"
              className="px-3 py-1.5 text-sm rounded transition-colors text-[var(--muted-on-dark)] hover:text-[var(--ivory-soft)]"
            >
              Dasha
            </Link>
          </nav>
        </div>
      </div>
      {children}
    </div>
  );
}
