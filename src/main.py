"""Swing Trading Bot — Entry Point

Usage:
    python src/main.py --mode paper --strategy mean_reversion
    python src/main.py --mode live --strategy ml_signal
    python src/main.py --mode backtest --strategy momentum --start 2023-01-01
"""

import argparse
import sys
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logging_config import setup_logging
from data.fetcher import DataFetcher
from data.features import FeatureEngineer
from strategies.momentum import MomentumStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.ml_strategy import MLStrategy
from risk.manager import RiskManager
from execution.broker import AlpacaBroker
from backtesting.engine import BacktestEngine

logger = setup_logging("main")


STRATEGY_MAP = {
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
    "ml_signal": MLStrategy,
}


def load_config(config_path: str = "config/config.yaml") -> dict:
    import yaml
    import os
    with open(config_path) as f:
        config = yaml.safe_load(f)
    # Expand env vars in config
    for key, value in config.get("broker", {}).items():
        if isinstance(value, str) and value.startswith("${"):
            env_var = value[2:-1]
            config["broker"][key] = os.environ.get(env_var, "")
    return config


def run_paper(config: dict, strategy_name: str, dry_run: bool = False):
    """Paper trading mode — uses Alpaca paper API with fake money, real market data.
    
    Alpaca's paper trading is completely free. You get:
    - $100,000 in fake starting capital
    - Real-time market data
    - Realistic fills with slippage
    - No risk to real money
    
    Set ALPACA_API_KEY and ALPACA_API_SECRET env vars (free at alpaca.markets).
    """
    mode_label = "DRY RUN" if dry_run else "PAPER"
    logger.info("Starting %s trading with strategy: %s", mode_label, strategy_name)
    
    fetcher = DataFetcher(config)
    engineer = FeatureEngineer(config)
    
    strategy_cls = STRATEGY_MAP.get(strategy_name)
    if not strategy_cls:
        logger.error("Unknown strategy: %s", strategy_name)
        sys.exit(1)
    
    strategy = strategy_cls(config)
    risk_mgr = RiskManager(config)
    broker = AlpacaBroker(config, paper=True)
    
    # Check account
    account = broker.get_account()
    logger.info("Account equity: $%.2f | Cash: $%.2f | Buying power: $%.2f",
                account.equity, account.cash, account.buying_power)
    
    # Check circuit breakers
    if risk_mgr.check_daily_loss_limit(account):
        logger.error("Daily loss limit reached. Halting all trading.")
        return
    
    # Fetch universe
    universe = fetcher.get_universe()
    logger.info("Universe: %d symbols", len(universe))
    
    # Generate signals
    data = fetcher.get_daily_bars(universe)
    if data.empty:
        logger.error("No data fetched. Check API keys and network.")
        return
    
    features = engineer.transform(data)
    signals = strategy.generate_signals(features)
    
    # Calculate volatilities for position sizing
    volatilities = {}
    for symbol in signals.index:
        symbol_data = data[data["symbol"] == symbol]
        if len(symbol_data) > 14:
            volatilities[symbol] = symbol_data["close"].pct_change().std()
    
    # Risk-filtered positions
    positions = risk_mgr.size_positions(signals, account.equity, 
                                         pd.Series(volatilities))
    
    if dry_run:
        logger.info("DRY RUN — would execute %d positions:", len(positions))
        for symbol, size in positions.items():
            signal = signals.get(symbol, 0)
            direction = "LONG" if signal > 0 else "SHORT" if signal < 0 else "FLAT"
            logger.info("  %s %s: %d shares", direction, symbol, abs(size))
        logger.info("Dry run complete. No orders placed.")
        return
    
    # Get current positions and calculate rebalance orders
    current_positions = broker.get_positions()
    orders = risk_mgr.get_rebalance_orders(current_positions, positions)
    
    logger.info("Paper trading — executing %d orders:", len(orders))
    results = []
    for order in orders:
        result = broker.place_order(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            limit_price=order.limit_price,
        )
        results.append(result)
        logger.info("  %s %s %d shares → %s (filled: %d @ $%.2f)",
                   order.side.upper(), order.symbol, order.quantity,
                   result.status, result.filled_quantity, result.filled_price)
    
    # Summary
    filled = sum(1 for r in results if r.status == "filled")
    partial = sum(1 for r in results if "partial" in str(r.status).lower())
    rejected = sum(1 for r in results if "reject" in str(r.status).lower())
    logger.info("Paper trading complete: %d filled, %d partial, %d rejected",
                filled, partial, rejected)


def run_live(config: dict, strategy_name: str):
    """Live trading mode — REAL MONEY. Use with extreme caution."""
    logger.warning("⚠️  LIVE TRADING MODE — REAL MONEY AT RISK ⚠️")
    
    fetcher = DataFetcher(config)
    engineer = FeatureEngineer(config)
    
    strategy_cls = STRATEGY_MAP.get(strategy_name)
    if not strategy_cls:
        logger.error("Unknown strategy: %s", strategy_name)
        sys.exit(1)
    
    strategy = strategy_cls(config)
    risk_mgr = RiskManager(config)
    broker = AlpacaBroker(config, paper=False)
    
    # Check circuit breakers first
    account = broker.get_account()
    if risk_mgr.check_daily_loss_limit(account):
        logger.error("Daily loss limit reached. Halting all trading.")
        return
    
    # Generate signals
    universe = fetcher.get_universe()
    data = fetcher.get_daily_bars(universe)
    features = engineer.transform(data)
    signals = strategy.generate_signals(features)
    
    # Risk-filtered positions
    positions = risk_mgr.size_positions(signals, account.equity)
    
    # Execute
    current_positions = broker.get_positions()
    orders_needed = risk_mgr.get_rebalance_orders(current_positions, positions)
    
    for order in orders_needed:
        broker.place_order(**order)
        logger.info("Order placed: %s", order)
    
    logger.info("Live trading complete. %d orders executed.", len(orders_needed))


def run_backtest(config: dict, strategy_name: str, start_date: str):
    """Backtest mode — historical simulation."""
    logger.info("Running backtest: %s from %s", strategy_name, start_date)
    
    strategy_cls = STRATEGY_MAP.get(strategy_name)
    if not strategy_cls:
        logger.error("Unknown strategy: %s", strategy_name)
        sys.exit(1)
    
    engine = BacktestEngine(config)
    results = engine.run(
        strategy_cls=strategy_cls,
        start_date=start_date,
    )
    
    # Print metrics
    print("\n" + "="*50)
    print("BACKTEST RESULTS")
    print("="*50)
    for metric, value in results.metrics.items():
        print(f"  {metric}: {value}")
    print("="*50)
    
    logger.info("Backtest complete.")


def main():
    parser = argparse.ArgumentParser(description="Swing Trading Bot")
    parser.add_argument("--mode", choices=["paper", "live", "backtest"], 
                       default="paper", help="Trading mode")
    parser.add_argument("--dry-run", action="store_true",
                       help="Paper mode: show signals without placing orders")
    parser.add_argument("--strategy", choices=list(STRATEGY_MAP.keys()),
                       default="mean_reversion", help="Strategy to run")
    parser.add_argument("--config", default="config/config.yaml",
                       help="Config file path")
    parser.add_argument("--start", default="2023-01-01",
                       help="Backtest start date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    config = load_config(args.config)
    
    if args.mode == "backtest":
        run_backtest(config, args.strategy, args.start)
    elif args.mode == "paper":
        run_paper(config, args.strategy, dry_run=args.dry_run)
    elif args.mode == "live":
        confirm = input("\n⚠️  LIVE TRADING — type 'YES' to confirm: ")
        if confirm == "YES":
            run_live(config, args.strategy)
        else:
            logger.info("Live trading cancelled.")
    else:
        logger.error("Unknown mode: %s", args.mode)


if __name__ == "__main__":
    main()
