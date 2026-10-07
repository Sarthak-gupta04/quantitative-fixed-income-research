// Lightweight, read-only frontend selection checks; no analysis or data generation.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const ts = require("typescript");
const { execFileSync } = require("node:child_process");
const source = fs.readFileSync("lib/research-view.ts", "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const box = { exports: {}, URL, URLSearchParams, Date };
vm.runInNewContext(compiled, box);
const { observationAtOrBefore, sampleWithSelection, restoreView, serializeView, isObservationDate } = box.exports;
const read = name => JSON.parse(fs.readFileSync(`public/data/${name}.json`, "utf8"));
const nav = read("nav_series");
const risk = read("rolling_metrics");
const weights = read("weights");
const signals = read("signals");
const rebalances = read("rebalance_log");
const diagnostics = read("signal_diagnostics");
const curves = read("yield_curve").monthly_series;
const sensitivity = read("sensitivity");
const meta = read("meta");
for (const series of [nav, risk, weights, signals, curves]) {
  assert(series.every((p, i) => isObservationDate(p.date) && (i === 0 || p.date > series[i - 1].date)), "Chronological saved observations");
  assert.equal(observationAtOrBefore(series, "1900-01-01"), undefined);
  assert.equal(observationAtOrBefore(series, "2999-12-31"), series.at(-1));
  for (let i = 0; i < series.length; i += 13) {
    assert.equal(observationAtOrBefore(series, series[i].date), series[i]);
    assert(sampleWithSelection(series, series[i].date).includes(series[i]), "Pinned observations survive chart sampling");
  }
}
for (const rebalance of rebalances) {
  const signal = signals.find(s => s.date === rebalance.signal_date);
  assert(signal, "Every replay rebalance has saved signals");
  assert(rebalance.effective_date > rebalance.signal_date, "Effective dates remain separate from signal dates");
  for (const a of ["SHY", "IEF", "TLT"]) {
    assert.equal(typeof signal[`eligible_${a}`], "boolean");
    assert(Number.isFinite(signal[`momentum_${a}`]));
    assert(Number.isFinite(signal[`rvol_${a}`]));
    assert(Math.abs(signal[`weight_${a}`] - rebalance[`weight_${a}`]) < 1e-12, "Replay uses saved targets");
  }
}
for (const record of diagnostics.records) {
  const rebalance = rebalances.find(r => r.signal_date === record.signal_date);
  assert(rebalance);
  for (const a of ["SHY", "IEF", "TLT"]) assert(Math.abs(record.new_allocation[a] - rebalance[`weight_${a}`]) < 1e-12);
}
const defaults = { date: rebalances.at(-1).signal_date, period: "", curve: curves.at(-1).date, compare: "", shock: 50, allocation: "current_model_target", config: sensitivity.methodology.baseline_configuration_id };
const valid = { first: meta.start_date, last: meta.end_date, periods: read("regime_analysis").periods.map(p => p.id), curves: curves.map(p => p.date), shocks: [-100,-50,0,50,100], configs: sensitivity.results.map(r => r.configuration_id) };
assert.deepEqual(JSON.parse(JSON.stringify(restoreView(new URLSearchParams("date=2022-02-31&shock=999&config=arbitrary&period=unknown&curve=bad&allocation=bad"), defaults, valid))), defaults);
assert.equal(restoreView(new URLSearchParams("shock=0"), defaults, valid).shock, 0);
assert.equal(restoreView(new URLSearchParams("date=2099-01-01"), defaults, valid).date, defaults.date);
const shared = { ...defaults, date: "2022-10-20", shock: -100, compare: curves[0].date, config: valid.configs.at(-1) };
const url = serializeView(shared, new URL("https://example.com/?utm_source=test#decision"));
assert.equal(url.hash, "#decision");
assert.equal(url.searchParams.get("utm_source"), "test");
assert.deepEqual(JSON.parse(JSON.stringify(restoreView(url.searchParams, defaults, valid))), shared);
const protectedChanges = execFileSync("git", ["diff", "--name-only", "HEAD", "--", "analytics", "tests", "public/data", "package.json", "package-lock.json"], { encoding: "utf8" }).trim();
assert.equal(protectedChanges, "", "Research, tests, saved data and dependency inputs must remain unchanged");
console.log(`PASS: chronological lookups, pinned chart samples, ${rebalances.length} observable rebalances, ${diagnostics.records.length} diagnostics, URL round-trip/invalid-input handling, protected-file integrity.`);
