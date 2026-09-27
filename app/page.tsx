import { promises as fs } from "fs";
import path from "path";
import type { DashboardData } from "@/types/data";
import Hero from "@/components/Hero";
import ExecutiveOverview from "@/components/ExecutiveOverview";
import StrategyOverview from "@/components/StrategyOverview";
import PerformanceSection from "@/components/PerformanceSection";
import RiskAnalysis from "@/components/RiskAnalysis";
import SignalGeneration from "@/components/SignalGeneration";
import PortfolioImplementation from "@/components/PortfolioImplementation";
import RegimeAnalysis from "@/components/RegimeAnalysis";
import ParameterSensitivity from "@/components/ParameterSensitivity";
import ResearcherView from "@/components/ResearcherView";
import DataMethodology from "@/components/DataMethodology";
import Limitations from "@/components/Limitations";
import References from "@/components/References";

// Load all JSON data at build time / server render
async function loadData(): Promise<DashboardData> {
  const dataDir = path.join(process.cwd(), "public", "data");

  async function readJson<T>(filename: string): Promise<T> {
    const content = await fs.readFile(path.join(dataDir, filename), "utf-8");
    return JSON.parse(content) as T;
  }

  const [summary, nav, annualReturns, monthlyReturns, rollingMetrics, signals, weights, rebalanceLog, volatility, meta, sensitivity, regimeAnalysis, researcherView, references] =
    await Promise.all([
      readJson("summary_stats.json"),
      readJson("nav_series.json"),
      readJson("annual_returns.json"),
      readJson("monthly_returns.json"),
      readJson("rolling_metrics.json"),
      readJson("signals.json"),
      readJson("weights.json"),
      readJson("rebalance_log.json"),
      readJson("volatility.json"),
      readJson("meta.json"),
      readJson("sensitivity.json"),
      readJson("regime_analysis.json"),
      readJson("researcher_view.json"),
      readJson("references.json"),
    ]);

  return {
    summary: summary as DashboardData["summary"],
    nav: nav as DashboardData["nav"],
    annualReturns: annualReturns as DashboardData["annualReturns"],
    monthlyReturns: monthlyReturns as DashboardData["monthlyReturns"],
    rollingMetrics: rollingMetrics as DashboardData["rollingMetrics"],
    signals: signals as DashboardData["signals"],
    weights: weights as DashboardData["weights"],
    rebalanceLog: rebalanceLog as DashboardData["rebalanceLog"],
    volatility: volatility as DashboardData["volatility"],
    meta: meta as DashboardData["meta"],
    sensitivity: sensitivity as DashboardData["sensitivity"],
    regimeAnalysis: regimeAnalysis as DashboardData["regimeAnalysis"],
    researcherView: researcherView as DashboardData["researcherView"],
    references: references as DashboardData["references"],
  };
}

export default async function DashboardPage() {
  let data: DashboardData;

  try {
    data = await loadData();
  } catch (err) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <div className="max-w-lg bg-slate-800 border border-slate-700 rounded-xl p-8">
          <h1 className="text-xl font-semibold text-red-400 mb-4">Data Not Found</h1>
          <p className="text-slate-400 text-sm mb-4">
            The analytics pipeline has not been run yet, or the data files are missing.
          </p>
          <p className="text-slate-500 text-sm mb-4">Run the analytics pipeline first:</p>
          <pre className="bg-slate-900 rounded p-4 text-xs text-slate-300 overflow-x-auto">
{`python run_pipeline.py`}
          </pre>
          <p className="text-slate-600 text-xs mt-4">
            Error: {err instanceof Error ? err.message : String(err)}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="divide-y divide-slate-800/60">
      {/* 01 — Hero */}
      <Hero meta={data.meta} />

      {/* 02 — Executive Overview */}
      <ExecutiveOverview summary={data.summary} meta={data.meta} />

      {/* 03 — Strategy */}
      <StrategyOverview meta={data.meta} />

      {/* 04 — Performance */}
      <PerformanceSection
        nav={data.nav}
        annualReturns={data.annualReturns}
        monthlyReturns={data.monthlyReturns}
        rollingMetrics={data.rollingMetrics}
      />

      {/* 05 — Risk Analysis */}
      <RiskAnalysis rollingMetrics={data.rollingMetrics} />

      {/* 06 — Signal Generation */}
      <SignalGeneration
        signals={data.signals}
        rebalanceLog={data.rebalanceLog}
        researcherView={data.researcherView}
      />

      {/* 07 — Portfolio Implementation */}
      <PortfolioImplementation
        signals={data.signals}
        weights={data.weights}
        rebalanceLog={data.rebalanceLog}
      />

      {/* 08 — Market Regime Analysis */}
      <RegimeAnalysis data={data.regimeAnalysis} />

      {/* 09 — Parameter Sensitivity */}
      <ParameterSensitivity data={data.sensitivity} />

      {/* 10 — Researcher's View */}
      <ResearcherView data={data.researcherView} />

      {/* 11 — Data & Methodology */}
      <DataMethodology meta={data.meta} />

      {/* 12 — Limitations */}
      <Limitations />

      {/* 13 — References */}
      <References data={data.references} />
    </div>
  );
}
