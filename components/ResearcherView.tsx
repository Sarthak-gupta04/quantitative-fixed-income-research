"use client";

import React from "react";
import { fmtDate, fmtPct } from "@/lib/formatters";
import type { ResearcherViewData } from "@/types/data";

const assets = ["SHY", "IEF", "TLT"] as const;

export default function ResearcherView({ data }: { data: ResearcherViewData }) {
  const signal = data.latest_signal;
  const allocation = data.latest_effective_allocation;
  const risk = data.recent_realized_risk;
  return (
    <section id="researcher-view" className="mx-auto max-w-7xl px-6 py-16">
      <div className="mb-8">
        <div className="mb-2 flex items-center gap-2"><span className="text-xs font-semibold uppercase tracking-widest text-blue-400">10</span><span className="text-xs uppercase tracking-widest text-slate-500">Researcher&apos;s View</span></div>
        <h2 className="text-2xl font-semibold text-slate-100">Latest Calculated Strategy State</h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">Based on the latest available observation. This is a factual summary of the historical model state, not investment advice or a forecast.</p>
      </div>

      <div className="rounded-xl border border-blue-500/30 bg-blue-950/20 p-5 sm:p-6">
        <div className="flex flex-col justify-between gap-4 border-b border-blue-400/15 pb-5 md:flex-row md:items-start">
          <div><p className="text-xs font-semibold uppercase tracking-wider text-blue-300">Current model allocation</p><p className="mt-2 text-xl font-semibold text-slate-100">{signal.is_fully_defensive ? "100% SHY — fully defensive state" : "Momentum-eligible inverse-volatility allocation"}</p></div>
          <div className="text-left text-xs text-slate-400 md:text-right"><p>Latest data date: <span className="font-mono text-slate-200">{fmtDate(risk.date)}</span></p><p className="mt-1">Latest signal date: <span className="font-mono text-slate-200">{fmtDate(signal.signal_date)}</span></p><p className="mt-1">Effective allocation date: <span className="font-mono text-slate-200">{fmtDate(allocation.date)}</span></p></div>
        </div>
        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          <div className="rounded-lg border border-slate-700/50 bg-slate-950/30 p-4"><p className="text-xs font-medium text-slate-300">Latest signal inputs</p>{assets.map((asset) => <div key={asset} className="mt-3 grid grid-cols-3 gap-2 text-xs"><span className="font-medium text-slate-300">{asset}</span><span className="tabular-nums text-slate-400">Mom. {fmtPct(signal.momentum[asset])}</span><span className="tabular-nums text-slate-400">Vol. {fmtPct(signal.realized_volatility[asset])}</span></div>)}</div>
          <div className="rounded-lg border border-slate-700/50 bg-slate-950/30 p-4"><p className="text-xs font-medium text-slate-300">Target / effective allocation</p>{assets.map((asset) => <div key={asset} className="mt-3 flex justify-between text-xs"><span className="text-slate-400">{asset}</span><span className="tabular-nums text-slate-200">{fmtPct(signal.target_weights[asset])} / {fmtPct(allocation.weights[asset])}</span></div>)}</div>
          <div className="rounded-lg border border-slate-700/50 bg-slate-950/30 p-4"><p className="text-xs font-medium text-slate-300">Recent realized risk</p><p className="mt-3 text-xs text-slate-400">20-day rolling vol. (ann.) <span className="float-right tabular-nums text-slate-200">{fmtPct(risk.strategy_rolling_volatility)}</span></p><p className="mt-3 text-xs text-slate-400">Current strategy drawdown <span className="float-right tabular-nums text-red-300">{fmtPct(risk.strategy_drawdown)}</span></p><p className="mt-3 text-xs text-slate-400">AGG rolling vol. <span className="float-right tabular-nums text-slate-200">{fmtPct(risk.benchmark_rolling_volatility)}</span></p></div>
        </div>
        {data.latest_observable_rebalance && <p className="mt-5 text-xs text-slate-500">Latest observable rebalance: signal {fmtDate(data.latest_observable_rebalance.signal_date)} → effective {fmtDate(data.latest_observable_rebalance.effective_date)}. Trading notional: {fmtPct(data.latest_observable_rebalance.trading_notional)}.</p>}
      </div>
    </section>
  );
}
