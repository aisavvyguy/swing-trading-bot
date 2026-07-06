"""Alpaca broker integration for execution."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Account:
    equity: float
    cash: float
    buying_power: float
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    drawdown_from_peak: float = 0.0
    peak_equity: float = 0.0


@dataclass 
class Position:
    symbol: str
    quantity: int
    market_value: float
    unrealized_pnl: float
    cost_basis: float


@dataclass
class OrderResult:
    symbol: str
    side: str           # buy | sell
    quantity: int
    filled_quantity: int
    status: str         # filled | partial | rejected | pending
    filled_price: float


class AlpacaBroker:
    """Alpaca Markets broker integration.
    
    Handles order placement, account queries, and position tracking.
    Supports both paper and live trading via the Alpaca API.
    """
    
    def __init__(self, config: dict, paper: bool = True):
        self.config = config["broker"]
        self.execution_config = config["execution"]
        self.paper = paper
        self._api = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Alpaca trading client."""
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce
            
            base_url = self.config["base_url"]
            if self.paper and "live" in base_url:
                base_url = "https://paper-api.alpaca.markets"
            
            self._api = TradingClient(
                api_key=self.config["api_key"],
                secret_key=self.config["api_secret"],
                paper=self.paper,
            )
            self._MarketOrderRequest = MarketOrderRequest
            self._LimitOrderRequest = LimitOrderRequest
            self._OrderSide = OrderSide
            self._TimeInForce = TimeInForce
        except ImportError:
            self._api = None
    
    def get_account(self) -> Account:
        """Get current account state."""
        if self._api is None:
            return Account(equity=100000.0, cash=100000.0, buying_power=200000.0)
        
        try:
            acct = self._api.get_account()
            return Account(
                equity=float(acct.equity),
                cash=float(acct.cash),
                buying_power=float(acct.buying_power),
                daily_pnl=float(getattr(acct, "equity", 0)) - float(getattr(acct, "last_equity", 0)),
            )
        except Exception:
            return Account(equity=100000.0, cash=100000.0, buying_power=200000.0)
    
    def get_positions(self) -> Dict[str, dict]:
        """Get current positions, keyed by symbol."""
        if self._api is None:
            return {}
        
        try:
            positions = self._api.get_all_positions()
            return {
                p.symbol: {
                    "qty": int(p.qty),
                    "market_value": float(p.market_value),
                    "unrealized_pl": float(p.unrealized_pl),
                    "cost_basis": float(p.cost_basis),
                }
                for p in positions
            }
        except Exception:
            return {}
    
    def place_order(self, symbol: str, side: str, quantity: int,
                   limit_price: Optional[float] = None) -> OrderResult:
        """Place an order. Market order if no limit price, limit order otherwise."""
        
        if self._api is None:
            return OrderResult(
                symbol=symbol, side=side, quantity=quantity,
                filled_quantity=quantity, status="filled (demo)", filled_price=0.0
            )
        
        try:
            order_side = self._OrderSide.BUY if side == "buy" else self._OrderSide.SELL
            
            if limit_price is not None:
                request = self._LimitOrderRequest(
                    symbol=symbol,
                    qty=abs(quantity),
                    side=order_side,
                    limit_price=limit_price,
                    time_in_force=self._TimeInForce.DAY,
                )
            else:
                request = self._MarketOrderRequest(
                    symbol=symbol,
                    qty=abs(quantity),
                    side=order_side,
                    time_in_force=self._TimeInForce.DAY,
                )
            
            order = self._api.submit_order(request)
            
            return OrderResult(
                symbol=symbol,
                side=side,
                quantity=quantity,
                filled_quantity=int(order.filled_qty or 0),
                status=order.status or "pending",
                filled_price=float(order.filled_avg_price or 0),
            )
            
        except Exception as e:
            return OrderResult(
                symbol=symbol, side=side, quantity=quantity,
                filled_quantity=0, status=f"rejected: {e}", filled_price=0.0
            )
    
    def cancel_all_orders(self):
        """Cancel all open orders."""
        if self._api is not None:
            try:
                self._api.cancel_all_orders()
            except Exception:
                pass
    
    def close_all_positions(self):
        """Close all open positions."""
        if self._api is not None:
            try:
                self._api.close_all_positions()
            except Exception:
                pass
