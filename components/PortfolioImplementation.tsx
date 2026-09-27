"use client";

import React, { useMemo } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine, LineChart, Line
} from "recharts";
import type { SignalPoint, WeightPoint, RebalanceEvent } from "@/types/data";
import { fmtPct, fmtPctSigned, fmtDate } from "@/lib/formatters";

interface Props {
  signals: SignalPoint[];
  weights: WeightPoint[];
  rebalanceLog: RebalanceEvent[];
}

const ASSET_COLORS = {
  SHY: "#10b981",  // emerald
  IEF: "#f59e0b",  // amber
  TLT: "#ef4444",  // red
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-900/95 border border-slate-700 rounded-lg p-3 text-xs shadow-xl">
      <p className="text-slate-400 mb-2">{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex gap-2 mb-1">
          <span className="w-2 h-2 mt-0.5 rounded-full flex-shrink-0" style={{ backgroundColor: p.color }} />
          <span className="text-slate-300">{p.name}:</span>
          <span className="font-semibold" style={{ color: p.color }}>
            {fmtPct(p.value)}
          </span>
        </div>
      ))}
    </div>
  );
};

// Stacked area-style allocation chart using bars
function AllocationChart({ weights }: { weights: WeightPoint[] }) {
  // Already subsampled to weekly
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-300 mb-1">Portfolio Allocation Over Time</h3>
      <p className="text-xs text-slate-500 mb-4">
        Weekly snapshot of active weights. Weights sum to 100% at all times.
        Periods showing 100% SHY = fully defensive allocation.
      </p>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={weights} margin={{ top: 5, right: 10, left: 0, bottom: 5 }} barSize={4}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickFormatter={(d) => d?.slice(0, 7)}
            interval={Math.floor(weights.length / 8)}
          />
          <YAxis
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            domain={[0, 1]}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend formatter={(v) => <span style={{ color: "#94a3b8", fontSize: 11 }}>{v}</span>} />
          <Bar dataKey="SHY" name="SHY" stackId="a" fill={ASSET_COLORS.SHY} />
          <Bar dataKey="IEF" name="IEF" stackId="a" fill={ASSET_COLORS.IEF} />
          <Bar dataKey="TLT" name="TLT" stackId="a" fill={ASSET_COLORS.TLT} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// Signal chart: momentum values over time
function MomentumChart({ signals }: { signals: SignalPoint[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-300 mb-1">Monthly Momentum Signals</h3>
      <p className="text-xs text-slate-500 mb-4">
        60-day price momentum at each rebalance date. Positive momentum → asset eligible.
        Reference line at 0.
      </p>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={signals} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickFormatter={(d) => d?.slice(0, 7)}
            interval={Math.floor(signals.length / 8)}
          />
          <YAxis
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend formatter={(v) => <span style={{ color: "#94a3b8", fontSize: 11 }}>{v}</span>} />
          <ReferenceLine y={0} stroke="#475569" strokeWidth={1.5} strokeDasharray="3 3" />
          <Line type="monotone" dataKey="momentum_SHY" name="SHY Mom" stroke={ASSET_COLORS.SHY} dot={false} strokeWidth={1.5} />
          <Line type="monotone" dataKey="momentum_IEF" name="IEF Mom" stroke={ASSET_COLORS.IEF} dot={false} strokeWidth={1.5} />
          <Line type="monotone" dataKey="momentum_TLT" name="TLT Mom" stroke={ASSET_COLORS.TLT} dot={false} strokeWidth={1.5} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// Latest signal state
function LatestSignal({ signals }: { signals: SignalPoint[] }) {
  const latest = signals[signals.length - 1];
  if (!latest) return null;

  const eligibleColor = (v: boolean) => v ? "text-emerald-400" : "text-red-400";

  return (
    <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg p-5">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
        Latest Signal State — {latest.date}
      </p>
      <div className="grid grid-cols-3 gap-4">
        {(["SHY", "IEF", "TLT"] as const).map((t) => (
          <div key={t} className="text-center">
            <p className="text-sm font-semibold text-slate-300 mb-2">{t}</p>
            <div className={`text-xs font-bold uppercase tracking-wider mb-3 ${latest[`eligible_${t}`] ? "text-emerald-400" : "text-red-400"}`}>
              {latest[`eligible_${t}`] ? "ELIGIBLE" : "INELIGIBLE"}
            </div>
            <div className="space-y-1.5">
              <div>
                <p className="text-xs text-slate-500">Momentum</p>
                <p className={`text-sm font-mono tabular-nums ${latest[`momentum_${t}`]! > 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {fmtPctSigned(latest[`momentum_${t}`])}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Realized Vol</p>
                <p className="text-sm font-mono tabular-nums text-slate-200">
                  {fmtPct(latest[`rvol_${t}`])}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Target Weight</p>
                <p className="text-sm font-mono tabular-nums text-blue-400">
                  {fmtPct(latest[`weight_${t}`])}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
      {latest.is_defensive && (
        <div className="mt-4 p-2 bg-amber-900/30 border border-amber-700/40 rounded text-xs text-amber-400 text-center">
          Strategy is currently in FULLY DEFENSIVE mode → 100% SHY allocation
        </div>
      )}
    </div>
  );
}

// Rebalance log table
function RebalanceTable({ log }: { log: RebalanceEvent[] }) {
  const recent = log.slice(-20).reverse();
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-300 mb-1">
        Recent Rebalance Events (last 20)
      </h3>
      <p className="text-xs text-slate-500 mb-4">
        Signal date = when weights computed. Effective date = when weights applied (1-day lag).
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-700/50">
              {["Signal Date", "Eff. Date", "SHY", "IEF", "TLT", "Turnover", "TC Cost"].map((h) => (
                <th key={h} className="text-left text-slate-500 pb-2 pr-4 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {recent.map((row, i) => (
              <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                <td className="py-2 pr-4 text-slate-400 font-mono">{row.signal_date}</td>
                <td className="py-2 pr-4 text-slate-400 font-mono">{row.effective_date}</td>
                <td className="py-2 pr-4 tabular-nums" style={{ color: ASSET_COLORS.SHY }}>
                  {fmtPct(row.weight_SHY)}
                </td>
                <td className="py-2 pr-4 tabular-nums" style={{ color: ASSET_COLORS.IEF }}>
                  {fmtPct(row.weight_IEF)}
                </td>
                <td className="py-2 pr-4 tabular-nums" style={{ color: ASSET_COLORS.TLT }}>
                  {fmtPct(row.weight_TLT)}
                </td>
                <td className="py-2 pr-4 tabular-nums text-slate-300">
                  {fmtPct(row.turnover_oneway)}
                </td>
                <td className="py-2 pr-4 tabular-nums text-slate-400">
                  {row.tc_cost != null ? `${(row.tc_cost * 10000).toFixed(3)} bps` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function PortfolioImplementation({ signals, weights, rebalanceLog }: Props) {
  return (
    <section id="portfolio" className="py-16 px-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-semibold text-blue-400 uppercase tracking-widest">07</span>
          <span className="text-xs text-slate-500 uppercase tracking-widest">Portfolio Implementation</span>
        </div>
        <h2 className="text-2xl font-semibold text-slate-100">Portfolio Implementation</h2>
        <p className="text-slate-400 mt-2 text-sm max-w-2xl">
          Monthly rebalancing with a 1-day look-ahead lag. Weights determined by inverse-volatility
          sizing among momentum-eligible assets.
        </p>
      </div>

      <div className="space-y-8">
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-6">
          <LatestSignal signals={signals} />
        </div>
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-6">
          <AllocationChart weights={weights} />
        </div>
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-6">
          <MomentumChart signals={signals} />
        </div>
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-6 overflow-x-auto">
          <RebalanceTable log={rebalanceLog} />
        </div>
      </div>
    </section>
  );
}
