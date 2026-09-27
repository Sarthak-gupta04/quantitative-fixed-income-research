# Quantitative Fixed-Income Strategy & Risk Dashboard

An educational quantitative investment research project demonstrating a rules-based, momentum-driven fixed-income ETF strategy with full backtesting, risk analysis, and an interactive dashboard.

> **Disclaimer:** This is an educational project based on public historical data. All results are historical backtest statistics. This is not investment advice. Not affiliated with any investment firm. Historical results do not guarantee future performance.

---

## Project Overview

This project implements and backtests a quantitative fixed-income strategy across three U.S. Treasury ETFs (SHY, IEF, TLT), benchmarked against the U.S. Aggregate Bond Index (AGG). The project demonstrates:

- Rules-based signal generation (60-day momentum)
- Volatility-aware position sizing (inverse realized volatility)
- Monthly portfolio rebalancing with explicit look-ahead bias prevention
- Transaction cost modelling (gross vs. net returns)
- Standard risk metrics (Sharpe, MDD, VaR, CVaR, Tracking Error, IR)
- Interactive visualization built on real calculated outputs (no fabricated numbers)

---

## Research Question

*Does a simple momentum-based strategy across U.S. Treasury ETFs, sized by inverse realized volatility, deliver a materially different risk/return profile compared to a passive aggregate bond benchmark?*

Answer (honest): The strategy underperforms the AGG benchmark in absolute return (~2.24% CAGR vs. ~2.93% CAGR) but achieves meaningfully lower volatility (2.53% vs. 5.17%) and maximum drawdown (7.08% vs. 18.43%), resulting in a higher Sharpe ratio (0.89 vs. 0.58). The information ratio is negative, indicating active returns are not sufficient to justify the tracking error.

---

## Investment Universe

| Ticker | Name | Role |
|--------|------|------|
| SHY | iShares 1–3 Year Treasury Bond ETF | Short duration / Defensive asset |
| IEF | iShares 7–10 Year Treasury Bond ETF | Intermediate duration |
| TLT | iShares 20+ Year Treasury Bond ETF | Long duration |
| AGG | iShares Core U.S. Aggregate Bond ETF | Passive benchmark |

---

## Data Sources

- **Source:** Yahoo Finance via `yfinance` (Python)
- **Price field:** Adjusted Close (`Adj Close`) — total-return proxy (dividends reinvested, splits adjusted)
- **Period:** 2003-10-01 → latest available date
- **Frequency:** Daily

---

## Strategy Methodology

### Momentum Signal (60-day)
```
Mom(i, t) = P(i, t) / P(i, t - 60) - 1
Eligible(i, t) = 1 if Mom(i, t) > 0, else 0
SHY is always eligible (defensive asset)
```

### Realized Volatility (20-day)
```
RVol(i, t) = std(r(i, t-19..t)) × sqrt(252)
```

### Inverse-Volatility Weights
```
InvVol(i, t) = 1 / RVol(i, t)
w(i, t) = InvVol(i, t) / sum(InvVol(j, t))  for j in eligible set
```

### Defensive Rule
If neither IEF nor TLT is eligible → 100% SHY

### Rebalancing
Monthly (last trading day of each month)

### Look-Ahead Bias Prevention
Signals computed at close of rebalance date t → weights effective at close of t+1 (1-day lag). Programmatic assertion `assert_no_lookahead()` validates date alignment after every run.

### Transaction Costs
2 basis points (0.0002) one-way per unit of absolute weight change. Both gross and net results reported.

---

## Backtest Results (2003-10-02 → 2026-09-25)

| Metric | Strategy (Net) | Benchmark (AGG) |
|--------|----------------|-----------------|
| Cumulative Return | ~66.4% | ~93.9% |
| Ann. Return (CAGR) | ~2.24% | ~2.93% |
| Ann. Volatility | ~2.53% | ~5.17% |
| Sharpe Ratio (Rf=0) | ~0.89 | ~0.58 |
| Max Drawdown | ~-7.1% | ~-18.4% |
| Calmar Ratio | ~0.32 | ~0.16 |
| Win Rate | ~50.8% | ~52.4% |
| VaR 95% (daily) | ~-0.22% | ~-0.45% |

*Results are computed from real data. They will update when the pipeline is re-run.*

---

## Limitations

1. Historical backtest ≠ live performance
2. ETF proxy limitations (management fees, tracking error)
3. Parameter sensitivity (momentum window, vol window not optimized)
4. Sharpe ratio uses Rf = 0% (documented assumption)
5. Transaction cost estimate (2 bps) is approximate
6. Period includes a long Treasury bull market (2003–2021) and 2022 rate shock
7. No inflation adjustment (nominal returns only)
8. Data source quality (Yahoo Finance may contain errors)

---

## Reproducibility

### Prerequisites
```bash
pip install yfinance pandas numpy pytest
npm install  # (in project root)
```

### Step 1: Download data
```bash
python analytics/download_data.py
```

### Step 2: Clean data
```bash
python analytics/clean_data.py
```

### Step 3: Compute signals
```bash
python analytics/signals.py
```

### Step 4: Run backtest
```bash
python analytics/backtest.py
```

### Step 5: Compute metrics
```bash
python analytics/metrics.py
```

### Step 6: Generate JSON outputs
```bash
python analytics/generate_outputs.py
```

### Or run the full pipeline
```bash
python run_pipeline.py
```

### Step 7: Start the dashboard
```bash
npm run dev
```

Visit http://localhost:3000

### Refresh data
Re-run steps 1–6 (or `python run_pipeline.py`) then refresh the browser.

### Run tests
```bash
pytest tests/test_analytics.py -v
```

---

## Technology Stack

**Python Analytics:**
- `yfinance` 1.7.x — data acquisition
- `pandas` 2.x — data manipulation
- `numpy` 2.x — numerical computation
- `pytest` — unit testing

**Frontend:**
- `Next.js` 16 (App Router, SSR)
- `TypeScript`
- `Tailwind CSS` v4
- `Recharts` — charts

---

## Project Structure

```
quantitative-fixed-income-research/
├── analytics/
│   ├── config.py           # All configurable parameters
│   ├── download_data.py    # yfinance data acquisition
│   ├── clean_data.py       # Validation and cleaning
│   ├── signals.py          # Momentum, vol, weights
│   ├── backtest.py         # Portfolio backtest engine
│   ├── metrics.py          # Performance & risk metrics
│   └── generate_outputs.py # JSON output for frontend
├── data/
│   ├── raw/                # Raw prices (git-ignored)
│   └── processed/          # Cleaned/computed data (git-ignored)
├── tests/
│   └── test_analytics.py   # 42 unit tests
├── app/
│   ├── layout.tsx
│   ├── page.tsx            # Main dashboard
│   └── globals.css
├── components/             # React components
├── public/data/            # JSON outputs (served to frontend)
├── types/data.ts           # TypeScript interfaces
├── lib/formatters.ts       # Display utilities
├── run_pipeline.py         # One-command pipeline runner
├── requirements.txt
├── package.json
└── README.md
```

---

## Author

**BBA (Decision Science), CHRIST University, Bengaluru**  
Educational project for quantitative finance skill development.

---

*Last pipeline run: see `public/data/meta.json`*
