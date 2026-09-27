"""
analytics/clean_data.py
========================
Reads raw prices from data/raw/prices_raw.csv, applies cleaning and
validation, and writes aligned/cleaned data to data/processed/.

Cleaning steps:
  1. Load raw prices
  2. Remove duplicate dates (raise if found in raw)
  3. Forward-fill isolated NaN values (≤ MAX_CONSECUTIVE_NAN)
  4. Trim to common available date range across all tickers
  5. Compute and store daily log returns and simple returns
  6. Run post-clean validation assertions
  7. Save processed files

Usage:
    python analytics/clean_data.py
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
    ALL_TICKERS,
    BENCHMARK,
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    DESIRED_START,
    MAX_CONSECUTIVE_NAN,
    MOMENTUM_WINDOW,
    TICKERS,
    VOLATILITY_WINDOW,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_raw() -> pd.DataFrame:
    raw_path = DATA_RAW_DIR / "prices_raw.csv"
    if not raw_path.exists():
        raise FileNotFoundError(
            f"Raw price file not found: {raw_path}\n"
            "Run: python analytics/download_data.py"
        )
    df = pd.read_csv(raw_path, index_col=0, parse_dates=True)
    df.index.name = "Date"
    log.info("Loaded raw prices: %s rows × %s cols", *df.shape)
    return df


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

def clean_prices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and clean raw price DataFrame.
    Returns a cleaned wide price DataFrame (columns = tickers).
    """

    # 1. Duplicate dates
    dups = df.index[df.index.duplicated()]
    if not dups.empty:
        raise ValueError(f"Duplicate dates in raw file: {dups.tolist()[:5]}")

    # 2. Sort ascending
    df = df.sort_index()

    # 3. Forward-fill isolated NaN (market microstructure gaps ≤ threshold)
    #    We never back-fill — that would use future information.
    for ticker in df.columns:
        nan_before = df[ticker].isna().sum()
        if nan_before > 0:
            # Check max consecutive run BEFORE filling
            s = df[ticker].isna().astype(int)
            max_run = (
                s.groupby((s != s.shift()).cumsum()).sum().max()
            )
            if max_run > MAX_CONSECUTIVE_NAN:
                raise ValueError(
                    f"[{ticker}] {max_run} consecutive NaN prices after loading. "
                    f"Cannot safely forward-fill. Review raw data."
                )
            df[ticker] = df[ticker].ffill()
            nan_after = df[ticker].isna().sum()
            log.info(
                "[%s] Forward-filled: %d NaN → %d NaN remaining.",
                ticker, nan_before, nan_after,
            )

    # 4. Find common date range (first non-NaN date for each ticker)
    first_valid = {col: df[col].first_valid_index() for col in df.columns}
    common_start = max(first_valid.values())
    log.info("Common start (all tickers have data): %s", common_start.date())
    df = df[df.index >= common_start]

    # 5. Drop rows still NaN for any ticker after forward-fill
    before = len(df)
    df = df.dropna(how="any")
    dropped = before - len(df)
    if dropped:
        log.warning("Dropped %d rows with remaining NaN after forward-fill.", dropped)

    # 6. Post-clean validation
    _validate_clean(df)

    log.info("Cleaned price DataFrame: %s rows × %s cols", *df.shape)
    log.info("Date range: %s → %s", df.index[0].date(), df.index[-1].date())
    return df


def _validate_clean(df: pd.DataFrame) -> None:
    """Assertions on the cleaned price DataFrame."""
    assert not df.empty, "Cleaned DataFrame is empty."
    assert df.index.is_monotonic_increasing, "Date index not sorted."
    assert not df.index.duplicated().any(), "Duplicate dates after cleaning."
    assert (df > 0).all().all(), "Non-positive prices after cleaning."
    assert not df.isna().any().any(), "NaN values remain after cleaning."
    log.info("Post-clean validation: all assertions passed.")


# ---------------------------------------------------------------------------
# Returns
# ---------------------------------------------------------------------------

def compute_returns(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute simple (arithmetic) daily returns and log returns.

    Simple returns:   r(t) = P(t)/P(t-1) - 1
    Log returns:      lr(t) = ln(P(t)/P(t-1))

    Returns are aligned: index[0] of returns corresponds to the first
    day where P(t-1) exists. The first price row is consumed to produce
    the first return; the returns DataFrame has (N-1) rows.

    NO forward-filling of returns. A missing price would produce NaN.
    """
    simple_ret = prices.pct_change(fill_method=None).iloc[1:]   # drop first NaN row
    log_ret = np.log(prices / prices.shift(1)).iloc[1:]

    # Validation
    assert not simple_ret.isna().any().any(), "NaN in simple returns after computation."
    assert not log_ret.isna().any().any(), "NaN in log returns after computation."
    assert (simple_ret > -1).all().all(), "Return of ≤ -100% found (impossible for ETFs)."

    log.info("Simple returns computed: %s rows", len(simple_ret))
    return simple_ret, log_ret


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_processed(
    prices: pd.DataFrame,
    simple_ret: pd.DataFrame,
    log_ret: pd.DataFrame,
) -> None:
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    prices.to_csv(DATA_PROCESSED_DIR / "prices_clean.csv", date_format="%Y-%m-%d")
    simple_ret.to_csv(DATA_PROCESSED_DIR / "returns_simple.csv", date_format="%Y-%m-%d")
    log_ret.to_csv(DATA_PROCESSED_DIR / "returns_log.csv", date_format="%Y-%m-%d")

    meta = {
        "processed_at_utc": datetime.now(timezone.utc).isoformat(),
        "start_date": str(prices.index[0].date()),
        "end_date": str(prices.index[-1].date()),
        "rows_prices": len(prices),
        "rows_returns": len(simple_ret),
        "columns": list(prices.columns),
        "notes": (
            "Prices forward-filled for isolated gaps (≤ 5 consecutive). "
            "Returns computed as pct_change(). First price row consumed. "
            "All prices positive, no NaN, dates ascending."
        ),
    }
    with open(DATA_PROCESSED_DIR / "clean_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    log.info("Saved: prices_clean.csv, returns_simple.csv, returns_log.csv, clean_meta.json")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    raw = load_raw()
    prices = clean_prices(raw)
    simple_ret, log_ret = compute_returns(prices)
    save_processed(prices, simple_ret, log_ret)

    print("\n✓ Data cleaning complete.")
    print(f"  Price rows   : {len(prices)}")
    print(f"  Return rows  : {len(simple_ret)}")
    print(f"  Date range   : {prices.index[0].date()} → {prices.index[-1].date()}")
    print(f"  Tickers      : {list(prices.columns)}")
