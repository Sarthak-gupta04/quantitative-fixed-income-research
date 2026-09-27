"use client";

import React from "react";
import type { MetaData } from "@/types/data";

interface Props {
  meta: MetaData;
}

function Formula({ children }: { children: React.ReactNode }) {
  return (
    <div className="my-3 p-3 bg-slate-900/70 border border-slate-700/50 rounded font-mono text-xs text-slate-300 overflow-x-auto">
      {children}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-8">
      <h3 className="text-sm font-semibold text-slate-200 mb-3 border-b border-slate-700/50 pb-2">
        {title}
      </h3>
      {children}
    </div>
  );
}

export default function StrategyOverview({ meta }: Props) {
  return (
    <section id="strategy" className="py-16 px-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-semibold text-blue-400 uppercase tracking-widest">03</span>
          <span className="text-xs text-slate-500 uppercase tracking-widest">Strategy Overview</span>
        </div>
        <h2 className="text-2xl font-semibold text-slate-100">Strategy Design</h2>
        <p className="text-slate-400 mt-2 text-sm max-w-2xl">
          A simple, transparent, rules-based quantitative strategy. Priority: correct methodology,
          explainability, and reproducibility — not maximizing historical returns.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Left column */}
        <div>
          <Section title="Investment Universe & Benchmark">
            <div className="space-y-2">
              {[
                ["SHY", "iShares 1–3 Year Treasury Bond ETF", "Short duration / Defensive"],
                ["IEF", "iShares 7–10 Year Treasury Bond ETF", "Intermediate duration"],
                ["TLT", "iShares 20+ Year Treasury Bond ETF", "Long duration"],
              ].map(([ticker, name, role]) => (
                <div
                  key={ticker}
                  className="flex items-start gap-3 p-3 bg-slate-800/40 rounded border border-slate-700/40"
                >
                  <span className="font-mono text-xs font-bold text-blue-400 mt-0.5 w-8">{ticker}</span>
                  <div>
                    <p className="text-xs text-slate-200">{name}</p>
                    <p className="text-xs text-slate-500">{role}</p>
                  </div>
                </div>
              ))}
              <div className="flex items-start gap-3 p-3 bg-slate-800/20 rounded border border-slate-700/30">
                <span className="font-mono text-xs font-bold text-slate-400 mt-0.5 w-8">AGG</span>
                <div>
                  <p className="text-xs text-slate-300">iShares Core U.S. Aggregate Bond ETF</p>
                  <p className="text-xs text-slate-500">Passive benchmark (buy-and-hold)</p>
                </div>
              </div>
            </div>
          </Section>

          <Section title="Momentum Signal">
            <p className="text-xs text-slate-400 mb-2">
              An asset is eligible for allocation when its 60-trading-day price momentum is positive.
            </p>
            <Formula>
              Mom(i, t) = P(i, t) / P(i, t − 60) − 1{"\n"}
              {"\n"}Eligible(i, t) = 1  if Mom(i, t) &gt; 0{"\n"}
              {"              "}= 0  otherwise
            </Formula>
            <p className="text-xs text-slate-500">
              L = {meta.momentum_window_days} trading days (configurable).
              SHY is always eligible as the defensive asset.
            </p>
          </Section>

          <Section title="Realized Volatility">
            <p className="text-xs text-slate-400 mb-2">
              20-trading-day rolling standard deviation of daily returns, annualized.
            </p>
            <Formula>
              RVol(i, t) = σ(r(i, t−W+1 … t)) × √252{"\n"}
              {"\n"}where W = {meta.volatility_window_days} trading days
            </Formula>
          </Section>
        </div>

        {/* Right column */}
        <div>
          <Section title="Inverse-Volatility Position Sizing">
            <p className="text-xs text-slate-400 mb-2">
              Among eligible assets, weights are proportional to the inverse of realized volatility.
              Lower-volatility assets receive relatively higher weights.
            </p>
            <Formula>
              InvVol(i, t) = 1 / RVol(i, t){"\n"}
              {"\n"}w(i, t) = InvVol(i, t) / Σ_j InvVol(j, t){"\n"}
              {"         "}for j ∈ eligible set E(t)
            </Formula>
          </Section>

          <Section title="Defensive Rule">
            <p className="text-xs text-slate-400">
              If neither IEF nor TLT satisfies the momentum condition, the strategy allocates
              100% to SHY (short-duration, defensive). SHY's volatility participates in sizing
              when longer-duration assets are also eligible.
            </p>
          </Section>

          <Section title="Rebalancing & Transaction Costs">
            <div className="space-y-3 text-xs text-slate-400">
              <p>
                <strong className="text-slate-300">Rebalancing:</strong> Monthly, on the last
                trading day of each calendar month.
              </p>
              <p>
                <strong className="text-slate-300">Look-ahead lag:</strong> Signals computed at
                close of rebalance date t → weights first apply on the next available trading date.
                The return on that effective date uses only the earlier signal-date information.
              </p>
              <p>
                <strong className="text-slate-300">Transaction costs:</strong> {meta.transaction_cost_bps} bps
                applied to traded notional (the sum of absolute weight changes).
              </p>
              <Formula>
                Trading Notional(t) = Σ_i |w(i, t) − w(i, t−1)|{"\n"}
                TC(t) = Trading Notional(t) × {meta.transaction_cost_bps / 10000}{"\n"}
                One-Way Turnover(t) = 0.5 × Trading Notional(t)
              </Formula>
            </div>
          </Section>

          <Section title="Key Assumptions">
            <ul className="space-y-1.5 text-xs text-slate-400">
              <li>• Adjusted close prices (total-return proxy, dividends included)</li>
              <li>• Risk-free rate = {meta.risk_free_rate_annual * 100}% for Sharpe ratio (documented simplification)</li>
              <li>• Fractional shares allowed (standard in academic backtests)</li>
              <li>• No taxes or fund-level costs beyond transaction cost assumption</li>
              <li>• No leverage; weights always sum to 1.0</li>
              <li>• Missing, zero, or effectively-zero realized volatility is excluded from inverse-volatility sizing; SHY is the documented all-invalid-volatility fallback</li>
              <li>• Data source: Yahoo Finance via yfinance</li>
            </ul>
          </Section>
        </div>
      </div>
    </section>
  );
}
