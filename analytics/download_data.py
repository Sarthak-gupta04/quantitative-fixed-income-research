"""
analytics/download_data.py
===========================
Downloads historical price data for the fixed-income ETF universe from
Yahoo Finance via yfinance, performs pre-download validation, and saves
raw price series to data/raw/.

Usage:
    python analytics/download_data.py

Outputs:
    data/raw/prices_raw.csv   — raw adjusted-price DataFrame (wide format)
    data/raw/download_meta.json — metadata about the download

Important:
    yfinance ≥ 0.2.54 changes the multi-ticker download API slightly.
    We explicitly inspect the returned columns/keys rather than hardcoding
    field names, to avoid silent failures if Yahoo changes their response.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Ensure analytics package is importable when run as a script from any cwd
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.config import (
    ALL_TICKERS,
    DATA_RAW_DIR,
    DESIRED_END,
    DESIRED_START,
    MAX_CONSECUTIVE_NAN,
    MIN_COVERAGE_FRACTION,
    TICKER_NAMES,
)

# Keep the data-provider cache within the project rather than a protected
# user-profile location.  It is an operational download cache only; raw input
# snapshots remain the CSV files recorded in download metadata.
DATA_PROVIDER_CACHE_DIR = DATA_RAW_DIR / ".yfinance_cache"
yf.cache.set_cache_location(DATA_PROVIDER_CACHE_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_price_field(df: pd.DataFrame, ticker: str) -> pd.Series:
    """
    Inspect the DataFrame returned by yfinance and extract the best
    available total-return price series for a given ticker.

    yfinance 1.7.x returns a MultiIndex where:
      level 0 (name='Price')  = field name: 'Adj Close', 'Close', etc.
      level 1 (name='Ticker') = ticker symbol

    We prefer 'Adj Close' (total-return proxy: dividends reinvested, splits adjusted).
    Fall back to 'Close' with a warning if 'Adj Close' is absent.
    """
    cols = df.columns

    # --- MultiIndex case (both single and multi-ticker in yfinance 1.7.x) ---
    if isinstance(cols, pd.MultiIndex):
        # Level 0 holds the price-field names regardless of its label
        price_types = cols.get_level_values(0).unique().tolist()
        log.debug("MultiIndex price fields available: %s", price_types)

        if "Adj Close" in price_types:
            series = df["Adj Close"]
            # If multi-ticker: df["Adj Close"] is a DataFrame; select the ticker column
            if isinstance(series, pd.DataFrame):
                if ticker not in series.columns:
                    raise KeyError(f"[{ticker}] not found in 'Adj Close' sub-DataFrame. "
                                   f"Available: {list(series.columns)}")
                return series[ticker]
            return series  # Single-ticker case: already a Series

        elif "Close" in price_types:
            log.warning(
                "[%s] 'Adj Close' not found. Using 'Close'. "
                "Returns will NOT include dividend reinvestment.",
                ticker,
            )
            series = df["Close"]
            if isinstance(series, pd.DataFrame):
                return series[ticker]
            return series

        else:
            raise KeyError(
                f"[{ticker}] Neither 'Adj Close' nor 'Close' found. "
                f"Available price fields: {price_types}"
            )

    # --- Flat Index case ---
    flat_cols = cols.tolist()
    log.debug("Flat columns: %s", flat_cols)
    if "Adj Close" in flat_cols:
        return df["Adj Close"]
    elif "Close" in flat_cols:
        log.warning("[%s] 'Adj Close' not found in flat columns. Using 'Close'.", ticker)
        return df["Close"]
    else:
        raise KeyError(
            f"[{ticker}] Neither 'Adj Close' nor 'Close' found in flat columns: {flat_cols}"
        )


def _validate_single_series(series: pd.Series, ticker: str) -> None:
    """
    Run pre-validation checks on a raw price series.
    Raises ValueError on critical failures.
    Logs warnings on non-critical issues.
    """
    # 1. Non-empty
    if series.empty:
        raise ValueError(f"[{ticker}] Downloaded series is empty.")

    # 2. Duplicate dates
    dups = series.index[series.index.duplicated()].tolist()
    if dups:
        raise ValueError(f"[{ticker}] Duplicate dates found: {dups[:5]}…")

    # 3. Date ordering
    if not series.index.is_monotonic_increasing:
        raise ValueError(f"[{ticker}] Dates are not in ascending order.")

    # 4. No negative or zero prices
    bad_prices = series[series <= 0].dropna()
    if not bad_prices.empty:
        raise ValueError(
            f"[{ticker}] Non-positive prices found on {len(bad_prices)} dates. "
            f"First: {bad_prices.index[0].date()} = {bad_prices.iloc[0]}"
        )

    # 5. NaN count
    nan_count = series.isna().sum()
    if nan_count > 0:
        log.warning("[%s] %d NaN values in raw price series.", ticker, nan_count)

    # 6. Consecutive NaN check
    if nan_count > 0:
        consecutive_nan = (
            series.isna()
            .astype(int)
            .groupby((series.isna() != series.isna().shift()).cumsum())
            .sum()
            .max()
        )
        if consecutive_nan > MAX_CONSECUTIVE_NAN:
            raise ValueError(
                f"[{ticker}] {consecutive_nan} consecutive NaN prices found "
                f"(threshold: {MAX_CONSECUTIVE_NAN}). Possible data gap."
            )

    log.info("[%s] Single-series validation passed. %d rows, %d NaN.", ticker, len(series), nan_count)


# ---------------------------------------------------------------------------
# Main download function
# ---------------------------------------------------------------------------

def download_prices(
    tickers: list[str] = ALL_TICKERS,
    start: str = DESIRED_START,
    end: str | None = DESIRED_END,
) -> pd.DataFrame:
    """
    Download adjusted closing prices for all tickers via yfinance.

    Returns a wide DataFrame:
        index  = DatetimeIndex (trading days)
        columns = ticker symbols
    """
    log.info("Downloading tickers: %s  |  start=%s  end=%s", tickers, start, end or "latest")

    # --- Download ---
    raw = yf.download(
        tickers=tickers,
        start=start,
        end=end,
        auto_adjust=False,   # Keep raw OHLCV + Adj Close columns explicitly
        actions=False,       # We don't need dividends/splits separately
        progress=False,
        # A single request sequence avoids a cache-initialisation race in
        # current yfinance releases on Windows.  It does not change prices,
        # fields, dates, or portfolio methodology.
        threads=False,
    )

    if raw is None or raw.empty:
        raise RuntimeError("yfinance returned empty data. Check network and tickers.")

    log.info("Raw download shape: %s", raw.shape)
    log.debug("Raw columns (first 10): %s", list(raw.columns)[:10])

    # --- Inspect what yfinance actually returned ---
    # Determine if MultiIndex or flat
    is_multi = isinstance(raw.columns, pd.MultiIndex)
    log.info("Column structure: %s", "MultiIndex" if is_multi else "flat")

    # Determine which price type was returned
    if is_multi:
        available_types = raw.columns.get_level_values(0).unique().tolist()
        log.info("Available price fields (MultiIndex level 0): %s", available_types)
        price_field = "Adj Close" if "Adj Close" in available_types else "Close"
    else:
        price_field = "Adj Close" if "Adj Close" in raw.columns else "Close"

    log.info("Price field selected: '%s'", price_field)

    # --- Extract price DataFrame ---
    price_df = pd.DataFrame()
    actual_field_used: dict[str, str] = {}

    for ticker in tickers:
        try:
            s = _resolve_price_field(raw, ticker)
            s = s.rename(ticker)
            s.index = pd.to_datetime(s.index)
            # Remove timezone info for consistency (yfinance may or may not include it)
            if hasattr(s.index, "tz") and s.index.tz is not None:
                s.index = s.index.tz_localize(None)
            _validate_single_series(s, ticker)
            price_df[ticker] = s
            actual_field_used[ticker] = price_field
        except (KeyError, ValueError) as exc:
            log.error("Failed to extract/validate [%s]: %s", ticker, exc)
            raise

    # --- Common date alignment ---
    # Drop rows where ALL tickers are NaN (genuine market holidays)
    price_df = price_df.dropna(how="all")

    # Log coverage
    for ticker in tickers:
        non_nan = price_df[ticker].notna().sum()
        total = len(price_df)
        coverage = non_nan / total
        log.info("[%s] Coverage: %d/%d days (%.1f%%)", ticker, non_nan, total, coverage * 100)
        if coverage < MIN_COVERAGE_FRACTION:
            raise ValueError(
                f"[{ticker}] Coverage {coverage:.1%} < required {MIN_COVERAGE_FRACTION:.0%}."
            )

    log.info("Final aligned price DataFrame: %s rows × %s columns", *price_df.shape)
    log.info("Date range: %s → %s", price_df.index[0].date(), price_df.index[-1].date())

    return price_df, actual_field_used


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_raw(price_df: pd.DataFrame, field_used: dict[str, str]) -> None:
    """Persist raw prices and download metadata."""
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Prices
    raw_path = DATA_RAW_DIR / "prices_raw.csv"
    price_df.to_csv(raw_path, date_format="%Y-%m-%d")
    log.info("Saved raw prices → %s", raw_path)

    # Metadata
    meta = {
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "tickers": list(price_df.columns),
        "price_field_per_ticker": field_used,
        "start_date": str(price_df.index[0].date()),
        "end_date": str(price_df.index[-1].date()),
        "total_rows": len(price_df),
        "nan_counts": price_df.isna().sum().to_dict(),
        "yfinance_auto_adjust": False,
        "notes": (
            "Prices are adjusted-close where 'Adj Close' is available from yfinance. "
            "This is a total-return proxy (dividends reinvested, splits adjusted). "
            "Source: Yahoo Finance via yfinance. "
            "Not suitable as live investment data. Educational use only."
        ),
    }
    meta_path = DATA_RAW_DIR / "download_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    log.info("Saved download metadata → %s", meta_path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    price_df, field_used = download_prices()
    save_raw(price_df, field_used)
    print("\n✓ Data download complete.")
    print(f"  Rows      : {len(price_df)}")
    print(f"  Columns   : {list(price_df.columns)}")
    print(f"  Date range: {price_df.index[0].date()} → {price_df.index[-1].date()}")
    print(f"  Price field: {field_used}")
