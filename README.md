# Quantitative Fixed-Income Strategy & Risk Dashboard

An educational quantitative investment research project demonstrating a rules-based, momentum-driven fixed-income ETF strategy with full backtesting, risk analysis, and an interactive dashboard.

> **Disclaimer:** This is an educational project based on public historical data. All results are historical backtest statistics. This is not investment advice. Not affiliated with any investment firm. Historical results do not guarantee future performance.

---

## Project Overview

This project implements and backtests a quantitative fixed-income strategy across three U.S. Treasury ETFs (SHY, IEF, TLT), benchmarked against the U.S. Aggregate Bond Index (AGG). The project demonstrates:

- Rules-based signal generation (60-day momentum)
- Volatility-aware position sizing (inverse realized volatility)
- Monthly portfolio rebalancing with event-level look-ahead timing checks
- Transaction costs based on traded notional (gross vs. net returns)
- Standard risk metrics (Sharpe, MDD, VaR, CVaR, Tracking Error, IR)
- Interactive visualization built on real calculated outputs (no fabricated numbers)

---

## Research Question

*Does a simple momentum-based strategy across U.S. Treasury ETFs, sized by inverse realized volatility, deliver a materially different risk/return profile compared to a passive aggregate bond benchmark?*

Answer (honest): The strategy underperforms the AGG benchmark in absolute return (~2.27% CAGR vs. ~2.93% CAGR) but achieves meaningfully lower volatility (2.54% vs. 5.17%) and maximum drawdown (7.08% vs. 18.43%), resulting in a higher Sharpe ratio (0.89 vs. 0.59). The information ratio is negative, indicating active returns are not sufficient to justify the tracking error.

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
- **Raw price history:** 2003-10-01 → latest available date
- **Frequency:** Daily

### Evaluation Window and Warm-up

The raw price history is retained in full. Momentum and volatility indicators
warm up on that history, but no zero-return strategy period is compared with an
invested benchmark. Comparative performance begins on the first effective
trading date for which the prior signal date has complete momentum, realized
volatility, target weights, and benchmark data.

For the bundled data snapshot:

- Raw price start: 2003-10-01
- Raw return start: 2003-10-02
- Indicator warm-up: 63 trading days
- First investable comparative return: 2004-01-02
- NAV base date: 2003-12-31, with `NAV_0 = 1.0`

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

Missing, zero, or effectively-zero annualized realized volatility (≤ 1e-6) is
excluded from inverse-volatility sizing rather than clipped to a tiny value.
If no eligible asset has estimable volatility, the strategy uses a transparent
100% SHY defensive fallback; this is not an inverse-volatility allocation.

### Defensive Rule
If neither IEF nor TLT is eligible → 100% SHY

### Rebalancing
Monthly (last trading day of each month)

### Look-Ahead Bias Prevention
Signals computed with information available through the close of rebalance date
`t` become effective on the next available trading date. The return on that
effective date is the first return earned by the new weights. A programmatic
audit checks every valid event's signal date, effective date, target weights,
and holding period; synthetic tests verify future data cannot alter an earlier
signal.

### Transaction Costs
The economic cost assumption is 2 basis points (0.0002) per unit of traded
notional. Trading notional is `Σ|w_new - w_old|`, including both sides of a
switch. Conventional one-way turnover is reported separately as half of traded
notional. Both gross and net results are reported.

### NAV and Metric Convention

Each strategy and benchmark NAV begins at `NAV_0 = 1.0` on the trading date
immediately before the first investable return. Each subsequent row applies one
daily return: `NAV_t = NAV_(t-1) × (1 + r_t)`. Cumulative return is
`NAV_final / NAV_0 - 1`; CAGR uses the number of realized daily returns. The
Sharpe ratio is the annualized mean daily excess return divided by the standard
deviation of daily excess returns, using a 0% risk-free-rate assumption. It is
not CAGR divided by volatility.

---

## Backtest Results (2004-01-02 → 2026-09-25)

| Metric | Strategy (Net) | Benchmark (AGG) |
|--------|----------------|-----------------|
| Cumulative Return | ~66.4% | ~92.7% |
| Ann. Return (CAGR) | ~2.27% | ~2.93% |
| Ann. Volatility | ~2.54% | ~5.17% |
| Sharpe Ratio (Rf=0) | ~0.89 | ~0.59 |
| Max Drawdown | ~-7.1% | ~-18.4% |
| Calmar Ratio | ~0.32 | ~0.16 |
| Win Rate | ~51.4% | ~52.5% |
| Historical VaR 95% (daily) | ~-0.23% | ~-0.44% |

VaR is the historical 5th percentile of daily returns; CVaR is the mean of
returns at or below that threshold. Results are computed from the included data
snapshot and will update when the pipeline is re-run.

---

## Limitations

1. Historical backtest ≠ live performance
2. ETF proxy limitations (management fees, tracking error)
3. Parameter sensitivity (momentum window, vol window not optimized)
4. Sharpe ratio uses Rf = 0% (documented assumption)
5. Transaction cost estimate (2 bps per traded-notional unit) is approximate
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
│   └── test_analytics.py   # unit and timing tests
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
