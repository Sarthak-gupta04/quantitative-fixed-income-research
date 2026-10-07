"use client";

import { useState } from "react";
import { fmtDate } from "@/lib/formatters";
import { useResearch } from "@/components/ResearchExperience";

const terms = [
  ["Momentum", "An asset’s observed price change over the model’s trailing window. Here it controls eligibility for IEF and TLT; it is not a forecast."],
  ["Realized volatility", "A measure of historical return variability, annualized using the saved convention. It informs position sizing."],
  ["Drawdown", "The decline from a previous NAV peak. A selected period’s chart retains the original full-path drawdown observations."],
  ["Sharpe ratio", "Historical return relative to volatility under the recorded risk-free-rate assumption. This project uses 0%; it is not a guarantee of performance."],
  ["Duration", "A first-order measure of bond-price sensitivity to yields. The lab uses fixed issuer duration snapshots and excludes convexity, income and non-parallel shifts."],
  ["Turnover", "One-way turnover is half of gross traded notional. Gross traded notional sums absolute target-weight changes."],
  ["Target versus effective", "A signal produces target weights at the close. Those weights first govern returns on the next available trading day."],
  ["CAGR", "The annualized compounded growth rate over a stated evaluation window. Compare figures only after checking their dates."],
];

export default function ResearchProvenance() {
  const { data } = useResearch();
  const [filter, setFilter] = useState("");
  const filtered = terms.filter(([term, definition]) => `${term} ${definition}`.toLowerCase().includes(filter.toLowerCase()));
  return <section className="section provenance-section" id="provenance"><div className="shell">
    <div className="section-head"><span className="section-index">Research desk</span><div><h2>Traceable by design.</h2><p className="section-copy">A saved research snapshot, not a live trading terminal. Every interactive view points back to the same recorded evidence.</p></div></div>
    <div className="provenance-grid"><article className="provenance-card"><span className="snapshot-pill">Historical snapshot</span><h3>Dates &amp; baseline</h3><dl><div><dt>Market data through</dt><dd>{fmtDate(data.meta.end_date)}</dd></div><div><dt>Outputs generated (UTC)</dt><dd>{fmtDate(data.meta.generated_at_utc)}</dd></div><div><dt>Baseline windows</dt><dd>{data.meta.momentum_window_days}D momentum / {data.meta.volatility_window_days}D volatility</dd></div><div><dt>Implementation lag</dt><dd>Next available trading day</dd></div><div><dt>Cost convention</dt><dd>{data.meta.transaction_cost_bps} bps × gross traded notional</dd></div><div><dt>Risk-free rate</dt><dd>{data.meta.risk_free_rate_annual * 100}% annual</dd></div></dl></article>
    <article className="provenance-card brief-card"><span className="mini-label">Take the research with you</span><h3>A concise research brief.</h3><p>Question, method, saved findings, holdout evidence, selected charts and limitations in one printable document.</p><a className="primary-link" href="/research-brief" target="_blank" rel="noopener noreferrer">Read / print the brief ↗</a><a className="secondary-link" href="/research-brief?download=1" download="qfi-research-brief.html">Download standalone HTML ↓</a><p className="research-caption">Use your browser’s Print → Save as PDF for a PDF copy. The HTML download is self-contained and works offline.</p></article></div>
    <details><summary>Inspect sources, reproducibility &amp; saved data</summary><p>{data.reproducibility.workflow_reproducibility_note}</p><div className="provenance-links"><a href="https://github.com/Sarthak-gupta04/quantitative-fixed-income-research" target="_blank" rel="noopener noreferrer">Source repository ↗</a><a href="https://github.com/Sarthak-gupta04/quantitative-fixed-income-research/blob/main/README.md" target="_blank" rel="noopener noreferrer">Reproduction instructions ↗</a><a href="/data/reproducibility.json" target="_blank" rel="noopener noreferrer">Saved provenance JSON ↗</a><a href="/data/signal_diagnostics.json" target="_blank" rel="noopener noreferrer">Decision diagnostics ↗</a><a href={data.yieldCurve.methodology.source_url} target="_blank" rel="noopener noreferrer">Treasury source ↗</a></div><p className="research-caption">Baseline price provider: {data.reproducibility.data_source.provider}. Download recorded {fmtDate(data.reproducibility.data_source.download_timestamp_utc)}. Data-source revisions can change the results of a future rerun.</p><div className="source-hashes">{Object.entries(data.reproducibility.data_source.raw_file_sha256).map(([file, hash]) => <p key={file}><strong>{file} · saved SHA-256</strong><code>{hash}</code></p>)}</div></details>
    <div className="research-subhead"><div><span className="mini-label">On-demand explanation</span><h3>The research vocabulary.</h3></div><label className="glossary-search"><span className="sr-only">Search research terms</span><input type="search" placeholder="Find a term…" value={filter} onChange={e => setFilter(e.target.value)} /></label></div><div className="glossary-grid">{filtered.map(([term, definition]) => <details key={term}><summary>{term}</summary><p>{definition}</p></details>)}</div>{filtered.length === 0 && <p role="status">No matching term. Try “duration,” “risk” or “turnover.”</p>}
  </div></section>;
}
