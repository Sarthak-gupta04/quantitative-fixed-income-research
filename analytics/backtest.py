"""
analytics/backtest.py
======================
Implements the portfolio backtesting engine with explicit event timing.

Timeline:
---------
  Signal date t (month-end close): compute momentum, realized volatility, and
  target weights using information available through t.

  Effective date t+1 (next available trading date): target weights first apply
  to that date's close-to-close return.  The benchmark begins on the same
  first investable return date; indicator warm-up is never recorded as a
  zero-return strategy period in comparative metrics.

NAV convention:
---------------
  NAV_0 = 1.0 on the trading date immediately before the first investable
  return.  Each subsequent row applies exactly one daily return.

Trading convention:
-------------------
  Trading notional(t) = Σ_i |w_new(i) - w_old(i)|
  Transaction cost(t) = trading notional(t) × 0.0002
  One-way turnover(t) = 0.5 × trading notional(t)

The saved rebalance audit contains signal date, effective date, first return
date, next signal date, target/effective weights, trading notional, turnover,
and transaction cost for every observable event.

Usage:
    python analytics/backtest.py
"""

import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.config import (
    BENCHMARK,
    DATA_PROCESSED_DIR,
    DEFAULT_STRATEGY_PARAMETERS,
    StrategyParameters,
    TICKERS,
)
from analytics.signals import (
    compute_eligibility,
    compute_momentum,
    compute_realized_vol,
    compute_weights,
    get_rebalance_dates,
    load_processed,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


@dataclass
class BacktestRun:
    """Complete in-memory result for one pre-specified parameter configuration."""

    momentum: pd.DataFrame
    realized_volatility: pd.DataFrame
    target_weights: pd.DataFrame
    active_weights: pd.DataFrame
    evaluation_weights: pd.DataFrame
    trading_notional: pd.Series
    one_way_turnover: pd.Series
    transaction_costs: pd.Series
    gross_daily_returns: pd.Series
    net_daily_returns: pd.Series
    benchmark_daily_returns: pd.Series
    gross_nav: pd.Series
    net_nav: pd.Series
    benchmark_nav: pd.Series
    rebalance_audit: pd.DataFrame
    first_investable_date: pd.Timestamp
    nav_base_date: pd.Timestamp
    raw_return_start_date: pd.Timestamp
    indicator_warmup_trading_days: int


@dataclass
class EvaluationWindow:
    """A common subperiod extracted from an already validated backtest run."""

    start_date: pd.Timestamp
    nav_base_date: pd.Timestamp
    gross_daily_returns: pd.Series
    net_daily_returns: pd.Series
    benchmark_daily_returns: pd.Series
    weights: pd.DataFrame
    trading_notional: pd.Series
    one_way_turnover: pd.Series
    transaction_costs: pd.Series
    gross_nav: pd.Series
    net_nav: pd.Series
    benchmark_nav: pd.Series
    rebalance_audit: pd.DataFrame


def _is_fully_invested(weights: pd.Series) -> bool:
    """Whether a finite, long-only target vector sums to one."""
    return bool(
        weights.notna().all()
        and np.isfinite(weights.to_numpy(dtype=float)).all()
        and (weights >= -1e-10).all()
        and np.isclose(float(weights.sum()), 1.0, atol=1e-8)
    )


def _next_trading_date(date: pd.Timestamp, dates: pd.DatetimeIndex) -> pd.Timestamp | None:
    """Return the first available trading date strictly after ``date``."""
    position = dates.searchsorted(date, side="right")
    return dates[position] if position < len(dates) else None


# ---------------------------------------------------------------------------
# Build active weights (with lag and monthly rebalancing)
# ---------------------------------------------------------------------------

def build_active_weights(
    weights_daily: pd.DataFrame,
    rebalance_dates: pd.DatetimeIndex,
    all_dates: pd.DatetimeIndex,
    signal_to_weight_lag: int = DEFAULT_STRATEGY_PARAMETERS.signal_to_weight_lag,
) -> pd.DataFrame:
    """
    Construct the daily active weight series with:
      1. Monthly rebalancing (weights only change on rebalance dates)
      2. 1-day forward shift (look-ahead prevention)

    Approach:
      - Start with all-zero weights.
      - On each rebalance date, record the target weight.
      - Forward-fill so weights are held until the next rebalance.
      - Shift forward by SIGNAL_TO_WEIGHT_LAG trading days.

    The shift means: weight computed at close of rebalance date t
    is first applied to the return on day t+1.
    """
    # Initialize with NaN; only fully-invested target weights are scheduled.
    # Warm-up rows remain zero and are excluded from comparative metrics later.
    rebalance_weights = pd.DataFrame(np.nan, index=all_dates, columns=TICKERS)

    for rdate in rebalance_dates:
        if rdate in weights_daily.index:
            target = weights_daily.loc[rdate]
            if _is_fully_invested(target):
                rebalance_weights.loc[rdate] = target.values

    # Forward-fill: hold weights between rebalances
    active = rebalance_weights.ffill()

    # Before the first rebalance date where we have valid weights,
    # there are NaN rows (warm-up). Fill with 0 (no position = cash).
    active = active.fillna(0.0)

    # Apply look-ahead lag: shift weights forward by 1 day
    # This means the weight determined at end of day t is used for day t+1 return.
    active = active.shift(signal_to_weight_lag)
    active = active.fillna(0.0)  # First row after shift becomes NaN → fill with 0

    # Validation: weights should sum to 0 (pre-start) or ~1 (once active)
    weight_sums = active.sum(axis=1)
    active_rows = weight_sums[weight_sums > 0.01]
    if not active_rows.empty:
        bad = active_rows[(active_rows - 1.0).abs() > 1e-4]
        if not bad.empty:
            log.warning(
                "Active weight sums deviate from 1.0 on %d dates. First: %s = %.6f",
                len(bad), bad.index[0].date(), bad.iloc[0],
            )

    log.info(
        "Active weights built: %d total days, first active date: %s",
        len(active),
        active[active.sum(axis=1) > 0].index[0].date() if (active.sum(axis=1) > 0).any() else "N/A",
    )
    return active


# ---------------------------------------------------------------------------
# Turnover calculation
# ---------------------------------------------------------------------------

def compute_trading_notional(active_weights: pd.DataFrame) -> pd.Series:
    """Traded notional: Σ|w_t - w_(t-1)|, including the initial entry trade."""
    changes = active_weights.diff()
    if not active_weights.empty:
        changes.iloc[0] = active_weights.iloc[0]
    return changes.abs().sum(axis=1).rename("trading_notional")


def compute_one_way_turnover(trading_notional: pd.Series) -> pd.Series:
    """Conventional one-way turnover: 0.5 × traded notional."""
    return (0.5 * trading_notional).rename("one_way_turnover")


# ---------------------------------------------------------------------------
# Transaction costs
# ---------------------------------------------------------------------------

def compute_transaction_costs(
    active_weights: pd.DataFrame,
    tc_rate: float = DEFAULT_STRATEGY_PARAMETERS.transaction_cost_rate,
) -> pd.Series:
    """
    Compute daily transaction cost series.
    Cost is only incurred when weights change (on effective rebalance days).

    TC(t) = Σ_i |w(i,t) - w(i,t-1)| × tc_rate
    """
    return (compute_trading_notional(active_weights) * tc_rate).rename("transaction_cost")


# ---------------------------------------------------------------------------
# NAV computation
# ---------------------------------------------------------------------------

def compute_nav(
    returns: pd.DataFrame,
    active_weights: pd.DataFrame,
    tc_series: pd.Series,
    nav_base_date: pd.Timestamp,
    start_value: float = 1.0,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Compute gross and net NAV time series.

    Gross:  r_port(t) = Σ_i w(i,t) × r(i,t)
    Net:    r_port_net(t) = r_port(t) - TC(t)

    NAV has an explicit base observation of 1.0 on ``nav_base_date``.  The
    first supplied daily return is then applied on its own date.  This makes
    the NAV convention consistent for cumulative return, CAGR, drawdown, and
    charting.

    The active weights are already shifted, so weight[t] applies to return[t].
    We only compute from the first date where active weights > 0.
    """
    # Restrict returns to strategy tickers only
    strategy_returns = returns[TICKERS]

    # Align
    common_idx = strategy_returns.index.intersection(active_weights.index)
    strategy_returns = strategy_returns.loc[common_idx]
    active_weights = active_weights.loc[common_idx]
    tc_aligned = tc_series.reindex(common_idx).fillna(0.0)

    # Gross portfolio return each day
    gross_daily = (strategy_returns * active_weights).sum(axis=1)

    # Net of transaction costs
    net_daily = gross_daily - tc_aligned

    def nav_from_returns(daily_returns: pd.Series, name: str) -> pd.Series:
        values = np.concatenate(([start_value], start_value * (1 + daily_returns).cumprod().to_numpy()))
        index = pd.DatetimeIndex([nav_base_date, *daily_returns.index])
        return pd.Series(values, index=index, name=name)

    gross_nav = nav_from_returns(gross_daily, "strategy_gross")
    net_nav = nav_from_returns(net_daily, "strategy_net")

    log.info(
        "NAV computed: %d days, gross cumulative: %.4f, net cumulative: %.4f",
        len(gross_nav), gross_nav.iloc[-1], net_nav.iloc[-1],
    )
    return gross_nav, net_daily, gross_daily, net_nav


def compute_benchmark_nav(
    benchmark_returns: pd.Series,
    nav_base_date: pd.Timestamp,
    start_value: float = 1.0,
) -> pd.Series:
    """
    Buy-and-hold benchmark NAV (AGG).
    100% invested in benchmark on day 1, no transaction costs, no rebalancing.
    """
    values = np.concatenate(([start_value], start_value * (1 + benchmark_returns).cumprod().to_numpy()))
    index = pd.DatetimeIndex([nav_base_date, *benchmark_returns.index])
    return pd.Series(values, index=index, name="benchmark")


def build_nav_from_daily_returns(
    daily_returns: pd.Series,
    nav_base_date: pd.Timestamp,
    name: str,
    start_value: float = 1.0,
) -> pd.Series:
    """Build a base-NAV series from an already aligned daily return series."""
    values = np.concatenate(([start_value], start_value * (1 + daily_returns).cumprod().to_numpy()))
    index = pd.DatetimeIndex([nav_base_date, *daily_returns.index])
    return pd.Series(values, index=index, name=name)


def evaluate_from_date(run: BacktestRun, start_date: pd.Timestamp) -> EvaluationWindow:
    """Rebase a validated run to a later common evaluation date.

    This does not recompute signals, weights, or costs.  It only expresses an
    existing run over a common subperiod, allowing parameter configurations
    with different indicator warm-ups to be compared fairly.
    """
    start_date = pd.Timestamp(start_date)
    if start_date < run.first_investable_date:
        raise ValueError("Evaluation start cannot precede the run's first investable date.")
    if start_date not in run.net_daily_returns.index:
        raise KeyError(f"Evaluation start {start_date.date()} is not a realized return date.")
    position = run.net_daily_returns.index.get_loc(start_date)
    if position == 0:
        base_date = run.nav_base_date
    else:
        base_date = run.net_daily_returns.index[position - 1]

    gross = run.gross_daily_returns.loc[start_date:]
    net = run.net_daily_returns.loc[start_date:]
    benchmark = run.benchmark_daily_returns.loc[start_date:]
    weights = run.evaluation_weights.loc[start_date:]
    notional = run.trading_notional.loc[start_date:]
    one_way = run.one_way_turnover.loc[start_date:]
    costs = run.transaction_costs.loc[start_date:]
    audit = run.rebalance_audit[run.rebalance_audit["effective_date"] >= start_date].copy()
    return EvaluationWindow(
        start_date=start_date,
        nav_base_date=base_date,
        gross_daily_returns=gross,
        net_daily_returns=net,
        benchmark_daily_returns=benchmark,
        weights=weights,
        trading_notional=notional,
        one_way_turnover=one_way,
        transaction_costs=costs,
        gross_nav=build_nav_from_daily_returns(gross, base_date, "strategy_gross"),
        net_nav=build_nav_from_daily_returns(net, base_date, "strategy_net"),
        benchmark_nav=build_nav_from_daily_returns(benchmark, base_date, "benchmark"),
        rebalance_audit=audit,
    )


# ---------------------------------------------------------------------------
# Rebalance log
# ---------------------------------------------------------------------------

def build_rebalance_audit(
    target_weights: pd.DataFrame,
    active_weights: pd.DataFrame,
    rebalance_dates: pd.DatetimeIndex,
    returns_index: pd.DatetimeIndex,
    trading_notional: pd.Series,
    one_way_turnover: pd.Series,
    tc_series: pd.Series,
) -> pd.DataFrame:
    """Build a human-readable signal-to-return timing audit table."""
    valid_signal_dates = [
        date for date in rebalance_dates
        if date in target_weights.index and _is_fully_invested(target_weights.loc[date])
    ]
    records = []
    for position, signal_date in enumerate(valid_signal_dates):
        effective_date = _next_trading_date(signal_date, returns_index)
        if effective_date is None:
            continue
        target = target_weights.loc[signal_date]
        effective = active_weights.loc[effective_date]
        next_signal = valid_signal_dates[position + 1] if position + 1 < len(valid_signal_dates) else pd.NaT
        records.append({
            "signal_date": signal_date,
            "effective_date": effective_date,
            "first_return_date": effective_date,
            "next_signal_date": next_signal,
            "target_weight_SHY": target["SHY"],
            "target_weight_IEF": target["IEF"],
            "target_weight_TLT": target["TLT"],
            "weight_SHY": effective["SHY"],
            "weight_IEF": effective["IEF"],
            "weight_TLT": effective["TLT"],
            "weight_sum": effective.sum(),
            "trading_notional": trading_notional.loc[effective_date],
            "one_way_turnover": one_way_turnover.loc[effective_date],
            "transaction_cost": tc_series.loc[effective_date],
        })
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Validate look-ahead bias (programmatic assertion)
# ---------------------------------------------------------------------------

def assert_no_lookahead(
    target_weights: pd.DataFrame,
    active_weights: pd.DataFrame,
    momentum: pd.DataFrame,
    realized_volatility: pd.DataFrame,
    rebalance_dates: pd.DatetimeIndex,
    returns_index: pd.DatetimeIndex,
    signal_to_weight_lag: int = DEFAULT_STRATEGY_PARAMETERS.signal_to_weight_lag,
) -> None:
    """
    For every valid rebalance, assert that the next trading date is the first
    effective return date, its weights equal the signal-date target, and those
    weights remain unchanged until the next effective rebalance.  This prevents
    a later target from changing an earlier holding period.
    """
    if signal_to_weight_lag != 1:
        raise NotImplementedError("The timing audit currently supports a one-trading-day execution lag only.")
    valid_signal_dates = [
        date for date in rebalance_dates
        if date in target_weights.index and _is_fully_invested(target_weights.loc[date])
    ]
    for position, signal_date in enumerate(valid_signal_dates):
        effective_date = _next_trading_date(signal_date, returns_index)
        if effective_date is None:
            continue
        target = target_weights.loc[signal_date, TICKERS]
        if not momentum.loc[signal_date, TICKERS].notna().all():
            raise AssertionError(f"Missing momentum at {signal_date.date()}")
        if not realized_volatility.loc[signal_date, TICKERS].notna().all():
            raise AssertionError(f"Missing realized volatility at {signal_date.date()}")
        if not np.allclose(active_weights.loc[effective_date, TICKERS], target, atol=1e-10):
            raise AssertionError(f"Weights at {effective_date.date()} do not equal {signal_date.date()} target")

        next_signal = valid_signal_dates[position + 1] if position + 1 < len(valid_signal_dates) else None
        next_effective = _next_trading_date(next_signal, returns_index) if next_signal is not None else None
        holding_dates = returns_index[returns_index >= effective_date]
        if next_effective is not None:
            holding_dates = holding_dates[holding_dates < next_effective]
        expected = np.tile(target.to_numpy(), (len(holding_dates), 1))
        if len(holding_dates) and not np.allclose(active_weights.loc[holding_dates, TICKERS], expected, atol=1e-10):
            raise AssertionError(f"Future rebalance altered holdings before it became effective after {signal_date.date()}")
    log.info("Look-ahead timing assertion: PASSED (%d valid rebalance dates checked)", len(valid_signal_dates))


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def run_backtest(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    parameters: StrategyParameters = DEFAULT_STRATEGY_PARAMETERS,
) -> BacktestRun:
    """Run one reusable, pre-specified parameter configuration.

    Future sensitivity analysis can call this exact function with parameter
    objects from ``SENSITIVITY_PARAMETER_GRID``; no parameter selection occurs
    inside the engine.
    """
    momentum = compute_momentum(prices, window=parameters.momentum_window)
    rvol = compute_realized_vol(returns, window=parameters.volatility_window)
    eligibility = compute_eligibility(momentum)
    target_weights = compute_weights(
        eligibility,
        rvol,
        min_realized_volatility=parameters.min_realized_volatility,
    )
    rebalance_dates = get_rebalance_dates(prices.index)
    active_weights = build_active_weights(
        target_weights,
        rebalance_dates,
        returns.index,
        signal_to_weight_lag=parameters.signal_to_weight_lag,
    )

    first_investable_date = determine_investable_start(
        target_weights, rebalance_dates, returns, momentum, rvol
    )
    first_position = returns.index.get_loc(first_investable_date)
    if first_position == 0:
        raise ValueError("A trading-day NAV base before the first investable return is required.")
    nav_base_date = returns.index[first_position - 1]
    evaluation_returns = returns.loc[first_investable_date:]
    evaluation_weights = active_weights.loc[first_investable_date:]

    all_trading_notional = compute_trading_notional(active_weights)
    all_transaction_costs = compute_transaction_costs(
        active_weights, tc_rate=parameters.transaction_cost_rate
    )
    trading_notional = all_trading_notional.loc[first_investable_date:]
    one_way_turnover = compute_one_way_turnover(trading_notional)
    transaction_costs = all_transaction_costs.loc[first_investable_date:]
    gross_nav, net_daily, gross_daily, net_nav = compute_nav(
        evaluation_returns, evaluation_weights, transaction_costs, nav_base_date
    )
    benchmark_daily = evaluation_returns[BENCHMARK].rename("benchmark")
    benchmark_nav = compute_benchmark_nav(benchmark_daily, nav_base_date)

    assert_no_lookahead(
        target_weights,
        active_weights,
        momentum,
        rvol,
        rebalance_dates,
        returns.index,
        signal_to_weight_lag=parameters.signal_to_weight_lag,
    )
    audit = build_rebalance_audit(
        target_weights,
        active_weights,
        rebalance_dates,
        returns.index,
        all_trading_notional,
        compute_one_way_turnover(all_trading_notional),
        all_transaction_costs,
    )
    audit = audit[audit["effective_date"] >= first_investable_date].copy()

    return BacktestRun(
        momentum=momentum,
        realized_volatility=rvol,
        target_weights=target_weights,
        active_weights=active_weights,
        evaluation_weights=evaluation_weights,
        trading_notional=trading_notional,
        one_way_turnover=one_way_turnover,
        transaction_costs=transaction_costs,
        gross_daily_returns=gross_daily,
        net_daily_returns=net_daily,
        benchmark_daily_returns=benchmark_daily,
        gross_nav=gross_nav,
        net_nav=net_nav,
        benchmark_nav=benchmark_nav,
        rebalance_audit=audit,
        first_investable_date=first_investable_date,
        nav_base_date=nav_base_date,
        raw_return_start_date=returns.index[0],
        indicator_warmup_trading_days=first_position,
    )


def determine_investable_start(
    target_weights: pd.DataFrame,
    rebalance_dates: pd.DatetimeIndex,
    returns: pd.DataFrame,
    momentum: pd.DataFrame,
    realized_volatility: pd.DataFrame,
) -> pd.Timestamp:
    """Return the first common date that can receive an invested return."""
    for signal_date in rebalance_dates:
        if signal_date not in target_weights.index:
            continue
        effective_date = _next_trading_date(signal_date, returns.index)
        if effective_date is None:
            continue
        valid_inputs = (
            _is_fully_invested(target_weights.loc[signal_date])
            and momentum.loc[signal_date, TICKERS].notna().all()
            and realized_volatility.loc[signal_date, TICKERS].notna().all()
            and returns.loc[effective_date, TICKERS + [BENCHMARK]].notna().all()
        )
        if valid_inputs:
            return effective_date
    raise ValueError("No date has complete signal, weight, and benchmark inputs for a common evaluation period.")


def save_backtest(run: BacktestRun, raw_price_start_date: pd.Timestamp) -> None:
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # NAV
    nav_df = pd.DataFrame({
        "strategy_gross": run.gross_nav,
        "strategy_net": run.net_nav,
        "benchmark": run.benchmark_nav,
    })
    nav_df.to_csv(DATA_PROCESSED_DIR / "nav.csv", date_format="%Y-%m-%d")

    # Daily returns
    ret_df = pd.DataFrame({
        "strategy_gross": run.gross_daily_returns,
        "strategy_net": run.net_daily_returns,
        "benchmark": run.benchmark_daily_returns,
    })
    ret_df.to_csv(DATA_PROCESSED_DIR / "portfolio_returns.csv", date_format="%Y-%m-%d")

    # Active weights
    run.evaluation_weights.to_csv(DATA_PROCESSED_DIR / "active_weights.csv", date_format="%Y-%m-%d")

    # TC
    pd.DataFrame({
        "trading_notional": run.trading_notional,
        "one_way_turnover": run.one_way_turnover,
        "transaction_cost": run.transaction_costs,
    }).to_csv(DATA_PROCESSED_DIR / "transaction_costs.csv", date_format="%Y-%m-%d")

    # Rebalance log
    run.rebalance_audit.to_csv(DATA_PROCESSED_DIR / "rebalance_log.csv", index=False, date_format="%Y-%m-%d")

    # Turnover
    pd.DataFrame({
        "trading_notional": run.trading_notional,
        "one_way_turnover": run.one_way_turnover,
    }).to_csv(DATA_PROCESSED_DIR / "turnover.csv", date_format="%Y-%m-%d")

    metadata = {
        "raw_price_start_date": str(raw_price_start_date.date()),
        "raw_return_start_date": str(run.raw_return_start_date.date()),
        "first_investable_date": str(run.first_investable_date.date()),
        "nav_base_date": str(run.nav_base_date.date()),
        "indicator_warmup_trading_days": run.indicator_warmup_trading_days,
        "evaluation_trading_days": len(run.net_daily_returns),
        "notes": (
            "Indicators retain warm-up history; comparative strategy and benchmark returns begin together "
            "on first_investable_date. NAV is 1.0 on nav_base_date and applies the first return on "
            "first_investable_date."
        ),
    }
    with open(DATA_PROCESSED_DIR / "backtest_metadata.json", "w") as file:
        json.dump(metadata, file, indent=2)

    log.info("Saved backtest outputs to %s", DATA_PROCESSED_DIR)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    prices, returns = load_processed()
    run = run_backtest(prices, returns)
    save_backtest(run, prices.index[0])
    print("\n✓ Backtest complete.")
    print(f"  Raw price start      : {prices.index[0].date()}")
    print(f"  First investable date: {run.first_investable_date.date()}")
    print(f"  NAV base date        : {run.nav_base_date.date()}")
    print(f"  Evaluation days      : {len(run.net_daily_returns)}")
    print(f"  Net final NAV        : {run.net_nav.iloc[-1]:.4f}")
    print(f"  Benchmark final NAV  : {run.benchmark_nav.iloc[-1]:.4f}")
    print(f"  Audited rebalances   : {len(run.rebalance_audit)}")
