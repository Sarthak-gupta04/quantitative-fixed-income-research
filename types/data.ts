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
    raw_price_start_date?: string;
    raw_return_start_date?: string;
    first_investable_date?: string;
    nav_base_date?: string;
    indicator_warmup_trading_days?: number;
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
  first_return_date?: string;
  next_signal_date?: string;
  weight_SHY: number | null;
  weight_IEF: number | null;
  weight_TLT: number | null;
  weight_sum: number | null;
  trading_notional: number | null;
  one_way_turnover: number | null;
  transaction_cost: number | null;
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
  raw_price_start_date?: string;
  raw_return_start_date?: string;
  first_investable_date?: string;
  nav_base_date?: string;
  indicator_warmup_trading_days?: number;
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

export interface SensitivityResult {
  configuration_id: string;
  is_baseline: boolean;
  parameters: {
    momentum_window_days: number;
    volatility_window_days: number;
    signal_to_weight_lag_days: number;
    transaction_cost_rate: number;
  };
  native_first_investable_date: string;
  evaluation_start_date: string;
  evaluation_end_date: string;
  metrics: {
    cumulative_return: number;
    cagr: number;
    annualized_volatility: number;
    sharpe_ratio: number;
    maximum_drawdown: number;
    monthly_win_rate: number;
    total_trading_notional: number;
    total_one_way_turnover: number;
    number_of_rebalances: number;
  };
}

export interface SensitivityData {
  analysis_timestamp_utc: string;
  methodology: {
    purpose: string;
    common_evaluation_start_date: string;
    common_evaluation_end_date: string;
    baseline_configuration_id: string;
    common_window_note: string;
  };
  results: SensitivityResult[];
  interpretation: {
    summary: string;
  };
}

export interface RegimePeriod {
  id: string;
  label: string;
  actual_start_date: string;
  actual_end_date: string;
  trading_days: number;
  strategy_return: number;
  benchmark_return: number;
  strategy_annualized_volatility: number;
  benchmark_annualized_volatility: number;
  strategy_maximum_drawdown: number;
  average_allocation: Record<string, number>;
  beginning_allocation: Record<string, number>;
  ending_allocation: Record<string, number>;
  number_of_rebalances: number;
  defensive_shy_allocation: {
    average_weight: number;
    fully_defensive_trading_days: number;
    fully_defensive_fraction: number;
  };
}

export interface RegimeAnalysisData {
  methodology: {
    period_definition: string;
    return_convention: string;
    naming_note: string;
  };
  periods: RegimePeriod[];
}

export interface ResearcherViewData {
  latest_signal: {
    signal_date: string;
    momentum: Record<string, number | null>;
    realized_volatility: Record<string, number | null>;
    target_weights: Record<string, number | null>;
    eligibility: Record<string, boolean>;
    is_fully_defensive: boolean;
  };
  latest_effective_allocation: {
    date: string;
    weights: Record<string, number | null>;
  };
  latest_observable_rebalance: {
    signal_date: string;
    effective_date: string;
    weights: Record<string, number | null>;
    trading_notional: number;
    one_way_turnover: number;
    transaction_cost: number;
  } | null;
  recent_realized_risk: {
    date: string;
    strategy_rolling_volatility: number;
    benchmark_rolling_volatility: number;
    strategy_drawdown: number;
    benchmark_drawdown: number;
  };
  summary: string;
}

export interface ReferenceItem {
  id: string;
  category: string;
  title: string;
  publisher: string;
  url: string;
  use: string;
}

export interface ReferencesData {
  references: ReferenceItem[];
}

export interface CurvePoint {
  date: string;
  two_year?: number;
  five_year?: number;
  ten_year?: number;
  level: number;
  slope_2s10s: number;
  slope_5s10s?: number;
  curvature: number;
  SHY?: number;
  IEF?: number;
  TLT?: number;
}

export interface YieldCurveData {
  methodology: { source: string; source_url: string; convention: string; alignment: string; research_limit: string; units: string };
  first_date: string;
  last_date: string;
  daily_observations: number;
  latest: CurvePoint;
  monthly_series: CurvePoint[];
  allocation_context: CurvePoint[];
  regime_context: Array<{ id: string; label: string; average_10y_yield: number; average_2s10s: number; ending_2s10s: number; average_allocation: Record<string, number>; strategy_annualized_volatility: number }>;
}

export interface HoldoutMetrics {
  cumulative_return: number;
  cagr: number;
  annualized_volatility: number;
  sharpe_ratio: number;
  maximum_drawdown: number;
  monthly_win_rate: number;
  one_way_turnover: number;
  number_of_rebalances: number;
}

export interface HoldoutPeriod {
  start_date: string;
  end_date: string;
  trading_days: number;
  strategy: HoldoutMetrics;
  benchmark: HoldoutMetrics;
}

export interface HoldoutData {
  methodology: { label: string; note: string; split_rule: string };
  periods: Record<"full" | "development" | "holdout", HoldoutPeriod>;
}

export interface RateShockScenario { shock_bps: number; asset_impact: Record<string, number>; portfolio_impact: number }
export interface RateShockAllocation { as_of: string; weights: Record<string, number>; scenarios: RateShockScenario[] }
export interface RateShockData {
  methodology: { label: string; formula: string; duration_as_of: string; limitations: string };
  durations: Record<string, { years: number; source: string }>;
  allocations: { current_model_target: RateShockAllocation; latest_effective: RateShockAllocation };
}

export interface DecisionRecord {
  signal_date: string;
  previous_signal_date: string | null;
  effective_date: string;
  previous_allocation: Record<string, number>;
  new_allocation: Record<string, number>;
  momentum: Record<string, number>;
  eligibility: Record<string, boolean>;
  realized_volatility: Record<string, number>;
  weight_change: Record<string, number>;
  trading_notional: number;
  transaction_cost: number;
  explanations: string[];
}
export interface SignalDiagnosticsData {
  methodology: { meaningful_change_gross_notional: number; note: string };
  total_observable_rebalances: number;
  records: DecisionRecord[];
}

export interface FailureEvent {
  start_date: string;
  trough_date: string;
  recovery_date: string | null;
  drawdown: number;
  strategy_return: number;
  benchmark_return: number;
  average_allocation: Record<string, number>;
  allocation_at_trough: Record<string, number>;
  signal_state_at_trough: { signal_date: string; momentum: Record<string, number>; eligibility: Record<string, boolean>; realized_volatility: Record<string, number> } | null;
}
export interface FailurePeriod { period: string; strategy_return: number; benchmark_return: number; active_return: number }
export interface FailureModesData {
  methodology: { drawdown: string; worst_periods: string; underperformance: string };
  events: FailureEvent[];
  worst_months: FailurePeriod[];
  worst_quarters: FailurePeriod[];
  underperformance_windows: Array<{ start_date: string; end_date: string; strategy_return: number; benchmark_return: number; active_return: number }>;
  drawdown_series: Array<{ date: string; strategy_drawdown: number }>;
}


export interface DashboardData {
  summary: SummaryStats;
  nav: NavDataPoint[];
  rollingMetrics: RollingMetricsPoint[];
  weights: WeightPoint[];
  meta: MetaData;
  sensitivity: SensitivityData;
  regimeAnalysis: RegimeAnalysisData;
  researcherView: ResearcherViewData;
  references: ReferencesData;
  yieldCurve: YieldCurveData;
  holdout: HoldoutData;
  rateShock: RateShockData;
  signalDiagnostics: SignalDiagnosticsData;
  failureModes: FailureModesData;
}
