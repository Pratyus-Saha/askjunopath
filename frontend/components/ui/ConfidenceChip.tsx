"use client";

import { useState, useRef, useEffect } from "react";

type Tier = "HIGH" | "MEDIUM" | "SPECULATIVE";

export default function ConfidenceChip({ tier }: { tier: Tier }) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const getTierColors = (t: Tier) => {
    switch (t) {
      case "HIGH":
        return "bg-sage/10 text-sage border-sage/30";
      case "MEDIUM":
        return "bg-gold/10 text-gold-soft border-gold/30"; // Using gold for medium
      case "SPECULATIVE":
        return "bg-clay/10 text-clay border-clay/30";
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        setOpen(false);
      }
    };
    
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };

    if (open) {
      window.addEventListener("keydown", handleKeyDown);
      window.addEventListener("click", handleClickOutside);
    }
    
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("click", handleClickOutside);
    };
  }, [open]);

  return (
    <div 
      className="relative inline-block" 
      ref={containerRef}
      onMouseEnter={() => window.matchMedia("(hover: hover)").matches && setOpen(true)}
      onMouseLeave={() => window.matchMedia("(hover: hover)").matches && setOpen(false)}
    >
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`inline-flex items-center px-2.5 py-0.5 rounded text-[11px] font-mono font-medium border ${getTierColors(tier)} focus:outline-none focus:ring-2 focus:ring-gold transition-colors cursor-pointer`}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        {tier}
      </button>

      {/* Popover */}
      {open && (
        <div 
          className="absolute z-50 mt-2 w-64 p-4 bg-surface border border-border rounded-lg shadow-lg text-left"
          role="dialog"
          aria-label="Confidence Tiers Explanation"
        >
          <h4 className="font-ui text-sm font-semibold text-text mb-2">Confidence Tiers</h4>
          <ul className="space-y-2 mb-3">
            <li className="flex items-center gap-2 text-xs font-mono">
              <span className="w-2 h-2 rounded-full bg-sage"></span>
              <span className="text-text">HIGH (85-100)</span>
            </li>
            <li className="flex items-center gap-2 text-xs font-mono">
              <span className="w-2 h-2 rounded-full bg-gold-soft"></span>
              <span className="text-text">MEDIUM (65-84)</span>
            </li>
            <li className="flex items-center gap-2 text-xs font-mono">
              <span className="w-2 h-2 rounded-full bg-clay"></span>
              <span className="text-text">SPECULATIVE (45-64)</span>
            </li>
          </ul>
          <p className="text-xs font-ui text-text-soft leading-relaxed border-t border-border/50 pt-2">
            JunoPath aims to publish how predictions hold up over time. Trust is earned by stating limits clearly.
          </p>
        </div>
      )}
    </div>
  );
}
