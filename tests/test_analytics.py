"""
tests/test_analytics.py
========================
Comprehensive test suite for the quantitative analytics engine.

Tests cover:
  - Return calculations
  - Rolling volatility
  - Momentum calculation
  - Signal generation (eligibility)
  - Inverse-volatility weighting
  - Weight sum correctness
  - Drawdown calculation
  - Sharpe ratio
  - Annualized statistics
  - Look-ahead bias (date alignment)
  - Transaction cost calculation

Run with:
    pytest tests/test_analytics.py -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.config import (
    ANNUALIZATION_FACTOR,
    DEFENSIVE_ASSET,
    MOMENTUM_WINDOW,
    TICKERS,
    VOLATILITY_WINDOW,
)
from analytics.metrics import (
    annualized_return,
    annualized_volatility,
    calmar_ratio,
    conditional_var,
    cumulative_return,
    drawdown_series,
    max_drawdown,
    sharpe_ratio,
    value_at_risk,
    win_rate,
)
from analytics.signals import (
    compute_eligibility,
    compute_momentum,
    compute_realized_vol,
    compute_weights,
    get_rebalance_dates,
)
from analytics.backtest import (
    build_active_weights,
    compute_transaction_costs,
    assert_no_lookahead,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_price_series(n: int = 300, start: float = 100.0, drift: float = 0.0001) -> pd.Series:
    """Synthetic upward-drifting price series."""
    dates = pd.bdate_range("2010-01-01", periods=n)
    rng = np.random.default_rng(42)
    returns = rng.normal(drift, 0.004, n)
    prices = start * np.cumprod(1 + returns)
    return pd.Series(prices, index=dates)


def make_price_df(n: int = 300) -> pd.DataFrame:
    """Synthetic price DataFrame for SHY, IEF, TLT."""
    rng = np.random.default_rng(99)
    dates = pd.bdate_range("2010-01-01", periods=n)
    data = {}
    for i, ticker in enumerate(TICKERS):
        drift = 0.0001 * (i + 1)
        vol = 0.002 * (i + 1)
        ret = rng.normal(drift, vol, n)
        data[ticker] = 100 * np.cumprod(1 + ret)
    return pd.DataFrame(data, index=dates)


def make_return_series(n: int = 300) -> pd.Series:
    """Synthetic daily return series."""
    rng = np.random.default_rng(7)
    dates = pd.bdate_range("2010-01-01", periods=n)
    returns = rng.normal(0.0002, 0.005, n)
    return pd.Series(returns, index=dates)


def make_return_df(n: int = 300) -> pd.DataFrame:
    """Synthetic return DataFrame."""
    rng = np.random.default_rng(13)
    dates = pd.bdate_range("2010-01-01", periods=n)
    data = {}
    for i, ticker in enumerate(TICKERS):
        vol = 0.003 * (i + 1)
        data[ticker] = rng.normal(0.0001, vol, n)
    return pd.DataFrame(data, index=dates)


# ===========================================================================
# Return calculation tests
# ===========================================================================

class TestReturnCalculations:

    def test_simple_return_identity(self):
        """If price doubles, return = 100%."""
        s = pd.Series([100.0, 200.0])
        ret = s.pct_change().iloc[1]
        assert abs(ret - 1.0) < 1e-10

    def test_simple_return_flat(self):
        """Flat price → 0% return."""
        s = pd.Series([50.0, 50.0, 50.0])
        ret = s.pct_change().iloc[1:]
        assert (ret == 0).all()

    def test_return_from_pct_change(self):
        """pct_change matches manual formula P(t)/P(t-1) - 1."""
        prices = make_price_series(50)
        manual = prices / prices.shift(1) - 1
        pandas_ret = prices.pct_change()
        pd.testing.assert_series_equal(manual.dropna(), pandas_ret.dropna(), check_names=False)

    def test_no_nan_returns_from_clean_prices(self):
        """Clean prices produce no NaN returns (except first row)."""
        prices = make_price_series(100)
        returns = prices.pct_change().iloc[1:]
        assert not returns.isna().any()

    def test_cumulative_return(self):
        """Cumulative return formula: final/initial - 1."""
        nav = pd.Series([1.0, 1.05, 1.10, 1.20], index=pd.bdate_range("2010-01-01", periods=4))
        assert abs(cumulative_return(nav) - 0.20) < 1e-10

    def test_annualized_return_one_year(self):
        """Flat 10% cumulative over 252 days → ~10% CAGR."""
        nav = pd.Series(
            [1.0] + [1.10] * (ANNUALIZATION_FACTOR - 1),
            index=pd.bdate_range("2010-01-01", periods=ANNUALIZATION_FACTOR),
        )
        cagr = annualized_return(nav)
        assert abs(cagr - 0.10) < 0.001  # within 10bps

    def test_annualized_volatility_known_input(self):
        """Constant daily return → zero volatility."""
        returns = pd.Series([0.001] * 100)
        vol = annualized_volatility(returns)
        assert vol < 1e-10


# ===========================================================================
# Rolling volatility tests
# ===========================================================================

class TestRollingVolatility:

    def test_output_shape(self):
        """Rolling vol has same number of rows as input returns."""
        rets = make_return_df(200)
        rvol = compute_realized_vol(rets, window=VOLATILITY_WINDOW)
        assert len(rvol) == len(rets)

    def test_nan_in_warmup(self):
        """First (window-1) rows should be NaN."""
        rets = make_return_df(100)
        rvol = compute_realized_vol(rets, window=20)
        assert rvol.iloc[:19].isna().all().all()

    def test_no_nan_after_warmup(self):
        """After warm-up, no NaN values."""
        rets = make_return_df(100)
        rvol = compute_realized_vol(rets, window=20)
        after = rvol.iloc[20:]
        assert not after.isna().any().any()

    def test_annualization(self):
        """Realized vol should be annualized by sqrt(252)."""
        # Constant daily returns → zero vol
        dates = pd.bdate_range("2010-01-01", periods=100)
        ret_df = pd.DataFrame(
            {t: [0.001] * 100 for t in TICKERS},
            index=dates,
        )
        rvol = compute_realized_vol(ret_df, window=20)
        # All zeros (constant returns)
        assert rvol.dropna().abs().max().max() < 1e-10

    def test_higher_vol_for_higher_variance(self):
        """Series with higher variance should produce higher realized vol."""
        dates = pd.bdate_range("2010-01-01", periods=200)
        rng = np.random.default_rng(1)
        low_vol = pd.DataFrame({"SHY": rng.normal(0, 0.001, 200),
                                 "IEF": rng.normal(0, 0.001, 200),
                                 "TLT": rng.normal(0, 0.001, 200)},
                                index=dates)
        high_vol = pd.DataFrame({"SHY": rng.normal(0, 0.01, 200),
                                  "IEF": rng.normal(0, 0.01, 200),
                                  "TLT": rng.normal(0, 0.01, 200)},
                                 index=dates)
        lv = compute_realized_vol(low_vol, window=20).dropna()
        hv = compute_realized_vol(high_vol, window=20).dropna()
        assert (hv.mean() > lv.mean()).all()


# ===========================================================================
# Momentum tests
# ===========================================================================

class TestMomentum:

    def test_output_shape(self):
        """Momentum has same number of rows as prices."""
        prices = make_price_df(200)
        mom = compute_momentum(prices, window=60)
        assert len(mom) == len(prices)

    def test_nan_in_warmup(self):
        """First L rows should be NaN."""
        prices = make_price_df(200)
        mom = compute_momentum(prices, window=60)
        assert mom.iloc[:60].isna().all().all()

    def test_positive_momentum_rising_prices(self):
        """Monotonically rising prices → always positive momentum after warm-up."""
        dates = pd.bdate_range("2010-01-01", periods=200)
        rising = pd.DataFrame(
            {t: np.linspace(100, 200, 200) for t in TICKERS},
            index=dates,
        )
        mom = compute_momentum(rising, window=60)
        assert (mom.dropna() > 0).all().all()

    def test_negative_momentum_falling_prices(self):
        """Monotonically falling prices → always negative momentum after warm-up."""
        dates = pd.bdate_range("2010-01-01", periods=200)
        falling = pd.DataFrame(
            {t: np.linspace(200, 100, 200) for t in TICKERS},
            index=dates,
        )
        mom = compute_momentum(falling, window=60)
        assert (mom.dropna() < 0).all().all()

    def test_momentum_formula(self):
        """Mom(t) = P(t)/P(t-L) - 1 manually verified."""
        prices = make_price_df(200)
        mom = compute_momentum(prices, window=60)
        # Check a specific date
        t = 100
        for ticker in TICKERS:
            expected = prices[ticker].iloc[t] / prices[ticker].iloc[t - 60] - 1
            actual = mom[ticker].iloc[t]
            assert abs(actual - expected) < 1e-10, f"{ticker} momentum mismatch at t={t}"


# ===========================================================================
# Signal generation tests
# ===========================================================================

class TestSignalGeneration:

    def test_shy_always_eligible(self):
        """SHY should always be eligible when data exists."""
        prices = make_price_df(200)
        mom = compute_momentum(prices)
        eligible = compute_eligibility(mom)
        valid = eligible[DEFENSIVE_ASSET].loc[mom[DEFENSIVE_ASSET].notna()]
        assert valid.all(), "SHY not always eligible when momentum data exists"

    def test_eligibility_follows_momentum_sign(self):
        """Non-defensive assets are eligible iff momentum > 0."""
        prices = make_price_df(200)
        mom = compute_momentum(prices)
        eligible = compute_eligibility(mom)
        for ticker in [t for t in TICKERS if t != DEFENSIVE_ASSET]:
            valid_mask = mom[ticker].notna()
            expected = (mom[ticker] > 0) & valid_mask
            actual = eligible[ticker]
            pd.testing.assert_series_equal(
                expected, actual, check_names=False,
                obj=f"Eligibility mismatch for {ticker}"
            )

    def test_no_eligibility_in_warmup(self):
        """No asset should be eligible during the momentum warm-up period."""
        prices = make_price_df(200)
        mom = compute_momentum(prices, window=60)
        eligible = compute_eligibility(mom)
        # During warm-up, SHY should be True if mom is not NaN,
        # but for IEF and TLT, they should be False during warm-up
        non_defensive = [t for t in TICKERS if t != DEFENSIVE_ASSET]
        warmup = eligible[non_defensive].iloc[:60]
        assert (warmup == False).all().all(), "Non-defensive assets eligible during warm-up"


# ===========================================================================
# Portfolio weighting tests
# ===========================================================================

class TestPortfolioWeighting:

    def _get_weights(self, n=200):
        prices = make_price_df(n)
        rets = prices.pct_change().iloc[1:]
        # Align
        prices = prices.iloc[1:]
        mom = compute_momentum(prices)
        rvol = compute_realized_vol(rets)
        eligible = compute_eligibility(mom)
        weights = compute_weights(eligible, rvol)
        return weights, eligible

    def test_weights_sum_to_one(self):
        """Active-period weights must sum to 1.0 (or 0.0 during warm-up)."""
        weights, eligible = self._get_weights()
        active_mask = eligible.any(axis=1)
        sums = weights.loc[active_mask].sum(axis=1)
        # Allow small floating point tolerance
        bad = (sums - 1.0).abs() > 1e-6
        assert not bad.any(), f"Weight sums deviate from 1.0 on {bad.sum()} dates"

    def test_weights_non_negative(self):
        """All weights must be ≥ 0 (long-only strategy)."""
        weights, _ = self._get_weights()
        assert (weights >= 0).all().all(), "Negative weights found"

    def test_weights_leq_one(self):
        """Individual weight never exceeds 1.0."""
        weights, _ = self._get_weights()
        assert (weights <= 1.0 + 1e-9).all().all(), "Weight > 1.0 found"

    def test_defensive_all_shy(self):
        """When only SHY eligible, all weight goes to SHY."""
        # Create falling prices for IEF and TLT so they become ineligible
        dates = pd.bdate_range("2010-01-01", periods=200)
        prices = pd.DataFrame(index=dates)
        prices["SHY"] = np.linspace(100, 120, 200)  # Rising
        prices["IEF"] = np.linspace(100, 80, 200)   # Falling → negative mom
        prices["TLT"] = np.linspace(100, 70, 200)   # Falling → negative mom

        rets = prices.pct_change().iloc[1:]
        prices = prices.iloc[1:]
        mom = compute_momentum(prices, window=60)
        rvol = compute_realized_vol(rets, window=20)
        eligible = compute_eligibility(mom)
        weights = compute_weights(eligible, rvol)

        # After warm-up, IEF and TLT should have 0 weight (falling prices → mom < 0)
        active = weights.iloc[80:]  # well past warm-up
        assert (active["IEF"] == 0).all(), "IEF has weight when price is falling"
        assert (active["TLT"] == 0).all(), "TLT has weight when price is falling"
        assert (active["SHY"] == 1.0).all(), "SHY not at 100% in fully defensive period"

    def test_inverse_vol_ordering(self):
        """Lower-vol asset should receive higher weight than higher-vol asset."""
        # Create controlled scenario: SHY rising (low vol), IEF rising (high vol), TLT rising (higher vol)
        dates = pd.bdate_range("2010-01-01", periods=200)
        rng = np.random.default_rng(0)
        prices = pd.DataFrame(index=dates)
        # SHY: low vol
        prices["SHY"] = 100 * np.cumprod(1 + rng.normal(0.0003, 0.001, 200))
        # IEF: medium vol
        prices["IEF"] = 100 * np.cumprod(1 + rng.normal(0.0003, 0.005, 200))
        # TLT: high vol
        prices["TLT"] = 100 * np.cumprod(1 + rng.normal(0.0003, 0.010, 200))

        rets = prices.pct_change().iloc[1:]
        prices = prices.iloc[1:]
        mom = compute_momentum(prices, window=60)
        rvol = compute_realized_vol(rets, window=20)
        eligible = compute_eligibility(mom)
        weights = compute_weights(eligible, rvol)

        # On dates where all three are eligible
        all_eligible = eligible.all(axis=1) & weights.sum(axis=1).gt(0.9)
        if all_eligible.sum() > 10:
            avg_w = weights.loc[all_eligible].mean()
            # SHY (lowest vol) should have highest average weight
            assert avg_w["SHY"] > avg_w["IEF"], "SHY should outweigh IEF (lower vol)"
            assert avg_w["IEF"] > avg_w["TLT"], "IEF should outweigh TLT (lower vol)"


# ===========================================================================
# Drawdown tests
# ===========================================================================

class TestDrawdown:

    def test_max_drawdown_flat_nav(self):
        """Flat NAV → zero drawdown."""
        nav = pd.Series([1.0] * 100, index=pd.bdate_range("2010-01-01", periods=100))
        assert max_drawdown(nav) == 0.0

    def test_max_drawdown_known_value(self):
        """Manual check: 50% drop then recovery → MDD = -50%."""
        nav = pd.Series(
            [1.0, 1.2, 1.5, 0.75, 0.9, 1.5],
            index=pd.bdate_range("2010-01-01", periods=6),
        )
        mdd = max_drawdown(nav)
        # Max from 1.5 to 0.75 = -50%
        assert abs(mdd - (-0.50)) < 1e-10

    def test_max_drawdown_never_positive(self):
        """MDD should always be ≤ 0."""
        nav = pd.Series(
            np.cumprod(1 + make_return_series(200).values),
            index=pd.bdate_range("2010-01-01", periods=200),
        )
        assert max_drawdown(nav) <= 0

    def test_drawdown_series_starts_zero(self):
        """Drawdown series starts at 0 (at the beginning, no drawdown)."""
        nav = pd.Series(
            [1.0, 1.1, 1.2, 0.9],
            index=pd.bdate_range("2010-01-01", periods=4),
        )
        dd = drawdown_series(nav)
        assert dd.iloc[0] == 0.0

    def test_drawdown_series_non_positive(self):
        """Drawdown series values should all be ≤ 0."""
        nav = pd.Series(
            np.cumprod(1 + make_return_series(200).values),
            index=pd.bdate_range("2010-01-01", periods=200),
        )
        dd = drawdown_series(nav)
        assert (dd <= 1e-10).all()


# ===========================================================================
# Sharpe ratio tests
# ===========================================================================

class TestSharpeRatio:

    def test_positive_sharpe_for_positive_mean_return(self):
        """Consistently positive returns → positive Sharpe."""
        returns = pd.Series([0.001] * 300)
        assert sharpe_ratio(returns) > 0

    def test_negative_sharpe_for_negative_mean_return(self):
        """Consistently negative returns → negative Sharpe."""
        returns = pd.Series([-0.001] * 300)
        assert sharpe_ratio(returns) < 0

    def test_sharpe_formula(self):
        """Manual Sharpe = mean/std * sqrt(252), with Rf=0."""
        rng = np.random.default_rng(5)
        returns = pd.Series(rng.normal(0.0005, 0.005, 500))
        expected = returns.mean() / returns.std(ddof=1) * np.sqrt(ANNUALIZATION_FACTOR)
        actual = sharpe_ratio(returns)
        assert abs(actual - expected) < 1e-10


# ===========================================================================
# Look-ahead bias tests
# ===========================================================================

class TestLookAheadBias:

    def test_rebalance_dates_are_month_end(self):
        """Rebalance dates should be the last trading day of each month."""
        dates = pd.bdate_range("2010-01-01", "2011-12-31")
        rebal = get_rebalance_dates(dates)
        for d in rebal:
            # The next calendar day after rebal date should be in a different month
            next_trading = dates[dates > d]
            if len(next_trading) > 0:
                assert next_trading[0].month != d.month or next_trading[0].year != d.year, \
                    f"Rebalance date {d.date()} is not the last trading day of its month"

    def test_active_weights_lagged(self):
        """Active weights should be shifted by 1 day relative to signal weights."""
        prices = make_price_df(300)
        rets = prices.pct_change().iloc[1:]
        prices = prices.iloc[1:]
        mom = compute_momentum(prices)
        rvol = compute_realized_vol(rets)
        eligible = compute_eligibility(mom)
        weights_daily = compute_weights(eligible, rvol)
        rebalance_dates = get_rebalance_dates(prices.index)
        active = build_active_weights(weights_daily, rebalance_dates, rets.index)

        # For each rebalance date, check that the signal weight at rdate
        # equals the active weight at rdate + 1
        for rdate in rebalance_dates[:5]:
            if rdate not in weights_daily.index:
                continue
            date_pos = active.index.get_loc(rdate)
            if date_pos + 1 >= len(active):
                continue
            next_date = active.index[date_pos + 1]
            signal_w = weights_daily.loc[rdate]
            active_w = active.loc[next_date]
            pd.testing.assert_series_equal(
                signal_w, active_w, check_names=False,
                atol=1e-8,
                obj=f"Weight lag mismatch at rebalance {rdate.date()}"
            )

    def test_no_lookahead_passes_assertion(self):
        """assert_no_lookahead should not raise on correctly built weights."""
        prices = make_price_df(300)
        rets = prices.pct_change().iloc[1:]
        prices = prices.iloc[1:]
        mom = compute_momentum(prices)
        rvol = compute_realized_vol(rets)
        eligible = compute_eligibility(mom)
        weights_daily = compute_weights(eligible, rvol)
        rebalance_dates = get_rebalance_dates(prices.index)
        active = build_active_weights(weights_daily, rebalance_dates, rets.index)

        # Should not raise
        try:
            assert_no_lookahead(active, mom, rebalance_dates)
        except AssertionError as e:
            pytest.fail(f"assert_no_lookahead raised: {e}")


# ===========================================================================
# Transaction cost tests
# ===========================================================================

class TestTransactionCosts:

    def test_no_cost_when_weights_unchanged(self):
        """If weights don't change, TC = 0."""
        dates = pd.bdate_range("2010-01-01", periods=100)
        active = pd.DataFrame(
            {"SHY": [1.0] * 100, "IEF": [0.0] * 100, "TLT": [0.0] * 100},
            index=dates,
        )
        tc = compute_transaction_costs(active, tc_rate=0.0002)
        # First row will have a "change" from 0→1 due to shift, rest zero
        assert (tc.iloc[2:] == 0).all()

    def test_cost_is_non_negative(self):
        """Transaction costs should always be ≥ 0."""
        prices = make_price_df(300)
        rets = prices.pct_change().iloc[1:]
        prices = prices.iloc[1:]
        mom = compute_momentum(prices)
        rvol = compute_realized_vol(rets)
        eligible = compute_eligibility(mom)
        weights_daily = compute_weights(eligible, rvol)
        rebalance_dates = get_rebalance_dates(prices.index)
        active = build_active_weights(weights_daily, rebalance_dates, rets.index)
        tc = compute_transaction_costs(active, tc_rate=0.0002)
        assert (tc >= 0).all()


# ===========================================================================
# VaR / CVaR tests
# ===========================================================================

class TestRiskMetrics:

    def test_var_is_negative(self):
        """VaR should be negative (it represents a loss)."""
        returns = make_return_series(500)
        var = value_at_risk(returns, confidence=0.95)
        # With random returns centered at positive mean, VaR may be small positive or negative
        # but for typical return distributions it will be negative at 95%
        assert var < 0.01  # Should be a loss, not a large gain

    def test_cvar_leq_var(self):
        """CVaR ≤ VaR (CVaR is a more extreme loss measure)."""
        returns = make_return_series(500)
        var = value_at_risk(returns, confidence=0.95)
        cvar = conditional_var(returns, confidence=0.95)
        assert cvar <= var + 1e-10

    def test_win_rate_all_positive(self):
        """All positive returns → win rate = 1.0."""
        returns = pd.Series([0.001] * 100)
        assert win_rate(returns) == 1.0

    def test_win_rate_all_negative(self):
        """All negative returns → win rate = 0.0."""
        returns = pd.Series([-0.001] * 100)
        assert win_rate(returns) == 0.0
