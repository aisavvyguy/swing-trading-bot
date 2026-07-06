"""Base strategy interface and abstract class."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


@dataclass
class Signal:
    """A trading signal for a single symbol."""
    symbol: str
    direction: int          # -1 (short), 0 (neutral/flat), 1 (long)
    strength: float         # 0.0 to 1.0 — confidence in the signal
    target_price: float     # Take-profit target
    stop_price: float       # Stop-loss price
    horizon_days: int       # Expected holding period
    reason: str             # Human-readable reason for the trade


class Strategy(ABC):
    """Abstract base class for all trading strategies."""
    
    def __init__(self, config: dict):
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def generate_signals(self, features: pd.DataFrame) -> pd.Series:
        """Generate trading signals for the universe.
        
        Args:
            features: DataFrame with engineered features, indexed by (date, symbol)
            
        Returns:
            Series of signals: -1 (short), 0 (neutral), 1 (long), indexed by symbol
        """
        pass
    
    def get_position_size(self, signal: float, capital: float, 
                         volatility: float) -> int:
        """Calculate position size in shares.
        
        Args:
            signal: Signal strength (-1 to 1)
            capital: Available capital
            volatility: ATR or standard deviation of returns
            
        Returns:
            Number of shares (positive for long, negative for short)
        """
        risk_per_trade = self.config["risk"]["max_position_pct"]
        risk_dollars = capital * risk_per_trade * abs(signal)
        
        if volatility <= 0:
            return 0
            
        # Shares = risk_dollars / (ATR-based stop distance)
        atr_multiple = 2.0  # Stop at 2x ATR
        shares = int(risk_dollars / (volatility * atr_multiple))
        
        return shares if signal > 0 else -shares
    
    def filter_universe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter universe by liquidity and other criteria.
        
        Args:
            df: DataFrame with market data, must include 'dollar_volume' column
            
        Returns:
            Filtered DataFrame
        """
        min_dollar_volume = self.config["data"].get("min_dollar_volume", 10_000_000)
        
        if "dollar_volume" in df.columns:
            df = df[df["dollar_volume"] >= min_dollar_volume]
        
        return df
    
    def get_name(self) -> str:
        return self.name
