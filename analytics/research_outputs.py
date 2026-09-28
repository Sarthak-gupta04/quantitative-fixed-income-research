"""Generate supplementary research artifacts after a baseline regression gate.

Run from the repository root with ``python -m analytics.research_outputs``.
The existing baseline JSON/CSV and strategy engine are never rewritten here.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from analytics.backtest import run_backtest
from analytics.config import DATA_PROCESSED_DIR, PUBLIC_DATA_DIR, PROJECT_ROOT, TICKERS
from analytics.failure_modes import build_failure_modes
from analytics.holdout_analysis import evaluate_holdout
from analytics.metrics import annualized_return, annualized_volatility, max_drawdown, sharpe_ratio
from analytics.rate_shock import build_rate_shock
from analytics.signal_diagnostics import build_decision_records
from analytics.signals import load_processed
from analytics.yield_curve import align_curve_and_allocation, calculate_curve, load_treasury_history


def assert_baseline_unchanged(run, checkpoint: dict) -> dict:
    expected = checkpoint["strategy_net"]
    actual = {
        "cumulative_return": float(run.net_nav.iloc[-1] - 1),
        "cagr": annualized_return(run.net_nav),
        "annualized_volatility": annualized_volatility(run.net_daily_returns),
        "sharpe_ratio": sharpe_ratio(run.net_daily_returns),
        "maximum_drawdown": max_drawdown(run.net_nav),
        "first_investable_date": run.first_investable_date.date().isoformat(),
    }
    comparisons = {
        "cumulative_return": expected["cumulative_return"],
        "cagr": expected["annualized_return"],
        "annualized_volatility": expected["annualized_volatility"],
        "sharpe_ratio": expected["sharpe_ratio"],
        "maximum_drawdown": expected["max_drawdown"],
        "first_investable_date": checkpoint["metadata"]["first_investable_date"],
    }
    for key, value in actual.items():
        reference = comparisons[key]
        if isinstance(value, str):
            if value != reference:
                raise AssertionError(f"Baseline {key} changed: {value} vs {reference}")
        elif not math.isclose(value, reference, rel_tol=0, abs_tol=1e-10):
            raise AssertionError(f"Baseline {key} changed: {value} vs {reference}")
    return {key: {"checkpoint": comparisons[key], "rerun": actual[key]} for key in actual}


def _records(frame: pd.DataFrame) -> list[dict]:
    return [{"date": date.date().isoformat(), **{key: float(value) for key, value in row.items()}}
            for date, row in frame.iterrows()]


def _save_json(name: str, content: dict) -> None:
    path = PUBLIC_DATA_DIR / name
    path.write_text(json.dumps(content, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Wrote {path.relative_to(PROJECT_ROOT)}")


def build_outputs() -> dict:
    prices, returns = load_processed()
    run = run_backtest(prices, returns)
    # The frontend JSON rounds numbers for transfer. Regression checks must
    # use the validated, full-precision processed checkpoint instead.
    checkpoint = json.loads((DATA_PROCESSED_DIR / "summary_stats.json").read_text(encoding="utf-8"))
    regression = assert_baseline_unchanged(run, checkpoint)
    print("Baseline regression gate: PASS", regression)

    treasury, sources = load_treasury_history(PROJECT_ROOT / "data" / "raw" / "treasury_curve", 2003, datetime.now(timezone.utc).year)
    curve = calculate_curve(treasury)
    curve = curve.loc[:run.net_daily_returns.index.max()]
    if curve.empty:
        raise ValueError("No usable Treasury curve dates overlap the backtest")
    allocation = align_curve_and_allocation(curve, run.evaluation_weights)
    # Monthly sample includes the latest actual observation within each month.
    monthly_curve = curve.groupby(curve.index.to_period("M")).tail(1)
    treasury_context = {
        "methodology": {
            "source": "U.S. Department of the Treasury, daily par yield curve rates",
            "source_url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates",
            "series": {"2Y": "BC_2YEAR (FRED counterpart DGS2)", "5Y": "BC_5YEAR (FRED counterpart DGS5)", "10Y": "BC_10YEAR (FRED counterpart DGS10)"},
            "units": "percentage points, not decimal returns",
            "convention": "Level = 10Y; 2s10s = 10Y − 2Y; 5s10s = 10Y − 5Y; curvature = 2×5Y − 2Y − 10Y.",
            "alignment": "Only dates with all three published tenors are used. Allocation context uses exact date intersections, with no missing-value imputation. Monthly charts use the last actual observation of each month.",
            "research_limit": "Curve/allocation comparisons are historical co-occurrences, not causal estimates.",
            "pandas_version": pd.__version__,
        },
        "source_files": sources,
        "first_date": curve.index.min().date().isoformat(),
        "last_date": curve.index.max().date().isoformat(),
        "daily_observations": len(curve),
        "latest": {"date": curve.index.max().date().isoformat(), **{key: float(value) for key, value in curve.iloc[-1].items() if not pd.isna(value)}},
        "monthly_series": _records(monthly_curve[["two_year", "five_year", "ten_year", "level", "slope_2s10s", "slope_5s10s", "curvature"]]),
        "allocation_context": _records(allocation),
    }
    regime_path = PUBLIC_DATA_DIR / "regime_analysis.json"
    regimes = json.loads(regime_path.read_text(encoding="utf-8"))["periods"]
    treasury_context["regime_context"] = []
    for regime in regimes:
        subset = curve.loc[regime["actual_start_date"]:regime["actual_end_date"]]
        if subset.empty:
            continue
        treasury_context["regime_context"].append({
            "id": regime["id"], "label": regime["label"],
            "start_date": subset.index.min().date().isoformat(), "end_date": subset.index.max().date().isoformat(),
            "average_10y_yield": float(subset["level"].mean()),
            "average_2s10s": float(subset["slope_2s10s"].mean()),
            "ending_2s10s": float(subset["slope_2s10s"].iloc[-1]),
            "average_allocation": regime["average_allocation"],
            "strategy_annualized_volatility": regime["strategy_annualized_volatility"],
        })

    holdout = evaluate_holdout(run)
    latest_signal_date = run.target_weights.index[-1]
    current_weights = {ticker: float(run.target_weights.loc[latest_signal_date, ticker]) for ticker in TICKERS}
    effective_date = run.evaluation_weights.index[-1]
    effective_weights = {ticker: float(run.evaluation_weights.loc[effective_date, ticker]) for ticker in TICKERS}
    shocks = build_rate_shock(current_weights, effective_weights,
                              latest_signal_date.date().isoformat(), effective_date.date().isoformat())
    decisions = build_decision_records(run)
    failures = build_failure_modes(run)

    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    curve.to_csv(DATA_PROCESSED_DIR / "yield_curve.csv", date_format="%Y-%m-%d")
    allocation.to_csv(DATA_PROCESSED_DIR / "curve_allocation.csv", date_format="%Y-%m-%d")
    _save_json("yield_curve.json", treasury_context)
    _save_json("holdout_analysis.json", holdout)
    _save_json("rate_shock.json", shocks)
    _save_json("signal_diagnostics.json", decisions)
    _save_json("failure_modes.json", failures)
    return regression


if __name__ == "__main__":
    print(build_outputs())
