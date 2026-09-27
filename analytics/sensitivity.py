"""Pre-specified parameter sensitivity analysis using the shared backtest engine.

This module is descriptive research, not parameter optimisation.  It runs the
six combinations declared in ``SENSITIVITY_PARAMETER_GRID`` and evaluates all
of them over the same common investable return window.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.backtest import evaluate_from_date, run_backtest
from analytics.config import (
    DATA_PROCESSED_DIR,
    DEFAULT_STRATEGY_PARAMETERS,
    PUBLIC_DATA_DIR,
    SENSITIVITY_PARAMETER_GRID,
    StrategyParameters,
)
from analytics.metrics import (
    annualized_return,
    annualized_volatility,
    max_drawdown,
    monthly_win_rate,
    sharpe_ratio,
)
from analytics.signals import load_processed


def configuration_id(parameters: StrategyParameters) -> str:
    return f"mom_{parameters.momentum_window}_vol_{parameters.volatility_window}"


def run_sensitivity(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    parameter_grid: tuple[StrategyParameters, ...] = SENSITIVITY_PARAMETER_GRID,
) -> dict:
    """Run the fixed grid and return results on a common non-optimised window."""
    runs = [(parameters, run_backtest(prices, returns, parameters)) for parameters in parameter_grid]
    common_start = max(run.first_investable_date for _, run in runs)
    rows: list[dict] = []

    for parameters, run in runs:
        window = evaluate_from_date(run, common_start)
        rows.append({
            "configuration_id": configuration_id(parameters),
            "is_baseline": parameters == DEFAULT_STRATEGY_PARAMETERS,
            "parameters": {
                "momentum_window_days": parameters.momentum_window,
                "volatility_window_days": parameters.volatility_window,
                "signal_to_weight_lag_days": parameters.signal_to_weight_lag,
                "transaction_cost_rate": parameters.transaction_cost_rate,
            },
            "native_first_investable_date": str(run.first_investable_date.date()),
            "evaluation_start_date": str(window.start_date.date()),
            "evaluation_end_date": str(window.net_daily_returns.index[-1].date()),
            "metrics": {
                "cumulative_return": float(window.net_nav.iloc[-1] - 1.0),
                "cagr": annualized_return(window.net_nav),
                "annualized_volatility": annualized_volatility(window.net_daily_returns),
                "sharpe_ratio": sharpe_ratio(window.net_daily_returns),
                "maximum_drawdown": max_drawdown(window.net_nav),
                "monthly_win_rate": monthly_win_rate(window.net_daily_returns),
                "total_trading_notional": float(window.trading_notional.sum()),
                "total_one_way_turnover": float(window.one_way_turnover.sum()),
                "number_of_rebalances": int(len(window.rebalance_audit)),
            },
        })

    if sum(row["is_baseline"] for row in rows) != 1:
        raise AssertionError("The sensitivity grid must contain the baseline exactly once.")

    metric_ranges = {
        key: {
            "minimum": min(row["metrics"][key] for row in rows),
            "maximum": max(row["metrics"][key] for row in rows),
        }
        for key in ("cagr", "annualized_volatility", "sharpe_ratio", "maximum_drawdown", "monthly_win_rate")
    }
    baseline = next(row for row in rows if row["is_baseline"])
    cagr_range = metric_ranges["cagr"]
    vol_range = metric_ranges["annualized_volatility"]
    drawdown_range = metric_ranges["maximum_drawdown"]
    return {
        "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "purpose": "Pre-specified descriptive sensitivity analysis; no configuration is selected or optimised.",
            "common_evaluation_start_date": str(common_start.date()),
            "common_evaluation_end_date": rows[0]["evaluation_end_date"],
            "baseline_configuration_id": baseline["configuration_id"],
            "baseline_parameters": baseline["parameters"],
            "transaction_cost_definition": "Trading notional × transaction_cost_rate, where trading notional = sum(abs(weight change)).",
            "one_way_turnover_definition": "0.5 × trading notional.",
            "timing": "Month-end signals become effective on the next available trading date using the shared validated backtest engine.",
            "common_window_note": (
                "The 90-day momentum configuration becomes investable later than the baseline. "
                "All six rows are therefore reported over the latest first-investable date across the fixed grid, "
                "so differences do not reflect unequal warm-up periods."
            ),
        },
        "results": rows,
        "interpretation": {
            "metric_ranges": metric_ranges,
            "summary": (
                "Across the six pre-specified configurations, CAGR ranged from "
                f"{cagr_range['minimum']:.2%} to {cagr_range['maximum']:.2%}, annualized volatility from "
                f"{vol_range['minimum']:.2%} to {vol_range['maximum']:.2%}, and maximum drawdown from "
                f"{drawdown_range['minimum']:.2%} to {drawdown_range['maximum']:.2%}. "
                "The baseline is reported as one row within these ranges. Results varied across reasonable "
                "parameter choices; this descriptive table does not identify, select, or optimise a winning configuration."
            ),
        },
    }


def save_sensitivity(result: dict) -> None:
    """Write browser-ready JSON and a human-readable flat CSV."""
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PUBLIC_DATA_DIR / "sensitivity.json", "w") as file:
        json.dump(result, file, indent=2)

    rows = []
    for row in result["results"]:
        rows.append({
            "configuration_id": row["configuration_id"],
            "is_baseline": row["is_baseline"],
            "native_first_investable_date": row["native_first_investable_date"],
            "evaluation_start_date": row["evaluation_start_date"],
            "evaluation_end_date": row["evaluation_end_date"],
            **row["parameters"],
            **row["metrics"],
        })
    pd.DataFrame(rows).to_csv(DATA_PROCESSED_DIR / "sensitivity.csv", index=False)


if __name__ == "__main__":
    prices, returns = load_processed()
    result = run_sensitivity(prices, returns)
    save_sensitivity(result)
    print(f"Generated sensitivity analysis for {len(result['results'])} pre-specified configurations.")
