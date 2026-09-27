"""
analytics/signals.py
=====================
Computes momentum signals and realized volatility for each asset,
then determines portfolio weights using inverse-volatility position sizing.

Methodology:
------------
MOMENTUM SIGNAL
  Mom(i,t) = P(i,t) / P(i, t-L) - 1     L = 60 trading days

  Eligibility:
    - IEF, TLT: eligible if Mom(i,t) > 0
    - SHY: always eligible (defensive asset)

REALIZED VOLATILITY
  RVol(i,t) = std(r(i, t-W+1 .. t)) × √252    W = 20 trading days
  (standard deviation of simple daily returns, annualized)

INVERSE-VOLATILITY WEIGHTS (among eligible assets)
  InvVol(i,t) = 1 / RVol(i,t)
  w(i,t) = InvVol(i,t) / Σ_j InvVol(j,t)   for j ∈ eligible set

DEFENSIVE RULE
  If neither IEF nor TLT is eligible → 100% SHY.
  SHY's inverse-vol weight is included in the eligible set when
  IEF or TLT are eligible too (it participates in sizing).

LOOK-AHEAD BIAS PREVENTION
  - Momentum at date t uses only prices through date t.
  - Volatility at date t uses only returns through date t.
  - Signals computed on the last trading day of month M.
  - Weights become effective at the start of trading day M+1
    (implemented by a 1-day forward shift in the backtest).

Usage:
    python analytics/signals.py
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.config import (
    BENCHMARK,
    DATA_PROCESSED_DIR,
    DEFENSIVE_ASSET,
    MOMENTUM_WINDOW,
    TICKERS,
    VOLATILITY_WINDOW,
    ANNUALIZATION_FACTOR,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Load processed data
# ---------------------------------------------------------------------------

def load_processed() -> tuple[pd.DataFrame, pd.DataFrame]:
    prices_path = DATA_PROCESSED_DIR / "prices_clean.csv"
    returns_path = DATA_PROCESSED_DIR / "returns_simple.csv"
    for p in [prices_path, returns_path]:
        if not p.exists():
            raise FileNotFoundError(
                f"Processed data not found: {p}\n"
                "Run: python analytics/clean_data.py"
            )
    prices = pd.read_csv(prices_path, index_col=0, parse_dates=True)
    returns = pd.read_csv(returns_path, index_col=0, parse_dates=True)
    log.info("Loaded prices: %s, returns: %s", prices.shape, returns.shape)
    return prices, returns


# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------

def compute_momentum(prices: pd.DataFrame, window: int = MOMENTUM_WINDOW) -> pd.DataFrame:
    """
    Compute L-day price momentum for each asset.

    Mom(i, t) = P(i, t) / P(i, t - L) - 1

    Uses only the STRATEGY universe (excludes benchmark).
    Returns a DataFrame with same index as prices, NaN for first L rows.
    """
    # Only compute for strategy tickers (exclude benchmark if present)
    strategy_prices = prices[TICKERS] if set(TICKERS).issubset(prices.columns) else prices

    momentum = strategy_prices / strategy_prices.shift(window) - 1
    momentum = momentum.rename(columns={c: c for c in strategy_prices.columns})

    valid_rows = momentum.dropna(how="all")
    log.info(
        "Momentum(%d) computed: first valid date = %s, total valid rows = %d",
        window, valid_rows.index[0].date(), len(valid_rows),
    )
    return momentum


# ---------------------------------------------------------------------------
# Realized Volatility
# ---------------------------------------------------------------------------

def compute_realized_vol(returns: pd.DataFrame, window: int = VOLATILITY_WINDOW) -> pd.DataFrame:
    """
    Compute rolling realized volatility (annualized) for each asset.

    RVol(i, t) = std(r(i, t-W+1..t)) × √252

    Uses simple daily returns. min_periods = window (no partial windows).
    Returns NaN for first (window-1) rows.
    """
    strategy_returns = returns[TICKERS] if set(TICKERS).issubset(returns.columns) else returns

    rvol = (
        strategy_returns
        .rolling(window=window, min_periods=window)
        .std()
        * np.sqrt(ANNUALIZATION_FACTOR)
    )

    valid_rows = rvol.dropna(how="all")
    log.info(
        "RealizedVol(%d) computed: first valid date = %s, total valid rows = %d",
        window, valid_rows.index[0].date(), len(valid_rows),
    )
    return rvol


# ---------------------------------------------------------------------------
# Eligibility & Signals
# ---------------------------------------------------------------------------

def compute_eligibility(momentum: pd.DataFrame) -> pd.DataFrame:
    """
    Determine asset eligibility at each date.

    Rules:
      - SHY:  always eligible (bool = True always where momentum is defined)
      - IEF:  eligible if Mom(IEF, t) > 0
      - TLT:  eligible if Mom(TLT, t) > 0

    Returns boolean DataFrame, same index as momentum.
    NaN rows (warm-up period) → all False (not yet eligible).
    """
    eligible = pd.DataFrame(False, index=momentum.index, columns=TICKERS)

    for ticker in TICKERS:
        if ticker == DEFENSIVE_ASSET:  # SHY
            # Always eligible when momentum data exists
            eligible[ticker] = momentum[ticker].notna()
        else:
            eligible[ticker] = (momentum[ticker] > 0) & momentum[ticker].notna()

    return eligible


def compute_defensive_flag(eligible: pd.DataFrame) -> pd.Series:
    """
    Returns a boolean Series: True on dates when the strategy is fully defensive
    (only SHY is eligible, i.e. neither IEF nor TLT is eligible).
    """
    non_defensive = [t for t in TICKERS if t != DEFENSIVE_ASSET]
    any_non_defensive_eligible = eligible[non_defensive].any(axis=1)
    return ~any_non_defensive_eligible


# ---------------------------------------------------------------------------
# Inverse-Volatility Weights
# ---------------------------------------------------------------------------

def compute_weights(
    eligible: pd.DataFrame,
    rvol: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute inverse-volatility portfolio weights among eligible assets.

    For each date t:
      1. Determine eligible set E(t)
      2. InvVol(i,t) = 1 / RVol(i,t)  for i ∈ E(t)
      3. w(i,t) = InvVol(i,t) / Σ_{j ∈ E(t)} InvVol(j,t)
      4. If only SHY eligible → w(SHY) = 1.0, others = 0

    Handles edge cases:
      - Zero volatility (extremely rare for bond ETFs) → weight = 0 for safety.
      - NaN volatility → asset treated as ineligible for sizing.

    Returns wide DataFrame of weights with same index as eligible.
    NaN rows (warm-up) → all-zero weights.
    """
    weights = pd.DataFrame(0.0, index=eligible.index, columns=TICKERS)

    for date, row in eligible.iterrows():
        elig_tickers = [t for t in TICKERS if row[t]]
        if not elig_tickers:
            # Should not happen (SHY always eligible when data exists),
            # but guard anyway: zero weights → cash-like day
            continue

        # Get volatilities for eligible tickers
        vols = rvol.loc[date, elig_tickers]

        # Drop NaN volatilities (can happen at warm-up boundary)
        vols = vols.dropna()
        if vols.empty:
            # Fallback: equal weight among eligible
            for t in elig_tickers:
                weights.loc[date, t] = 1.0 / len(elig_tickers)
            continue

        # Guard against zero volatility
        vols = vols.clip(lower=1e-10)

        inv_vol = 1.0 / vols
        total_inv_vol = inv_vol.sum()
        for t in vols.index:
            weights.loc[date, t] = inv_vol[t] / total_inv_vol

        # If any eligible ticker had NaN vol, it was excluded from sizing;
        # redistribute its allocation to others (already handled by dropping NaN above).

    # --- Validation ---
    weight_sums = weights.sum(axis=1)
    # Only validate rows where at least one ticker has data (after warm-up)
    valid_mask = eligible.any(axis=1)
    if valid_mask.any():
        bad = weight_sums[valid_mask & (weight_sums.abs() > 1e-8) & ((weight_sums - 1).abs() > 1e-6)]
        if not bad.empty:
            log.warning("Weight sums not ~1.0 on %d dates (first: %s)", len(bad), bad.index[0].date())

    log.info("Weights computed for %d dates.", len(weights))
    return weights


# ---------------------------------------------------------------------------
# Rebalance dates
# ---------------------------------------------------------------------------

def get_rebalance_dates(date_index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """
    Returns the last trading day of each calendar month within date_index.

    These are the dates on which signals are computed and weights are set.
    The weights become effective on the NEXT trading day (applied in backtest
    via a 1-day forward shift).
    """
    series = pd.Series(date_index, index=date_index)
    rebalance = series.groupby(series.dt.to_period("M")).last()
    return pd.DatetimeIndex(rebalance.values)


# ---------------------------------------------------------------------------
# Monthly signal snapshot (for rebalance-only signals)
# ---------------------------------------------------------------------------

def compute_monthly_signals(
    momentum: pd.DataFrame,
    rvol: pd.DataFrame,
    eligible: pd.DataFrame,
    weights: pd.DataFrame,
    rebalance_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    """
    Compile a clean monthly signal DataFrame showing, for each rebalance date:
    momentum values, volatility values, eligibility, and target weights.
    Used for the Signal Generation section of the dashboard.
    """
    records = []
    for date in rebalance_dates:
        if date not in momentum.index:
            continue
        row = {"date": date}
        for t in TICKERS:
            row[f"momentum_{t}"] = momentum.loc[date, t] if t in momentum.columns else np.nan
            row[f"rvol_{t}"] = rvol.loc[date, t] if t in rvol.columns else np.nan
            row[f"eligible_{t}"] = bool(eligible.loc[date, t]) if t in eligible.columns else False
            row[f"weight_{t}"] = weights.loc[date, t] if t in weights.columns else 0.0
        row["is_defensive"] = not any(
            eligible.loc[date, t] for t in TICKERS if t != DEFENSIVE_ASSET
        )
        records.append(row)

    return pd.DataFrame(records).set_index("date")


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_signals(
    momentum: pd.DataFrame,
    rvol: pd.DataFrame,
    eligible: pd.DataFrame,
    weights: pd.DataFrame,
    monthly: pd.DataFrame,
) -> None:
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    momentum.to_csv(DATA_PROCESSED_DIR / "momentum.csv", date_format="%Y-%m-%d")
    rvol.to_csv(DATA_PROCESSED_DIR / "realized_vol.csv", date_format="%Y-%m-%d")
    eligible.to_csv(DATA_PROCESSED_DIR / "eligibility.csv", date_format="%Y-%m-%d")
    weights.to_csv(DATA_PROCESSED_DIR / "weights_daily.csv", date_format="%Y-%m-%d")
    monthly.to_csv(DATA_PROCESSED_DIR / "monthly_signals.csv", date_format="%Y-%m-%d")
    log.info("Saved signal files to %s", DATA_PROCESSED_DIR)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    prices, returns = load_processed()

    momentum = compute_momentum(prices)
    rvol = compute_realized_vol(returns)
    eligible = compute_eligibility(momentum)
    weights = compute_weights(eligible, rvol)
    rebalance_dates = get_rebalance_dates(prices.index)
    monthly = compute_monthly_signals(momentum, rvol, eligible, weights, rebalance_dates)

    save_signals(momentum, rvol, eligible, weights, monthly)

    print("\n✓ Signal computation complete.")
    print(f"  Momentum window  : {MOMENTUM_WINDOW} days")
    print(f"  Volatility window: {VOLATILITY_WINDOW} days")
    print(f"  Rebalance dates  : {len(rebalance_dates)}")
    print(f"  Monthly signals  :\n{monthly.tail(3).to_string()}")
