"use client";

import React from "react";
import type { MetaData } from "@/types/data";

interface Props {
  meta: MetaData;
}

export default function Hero({ meta }: Props) {
  return (
    <section
      id="hero"
      className="relative pt-24 pb-16 px-6 max-w-7xl mx-auto"
    >
      {/* Background grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e293b_1px,transparent_1px),linear-gradient(to_bottom,#1e293b_1px,transparent_1px)] bg-[size:40px_40px] opacity-30 pointer-events-none" />

      <div className="relative z-10">
        {/* Badges */}
        <div className="flex flex-wrap gap-2 mb-6">
          {["Quantitative Research", "Fixed Income", "Python", "Backtesting"].map((tag) => (
            <span
              key={tag}
              className="px-3 py-1 text-xs font-medium border border-slate-700 text-slate-400 rounded-full bg-slate-800/50"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Title */}
        <h1 className="text-4xl md:text-5xl font-semibold text-slate-100 leading-tight mb-4 tracking-tight">
          Quantitative Fixed-Income
          <br />
          <span className="text-blue-400">Strategy & Risk Dashboard</span>
        </h1>

        {/* Description */}
        <p className="text-slate-400 text-base md:text-lg max-w-2xl mb-8 leading-relaxed">
          An educational quantitative research project implementing a rules-based momentum
          and volatility-aware fixed-income strategy across U.S. Treasury ETFs, with complete
          backtesting, risk analysis, and signal decomposition.
        </p>

        {/* Data info grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl">
          {[
            { label: "Universe", value: "SHY · IEF · TLT" },
            { label: "Benchmark", value: "AGG" },
            { label: "Period", value: `${meta.start_date} → ${meta.end_date}` },
            { label: "Data Through", value: meta.end_date },
          ].map((item) => (
            <div
              key={item.label}
              className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-4 py-3"
            >
              <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">{item.label}</p>
              <p className="text-sm font-medium text-slate-200 font-mono">{item.value}</p>
            </div>
          ))}
        </div>

        {/* Disclaimer ribbon */}
        <div className="mt-8 p-3 bg-slate-800/40 border-l-4 border-blue-500/50 rounded-r-lg max-w-3xl">
          <p className="text-xs text-slate-400">
            <strong className="text-slate-300">Educational Project.</strong> All results are
            historical backtest statistics based on publicly available data. This is not investment
            advice. Historical performance does not guarantee future results. Not affiliated with any
            investment firm.
          </p>
        </div>

        {/* Navigation */}
        <nav className="mt-10 flex flex-wrap gap-3">
          {[
            ["#executive-overview", "Overview"],
            ["#strategy", "Strategy"],
            ["#performance", "Performance"],
            ["#risk-analysis", "Risk"],
            ["#signals", "Signals"],
            ["#portfolio", "Portfolio"],
            ["#regime-analysis", "Regimes"],
            ["#sensitivity", "Sensitivity"],
            ["#methodology", "Methodology"],
            ["#limitations", "Limitations"],
            ["#references", "References"],
          ].map(([href, label]) => (
            <a
              key={href}
              href={href}
              className="px-4 py-2 text-xs font-medium border border-slate-700 text-slate-300 rounded-md hover:border-blue-500/60 hover:text-blue-400 transition-colors bg-slate-800/30"
            >
              {label}
            </a>
          ))}
        </nav>
      </div>
    </section>
  );
}
