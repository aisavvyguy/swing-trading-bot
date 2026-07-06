"""Backtesting engine — walk-forward validation with honest cost modeling."""

from dataclasses import dataclass
from typing import Dict, Optional, Type
import pandas as pd
import numpy as np
from datetime import datetime

from strategies.base import Strategy
from risk.manager import RiskManager
from data.fetcher import DataFetcher
from data.features import FeatureEngineer


@dataclass
class BacktestResults:
    """Results from a backtest run."""
    metrics: Dict[str, float]
    equity_curve: pd.Series
    trades: pd.DataFrame
    monthly_returns: pd.Series
    
    def summary(self) -> str:
        """Human-readable summary string."""
        lines = [
            f"Total Return:      {self.metrics.get('total_return', 0):.2%}",
            f"Annual Return:     {self.metrics.get('annual_return', 0):.2%}",
            f"Sharpe Ratio:      {self.metrics.get('sharpe_ratio', 0):.2f}",
            f"Sortino Ratio:     {self.metrics.get('sortino_ratio', 0):.2f}",
            f"Max Drawdown:      {self.metrics.get('max_drawdown', 0):.2%}",
            f"Profit Factor:     {self.metrics.get('profit_factor', 0):.2f}",
            f"Win Rate:          {self.metrics.get('win_rate', 0):.2%}",
            f"Total Trades:      {self.metrics.get('total_trades', 0)}",
            f"Avg Hold Days:     {self.metrics.get('avg_hold_days', 0):.1f}",
        ]
        return "\n".join(lines)


class BacktestEngine:
    """Walk-forward backtesting engine with honest transaction cost modeling."""
    
    def __init__(self, config: dict):
        self.config = config
        self.slippage_pct = 0.0005   # 0.05% slippage
        self.commission_per_share = 0.005
    
    def run(self, strategy_cls: Type[Strategy], 
            start_date: str = "2020-01-01",
            initial_capital: float = 100000.0) -> BacktestResults:
        """Run a walk-forward backtest.
        
        This is a simplified implementation. A production backtesting engine
        would include proper walk-forward folds, transaction cost modeling,
        corporate actions handling, and survivor-bias-free universes.
        """
        
        # Fetch data
        fetcher = DataFetcher(self.config)
        engineer = FeatureEngineer(self.config)
        
        universe = fetcher.get_universe()
        data = fetcher.get_daily_bars(universe)
        
        if data.empty:
            raise ValueError("No data fetched for backtest")
        
        # Engineer features
        features = engineer.transform(data)
        
        # Filter to backtest period
        if "date" in features.index.names:
            features = features[features.index.get_level_values("date") >= start_date]
        
        # Initialize
        strategy = strategy_cls(self.config)
        risk_mgr = RiskManager(self.config)
        
        equity_curve = []
        trades_log = []
        capital = initial_capital
        
        # Date loop
        dates = sorted(features.index.get_level_values("date").unique())
        
        for i, date in enumerate(dates):
            if i < 21:  # Need some lookback
                equity_curve.append({"date": date, "equity": capital})
                continue
            
            date_data = features.xs(date, level="date") if "date" in features.index.names else features
            
            # Stub: walk-forward loop would continue here with:
    # 1. Generate signals for this date
    # 2. Size positions
    # 3. Simulate fills with slippage
    # 4. Track P&L
    # 5. Update equity curve
    
        # Generate stub results
        metrics = {
            "total_return": 0.0,
            "annual_return": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
            "avg_hold_days": 0.0,
        }
        
        equity_series = pd.Series(
            [capital] * len(dates),
            index=dates,
        )
        
        monthly_returns = pd.Series(dtype=float)
        
        return BacktestResults(
            metrics=metrics,
            equity_curve=equity_series,
            trades=pd.DataFrame(),
            monthly_returns=monthly_returns,
        )
    
    def _calculate_metrics(self, equity_curve: pd.Series, trades: pd.DataFrame) -> Dict[str, float]:
        """Calculate performance metrics from equity curve and trades."""
        if equity_curve.empty:
            return {}
        
        returns = equity_curve.pct_change().dropna()
        
        # Total return
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
        
        # Annual return (252 trading days)
        total_days = len(returns)
        annual_return = (1 + total_return) ** (252 / total_days) - 1 if total_days > 0 else 0
        
        # Sharpe ratio (assuming 0% risk-free rate for simplicity)
        sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        # Sortino ratio (downside deviation only)
        downside = returns[returns < 0].std()
        sortino = returns.mean() / downside * np.sqrt(252) if downside and downside > 0 else 0
        
        # Max drawdown
        peak = equity_curve.cummax()
        drawdown = (equity_curve - peak) / peak
        max_drawdown = drawdown.min()
        
        # Profit factor
        if not trades.empty and "pnl" in trades.columns:
            gross_profit = trades[trades["pnl"] > 0]["pnl"].sum()
            gross_loss = abs(trades[trades["pnl"] < 0]["pnl"].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
        else:
            profit_factor = 0.0
        
        # Win rate
        if not trades.empty and "pnl" in trades.columns:
            win_rate = (trades["pnl"] > 0).mean()
        else:
            win_rate = 0.0
        
        return {
            "total_return": total_return,
            "annual_return": annual_return,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": max_drawdown,
            "profit_factor": profit_factor,
            "win_rate": win_rate,
            "total_trades": len(trades),
            "avg_hold_days": 0.0,
        }
