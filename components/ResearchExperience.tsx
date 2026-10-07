"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { DashboardData, RebalanceEvent } from "@/types/data";
import { observationAtOrBefore, restoreView, serializeView, type ResearchView } from "@/lib/research-view";

interface Experience {
  view: ResearchView;
  update: (next: Partial<ResearchView>) => void;
  selectDate: (date: string) => void;
  selectPeriod: (id: string) => void;
  data: DashboardData;
  rebalances: RebalanceEvent[];
  period: DashboardData["regimeAnalysis"]["periods"][number] | undefined;
  share: () => Promise<void>;
  shareStatus: string;
}
const Context = createContext<Experience | null>(null);

export function ResearchExperience({ data, children }: { data: DashboardData; children: React.ReactNode }) {
  const defaults = useMemo<ResearchView>(() => ({
    date: data.rebalances.at(-1)?.signal_date ?? data.meta.end_date,
    period: "", curve: data.yieldCurve.monthly_series.at(-1)?.date ?? "", compare: "",
    shock: 50, allocation: "current_model_target", config: data.sensitivity.methodology.baseline_configuration_id,
  }), [data]);
  const [view, setView] = useState(defaults);
  const [shareStatus, setShareStatus] = useState("");
  // Do not serialize defaults before URL restoration finishes (including Strict Mode replay).
  const [hydrated, setHydrated] = useState(false);
  const statusTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => {
    const read = () => {
      const restored = restoreView(new URLSearchParams(window.location.search), defaults, {
        first: data.meta.start_date, last: data.meta.end_date,
        periods: data.regimeAnalysis.periods.map(p => p.id), curves: data.yieldCurve.monthly_series.map(p => p.date),
        shocks: data.rateShock.allocations.current_model_target.scenarios.map(s => s.shock_bps),
        configs: data.sensitivity.results.map(r => r.configuration_id),
      });
      const period = data.regimeAnalysis.periods.find(p => p.id === restored.period);
      if (period && (restored.date < period.actual_start_date || restored.date > period.actual_end_date)) restored.date = period.actual_end_date;
      setView(restored);
      setHydrated(true);
    };
    read();
    window.addEventListener("popstate", read);
    return () => { window.removeEventListener("popstate", read); clearTimeout(statusTimer.current); };
  }, [data, defaults]);
  const update = useCallback((next: Partial<ResearchView>) => {
    setView(current => {
      const updated = { ...current, ...next };
      return updated;
    });
  }, []);
  useEffect(() => {
    if (hydrated) window.history.replaceState(null, "", serializeView(view, new URL(window.location.href)));
  }, [view, hydrated]);
  const period = data.regimeAnalysis.periods.find(p => p.id === view.period);
  const selectDate = useCallback((date: string) => {
    const clamped = date < data.meta.start_date ? data.meta.start_date : date > data.meta.end_date ? data.meta.end_date : date;
    setView(current => {
      const period = data.regimeAnalysis.periods.find(p => p.id === current.period);
      return { ...current, date: clamped, period: period && clamped >= period.actual_start_date && clamped <= period.actual_end_date ? current.period : "" };
    });
  }, [data]);
  const selectPeriod = useCallback((id: string) => {
    const selected = data.regimeAnalysis.periods.find(p => p.id === id);
    update({ period: selected?.id ?? "", date: selected?.actual_end_date ?? defaults.date });
  }, [data, defaults, update]);
  const share = useCallback(async () => {
    const url = serializeView(view, new URL(window.location.href)).toString();
    try {
      await navigator.clipboard.writeText(url);
      setShareStatus("View link copied");
    } catch {
      setShareStatus("Copy this view’s URL from your address bar");
    }
    clearTimeout(statusTimer.current);
    statusTimer.current = setTimeout(() => setShareStatus(""), 4500);
  }, [view]);
  const value = useMemo(() => ({ view, update, selectDate, selectPeriod, data, rebalances: data.rebalances, period, share, shareStatus }), [view, update, selectDate, selectPeriod, data, period, share, shareStatus]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useResearch() {
  const context = useContext(Context);
  if (!context) throw new Error("Research view requires ResearchExperience");
  return context;
}

export function useSelectedResearch() {
  const { data, view } = useResearch();
  return useMemo(() => {
    const nav = observationAtOrBefore(data.nav, view.date);
    const risk = observationAtOrBefore(data.rollingMetrics, view.date);
    const weights = observationAtOrBefore(data.weights, view.date);
    const signal = observationAtOrBefore(data.signals, view.date);
    const rebalance = observationAtOrBefore(data.rebalances.map(r => ({ ...r, date: r.signal_date })), view.date);
    return { nav, risk, weights, signal, rebalance };
  }, [data, view.date]);
}
