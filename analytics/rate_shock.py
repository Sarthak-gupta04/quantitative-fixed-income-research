"""Illustrative, duration-only parallel-yield-shift scenarios.

Issuer-published effective durations are point-in-time inputs, not historical
durations. Price impact omits convexity, income, spread changes, trading costs,
and changes in the portfolio after the shock. Nothing here enters backtesting.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from analytics.config import TICKERS

AS_OF = date(2026, 9, 25)
DURATIONS = {
    "SHY": {"years": 1.79, "source": "https://www.ishares.com/us/products/239452/ishares-1-3-year-treasury-bond-etf"},
    "IEF": {"years": 6.86, "source": "https://www.ishares.com/us/products/239456/ishares-710-year-treasury-bond-etf"},
    "TLT": {"years": 14.84, "source": "https://www.ishares.com/us/products/239454/ishares-20-year-treasury-bond-etf"},
}
SHOCKS_BPS = (-100, -50, 0, 50, 100)


def duration_impact(duration_years: float, shock_bps: int) -> float:
    """Approximate decimal price return = -effective duration × bps / 10,000."""
    return -duration_years * (shock_bps / 10_000)


def scenario(weights: dict[str, float], shock_bps: int) -> dict:
    if set(weights) != set(TICKERS) or abs(sum(weights.values()) - 1) > 1e-8:
        raise ValueError("Scenario weights must contain SHY, IEF, TLT and sum to one")
    if any(weight < 0 for weight in weights.values()):
        raise ValueError("Negative portfolio weight is not supported")
    assets = {ticker: duration_impact(DURATIONS[ticker]["years"], shock_bps) for ticker in TICKERS}
    return {
        "shock_bps": shock_bps, "asset_impact": assets,
        "portfolio_impact": sum(weights[ticker] * assets[ticker] for ticker in TICKERS),
    }


def build_rate_shock(current_weights: dict[str, float], effective_weights: dict[str, float],
                     current_signal_date: str, effective_date: str) -> dict:
    return {
        "methodology": {
            "label": "Illustrative duration-based scenario, not a historical forecast",
            "formula": "Approximate price return = -effective duration in years × parallel yield change in decimal units",
            "duration_definition": "Issuer-published effective duration",
            "duration_as_of": AS_OF.isoformat(),
            "source_retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "limitations": "Current issuer durations are applied to both model allocations. No historical duration, convexity, income, spread, tax, transaction cost, or rebalancing effect is modeled.",
        },
        "durations": DURATIONS,
        "allocations": {
            "current_model_target": {"as_of": current_signal_date, "weights": current_weights,
                                     "scenarios": [scenario(current_weights, bps) for bps in SHOCKS_BPS]},
            "latest_effective": {"as_of": effective_date, "weights": effective_weights,
                                 "scenarios": [scenario(effective_weights, bps) for bps in SHOCKS_BPS]},
        },
    }
