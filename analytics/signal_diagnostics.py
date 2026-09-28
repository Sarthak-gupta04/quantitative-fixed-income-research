"""Deterministic, auditable explanations of observed monthly weight changes."""

from __future__ import annotations

import pandas as pd

from analytics.backtest import BacktestRun
from analytics.config import DEFENSIVE_ASSET, TICKERS
from analytics.signals import compute_eligibility

MEANINGFUL_NOTIONAL = 0.01  # 1% of portfolio gross traded notional


def explain_change(previous: dict, current: dict) -> list[str]:
    """Emit only predicates provable from two dated signal snapshots."""
    messages = []
    for ticker in TICKERS:
        if ticker == DEFENSIVE_ASSET:
            continue
        before, after = previous["eligibility"][ticker], current["eligibility"][ticker]
        if before and not after:
            messages.append(f"{ticker} lost momentum eligibility; its target weight fell to zero.")
        elif not before and after:
            messages.append(f"{ticker} gained momentum eligibility and entered the target allocation.")
        elif before and after:
            prev_vol, next_vol = previous["volatility"][ticker], current["volatility"][ticker]
            prev_w, next_w = previous["weights"][ticker], current["weights"][ticker]
            if next_vol > prev_vol + 1e-10 and next_w < prev_w - 1e-4:
                messages.append(f"{ticker} remained eligible; its realized volatility rose while its target weight fell.")
            elif next_vol < prev_vol - 1e-10 and next_w > prev_w + 1e-4:
                messages.append(f"{ticker} remained eligible; its realized volatility fell while its target weight rose.")
    if current["weights"][DEFENSIVE_ASSET] > previous["weights"][DEFENSIVE_ASSET] + 1e-4:
        messages.append("Observed defensive SHY target weight increased.")
    if not messages:
        messages.append("Target weights changed under the same fixed eligibility and inverse-volatility rules.")
    return messages


def _snapshot(run: BacktestRun, eligibility: pd.DataFrame, date: pd.Timestamp) -> dict:
    return {
        "momentum": {ticker: float(run.momentum.loc[date, ticker]) for ticker in TICKERS},
        "volatility": {ticker: float(run.realized_volatility.loc[date, ticker]) for ticker in TICKERS},
        "eligibility": {ticker: bool(eligibility.loc[date, ticker]) for ticker in TICKERS},
        "weights": {ticker: float(run.target_weights.loc[date, ticker]) for ticker in TICKERS},
    }


def build_decision_records(run: BacktestRun) -> dict:
    eligibility = compute_eligibility(run.momentum)
    audit = run.rebalance_audit.sort_values("effective_date").reset_index(drop=True)
    records = []
    for index, row in audit.iterrows():
        signal_date = pd.Timestamp(row["signal_date"])
        current = _snapshot(run, eligibility, signal_date)
        if index == 0:
            previous = {"weights": {ticker: 0.0 for ticker in TICKERS},
                        "eligibility": {ticker: False for ticker in TICKERS},
                        "momentum": {}, "volatility": {}}
            explanations = ["Initial observable allocation after indicator warm-up."]
            previous_signal_date = None
        else:
            previous_signal_date = pd.Timestamp(audit.loc[index - 1, "signal_date"])
            previous = _snapshot(run, eligibility, previous_signal_date)
            explanations = explain_change(previous, current)
        notional = float(row["trading_notional"])
        if notional < MEANINGFUL_NOTIONAL:
            continue
        records.append({
            "signal_date": signal_date.date().isoformat(),
            "previous_signal_date": previous_signal_date.date().isoformat() if previous_signal_date is not None else None,
            "effective_date": pd.Timestamp(row["effective_date"]).date().isoformat(),
            "previous_allocation": previous["weights"],
            "new_allocation": current["weights"],
            "momentum": current["momentum"],
            "eligibility": current["eligibility"],
            "realized_volatility": current["volatility"],
            "previous_momentum": previous["momentum"],
            "previous_eligibility": previous["eligibility"],
            "previous_realized_volatility": previous["volatility"],
            "weight_change": {ticker: current["weights"][ticker] - previous["weights"][ticker] for ticker in TICKERS},
            "trading_notional": notional,
            "transaction_cost": float(row["transaction_cost"]),
            "explanations": explanations,
        })
    return {
        "methodology": {"meaningful_change_gross_notional": MEANINGFUL_NOTIONAL,
                        "note": "Only observable effective rebalances with at least 1% gross traded notional are displayed. Explanations are deterministic descriptions of signal and weight changes, not causal attributions."},
        "total_observable_rebalances": len(audit), "records": records,
    }
