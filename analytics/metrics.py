"""
analytics/metrics.py
=====================
Computes all performance and risk metrics from backtest outputs.

Metrics computed:
-----------------
PERFORMANCE
  - Cumulative return
  - Annualized return (CAGR)
  - Annualized volatility
  - Sharpe ratio (Rf = 0, documented)
  - Maximum drawdown
  - Calmar ratio (CAGR / |Max Drawdown|)
  - Best single-day return
  - Worst single-day return
  - Win rate (% positive days)
  - Best calendar year return
  - Worst calendar year return

RISK
  - Rolling 20-day realized volatility
  - Rolling 252-day Sharpe ratio
  - Drawdown series (daily)
  - Value at Risk (5th percentile, historical)
  - Conditional VaR / Expected Shortfall

RELATIVE
  - Active return (strategy - benchmark)
  - Tracking error (annualized std of active return)
  - Information ratio

All formulas are documented inline.

Usage:
    python analytics/metrics.py
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
    ANNUALIZATION_FACTOR,
    DATA_PROCESSED_DIR,
    RISK_FREE_RATE_ANNUAL,
    TRANSACTION_COST_BPS,
    VOLATILITY_WINDOW,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

RF_DAILY = (1 + RISK_FREE_RATE_ANNUAL) ** (1 / ANNUALIZATION_FACTOR) - 1


# ---------------------------------------------------------------------------
# Load backtest outputs
# ---------------------------------------------------------------------------

def load_backtest() -> tuple[pd.DataFrame, pd.DataFrame]:
    nav_path = DATA_PROCESSED_DIR / "nav.csv"
    ret_path = DATA_PROCESSED_DIR / "portfolio_returns.csv"
    for p in [nav_path, ret_path]:
        if not p.exists():
            raise FileNotFoundError(
                f"Backtest output not found: {p}\n"
                "Run: python analytics/backtest.py"
            )
    nav = pd.read_csv(nav_path, index_col=0, parse_dates=True)
    rets = pd.read_csv(ret_path, index_col=0, parse_dates=True)
    return nav, rets


# ---------------------------------------------------------------------------
# Core metric functions
# ---------------------------------------------------------------------------

def cumulative_return(nav: pd.Series) -> float:
    """Cumulative return = final_NAV / initial_NAV - 1"""
    return float(nav.iloc[-1] / nav.iloc[0] - 1)


def annualized_return(nav: pd.Series) -> float:
    """
    CAGR = (final_NAV / initial_NAV)^(252/N) - 1, where N is the number of
    realized daily returns.  NAV includes one explicit base row, so N equals
    len(nav) - 1 rather than len(nav).
    """
    n = len(nav) - 1
    if n <= 0:
        return np.nan
    return float((nav.iloc[-1] / nav.iloc[0]) ** (ANNUALIZATION_FACTOR / n) - 1)


def annualized_volatility(daily_returns: pd.Series) -> float:
    """
    Ann. Vol = std(daily_returns) × sqrt(252)
    Uses sample standard deviation (ddof=1).
    """
    return float(daily_returns.std(ddof=1) * np.sqrt(ANNUALIZATION_FACTOR))


def sharpe_ratio(daily_returns: pd.Series) -> float:
    """
    Sharpe = mean(daily excess return) / std(daily excess return) × sqrt(252).
    Rf = 0% annual (documented assumption).
    """
    excess = daily_returns - RF_DAILY
    volatility = excess.std(ddof=1)
    # A mathematically constant series can retain a tiny IEEE-754 residual;
    # treat that as zero rather than reporting a meaningless near-infinite ratio.
    if np.isclose(volatility, 0.0, atol=1e-15):
        return np.nan
    return float(excess.mean() / volatility * np.sqrt(ANNUALIZATION_FACTOR))


def max_drawdown(nav: pd.Series) -> float:
    """
    MDD = min over t [ NAV(t) / max(NAV(0..t)) - 1 ]
    Returns a negative number (e.g. -0.15 = -15% drawdown).
    """
    rolling_max = nav.cummax()
    drawdown = nav / rolling_max - 1
    return float(drawdown.min())


def drawdown_series(nav: pd.Series) -> pd.Series:
    """Daily drawdown series (negative or zero)."""
    rolling_max = nav.cummax()
    return (nav / rolling_max - 1).rename("drawdown")


def calmar_ratio(nav: pd.Series) -> float:
    """Calmar = CAGR / |Max Drawdown|. Returns NaN if MDD = 0."""
    cagr = annualized_return(nav)
    mdd = max_drawdown(nav)
    if mdd == 0:
        return np.nan
    return float(cagr / abs(mdd))


def win_rate(daily_returns: pd.Series) -> float:
    """Fraction of trading days with positive return."""
    return float((daily_returns > 0).mean())


def value_at_risk(daily_returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Historical VaR at given confidence level.
    VaR_95 = 5th percentile of daily returns.
    Returns a negative number.
    """
    return float(np.percentile(daily_returns, (1 - confidence) * 100))


def conditional_var(daily_returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Expected Shortfall (CVaR) = mean of returns below VaR threshold.
    """
    var = value_at_risk(daily_returns, confidence)
    tail = daily_returns[daily_returns <= var]
    return float(tail.mean()) if len(tail) > 0 else np.nan


def rolling_volatility(daily_returns: pd.Series, window: int = VOLATILITY_WINDOW) -> pd.Series:
    """Rolling annualized volatility."""
    return (
        daily_returns.rolling(window=window, min_periods=window)
        .std(ddof=1)
        * np.sqrt(ANNUALIZATION_FACTOR)
    ).rename("rolling_vol")


def rolling_sharpe(daily_returns: pd.Series, window: int = 252) -> pd.Series:
    """Rolling Sharpe (252-day window, Rf=0)."""
    excess = daily_returns - RF_DAILY
    roll_mean = excess.rolling(window=window, min_periods=window).mean()
    roll_std = excess.rolling(window=window, min_periods=window).std(ddof=1)
    return (roll_mean / roll_std * np.sqrt(ANNUALIZATION_FACTOR)).rename("rolling_sharpe")


def annual_returns(daily_returns: pd.Series) -> pd.Series:
    """Compound annual returns from daily returns."""
    return (1 + daily_returns).groupby(daily_returns.index.year).prod() - 1


def monthly_returns(daily_returns: pd.Series) -> pd.DataFrame:
    """Monthly return matrix (rows = years, columns = months)."""
    monthly = (1 + daily_returns).groupby(
        [daily_returns.index.year, daily_returns.index.month]
    ).prod() - 1
    monthly.index = pd.MultiIndex.from_tuples(monthly.index, names=["year", "month"])
    return monthly.unstack("month")


def active_return(strategy: pd.Series, benchmark: pd.Series) -> pd.Series:
    """Daily active (excess) return: strategy - benchmark."""
    return (strategy - benchmark).rename("active_return")


def tracking_error(strategy: pd.Series, benchmark: pd.Series) -> float:
    """Annualized tracking error = std(active return) × sqrt(252)."""
    ar = active_return(strategy, benchmark)
    return float(ar.std(ddof=1) * np.sqrt(ANNUALIZATION_FACTOR))


def information_ratio(strategy: pd.Series, benchmark: pd.Series) -> float:
    """Information Ratio = Ann. Active Return / Tracking Error."""
    ar = active_return(strategy, benchmark)
    ann_ar = float(ar.mean() * ANNUALIZATION_FACTOR)
    te = tracking_error(strategy, benchmark)
    if te == 0:
        return np.nan
    return ann_ar / te


# ---------------------------------------------------------------------------
# Compile summary statistics
# ---------------------------------------------------------------------------

def compute_summary(
    nav: pd.DataFrame,
    rets: pd.DataFrame,
    label_strategy: str = "Strategy (Net)",
    label_benchmark: str = "Benchmark (AGG)",
    backtest_metadata: dict | None = None,
) -> dict:
    """
    Compute all summary statistics for strategy (net) and benchmark.
    Returns a dict suitable for JSON serialization.
    """
    # Use net strategy by default
    s_nav = nav["strategy_net"]
    b_nav = nav["benchmark"]
    s_ret = rets["strategy_net"]
    b_ret = rets["benchmark"]
    g_ret = rets["strategy_gross"]

    summary = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "start_date": str(s_ret.index[0].date()),
            "end_date": str(s_ret.index[-1].date()),
            "nav_base_date": str(nav.index[0].date()),
            "trading_days": len(s_ret),
            "risk_free_rate_annual": RISK_FREE_RATE_ANNUAL,
            "transaction_cost_bps": TRANSACTION_COST_BPS,
        },
        "strategy_net": {
            "cumulative_return": cumulative_return(s_nav),
            "annualized_return": annualized_return(s_nav),
            "annualized_volatility": annualized_volatility(s_ret),
            "sharpe_ratio": sharpe_ratio(s_ret),
            "max_drawdown": max_drawdown(s_nav),
            "calmar_ratio": calmar_ratio(s_nav),
            "win_rate": win_rate(s_ret),
            "best_day": float(s_ret.max()),
            "worst_day": float(s_ret.min()),
            "var_95": value_at_risk(s_ret, 0.95),
            "cvar_95": conditional_var(s_ret, 0.95),
            "best_year": float(annual_returns(s_ret).max()),
            "worst_year": float(annual_returns(s_ret).min()),
        },
        "strategy_gross": {
            "cumulative_return": cumulative_return(nav["strategy_gross"]),
            "annualized_return": annualized_return(nav["strategy_gross"]),
            "annualized_volatility": annualized_volatility(g_ret),
            "sharpe_ratio": sharpe_ratio(g_ret),
            "max_drawdown": max_drawdown(nav["strategy_gross"]),
        },
        "benchmark": {
            "cumulative_return": cumulative_return(b_nav),
            "annualized_return": annualized_return(b_nav),
            "annualized_volatility": annualized_volatility(b_ret),
            "sharpe_ratio": sharpe_ratio(b_ret),
            "max_drawdown": max_drawdown(b_nav),
            "calmar_ratio": calmar_ratio(b_nav),
            "win_rate": win_rate(b_ret),
            "best_day": float(b_ret.max()),
            "worst_day": float(b_ret.min()),
            "var_95": value_at_risk(b_ret, 0.95),
            "cvar_95": conditional_var(b_ret, 0.95),
            "best_year": float(annual_returns(b_ret).max()),
            "worst_year": float(annual_returns(b_ret).min()),
        },
        "relative": {
            "tracking_error": tracking_error(s_ret, b_ret),
            "information_ratio": information_ratio(s_ret, b_ret),
            "cumulative_active_return": cumulative_return(s_nav) - cumulative_return(b_nav),
            # This arithmetic annualized active return is intentionally the
            # same numerator used by the information ratio.
            "annualized_active_return": float(active_return(s_ret, b_ret).mean() * ANNUALIZATION_FACTOR),
        },
    }
    if backtest_metadata:
        summary["metadata"].update(backtest_metadata)
    return summary


def load_backtest_metadata() -> dict:
    """Load evaluation-window metadata written by the backtest when present."""
    path = DATA_PROCESSED_DIR / "backtest_metadata.json"
    if not path.exists():
        return {}
    with open(path) as file:
        return json.load(file)


# ---------------------------------------------------------------------------
# Compute rolling metrics
# ---------------------------------------------------------------------------

def compute_rolling_metrics(nav: pd.DataFrame, rets: pd.DataFrame) -> pd.DataFrame:
    """Rolling volatility and Sharpe for strategy and benchmark."""
    s_ret = rets["strategy_net"]
    b_ret = rets["benchmark"]

    result = pd.DataFrame(index=s_ret.index)
    result["strategy_rolling_vol"] = rolling_volatility(s_ret, window=20)
    result["benchmark_rolling_vol"] = rolling_volatility(b_ret, window=20)
    result["strategy_rolling_sharpe"] = rolling_sharpe(s_ret, window=252)
    result["benchmark_rolling_sharpe"] = rolling_sharpe(b_ret, window=252)
    result["strategy_drawdown"] = drawdown_series(nav["strategy_net"])
    result["benchmark_drawdown"] = drawdown_series(nav["benchmark"])

    # IEF and TLT individual rolling vol (from raw returns)
    ret_path = DATA_PROCESSED_DIR / "returns_simple.csv"
    if ret_path.exists():
        all_rets = pd.read_csv(ret_path, index_col=0, parse_dates=True)
        for ticker in ["SHY", "IEF", "TLT"]:
            if ticker in all_rets.columns:
                result[f"{ticker}_rolling_vol"] = rolling_volatility(all_rets[ticker], window=20)

    return result


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_metrics(summary: dict, rolling: pd.DataFrame, nav: pd.DataFrame, rets: pd.DataFrame) -> None:
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Summary JSON
    with open(DATA_PROCESSED_DIR / "summary_stats.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Rolling metrics CSV
    rolling.to_csv(DATA_PROCESSED_DIR / "rolling_metrics.csv", date_format="%Y-%m-%d")

    # Annual returns
    ann_strat = annual_returns(rets["strategy_net"])
    ann_bench = annual_returns(rets["benchmark"])
    ann_df = pd.DataFrame({
        "strategy_net": ann_strat,
        "benchmark": ann_bench,
    })
    ann_df.to_csv(DATA_PROCESSED_DIR / "annual_returns.csv")

    # Monthly returns (strategy net)
    monthly = monthly_returns(rets["strategy_net"])
    monthly.to_csv(DATA_PROCESSED_DIR / "monthly_returns.csv")

    log.info("Saved metrics outputs to %s", DATA_PROCESSED_DIR)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    nav, rets = load_backtest()
    summary = compute_summary(nav, rets, backtest_metadata=load_backtest_metadata())
    rolling = compute_rolling_metrics(nav, rets)
    save_metrics(summary, rolling, nav, rets)

    # Print key metrics
    s = summary["strategy_net"]
    b = summary["benchmark"]
    print("\n" + "=" * 60)
    print("BACKTEST SUMMARY STATISTICS")
    print("=" * 60)
    print(f"Period: {summary['metadata']['start_date']} → {summary['metadata']['end_date']}")
    print(f"Trading days: {summary['metadata']['trading_days']}")
    print(f"\n{'Metric':<30} {'Strategy (Net)':>18} {'Benchmark (AGG)':>18}")
    print("-" * 66)
    print(f"{'Cumulative Return':<30} {s['cumulative_return']:>17.2%} {b['cumulative_return']:>17.2%}")
    print(f"{'Annualized Return (CAGR)':<30} {s['annualized_return']:>17.2%} {b['annualized_return']:>17.2%}")
    print(f"{'Annualized Volatility':<30} {s['annualized_volatility']:>17.2%} {b['annualized_volatility']:>17.2%}")
    print(f"{'Sharpe Ratio (Rf=0)':<30} {s['sharpe_ratio']:>17.4f} {b['sharpe_ratio']:>17.4f}")
    print(f"{'Maximum Drawdown':<30} {s['max_drawdown']:>17.2%} {b['max_drawdown']:>17.2%}")
    print(f"{'Calmar Ratio':<30} {s['calmar_ratio']:>17.4f} {b['calmar_ratio']:>17.4f}")
    print(f"{'Win Rate (% positive days)':<30} {s['win_rate']:>17.2%} {b['win_rate']:>17.2%}")
    print(f"{'VaR 95% (daily)':<30} {s['var_95']:>17.4%} {b['var_95']:>17.4%}")
    print(f"{'CVaR 95% (daily)':<30} {s['cvar_95']:>17.4%} {b['cvar_95']:>17.4%}")
    print("-" * 66)
    r = summary["relative"]
    print(f"\n{'Tracking Error':<30} {r['tracking_error']:>17.2%}")
    print(f"{'Information Ratio':<30} {r['information_ratio']:>17.4f}")
    print(f"{'Active Return (ann.)':<30} {r['annualized_active_return']:>17.2%}")
    print("=" * 60)
    print("\n✓ Metrics computation complete.")
