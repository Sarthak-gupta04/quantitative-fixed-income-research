"""Tests for descriptive research outputs built on the validated backtest engine."""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.backtest import evaluate_from_date, run_backtest
from analytics.config import DEFAULT_STRATEGY_PARAMETERS, SENSITIVITY_PARAMETER_GRID, TICKERS
from analytics.regime_analysis import calculate_period_metrics, select_periods
from analytics.research_metadata import build_references, build_reproducibility_metadata
from analytics.researcher_view import build_researcher_state
import analytics.sensitivity as sensitivity_module
from analytics.sensitivity import configuration_id, run_sensitivity, save_sensitivity


def synthetic_prices(rows: int = 360) -> pd.DataFrame:
    """Deterministic, non-zero-volatility universe including the benchmark."""
    dates = pd.bdate_range("2012-01-02", periods=rows)
    rng = np.random.default_rng(124)
    specifications = {
        "SHY": (0.00008, 0.0007),
        "IEF": (0.00022, 0.0025),
        "TLT": (0.00015, 0.0045),
        "AGG": (0.00014, 0.0018),
    }
    return pd.DataFrame(
        {
            ticker: 100.0 * np.cumprod(1.0 + rng.normal(drift, volatility, rows))
            for ticker, (drift, volatility) in specifications.items()
        },
        index=dates,
    )


class TestSensitivityAnalysis:
    def test_all_six_prespecified_configurations_share_one_window(self):
        prices = synthetic_prices()
        result = run_sensitivity(prices, prices.pct_change().dropna())

        assert len(result["results"]) == 6
        assert {row["configuration_id"] for row in result["results"]} == {
            f"mom_{momentum}_vol_{volatility}"
            for momentum in (40, 60, 90)
            for volatility in (20, 40)
        }
        assert len({row["evaluation_start_date"] for row in result["results"]}) == 1
        assert len({row["evaluation_end_date"] for row in result["results"]}) == 1
        assert sum(row["is_baseline"] for row in result["results"]) == 1

    def test_baseline_identification_and_shared_engine_consistency(self):
        prices = synthetic_prices()
        returns = prices.pct_change().dropna()
        result = run_sensitivity(prices, returns)
        baseline_row = next(row for row in result["results"] if row["is_baseline"])

        assert baseline_row["configuration_id"] == configuration_id(DEFAULT_STRATEGY_PARAMETERS)
        baseline_run = run_backtest(prices, returns, DEFAULT_STRATEGY_PARAMETERS)
        common_start = pd.Timestamp(result["methodology"]["common_evaluation_start_date"])
        expected = evaluate_from_date(baseline_run, common_start)
        assert np.isclose(baseline_row["metrics"]["cumulative_return"], expected.net_nav.iloc[-1] - 1.0)
        assert np.isclose(
            baseline_row["metrics"]["total_one_way_turnover"],
            0.5 * baseline_row["metrics"]["total_trading_notional"],
        )
        assert DEFAULT_STRATEGY_PARAMETERS in SENSITIVITY_PARAMETER_GRID

    def test_saved_sensitivity_outputs_preserve_engine_results(self, tmp_path, monkeypatch):
        prices = synthetic_prices()
        result = run_sensitivity(prices, prices.pct_change().dropna())
        monkeypatch.setattr(sensitivity_module, "PUBLIC_DATA_DIR", tmp_path / "public")
        monkeypatch.setattr(sensitivity_module, "DATA_PROCESSED_DIR", tmp_path / "processed")
        save_sensitivity(result)

        saved_json = json.loads((tmp_path / "public" / "sensitivity.json").read_text())
        saved_csv = pd.read_csv(tmp_path / "processed" / "sensitivity.csv")
        assert saved_json["results"] == result["results"]
        assert saved_csv["configuration_id"].tolist() == [row["configuration_id"] for row in result["results"]]
        assert saved_csv["is_baseline"].sum() == 1


class TestRegimeAnalysis:
    def test_select_periods_requires_full_calendar_coverage(self):
        periods = select_periods(pd.Timestamp("2004-01-02"), pd.Timestamp("2026-09-25"))
        assert [period["id"] for period in periods] == ["2007_2009", "2020", "2022", "2025"]
        assert all("period" in period["label"] for period in periods)

    def test_period_metrics_use_compounded_returns_and_realised_weights(self):
        dates = pd.bdate_range("2022-01-03", periods=5)
        returns = pd.DataFrame({
            "strategy_net": [0.01, -0.02, 0.03, 0.0, 0.01],
            "benchmark": [0.0, 0.01, -0.01, 0.0, 0.0],
        }, index=dates)
        weights = pd.DataFrame({
            "SHY": [1.0, 1.0, 0.5, 0.5, 0.5],
            "IEF": [0.0, 0.0, 0.5, 0.5, 0.5],
            "TLT": [0.0, 0.0, 0.0, 0.0, 0.0],
        }, index=dates)
        audit = pd.DataFrame({"effective_date": [dates[2], dates[4]]})
        result = calculate_period_metrics(
            {"id": "test", "label": "test period", "start_date": "2022-01-01", "end_date": "2022-12-31"},
            returns,
            weights,
            audit,
        )

        assert np.isclose(result["strategy_return"], np.prod(1 + returns["strategy_net"]) - 1)
        assert result["number_of_rebalances"] == 2
        assert np.isclose(result["average_allocation"]["SHY"], 0.7)
        assert result["defensive_shy_allocation"]["fully_defensive_trading_days"] == 2


class TestResearcherAndMetadataOutputs:
    def test_researcher_state_is_factual_and_uses_latest_rows(self):
        dates = pd.bdate_range("2024-01-02", periods=3)
        signals = pd.DataFrame({
            "momentum_SHY": [0.01, 0.02, 0.03], "momentum_IEF": [0.0, 0.01, 0.02], "momentum_TLT": [0.0, -0.01, 0.01],
            "rvol_SHY": [0.01, 0.01, 0.01], "rvol_IEF": [0.02, 0.02, 0.02], "rvol_TLT": [0.03, 0.03, 0.03],
            "weight_SHY": [1.0, 0.5, 0.3], "weight_IEF": [0.0, 0.5, 0.4], "weight_TLT": [0.0, 0.0, 0.3],
            "eligible_SHY": [True, True, True], "eligible_IEF": [False, True, True], "eligible_TLT": [False, False, True],
            "is_defensive": [True, False, False],
        }, index=dates)
        active = pd.DataFrame({"SHY": [1.0, 0.5, 0.3], "IEF": [0.0, 0.5, 0.4], "TLT": [0.0, 0.0, 0.3]}, index=dates)
        audit = pd.DataFrame({
            "signal_date": [dates[1]], "effective_date": [dates[2]],
            "weight_SHY": [0.3], "weight_IEF": [0.4], "weight_TLT": [0.3],
            "trading_notional": [0.4], "one_way_turnover": [0.2], "transaction_cost": [0.00008],
        })
        rolling = pd.DataFrame({
            "strategy_rolling_vol": [np.nan, 0.04, 0.05], "benchmark_rolling_vol": [np.nan, 0.06, 0.07],
            "strategy_drawdown": [0.0, -0.01, -0.02], "benchmark_drawdown": [0.0, -0.02, -0.03],
        }, index=dates)
        result = build_researcher_state(signals, active, audit, rolling)

        assert result["latest_signal"]["signal_date"] == str(dates[-1].date())
        assert result["latest_effective_allocation"]["weights"]["TLT"] == 0.3
        assert result["methodology"]["not_investment_advice"] is True
        assert "recommendation" in result["summary"].lower()

    def test_metadata_hashes_and_references_are_structured(self, tmp_path):
        raw_file = tmp_path / "prices_raw.csv"
        raw_file.write_text("date,SHY\n2024-01-02,100\n")
        (tmp_path / "download_meta.json").write_text(
            '{"downloaded_at_utc":"2024-01-03T00:00:00+00:00","price_field_per_ticker":{"SHY":"Adj Close"},"start_date":"2024-01-02","end_date":"2024-01-02"}'
        )
        result = build_reproducibility_metadata(tmp_path, datetime(2024, 1, 4, tzinfo=timezone.utc))
        references = build_references()

        assert result["data_source"]["raw_file_sha256"]["prices_raw.csv"] == hashlib.sha256(raw_file.read_bytes()).hexdigest()
        assert result["analysis_timestamp_utc"] == "2024-01-04T00:00:00+00:00"
        assert "not guaranteed" in result["workflow_reproducibility_note"]
        assert {"shy_fund_page", "ief_fund_page", "tlt_fund_page", "agg_fund_page"}.issubset(
            {reference["id"] for reference in references["references"]}
        )
        assert all(reference["url"].startswith("https://") for reference in references["references"])
