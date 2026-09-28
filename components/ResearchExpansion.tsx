"use client";

import { useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DashboardData } from "@/types/data";
import { fmtDate, fmtNumber, fmtPct, fmtPctSigned } from "@/lib/formatters";

const BLUE = "#1768e5";
const GREY = "#8493a5";
const assets = ["SHY", "IEF", "TLT"] as const;
const tick = { fontSize: 10, fill: "#757d86" };

function Intro({ n, eyebrow, title, copy }: { n: string; eyebrow: string; title: string; copy: string }) {
  return <div className="section-head"><div className="section-index">{n} — {eyebrow}</div><div><h2>{title}</h2><p className="section-copy">{copy}</p></div></div>;
}

function Chart({ children, label }: { children: React.ReactNode; label: string }) {
  return <div className="research-chart" role="img" aria-label={label}><ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer></div>;
}

export function CurveSection({ data }: { data: DashboardData["yieldCurve"] }) {
  const [mode, setMode] = useState<"level" | "slope" | "curvature">("level");
  const [window, setWindow] = useState<"all" | "10" | "5">("all");
  const [asset, setAsset] = useState<(typeof assets)[number]>("SHY");
  const chart = useMemo(() => {
    const cutoff = window === "all" ? "0000-01-01" : `${Number(data.last_date.slice(0, 4)) - Number(window)}-01-01`;
    return data.monthly_series.filter(point => point.date >= cutoff);
  }, [data, window]);
  const relation = data.allocation_context.filter((_, index) => index % 2 === 0 || index === data.allocation_context.length - 1);
  const series = mode === "level" ? [
    { key: "two_year", label: "2Y", color: "#a8b5c2" }, { key: "five_year", label: "5Y", color: "#6c88ac" },
    { key: "ten_year", label: "10Y", color: BLUE },
  ] : mode === "slope" ? [
    { key: "slope_2s10s", label: "2s10s", color: BLUE }, { key: "slope_5s10s", label: "5s10s", color: GREY },
  ] : [{ key: "curvature", label: "2×5Y − 2Y − 10Y", color: BLUE }];
  return <section className="section" id="curve"><div className="shell">
    <Intro n="03" eyebrow="The curve" title="The rate environment, observed." copy="U.S. Treasury par yields frame the historical setting around the model. The curve is context—not an input to the baseline allocation rule." />
    <div className="research-controls"><div className="segmented" role="group" aria-label="Curve measure">{(["level", "slope", "curvature"] as const).map(value => <button key={value} type="button" className={mode === value ? "active" : ""} aria-pressed={mode === value} onClick={() => setMode(value)}>{value}</button>)}</div><div className="segmented" role="group" aria-label="Historical window">{(["all", "10", "5"] as const).map(value => <button key={value} type="button" className={window === value ? "active" : ""} aria-pressed={window === value} onClick={() => setWindow(value)}>{value === "all" ? "Full" : `${value}Y`}</button>)}</div></div>
    <div className="research-stat"><span className="mini-label">Latest 2s10s slope · {fmtDate(data.latest.date)}</span><strong className="number">{data.latest.slope_2s10s.toFixed(2)} <small>pp</small></strong></div>
    <Chart label={`Historical Treasury yield curve ${mode}, ${window === "all" ? "full period" : `last ${window} years`}`}><LineChart data={chart} margin={{ left: 0, right: 14, top: 8, bottom: 0 }}><CartesianGrid vertical={false} stroke="#e2e1dc" /><XAxis dataKey="date" tick={tick} axisLine={false} tickLine={false} minTickGap={48} tickFormatter={value => String(value).slice(0, 4)} /><YAxis tick={tick} axisLine={false} tickLine={false} width={48} tickFormatter={value => `${Number(value).toFixed(1)}${mode === "level" ? "%" : "pp"}`} /><Tooltip formatter={(value, name) => [`${Number(value).toFixed(2)}${mode === "level" ? "%" : " pp"}`, String(name)]} labelFormatter={value => fmtDate(String(value))} />{series.map(line => <Line key={line.key} dataKey={line.key} name={line.label} stroke={line.color} strokeWidth={line.key === "ten_year" || series.length === 1 ? 2.3 : 1.4} dot={false} isAnimationActive={false} />)}</LineChart></Chart>
    <p className="research-caption">{data.methodology.convention} Values are percentage points. Monthly display uses the last published observation; no missing tenors are filled. {data.daily_observations.toLocaleString()} daily common observations from {fmtDate(data.first_date)} to {fmtDate(data.last_date)}.</p>
    <div className="research-subhead"><div><span className="mini-label">Historical relationship</span><h3>Curve context &amp; observed allocation</h3></div><div className="segmented" role="group" aria-label="Allocation asset">{assets.map(value => <button key={value} type="button" className={asset === value ? "active" : ""} aria-pressed={asset === value} onClick={() => setAsset(value)}>{value}</button>)}</div></div>
    <Chart label={`Historical 2s10s slope alongside observed ${asset} allocation`}><LineChart data={relation} margin={{ left: 0, right: 0, top: 8, bottom: 0 }}><CartesianGrid vertical={false} stroke="#e2e1dc" /><XAxis dataKey="date" tick={tick} axisLine={false} tickLine={false} minTickGap={55} tickFormatter={value => String(value).slice(0, 4)} /><YAxis yAxisId="slope" tick={tick} axisLine={false} tickLine={false} width={48} tickFormatter={value => `${Number(value).toFixed(1)}pp`} /><YAxis yAxisId="weight" orientation="right" tick={tick} axisLine={false} tickLine={false} width={40} domain={[0, 1]} tickFormatter={value => `${Math.round(Number(value) * 100)}%`} /><Tooltip formatter={(value, name) => [String(name) === "2s10s" ? `${Number(value).toFixed(2)} pp` : fmtPct(Number(value)), String(name)]} labelFormatter={value => fmtDate(String(value))} /><Line yAxisId="slope" dataKey="slope_2s10s" name="2s10s" stroke={GREY} dot={false} isAnimationActive={false} /><Line yAxisId="weight" dataKey={asset} name={`${asset} weight`} stroke={BLUE} strokeWidth={2} dot={false} isAnimationActive={false} /></LineChart></Chart>
    <p className="research-caption">Exact-date Treasury and model-weight observations, sampled at each month’s last shared trading date. Co-movement does not imply the curve caused a model decision.</p>
    <details><summary>Curve context across four historical periods</summary><div className="research-scroll"><table className="research-table"><thead><tr><th>Period</th><th>Average 10Y</th><th>Average 2s10s</th><th>Ending 2s10s</th><th>Average SHY</th><th>Strategy vol.</th></tr></thead><tbody>{data.regime_context.map(period => <tr key={period.id}><th scope="row">{period.label}</th><td>{period.average_10y_yield.toFixed(2)}%</td><td>{period.average_2s10s.toFixed(2)} pp</td><td>{period.ending_2s10s.toFixed(2)} pp</td><td>{fmtPct(period.average_allocation.SHY)}</td><td>{fmtPct(period.strategy_annualized_volatility)}</td></tr>)}</tbody></table></div><p className="research-caption">These are observed period averages, not macroeconomic explanations or evidence that the curve drove allocation.</p></details>
  </div></section>;
}

export function DecisionSection({ data }: { data: DashboardData["signalDiagnostics"] }) {
  const [selected, setSelected] = useState(Math.max(0, data.records.length - 1));
  const item = data.records[selected];
  return <section className="section" id="decision"><div className="shell">
    <Intro n="06" eyebrow="Decision trace" title="Why did the model move?" copy="Each visible change follows a dated signal, eligibility and inverse-volatility calculation. This trace reports only conditions present in the saved decision record." />
    <div className="research-controls"><label className="date-select">Select a rebalance<select value={selected} onChange={event => setSelected(Number(event.target.value))}>{data.records.map((record, index) => <option value={index} key={record.signal_date}>{fmtDate(record.signal_date)} → {fmtDate(record.effective_date)}</option>)}</select></label><span className="research-caption">{data.records.length} material changes / {data.total_observable_rebalances} observable rebalances</span></div>
    {item && <><div className="decision-path"><div><span className="mini-label">Previous state</span><strong>{item.previous_signal_date ? fmtDate(item.previous_signal_date) : "Initial"}</strong></div><span aria-hidden="true">→</span><div><span className="mini-label">Signal observed</span><strong>{fmtDate(item.signal_date)}</strong></div><span aria-hidden="true">→</span><div><span className="mini-label">Weights effective</span><strong>{fmtDate(item.effective_date)}</strong></div></div>
    <div className="research-scroll"><table className="research-table"><thead><tr><th>Asset</th><th>Momentum</th><th>Eligible</th><th>Realized vol.</th><th>Previous</th><th>New target</th><th>Change</th></tr></thead><tbody>{assets.map(asset => <tr key={asset}><th scope="row">{asset}</th><td>{fmtPctSigned(item.momentum[asset])}</td><td>{item.eligibility[asset] ? "Yes" : "No"}</td><td>{fmtPct(item.realized_volatility[asset])}</td><td>{fmtPct(item.previous_allocation[asset])}</td><td>{fmtPct(item.new_allocation[asset])}</td><td>{fmtPctSigned(item.weight_change[asset])}</td></tr>)}</tbody></table></div>
    <p className="decision-explanation">{item.explanations.join(" ")}</p><div className="research-footfacts"><span>Gross traded notional <strong>{fmtPct(item.trading_notional)}</strong></span><span>Transaction cost <strong>{(item.transaction_cost * 10_000).toFixed(3)} bps of NAV</strong></span></div></>}
    <p className="research-caption">{data.methodology.note}</p>
  </div></section>;
}

export function HoldoutSection({ data }: { data: DashboardData["holdout"] }) {
  const entries = (["full", "development", "holdout"] as const).map(key => ({ key, ...data.periods[key] }));
  const rows: Array<[string, keyof DashboardData["holdout"]["periods"]["full"]["strategy"], "pct" | "num"]> = [
    ["Cumulative return", "cumulative_return", "pct"], ["CAGR", "cagr", "pct"], ["Annualized volatility", "annualized_volatility", "pct"],
    ["Sharpe · Rf 0%", "sharpe_ratio", "num"], ["Maximum drawdown", "maximum_drawdown", "pct"],
    ["Monthly win rate", "monthly_win_rate", "pct"], ["One-way turnover", "one_way_turnover", "pct"], ["Rebalances", "number_of_rebalances", "num"],
  ];
  return <section className="section" id="holdout"><div className="shell">
    <Intro n="12" eyebrow="The holdout" title="The same rules, in a later period." copy="Fixed parameters are evaluated over the full history, a development window, and a later holdout. No parameter was selected using holdout results." />
    <div className="research-scroll"><table className="research-table holdout-table"><thead><tr><th>Measure</th>{entries.map(entry => <th key={entry.key}>{entry.key}<small>{fmtDate(entry.start_date)} – {fmtDate(entry.end_date)}</small></th>)}</tr></thead><tbody>{rows.map(([label, key, format]) => <tr key={label}><th scope="row">{label}</th>{entries.map(entry => <td key={entry.key}><strong>{format === "pct" ? fmtPct(entry.strategy[key]) : fmtNumber(entry.strategy[key], key === "number_of_rebalances" ? 0 : 2)}</strong><small>AGG {format === "pct" ? fmtPct(entry.benchmark[key]) : fmtNumber(entry.benchmark[key], key === "number_of_rebalances" ? 0 : 2)}</small></td>)}</tr>)}</tbody></table></div>
    <p className="research-caption">{data.methodology.note} Turnover and rebalance counts refer to the strategy; AGG is passive (zero modeled turnover/rebalances). This is not a claim of statistically independent parameter optimization.</p>
  </div></section>;
}

export function RateShockSection({ data }: { data: DashboardData["rateShock"] }) {
  const [basisPoints, setBasisPoints] = useState(50);
  const [allocation, setAllocation] = useState<"current_model_target" | "latest_effective">("current_model_target");
  const selected = data.allocations[allocation];
  const scenario = selected.scenarios.find(item => item.shock_bps === basisPoints) ?? selected.scenarios[2];
  return <section className="section dark" id="rate-shock"><div className="shell">
    <Intro n="14" eyebrow="Rate shock lab" title="What would a parallel yield shift imply?" copy="A transparent, duration-only price approximation applies an identical hypothetical Treasury-yield shift to each ETF at the displayed model allocation." />
    <div className="research-controls"><div className="segmented dark-segmented" role="group" aria-label="Hypothetical parallel yield shift">{selected.scenarios.map(item => <button key={item.shock_bps} type="button" aria-pressed={basisPoints === item.shock_bps} className={basisPoints === item.shock_bps ? "active" : ""} onClick={() => setBasisPoints(item.shock_bps)}>{item.shock_bps > 0 ? "+" : ""}{item.shock_bps}</button>)}</div><div className="segmented dark-segmented" role="group" aria-label="Model allocation">{(["current_model_target", "latest_effective"] as const).map(value => <button key={value} type="button" aria-pressed={allocation === value} className={allocation === value ? "active" : ""} onClick={() => setAllocation(value)}>{value === "current_model_target" ? "Current target" : "Latest effective"}</button>)}</div></div>
    <div className="shock-result"><div><span className="mini-label">Hypothetical portfolio price impact</span><strong className="number">{fmtPctSigned(scenario.portfolio_impact)}</strong><p>{basisPoints > 0 ? "+" : ""}{basisPoints} bps · allocation dated {fmtDate(selected.as_of)}</p></div><div className="shock-assets">{assets.map(asset => <div key={asset}><span>{asset} <small>{fmtPct(selected.weights[asset], 0)} weight · {data.durations[asset].years.toFixed(2)}y duration</small></span><strong className="number">{fmtPctSigned(scenario.asset_impact[asset])}</strong></div>)}</div></div>
    <p className="research-caption">{data.methodology.label}. {data.methodology.formula}. Issuer-published effective durations dated {fmtDate(data.methodology.duration_as_of)}. {data.methodology.limitations}</p>
    <details><summary>Duration sources and definition</summary><div className="shock-sources">{assets.map(asset => <a key={asset} href={data.durations[asset].source} target="_blank" rel="noreferrer">{asset} · iShares effective duration ↗</a>)}</div></details>
  </div></section>;
}

export function FailureSection({ data }: { data: DashboardData["failureModes"] }) {
  const [selected, setSelected] = useState(0);
  const event = data.events[selected];
  const chart = data.drawdown_series;
  return <section className="section" id="pressure"><div className="shell">
    <Intro n="09" eyebrow="Failure modes" title="When the model was under pressure." copy="Adverse periods are part of the record. Episodes below are ranked by observed strategy drawdown, not filtered to favor the model." />
    <Chart label="Net strategy drawdown through the full backtest"><LineChart data={chart} margin={{ left: 0, right: 10, top: 8, bottom: 0 }}><CartesianGrid vertical={false} stroke="#e2e1dc" /><XAxis dataKey="date" tick={tick} axisLine={false} tickLine={false} minTickGap={55} tickFormatter={value => String(value).slice(0, 4)} /><YAxis tick={tick} axisLine={false} tickLine={false} width={45} tickFormatter={value => fmtPct(Number(value), 0)} /><Tooltip formatter={value => [fmtPct(Number(value)), "Strategy drawdown"]} labelFormatter={value => fmtDate(String(value))} /><Line type="monotone" dataKey="strategy_drawdown" stroke={BLUE} strokeWidth={2} dot={false} isAnimationActive={false} /></LineChart></Chart>
    <div className="research-controls"><label className="date-select">Drawdown episode<select value={selected} onChange={event => setSelected(Number(event.target.value))}>{data.events.map((item, index) => <option key={`${item.start_date}-${index}`} value={index}>{fmtDate(item.start_date)} · {fmtPct(item.drawdown)}</option>)}</select></label></div>
    {event && <><div className="failure-hero"><div><span className="mini-label">Peak-to-trough drawdown</span><strong className="number">{fmtPct(event.drawdown)}</strong></div><p>Peak {fmtDate(event.start_date)}<br />Trough {fmtDate(event.trough_date)}<br />{event.recovery_date ? `Recovered ${fmtDate(event.recovery_date)}` : "Not recovered by sample end"}</p></div><div className="research-footfacts"><span>Strategy peak-to-trough <strong>{fmtPct(event.strategy_return)}</strong></span><span>AGG, same dates <strong>{fmtPct(event.benchmark_return)}</strong></span></div><div className="failure-state"><h3>Observed during the drawdown</h3><div className="failure-weights">{assets.map(asset => <div key={asset}><span>{asset} average / trough weight</span><strong>{fmtPct(event.average_allocation[asset])} / {fmtPct(event.allocation_at_trough[asset])}</strong><small>Signal {event.signal_state_at_trough?.eligibility[asset] ? "eligible" : "not eligible"} · momentum {fmtPctSigned(event.signal_state_at_trough?.momentum[asset])} · realized vol. {fmtPct(event.signal_state_at_trough?.realized_volatility[asset])}</small></div>)}</div><p className="research-caption">Latest observable signal by the trough: {fmtDate(event.signal_state_at_trough?.signal_date ?? "")}. These are descriptive states, not an attributed cause.</p></div></>}
    <details><summary>Worst calendar months, quarters &amp; relative windows</summary><div className="failure-lists"><div><h3>Worst months</h3>{data.worst_months.map(item => <p key={item.period}>{item.period}<strong>{fmtPct(item.strategy_return)}</strong><small>AGG {fmtPct(item.benchmark_return)}</small></p>)}</div><div><h3>Worst quarters</h3>{data.worst_quarters.map(item => <p key={item.period}>{item.period}<strong>{fmtPct(item.strategy_return)}</strong><small>AGG {fmtPct(item.benchmark_return)}</small></p>)}</div><div><h3>Relative underperformance · 63 days</h3>{data.underperformance_windows.map(item => <p key={item.end_date}>{fmtDate(item.start_date)} – {fmtDate(item.end_date)}<strong>{fmtPct(item.active_return)}</strong><small>Strategy {fmtPct(item.strategy_return)} · AGG {fmtPct(item.benchmark_return)}</small></p>)}</div></div><p className="research-caption">{data.methodology.underperformance} Neighboring windows may describe the same episode.</p></details>
  </div></section>;
}
