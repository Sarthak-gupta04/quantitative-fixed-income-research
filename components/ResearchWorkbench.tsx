"use client";

import { useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtDate, fmtNumber, fmtPct, fmtPctSigned, MONTH_NAMES } from "@/lib/formatters";
import { ASSETS, ASSET_COLORS, isObservationDate, observationAtOrBefore, sampleWithSelection } from "@/lib/research-view";
import { useResearch, useSelectedResearch } from "@/components/ResearchExperience";
import { ChartFrame } from "@/components/ResearchChrome";
import type { DecisionRecord } from "@/types/data";

const tick = { fontSize: 10, fill: "#7b8797" };

function chartDate(state: unknown): string | undefined {
  if (state && typeof state === "object" && "activeLabel" in state && typeof state.activeLabel === "string" && /^\d{4}-\d{2}-\d{2}$/.test(state.activeLabel)) return state.activeLabel;
}

export function AssetLegend({ benchmark = false }: { benchmark?: boolean }) {
  return <div className="asset-legend">{benchmark ? <><span><i style={{ background: "#1768e5" }} />Strategy</span><span><i style={{ background: "#8c99a9" }} />AGG · passive reference</span></> : ASSETS.map(asset => <span key={asset}><i style={{ background: ASSET_COLORS[asset] }} />{asset}</span>)}</div>;
}

export function ConnectedNavChart() {
  const { data, view, period, selectDate } = useResearch();
  const observations = period ? data.nav.filter(p => p.date >= period.actual_start_date && p.date <= period.actual_end_date) : data.nav;
  const selected = observationAtOrBefore(observations, view.date);
  const chart = sampleWithSelection(observations, view.date, 4);
  return <><AssetLegend benchmark /><ChartFrame title="Historical strategy and AGG NAV"><ResponsiveContainer width="100%" height="100%"><LineChart data={chart} syncId="research-date" syncMethod="value" onClick={state => { const date = chartDate(state); if (date) selectDate(date); }} margin={{ left: 0, right: 15, top: 12, bottom: 0 }}><CartesianGrid vertical={false} stroke="var(--chart-grid)" /><XAxis dataKey="date" tick={tick} axisLine={false} tickLine={false} minTickGap={55} tickFormatter={v => String(v).slice(0, 4)} /><YAxis tick={tick} axisLine={false} tickLine={false} width={40} domain={["auto", "auto"]} /><Tooltip labelFormatter={v => fmtDate(String(v))} formatter={(v, name) => [fmtNumber(Number(v), 3), String(name)]} /><ReferenceLine x={selected?.date} stroke="#45a6b5" strokeDasharray="3 4" /><Line type="linear" dataKey="strategy_net" name="Strategy NAV" stroke="#1768e5" strokeWidth={2.5} dot={false} isAnimationActive={false} /><Line type="linear" dataKey="benchmark" name="AGG NAV" stroke="#8c99a9" strokeWidth={1.4} strokeDasharray="4 5" dot={false} isAnimationActive={false} /></LineChart></ResponsiveContainer></ChartFrame><p className="research-caption">{period ? `${period.label} · ` : "Full history · "}NAV retains its original backtest base; it is not rebased at the selected period. Selected observation: {fmtDate(selected?.date ?? "")}.</p></>;
}

export function ConnectedRiskChart({ dataKey, benchmark, percent = true }: { dataKey: string; benchmark: string; percent?: boolean }) {
  const { data, view, period, selectDate } = useResearch();
  const observations = period ? data.rollingMetrics.filter(p => p.date >= period.actual_start_date && p.date <= period.actual_end_date) : data.rollingMetrics;
  const selected = observationAtOrBefore(observations, view.date);
  const title = dataKey.includes("drawdown") ? "Historical drawdown" : percent ? "Rolling realized volatility" : "Rolling Sharpe";
  return <><AssetLegend benchmark /><ChartFrame title={title}><ResponsiveContainer width="100%" height="100%"><LineChart data={sampleWithSelection(observations, view.date)} syncId="research-date" syncMethod="value" onClick={state => { const date = chartDate(state); if (date) selectDate(date); }}><CartesianGrid vertical={false} stroke="var(--chart-grid)" /><XAxis dataKey="date" tick={tick} axisLine={false} tickLine={false} minTickGap={45} tickFormatter={v => String(v).slice(0, 4)} /><YAxis tick={tick} axisLine={false} tickLine={false} width={44} tickFormatter={v => percent ? fmtPct(Number(v), 0) : fmtNumber(Number(v), 1)} /><Tooltip labelFormatter={v => fmtDate(String(v))} formatter={(v, name) => [percent ? fmtPct(Number(v)) : fmtNumber(Number(v), 2), String(name)]} /><ReferenceLine x={selected?.date} stroke="#45a6b5" strokeDasharray="3 4" /><Line type="linear" dataKey={dataKey} name="Strategy" stroke="#63a0ff" strokeWidth={2} dot={false} isAnimationActive={false} /><Line type="linear" dataKey={benchmark} name="AGG" stroke="#8c99a9" strokeWidth={1.2} strokeDasharray="4 5" dot={false} isAnimationActive={false} /></LineChart></ResponsiveContainer></ChartFrame></>;
}

export function AllocationChart() {
  const { data, view, period, selectDate } = useResearch();
  const observations = period ? data.weights.filter(p => p.date >= period.actual_start_date && p.date <= period.actual_end_date) : data.weights;
  const selected = observationAtOrBefore(observations, view.date);
  return <><AssetLegend /><ChartFrame title="Historical effective allocation" className="allocation"><ResponsiveContainer width="100%" height="100%"><AreaChart data={sampleWithSelection(observations, view.date)} syncId="research-date" syncMethod="value" onClick={state => { const date = chartDate(state); if (date) selectDate(date); }}><CartesianGrid vertical={false} stroke="var(--chart-grid)" /><XAxis dataKey="date" tick={tick} axisLine={false} tickLine={false} minTickGap={55} tickFormatter={v => String(v).slice(0, 4)} /><YAxis domain={[0, 1]} width={43} tick={tick} axisLine={false} tickLine={false} tickFormatter={v => fmtPct(Number(v), 0)} /><Tooltip formatter={(v, name) => [fmtPct(Number(v)), String(name)]} labelFormatter={v => fmtDate(String(v))} /><ReferenceLine x={selected?.date} stroke="#152b4b" strokeDasharray="3 4" />{ASSETS.map(a => <Area key={a} type="stepAfter" dataKey={a} name={a} stackId="1" stroke={ASSET_COLORS[a]} fill={ASSET_COLORS[a]} fillOpacity={.8} isAnimationActive={false} />)}</AreaChart></ResponsiveContainer></ChartFrame><p className="research-caption">Effective historical weights, sampled for display. Selected observation: {fmtDate(selected?.date ?? "")}. These are distinct from a same-day signal’s next-day target.</p></>;
}

export function ExplorationStatus() {
  const { view, period, selectPeriod, share } = useResearch();
  return <div className="exploration-status"><div><span className="mini-label">Shared research view</span><strong>{fmtDate(view.date)}</strong><span>{period ? ` · ${period.label}` : " · Full-history charts"}</span></div><div><a href="#decision">Change date</a>{period && <button className="text-button" type="button" onClick={() => selectPeriod("")}>Reset period</button>}<button className="text-button" type="button" onClick={share}>Copy view link ↗</button></div></div>;
}

function WeightComparison({ item }: { item: DecisionRecord }) {
  return <div className="decision-bars">{ASSETS.map(a => <div className="decision-bar-row" key={a}><div className="decision-bar-label"><strong>{a}</strong><span>{fmtPct(item.previous_allocation[a], 1)} → {fmtPct(item.new_allocation[a], 1)}</span></div><div className="comparison-track" aria-hidden="true"><i className="prior-bar" style={{ width: `${item.previous_allocation[a] * 100}%` }} /><i className="target-bar" style={{ width: `${item.new_allocation[a] * 100}%`, background: ASSET_COLORS[a] }} /></div></div>)}<p className="research-caption">Grey: previous target · colour: new target. Percentages above are the exact saved weights rounded for display.</p></div>;
}

function DateInspector({ date, first, last, onSelect }: { date: string; first: string; last: string; onSelect: (date: string) => void }) {
  return <form className="date-inspector" onSubmit={event => {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem("research-date") as HTMLInputElement;
    if (isObservationDate(input.value) && input.value >= first && input.value <= last) onSelect(input.value);
  }}><label>Inspect a historical date<input key={date} name="research-date" type="date" defaultValue={date} min={first} max={last} required /></label><button type="submit" className="outline-button">Inspect date ↗</button></form>;
}

export function HistoricalExplorer() {
  const { data, view, selectDate, selectPeriod, rebalances, period } = useResearch();
  const selected = useSelectedResearch();
  const [playing, setPlaying] = useState(false);
  const [step, setStep] = useState(0);
  const index = Math.max(0, rebalances.findLastIndex(r => r.signal_date <= view.date));
  const rebalance = rebalances[index];
  const signal = data.signals.find(s => s.date === rebalance?.signal_date);
  const prior = rebalances[index - 1];
  const diagnostic = data.signalDiagnostics.records.find(r => r.signal_date === rebalance?.signal_date);
  const item = useMemo<DecisionRecord | undefined>(() => {
    if (!rebalance || !signal) return;
    return diagnostic ?? {
      signal_date: rebalance.signal_date, effective_date: rebalance.effective_date,
      previous_signal_date: prior?.signal_date ?? null,
      previous_allocation: Object.fromEntries(ASSETS.map(a => [a, prior?.[`weight_${a}`] ?? 0])),
      new_allocation: Object.fromEntries(ASSETS.map(a => [a, rebalance[`weight_${a}`] ?? 0])),
      momentum: Object.fromEntries(ASSETS.map(a => [a, signal[`momentum_${a}`] ?? 0])),
      eligibility: Object.fromEntries(ASSETS.map(a => [a, signal[`eligible_${a}`]])),
      realized_volatility: Object.fromEntries(ASSETS.map(a => [a, signal[`rvol_${a}`] ?? 0])),
      weight_change: Object.fromEntries(ASSETS.map(a => [a, (rebalance[`weight_${a}`] ?? 0) - (prior?.[`weight_${a}`] ?? 0)])),
      trading_notional: rebalance.trading_notional ?? 0, transaction_cost: rebalance.transaction_cost ?? 0,
      explanations: ["This observable rebalance is below the saved material-change threshold. Its recorded signals and target weights are shown without a material-change narrative."],
    };
  }, [rebalance, signal, prior, diagnostic]);
  useEffect(() => {
    if (!playing) return;
    const next = rebalances[index + 1];
    if (!next) return;
    const timer = setTimeout(() => { selectDate(next.signal_date); if (index + 1 === rebalances.length - 1) setPlaying(false); }, 1400);
    const pause = () => { if (document.hidden) setPlaying(false); };
    document.addEventListener("visibilitychange", pause);
    return () => { clearTimeout(timer); document.removeEventListener("visibilitychange", pause); };
  }, [playing, index, rebalances, selectDate]);
  const selectIndex = (next: number) => { setPlaying(false); selectDate(rebalances[Math.max(0, Math.min(rebalances.length - 1, next))].signal_date); };
  const stages = [
    ["Momentum", `${data.meta.momentum_window_days}-day observed signal`, "Positive momentum admits IEF and TLT to the eligible set; SHY is the defensive asset."],
    ["Eligibility", "A rule, not a prediction", "The saved eligibility flags determine which assets can receive weight. No future information is used."],
    ["Volatility", `${data.meta.volatility_window_days}-day realized measure`, "Saved annualized realized volatility informs inverse-volatility sizing among eligible assets."],
    ["Target weights", "The recorded next portfolio", "The weights below are read from the research outputs, not recomputed by this website."],
    ["Implementation", "Next available trading day", `Signal ${fmtDate(item?.signal_date ?? "")} → effective ${fmtDate(item?.effective_date ?? "")}. Transaction costs follow the saved traded-notional convention.`],
  ];
  return <section className="section explorer-section" id="decision"><div className="shell">
    <div className="section-head"><span className="section-index">06 — Historical explorer</span><div><h2>Go inside<br />a model decision.</h2><p className="section-copy">Move through the saved record. Signals, targets, effective holdings and risk remain dated separately. Nothing here is a live recommendation.</p></div></div>
    <div className="episode-pills" role="group" aria-label="Focus research on a historical episode"><button type="button" className={!period ? "active" : ""} aria-pressed={!period} onClick={() => { setPlaying(false); selectPeriod(""); }}>Full history</button>{data.regimeAnalysis.periods.map(p => <button key={p.id} type="button" className={p.id === view.period ? "active" : ""} aria-pressed={p.id === view.period} onClick={() => { setPlaying(false); selectPeriod(p.id); }}>{p.label.split(" ")[0].replace("-", "–")}</button>)}</div>
    <div className="explorer-console">
      <div className="explorer-toolbar"><DateInspector date={view.date} first={data.meta.start_date} last={data.meta.end_date} onSelect={date => { setPlaying(false); selectDate(date); }} /><label>Observable rebalance<select aria-label="Observable rebalance" value={index} onChange={e => selectIndex(Number(e.target.value))}>{rebalances.map((r, i) => <option value={i} key={r.signal_date}>{r.signal_date} → {r.effective_date}</option>)}</select></label><button className="outline-button" type="button" onClick={() => { if (index === rebalances.length - 1) selectDate(rebalances[0].signal_date); setPlaying(!playing); }}>{playing ? "Pause replay" : "Play monthly replay"} {playing ? "Ⅱ" : "▷"}</button></div>
      <div className="replay-control"><button type="button" className="text-button" disabled={index === 0} aria-label="Previous rebalance" onClick={() => selectIndex(index - 1)}>←</button><label className="replay-range"><span className="sr-only">Historical rebalance timeline</span><input aria-label="Historical rebalance timeline" type="range" min="0" max={rebalances.length - 1} value={index} onChange={e => selectIndex(Number(e.target.value))} aria-valuetext={fmtDate(rebalance.signal_date)} /><span>{rebalances[0].effective_date.slice(0, 4)}<b>{index + 1} / {rebalances.length} saved rebalances</b>{rebalances.at(-1)?.effective_date.slice(0, 4)}</span></label><button type="button" className="text-button" disabled={index === rebalances.length - 1} aria-label="Next rebalance" onClick={() => selectIndex(index + 1)}>→</button></div>
      <div className="snapshot-readouts" aria-live="polite"><div><span className="mini-label">NAV observation · {fmtDate(selected.nav?.date ?? "")}</span><strong>{fmtNumber(selected.nav?.strategy_net, 3)}</strong><small>AGG {fmtNumber(selected.nav?.benchmark, 3)} · original base</small></div><div><span className="mini-label">Risk observation · {fmtDate(selected.risk?.date ?? "")}</span><strong>{fmtPct(selected.risk?.strategy_drawdown)}</strong><small>Drawdown from previous peak</small></div><div><span className="mini-label">Effective holdings · {fmtDate(selected.weights?.date ?? "")}</span><div className="allocation-ribbon" aria-hidden="true">{ASSETS.map(a => <i key={a} style={{ width: `${(selected.weights?.[a] ?? 0) * 100}%`, background: ASSET_COLORS[a] }} />)}</div><small>{ASSETS.map(a => `${a} ${fmtPct(selected.weights?.[a], 1)}`).join(" · ")}</small></div></div>
    </div>
    {item && <><div className="decision-focus"><div><span className="mini-label">Signal observed</span><h3>{fmtDate(item.signal_date)}</h3><p>Weights effective {fmtDate(item.effective_date)}</p><span className="snapshot-pill">{diagnostic ? "Saved material-change diagnostic" : "Observable rebalance"}</span></div><WeightComparison item={item} /></div>
    <div className="walkthrough"><div className="walkthrough-steps" role="group" aria-label="Decision explanation stages">{stages.map(([name], i) => <button key={name} type="button" className={step === i ? "active" : ""} aria-pressed={step === i} onClick={() => setStep(i)}><span>0{i + 1}</span>{name}</button>)}</div><div className="walkthrough-copy" aria-live="polite"><span className="mini-label">{stages[step][0]}</span><h3>{stages[step][1]}</h3><p>{stages[step][2]}</p></div></div>
    <div className="research-scroll"><table className="research-table"><caption className="sr-only">Saved inputs and target weights for {item.signal_date}</caption><thead><tr><th>Asset</th><th>Momentum</th><th>Eligible</th><th>Realized vol.</th><th>Previous</th><th>New target</th><th>Change</th></tr></thead><tbody>{ASSETS.map(a => <tr key={a}><th scope="row">{a}</th><td>{fmtPctSigned(item.momentum[a])}</td><td>{item.eligibility[a] ? "Yes" : "No"}</td><td>{fmtPct(item.realized_volatility[a])}</td><td>{fmtPct(item.previous_allocation[a])}</td><td>{fmtPct(item.new_allocation[a])}</td><td>{fmtPctSigned(item.weight_change[a])}</td></tr>)}</tbody></table></div><details><summary>{diagnostic ? "Read the recorded decision explanation" : "Inspect observable rebalance details"}</summary><p>{item.explanations.join(" ")}</p><div className="research-footfacts"><span>Gross traded notional<strong>{fmtPct(item.trading_notional)}</strong></span><span>Transaction cost<strong>{(item.transaction_cost * 10_000).toFixed(3)} bps of NAV</strong></span></div></details></>}
    <p className="research-caption">{data.signalDiagnostics.records.length} material-change diagnostics within {data.signalDiagnostics.total_observable_rebalances} observable rebalances. Material-change diagnostic scope: {data.signalDiagnostics.methodology.note} A requested date resolves to observations on or before that date; actual observation dates are always shown.</p>
    <div className="explorer-chart-grid"><div><h3>Performance context</h3><ConnectedNavChart /></div><div><h3>Effective allocation context</h3><AllocationChart /></div></div>
  </div></section>;
}

export function CurveComparison() {
  const { data, view, update } = useResearch();
  const series = data.yieldCurve.monthly_series;
  const selected = series.find(p => p.date === view.curve) ?? series.at(-1)!;
  const comparison = series.find(p => p.date === view.compare);
  const chart = [{ maturity: "2Y", selected: selected.two_year, comparison: comparison?.two_year }, { maturity: "5Y", selected: selected.five_year, comparison: comparison?.five_year }, { maturity: "10Y", selected: selected.ten_year, comparison: comparison?.ten_year }];
  return <div className="curve-comparison"><div className="research-subhead"><div><span className="mini-label">Curve explorer</span><h3>Same maturities. Different dates.</h3></div></div><div className="explorer-toolbar"><label>Curve date<select aria-label="Curve date" value={selected.date} onChange={e => update({ curve: e.target.value })}>{series.map(p => <option key={p.date} value={p.date}>{p.date}</option>)}</select></label><label>Compare with<select aria-label="Compare Treasury curve with" value={comparison?.date ?? ""} onChange={e => update({ compare: e.target.value })}><option value="">No comparison</option>{series.map(p => <option key={p.date} value={p.date}>{p.date}</option>)}</select></label><button className="text-button" type="button" onClick={() => update({ curve: observationAtOrBefore(series, view.date)?.date ?? series[0].date })}>Use research date ↗</button></div><label className="curve-range"><span className="sr-only">Treasury curve month</span><input type="range" aria-label="Treasury curve month" min="0" max={series.length - 1} value={series.findIndex(p => p.date === selected.date)} onChange={e => update({ curve: series[Number(e.target.value)].date })} aria-valuetext={selected.date} /></label><ChartFrame title="Treasury yields by maturity" className="research-chart" dateSelection={false}><ResponsiveContainer width="100%" height="100%"><LineChart data={chart} margin={{ top: 20, left: 0, right: 24, bottom: 0 }}><CartesianGrid vertical={false} stroke="var(--chart-grid)" /><XAxis dataKey="maturity" tick={tick} axisLine={false} tickLine={false} /><YAxis tick={tick} tickFormatter={v => `${Number(v).toFixed(1)}%`} width={50} axisLine={false} tickLine={false} /><Tooltip formatter={(v, name) => [`${Number(v).toFixed(2)}%`, String(name)]} /><Line dataKey="selected" name={selected.date} stroke="#1768e5" strokeWidth={3} dot={{ r: 5 }} isAnimationActive={false} />{comparison && <Line dataKey="comparison" name={comparison.date} stroke="#45a6b5" strokeDasharray="5 5" strokeWidth={2} dot={{ r: 4 }} isAnimationActive={false} />}</LineChart></ResponsiveContainer></ChartFrame><div className="curve-readout"><strong>{fmtDate(selected.date)}</strong><span>2Y {selected.two_year?.toFixed(2) ?? "—"}%</span><span>5Y {selected.five_year?.toFixed(2) ?? "—"}%</span><span>10Y {selected.ten_year?.toFixed(2) ?? "—"}%</span><span>2s10s {selected.slope_2s10s.toFixed(2)} pp</span>{comparison && <span>Dashed: {fmtDate(comparison.date)}</span>}</div><p className="research-caption">Three saved Treasury par-yield observations per curve. Lines connect the published maturities; they are not fitted yield curves. Monthly dates are actual published observations, not interpolated values.</p></div>;
}

export function ConfigurationComparison() {
  const { data, view, update } = useResearch();
  const selected = data.sensitivity.results.find(r => r.configuration_id === view.config) ?? data.sensitivity.results[0];
  const baseline = data.sensitivity.results.find(r => r.is_baseline)!;
  const measures = [["CAGR", "cagr", "pct"], ["Volatility", "annualized_volatility", "pct"], ["Sharpe", "sharpe_ratio", "num"], ["Max drawdown", "maximum_drawdown", "pct"]] as const;
  return <div className="configuration-comparison"><div className="research-controls"><label className="date-select">Compare a saved configuration<select aria-label="Saved configuration" value={selected.configuration_id} onChange={e => update({ config: e.target.value })}>{data.sensitivity.results.map(r => <option key={r.configuration_id} value={r.configuration_id}>{r.parameters.momentum_window_days}D / {r.parameters.volatility_window_days}D{r.is_baseline ? " · baseline" : ""}</option>)}</select></label><span className="snapshot-pill">No optimization or live recalculation</span></div><div className="comparison-metrics">{measures.map(([label, key, format]) => <div key={key}><span className="mini-label">{label}</span><strong>{format === "pct" ? fmtPct(selected.metrics[key]) : fmtNumber(selected.metrics[key], 2)}</strong><small>Baseline {format === "pct" ? fmtPct(baseline.metrics[key]) : fmtNumber(baseline.metrics[key], 2)}</small></div>)}</div><p className="research-caption">Common comparison window: {fmtDate(data.sensitivity.methodology.common_evaluation_start_date)} – {fmtDate(data.sensitivity.methodology.common_evaluation_end_date)}. This differs from the headline full-history window. {data.sensitivity.methodology.common_window_note}</p></div>;
}

export function MonthlyHeatmap() {
  const { data, view, selectDate } = useResearch();
  const [expanded, setExpanded] = useState(false);
  const years = [...new Set(data.monthlyReturns.map(r => r.year))];
  const rows = expanded ? years : years.slice(-7);
  const selected = data.monthlyReturns.find(r => `${r.year}-${String(r.month).padStart(2, "0")}` === view.date.slice(0, 7));
  return <div className="monthly-heatmap"><div className="research-subhead"><div><span className="mini-label">Saved calendar returns</span><h3>The month-by-month texture.</h3></div><button type="button" className="text-button" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? "Show recent years" : "Show full history"} {expanded ? "−" : "+"}</button></div><p className="heatmap-readout" aria-live="polite">{selected ? `${MONTH_NAMES[selected.month - 1]} ${selected.year} · strategy net ${fmtPctSigned(selected.return)}` : "Select a month to inspect its saved strategy return."}</p><div className="research-scroll"><table className="heatmap-table"><caption className="sr-only">Saved monthly strategy net returns. Select a month to update the shared historical date.</caption><thead><tr><th scope="col">Year</th>{MONTH_NAMES.map(m => <th scope="col" key={m}>{m}</th>)}</tr></thead><tbody>{rows.map(year => <tr key={year}><th scope="row">{year}</th>{MONTH_NAMES.map((m, i) => {
    const record = data.monthlyReturns.find(r => r.year === year && r.month === i + 1);
    const month = `${year}-${String(i + 1).padStart(2, "0")}`;
    // Use the last saved NAV observation in this month; never manufacture a date.
    const lastDate = observationAtOrBefore(data.nav, `${month}-31`)?.date;
    const available = record?.return != null && lastDate?.startsWith(month);
    return <td key={m}>{available ? <button type="button" aria-label={`${m} ${year}, strategy net return ${fmtPctSigned(record.return)}`} aria-pressed={view.date.startsWith(month)} onClick={() => selectDate(lastDate!)} style={{ background: record.return! >= 0 ? `rgba(23,104,229,${Math.min(.65, .07 + Math.abs(record.return!) * 14)})` : `rgba(172,83,54,${Math.min(.65, .07 + Math.abs(record.return!) * 14)})` }}>{fmtPct(record.return, 1)}</button> : <span aria-label={`${m} ${year}: no saved return`}>—</span>}</td>;
  })}</tr>)}</tbody></table></div><p className="research-caption">Blue: positive · warm: negative · numbers convey the result independently of colour. Latest month may be partial through {fmtDate(data.meta.end_date)}. Missing months remain blank; no new returns are calculated.</p></div>;
}
