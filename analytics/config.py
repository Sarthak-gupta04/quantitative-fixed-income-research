"""
analytics/config.py
====================
Central configuration for the quantitative fixed-income research project.
All strategy parameters, data parameters, and file paths are defined here.
Edit this file to adjust the strategy without touching analytics logic.
"""

from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Project paths (all relative to project root)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PUBLIC_DATA_DIR = PROJECT_ROOT / "public" / "data"

# ---------------------------------------------------------------------------
# Universe & benchmark
# ---------------------------------------------------------------------------
TICKERS = ["SHY", "IEF", "TLT"]          # Strategy universe
BENCHMARK = "AGG"                          # Passive benchmark
ALL_TICKERS = TICKERS + [BENCHMARK]

TICKER_NAMES = {
    "SHY": "iShares 1-3 Year Treasury",
    "IEF": "iShares 7-10 Year Treasury",
    "TLT": "iShares 20+ Year Treasury",
    "AGG": "iShares Core U.S. Agg Bond",
}

DEFENSIVE_ASSET = "SHY"

# ---------------------------------------------------------------------------
# Data parameters
# ---------------------------------------------------------------------------
# Intended start of backtest history.  The actual first date will be later
# once warm-up periods and common sample alignment are applied.
DESIRED_START = "2003-10-01"
# End date: None → use latest date available from yfinance
DESIRED_END = None

# ---------------------------------------------------------------------------
# Strategy parameters (all configurable)
# ---------------------------------------------------------------------------
MOMENTUM_WINDOW = 60       # Trading days for momentum lookback
VOLATILITY_WINDOW = 20     # Trading days for rolling realized volatility
ANNUALIZATION_FACTOR = 252 # Trading days per year (standard)

# One-way transaction cost per unit of absolute weight change (basis points)
TRANSACTION_COST_BPS = 2.0
TRANSACTION_COST_RATE = TRANSACTION_COST_BPS / 10_000  # as decimal

# Sharpe ratio risk-free rate assumption (documented: 0% for simplicity)
RISK_FREE_RATE_ANNUAL = 0.0

# ---------------------------------------------------------------------------
# Backtesting parameters
# ---------------------------------------------------------------------------
# Rebalancing: "month-end" → last trading day of each calendar month
REBALANCE_FREQUENCY = "month-end"

# Number of trading days to shift weights forward relative to signal date
# 1 = signals computed at the close of day t; weights first apply to the
# close-to-close return observed on the next available trading date.
SIGNAL_TO_WEIGHT_LAG = 1

# Annualized volatility at or below this threshold is treated as not
# estimable for inverse-volatility sizing.  It avoids manufacturing an
# effectively infinite inverse-volatility weight from a zero-variance window.
MIN_REALIZED_VOLATILITY = 1e-6


@dataclass(frozen=True)
class StrategyParameters:
    """Inputs for one reproducible strategy run.

    The analytics engine accepts this object so a later sensitivity analysis
    can run the identical implementation for pre-specified parameter sets.
    It does not select or optimise a parameter combination.
    """

    momentum_window: int = MOMENTUM_WINDOW
    volatility_window: int = VOLATILITY_WINDOW
    annualization_factor: int = ANNUALIZATION_FACTOR
    transaction_cost_rate: float = TRANSACTION_COST_RATE
    signal_to_weight_lag: int = SIGNAL_TO_WEIGHT_LAG
    min_realized_volatility: float = MIN_REALIZED_VOLATILITY


DEFAULT_STRATEGY_PARAMETERS = StrategyParameters()

# Architecture-only grid for a future descriptive sensitivity report.  These
# combinations are deliberately pre-specified and are not used to choose a
# "best" strategy configuration.
SENSITIVITY_PARAMETER_GRID = tuple(
    StrategyParameters(momentum_window=momentum, volatility_window=volatility)
    for momentum in (40, 60, 90)
    for volatility in (20, 40)
)

# ---------------------------------------------------------------------------
# Validation thresholds
# ---------------------------------------------------------------------------
MAX_CONSECUTIVE_NAN = 5   # Fail if any ticker has more than this many consecutive NaN prices
MIN_COVERAGE_FRACTION = 0.95  # Require at least 95% of expected trading days
