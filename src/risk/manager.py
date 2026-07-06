"""Risk Manager — position sizing, circuit breakers, drawdown limits."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


@dataclass
class Account:
    """Account state snapshot."""
    equity: float
    cash: float
    buying_power: float
    daily_pnl: float
    weekly_pnl: float
    drawdown_from_peak: float
    peak_equity: float
    positions: Dict[str, dict] = field(default_factory=dict)


@dataclass
class OrderRequest:
    """A risk-approved order."""
    symbol: str
    side: str           # buy | sell
    quantity: int
    order_type: str     # market | limit
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None


class RiskManager:
    """Manages position sizing, drawdown limits, and circuit breakers."""
    
    def __init__(self, config: dict):
        self.config = config["risk"]
        self.execution_config = config["execution"]
        self.trade_log: List[dict] = []
        self.consecutive_losses = 0
        self.daily_start_equity: Optional[float] = None
        self.weekly_start_equity: Optional[float] = None
    
    def size_positions(self, signals: pd.Series, equity: float, 
                       volatilities: pd.Series) -> Dict[str, int]:
        """Calculate position sizes for each signal.
        
        Args:
            signals: Series of -1, 0, 1 indexed by symbol
            equity: Current account equity
            volatilities: ATR or std dev per symbol
            
        Returns:
            Dict of symbol -> share quantity (may be negative for shorts)
        """
        max_position_pct = self.config["max_position_pct"]
        positions = {}
        
        for symbol in signals.index:
            signal = signals[symbol]
            if signal == 0:
                continue
            
            vol = volatilities.get(symbol, 0)
            if vol <= 0:
                continue
            
            # Risk dollars per position
            risk_dollars = equity * max_position_pct * abs(signal)
            
            # ATR-based stop distance (2x ATR)
            stop_distance = vol * 2.0  # Assume ATR in dollar terms
            
            # Shares = risk / stop_distance
            shares = int(risk_dollars / stop_distance) if stop_distance > 0 else 0
            
            # Apply direction
            if signal < 0:
                shares = -shares
            
            positions[symbol] = shares
        
        # Sector concentration check
        positions = self._apply_sector_limits(positions)
        
        return positions
    
    def _apply_sector_limits(self, positions: Dict[str, int]) -> Dict[str, int]:
        """Ensure no sector exceeds max allocation. Stub — implement with sector data."""
        # TODO: Add sector mapping (e.g., from Alpaca asset metadata)
        return positions
    
    def get_rebalance_orders(self, current_positions: Dict[str, dict],
                            target_positions: Dict[str, int]) -> List[OrderRequest]:
        """Generate orders to rebalance from current to target positions."""
        orders = []
        all_symbols = set(list(current_positions.keys()) + list(target_positions.keys()))
        
        for symbol in all_symbols:
            current_qty = int(current_positions.get(symbol, {}).get("qty", 0))
            target_qty = target_positions.get(symbol, 0)
            delta = target_qty - current_qty
            
            if delta == 0:
                continue
            
            side = "buy" if delta > 0 else "sell"
            order = OrderRequest(
                symbol=symbol,
                side=side,
                quantity=abs(delta),
                order_type=self.execution_config["entry_order_type"],
            )
            orders.append(order)
        
        return orders
    
    def check_daily_loss_limit(self, account: Account) -> bool:
        """Returns True if daily loss limit is breached — STOP TRADING."""
        if self.daily_start_equity is None:
            self.daily_start_equity = account.equity
        
        daily_change = (account.equity - self.daily_start_equity) / self.daily_start_equity
        limit = self.config["daily_loss_limit_pct"]
        
        if daily_change <= -limit:
            return True
        
        return False
    
    def check_weekly_loss_limit(self, account: Account) -> bool:
        """Returns True if weekly loss limit is breached."""
        if self.weekly_start_equity is None:
            self.weekly_start_equity = account.equity
        
        weekly_change = (account.equity - self.weekly_start_equity) / self.weekly_start_equity
        limit = self.config["weekly_loss_limit_pct"]
        
        if weekly_change <= -limit:
            return True
        
        return False
    
    def check_drawdown(self, account: Account) -> str:
        """Returns action: 'normal', 'reduce', or 'kill'."""
        dd = account.drawdown_from_peak
        
        if dd >= self.config["max_drawdown_pct"]:
            return "kill"
        elif dd >= self.config["reduce_at_drawdown_pct"]:
            return "reduce"
        
        return "normal"
    
    def check_consecutive_losses(self) -> bool:
        """Returns True if consecutive loss limit breached."""
        return self.consecutive_losses >= self.config["max_consecutive_losses"]
    
    def check_vix_condition(self, vix_level: float) -> bool:
        """Returns True if VIX is above the size-reduction threshold."""
        return vix_level > self.config["vix_size_reduction"]
    
    def record_trade(self, symbol: str, pnl: float, timestamp: datetime):
        """Record a completed trade for tracking."""
        self.trade_log.append({
            "symbol": symbol,
            "pnl": pnl,
            "timestamp": timestamp,
        })
        
        if pnl <= 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
    
    def reset_daily(self):
        """Reset daily tracking at start of new trading day."""
        self.daily_start_equity = None
    
    def reset_weekly(self):
        """Reset weekly tracking."""
        self.weekly_start_equity = None
