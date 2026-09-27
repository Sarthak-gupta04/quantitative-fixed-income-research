"use client";

import React, { useMemo } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Legend, ReferenceLine } from "recharts";
import { fmtDate, fmtPct } from "@/lib/formatters";
import type { RebalanceEvent, ResearcherViewData, SignalPoint } from "@/types/data";

interface Props {
  signals: SignalPoint[];
  rebalanceLog: RebalanceEvent[];
  researcherView: ResearcherViewData;
}

const assets = ["SHY", "IEF", "TLT"] as const;

function SignalTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ color: string; dataKey: string; name: string; value: number }>; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-950/95 p-3 text-xs shadow-xl">
      <p className="mb-2 text-slate-400">{fmtDate(label ?? "")}</p>
      {payload.map((item) => (
        <p key={item.dataKey} className="mb-1 flex gap-2" style={{ color: item.color }}>
          <span>{item.name}</span><span className="font-semibold tabular-nums">{fmtPct(item.value)}</span>
        </p>
      ))}
    </div>
  );
}

export default function SignalGeneration({ signals, rebalanceLog, researcherView }: Props) {
  const latest = researcherView.latest_signal;
  const history = useMemo(() => signals.slice(-48), [signals]);
  const transitions = useMemo(
    () => signals
      .map((signal, index) => ({ signal, previous: signals[index - 1] }))
      .filter(({ signal, previous }) => previous && signal.is_defensive !== previous.is_defensive)
      .slice(-6)
      .reverse(),
    [signals]
  );
  const recentRebalances = useMemo(() => rebalanceLog.slice(-6).reverse(), [rebalanceLog]);

  return (
    <section id="signals" className="mx-auto max-w-7xl px-6 py-16">
      <div className="mb-8">
        <div className="mb-2 flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-widest text-blue-400">06</span>
          <span className="text-xs uppercase tracking-widest text-slate-500">Signal Generation</span>
        </div>
        <h2 className="text-2xl font-semibold text-slate-100">Model Signal & Historical Strategy State</h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          At each month-end, the model measures 60-day momentum and 20-day realized volatility. IEF and TLT
          require positive momentum; eligible assets are sized by inverse volatility. If neither risk asset is
          eligible, the documented defensive allocation is SHY. These are historical model states, not recommendations.
        </p>
      </div>

      <div className="mb-8 grid gap-4 lg:grid-cols-[1.1fr_1.9fr]">
        <div className="rounded-xl border border-blue-500/30 bg-blue-950/20 p-5">
          <p className="text-xs font-semibold uppercase tracking-wider text-blue-300">Latest model signal</p>
          <p className="mt-2 text-lg font-semibold text-slate-100">{fmtDate(latest.signal_date)}</p>
          <p className="mt-2 text-xs leading-relaxed text-slate-400">
            {latest.is_fully_defensive ? "Fully defensive historical model state: SHY receives the target allocation." : "Risk assets remain eligible under the documented momentum rule."}
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {assets.map((asset) => (
            <div key={asset} className="rounded-xl border border-slate-700/50 bg-slate-800/40 p-4">
              <p className="text-xs font-medium text-slate-300">{asset}</p>
              <p className="mt-3 text-[11px] text-slate-500">60-day momentum</p>
              <p className="tabular-nums text-sm font-semibold text-slate-100">{fmtPct(latest.momentum[asset])}</p>
              <p className="mt-2 text-[11px] text-slate-500">20-day realized vol. (ann.)</p>
              <p className="tabular-nums text-sm font-semibold text-slate-100">{fmtPct(latest.realized_volatility[asset])}</p>
              <p className="mt-2 text-[11px] text-slate-500">Model allocation</p>
              <p className="tabular-nums text-sm font-semibold text-blue-300">{fmtPct(latest.target_weights[asset])}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-8">
        <div className="rounded-xl border border-slate-700/50 bg-slate-800/40 p-4 sm:p-6">
          <h3 className="text-sm font-semibold text-slate-200">Historical momentum at month-end signals</h3>
          <p className="mb-4 mt-1 text-xs text-slate-500">Latest 48 monthly observations. The zero line is the IEF/TLT eligibility threshold.</p>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={history} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 10 }} tickFormatter={(value) => value.slice(0, 7)} minTickGap={28} />
              <YAxis tick={{ fill: "#64748b", fontSize: 10 }} tickFormatter={(value) => `${(value * 100).toFixed(0)}%`} width={42} />
              <Tooltip content={<SignalTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
              <ReferenceLine y={0} stroke="#475569" />
              <Line type="monotone" dataKey="momentum_SHY" name="SHY" stroke="#60a5fa" dot={false} strokeWidth={1.6} />
              <Line type="monotone" dataKey="momentum_IEF" name="IEF" stroke="#f59e0b" dot={false} strokeWidth={1.6} />
              <Line type="monotone" dataKey="momentum_TLT" name="TLT" stroke="#a78bfa" dot={false} strokeWidth={1.6} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="grid gap-8 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-700/50 bg-slate-800/40 p-5">
            <h3 className="text-sm font-semibold text-slate-200">Recent signal transitions</h3>
            <p className="mb-4 mt-1 text-xs text-slate-500">Changes between fully defensive and non-defensive historical signal states.</p>
            <div className="space-y-3">
              {transitions.length ? transitions.map(({ signal, previous }) => (
                <div key={signal.date} className="flex items-start justify-between gap-4 border-b border-slate-700/40 pb-3 text-xs last:border-0">
                  <div><p className="font-mono text-slate-300">{fmtDate(signal.date)}</p><p className="mt-1 text-slate-500">{previous?.is_defensive ? "Defensive" : "Non-defensive"} → {signal.is_defensive ? "Defensive" : "Non-defensive"}</p></div>
                  <span className="rounded bg-slate-900 px-2 py-1 text-slate-400">SHY {fmtPct(signal.weight_SHY)}</span>
                </div>
              )) : <p className="text-xs text-slate-500">No observable state transitions are available.</p>}
            </div>
          </div>

          <div className="rounded-xl border border-slate-700/50 bg-slate-800/40 p-5">
            <h3 className="text-sm font-semibold text-slate-200">Recent effective rebalances</h3>
            <p className="mb-4 mt-1 text-xs text-slate-500">Weights take effect on the next available trading date.</p>
            <div className="space-y-3">
              {recentRebalances.map((event) => (
                <div key={event.effective_date} className="flex items-start justify-between gap-4 border-b border-slate-700/40 pb-3 text-xs last:border-0">
                  <div><p className="font-mono text-slate-300">Effective {fmtDate(event.effective_date)}</p><p className="mt-1 text-slate-500">Next signal: {fmtDate(event.next_signal_date ?? "")}</p></div>
                  <p className="tabular-nums text-slate-400">SHY {fmtPct(event.weight_SHY)} · IEF {fmtPct(event.weight_IEF)} · TLT {fmtPct(event.weight_TLT)}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
