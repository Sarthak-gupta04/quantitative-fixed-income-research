"""Generate a factual current-state summary from calculated dashboard data."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.config import DATA_PROCESSED_DIR, PUBLIC_DATA_DIR, TICKERS


def _float_dict(row: pd.Series, prefix: str = "") -> dict[str, float | None]:
    result = {}
    for ticker in TICKERS:
        key = f"{prefix}{ticker}"
        value = row.get(key)
        result[ticker] = None if pd.isna(value) else float(value)
    return result


def build_researcher_state(
    signals: pd.DataFrame,
    active_weights: pd.DataFrame,
    rebalance_audit: pd.DataFrame,
    rolling_metrics: pd.DataFrame,
) -> dict:
    """Build a non-predictive description of the latest calculated state."""
    latest_signal = signals.dropna(subset=["momentum_SHY", "rvol_SHY"]).iloc[-1]
    latest_allocation = active_weights.iloc[-1]
    latest_risk = rolling_metrics.dropna(subset=["strategy_rolling_vol", "strategy_drawdown"]).iloc[-1]
    latest_rebalance = rebalance_audit.iloc[-1] if not rebalance_audit.empty else None

    target_weights = _float_dict(latest_signal, "weight_")
    effective_weights = _float_dict(latest_allocation)
    defensive = bool(latest_signal.get("is_defensive", False))
    signal_date = pd.Timestamp(latest_signal.name)
    allocation_date = pd.Timestamp(active_weights.index[-1])
    summary = (
        f"As of the latest target signal ({signal_date.date()}), IEF and TLT were "
        f"{'both ineligible' if defensive else 'not both excluded'} under the documented momentum rule. "
        f"The latest available effective allocation is dated {allocation_date.date()}. "
        "This describes calculated historical inputs and portfolio state only; it is not an investment recommendation or forecast."
    )

    return {
        "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "scope": "Factual summary of the latest saved signal, effective allocation, and realised risk measurements.",
            "not_investment_advice": True,
            "no_forecast": True,
        },
        "latest_signal": {
            "signal_date": str(signal_date.date()),
            "momentum": _float_dict(latest_signal, "momentum_"),
            "realized_volatility": _float_dict(latest_signal, "rvol_"),
            "target_weights": target_weights,
            "eligibility": {ticker: bool(latest_signal[f"eligible_{ticker}"]) for ticker in TICKERS},
            "is_fully_defensive": defensive,
        },
        "latest_effective_allocation": {
            "date": str(allocation_date.date()),
            "weights": effective_weights,
        },
        "latest_observable_rebalance": None if latest_rebalance is None else {
            "signal_date": str(pd.Timestamp(latest_rebalance["signal_date"]).date()),
            "effective_date": str(pd.Timestamp(latest_rebalance["effective_date"]).date()),
            "weights": _float_dict(latest_rebalance, "weight_"),
            "trading_notional": float(latest_rebalance["trading_notional"]),
            "one_way_turnover": float(latest_rebalance["one_way_turnover"]),
            "transaction_cost": float(latest_rebalance["transaction_cost"]),
        },
        "recent_realized_risk": {
            "date": str(pd.Timestamp(latest_risk.name).date()),
            "strategy_rolling_volatility": float(latest_risk["strategy_rolling_vol"]),
            "benchmark_rolling_volatility": float(latest_risk["benchmark_rolling_vol"]),
            "strategy_drawdown": float(latest_risk["strategy_drawdown"]),
            "benchmark_drawdown": float(latest_risk["benchmark_drawdown"]),
        },
        "summary": summary,
    }


def load_researcher_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    signals = pd.read_csv(DATA_PROCESSED_DIR / "monthly_signals.csv", index_col=0, parse_dates=True)
    active_weights = pd.read_csv(DATA_PROCESSED_DIR / "active_weights.csv", index_col=0, parse_dates=True)
    audit = pd.read_csv(
        DATA_PROCESSED_DIR / "rebalance_log.csv",
        parse_dates=["signal_date", "effective_date", "first_return_date", "next_signal_date"],
    )
    rolling = pd.read_csv(DATA_PROCESSED_DIR / "rolling_metrics.csv", index_col=0, parse_dates=True)
    return signals, active_weights, audit, rolling


def save_researcher_state(result: dict) -> None:
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PUBLIC_DATA_DIR / "researcher_view.json", "w") as file:
        json.dump(result, file, indent=2)


if __name__ == "__main__":
    inputs = load_researcher_inputs()
    result = build_researcher_state(*inputs)
    save_researcher_state(result)
    print("Generated factual researcher-state output.")
