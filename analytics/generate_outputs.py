"""
analytics/generate_outputs.py
==============================
Reads all processed analytical data and generates clean JSON files
in public/data/ for consumption by the Next.js frontend.

The frontend NEVER calculates financial metrics — it only reads these files.
All numbers shown in the UI originate here.

Generated files:
----------------
  public/data/summary_stats.json     — KPI summary (perf + risk)
  public/data/nav_series.json        — Daily NAV time series (strategy + benchmark)
  public/data/annual_returns.json    — Annual return bar chart data
  public/data/monthly_returns.json   — Monthly return heatmap data
  public/data/rolling_metrics.json   — Rolling vol, Sharpe, drawdown series
  public/data/signals.json           — Monthly signal snapshots
  public/data/weights.json           — Daily active portfolio weights
  public/data/rebalance_log.json     — Per-rebalance event log
  public/data/volatility.json        — Individual ETF rolling vol series
  public/data/meta.json              — Data coverage, refresh timestamp

Usage:
    python analytics/generate_outputs.py
"""

import json
import logging
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.config import (
    ALL_TICKERS,
    ANNUALIZATION_FACTOR,
    BENCHMARK,
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    DEFENSIVE_ASSET,
    MOMENTUM_WINDOW,
    PUBLIC_DATA_DIR,
    TICKER_NAMES,
    TICKERS,
    TRANSACTION_COST_BPS,
    VOLATILITY_WINDOW,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def clean_float(val) -> float | None:
    """Convert to float, replacing NaN/Inf with None for JSON safety."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def series_to_records(
    s: pd.Series,
    value_name: str = "value",
    date_every_nth: int = 1,
) -> list[dict]:
    """Convert a Series to a list of {date, value} dicts. Subsample if needed."""
    records = []
    for i, (date, val) in enumerate(s.items()):
        if i % date_every_nth != 0:
            continue
        records.append({
            "date": str(date.date()) if hasattr(date, "date") else str(date),
            value_name: clean_float(val),
        })
    return records


def df_to_multi_records(df: pd.DataFrame, date_every_nth: int = 1) -> list[dict]:
    """Convert a DataFrame to a list of {date, col1, col2, ...} dicts."""
    records = []
    for i, (date, row) in enumerate(df.iterrows()):
        if i % date_every_nth != 0:
            continue
        record = {"date": str(date.date()) if hasattr(date, "date") else str(date)}
        for col in df.columns:
            record[col] = clean_float(row[col])
        records.append(record)
    return records


# ---------------------------------------------------------------------------
# Load processed files
# ---------------------------------------------------------------------------

def load_all() -> dict:
    # Files that have date indices
    date_files = {
        "nav": "nav.csv",
        "portfolio_returns": "portfolio_returns.csv",
        "rolling_metrics": "rolling_metrics.csv",
        "monthly_signals": "monthly_signals.csv",
        "active_weights": "active_weights.csv",
        "momentum": "momentum.csv",
        "realized_vol": "realized_vol.csv",
    }
    # Files that have non-date indices (integer years, etc.)
    non_date_files = {
        "annual_returns": "annual_returns.csv",
        "monthly_returns": "monthly_returns.csv",
        "turnover": "turnover.csv",
    }
    json_files = {
        "summary_stats": "summary_stats.json",
    }

    data = {}

    for key, filename in json_files.items():
        path = DATA_PROCESSED_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}\nRun the full analytics pipeline first.")
        with open(path) as f:
            data[key] = json.load(f)
        log.info("Loaded: %s", filename)

    for key, filename in date_files.items():
        path = DATA_PROCESSED_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}\nRun the full analytics pipeline first.")
        data[key] = pd.read_csv(path, index_col=0, parse_dates=True)
        log.info("Loaded: %s", filename)

    for key, filename in non_date_files.items():
        path = DATA_PROCESSED_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}\nRun the full analytics pipeline first.")
        data[key] = pd.read_csv(path, index_col=0)
        log.info("Loaded: %s", filename)

    # The first CSV column is signal_date, not an index to discard.
    data["rebalance_log"] = load_rebalance_log(DATA_PROCESSED_DIR / "rebalance_log.csv")

    return data


def load_rebalance_log(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}\nRun the full analytics pipeline first.")
    rebal = pd.read_csv(path)
    if "signal_date" not in rebal.columns or rebal["signal_date"].isna().any():
        raise ValueError(f"Rebalance log is missing signal_date: {path}")
    log.info("Loaded: %s", path.name)
    return rebal



# ---------------------------------------------------------------------------
# Generate individual JSON outputs
# ---------------------------------------------------------------------------

def gen_summary(data: dict) -> dict:
    """Pass-through summary stats with minor formatting."""
    summary = data["summary_stats"]
    # Round floats for readability
    def round_recursive(obj, decimals=6):
        if isinstance(obj, dict):
            return {k: round_recursive(v, decimals) for k, v in obj.items()}
        if isinstance(obj, float):
            return round(obj, decimals)
        return obj
    return round_recursive(summary)


def gen_nav_series(data: dict) -> list[dict]:
    """
    NAV time series for the cumulative wealth chart.
    Subsampled to weekly (every 5 trading days) for performance.
    """
    nav = data["nav"]
    # Keep full resolution — frontend can handle it
    records = []
    for date, row in nav.iterrows():
        records.append({
            "date": str(date.date()),
            "strategy_gross": clean_float(row.get("strategy_gross")),
            "strategy_net": clean_float(row.get("strategy_net")),
            "benchmark": clean_float(row.get("benchmark")),
        })
    return records


def gen_annual_returns(data: dict) -> list[dict]:
    ann = data["annual_returns"]
    records = []
    for year, row in ann.iterrows():
        # Index may be int or Timestamp depending on pandas read_csv behavior
        year_int = year.year if hasattr(year, "year") else int(year)
        records.append({
            "year": year_int,
            "strategy_net": clean_float(row.get("strategy_net")),
            "benchmark": clean_float(row.get("benchmark")),
        })
    return sorted(records, key=lambda x: x["year"])



def gen_monthly_returns(data: dict) -> list[dict]:
    """Monthly returns for heatmap. Returns {year, month, strategy_net}."""
    monthly = data["monthly_returns"]
    records = []
    for year, row in monthly.iterrows():
        for col in monthly.columns:
            month_num = int(col) if not isinstance(col, tuple) else int(col[1])
            records.append({
                "year": int(year),
                "month": month_num,
                "return": clean_float(row[col]),
            })
    return records


def gen_rolling_metrics(data: dict) -> list[dict]:
    """Rolling vol, Sharpe, drawdown. Keep full resolution."""
    rolling = data["rolling_metrics"]
    return df_to_multi_records(rolling)


def gen_signals(data: dict) -> list[dict]:
    """Monthly signal snapshots."""
    signals = data["monthly_signals"]
    records = []
    for date, row in signals.iterrows():
        record = {"date": str(date.date())}
        for t in TICKERS:
            record[f"momentum_{t}"] = clean_float(row.get(f"momentum_{t}"))
            record[f"rvol_{t}"] = clean_float(row.get(f"rvol_{t}"))
            record[f"eligible_{t}"] = bool(row.get(f"eligible_{t}", False))
            record[f"weight_{t}"] = clean_float(row.get(f"weight_{t}"))
        record["is_defensive"] = bool(row.get("is_defensive", False))
        records.append(record)
    return records


def gen_weights(data: dict) -> list[dict]:
    """Daily active weights (subsampled to weekly for file size)."""
    weights = data["active_weights"]
    # Subsample to every 5th day (weekly) for frontend
    records = []
    for i, (date, row) in enumerate(weights.iterrows()):
        if i % 5 != 0:
            continue
        record = {"date": str(date.date())}
        for t in TICKERS:
            record[t] = clean_float(row.get(t, 0))
        records.append(record)
    return records


def gen_rebalance_log(data: dict) -> list[dict]:
    """Rebalance event log."""
    rebal = data["rebalance_log"]
    records = []
    for _, row in rebal.iterrows():
        records.append({
            "signal_date": str(row.get("signal_date", "")),
            "effective_date": str(row.get("effective_date", "")),
            "first_return_date": str(row.get("first_return_date", "")),
            "next_signal_date": str(row.get("next_signal_date", "")),
            "weight_SHY": clean_float(row.get("weight_SHY")),
            "weight_IEF": clean_float(row.get("weight_IEF")),
            "weight_TLT": clean_float(row.get("weight_TLT")),
            "weight_sum": clean_float(row.get("weight_sum")),
            "trading_notional": clean_float(row.get("trading_notional")),
            "one_way_turnover": clean_float(row.get("one_way_turnover")),
            "transaction_cost": clean_float(row.get("transaction_cost")),
        })
    return records


def gen_volatility(data: dict) -> list[dict]:
    """Individual ETF rolling 20-day volatility (subsampled weekly)."""
    rolling = data["rolling_metrics"]
    vol_cols = [c for c in rolling.columns if "rolling_vol" in c]
    records = []
    for i, (date, row) in enumerate(rolling.iterrows()):
        if i % 5 != 0:
            continue
        record = {"date": str(date.date())}
        for col in vol_cols:
            record[col] = clean_float(row[col])
        records.append(record)
    return records


def gen_meta(data: dict) -> dict:
    """Metadata about the data and last refresh."""
    try:
        with open(DATA_RAW_DIR / "download_meta.json") as f:
            dl_meta = json.load(f)
    except FileNotFoundError:
        dl_meta = {}

    summary_meta = data["summary_stats"].get("metadata", {})

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "start_date": summary_meta.get("start_date"),
        "end_date": summary_meta.get("end_date"),
        "trading_days": summary_meta.get("trading_days"),
        "tickers": TICKERS,
        "ticker_names": TICKER_NAMES,
        "benchmark": BENCHMARK,
        "momentum_window_days": MOMENTUM_WINDOW,
        "volatility_window_days": VOLATILITY_WINDOW,
        "annualization_factor": ANNUALIZATION_FACTOR,
        "transaction_cost_bps": TRANSACTION_COST_BPS,
        "risk_free_rate_annual": 0.0,
        "raw_price_start_date": summary_meta.get("raw_price_start_date"),
        "raw_return_start_date": summary_meta.get("raw_return_start_date"),
        "first_investable_date": summary_meta.get("first_investable_date"),
        "nav_base_date": summary_meta.get("nav_base_date"),
        "indicator_warmup_trading_days": summary_meta.get("indicator_warmup_trading_days"),
        "download_meta": dl_meta,
        "disclaimer": (
            "This project is an educational quantitative research exercise based on "
            "publicly available historical data. All results are historical backtest "
            "statistics and do not represent live trading performance. Historical results "
            "do not guarantee future performance. This is not investment advice. "
            "The project is not affiliated with any investment firm."
        ),
    }


# ---------------------------------------------------------------------------
# Write JSON files
# ---------------------------------------------------------------------------

def write_json(obj, filename: str) -> None:
    path = PUBLIC_DATA_DIR / filename
    with open(path, "w") as f:
        json.dump(obj, f, separators=(",", ":"))
    size_kb = path.stat().st_size / 1024
    log.info("Written: %s (%.1f KB)", filename, size_kb)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)

    data = load_all()

    write_json(gen_summary(data), "summary_stats.json")
    write_json(gen_nav_series(data), "nav_series.json")
    write_json(gen_annual_returns(data), "annual_returns.json")
    write_json(gen_monthly_returns(data), "monthly_returns.json")
    write_json(gen_rolling_metrics(data), "rolling_metrics.json")
    write_json(gen_signals(data), "signals.json")
    write_json(gen_weights(data), "weights.json")
    write_json(gen_rebalance_log(data), "rebalance_log.json")
    write_json(gen_volatility(data), "volatility.json")
    write_json(gen_meta(data), "meta.json")

    print("\n✓ JSON outputs generated in public/data/")
    print(f"  Location: {PUBLIC_DATA_DIR}")
    files = list(PUBLIC_DATA_DIR.glob("*.json"))
    for f in sorted(files):
        print(f"  {f.name:40s}  {f.stat().st_size/1024:.1f} KB")
