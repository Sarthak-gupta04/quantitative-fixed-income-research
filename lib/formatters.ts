// lib/formatters.ts
// ==================
// Utility functions for formatting numbers and dates in the dashboard.

export const fmtPct = (v: number | null | undefined, decimals = 2): string => {
  if (v == null || isNaN(v)) return "—";
  return `${(v * 100).toFixed(decimals)}%`;
};

export const fmtPctSigned = (v: number | null | undefined, decimals = 2): string => {
  if (v == null || isNaN(v)) return "—";
  const pct = (v * 100).toFixed(decimals);
  return v >= 0 ? `+${pct}%` : `${pct}%`;
};

export const fmtNumber = (v: number | null | undefined, decimals = 2): string => {
  if (v == null || isNaN(v)) return "—";
  return v.toFixed(decimals);
};

export const fmtBps = (v: number | null | undefined): string => {
  if (v == null || isNaN(v)) return "—";
  return `${(v * 10000).toFixed(1)} bps`;
};

export const fmtDate = (dateStr: string): string => {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

export const fmtDateShort = (dateStr: string): string => {
  if (!dateStr) return "—";
  return dateStr.slice(0, 7); // "YYYY-MM"
};

export const fmtNav = (v: number | null | undefined): string => {
  if (v == null || isNaN(v)) return "—";
  return v.toFixed(4);
};

export const colorClass = (v: number | null | undefined): string => {
  if (v == null) return "text-slate-400";
  return v >= 0 ? "text-emerald-400" : "text-red-400";
};

export const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];
