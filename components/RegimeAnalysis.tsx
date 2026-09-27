"use client";

import React from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtPct } from "@/lib/formatters";
import type { RegimeAnalysisData } from "@/types/data";

export default function RegimeAnalysis({ data }: { data: RegimeAnalysisData }) {
  return (
    <section id="regime-analysis" className="mx-auto max-w-7xl px-6 py-16">
      <div className="mb-8">
        <div className="mb-2 flex items-center gap-2"><span className="text-xs font-semibold uppercase tracking-widest text-blue-400">08</span><span className="text-xs uppercase tracking-widest text-slate-500">Market Regime Analysis</span></div>
        <h2 className="text-2xl font-semibold text-slate-100">Historical Period Analysis</h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">{data.methodology.period_definition} {data.methodology.naming_note}</p>
      </div>
      <div className="mb-8 rounded-xl border border-slate-700/50 bg-slate-800/40 p-4 sm:p-6">
        <h3 className="mb-1 text-sm font-semibold text-slate-200">Compounded return by historical period</h3>
        <p className="mb-4 text-xs text-slate-500">Strategy net return and buy-and-hold AGG return; periods are not ranked.</p>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data.periods} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
            <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 10 }} tickFormatter={(value) => value.replace(" period", "")} />
            <YAxis tick={{ fill: "#64748b", fontSize: 10 }} tickFormatter={(value) => `${(value * 100).toFixed(0)}%`} width={42} />
            <Tooltip formatter={(value) => fmtPct(Number(value))} contentStyle={{ background: "#020617", border: "1px solid #334155", borderRadius: 8, fontSize: 12 }} />
            <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
            <Bar dataKey="strategy_return" name="Strategy (Net)" fill="#3b82f6" radius={[3, 3, 0, 0]} />
            <Bar dataKey="benchmark_return" name="AGG" fill="#94a3b8" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="overflow-x-auto rounded-xl border border-slate-700/50 bg-slate-800/40">
        <table className="min-w-[920px] w-full text-left text-xs">
          <thead className="border-b border-slate-700/60 bg-slate-900/40 text-slate-500"><tr>{["Period", "Strategy", "AGG", "Strategy vol.", "AGG vol.", "Strategy max DD", "Avg. SHY", "Fully defensive", "Rebalances"].map((heading) => <th key={heading} className="whitespace-nowrap px-4 py-3 font-medium">{heading}</th>)}</tr></thead>
          <tbody className="divide-y divide-slate-700/40">
            {data.periods.map((period) => <tr key={period.id} className="text-slate-300"><td className="px-4 py-3 font-medium">{period.label}</td><td className="px-4 py-3 tabular-nums text-blue-300">{fmtPct(period.strategy_return)}</td><td className="px-4 py-3 tabular-nums">{fmtPct(period.benchmark_return)}</td><td className="px-4 py-3 tabular-nums">{fmtPct(period.strategy_annualized_volatility)}</td><td className="px-4 py-3 tabular-nums">{fmtPct(period.benchmark_annualized_volatility)}</td><td className="px-4 py-3 tabular-nums text-red-300">{fmtPct(period.strategy_maximum_drawdown)}</td><td className="px-4 py-3 tabular-nums">{fmtPct(period.defensive_shy_allocation.average_weight)}</td><td className="px-4 py-3 tabular-nums">{fmtPct(period.defensive_shy_allocation.fully_defensive_fraction)}</td><td className="px-4 py-3 tabular-nums">{period.number_of_rebalances}</td></tr>)}
          </tbody>
        </table>
      </div>
    </section>
  );
}
