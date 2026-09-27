"use client";

import React from "react";

const limitations = [
  {
    title: "Historical Backtest ≠ Live Performance",
    body: "All results are backtested using historical data. Actual trading would incur market impact, bid-ask spreads, management costs, and execution delays not captured here.",
  },
  {
    title: "ETF Proxy Limitations",
    body: "SHY, IEF, TLT, and AGG are ETF proxies for fixed-income exposures. They carry management fees, tracking error relative to the underlying index, and liquidity-related costs.",
  },
  {
    title: "Parameter Sensitivity",
    body: "The 60-day momentum and 20-day volatility windows are chosen heuristically. Results are sensitive to these parameters. No formal optimization was performed to avoid overfitting.",
  },
  {
    title: "Risk-Free Rate Assumption",
    body: "The Sharpe ratio uses Rf = 0%. Using the prevailing short-term Treasury rate would reduce the Sharpe ratio in low-rate environments and increase it during high-rate periods (2022–2024).",
  },
  {
    title: "Transaction Cost Estimate",
    body: "2 bps one-way is a conservative estimate for liquid ETFs. Actual costs depend on broker, trade size, and market conditions. Real institutional costs differ significantly.",
  },
  {
    title: "Bond Bull Market Context",
    body: "The 2003–2021 period was a long bull market for U.S. Treasuries (declining rates). Results from this period may not reflect future performance in different rate regimes.",
  },
  {
    title: "2022 Rate Shock",
    body: "The 2022 Federal Reserve rate hiking cycle caused large losses in intermediate and long-duration Treasuries. The strategy's performance in this period reflects the momentum signal's response to price trends.",
  },
  {
    title: "Survivorship Bias",
    body: "Not applicable for these specific ETFs (all still exist), but is relevant as a general backtesting limitation. ETF closures are not captured in retrospective studies.",
  },
  {
    title: "No Inflation Adjustment",
    body: "All returns are nominal. Real (inflation-adjusted) returns differ, particularly during high-inflation periods like 2021–2023.",
  },
  {
    title: "Data Source Quality",
    body: "Yahoo Finance (yfinance) data may contain errors in corporate action adjustments. Prices are used as-is after basic validation. Professional-grade data (Bloomberg, Refinitiv) would provide higher confidence.",
  },
];

export default function Limitations() {
  return (
    <section id="limitations" className="py-16 px-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-semibold text-blue-400 uppercase tracking-widest">09</span>
          <span className="text-xs text-slate-500 uppercase tracking-widest">Limitations</span>
        </div>
        <h2 className="text-2xl font-semibold text-slate-100">Limitations & Honest Assessment</h2>
        <p className="text-slate-400 mt-2 text-sm max-w-2xl">
          A rigorous quantitative project requires explicit discussion of its limitations.
          The following are real constraints, not disclaimers added to be cautious.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {limitations.map((lim, i) => (
          <div
            key={i}
            className="bg-slate-800/30 border border-slate-700/40 rounded-xl p-5 hover:border-slate-600/60 transition-colors"
          >
            <p className="text-sm font-semibold text-slate-200 mb-2">{lim.title}</p>
            <p className="text-xs text-slate-400 leading-relaxed">{lim.body}</p>
          </div>
        ))}
      </div>

      {/* Final summary */}
      <div className="mt-8 p-6 bg-slate-800/40 border border-slate-700/50 rounded-xl">
        <h3 className="text-sm font-semibold text-slate-200 mb-3">What This Project Does and Does Not Demonstrate</h3>
        <div className="grid md:grid-cols-2 gap-6 text-xs">
          <div>
            <p className="text-emerald-400 font-semibold uppercase tracking-wider mb-2">What it demonstrates</p>
            <ul className="space-y-1.5 text-slate-400">
              {[
                "Rules-based strategy design and documentation",
                "Programmatic look-ahead bias prevention",
                "Momentum and volatility signal calculation",
                "Inverse-volatility portfolio construction",
                "Gross and net-of-cost performance comparison",
                "Standard risk metrics (Sharpe, MDD, VaR, CVaR)",
                "Reproducible Python analytics pipeline",
                "Clean data validation and handling",
                "Honest reporting of results (strategy underperforms AGG in absolute return)",
              ].map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="text-emerald-500 flex-shrink-0">✓</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-red-400 font-semibold uppercase tracking-wider mb-2">What it does not demonstrate</p>
            <ul className="space-y-1.5 text-slate-400">
              {[
                "Live investment management or execution",
                "Bloomberg, FactSet, or proprietary data experience",
                "GARCH, stochastic calculus, or advanced econometrics",
                "Machine learning or AI-based signal generation",
                "Institutional-scale portfolio management",
                "Client-facing investment advisory work",
                "Guaranteed alpha or market outperformance",
                "Coverage of the 2008 financial crisis or pre-2003 markets",
              ].map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="text-red-500 flex-shrink-0">✗</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
