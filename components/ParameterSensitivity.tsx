"use client";

import React from "react";
import { fmtPct, fmtNumber } from "@/lib/formatters";
import type { SensitivityData } from "@/types/data";

export default function ParameterSensitivity({ data }: { data: SensitivityData }) {
  return (
    <section id="sensitivity" className="mx-auto max-w-7xl px-6 py-16">
      <div className="mb-8">
        <div className="mb-2 flex items-center gap-2"><span className="text-xs font-semibold uppercase tracking-widest text-blue-400">09</span><span className="text-xs uppercase tracking-widest text-slate-500">Parameter Sensitivity</span></div>
        <h2 className="text-2xl font-semibold text-slate-100">Pre-Specified Robustness Analysis</h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">{data.methodology.purpose}</p>
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-700/50 bg-slate-800/40 p-5"><p className="text-xs uppercase tracking-wider text-slate-500">Common comparison window</p><p className="mt-2 font-mono text-sm text-slate-200">{data.methodology.common_evaluation_start_date} → {data.methodology.common_evaluation_end_date}</p><p className="mt-2 text-xs leading-relaxed text-slate-500">{data.methodology.common_window_note}</p></div>
        <div className="rounded-xl border border-slate-700/50 bg-slate-800/40 p-5"><p className="text-xs uppercase tracking-wider text-slate-500">Interpretation</p><p className="mt-2 text-sm leading-relaxed text-slate-300">{data.interpretation.summary}</p></div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-700/50 bg-slate-800/40">
        <table className="min-w-[960px] w-full text-left text-xs">
          <thead className="border-b border-slate-700/60 bg-slate-900/40 text-slate-500"><tr>{["Momentum", "Volatility", "CAGR", "Ann. vol.", "Sharpe", "Max drawdown", "One-way turnover", "Rebalances", "Status"].map((heading) => <th key={heading} className="whitespace-nowrap px-4 py-3 font-medium">{heading}</th>)}</tr></thead>
          <tbody className="divide-y divide-slate-700/40">
            {data.results.map((row) => <tr key={row.configuration_id} className={row.is_baseline ? "bg-blue-950/30 text-slate-100" : "text-slate-300"}>
              <td className="px-4 py-3 tabular-nums">{row.parameters.momentum_window_days} days</td>
              <td className="px-4 py-3 tabular-nums">{row.parameters.volatility_window_days} days</td>
              <td className="px-4 py-3 tabular-nums text-blue-300">{fmtPct(row.metrics.cagr)}</td>
              <td className="px-4 py-3 tabular-nums">{fmtPct(row.metrics.annualized_volatility)}</td>
              <td className="px-4 py-3 tabular-nums">{fmtNumber(row.metrics.sharpe_ratio, 3)}</td>
              <td className="px-4 py-3 tabular-nums text-red-300">{fmtPct(row.metrics.maximum_drawdown)}</td>
              <td className="px-4 py-3 tabular-nums">{fmtNumber(row.metrics.total_one_way_turnover, 2)}</td>
              <td className="px-4 py-3 tabular-nums">{row.metrics.number_of_rebalances}</td>
              <td className="px-4 py-3">{row.is_baseline && <span className="rounded bg-blue-500/20 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-blue-300">Baseline</span>}</td>
            </tr>)}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-slate-500">The 60-day momentum / 20-day volatility row is highlighted because it was pre-specified as the baseline. No row is ranked or recommended.</p>
    </section>
  );
}
