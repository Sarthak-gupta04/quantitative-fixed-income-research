import { promises as fs } from "fs";
import path from "path";
import ResearchStory from "@/components/ResearchStory";
import type { DashboardData } from "@/types/data";

async function loadData(): Promise<DashboardData> {
  const directory = path.join(process.cwd(), "public", "data");
  const read = async <T,>(name: string): Promise<T> =>
    JSON.parse(await fs.readFile(path.join(directory, name), "utf8")) as T;
  const [summary, nav, rollingMetrics, weights, meta, sensitivity, regimeAnalysis, researcherView, references, yieldCurve, holdout, rateShock, signalDiagnostics, failureModes] = await Promise.all([
    read("summary_stats.json"), read("nav_series.json"), read("rolling_metrics.json"), read("weights.json"),
    read("meta.json"), read("sensitivity.json"), read("regime_analysis.json"),
    read("researcher_view.json"), read("references.json"),
    read("yield_curve.json"), read("holdout_analysis.json"), read("rate_shock.json"),
    read("signal_diagnostics.json"), read("failure_modes.json"),
  ]);
  return { summary, nav, rollingMetrics, weights, meta, sensitivity, regimeAnalysis, researcherView, references, yieldCurve, holdout, rateShock, signalDiagnostics, failureModes } as DashboardData;
}

export default async function Page() {
  return <ResearchStory data={await loadData()} />;
}
