"""Observed negative-return episodes and relative underperformance, without narratives."""

from __future__ import annotations

import pandas as pd

from analytics.backtest import BacktestRun
from analytics.config import TICKERS
from analytics.signals import compute_eligibility


def drawdown_events(nav: pd.Series) -> list[dict]:
    """Locate peak-to-trough episodes and first full recovery, including open episodes."""
    if nav.empty:
        return []
    events = []
    peak_date, peak_value = nav.index[0], float(nav.iloc[0])
    active = None
    for date, value in nav.iloc[1:].items():
        value = float(value)
        if value >= peak_value:
            if active is not None:
                active["recovery_date"] = date.date().isoformat()
                events.append(active)
                active = None
            peak_date, peak_value = date, value
        else:
            depth = value / peak_value - 1
            if active is None:
                active = {"start_date": peak_date.date().isoformat(),
                          "trough_date": date.date().isoformat(), "recovery_date": None,
                          "drawdown": depth}
            elif depth < active["drawdown"]:
                active["trough_date"] = date.date().isoformat()
                active["drawdown"] = depth
    if active is not None:
        events.append(active)
    return sorted(events, key=lambda item: item["drawdown"])


def ranked_period_returns(daily: pd.Series, benchmark: pd.Series, frequency: str, count: int = 5) -> list[dict]:
    grouped = pd.DataFrame({"strategy": daily, "benchmark": benchmark})
    compounded = (1 + grouped).groupby(grouped.index.to_period(frequency)).prod() - 1
    return [{"period": str(period), "strategy_return": float(row.strategy),
             "benchmark_return": float(row.benchmark),
             "active_return": float(row.strategy - row.benchmark)}
            for period, row in compounded.nsmallest(count, "strategy").iterrows()]


def build_failure_modes(run: BacktestRun) -> dict:
    nav, benchmark_nav = run.net_nav, run.benchmark_nav
    eligibility = compute_eligibility(run.momentum)
    events = []
    for episode in drawdown_events(nav)[:6]:
        start = pd.Timestamp(episode["start_date"])
        trough = pd.Timestamp(episode["trough_date"])
        period_weights = run.evaluation_weights.loc[start:trough]
        known_signals = run.rebalance_audit[run.rebalance_audit["signal_date"] <= trough]
        signal_date = pd.Timestamp(known_signals.iloc[-1]["signal_date"]) if not known_signals.empty else None
        events.append({
            **episode,
            "strategy_return": float(nav.loc[trough] / nav.loc[start] - 1),
            "benchmark_return": float(benchmark_nav.loc[trough] / benchmark_nav.loc[start] - 1),
            "average_allocation": {ticker: float(period_weights[ticker].mean()) for ticker in TICKERS},
            "allocation_at_trough": {ticker: float(run.evaluation_weights.loc[trough, ticker]) for ticker in TICKERS},
            "signal_state_at_trough": None if signal_date is None else {
                "signal_date": signal_date.date().isoformat(),
                "momentum": {ticker: float(run.momentum.loc[signal_date, ticker]) for ticker in TICKERS},
                "eligibility": {ticker: bool(eligibility.loc[signal_date, ticker]) for ticker in TICKERS},
                "realized_volatility": {ticker: float(run.realized_volatility.loc[signal_date, ticker]) for ticker in TICKERS},
            },
        })
    daily = run.net_daily_returns
    benchmark = run.benchmark_daily_returns
    # Rolling 63-trading-day compounded differential. This is descriptive and
    # overlapping; the output explicitly discloses that neighboring windows
    # may represent the same adverse episode.
    rolling_strategy = (1 + daily).rolling(63).apply(lambda values: values.prod() - 1, raw=True)
    rolling_benchmark = (1 + benchmark).rolling(63).apply(lambda values: values.prod() - 1, raw=True)
    active = (rolling_strategy - rolling_benchmark).nsmallest(5)
    underperformance = [{"start_date": daily.index[daily.index.get_loc(date) - 62].date().isoformat(),
                         "end_date": date.date().isoformat(), "strategy_return": float(rolling_strategy.loc[date]),
                         "benchmark_return": float(rolling_benchmark.loc[date]), "active_return": float(value)}
                        for date, value in active.items()]
    drawdown = nav / nav.cummax() - 1
    # Keep the frontend payload compact while retaining each selected exact
    # trough and the latest date. The underlying daily NAV remains untouched.
    plot_dates = drawdown.index[::5].union(pd.DatetimeIndex(
        [drawdown.index[-1], *[pd.Timestamp(event["trough_date"]) for event in events]]
    )).sort_values()
    return {
        "methodology": {"drawdown": "Episodes begin at the preceding NAV peak and end at first full recovery; open episodes have null recovery date.",
                        "worst_periods": "Compounded calendar-month and calendar-quarter net returns.",
                        "underperformance": "Five lowest overlapping rolling 63-trading-day compounded strategy-minus-AGG returns."},
        "events": events,
        "worst_months": ranked_period_returns(daily, benchmark, "M"),
        "worst_quarters": ranked_period_returns(daily, benchmark, "Q"),
        "underperformance_windows": underperformance,
        "drawdown_series": [{"date": date.date().isoformat(), "strategy_drawdown": float(drawdown.loc[date])}
                            for date in plot_dates],
    }
