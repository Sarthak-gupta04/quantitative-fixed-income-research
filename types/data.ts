// types/data.ts
// ==================
// TypeScript interfaces matching the JSON output from the Python pipeline.
// All fields are nullable to handle edge cases safely.

export interface SummaryStatsSection {
  cumulative_return: number | null;
  annualized_return: number | null;
  annualized_volatility: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  calmar_ratio: number | null;
  win_rate: number | null;
  best_day: number | null;
  worst_day: number | null;
  var_95: number | null;
  cvar_95: number | null;
  best_year: number | null;
  worst_year: number | null;
}

export interface SummaryStatsGross {
  cumulative_return: number | null;
  annualized_return: number | null;
  annualized_volatility: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
}

export interface RelativeStats {
  tracking_error: number | null;
  information_ratio: number | null;
  cumulative_active_return: number | null;
  annualized_active_return: number | null;
}

export interface SummaryStats {
  metadata: {
    generated_at_utc: string;
    start_date: string;
    end_date: string;
    trading_days: number;
    risk_free_rate_annual: number;
    transaction_cost_bps: number;
  };
  strategy_net: SummaryStatsSection;
  strategy_gross: SummaryStatsGross;
  benchmark: SummaryStatsSection;
  relative: RelativeStats;
}

export interface NavDataPoint {
  date: string;
  strategy_gross: number | null;
  strategy_net: number | null;
  benchmark: number | null;
}

export interface AnnualReturn {
  year: number;
  strategy_net: number | null;
  benchmark: number | null;
}

export interface MonthlyReturn {
  year: number;
  month: number;
  return: number | null;
}

export interface RollingMetricsPoint {
  date: string;
  strategy_rolling_vol: number | null;
  benchmark_rolling_vol: number | null;
  strategy_rolling_sharpe: number | null;
  benchmark_rolling_sharpe: number | null;
  strategy_drawdown: number | null;
  benchmark_drawdown: number | null;
  SHY_rolling_vol?: number | null;
  IEF_rolling_vol?: number | null;
  TLT_rolling_vol?: number | null;
}

export interface SignalPoint {
  date: string;
  momentum_SHY: number | null;
  momentum_IEF: number | null;
  momentum_TLT: number | null;
  rvol_SHY: number | null;
  rvol_IEF: number | null;
  rvol_TLT: number | null;
  eligible_SHY: boolean;
  eligible_IEF: boolean;
  eligible_TLT: boolean;
  weight_SHY: number | null;
  weight_IEF: number | null;
  weight_TLT: number | null;
  is_defensive: boolean;
}

export interface WeightPoint {
  date: string;
  SHY: number | null;
  IEF: number | null;
  TLT: number | null;
}

export interface RebalanceEvent {
  signal_date: string;
  effective_date: string;
  weight_SHY: number | null;
  weight_IEF: number | null;
  weight_TLT: number | null;
  weight_sum: number | null;
  turnover_oneway: number | null;
  tc_cost: number | null;
}

export interface VolatilityPoint {
  date: string;
  strategy_rolling_vol: number | null;
  benchmark_rolling_vol: number | null;
  SHY_rolling_vol?: number | null;
  IEF_rolling_vol?: number | null;
  TLT_rolling_vol?: number | null;
}

export interface MetaData {
  generated_at_utc: string;
  start_date: string;
  end_date: string;
  trading_days: number;
  tickers: string[];
  ticker_names: Record<string, string>;
  benchmark: string;
  momentum_window_days: number;
  volatility_window_days: number;
  annualization_factor: number;
  transaction_cost_bps: number;
  risk_free_rate_annual: number;
  disclaimer: string;
  download_meta?: {
    downloaded_at_utc?: string;
    tickers?: string[];
    price_field_per_ticker?: Record<string, string>;
    start_date?: string;
    end_date?: string;
    total_rows?: number;
    nan_counts?: Record<string, number>;
    notes?: string;
  };
}


export interface DashboardData {
  summary: SummaryStats;
  nav: NavDataPoint[];
  annualReturns: AnnualReturn[];
  monthlyReturns: MonthlyReturn[];
  rollingMetrics: RollingMetricsPoint[];
  signals: SignalPoint[];
  weights: WeightPoint[];
  rebalanceLog: RebalanceEvent[];
  volatility: VolatilityPoint[];
  meta: MetaData;
}
