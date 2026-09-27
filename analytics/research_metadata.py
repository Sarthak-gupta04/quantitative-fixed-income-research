"""Write reproducibility metadata and a structured, source-backed reference list."""

import hashlib
import importlib.metadata
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analytics.config import (
    ALL_TICKERS,
    DATA_RAW_DIR,
    DEFAULT_STRATEGY_PARAMETERS,
    PUBLIC_DATA_DIR,
    TICKER_NAMES,
)


def _sha256(path: Path) -> str:
    """Return a SHA-256 digest without loading the whole raw file at once."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _package_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def build_reproducibility_metadata(
    raw_dir: Path = DATA_RAW_DIR,
    now: datetime | None = None,
) -> dict:
    """Describe the saved input snapshot and the analysis environment honestly."""
    metadata_path = raw_dir / "download_meta.json"
    download_metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    raw_hashes = {
        path.name: _sha256(path)
        for path in sorted(raw_dir.glob("*.csv"))
    }
    timestamp = now or datetime.now(timezone.utc)
    parameters = DEFAULT_STRATEGY_PARAMETERS

    return {
        "analysis_timestamp_utc": timestamp.astimezone(timezone.utc).isoformat(),
        "workflow_reproducibility_note": (
            "The code, parameter settings, saved raw-data hashes, and output workflow are recorded to support reproducible analysis. "
            "Yahoo Finance data can be revised or served differently over time, so a fresh download is not guaranteed to reproduce this snapshot byte-for-byte."
        ),
        "data_source": {
            "provider": "Yahoo Finance",
            "access_library": "yfinance",
            "tickers": ALL_TICKERS,
            "ticker_names": TICKER_NAMES,
            "price_field_per_ticker": download_metadata.get("price_field_per_ticker"),
            "download_timestamp_utc": download_metadata.get("downloaded_at_utc"),
            "data_start": download_metadata.get("start_date"),
            "data_end": download_metadata.get("end_date"),
            "download_notes": download_metadata.get("notes"),
            "raw_file_sha256": raw_hashes,
        },
        "strategy_parameters": {
            "momentum_window_trading_days": parameters.momentum_window,
            "volatility_window_trading_days": parameters.volatility_window,
            "annualization_factor": parameters.annualization_factor,
            "signal_to_weight_lag_trading_days": parameters.signal_to_weight_lag,
            "transaction_cost_rate": parameters.transaction_cost_rate,
            "transaction_cost_basis_points": parameters.transaction_cost_rate * 10_000,
            "trading_notional_definition": "sum(abs(weight_new - weight_old))",
            "one_way_turnover_definition": "0.5 × trading notional",
            "risk_free_rate_annual": 0.0,
        },
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "packages": {
                package: _package_version(package)
                for package in ("numpy", "pandas", "pytest", "yfinance")
            },
        },
    }


def build_references() -> dict:
    """Return real, public sources used to identify instruments and definitions."""
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "references": [
            {
                "id": "shy_fund_page",
                "category": "Fund documentation",
                "title": "iShares 1-3 Year Treasury Bond ETF (SHY)",
                "publisher": "BlackRock / iShares",
                "url": "https://www.ishares.com/us/products/239452/ishares-1-3-year-treasury-bond-etf",
                "use": "Instrument identification and fund documentation.",
            },
            {
                "id": "ief_fund_page",
                "category": "Fund documentation",
                "title": "iShares 7-10 Year Treasury Bond ETF (IEF)",
                "publisher": "BlackRock / iShares",
                "url": "https://www.ishares.com/us/products/239456/ishares-710-year-treasury-bond-etf",
                "use": "Instrument identification and fund documentation.",
            },
            {
                "id": "tlt_fund_page",
                "category": "Fund documentation",
                "title": "iShares 20+ Year Treasury Bond ETF (TLT)",
                "publisher": "BlackRock / iShares",
                "url": "https://www.ishares.com/us/products/239454/ishares-20-year-treasury-bond-etf",
                "use": "Instrument identification and fund documentation.",
            },
            {
                "id": "agg_fund_page",
                "category": "Fund documentation",
                "title": "iShares Core U.S. Aggregate Bond ETF (AGG)",
                "publisher": "BlackRock / iShares",
                "url": "https://www.ishares.com/us/products/239458/ishares-core-us-aggregate-bond-etf",
                "use": "Benchmark instrument identification and fund documentation.",
            },
            {
                "id": "treasurydirect_bonds",
                "category": "Fixed-income concepts",
                "title": "Treasury Bonds",
                "publisher": "U.S. Department of the Treasury, TreasuryDirect",
                "url": "https://treasurydirect.services.treasury.gov/marketable-securities/treasury-bonds/",
                "use": "Background on U.S. Treasury bonds.",
            },
            {
                "id": "sec_corporate_bonds",
                "category": "Fixed-income concepts",
                "title": "Investor Bulletin: Corporate Bonds",
                "publisher": "U.S. Securities and Exchange Commission",
                "url": "https://www.sec.gov/files/ib_corporatebonds.pdf?source=syndication",
                "use": "Background on bond risks and terminology.",
            },
            {
                "id": "sharpe_1966",
                "category": "Performance and risk metrics",
                "title": "Mutual Fund Performance",
                "publisher": "William F. Sharpe, Journal of Business 39(1), 1966",
                "url": "https://doi.org/10.1086/294846",
                "use": "Historical source for the Sharpe-ratio framework.",
            },
            {
                "id": "yfinance_documentation",
                "category": "Data access",
                "title": "yfinance documentation",
                "publisher": "ranaroussi / yfinance",
                "url": "https://ranaroussi.github.io/yfinance/",
                "use": "Library used to access Yahoo Finance historical data.",
            },
        ],
    }


def save_research_metadata(metadata: dict, references: dict) -> None:
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    (PUBLIC_DATA_DIR / "reproducibility.json").write_text(json.dumps(metadata, indent=2))
    (PUBLIC_DATA_DIR / "references.json").write_text(json.dumps(references, indent=2))


if __name__ == "__main__":
    metadata = build_reproducibility_metadata()
    references = build_references()
    save_research_metadata(metadata, references)
    print("Generated reproducibility metadata and structured references.")
