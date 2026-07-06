"""Mean reversion strategy — z-score based on Bollinger Bands / rolling stats."""

import pandas as pd
import numpy as np
from .base import Strategy


class MeanReversionStrategy(Strategy):
    """Statistical mean reversion using z-score deviation from rolling mean.
    
    Goes long when price is significantly below its rolling average (oversold),
    goes short when significantly above (overbought). Best on mean-reverting
    instruments like ETFs and large-cap stocks.
    """
    
    def generate_signals(self, features: pd.DataFrame) -> pd.Series:
        config = self.config["strategy"]["mean_reversion"]
        lookback = config["lookback_days"]           # e.g., 20
        entry_zscore = config["entry_zscore"]        # e.g., 2.0
        exit_zscore = config["exit_zscore"]         # e.g., 0.5
        max_pairs = config.get("max_pairs", 5)
        
        signals = {}
        zscores_all = {}
        
        for symbol, group in features.groupby("symbol"):
            if len(group) < lookback:
                continue
            
            prices = group["close"]
            rolling_mean = prices.rolling(lookback).mean()
            rolling_std = prices.rolling(lookback).std()
            
            # Current z-score
            current_price = prices.iloc[-1]
            current_mean = rolling_mean.iloc[-1]
            current_std = rolling_std.iloc[-1]
            
            if current_std <= 0:
                continue
                
            zscore = (current_price - current_mean) / current_std
            zscores_all[symbol] = zscore
        
        if not zscores_all:
            return pd.Series(dtype=float)
        
        zscores = pd.Series(zscores_all)
        
        # Find most oversold (for long) and most overbought (for short)
        most_oversold = zscores[zscores <= -entry_zscore].nsmallest(max_pairs)
        most_overbought = zscores[zscores >= entry_zscore].nlargest(max_pairs)
        
        # Generate signals
        signals = pd.Series(0.0, index=zscores.index)
        signals[most_oversold.index] = 1.0     # Long oversold
        signals[most_overbought.index] = -1.0  # Short overbought
        
        return signals
