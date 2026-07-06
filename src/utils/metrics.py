"""Performance metrics calculator."""

import pandas as pd
import numpy as np
from typing import Dict


def calculate_metrics(equity_curve: pd.Series, trades: pd.DataFrame,
                     risk_free_rate: float = 0.0) -> Dict[str, float]:
    """Calculate comprehensive performance metrics.
    
    Args:
        equity_curve: Series of portfolio equity over time
        trades: DataFrame with columns ['pnl', 'hold_days', 'entry_date']
        risk_free_rate: Annual risk-free rate (default: 0.0)
        
    Returns:
        Dict of metric name -> value
    """
    metrics = {}
    
    if equity_curve.empty:
        return {k: 0.0 for k in ["total_return", "annual_return", "sharpe_ratio", 
                                  "sortino_ratio", "max_drawdown", "profit_factor",
                                  "win_rate", "calmar_ratio"]}
    
    returns = equity_curve.pct_change().dropna()
    trading_days_per_year = 252
    
    # Total return
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    metrics["total_return"] = total_return
    
    # Annualized return (CAGR)
    years = len(returns) / trading_days_per_year
    if years > 0:
        cagr = (1 + total_return) ** (1 / years) - 1
    else:
        cagr = 0.0
    metrics["annual_return"] = cagr
    
    # Sharpe ratio
    excess_returns = returns - risk_free_rate / trading_days_per_year
    if returns.std() > 0:
        sharpe = excess_returns.mean() / returns.std() * np.sqrt(trading_days_per_year)
    else:
        sharpe = 0.0
    metrics["sharpe_ratio"] = sharpe
    
    # Sortino ratio (downside deviation)
    downside_returns = returns[returns < 0]
    if len(downside_returns) > 0 and downside_returns.std() > 0:
        sortino = excess_returns.mean() / downside_returns.std() * np.sqrt(trading_days_per_year)
    else:
        sortino = 0.0
    metrics["sortino_ratio"] = sortino
    
    # Maximum drawdown
    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak
    max_dd = drawdown.min()
    metrics["max_drawdown"] = max_dd
    
    # Calmar ratio (CAGR / max drawdown)
    if abs(max_dd) > 0:
        calmar = cagr / abs(max_dd)
    else:
        calmar = 0.0
    metrics["calmar_ratio"] = calmar
    
    # Profit factor
    if not trades.empty and "pnl" in trades.columns:
        gross_profit = trades[trades["pnl"] > 0]["pnl"].sum()
        gross_loss = abs(trades[trades["pnl"] < 0]["pnl"].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    else:
        profit_factor = 0.0
    metrics["profit_factor"] = profit_factor
    
    # Win rate
    if not trades.empty:
        win_rate = (trades["pnl"] > 0).mean() if "pnl" in trades.columns else 0.0
    else:
        win_rate = 0.0
    metrics["win_rate"] = win_rate
    
    # Average win / average loss ratio
    if not trades.empty and "pnl" in trades.columns:
        wins = trades[trades["pnl"] > 0]["pnl"]
        losses = trades[trades["pnl"] < 0]["pnl"]
        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = abs(losses.mean()) if len(losses) > 0 else 0
        avg_wl_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        metrics["avg_win_loss_ratio"] = avg_wl_ratio
    
    # Expectancy (average profit per trade)
    if not trades.empty and "pnl" in trades.columns:
        metrics["expectancy"] = trades["pnl"].mean()
        metrics["total_trades"] = len(trades)
        metrics["avg_hold_days"] = trades["hold_days"].mean() if "hold_days" in trades.columns else 0
    else:
        metrics["total_trades"] = 0
        metrics["avg_hold_days"] = 0
    
    # Monthly return stats
    monthly = returns.resample("ME").apply(lambda x: (1 + x).prod() - 1) if isinstance(returns.index, pd.DatetimeIndex) else pd.Series()
    if not monthly.empty:
        metrics["monthly_win_rate"] = (monthly > 0).mean()
        metrics["best_month"] = monthly.max()
        metrics["worst_month"] = monthly.min()
    
    return metrics
