"""Neutral historical-period analysis of the validated baseline strategy."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.backtest import build_nav_from_daily_returns
from analytics.config import DATA_PROCESSED_DIR, PUBLIC_DATA_DIR, TICKERS
from analytics.metrics import annualized_volatility, max_drawdown


def select_periods(data_start: pd.Timestamp, data_end: pd.Timestamp) -> list[dict]:
    """Select only fully supported, neutrally named historical periods."""
    candidates = [
        {"id": "2007_2009", "label": "2007-2009 period", "start_date": "2007-01-01", "end_date": "2009-12-31"},
        {"id": "2020", "label": "2020 period", "start_date": "2020-01-01", "end_date": "2020-12-31"},
        {"id": "2022", "label": "2022 period", "start_date": "2022-01-01", "end_date": "2022-12-31"},
    ]
    latest_completed_year = data_end.year if (data_end.month, data_end.day) == (12, 31) else data_end.year - 1
    candidates.append({
        "id": f"{latest_completed_year}",
        "label": f"{latest_completed_year} period (most recent completed calendar year)",
        "start_date": f"{latest_completed_year}-01-01",
        "end_date": f"{latest_completed_year}-12-31",
    })
    return [
        period for period in candidates
        if pd.Timestamp(period["start_date"]) >= data_start and pd.Timestamp(period["end_date"]) <= data_end
    ]


def _allocation_dict(row: pd.Series) -> dict[str, float]:
    return {ticker: float(row[ticker]) for ticker in TICKERS}


def calculate_period_metrics(
    period: dict,
    returns: pd.DataFrame,
    weights: pd.DataFrame,
    rebalance_audit: pd.DataFrame,
) -> dict:
    """Calculate comparable realised-period metrics from aligned daily data."""
    start = pd.Timestamp(period["start_date"])
    end = pd.Timestamp(period["end_date"])
    period_returns = returns.loc[(returns.index >= start) & (returns.index <= end)]
    period_weights = weights.loc[period_returns.index]
    if period_returns.empty:
        raise ValueError(f"No aligned returns exist for {period['id']}")

    first_date = period_returns.index[0]
    location = returns.index.get_loc(first_date)
    base_date = returns.index[location - 1] if location > 0 else first_date - pd.offsets.BDay(1)
    strategy_nav = build_nav_from_daily_returns(period_returns["strategy_net"], base_date, "strategy_net")
    benchmark_nav = build_nav_from_daily_returns(period_returns["benchmark"], base_date, "benchmark")
    rebalance_count = int(
        ((rebalance_audit["effective_date"] >= first_date) & (rebalance_audit["effective_date"] <= period_returns.index[-1])).sum()
    )
    fully_defensive = np.isclose(period_weights["SHY"], 1.0, atol=1e-8)

    return {
        **period,
        "actual_start_date": str(first_date.date()),
        "actual_end_date": str(period_returns.index[-1].date()),
        "trading_days": int(len(period_returns)),
        "strategy_return": float(strategy_nav.iloc[-1] - 1.0),
        "benchmark_return": float(benchmark_nav.iloc[-1] - 1.0),
        "strategy_annualized_volatility": annualized_volatility(period_returns["strategy_net"]),
        "benchmark_annualized_volatility": annualized_volatility(period_returns["benchmark"]),
        "strategy_maximum_drawdown": max_drawdown(strategy_nav),
        "average_allocation": {ticker: float(period_weights[ticker].mean()) for ticker in TICKERS},
        "beginning_allocation": _allocation_dict(period_weights.iloc[0]),
        "ending_allocation": _allocation_dict(period_weights.iloc[-1]),
        "number_of_rebalances": rebalance_count,
        "defensive_shy_allocation": {
            "average_weight": float(period_weights["SHY"].mean()),
            "fully_defensive_trading_days": int(fully_defensive.sum()),
            "fully_defensive_fraction": float(fully_defensive.mean()),
        },
    }


def run_regime_analysis(
    returns: pd.DataFrame,
    weights: pd.DataFrame,
    rebalance_audit: pd.DataFrame,
) -> dict:
    periods = select_periods(returns.index[0], returns.index[-1])
    return {
        "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "period_definition": "Calendar-date intervals, included only when the common strategy/benchmark evaluation data covers the full interval.",
            "return_convention": "Compounded daily net strategy and benchmark returns, each rebased to NAV 1.0 immediately before the period's first return.",
            "allocation_convention": "Average and endpoint active portfolio weights over the realised daily return dates.",
            "naming_note": "Period labels are neutral calendar-period descriptions and do not assert a market-regime explanation.",
        },
        "periods": [calculate_period_metrics(period, returns, weights, rebalance_audit) for period in periods],
    }


def load_baseline_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    returns = pd.read_csv(DATA_PROCESSED_DIR / "portfolio_returns.csv", index_col=0, parse_dates=True)
    weights = pd.read_csv(DATA_PROCESSED_DIR / "active_weights.csv", index_col=0, parse_dates=True)
    audit = pd.read_csv(
        DATA_PROCESSED_DIR / "rebalance_log.csv",
        parse_dates=["signal_date", "effective_date", "first_return_date", "next_signal_date"],
    )
    return returns, weights, audit


def save_regime_analysis(result: dict) -> None:
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PUBLIC_DATA_DIR / "regime_analysis.json", "w") as file:
        json.dump(result, file, indent=2)
    rows = []
    for period in result["periods"]:
        rows.append({
            key: value for key, value in period.items()
            if not isinstance(value, dict)
        } | {
            **{f"average_{ticker}": period["average_allocation"][ticker] for ticker in TICKERS},
            **{f"beginning_{ticker}": period["beginning_allocation"][ticker] for ticker in TICKERS},
            **{f"ending_{ticker}": period["ending_allocation"][ticker] for ticker in TICKERS},
            **period["defensive_shy_allocation"],
        })
    pd.DataFrame(rows).to_csv(DATA_PROCESSED_DIR / "regime_analysis.csv", index=False)


if __name__ == "__main__":
    returns, weights, audit = load_baseline_inputs()
    result = run_regime_analysis(returns, weights, audit)
    save_regime_analysis(result)
    print(f"Generated neutral analysis for {len(result['periods'])} historical periods.")
