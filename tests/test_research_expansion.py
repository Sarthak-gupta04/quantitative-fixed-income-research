"""Regression tests for supplemental research layers (no live network needed)."""

from types import SimpleNamespace

import pandas as pd
import pytest

from analytics.failure_modes import drawdown_events, ranked_period_returns
from analytics.generate_outputs import gen_rebalance_log, load_rebalance_log
from analytics.holdout_analysis import evaluate_holdout
from analytics.rate_shock import duration_impact, scenario
from analytics.signal_diagnostics import build_decision_records, explain_change
from analytics.yield_curve import align_curve_and_allocation, calculate_curve, parse_treasury_xml


def test_rebalance_export_preserves_signal_date(tmp_path):
    source = tmp_path / "rebalance_log.csv"
    source.write_text("signal_date,effective_date,weight_SHY\n2020-01-31,2020-02-03,1.0\n")
    records = gen_rebalance_log({"rebalance_log": load_rebalance_log(source)})
    assert records[0]["signal_date"] == "2020-01-31"
    assert records[0]["effective_date"] == "2020-02-03"


def test_curve_conventions_and_daily_change():
    yields = pd.DataFrame({"two_year": [3.0, 3.1], "five_year": [3.5, 3.6],
                           "ten_year": [4.0, 4.2]}, index=pd.to_datetime(["2020-01-02", "2020-01-03"]))
    curve = calculate_curve(yields)
    assert curve.iloc[0]["level"] == 4.0
    assert curve.iloc[0]["slope_2s10s"] == 1.0
    assert curve.iloc[0]["slope_5s10s"] == 0.5
    assert curve.iloc[0]["curvature"] == 0.0
    assert curve.iloc[1]["change_slope_2s10s"] == pytest.approx(0.1)


def test_curve_drops_missing_tenors_without_filling_and_aligns_exact_dates():
    index = pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"])
    yields = pd.DataFrame({"two_year": [2.0, None, 2.1], "five_year": [3.0, 3.1, 3.2],
                           "ten_year": [4.0, 4.1, 4.2]}, index=index)
    curve = calculate_curve(yields)
    assert list(curve.index) == [index[0], index[2]]
    weights = pd.DataFrame({"SHY": [1, 0, 1], "IEF": [0, 1, 0], "TLT": [0, 0, 0]}, index=index)
    aligned = align_curve_and_allocation(curve, weights)
    assert list(aligned.index) == [index[2]]
    assert aligned.iloc[0]["SHY"] == 1


def test_treasury_xml_keeps_missing_tenor_as_nan():
    xml = b'''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"><entry><content><m:properties><d:NEW_DATE>2020-01-02T00:00:00</d:NEW_DATE><d:BC_2YEAR>1.5</d:BC_2YEAR><d:BC_5YEAR></d:BC_5YEAR><d:BC_10YEAR>2.0</d:BC_10YEAR></m:properties></content></entry></feed>'''
    frame = parse_treasury_xml(xml)
    assert frame.iloc[0]["two_year"] == 1.5
    assert pd.isna(frame.iloc[0]["five_year"])
    assert calculate_curve(frame).empty


def _sample_run():
    dates = pd.to_datetime(["2019-12-30", "2019-12-31", "2020-01-02", "2020-01-03"])
    returns = pd.Series([0.01, -0.01, 0.02, -0.01], index=dates, name="strategy_net")
    benchmark = pd.Series([0.005, 0.005, -0.005, 0.005], index=dates, name="benchmark")
    audit = pd.DataFrame({"signal_date": pd.to_datetime(["2019-12-27", "2019-12-31"]),
                          "effective_date": pd.to_datetime(["2019-12-30", "2020-01-02"]),
                          "trading_notional": [1.0, 0.2], "transaction_cost": [0.0002, 0.00004]})
    return SimpleNamespace(
        first_investable_date=dates[0], nav_base_date=pd.Timestamp("2019-12-27"),
        net_daily_returns=returns, gross_daily_returns=returns + 0.0001,
        benchmark_daily_returns=benchmark,
        evaluation_weights=pd.DataFrame({"SHY": [1, 0.9, 0.8, 0.8],
                                         "IEF": [0, 0.1, 0.2, 0.2], "TLT": [0, 0, 0, 0]}, index=dates),
        trading_notional=pd.Series([1.0, 0, 0.2, 0], index=dates),
        one_way_turnover=pd.Series([0.5, 0, 0.1, 0], index=dates),
        transaction_costs=pd.Series([0.0002, 0, 0.00004, 0], index=dates),
        rebalance_audit=audit,
    )


def test_holdout_split_keeps_common_investable_dates_and_fixed_parameters():
    result = evaluate_holdout(_sample_run())
    assert result["periods"]["development"]["end_date"] == "2019-12-31"
    assert result["periods"]["holdout"]["start_date"] == "2020-01-02"
    assert result["periods"]["holdout"]["nav_base_date"] == "2019-12-31"
    assert result["periods"]["holdout"]["trading_days"] == 2
    assert result["methodology"]["fixed_parameters"]["momentum_window"] == 60
    assert result["methodology"]["fixed_parameters"]["volatility_window"] == 20
    assert result["periods"]["holdout"]["strategy"]["one_way_turnover"] == pytest.approx(0.1)
    assert result["periods"]["holdout"]["benchmark"]["one_way_turnover"] == 0


def test_holdout_refuses_a_missing_period():
    run = _sample_run()
    run.net_daily_returns = run.net_daily_returns.loc[:"2019-12-31"]
    with pytest.raises(ValueError, match="Both development and holdout"):
        evaluate_holdout(run)


@pytest.mark.parametrize("bps,expected", [(-100, 0.0686), (-50, 0.0343), (0, 0), (50, -0.0343), (100, -0.0686)])
def test_duration_basis_point_conversion(bps, expected):
    assert duration_impact(6.86, bps) == pytest.approx(expected)


def test_rate_shock_portfolio_weighting():
    weights = {"SHY": 0.5, "IEF": 0.3, "TLT": 0.2}
    result = scenario(weights, 100)
    assert result["portfolio_impact"] == pytest.approx(-0.5 * 0.0179 - 0.3 * 0.0686 - 0.2 * 0.1484)
    with pytest.raises(ValueError):
        scenario({"SHY": 1, "IEF": 1, "TLT": 0}, 100)


def test_explanations_only_when_eligibility_or_volatility_predicate_holds():
    previous = {"eligibility": {"IEF": True, "TLT": False},
                "weights": {"SHY": 0.7, "IEF": 0.3, "TLT": 0},
                "volatility": {"IEF": 0.05, "TLT": 0.10}}
    current = {"eligibility": {"IEF": False, "TLT": True},
               "weights": {"SHY": 0.8, "IEF": 0, "TLT": 0.2},
               "volatility": {"IEF": 0.06, "TLT": 0.09}}
    explanations = explain_change(previous, current)
    assert any("IEF lost momentum eligibility" in text for text in explanations)
    assert any("TLT gained momentum eligibility" in text for text in explanations)
    assert not any("remained eligible" in text for text in explanations)


def test_decision_record_uses_actual_signal_and_effective_dates():
    dates = pd.to_datetime(["2019-12-27", "2019-12-31"])
    columns = ["SHY", "IEF", "TLT"]
    run = SimpleNamespace(
        momentum=pd.DataFrame([[0.01, 0.02, -0.01], [0.01, -0.01, 0.01]], index=dates, columns=columns),
        realized_volatility=pd.DataFrame([[0.02, 0.04, 0.08], [0.02, 0.05, 0.08]], index=dates, columns=columns),
        target_weights=pd.DataFrame([[0.7, 0.3, 0], [0.8, 0, 0.2]], index=dates, columns=columns),
        rebalance_audit=pd.DataFrame({"signal_date": dates, "effective_date": pd.to_datetime(["2019-12-30", "2020-01-02"]),
                                      "trading_notional": [1.0, 0.4], "transaction_cost": [0.0002, 0.00008]}),
    )
    output = build_decision_records(run)
    second = output["records"][1]
    assert second["signal_date"] == "2019-12-31"
    assert second["effective_date"] == "2020-01-02"
    assert second["previous_allocation"]["IEF"] == 0.3
    assert second["new_allocation"]["IEF"] == 0
    assert second["weight_change"]["IEF"] == pytest.approx(-0.3)


def test_drawdown_peak_trough_recovery_and_open_episode():
    dates = pd.date_range("2020-01-01", periods=7)
    nav = pd.Series([1.0, 1.1, 1.0, 0.9, 1.05, 1.1, 1.0], index=dates)
    events = drawdown_events(nav)
    assert events[0]["start_date"] == "2020-01-02"
    assert events[0]["trough_date"] == "2020-01-04"
    assert events[0]["recovery_date"] == "2020-01-06"
    assert events[0]["drawdown"] == pytest.approx(0.9 / 1.1 - 1)
    assert events[1]["recovery_date"] is None


def test_worst_months_use_compounding_and_rank_negative_period():
    dates = pd.to_datetime(["2020-01-02", "2020-01-03", "2020-02-03"])
    strategy = pd.Series([0.1, -0.1, -0.02], index=dates)
    benchmark = pd.Series([0, 0, 0.01], index=dates)
    periods = ranked_period_returns(strategy, benchmark, "M")
    assert periods[0]["period"] == "2020-02"
    assert periods[1]["strategy_return"] == pytest.approx(-0.01)
