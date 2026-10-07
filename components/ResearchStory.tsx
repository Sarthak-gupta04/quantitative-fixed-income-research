"use client";

import type { DashboardData } from "@/types/data";
import { fmtDate, fmtNumber, fmtPct, fmtPctSigned } from "@/lib/formatters";
import RegimeSequence from "@/components/RegimeSequence";
import { CurveSection, FailureSection, HoldoutSection, RateShockSection } from "@/components/ResearchExpansion";
import { ChapterNav, HeroVisual, ResearchOverview, RevealSections } from "@/components/ResearchChrome";
import { AllocationChart, ConfigurationComparison, ConnectedNavChart, ConnectedRiskChart, ExplorationStatus, HistoricalExplorer, MonthlyHeatmap } from "@/components/ResearchWorkbench";
import ResearchProvenance from "@/components/ResearchProvenance";

const assets = ["SHY", "IEF", "TLT"] as const;

function Heading({ n, label, title, copy }: { n: string; label: string; title: string; copy?: string }) {
  return <div className="section-head"><div className="section-index">{n} — {label}</div><div><h2>{title}</h2>{copy && <p className="section-copy">{copy}</p>}</div></div>;
}

export default function ResearchStory({ data }: { data: DashboardData }) {
  const { meta, summary, researcherView: view } = data;
  const latest = view.latest_signal;
  const year = (d: string) => d.slice(0, 4);
  const pipeline = ["Data", `${meta.momentum_window_days}D momentum`, "Eligibility", `${meta.volatility_window_days}D volatility`, "Weighting", "Monthly rebalance", "Next-day implementation"];
  const methodology = ["Market data", "Data validation", `${meta.momentum_window_days}-day momentum`, "Eligibility", `${meta.volatility_window_days}-day realized volatility`, "Inverse-volatility weighting", "Monthly rebalance", "Next-day implementation", "Backtest", "Risk analysis"];
  const limitations = [
    ["Public market data", "Historical adjusted-close data is sourced from Yahoo Finance through yfinance and may be revised by the vendor."],
    ["ETF proxies", "The selected ETFs are tradable proxies; they do not reproduce direct Treasury holdings or every fixed-income market segment."],
    ["Parameter sensitivity", "Results vary with momentum and volatility windows. Six predetermined configurations are shown without optimization."],
    ["Risk-free rate", `Sharpe ratios use the implemented ${(meta.risk_free_rate_annual * 100).toFixed(0)}% annual risk-free-rate assumption.`],
    ["Implementation costs", `The backtest applies ${meta.transaction_cost_bps} bps to traded notional; taxes, market impact and other frictions are excluded.`],
    ["Historical simulation", "There is no live execution record. Historical relationships may not persist and backtested performance is not a forecast."],
  ];
  return <>
    <a className="skip-link" href="#research-content">Skip to research</a>
    <ChapterNav />
    <RevealSections />

    <main id="research-content">
      <section className="hero shell" id="overview"><div className="hero-grid"><div className="hero-copy"><div className="eyebrow">Independent quantitative research · {year(meta.start_date)}—{year(meta.end_date)}</div><h1>Fixed-Income<br />Strategy &amp;<br /><span>Risk Research.</span></h1><p className="lede">A transparent Treasury allocation framework. Explore the decisions, inspect the evidence, understand the trade-offs.</p><div className="hero-cta"><a className="primary-link" href="#decision">Explore the model <span>↗</span></a><a className="secondary-link" href="#at-a-glance">The 30-second overview ↓</a></div></div><HeroVisual /></div><div className="metadata"><div><span>Research period</span><strong>{year(meta.start_date)}–{year(meta.end_date)}</strong></div><div><span>Universe</span><strong>{meta.tickers.length + 1} ETFs</strong></div><div><span>Rebalance</span><strong>Monthly</strong></div><div><span>System</span><strong>Python + Next.js</strong></div></div><div className="hero-foot"><div><span className="mini-label">Historical backtest · not live market data</span>Data through {fmtDate(meta.end_date)} · Educational research</div><a className="scrollcue" href="#at-a-glance">Follow the research</a></div></section>

      <ResearchOverview />

      <section className="section idea"><div className="shell"><div className="section-index">01 — The idea</div><h2>Can a transparent, rules-based framework adapt fixed-income exposure using <em>momentum</em> and <em>volatility?</em></h2><p className="section-copy">The question is tested through a historical allocation model, with explicit signals, implementation timing and risk measurement.</p></div></section>


      <section className="section" id="signal"><div className="shell"><Heading n="02" label="The signal" title="A clear rule for entering the eligible set." copy="At each month-end, the model observes trailing momentum. Intermediate- and long-duration assets enter the eligible set only when their historical signal is positive; SHY remains the defensive asset." /><div className="signal-rule"><span className="signal-number number">{meta.momentum_window_days}D</span><div><span className="mini-label">Momentum signal</span><p>Positive momentum makes IEF and TLT eligible. SHY remains the defensive asset.</p></div></div><details className="signal-details"><summary>Explore latest model signals <span>SHY · IEF · TLT</span></summary><div className="asset-row">{assets.map(a => <article className="asset" key={a}><div className="asset-code">{a}</div><p>{meta.ticker_names[a]}</p><div className="asset-data"><div><span className="mini-label">Momentum</span><strong className="number">{fmtPctSigned(latest.momentum[a])}</strong></div><div><span className="mini-label">Model allocation</span><strong className="number">{fmtPct(latest.target_weights[a])}</strong></div></div><span className="state">{a === "SHY" ? "Defensive asset · always eligible" : latest.eligibility[a] ? "Eligible model state" : "Not eligible"}</span></article>)}</div></details></div></section>

      <CurveSection data={data.yieldCurve} />


      <section className="section dark" id="risk"><div className="shell"><Heading n="04" label="The risk lens" title="Volatility is treated as information—not decoration." copy={`A ${meta.volatility_window_days}-trading-day realized-volatility measure informs position sizing across eligible assets.`} /><div className="hero-stat"><span className="number">{fmtPct(summary.strategy_net.annualized_volatility)}</span><p>Annualized strategy volatility · full historical backtest</p></div><ExplorationStatus /><div className="chart-panel"><div className="chart-title"><h3>Rolling realized volatility</h3><p>Strategy compared with AGG · annualized</p></div><ConnectedRiskChart dataKey="strategy_rolling_vol" benchmark="benchmark_rolling_vol" /></div></div></section>

      <section className="section" id="portfolio"><div className="shell"><Heading n="05" label="The portfolio" title="From observation to implementation." copy="A deliberate sequence turns end-of-month market information into the next portfolio state. The execution lag keeps information and implementation separate." /><div className="pipeline">{pipeline.map(x => <div className="pipe" key={x}>{x}</div>)}</div><ExplorationStatus /><div className="chart-title"><h3>Historical portfolio allocation</h3><p>Saved effective weights</p></div><AllocationChart /><details><summary>View recent implementation details</summary><p>Signals are calculated at the close of each monthly signal date. Target weights first govern returns on the next available trading day. The latest observable rebalance became effective {fmtDate(view.latest_observable_rebalance?.effective_date ?? "")}.</p></details></div></section>

      <HistoricalExplorer />

      <section className="section" id="performance"><div className="shell"><Heading n="07" label="The result" title="A measured view of historical performance." copy={`Net strategy results include the implemented ${meta.transaction_cost_bps} bps cost on traded notional. AGG is shown as a passive historical reference, not as a claim of superiority.`} /><div className="metrics">{[["CAGR",fmtPct(summary.strategy_net.annualized_return),`AGG ${fmtPct(summary.benchmark.annualized_return)}`],["Annualized volatility",fmtPct(summary.strategy_net.annualized_volatility),`AGG ${fmtPct(summary.benchmark.annualized_volatility)}`],["Sharpe ratio",fmtNumber(summary.strategy_net.sharpe_ratio,2),`AGG ${fmtNumber(summary.benchmark.sharpe_ratio,2)}`],["Maximum drawdown",fmtPct(summary.strategy_net.max_drawdown),`AGG ${fmtPct(summary.benchmark.max_drawdown)}`]].map(([l,v,s]) => <div className="metric" key={l}><span className="mini-label">{l} · full history</span><strong className="number">{v}</strong><small>{s}</small></div>)}</div><ExplorationStatus /><div className="chart-title"><h3>Growth of one unit</h3><p>Net strategy is primary · AGG is contextual</p></div><ConnectedNavChart /><MonthlyHeatmap /></div></section>

      <section className="section dark" id="risk-path"><div className="shell"><Heading n="08" label="Risk through time" title="Risk is a path, not a single number." copy="Drawdown shows distance from the previous peak. Rolling Sharpe provides a deliberately unstable, time-varying view of risk-adjusted historical returns." /><ExplorationStatus /><div className="risk-grid"><div><div className="chart-title"><h3>Drawdown</h3><p>Peak-to-trough path</p></div><ConnectedRiskChart dataKey="strategy_drawdown" benchmark="benchmark_drawdown" /></div><div><div className="chart-title"><h3>Rolling Sharpe</h3><p>252-day window · Rf = 0%</p></div><ConnectedRiskChart dataKey="strategy_rolling_sharpe" benchmark="benchmark_rolling_sharpe" percent={false} /></div></div></div></section>

      <FailureSection data={data.failureModes} />

      <section className="section" id="regimes"><div className="shell"><Heading n="10" label="The regimes" title="Four periods. The same rules." copy="Selected historical windows are reported neutrally using the saved regime analysis. They are descriptive slices—not rankings, forecasts or causal explanations." /><RegimeSequence periods={data.regimeAnalysis.periods} /></div></section>

      <section className="section" id="robustness"><div className="shell"><Heading n="11" label="Robustness" title="Sensitivity, without optimization." copy="Six predetermined momentum and volatility-window combinations are evaluated over a common historical period." /><ConfigurationComparison /><details><summary>View all six saved configurations</summary><div className="sensitivity-scroll"><table className="sensitivity-table"><thead><tr><th>Configuration</th><th>CAGR</th><th>Volatility</th><th>Sharpe</th><th>Max drawdown</th><th>Turnover</th></tr></thead><tbody>{data.sensitivity.results.map(r => <tr key={r.configuration_id} className={r.is_baseline ? "baseline" : ""}><td>{r.parameters.momentum_window_days}D / {r.parameters.volatility_window_days}D {r.is_baseline && <span className="badge">BASELINE</span>}</td><td>{fmtPct(r.metrics.cagr)}</td><td>{fmtPct(r.metrics.annualized_volatility)}</td><td>{fmtNumber(r.metrics.sharpe_ratio,2)}</td><td>{fmtPct(r.metrics.maximum_drawdown)}</td><td>{fmtPct(r.metrics.total_one_way_turnover,0)}</td></tr>)}</tbody></table></div></details><p className="section-copy">Predetermined sensitivity analysis; parameters were not optimized against historical performance.</p></div></section>

      <HoldoutSection data={data.holdout} />

      <section className="section dark" id="current-state"><div className="shell"><Heading n="13" label="Current model state" title="Researcher’s view." copy="The latest observable model state, shown exactly as saved by the research pipeline. This is descriptive model output—not investment advice or a forecast." /><div className="current-card"><div><div className="asof">Latest signal date</div><h3>{fmtDate(latest.signal_date)}</h3></div><div className="weight-bars"><span className="mini-label">Current model allocation</span>{assets.map(a => <div className="weight-row" key={a}><b>{a}</b><div className="bar"><i style={{ width: `${(latest.target_weights[a] ?? 0)*100}%` }} /></div><span className="number">{fmtPct(latest.target_weights[a],0)}</span></div>)}</div></div><div className="current-inputs">{assets.map(a => <div key={a}><strong>{a}</strong><span>Momentum <b className="number">{fmtPctSigned(latest.momentum[a])}</b></span><span>Realized volatility <b className="number">{fmtPct(latest.realized_volatility[a])}</b></span></div>)}</div><div className="current-details"><div><span className="mini-label">Effective allocation date</span><strong className="number">{fmtDate(view.latest_effective_allocation.date)}</strong></div><div><span className="mini-label">Rolling strategy volatility</span><strong className="number">{fmtPct(view.recent_realized_risk.strategy_rolling_volatility)}</strong></div><div><span className="mini-label">Current drawdown</span><strong className="number">{fmtPct(view.recent_realized_risk.strategy_drawdown)}</strong></div></div></div></section>

      <aside className="research-links shell" aria-label="Explore current model context"><span className="mini-label">Continue the current-state research</span><div><a href="#curve">Latest 2s10s <strong>{data.yieldCurve.latest.slope_2s10s.toFixed(2)} pp</strong> ↗</a><a href="#decision">Latest decision trace ↗</a><a href="#rate-shock">Illustrative rate sensitivity ↗</a></div></aside>

      <RateShockSection data={data.rateShock} />

      <section className="section" id="method"><div className="shell"><Heading n="15" label="The method" title="A transparent chain from data to evidence." copy="The framework prioritizes reproducibility, explicit timing and explainability. Technical detail is available without obscuring the core research logic." /><div className="method-flow">{methodology.map((x,i) => <div className="method-step" key={x}><span>{String(i+1).padStart(2,"0")}</span><div><strong>{x}</strong>{i === 1 && <p>Missing values, timeline integrity and adjusted-price coverage are checked before signals are formed.</p>}{i === 5 && <p>Eligible assets receive weights proportional to inverse realized volatility.</p>}</div></div>)}</div><div className="lag"><h3>Look-ahead-bias prevention</h3><div className="lag-flow"><div><span className="mini-label">01</span>Signal at month-end</div><span>→</span><div><span className="mini-label">02</span>Weights determined after the signal</div><span>→</span><div><span className="mini-label">03</span>Active next available trading day</div></div></div><details><summary>View research assumptions</summary><p>Adjusted close is used as a total-return proxy. Fractional positions are allowed, no leverage is used, and portfolio weights sum to one. Transaction costs are applied to trading notional. Sharpe ratio uses the saved zero risk-free-rate assumption.</p></details></div></section>

      <ResearchProvenance />

      <section className="section" id="limitations"><div className="shell"><Heading n="16" label="Limitations" title="What this research cannot establish." /><div className="notes">{limitations.map(([a,b]) => <article className="note" key={a}><strong>{a}</strong><p>{b}</p></article>)}</div></div></section>

      <section className="section" id="references"><div className="shell"><Heading n="17" label="References" title="Source material and documentation." /><div className="references">{data.references.references.map(r => <a className="reference" key={r.id} href={r.url} target="_blank" rel="noopener noreferrer"><small>{r.category}</small><strong>{r.title} ↗</strong><span>{r.publisher} · {r.use}</span></a>)}</div></div></section>
    </main>

    <footer className="author"><div className="shell"><div className="author-grid"><div><div className="eyebrow">Independent research</div><h2>Sarthak Gupta</h2></div><div className="author-copy">BBA — Decision Science<br />Independent Quantitative Research Project<br />Python · Pandas · NumPy · Next.js · TypeScript<div className="author-links"><a href="https://github.com/Sarthak-gupta04" target="_blank" rel="noreferrer">GitHub ↗</a><a href="https://www.linkedin.com/in/sarthak-gupta-10868624b" target="_blank" rel="noopener noreferrer">LinkedIn</a></div></div></div><div className="disclaimer"><strong>Important disclosure.</strong> {meta.disclaimer} Data: Yahoo Finance via yfinance. Universe: {meta.tickers.join(", ")}. Benchmark: {meta.benchmark}. Generated {fmtDate(meta.generated_at_utc)} UTC.</div></div></footer>
  </>;
}
