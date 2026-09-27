"""
analytics/backtest.py
======================
Implements the portfolio backtesting engine.

CRITICAL: Look-ahead bias prevention is the top priority.

Timeline:
---------
  Day t-1 (last day of month M):
    → Compute signals using data through close of t-1
    → Determine target weights

  Day t (first day of month M+1):
    → Weights become effective (SIGNAL_TO_WEIGHT_LAG = 1)
    → Strategy earns r(t) × w(i, t-1)

This is implemented by shifting the weight series forward by 1 trading day.

Key outputs:
------------
  - strategy_nav:    daily NAV series (gross)
  - strategy_nav_net: daily NAV series (net of transaction costs)
  - benchmark_nav:   AGG buy-and-hold NAV
  - weights_active:  weights that were actually in use on each day
  - turnover:        absolute weight change per rebalance date
  - rebalance_log:   detailed log of each rebalance event

Transaction costs:
------------------
  TC(t) = Σ_i |w_new(i) - w_old(i)| × TC_rate / 2
  (TC_rate split between entry and exit for round-trip representation,
   but applied as a one-way cost per unit of absolute change)

  Actually we implement: TC(t) = Σ_i |Δw(i)| × TC_rate
  where TC_rate = 0.0002 (2 basis points one-way per unit of weight change).
  This is applied as a cost on the rebalance date.

Usage:
    python analytics/backtest.py
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.config import (
    BENCHMARK,
    DATA_PROCESSED_DIR,
    DEFENSIVE_ASSET,
    SIGNAL_TO_WEIGHT_LAG,
    TICKERS,
    TRANSACTION_COST_RATE,
)
from analytics.signals import (
    compute_eligibility,
    compute_momentum,
    compute_realized_vol,
    compute_weights,
    get_rebalance_dates,
    load_processed,
    compute_monthly_signals,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Build active weights (with lag and monthly rebalancing)
# ---------------------------------------------------------------------------

def build_active_weights(
    weights_daily: pd.DataFrame,
    rebalance_dates: pd.DatetimeIndex,
    all_dates: pd.DatetimeIndex,
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
    # Initialize with NaN; we'll fill on rebalance dates only
    rebalance_weights = pd.DataFrame(np.nan, index=all_dates, columns=TICKERS)

    for rdate in rebalance_dates:
        if rdate in weights_daily.index:
            rebalance_weights.loc[rdate] = weights_daily.loc[rdate].values

    # Forward-fill: hold weights between rebalances
    active = rebalance_weights.ffill()

    # Before the first rebalance date where we have valid weights,
    # there are NaN rows (warm-up). Fill with 0 (no position = cash).
    active = active.fillna(0.0)

    # Apply look-ahead lag: shift weights forward by 1 day
    # This means the weight determined at end of day t is used for day t+1 return.
    active = active.shift(SIGNAL_TO_WEIGHT_LAG)
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

def compute_turnover(active_weights: pd.DataFrame, rebalance_dates: pd.DatetimeIndex) -> pd.Series:
    """
    Compute one-way portfolio turnover on each rebalance date.
    Turnover(t) = Σ_i |w(i,t) - w(i,t_prev)| / 2
    (divide by 2 for one-way; standard convention)
    Actually returning full Σ|Δw| and labelling correctly.

    Note: we compare weight BEFORE shift (i.e., before look-ahead lag)
    because the shift is a mechanical operation, not an economic change.
    """
    weight_changes = active_weights.diff().abs()

    # Turnover only meaningful on rebalance dates (where weights actually change)
    turnover = pd.Series(np.nan, index=rebalance_dates)
    for rdate in rebalance_dates:
        if rdate in active_weights.index:
            # Find the next trading day (the day weights become effective)
            date_pos = active_weights.index.get_loc(rdate)
            next_pos = date_pos + SIGNAL_TO_WEIGHT_LAG
            if next_pos < len(active_weights):
                next_date = active_weights.index[next_pos]
                turnover[rdate] = weight_changes.loc[next_date].sum()
    return turnover.dropna()


# ---------------------------------------------------------------------------
# Transaction costs
# ---------------------------------------------------------------------------

def compute_transaction_costs(
    active_weights: pd.DataFrame,
    tc_rate: float = TRANSACTION_COST_RATE,
) -> pd.Series:
    """
    Compute daily transaction cost series.
    Cost is only incurred when weights change (on effective rebalance days).

    TC(t) = Σ_i |w(i,t) - w(i,t-1)| × tc_rate
    """
    weight_changes = active_weights.diff().abs().sum(axis=1)
    tc_series = weight_changes * tc_rate
    return tc_series


# ---------------------------------------------------------------------------
# NAV computation
# ---------------------------------------------------------------------------

def compute_nav(
    returns: pd.DataFrame,
    active_weights: pd.DataFrame,
    tc_series: pd.Series,
    start_value: float = 1.0,
) -> tuple[pd.Series, pd.Series]:
    """
    Compute gross and net NAV time series.

    Gross:  r_port(t) = Σ_i w(i,t) × r(i,t)
    Net:    r_port_net(t) = r_port(t) - TC(t)

    Starting NAV = 1.0 (normalized).

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

    # Compute NAV
    gross_nav = (1 + gross_daily).cumprod() * start_value
    net_nav = (1 + net_daily).cumprod() * start_value

    log.info(
        "NAV computed: %d days, gross cumulative: %.4f, net cumulative: %.4f",
        len(gross_nav), gross_nav.iloc[-1], net_nav.iloc[-1],
    )
    return gross_nav, net_daily, gross_daily, net_nav


def compute_benchmark_nav(
    returns: pd.DataFrame,
    benchmark: str = BENCHMARK,
    start_value: float = 1.0,
) -> tuple[pd.Series, pd.Series]:
    """
    Buy-and-hold benchmark NAV (AGG).
    100% invested in benchmark on day 1, no transaction costs, no rebalancing.
    """
    bench_ret = returns[benchmark]
    bench_nav = (1 + bench_ret).cumprod() * start_value
    return bench_nav, bench_ret


# ---------------------------------------------------------------------------
# Rebalance log
# ---------------------------------------------------------------------------

def build_rebalance_log(
    active_weights: pd.DataFrame,
    rebalance_dates: pd.DatetimeIndex,
    turnover: pd.Series,
    tc_series: pd.Series,
) -> pd.DataFrame:
    """
    Build a human-readable log of each rebalance event.
    """
    records = []
    for i, rdate in enumerate(rebalance_dates):
        # The weights become effective 1 day after rdate
        date_pos = active_weights.index.get_loc(rdate) if rdate in active_weights.index else None
        if date_pos is None:
            continue
        eff_pos = date_pos + SIGNAL_TO_WEIGHT_LAG
        if eff_pos >= len(active_weights):
            continue
        eff_date = active_weights.index[eff_pos]
        w = active_weights.loc[eff_date]
        to = turnover.get(rdate, np.nan)
        tc = tc_series.iloc[eff_pos] if eff_pos < len(tc_series) else np.nan
        records.append({
            "signal_date": rdate.date(),
            "effective_date": eff_date.date(),
            "weight_SHY": round(w.get("SHY", 0), 6),
            "weight_IEF": round(w.get("IEF", 0), 6),
            "weight_TLT": round(w.get("TLT", 0), 6),
            "weight_sum": round(w.sum(), 6),
            "turnover_oneway": round(to, 6) if not np.isnan(to) else np.nan,
            "tc_cost": round(tc, 8) if not np.isnan(tc) else np.nan,
        })
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Validate look-ahead bias (programmatic assertion)
# ---------------------------------------------------------------------------

def assert_no_lookahead(
    active_weights: pd.DataFrame,
    momentum: pd.DataFrame,
    rebalance_dates: pd.DatetimeIndex,
) -> None:
    """
    Programmatic check: for each rebalance date r, verify that the weights
    effective at r+1 are consistent with momentum values at r (not r+1 or later).

    Specifically: if momentum at r+1 > 0 but momentum at r ≤ 0, yet we are
    holding a non-defensive weight, that would indicate look-ahead bias.

    This test checks the structure rather than exhaustively checking every date.
    """
    errors = []
    for rdate in rebalance_dates:
        if rdate not in momentum.index:
            continue
        rdate_pos = active_weights.index.get_loc(rdate) if rdate in active_weights.index else None
        if rdate_pos is None:
            continue
        eff_pos = rdate_pos + SIGNAL_TO_WEIGHT_LAG
        if eff_pos >= len(active_weights):
            continue
        eff_date = active_weights.index[eff_pos]

        # Weight at effective date
        eff_weight = active_weights.loc[eff_date]

        # Signal date momentum
        signal_mom = momentum.loc[rdate]

        # For non-defensive tickers, check: if signal_mom ≤ 0 but weight > 0
        for t in [tkr for tkr in TICKERS if tkr != DEFENSIVE_ASSET]:
            if signal_mom[t] <= 0 and eff_weight[t] > 1e-8:
                errors.append(
                    f"Possible look-ahead on rebalance {rdate.date()}: "
                    f"{t} has mom={signal_mom[t]:.4f} ≤ 0 but effective weight={eff_weight[t]:.4f}"
                )

    if errors:
        for e in errors[:5]:
            log.error("LOOK-AHEAD CHECK FAILED: %s", e)
        raise AssertionError(
            f"Look-ahead bias checks failed on {len(errors)} rebalance dates. See logs."
        )
    log.info("Look-ahead bias assertion: PASSED (%d rebalance dates checked)", len(rebalance_dates))


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_backtest(
    gross_nav: pd.Series,
    net_nav: pd.Series,
    bench_nav: pd.Series,
    gross_daily: pd.Series,
    net_daily: pd.Series,
    bench_daily: pd.Series,
    active_weights: pd.DataFrame,
    tc_series: pd.Series,
    rebalance_log: pd.DataFrame,
    turnover: pd.Series,
) -> None:
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # NAV
    nav_df = pd.DataFrame({
        "strategy_gross": gross_nav,
        "strategy_net": net_nav,
        "benchmark": bench_nav,
    })
    nav_df.to_csv(DATA_PROCESSED_DIR / "nav.csv", date_format="%Y-%m-%d")

    # Daily returns
    ret_df = pd.DataFrame({
        "strategy_gross": gross_daily,
        "strategy_net": net_daily,
        "benchmark": bench_daily,
    })
    ret_df.to_csv(DATA_PROCESSED_DIR / "portfolio_returns.csv", date_format="%Y-%m-%d")

    # Active weights
    active_weights.to_csv(DATA_PROCESSED_DIR / "active_weights.csv", date_format="%Y-%m-%d")

    # TC
    tc_series.to_csv(DATA_PROCESSED_DIR / "transaction_costs.csv", date_format="%Y-%m-%d", header=True)

    # Rebalance log
    rebalance_log.to_csv(DATA_PROCESSED_DIR / "rebalance_log.csv", index=False)

    # Turnover
    turnover.to_csv(DATA_PROCESSED_DIR / "turnover.csv", date_format="%Y-%m-%d", header=True)

    log.info("Saved backtest outputs to %s", DATA_PROCESSED_DIR)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    prices, returns = load_processed()

    # Compute signals
    momentum = compute_momentum(prices)
    rvol = compute_realized_vol(returns)
    eligible = compute_eligibility(momentum)
    weights_daily = compute_weights(eligible, rvol)
    rebalance_dates = get_rebalance_dates(prices.index)

    # Build active weight series (with monthly rebalancing + 1-day lag)
    active_weights = build_active_weights(weights_daily, rebalance_dates, returns.index)

    # Look-ahead bias assertion
    assert_no_lookahead(active_weights, momentum, rebalance_dates)

    # Transaction costs
    tc_series = compute_transaction_costs(active_weights)

    # NAV
    gross_nav, net_daily, gross_daily, net_nav = compute_nav(
        returns, active_weights, tc_series
    )
    bench_nav, bench_daily = compute_benchmark_nav(returns)

    # Align all series to common index
    common_idx = gross_nav.index.intersection(bench_nav.index)
    gross_nav = gross_nav.loc[common_idx]
    net_nav = net_nav.loc[common_idx]
    bench_nav = bench_nav.loc[common_idx]
    gross_daily = gross_daily.loc[common_idx]
    net_daily = net_daily.loc[common_idx]
    bench_daily = bench_daily.loc[common_idx]

    # Turnover & rebalance log
    turnover = compute_turnover(active_weights, rebalance_dates)
    rebalance_log = build_rebalance_log(active_weights, rebalance_dates, turnover, tc_series)

    # Save
    save_backtest(
        gross_nav, net_nav, bench_nav,
        gross_daily, net_daily, bench_daily,
        active_weights, tc_series,
        rebalance_log, turnover,
    )

    print("\n✓ Backtest complete.")
    print(f"  Period           : {gross_nav.index[0].date()} → {gross_nav.index[-1].date()}")
    print(f"  Days             : {len(gross_nav)}")
    print(f"  Gross final NAV  : {gross_nav.iloc[-1]:.4f}")
    print(f"  Net final NAV    : {net_nav.iloc[-1]:.4f}")
    print(f"  Benchmark final  : {bench_nav.iloc[-1]:.4f}")
    print(f"  Rebalances       : {len(rebalance_log)}")
    print(f"  Avg turnover     : {turnover.mean():.4f}")
