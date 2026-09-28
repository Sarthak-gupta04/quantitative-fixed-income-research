"""Fixed-parameter temporal evaluation of the validated backtest run.

The full price history remains available for indicator warm-up at 2020-01-01.
No parameter is fitted or selected in either period. This is a holdout
description, not a claim of statistically independent optimization testing.
"""

from __future__ import annotations

import pandas as pd

from analytics.backtest import BacktestRun, build_nav_from_daily_returns, evaluate_from_date
from analytics.config import DEFAULT_STRATEGY_PARAMETERS
from analytics.metrics import (
    annualized_return, annualized_volatility, cumulative_return, max_drawdown,
    monthly_win_rate, sharpe_ratio,
)

SPLIT = pd.Timestamp("2020-01-01")


def _metrics(returns: pd.Series, base_date: pd.Timestamp, turnover: pd.Series | None,
             rebalance_dates: pd.Series | None) -> dict:
    nav = build_nav_from_daily_returns(returns, base_date, returns.name or "nav")
    return {
        "cumulative_return": cumulative_return(nav), "cagr": annualized_return(nav),
        "annualized_volatility": annualized_volatility(returns),
        "sharpe_ratio": sharpe_ratio(returns), "maximum_drawdown": max_drawdown(nav),
        "monthly_win_rate": monthly_win_rate(returns),
        "one_way_turnover": float(turnover.sum()) if turnover is not None else 0.0,
        "number_of_rebalances": int(len(rebalance_dates)) if rebalance_dates is not None else 0,
    }


def evaluate_holdout(run: BacktestRun) -> dict:
    dates = run.net_daily_returns.index
    holdout = dates[dates >= SPLIT]
    development = dates[dates < SPLIT]
    if holdout.empty or development.empty:
        raise ValueError("Both development and holdout require investable returns")
    windows = {
        "full": (dates[0], dates[-1]),
        "development": (development[0], development[-1]),
        "holdout": (holdout[0], holdout[-1]),
    }
    periods = {}
    for name, (first, last) in windows.items():
        # Reuse the already validated engine output. Rebase NAV at the prior
        # trading date, preserving signals and cost timing from full history.
        evaluation = evaluate_from_date(run, first)
        strategy = evaluation.net_daily_returns.loc[:last]
        benchmark = evaluation.benchmark_daily_returns.loc[:last]
        turnover = evaluation.one_way_turnover.loc[:last]
        audit = evaluation.rebalance_audit[evaluation.rebalance_audit["effective_date"] <= last]
        periods[name] = {
            "start_date": first.date().isoformat(), "end_date": last.date().isoformat(),
            "nav_base_date": evaluation.nav_base_date.date().isoformat(),
            "trading_days": len(strategy),
            "strategy": _metrics(strategy, evaluation.nav_base_date, turnover, audit["effective_date"]),
            "benchmark": _metrics(benchmark, evaluation.nav_base_date, None, None),
        }
    return {
        "methodology": {
            "label": "Holdout evaluation", "split_rule": "Development before 2020-01-01; holdout from 2020-01-01",
            "fixed_parameters": vars(DEFAULT_STRATEGY_PARAMETERS),
            "note": "Pre-specified parameters were not fitted or tuned. Full-history warm-up is retained for later-period signals; each period NAV is rebased to one at the preceding trading date.",
        }, "periods": periods,
    }
