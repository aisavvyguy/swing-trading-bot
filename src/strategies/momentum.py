"""Momentum strategy — buy top performers, rotate monthly."""

import pandas as pd
import numpy as np
from .base import Strategy


class MomentumStrategy(Strategy):
    """Cross-sectional momentum strategy.
    
    Ranks ETFs by trailing returns (skip most recent month to avoid reversal).
    Goes long the top N ETFs. Rebalances at configured frequency.
    """
    
    def generate_signals(self, features: pd.DataFrame) -> pd.Series:
        config = self.config["strategy"]["momentum"]
        lookback = config["lookback_days"]        # e.g., 252 for 12-month
        skip = config["skip_days"]                # e.g., 21 to skip reversal
        top_n = config["top_n"]
        
        # Get latest data per symbol
        latest = features.groupby("symbol").last()
        
        # Calculate momentum: return from (T - lookback) to (T - skip)
        momentum_scores = {}
        for symbol, group in features.groupby("symbol"):
            if len(group) < lookback:
                continue
            prices = group["close"]
            momentum_score = (prices.iloc[-skip-1] / prices.iloc[-lookback-1]) - 1
            momentum_scores[symbol] = momentum_score
        
        if not momentum_scores:
            return pd.Series(dtype=float)
        
        # Rank and select top N
        scores = pd.Series(momentum_scores).sort_values(ascending=False)
        top_symbols = scores.head(top_n).index
        
        # Generate signals
        signals = pd.Series(0.0, index=scores.index)
        signals[top_symbols] = 1.0
        
        return signals
