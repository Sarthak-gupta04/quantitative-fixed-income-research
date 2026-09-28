import { promises as fs } from "fs";
import path from "path";
import ResearchStory from "@/components/ResearchStory";
import type { DashboardData } from "@/types/data";

async function loadData(): Promise<DashboardData> {
  const directory = path.join(process.cwd(), "public", "data");
  const read = async <T,>(name: string): Promise<T> =>
    JSON.parse(await fs.readFile(path.join(directory, name), "utf8")) as T;
  const [summary, nav, annualReturns, monthlyReturns, rollingMetrics, signals, weights, rebalanceLog, volatility, meta, sensitivity, regimeAnalysis, researcherView, references] = await Promise.all([
    read("summary_stats.json"), read("nav_series.json"), read("annual_returns.json"), read("monthly_returns.json"),
    read("rolling_metrics.json"), read("signals.json"), read("weights.json"), read("rebalance_log.json"),
    read("volatility.json"), read("meta.json"), read("sensitivity.json"), read("regime_analysis.json"),
    read("researcher_view.json"), read("references.json"),
  ]);
  return { summary, nav, annualReturns, monthlyReturns, rollingMetrics, signals, weights, rebalanceLog, volatility, meta, sensitivity, regimeAnalysis, researcherView, references } as DashboardData;
}

export default async function Page() {
  return <ResearchStory data={await loadData()} />;
}
