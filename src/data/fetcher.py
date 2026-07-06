"""Data fetcher — Alpaca + Yahoo Finance integration."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional


class DataFetcher:
    """Fetches market data from Alpaca and Yahoo Finance.
    
    Uses Alpaca for reliable production data. Falls back to Yahoo Finance
    for delisted stocks and historical data beyond Alpaca's free tier range.
    """
    
    def __init__(self, config: dict):
        self.config = config["data"]
        self.broker_config = config["broker"]
        self._alpaca = None
        self._init_alpaca()
    
    def _init_alpaca(self):
        """Lazy-init Alpaca client."""
        api_key = self.broker_config.get("api_key", "")
        api_secret = self.broker_config.get("api_secret", "")
        
        if not api_key or not api_secret or api_key.startswith("${") or api_secret.startswith("${"):
            self._alpaca = None
            return
        
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            
            self._alpaca = StockHistoricalDataClient(
                api_key=api_key,
                secret_key=api_secret,
            )
            self._StockBarsRequest = StockBarsRequest
            self._TimeFrame = TimeFrame
        except ImportError:
            self._alpaca = None
    
    def get_universe(self) -> List[str]:
        """Get the trading universe of symbols."""
        universe_config = self.config["universe"]
        
        if universe_config["type"] == "etf":
            return [
                "SPY", "QQQ", "IWM", "DIA",
                "XLF", "XLK", "XLE", "XLV", "XLI", "XLP",
                "XLY", "XLB", "XLU", "XLRE", "XLC",
                "SMH", "IBB", "XRT", "XHB", "XME",
            ]
        elif universe_config["type"] == "sp500":
            # Would pull from Wikipedia or file — stub
            return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        elif universe_config["type"] == "custom":
            return universe_config.get("symbols", [])
        
        return ["SPY"]  # Safe default
    
    def get_daily_bars(self, symbols: List[str], 
                       lookback_days: Optional[int] = None) -> pd.DataFrame:
        """Fetch daily OHLCV bars for the given symbols.
        
        Returns DataFrame with columns: symbol, date, open, high, low, close, volume
        """
        if lookback_days is None:
            lookback_days = self.config.get("lookback_days", 1095)
        
        end = datetime.now()
        start = end - timedelta(days=lookback_days)
        
        all_data = []
        
        for symbol in symbols:
            df = self._fetch_single(symbol, start, end)
            if df is not None and not df.empty:
                df["symbol"] = symbol
                all_data.append(df)
        
        if not all_data:
            return pd.DataFrame()
        
        result = pd.concat(all_data)
        result = result.reset_index().rename(columns={"index": "date"})
        
        # Calculate dollar volume for liquidity filtering
        if "close" in result.columns and "volume" in result.columns:
            result["dollar_volume"] = result["close"] * result["volume"]
        
        return result
    
    def _fetch_single(self, symbol: str, start: datetime, end: datetime) -> Optional[pd.DataFrame]:
        """Fetch data for a single symbol. Try Alpaca first, then Yahoo."""
        
        # Try Alpaca first
        if self._alpaca is not None:
            try:
                request = self._StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=self._TimeFrame.Day,
                    start=start,
                    end=end,
                )
                bars = self._alpaca.get_stock_bars(request)
                df = bars.df
                if not df.empty:
                    df = df.reset_index()
                    return df[["timestamp", "open", "high", "low", "close", "volume"]].rename(
                        columns={"timestamp": "date"}
                    ).set_index("date")
            except Exception:
                pass  # Fall through to Yahoo
        
        # Fallback to Yahoo Finance
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start, end=end)
            if not df.empty:
                return df
        except Exception:
            pass
        
        return None
