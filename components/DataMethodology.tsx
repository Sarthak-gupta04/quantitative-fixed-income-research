"use client";

import React from "react";
import type { MetaData } from "@/types/data";

interface Props {
  meta: MetaData;
}

export default function DataMethodology({ meta }: Props) {
  return (
    <section id="methodology" className="py-16 px-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-semibold text-blue-400 uppercase tracking-widest">08</span>
          <span className="text-xs text-slate-500 uppercase tracking-widest">Data & Methodology</span>
        </div>
        <h2 className="text-2xl font-semibold text-slate-100">Data & Methodology</h2>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        <div className="space-y-6">
          <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">Data Specification</h3>
            <table className="w-full text-xs">
              <tbody className="divide-y divide-slate-700/40">
                {[
                  ["Source", "Yahoo Finance (yfinance)"],
                  ["Tickers", meta.tickers.join(", ")],
                  ["Benchmark", meta.benchmark],
                  ["Raw price start", meta.raw_price_start_date ?? "—"],
                  ["Indicator warm-up", meta.indicator_warmup_trading_days != null ? `${meta.indicator_warmup_trading_days} trading days` : "—"],
                  ["Comparative return start", meta.first_investable_date ?? meta.start_date],
                  ["NAV base date", meta.nav_base_date ?? "—"],
                  ["Evaluation end", meta.end_date],
                  ["Frequency", "Daily"],
                  ["Price Field", "Adj Close (dividends reinvested, splits adjusted)"],
                  ["Trading Days", meta.trading_days.toLocaleString()],
                  ["Last Refresh", meta.generated_at_utc?.slice(0, 10) ?? "—"],
                ].map(([k, v]) => (
                  <tr key={k}>
                    <td className="py-2 pr-4 text-slate-500 w-40">{k}</td>
                    <td className="py-2 text-slate-300 font-mono">{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">Look-Ahead Bias Prevention</h3>
            <div className="space-y-3 text-xs text-slate-400">
              <p>
                Look-ahead bias occurs when a backtest uses information that would not have been
                available at the time of the trading decision. This project prevents it through:
              </p>
              <ul className="space-y-2 list-none">
                {[
                  "Signals computed exclusively from data available through end-of-day on the rebalance date",
                  "1-day execution lag: weights computed at t → first applied to the next available trading-date return",
                  "Programmatic event-level audit verifies every signal date, effective date, target weight, and holding period",
                  "Monthly rebalancing avoids daily signal look-ahead from return correlations",
                  "No forward-filling of returns (only forward-filling of prices for isolated gaps)",
                ].map((item, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-blue-400 mt-0.5 flex-shrink-0">→</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">Strategy Parameters</h3>
            <table className="w-full text-xs">
              <tbody className="divide-y divide-slate-700/40">
                {[
                  ["Momentum Window", `${meta.momentum_window_days} trading days`],
                  ["Volatility Window", `${meta.volatility_window_days} trading days`],
                  ["Annualization Factor", `${meta.annualization_factor} (trading days/year)`],
                  ["Rebalance Frequency", "Monthly (last trading day)"],
                  ["Signal-to-Weight Lag", "1 trading day"],
                  ["Transaction Cost", `${meta.transaction_cost_bps} bps one-way`],
                  ["Risk-Free Rate", `${meta.risk_free_rate_annual * 100}% annual (Sharpe)`],
                  ["Defensive Asset", "SHY (always eligible)"],
                ].map(([k, v]) => (
                  <tr key={k}>
                    <td className="py-2 pr-4 text-slate-500 w-48">{k}</td>
                    <td className="py-2 text-slate-300 font-mono">{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">Risk Metrics Formulas</h3>
            <div className="space-y-3 text-xs">
              {[
                ["Cumulative Return", "NAV_final / NAV_0 − 1, where NAV_0 = 1.0"],
                ["CAGR", "(NAV_final / NAV_0)^(252/N) − 1"],
                ["Ann. Volatility", "σ(daily returns) × √252"],
                ["Sharpe Ratio", "mean(daily excess return) / σ(daily excess return) × √252  (Rf = 0)"],
                ["Max Drawdown", "min_t [ NAV(t) / max(NAV(0..t)) − 1 ]"],
                ["Tracking Error", "σ(strategy daily ret − benchmark daily ret) × √252"],
                ["Information Ratio", "mean(strategy − benchmark daily return) × 252 / Tracking Error"],
                ["VaR 95%", "5th percentile of daily return distribution"],
                ["CVaR 95%", "Mean of returns below VaR threshold"],
              ].map(([name, formula]) => (
                <div key={name} className="flex gap-3">
                  <span className="text-slate-500 w-36 flex-shrink-0">{name}</span>
                  <code className="text-slate-300 text-[10px] bg-slate-900/50 px-1.5 py-0.5 rounded">
                    {formula}
                  </code>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
