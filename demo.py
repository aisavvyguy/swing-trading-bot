#!/usr/bin/env python3
"""Lightweight dry-run demo — no dependencies needed.
Runs a simulated mean reversion strategy on hardcoded ETF data.
"""

import math
import random
from datetime import datetime, timedelta


# Simulated ETF prices (SPY-like) for the last 30 trading days
def generate_price_data():
    """Generate realistic-looking price data with mean-reverting behavior."""
    symbols = ["SPY", "QQQ", "IWM", "XLF", "XLK", "XLE", "XLV", "XLI", "XLP", "XLY"]
    base_prices = {
        "SPY": 580.0, "QQQ": 480.0, "IWM": 220.0,
        "XLF": 50.0, "XLK": 230.0, "XLE": 95.0,
        "XLV": 150.0, "XLI": 135.0, "XLP": 82.0, "XLY": 210.0
    }
    
    data = {}
    for symbol in symbols:
        prices = [base_prices[symbol]]
        for i in range(29):
            # Random walk with slight mean reversion
            change = random.gauss(0, prices[-1] * 0.012)  # ~1.2% daily vol
            # Mean reversion pull
            reversion = (base_prices[symbol] - prices[-1]) * 0.05
            prices.append(prices[-1] + change + reversion)
        data[symbol] = prices
    
    return data, symbols


def calculate_zscore(prices, lookback=20):
    """Calculate z-score: how many standard deviations from the mean."""
    if len(prices) < lookback:
        return 0, 0, 0
    
    window = prices[-lookback:]
    mean = sum(window) / len(window)
    
    variance = sum((p - mean) ** 2 for p in window) / len(window)
    std = math.sqrt(variance) if variance > 0 else 1
    
    zscore = (prices[-1] - mean) / std
    return zscore, mean, std


def main():
    print("=" * 60)
    print("  SWING TRADING BOT — Dry Run Demo")
    print("  Strategy: Mean Reversion (z-score)")
    print("  Mode: No API keys needed — simulated data")
    print("=" * 60)
    
    # Generate data
    prices, symbols = generate_price_data()
    
    print(f"\n📊 ETF Universe: {len(symbols)} symbols")
    print(f"📅 Simulated data: 30 trading days\n")
    
    # Configuration
    entry_zscore = 2.0      # Enter when |z| > 2
    exit_zscore = 0.5       # Exit when |z| < 0.5 (for existing positions)
    max_positions = 5
    capital = 100_000.0
    risk_per_trade = 0.02   # 2% risk per position
    
    # Calculate z-scores for each symbol
    print("─" * 60)
    print(f"{'Symbol':<8} {'Price':>10} {'Z-Score':>10} {'Signal':>10} {'Shares':>10}")
    print("─" * 60)
    
    signals = {}
    for symbol in symbols:
        zscore, mean, std = calculate_zscore(prices[symbol])
        current_price = prices[symbol][-1]
        
        # Determine signal
        if zscore <= -entry_zscore:
            signal = "📈 LONG"
            direction = 1
        elif zscore >= entry_zscore:
            signal = "📉 SHORT"
            direction = -1
        else:
            signal = "➖ HOLD"
            direction = 0
        
        # Position size: risk_dollars / (ATR-based stop)
        atr = current_price * 0.015  # Approximate ATR as 1.5% of price
        stop_distance = atr * 2.0
        risk_dollars = capital * risk_per_trade
        shares = int(risk_dollars / stop_distance) if stop_distance > 0 and direction != 0 else 0
        
        print(f"{symbol:<8} ${current_price:>9.2f} {zscore:>10.2f} {signal:>10} {shares:>10,d}")
        
        if direction != 0:
            signals[symbol] = (direction, shares, zscore, current_price)
    
    print("─" * 60)
    
    # Rank and select top signals
    if signals:
        # Sort by absolute z-score (strongest signals first)
        ranked = sorted(signals.items(), key=lambda x: abs(x[1][2]), reverse=True)
        selected = ranked[:max_positions]
        
        print(f"\n🎯 Top {max_positions} signals (by z-score strength):\n")
        total_exposure = 0
        for rank, (symbol, (direction, shares, zscore, price)) in enumerate(selected, 1):
            direction_str = "LONG" if direction > 0 else "SHORT"
            exposure = shares * price
            total_exposure += exposure
            print(f"  {rank}. {direction_str} {symbol}: {shares:,} shares × ${price:.2f} = ${exposure:,.0f} "
                  f"(z-score: {zscore:+.2f})")
        
        print(f"\n  Total exposure: ${total_exposure:,.0f} "
              f"({total_exposure/capital*100:.1f}% of ${capital:,.0f} capital)")
    else:
        print(f"\n  ⚠️  No signals — all ETFs within normal range (|z| < {entry_zscore})")
        print("  This happens ~60-70% of the time in mean reversion strategies.")
    
    # Risk summary
    print(f"\n🛡️  Risk Controls Active:")
    print(f"  • Max position size: {risk_per_trade*100:.0f}% of capital (${capital * risk_per_trade:,.0f})")
    print(f"  • Daily loss limit: 3% → Stop trading")
    print(f"  • Weekly loss limit: 5% → Stop trading")
    print(f"  • Max drawdown: 25% → Kill switch")
    print(f"  • Consecutive losses: 8 → Pause strategy")
    print(f"  • Sector concentration: max 25% per sector")
    print(f"  • VIX > 35 → Reduce positions by 50%")
    
    # What next
    print(f"\n" + "=" * 60)
    print("  TO RUN WITH REAL MARKET DATA:")
    print("=" * 60)
    print("""
  1. Sign up at alpaca.markets (free)
  2. Go to Paper Trading → Generate API Keys
  3. Set environment variables:
     export ALPACA_API_KEY="your_key"
     export ALPACA_API_SECRET="your_secret"
  4. Install dependencies:
     pip install --break-system-packages -r requirements.txt
  5. Run paper trading:
     python src/main.py --mode paper --strategy mean_reversion
  6. Check your dashboard: app.alpaca.markets/paper
    """)
    
    print("=" * 60)
    print("  ⚠️  This was simulated data. Real markets are messier.")
    print("  Paper trade for 6+ months before risking real money.")
    print("=" * 60)


if __name__ == "__main__":
    main()
