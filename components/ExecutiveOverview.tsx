"use client";

import React from "react";
import { fmtPct, fmtNumber, colorClass, fmtDate } from "@/lib/formatters";
import type { SummaryStats, MetaData } from "@/types/data";

interface Props {
  summary: SummaryStats;
  meta: MetaData;
}

function KpiCard({
  label,
  stratVal,
  benchVal,
  format = "pct",
  description,
  higherIsBetter = true,
}: {
  label: string;
  stratVal: number | null;
  benchVal: number | null;
  format?: "pct" | "number";
  description?: string;
  higherIsBetter?: boolean;
}) {
  const fmt = (v: number | null) =>
    v == null ? "—" : format === "pct" ? fmtPct(v) : fmtNumber(v, 4);

  const stratBetter =
    stratVal != null && benchVal != null
      ? higherIsBetter
        ? stratVal > benchVal
        : stratVal < benchVal
      : null;

  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-lg p-4 hover:border-slate-600/80 transition-colors">
      <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">{label}</p>
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs text-slate-500 mb-1">Strategy (Net)</p>
          <p
            className={`text-xl font-semibold tabular-nums ${
              stratBetter === true
                ? "text-emerald-400"
                : stratBetter === false
                ? "text-red-400"
                : "text-slate-100"
            }`}
          >
            {fmt(stratVal)}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500 mb-1">Benchmark</p>
          <p className="text-xl font-semibold tabular-nums text-slate-300">{fmt(benchVal)}</p>
        </div>
      </div>
      {description && (
        <p className="text-xs text-slate-500 mt-2 border-t border-slate-700/50 pt-2">{description}</p>
      )}
    </div>
  );
}

export default function ExecutiveOverview({ summary, meta }: Props) {
  const s = summary.strategy_net;
  const b = summary.benchmark;

  return (
    <section id="executive-overview" className="py-16 px-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-semibold text-blue-400 uppercase tracking-widest">02</span>
          <span className="text-xs text-slate-500 uppercase tracking-widest">Executive Overview</span>
        </div>
        <h2 className="text-2xl font-semibold text-slate-100">Historical Backtest Summary</h2>
        <p className="text-slate-400 mt-2 text-sm max-w-2xl">
          All statistics are computed from daily historical backtest data.{" "}
          <strong className="text-slate-300">
            These are backtested results, not live performance.
          </strong>{" "}
          Strategy (Net) reflects a 2 bps cost applied to traded notional.
          Benchmark is AGG (buy-and-hold, no costs).
        </p>
        <div className="mt-3 text-xs text-slate-500">
          Period:{" "}
          <span className="text-slate-300 font-mono">
            {meta.start_date} → {meta.end_date}
          </span>{" "}
          ({meta.trading_days.toLocaleString()} trading days)
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard
          label="Cumulative Return"
          stratVal={s.cumulative_return}
          benchVal={b.cumulative_return}
          description="Total compounded return over backtest period"
        />
        <KpiCard
          label="Ann. Return (CAGR)"
          stratVal={s.annualized_return}
          benchVal={b.annualized_return}
          description="Compound annual growth rate"
        />
        <KpiCard
          label="Ann. Volatility"
          stratVal={s.annualized_volatility}
          benchVal={b.annualized_volatility}
          higherIsBetter={false}
          description="Std dev of daily returns × √252"
        />
        <KpiCard
          label="Sharpe Ratio (Rf=0)"
          stratVal={s.sharpe_ratio}
          benchVal={b.sharpe_ratio}
          format="number"
          description="Mean daily excess return / daily standard deviation × √252. Risk-free rate = 0%"
        />
        <KpiCard
          label="Max Drawdown"
          stratVal={s.max_drawdown}
          benchVal={b.max_drawdown}
          higherIsBetter={false}
          description="Peak-to-trough decline"
        />
        <KpiCard
          label="Calmar Ratio"
          stratVal={s.calmar_ratio}
          benchVal={b.calmar_ratio}
          format="number"
          description="CAGR / |Max Drawdown|"
        />
        <KpiCard
          label="Win Rate"
          stratVal={s.win_rate}
          benchVal={b.win_rate}
          description="% of trading days with positive return"
        />
        <KpiCard
          label="Daily VaR (95%)"
          stratVal={s.var_95}
          benchVal={b.var_95}
          higherIsBetter={false}
          description="Historical 5th percentile of daily returns"
        />
      </div>

      {/* Relative stats */}
      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-5">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
          Relative to Benchmark (AGG)
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
          <div>
            <p className="text-xs text-slate-500 mb-1">Active Return (Ann.)</p>
            <p
              className={`text-lg font-semibold tabular-nums ${colorClass(
                summary.relative.annualized_active_return
              )}`}
            >
              {fmtPct(summary.relative.annualized_active_return)}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-500 mb-1">Tracking Error</p>
            <p className="text-lg font-semibold tabular-nums text-slate-200">
              {fmtPct(summary.relative.tracking_error)}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-500 mb-1">Information Ratio</p>
            <p
              className={`text-lg font-semibold tabular-nums ${colorClass(
                summary.relative.information_ratio
              )}`}
            >
              {fmtNumber(summary.relative.information_ratio, 4)}
            </p>
          </div>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="mt-4 p-3 bg-amber-900/20 border border-amber-700/40 rounded-lg">
        <p className="text-xs text-amber-400/80">
          <strong>Disclaimer:</strong> All results shown are historical backtest statistics based on
          public market data. Historical backtesting does not guarantee future performance. This
          project is not investment advice and is not affiliated with any investment firm. Results
          differ from live trading due to implementation costs, market impact, and real-world
          constraints not captured in backtests.
        </p>
      </div>
    </section>
  );
}
