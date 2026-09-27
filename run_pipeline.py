"""
run_pipeline.py
================
Master script to run the full analytics pipeline in order.

Usage:
    python run_pipeline.py

Steps:
    1. Download raw data (yfinance)
    2. Clean and validate data
    3. Compute signals (momentum, volatility, weights)
    4. Run backtest
    5. Compute metrics
    6. Generate JSON outputs for frontend

All outputs are written to data/processed/ and public/data/.
"""

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = [
    ROOT / "analytics" / "download_data.py",
    ROOT / "analytics" / "clean_data.py",
    ROOT / "analytics" / "signals.py",
    ROOT / "analytics" / "backtest.py",
    ROOT / "analytics" / "metrics.py",
    ROOT / "analytics" / "generate_outputs.py",
]

def run_step(script: Path) -> None:
    print(f"\n{'='*60}")
    print(f"Running: {script.name}")
    print('='*60)
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=False,
    )
    if result.returncode != 0:
        print(f"\n✗ FAILED: {script.name} (exit code {result.returncode})")
        sys.exit(result.returncode)
    print(f"\n✓ Completed: {script.name}")

if __name__ == "__main__":
    print("Quantitative Fixed-Income Research — Analytics Pipeline")
    print(f"Project root: {ROOT}")
    for script in SCRIPTS:
        run_step(script)
    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)
    print("JSON outputs written to: public/data/")
    print("Run 'npm run dev' to start the dashboard.")
