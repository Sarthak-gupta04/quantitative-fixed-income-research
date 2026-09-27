"use client";

import React, { useMemo } from "react";
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  ReferenceLine,
  Area,
} from "recharts";
import type { NavDataPoint, AnnualReturn, MonthlyReturn, RollingMetricsPoint } from "@/types/data";
import { fmtPct, fmtPctSigned, MONTH_NAMES } from "@/lib/formatters";

interface Props {
  nav: NavDataPoint[];
  annualReturns: AnnualReturn[];
  monthlyReturns: MonthlyReturn[];
  rollingMetrics: RollingMetricsPoint[];
}

// Subsample data for performance
function subsample<T>(arr: T[], every = 5): T[] {
  return arr.filter((_, i) => i % every === 0 || i === arr.length - 1);
}

const STRATEGY_COLOR = "#3b82f6"; // blue-500
const BENCHMARK_COLOR = "#94a3b8"; // slate-400
const GROSS_COLOR = "#60a5fa"; // blue-400

// Custom tooltip style
const CustomTooltip = ({ active, payload, label, format = "pct" }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-900/95 border border-slate-700 rounded-lg p-3 text-xs shadow-xl">
      <p className="text-slate-400 mb-2 font-medium">{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2 mb-1">
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: p.color }} />
          <span className="text-slate-300">{p.name}:</span>
          <span className="font-semibold tabular-nums" style={{ color: p.color }}>
            {format === "nav"
              ? p.value?.toFixed(4)
              : format === "pct"
              ? fmtPct(p.value)
              : fmtPctSigned(p.value)}
          </span>
        </div>
      ))}
    </div>
  );
};

// Cumulative NAV chart
function NavChart({ nav }: { nav: NavDataPoint[] }) {
  const data = useMemo(() => subsample(nav, 3), [nav]);
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-300 mb-1">Cumulative Wealth Index (NAV)</h3>
      <p className="text-xs text-slate-500 mb-4">Starting value = 1.0. Includes reinvested dividends (adjusted prices).</p>
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickFormatter={(d) => d?.slice(0, 7)}
            interval={Math.floor(data.length / 8)}
          />
          <YAxis
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickFormatter={(v) => v?.toFixed(2)}
            domain={["auto", "auto"]}
          />
          <Tooltip content={<CustomTooltip format="nav" />} />
          <Legend
            formatter={(v) => <span style={{ color: "#94a3b8", fontSize: 11 }}>{v}</span>}
          />
          <Line
            type="monotone"
            dataKey="strategy_net"
            name="Strategy (Net)"
            stroke={STRATEGY_COLOR}
            dot={false}
            strokeWidth={2}
          />
          <Line
            type="monotone"
            dataKey="benchmark"
            name="Benchmark (AGG)"
            stroke={BENCHMARK_COLOR}
            dot={false}
            strokeWidth={1.5}
            strokeDasharray="4 2"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

// Annual returns bar chart
function AnnualReturnsChart({ data }: { data: AnnualReturn[] }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-300 mb-1">Annual Returns</h3>
      <p className="text-xs text-slate-500 mb-4">Calendar-year compounded returns.</p>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="year" tick={{ fill: "#64748b", fontSize: 10 }} />
          <YAxis
            tick={{ fill: "#64748b", fontSize: 10 }}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
          />
          <Tooltip content={<CustomTooltip format="signed" />} />
          <Legend
            formatter={(v) => <span style={{ color: "#94a3b8", fontSize: 11 }}>{v}</span>}
          />
          <ReferenceLine y={0} stroke="#334155" strokeWidth={1} />
          <Bar dataKey="strategy_net" name="Strategy (Net)" fill={STRATEGY_COLOR} opacity={0.85} radius={[2, 2, 0, 0]} />
          <Bar dataKey="benchmark" name="Benchmark (AGG)" fill={BENCHMARK_COLOR} opacity={0.7} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// Monthly returns heatmap
function MonthlyHeatmap({ data }: { data: MonthlyReturn[] }) {
  // Build a year → month → return map
  const yearMap = useMemo(() => {
    const map: Record<number, Record<number, number | null>> = {};
    for (const row of data) {
      if (!map[row.year]) map[row.year] = {};
      map[row.year][row.month] = row.return;
    }
    return map;
  }, [data]);

  const years = Object.keys(yearMap)
    .map(Number)
    .sort((a, b) => b - a);

  const getColor = (v: number | null) => {
    if (v == null) return "bg-slate-800";
    if (v > 0.02) return "bg-emerald-600";
    if (v > 0.01) return "bg-emerald-700";
    if (v > 0) return "bg-emerald-900";
    if (v > -0.01) return "bg-red-900";
    if (v > -0.02) return "bg-red-700";
    return "bg-red-600";
  };

  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-300 mb-1">Monthly Returns Heatmap — Strategy (Net)</h3>
      <p className="text-xs text-slate-500 mb-4">Green = positive, red = negative. Each cell = one calendar month.</p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr>
              <th className="text-left text-slate-500 pr-3 pb-2 font-normal w-12">Year</th>
              {MONTH_NAMES.map((m) => (
                <th key={m} className="text-center text-slate-500 pb-2 font-normal min-w-[36px]">
                  {m}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {years.map((year) => (
              <tr key={year}>
                <td className="text-slate-400 pr-3 py-0.5 font-mono">{year}</td>
                {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => {
                  const v = yearMap[year]?.[month] ?? null;
                  return (
                    <td key={month} className="px-0.5 py-0.5">
                      <div
                        className={`${getColor(v)} rounded text-center py-1 tabular-nums`}
                        title={v != null ? `${(v * 100).toFixed(2)}%` : "N/A"}
                      >
                        <span className="text-slate-200 text-[9px]">
                          {v != null ? `${(v * 100).toFixed(1)}` : ""}
                        </span>
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function PerformanceSection({ nav, annualReturns, monthlyReturns, rollingMetrics }: Props) {
  return (
    <section id="performance" className="py-16 px-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-semibold text-blue-400 uppercase tracking-widest">04</span>
          <span className="text-xs text-slate-500 uppercase tracking-widest">Performance</span>
        </div>
        <h2 className="text-2xl font-semibold text-slate-100">Performance Analysis</h2>
        <p className="text-slate-400 mt-2 text-sm">
          Historical backtest performance versus the AGG benchmark. All returns are total-return proxies
          using adjusted prices (dividends reinvested).
        </p>
      </div>

      <div className="space-y-10">
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-6">
          <NavChart nav={nav} />
        </div>
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-6">
          <AnnualReturnsChart data={annualReturns} />
        </div>
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-6 overflow-x-auto">
          <MonthlyHeatmap data={monthlyReturns} />
        </div>
      </div>
    </section>
  );
}
