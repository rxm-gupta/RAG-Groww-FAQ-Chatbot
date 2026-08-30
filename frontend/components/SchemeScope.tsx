"use client";

import { useState } from "react";

const SCHEME_PILLS = [
  "HDFC Flexi Cap Fund",
  "HDFC Small Cap Fund",
  "HDFC Large and Mid Cap Fund",
  "HDFC Nifty 50 Index Fund",
  "HDFC ELSS Tax Saver Fund",
];

export function SchemeScope() {
  const [open, setOpen] = useState(false);

  return (
    <section>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex items-center gap-2 rounded-md border border-line px-3 py-2 text-left text-sm text-muted transition-colors hover:border-groww-green hover:text-ink"
      >
        Covers 5 HDFC schemes
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {open && (
        <div className="mt-2 flex flex-wrap gap-2">
          {SCHEME_PILLS.map((pill) => (
            <span key={pill} className="rounded-full border border-line bg-surface px-2.5 py-1 text-xs text-muted">
              {pill}
            </span>
          ))}
        </div>
      )}
    </section>
  );
}
