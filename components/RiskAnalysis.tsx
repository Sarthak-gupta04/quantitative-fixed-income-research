"use client";

import React, { useMemo } from "react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { RollingMetricsPoint } from "@/types/data";
import { fmtPct, fmtNumber } from "@/lib/formatters";

interface Props {
  rollingMetrics: RollingMetricsPoint[];
}

function subsample<T>(arr: T[], every = 5): T[] {
  return arr.filter((_, i) => i % every === 0 || i === arr.length - 1);
}

const CustomTooltip = ({ active, payload, label, format = "pct" }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-900/95 border border-slate-700 rounded-lg p-3 text-xs shadow-xl">
      <p className="text-slate-400 mb-2">{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2 mb-1">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-slate-300">{p.name}:</span>
          <span className="font-semibold" style={{ color: p.color }}>
            {format === "pct" ? fmtPct(p.value) : fmtNumber(p.value, 2)}
          </span>
        </div>
      ))}
    </div>
  );
};

function DrawdownChart({ data }: { data: RollingMetricsPoint[] }) {
  const sampled = useMemo(() => subsample(data, 3), [data]);
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-300 mb-1">Drawdown</h3>
      <p className="text-xs text-slate-500 mb-4">
        Peak-to-trough decline from running maximum. A shallower drawdown indicates better
        capital preservation.
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={sampled} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <defs>
            <linearGradient id="stratDD" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="benchDD" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#94a3b8" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickFormatter={(d) => d?.slice(0, 7)}
            interval={Math.floor(sampled.length / 8)}
          />
          <YAxis
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            domain={["auto", 0]}
          />
          <Tooltip content={<CustomTooltip format="pct" />} />
          <Legend formatter={(v) => <span style={{ color: "#94a3b8", fontSize: 11 }}>{v}</span>} />
          <ReferenceLine y={0} stroke="#334155" />
          <Area
            type="monotone"
            dataKey="strategy_drawdown"
            name="Strategy (Net)"
            stroke="#3b82f6"
            fill="url(#stratDD)"
            dot={false}
            strokeWidth={1.5}
          />
          <Area
            type="monotone"
            dataKey="benchmark_drawdown"
            name="Benchmark (AGG)"
            stroke="#94a3b8"
            fill="url(#benchDD)"
            dot={false}
            strokeWidth={1.5}
            strokeDasharray="4 2"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function RollingVolChart({ data }: { data: RollingMetricsPoint[] }) {
  const sampled = useMemo(() => subsample(data, 5), [data]);
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-300 mb-1">
        Rolling 20-Day Realized Volatility (Annualized)
      </h3>
      <p className="text-xs text-slate-500 mb-4">
        σ(returns, 20-day) × √252. Captures short-term volatility regimes.
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={sampled} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickFormatter={(d) => d?.slice(0, 7)}
            interval={Math.floor(sampled.length / 8)}
          />
          <YAxis
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickFormatter={(v) => `${(v * 100).toFixed(1)}%`}
          />
          <Tooltip content={<CustomTooltip format="pct" />} />
          <Legend formatter={(v) => <span style={{ color: "#94a3b8", fontSize: 11 }}>{v}</span>} />
          <Line type="monotone" dataKey="SHY_rolling_vol" name="SHY" stroke="#10b981" dot={false} strokeWidth={1.5} />
          <Line type="monotone" dataKey="IEF_rolling_vol" name="IEF" stroke="#f59e0b" dot={false} strokeWidth={1.5} />
          <Line type="monotone" dataKey="TLT_rolling_vol" name="TLT" stroke="#ef4444" dot={false} strokeWidth={1.5} />
          <Line type="monotone" dataKey="benchmark_rolling_vol" name="AGG (Benchmark)" stroke="#94a3b8" dot={false} strokeWidth={1} strokeDasharray="4 2" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function RollingSharpeChart({ data }: { data: RollingMetricsPoint[] }) {
  const sampled = useMemo(() => subsample(data, 5), [data]);
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-300 mb-1">
        Rolling 252-Day Sharpe Ratio
      </h3>
      <p className="text-xs text-slate-500 mb-4">
        Rolling 1-year Sharpe ratio. Risk-free rate = 0%. Values fluctuate significantly over
        short windows — interpret with caution.
      </p>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={sampled} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickFormatter={(d) => d?.slice(0, 7)}
            interval={Math.floor(sampled.length / 8)}
          />
          <YAxis tick={{ fill: "#64748b", fontSize: 10 }} tickFormatter={(v) => v.toFixed(1)} />
          <Tooltip content={<CustomTooltip format="number" />} />
          <Legend formatter={(v) => <span style={{ color: "#94a3b8", fontSize: 11 }}>{v}</span>} />
          <ReferenceLine y={0} stroke="#334155" />
          <Line
            type="monotone"
            dataKey="strategy_rolling_sharpe"
            name="Strategy (Net)"
            stroke="#3b82f6"
            dot={false}
            strokeWidth={2}
          />
          <Line
            type="monotone"
            dataKey="benchmark_rolling_sharpe"
            name="Benchmark (AGG)"
            stroke="#94a3b8"
            dot={false}
            strokeWidth={1.5}
            strokeDasharray="4 2"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function RiskAnalysis({ rollingMetrics }: Props) {
  return (
    <section id="risk-analysis" className="py-16 px-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-semibold text-blue-400 uppercase tracking-widest">05</span>
          <span className="text-xs text-slate-500 uppercase tracking-widest">Risk Analysis</span>
        </div>
        <h2 className="text-2xl font-semibold text-slate-100">Risk Analysis</h2>
        <p className="text-slate-400 mt-2 text-sm max-w-2xl">
          The strategy targets lower volatility through its inverse-volatility position-sizing rule.
          The trade-off is potentially lower absolute return versus the benchmark.
        </p>
      </div>

      <div className="space-y-8">
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-6">
          <DrawdownChart data={rollingMetrics} />
        </div>
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-6">
          <RollingVolChart data={rollingMetrics} />
        </div>
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-6">
          <RollingSharpeChart data={rollingMetrics} />
        </div>
      </div>
    </section>
  );
}
