// Presentation-only selection helpers. Never recompute research results here.
export const ASSETS = ["SHY", "IEF", "TLT"] as const;
export const ASSET_COLORS = { SHY: "#768da4", IEF: "#45a6b5", TLT: "#1768e5" };
export type Asset = (typeof ASSETS)[number];

export function isObservationDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

export function observationAtOrBefore<T extends { date: string }>(points: readonly T[], date: string): T | undefined {
  let low = 0;
  let high = points.length - 1;
  let found = -1;
  while (low <= high) {
    const middle = Math.floor((low + high) / 2);
    if (points[middle].date <= date) { found = middle; low = middle + 1; }
    else high = middle - 1;
  }
  return found < 0 ? undefined : points[found];
}

export function sampleWithSelection<T extends { date: string }>(points: T[], date: string, step = 5): T[] {
  const selected = observationAtOrBefore(points, date);
  return points.filter((point, index) => index % step === 0 || index === points.length - 1 || point === selected);
}

export interface ResearchView {
  date: string;
  period: string;
  curve: string;
  compare: string;
  shock: number;
  allocation: "current_model_target" | "latest_effective";
  config: string;
}

export function restoreView(params: URLSearchParams, defaults: ResearchView, valid: {
  first: string; last: string; periods: string[]; curves: string[]; shocks: number[]; configs: string[];
}): ResearchView {
  const date = params.get("date") ?? "";
  const shock = Number(params.get("shock"));
  return {
    date: isObservationDate(date) && date >= valid.first && date <= valid.last ? date : defaults.date,
    period: valid.periods.includes(params.get("period") ?? "") ? params.get("period")! : defaults.period,
    curve: valid.curves.includes(params.get("curve") ?? "") ? params.get("curve")! : defaults.curve,
    compare: valid.curves.includes(params.get("compare") ?? "") ? params.get("compare")! : defaults.compare,
    shock: params.has("shock") && valid.shocks.includes(shock) ? shock : defaults.shock,
    allocation: params.get("allocation") === "latest_effective" ? "latest_effective" : defaults.allocation,
    config: valid.configs.includes(params.get("config") ?? "") ? params.get("config")! : defaults.config,
  };
}

export function serializeView(view: ResearchView, url: URL): URL {
  for (const [key, value] of Object.entries(view)) {
    if (value === "") url.searchParams.delete(key);
    else url.searchParams.set(key, String(value));
  }
  return url;
}
