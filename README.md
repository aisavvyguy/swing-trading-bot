# Swing Trading Bot — Dual-Track Project

> **Track 1:** Technical architecture for a realistic, production-grade swing trading engine  
> **Track 2:** Income modeling — what it actually takes to make $5-15K/year supplemental

## Why Swing Trading (Not Day Trading)

| | Day Trading | Swing Trading |
|---|---|---|
| **Holding period** | Seconds to minutes | 1-10 days |
| **Competition** | HFT firms, market makers with nanosecond infrastructure | Fund managers, other systematic traders |
| **Latency sensitivity** | Extreme (<1ms edge matters) | Moderate (seconds are fine) |
| **Transaction costs** | Compound rapidly, dominate edge | Manageable with 2-5 trades/week |
| **PDT rule** | $25K minimum or blocked | Cash account works, no PDT anxiety |
| **ML approach** | Deep learning mostly fails at intraday | XGBoost/LightGBM on daily/weekly factors works |
| **Realistic edge** | Nearly impossible for retail | Small but achievable |

## Project Structure

```
swing-trading-bot/
├── README.md                    # You are here
├── docs/
│   ├── architecture.md          # Full technical architecture
│   └── income-model.md          # Realistic income math & capital planning
├── config/
│   └── config.yaml              # Bot configuration
├── src/
│   ├── main.py                  # Entry point
│   ├── data/
│   │   ├── fetcher.py           # Data acquisition (Alpaca, Polygon, Yahoo)
│   │   └── features.py          # Factor engineering pipeline
│   ├── strategies/
│   │   ├── base.py              # Strategy interface
│   │   ├── mean_reversion.py    # Pairs/mean reversion strategies
│   │   ├── momentum.py          # Trend/momentum strategies
│   │   └── ml_strategy.py       # XGBoost/LightGBM signal strategy
│   ├── backtesting/
│   │   └── engine.py            # Walk-forward backtesting engine
│   ├── execution/
│   │   └── broker.py            # Broker API (Alpaca)
│   ├── risk/
│   │   └── manager.py           # Position sizing, circuit breakers, drawdown limits
│   └── utils/
│       ├── metrics.py           # Sharpe, Sortino, max drawdown, profit factor
│       └── logging_config.py    # Structured logging
└── requirements.txt
```

## Quick Start

```bash
# Clone
git clone https://github.com/aisavvyguy/swing-trading-bot
cd swing-trading-bot

# Install dependencies
pip install --break-system-packages -r requirements.txt

# Paper trade (free — no real money)
python src/main.py --mode paper --strategy mean_reversion

# Live trading (requires Alpaca API keys)
python src/main.py --mode live --strategy ml_signal
```

## The Dual-Track Philosophy

**Track 1 (Engineering):** Build this as a legitimate software project. Clean architecture, testable components, proper data pipeline, walk-forward backtesting. Even if the strategies never make money, you'll have built production-grade ML infrastructure that demonstrates serious engineering skill — valuable for any AI/ML role.

**Track 2 (Income):** Read `docs/income-model.md` before risking a dollar. The math is brutal but honest. This project is designed to help you find a small, sustainable edge — not to promise riches. Target: $5-15K/year supplemental income from $50-100K capital at 10-15% annual returns.

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| **ML framework** | XGBoost + LightGBM | Only ML approach with documented real-world quant success |
| **Data source** | Alpaca (free tier) + Yahoo Finance (supplement) | Low cost, production-grade API |
| **Broker** | Alpaca | Best retail algo trading API, paper trading, Python SDK |
| **Backtesting** | Custom walk-forward engine | Off-the-shelf libraries (backtrader, zipline) hide slippage assumptions |
| **Strategies** | Mean reversion + momentum + ML signals | Diversified across regimes |
| **Risk management** | Half-Kelly, volatility-adjusted, circuit breakers | Surviving bad years is more important than maximizing good years |
| **Language** | Python 3.12+ | Ecosystem: pandas, numpy, sklearn, xgboost, lightgbm, alpaca-py |

## Important Warnings

⚠️ **This is educational infrastructure, not financial advice.** The starter strategies are deliberately simple and untuned. Finding a real edge requires months of research, feature engineering, and out-of-sample validation.

⚠️ **Never trade money you can't afford to lose.** Start with paper trading. Stay there for 6+ months. Then start with $5,000. Scale only after consistent profitability over multiple market regimes.

⚠️ **Past performance does not predict future results.** Walk-forward backtesting helps but doesn't eliminate regime risk. Every strategy eventually encounters a market it wasn't designed for.

## License

MIT — see LICENSE file.
