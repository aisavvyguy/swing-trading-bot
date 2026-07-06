"""Feature engineering pipeline for ML strategy."""

import pandas as pd
import numpy as np
from typing import List


class FeatureEngineer:
    """Engineers features from raw OHLCV data for ML model consumption.
    
    Generates: returns (multiple horizons), volatility, RSI, MACD,
    volume features, and cross-sectional rankings.
    """
    
    def __init__(self, config: dict):
        self.config = config["data"]
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform raw market data into engineered features.
        
        Args:
            df: DataFrame with columns [symbol, date, open, high, low, close, volume, dollar_volume]
            
        Returns:
            DataFrame with engineered features, indexed by (date, symbol)
        """
        if df.empty:
            return df
        
        df = df.copy()
        df = df.set_index(["date", "symbol"]).sort_index()
        
        # Returns at multiple horizons
        df["return_1d"] = df.groupby("symbol")["close"].pct_change(1)
        df["return_5d"] = df.groupby("symbol")["close"].pct_change(5)
        df["return_21d"] = df.groupby("symbol")["close"].pct_change(21)
        df["return_63d"] = df.groupby("symbol")["close"].pct_change(63)
        
        # Volatility
        df["volatility_5d"] = df.groupby("symbol")["return_1d"].rolling(5).std().droplevel(0)
        df["volatility_21d"] = df.groupby("symbol")["return_1d"].rolling(21).std().droplevel(0)
        
        # RSI (14-day)
        delta = df.groupby("symbol")["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.groupby("symbol").rolling(14).mean().droplevel(0)
        avg_loss = loss.groupby("symbol").rolling(14).mean().droplevel(0)
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["rsi_14"] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = df.groupby("symbol")["close"].transform(lambda x: x.ewm(span=12, adjust=False).mean())
        ema_26 = df.groupby("symbol")["close"].transform(lambda x: x.ewm(span=26, adjust=False).mean())
        df["macd"] = ema_12 - ema_26
        df["macd_signal"] = df.groupby("symbol")["macd"].transform(lambda x: x.ewm(span=9, adjust=False).mean())
        df["macd_histogram"] = df["macd"] - df["macd_signal"]
        
        # Volume features
        df["volume_ratio_5d"] = df["volume"] / df.groupby("symbol")["volume"].rolling(5).mean().droplevel(0)
        df["volume_ratio_21d"] = df["volume"] / df.groupby("symbol")["volume"].rolling(21).mean().droplevel(0)
        
        # Price position within range
        high_21 = df.groupby("symbol")["high"].rolling(21).max().droplevel(0)
        low_21 = df.groupby("symbol")["low"].rolling(21).min().droplevel(0)
        df["price_position_21d"] = (df["close"] - low_21) / (high_21 - low_21).replace(0, np.nan)
        
        # Cross-sectional momentum rank
        df["momentum_rank"] = df.groupby("date")["return_21d"].rank(pct=True)
        
        # Forward return (target for ML)
        df["target_5d"] = df.groupby("symbol")["close"].pct_change(-5).shift(-5) * -1  # + = up in 5 days
        
        # Drop rows with NaN (from rolling calculations)
        df = df.dropna()
        
        return df
    
    def get_feature_columns(self) -> List[str]:
        """Return list of feature columns (excluding target)."""
        return [
            "return_1d", "return_5d", "return_21d", "return_63d",
            "volatility_5d", "volatility_21d",
            "rsi_14",
            "macd", "macd_signal", "macd_histogram",
            "volume_ratio_5d", "volume_ratio_21d",
            "price_position_21d",
            "momentum_rank",
        ]
    
    def get_target_column(self) -> str:
        return "target_5d"
