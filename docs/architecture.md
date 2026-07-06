# Technical Architecture — Swing Trading Bot

## Overview

A modular, production-grade swing trading engine designed for 1-10 day holding periods on US equities (NYSE, NASDAQ). Uses XGBoost/LightGBM for signal generation on engineered factor datasets.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                             │
│                        (main.py)                                 │
│    Scheduler → Signal Pipeline → Risk Check → Execution         │
└─────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ DATA LAYER  │ │  STRATEGY   │ │    RISK     │ │  EXECUTION  │
│             │ │   LAYER     │ │   LAYER     │ │   LAYER     │
├─────────────┤ ├─────────────┤ ├─────────────┤ ├─────────────┤
│ fetcher.py  │ │ base.py     │ │ manager.py  │ │ broker.py   │
│ features.py │ │ mean_rev..  │ │             │ │             │
│             │ │ momentum.py │ │ Position    │ │ Alpaca REST │
│ Alpaca API  │ │ ml_strat..  │ │ Sizing      │ │ + WebSocket │
│ Yahoo Fin   │ │             │ │ Drawdown    │ │             │
│             │ │ XGBoost/    │ │ Limits      │ │ Order Types │
│ SQLite/     │ │ LightGBM    │ │ Circuit     │ │ Market/Limit│
│ Parquet     │ │             │ │ Breakers    │ │             │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
                                              │
                    ┌─────────────────────────┘
                    ▼
            ┌─────────────┐     ┌──────────────┐
            │ BACKTESTING │     │  MONITORING   │
            │   ENGINE    │     │               │
            ├─────────────┤     ├───────────────┤
            │ engine.py   │     │ metrics.py    │
            │             │     │ logging.py    │
            │ Walk-       │     │               │
            │ Forward     │     │ Sharpe Ratio  │
            │ Validation  │     │ Max Drawdown  │
            │             │     │ Profit Factor │
            └─────────────┘     └───────────────┘
```

## Component Details

### 1. Data Layer (`src/data/`)

#### Data Sources
- **Alpaca Markets** (primary): Free tier includes real-time Level 1 quotes + historical bars + corporate actions
- **Yahoo Finance** (supplement): Free, covers delisted stocks for survivorship-bias-free backtesting
- **FRED/Quandl** (macro): Interest rates, VIX, sector ETFs

#### Data Pipeline

```
Raw Quote/Trade → Clean → Aggregate → Feature Engineer → Factor Store
                         │
                    ▼
              Corporate Actions (splits, dividends)
              Survivorship Bias Correction
              Outlier Detection & Handling
```

#### Key Features Engineered

| Category | Features | Horizon |
|----------|----------|---------|
| **Price-based** | Returns (1d, 5d, 21d), volatility, RSI, MACD, ATR | Daily |
| **Volume-based** | Volume ratios, dollar volume, turnover | Daily |
| **Factor-based** | Value (P/E, P/B), momentum (12-1m), quality (ROE), low vol | Weekly |
| **Market regime** | VIX level, sector correlations, breadth indicators | Weekly |
| **Cross-asset** | Sector ETF returns, SPY correlation, bond yields | Daily |
| **Sentiment** | Earnings surprise, analyst revision trend | Event-driven |

### 2. Strategy Layer (`src/strategies/`)

#### Strategy Interface
```python
class Strategy(ABC):
    @abstractmethod
    def generate_signals(self, universe: pd.DataFrame) -> pd.Series:
        """Returns series of -1 (short), 0 (neutral), 1 (long) per ticker"""
    
    @abstractmethod
    def get_position_size(self, signal: float, capital: float) -> int:
        """Returns number of shares to trade"""
```

#### Included Strategies

| Strategy | Type | Horizon | Complexity | Edge Type |
|----------|------|---------|------------|-----------|
| **Mean Reversion** | Pairs/stat arb | 5-10 days | Medium | Short-term overreaction reversion |
| **Momentum** | Trend following | 10-21 days | Low | Persistent trends in liquid ETFs |
| **ML Signal** | XGBoost/LightGBM | 5-21 days | High | Engineered factors → probability signal |

#### ML Strategy Details
- **Model:** XGBoost classifier (probability of positive 5-day forward return)
- **Training:** Walk-forward with expanding window (train on prior 3 years, test on next quarter)
- **Feature importance:** SHAP values for interpretability
- **Signal filtering:** Only trade when predicted probability > 0.55 or < 0.45
- **Regime adaptation:** Model retrained weekly on expanding window

### 3. Risk Layer (`src/risk/`)

#### Position Sizing

```
Position Size (shares) = (Account Equity × Risk Per Trade) / ATR(14)
```

- **Risk per trade:** 1-2% of account equity (not the full Kelly criterion)
- **ATR-based:** Position risk scales with volatility — tighter stops on volatile names
- **Sector limits:** Max 25% of portfolio in any single sector
- **Correlation cap:** No more than 2 positions with >0.7 correlation

#### Circuit Breakers

| Condition | Action |
|-----------|--------|
| Daily loss > 3% of account | Stop trading for the day |
| Weekly loss > 5% of account | Stop trading for the week, review strategies |
| Drawdown > 15% from peak | Reduce position sizes to 0.5% risk per trade |
| Drawdown > 25% from peak | **Kill switch** — halt all trading, human review required |
| Consecutive losses > 8 | Pause strategy, investigate regime change |
| API errors > 3 in 60 seconds | Stop trading, log, alert |
| VIX > 35 | Reduce position sizes by 50% |

### 4. Execution Layer (`src/execution/`)

#### Order Types by Scenario

| Scenario | Order Type | Why |
|----------|-----------|-----|
| Entry (normal) | Limit order at mid price | Avoid paying the spread |
| Entry (momentum signal) | Marketable limit (limit = ask + 0.1%) | Slight premium for fill certainty |
| Exit (take profit) | Limit order at target | Mechanical exit |
| Exit (stop loss) | Stop market order | Guaranteed fill on adverse move |
| Exit (EOD) | Market on Close (MOC) | Clean end-of-day exit, good for swing |

#### Execution Flow
```
Signal → Risk Check → Position Size → Order Construction → Submit → Fill Check → Log
                                                                      │
                                                                 ▼
                                                        Partial Fill Handler
                                                        (cancel remainder or adjust)
```

### 5. Backtesting Engine (`src/backtesting/`)

#### Walk-Forward Validation

```
Year 1-3  │ Year 4        ← Train on 1-3, test on 4
Year 2-4  │ Year 5        ← Train on 2-4, test on 5
Year 3-5  │ Year 6        ← Train on 3-5, test on 6
```

Each fold: train → optimize hyperparams on validation → test on out-of-sample

#### What It Models (Honestly)

| Factor | Modeled? | How |
|--------|---------|-----|
| Slippage | ✅ Yes | 0.05% per trade (adjustable) |
| Commission | ✅ Yes | $0.005/share or SEC/FINRA fees |
| Spread cost | ✅ Yes | Half-spread assumption |
| Survivorship bias | ✅ Yes | Include delisted stocks in universe |
| Look-ahead bias | ✅ Yes | Strict timestamp alignment |
| Corporate actions | ✅ Yes | Split/dividend adjusted prices |
| Market impact | ⚠️ Partial | Simple model, breaks at large position sizes |
| Queue position | ❌ No | Requires Level 2 data |

#### Key Backtest Metrics

```python
{
    "total_return": float,       # Cumulative return %
    "annual_return": float,      # CAGR
    "sharpe_ratio": float,       # Risk-adjusted return (annualized)
    "sortino_ratio": float,      # Downside risk-adjusted
    "max_drawdown": float,       # Worst peak-to-trough %
    "profit_factor": float,      # Gross profit / gross loss
    "win_rate": float,           # Winning trades %
    "avg_win_avg_loss_ratio": float,  # Magnitude ratio
    "total_trades": int,
    "avg_hold_days": float,
    "best_month": float,
    "worst_month": float,
    "monthly_win_rate": float,   # % of profitable months
}
```

---

## Technology Stack

| Component | Choice | Alternatives Considered |
|-----------|--------|------------------------|
| **Language** | Python 3.12+ | Julia (better perf, smaller ecosystem) |
| **ML framework** | XGBoost + LightGBM + scikit-learn | PyTorch (overkill), Statsmodels (baseline) |
| **Data manipulation** | pandas, numpy, polars | Dask (not needed for <10GB data) |
| **Data storage** | Parquet + SQLite | PostgreSQL (overkill for this scale) |
| **Broker API** | alpaca-py | IB API (more powerful, harder to use) |
| **Data API** | alpaca-py, yfinance | Polygon.io ($79/mo), IQFeed ($150/mo) |
| **Logging** | structlog | loguru, standard logging |
| **Config** | YAML + pydantic | TOML, JSON |
| **Testing** | pytest + pytest-cov | unittest |
| **CI/CD** | GitHub Actions | — |
| **Deployment** | Docker + systemd | Kubernetes (overkill) |

---

## Development Roadmap

### Phase 1: Data Pipeline (Weeks 1-4)
- [ ] Alpaca API integration (historical + real-time bars)
- [ ] Yahoo Finance supplement for delisted stocks
- [ ] Corporate actions handler
- [ ] Factor engineering pipeline
- [ ] Local Parquet data store
- [ ] Data quality checks (missing data, outliers, stale quotes)

### Phase 2: Backtesting Engine (Weeks 5-8)
- [ ] Walk-forward validation framework
- [ ] Slippage + commission model
- [ ] Portfolio-level metrics
- [ ] Benchmark comparison (SPY buy-and-hold)
- [ ] Parameter sensitivity analysis

### Phase 3: Baseline Strategies (Weeks 9-12)
- [ ] Momentum strategy (ETF rotation)
- [ ] Mean reversion strategy (pairs on large caps)
- [ ] Combined signal aggregator
- [ ] Paper trading deployment

### Phase 4: ML Strategy (Weeks 13-20)
- [ ] Feature importance analysis (SHAP)
- [ ] XGBoost model training pipeline
- [ ] Hyperparameter optimization (Optuna)
- [ ] Model versioning and rollback
- [ ] Out-of-sample validation

### Phase 5: Risk & Execution (Weeks 21-24)
- [ ] Position sizing engine
- [ ] Circuit breakers
- [ ] Order execution with retry logic
- [ ] Live Alpaca integration (paper account)

### Phase 6: Production (Weeks 25-32)
- [ ] Live trading on Alpaca paper
- [ ] Monitoring dashboard
- [ ] Automated daily reports
- [ ] Regime detection integration
- [ ] Live deployment with real capital ($5,000 start)

---

## Why Not {alternative}?

### Why Not Deep Learning?
- LSTMs/Transformers on OHLCV: marginal improvement over XGBoost on daily data, dramatically more overfitting risk, harder to debug
- Reinforcement learning: catastrophic in non-stationary environments, impossible to validate

### Why Not High-Frequency?
- Requires colocation, exchange membership, FPGA hardware
- Latency edge of <1ms is physically impossible from a home connection
- Billion-dollar firms with PhD teams own this space entirely

### Why Not Crypto?
- 24/7 markets with no circuit breakers
- Exchange risk (FTX, anyone?)
- Less regulatory protection
- Even more manipulated than equities

### Why Not Options?
- Complex Greeks management
- Liquidity issues in many strikes
- Pin risk on expiration
- Better as an overlay on equity positions than as a standalone strategy
