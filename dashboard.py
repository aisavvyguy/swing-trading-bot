#!/usr/bin/env python3
"""Trading Bot Dashboard — opens a live dashboard in your browser.
Zero dependencies. Pure Python + HTML/Chart.js (CDN).
"""

import http.server
import json
import math
import random
import socketserver
import webbrowser
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

PORT = 8765

SYMBOLS = ["SPY", "QQQ", "IWM", "XLF", "XLK", "XLE", "XLV", "XLI", "XLP", "XLY"]
BASE_PRICES = {
    "SPY": 580, "QQQ": 480, "IWM": 220,
    "XLF": 50, "XLK": 230, "XLE": 95,
    "XLV": 150, "XLI": 135, "XLP": 82, "XLY": 210
}
COLORS = [
    "#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
    "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#3b82f6"
]
SYMBOL_COLORS = dict(zip(SYMBOLS, COLORS))


def generate_prices(days=60):
    """Generate simulated price data with mean-reverting behavior."""
    data = {}
    end_date = datetime.now()
    dates = [(end_date - timedelta(days=days - i)).strftime("%Y-%m-%d") 
             for i in range(days)]
    
    for symbol in SYMBOLS:
        base = BASE_PRICES[symbol]
        prices = [base]
        for i in range(1, days):
            change = random.gauss(0, prices[-1] * 0.012)
            reversion = (base - prices[-1]) * 0.03
            prices.append(prices[-1] + change + reversion)
        data[symbol] = {"dates": dates, "prices": prices}
    return data


def calculate_zscores(prices, lookback=20):
    """Calculate z-scores for each symbol."""
    zscores = {}
    for symbol, info in prices.items():
        p = info["prices"]
        zs = [None] * len(p)
        for i in range(len(p)):
            start = max(0, i - lookback + 1)
            window = p[start:i + 1]
            if len(window) < lookback:
                continue
            mean = sum(window) / len(window)
            var = sum((v - mean) ** 2 for v in window) / len(window)
            std = math.sqrt(var) if var > 0 else 1e-9
            zs[i] = round((p[i] - mean) / std, 3)
        zscores[symbol] = zs
    return zscores


def calculate_signals(zscores, entry=2.0):
    """Generate trading signals from z-scores."""
    signals = {}
    for symbol, zs in zscores.items():
        sigs = [0] * len(zs)
        for i, z in enumerate(zs):
            if z is None:
                sigs[i] = 0
            elif z <= -entry:
                sigs[i] = 1   # LONG
            elif z >= entry:
                sigs[i] = -1  # SHORT
            else:
                sigs[i] = 0   # HOLD
        signals[symbol] = sigs
    return signals


def simulate_equity(signals, prices, capital=100000, risk_pct=0.02):
    """Simulate equity curve."""
    equity = [capital]
    peak = capital
    max_dd = 0
    wins = 0
    losses = 0
    
    for i in range(1, len(list(prices.values())[0]["prices"])):
        daily_change = 0
        for symbol in SYMBOLS:
            sig = signals[symbol][i] if i < len(signals[symbol]) else 0
            if sig != 0:
                price = prices[symbol]["prices"][i]
                prev_price = prices[symbol]["prices"][i - 1]
                ret = (price / prev_price - 1) * sig
                daily_change += ret * risk_pct
        
        if daily_change > 0:
            wins += 1
        elif daily_change < 0:
            losses += 1
            
        equity.append(equity[-1] * (1 + daily_change))
        
        if equity[-1] > peak:
            peak = equity[-1]
        dd = (equity[-1] - peak) / peak
        if dd < max_dd:
            max_dd = dd
    
    # Calculate metrics
    returns = [(equity[i] / equity[i - 1] - 1) for i in range(1, len(equity))]
    if returns:
        avg_return = sum(returns) / len(returns)
        std_return = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns)) if len(returns) > 1 else 1e-9
        sharpe = (avg_return / std_return * math.sqrt(252)) if std_return > 0 else 0
        total_return = (equity[-1] / equity[0] - 1) * 100
        years = len(returns) / 252
        cagr = ((1 + total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
    else:
        sharpe, total_return, cagr = 0, 0, 0
    
    return {
        "equity": [round(e, 2) for e in equity],
        "peak": peak,
        "max_drawdown": round(max_dd * 100, 2),
        "sharpe": round(sharpe, 2),
        "total_return": round(total_return, 2),
        "cagr": round(cagr, 2),
        "win_rate": round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0,
        "trades": wins + losses,
    }


def get_latest_signals(signals, prices, zscores):
    """Get current signals for the dashboard."""
    latest = []
    last_idx = len(list(prices.values())[0]["prices"]) - 1
    for symbol in SYMBOLS:
        sig = signals[symbol][last_idx] if last_idx < len(signals[symbol]) else 0
        z = zscores[symbol][last_idx] if last_idx < len(zscores[symbol]) else None
        price = prices[symbol]["prices"][last_idx]
        
        if sig == 1:
            label = "📈 LONG"
        elif sig == -1:
            label = "📉 SHORT"
        else:
            label = "➖ HOLD"
        
        atr = price * 0.015
        risk_dollars = 100000 * 0.02
        shares = int(risk_dollars / (atr * 2)) if sig != 0 else 0
        
        latest.append({
            "symbol": symbol,
            "price": round(price, 2),
            "zscore": round(z, 2) if z else 0,
            "signal": label,
            "direction": sig,
            "shares": shares,
            "exposure": round(shares * price, 2) if sig != 0 else 0,
            "color": SYMBOL_COLORS[symbol],
        })
    
    latest.sort(key=lambda x: abs(x["zscore"]), reverse=True)
    return latest


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/api/data":
            self.send_api_data()
        elif path == "/api/refresh":
            self.send_api_data(refresh=True)
        else:
            self.send_dashboard()
    
    def send_api_data(self, refresh=False):
        if refresh:
            global _prices, _zscores, _signals, _equity_data, _latest
            _prices = generate_prices(60)
            _zscores = calculate_zscores(_prices)
            _signals = calculate_signals(_zscores)
            _equity_data = simulate_equity(_signals, _prices)
            _latest = get_latest_signals(_signals, _prices, _zscores)
        
        data = {
            "prices": _prices,
            "zscores": _zscores,
            "signals": _signals,
            "equity": _equity_data,
            "latest_signals": _latest,
            "symbol_colors": SYMBOL_COLORS,
            "generated_at": datetime.now().strftime("%H:%M:%S"),
        }
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def send_dashboard(self):
        html = DASHBOARD_HTML
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        pass  # Silence HTTP logs


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Swing Trading Bot — Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
.header{background:#1e293b;border-bottom:2px solid #334155;padding:16px 24px;display:flex;justify-content:space-between;align-items:center}
.header h1{font-size:1.4rem;font-weight:700}
.header .status{display:flex;gap:16px;align-items:center;font-size:0.85rem}
.live-dot{width:8px;height:8px;background:#10b981;border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}
.btn{background:#334155;border:1px solid #475569;color:#e2e8f0;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:0.85rem}
.btn:hover{background:#475569}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px 24px}
.card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px;overflow:hidden}
.card-title{font-size:0.9rem;font-weight:600;color:#94a3b8;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.05em}
.chart-container{position:relative;height:250px}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.metric{background:#0f172a;border-radius:8px;padding:12px;text-align:center}
.metric-value{font-size:1.6rem;font-weight:700}
.metric-label{font-size:0.75rem;color:#64748b;margin-top:2px}
.positive{color:#10b981}.negative{color:#ef4444}.neutral{color:#f59e0b}
.signals-table{width:100%;border-collapse:collapse;font-size:0.85rem}
.signals-table th{text-align:left;padding:8px 12px;border-bottom:1px solid #334155;color:#64748b;font-weight:500;font-size:0.75rem;text-transform:uppercase}
.signals-table td{padding:8px 12px;border-bottom:1px solid #1e293b}
.signal-badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:0.75rem;font-weight:600}
.signal-long{background:rgba(16,185,129,0.15);color:#10b981}
.signal-short{background:rgba(239,68,68,0.15);color:#ef4444}
.signal-hold{background:rgba(100,116,139,0.15);color:#64748b}
.full-width{grid-column:1/-1}
.footer{text-align:center;padding:16px;color:#475569;font-size:0.75rem}
</style>
</head>
<body>
<div class="header">
  <h1>📊 Swing Trading Bot Dashboard</h1>
  <div class="status">
    <span class="live-dot"></span>
    <span id="update-time">Loading...</span>
    <button class="btn" onclick="refresh()">🔄 New Simulation</button>
  </div>
</div>

<div class="grid">
  <div class="card">
    <div class="card-title">📈 Equity Curve</div>
    <div class="chart-container"><canvas id="equityChart"></canvas></div>
  </div>
  <div class="card">
    <div class="card-title">⚠️ Drawdown</div>
    <div class="chart-container"><canvas id="drawdownChart"></canvas></div>
  </div>
  <div class="card">
    <div class="card-title">📉 ETF Prices (Normalized)</div>
    <div class="chart-container"><canvas id="priceChart"></canvas></div>
  </div>
  <div class="card">
    <div class="card-title">🎯 Z-Scores</div>
    <div class="chart-container"><canvas id="zscoreChart"></canvas></div>
  </div>
</div>

<div class="grid">
  <div class="card full-width">
    <div class="card-title">🏆 Performance Metrics</div>
    <div class="metrics" id="metrics-container"></div>
  </div>
</div>

<div class="grid">
  <div class="card full-width">
    <div class="card-title">📋 Current Signals</div>
    <div style="overflow-x:auto">
      <table class="signals-table" id="signals-table">
        <thead><tr><th>Symbol</th><th>Price</th><th>Z-Score</th><th>Signal</th><th>Shares</th><th>Exposure</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
  </div>
</div>

<div class="footer">
  📡 <span id="footer-time"></span> · Simulated data · 10 ETF universe · Mean Reversion Strategy
</div>

<script>
let charts = {};

async function fetchData() {
  const res = await fetch('/api/data');
  return res.json();
}

async function refresh() {
  const res = await fetch('/api/refresh');
  const data = await res.json();
  render(data);
}

function createChart(canvasId, type, datasets, options={}) {
  const ctx = document.getElementById(canvasId).getContext('2d');
  if (charts[canvasId]) charts[canvasId].destroy();
  charts[canvasId] = new Chart(ctx, {
    type: type,
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#94a3b8', boxWidth: 12, padding: 12, font: { size: 10 } } } },
      scales: { 
        x: { ticks: { color: '#475569', maxTicksLimit: 8, font: { size: 9 } }, grid: { color: '#1e293b' } },
        y: { ticks: { color: '#475569', font: { size: 9 } }, grid: { color: '#1e293b' } }
      },
      ...options
    }
  });
}

function render(data) {
  document.getElementById('update-time').textContent = 'Updated: ' + data.generated_at;
  document.getElementById('footer-time').textContent = 'Generated at ' + data.generated_at;
  
  // Equity curve
  const equityDates = data.prices.SPY.dates.map(d => d.slice(5));
  createChart('equityChart', 'line', [{
    label: 'Portfolio Equity',
    data: data.equity.equity.map((v,i) => ({x: equityDates[i], y: v})),
    borderColor: '#6366f1',
    backgroundColor: 'rgba(99,102,241,0.1)',
    borderWidth: 2,
    pointRadius: 0,
    fill: true
  }]);
  
  // Drawdown
  const peak = data.equity.peak;
  const dd = data.equity.equity.map(v => ((v - peak) / peak * 100));
  createChart('drawdownChart', 'line', [{
    label: 'Drawdown %',
    data: dd.map((v,i) => ({x: equityDates[i], y: Math.min(v, 0)})),
    borderColor: '#ef4444',
    backgroundColor: 'rgba(239,68,68,0.1)',
    borderWidth: 1.5,
    pointRadius: 0,
    fill: true
  }]);
  
  // Price chart (normalized, last 30 days)
  const recentDates = data.prices.SPY.dates.slice(-30).map(d => d.slice(5));
  const priceDatasets = Object.entries(data.prices).map(([sym, info]) => {
    const recent = info.prices.slice(-30);
    const norm = recent.map(p => p / recent[0] * 100);
    return {
      label: sym,
      data: norm.map((v,i) => ({x: recentDates[i], y: v})),
      borderColor: data.symbol_colors[sym],
      borderWidth: 1.5,
      pointRadius: 0,
    };
  });
  createChart('priceChart', 'line', priceDatasets, {
    plugins: { legend: { labels: { color: '#94a3b8', boxWidth: 10, padding: 8, font: { size: 9 } } } }
  });
  
  // Z-score chart
  const zscoreDates = data.prices.SPY.dates.slice(-30).map(d => d.slice(5));
  const zDatasets = Object.entries(data.zscores).filter(([sym, zs]) => {
    return zs.some(z => z !== null && Math.abs(z) > 1);
  }).slice(0, 6).map(([sym, zs]) => {
    const recent = zs.slice(-30);
    return {
      label: sym,
      data: recent.map((v,i) => ({x: zscoreDates[i], y: v || 0})),
      borderColor: data.symbol_colors[sym],
      borderWidth: 1.5,
      pointRadius: 0,
    };
  });
  createChart('zscoreChart', 'line', [
    ...zDatasets,
    {label: 'ENTRY (+2)', data: zscoreDates.map(d => ({x: d, y: 2})), borderColor: '#ef4444', borderWidth: 1, borderDash: [4,4], pointRadius: 0},
    {label: 'ENTRY (-2)', data: zscoreDates.map(d => ({x: d, y: -2})), borderColor: '#10b981', borderWidth: 1, borderDash: [4,4], pointRadius: 0},
  ], {
    plugins: { legend: { labels: { color: '#94a3b8', boxWidth: 10, padding: 8, font: { size: 9 } } } }
  });
  
  // Metrics
  const m = data.equity;
  document.getElementById('metrics-container').innerHTML = `
    <div class="metric"><div class="metric-value ${m.total_return >= 0 ? 'positive' : 'negative'}">${m.total_return}%</div><div class="metric-label">Total Return</div></div>
    <div class="metric"><div class="metric-value neutral">${m.cagr}%</div><div class="metric-label">Annual Return (CAGR)</div></div>
    <div class="metric"><div class="metric-value positive">${m.sharpe}</div><div class="metric-label">Sharpe Ratio</div></div>
    <div class="metric"><div class="metric-value negative">${m.max_drawdown}%</div><div class="metric-label">Max Drawdown</div></div>
    <div class="metric"><div class="metric-value neutral">${m.win_rate}%</div><div class="metric-label">Win Rate</div></div>
    <div class="metric"><div class="metric-value neutral">${m.trades}</div><div class="metric-label">Total Trades</div></div>
  `;
  
  // Signals table
  const tbody = document.querySelector('#signals-table tbody');
  tbody.innerHTML = data.latest_signals.map(s => `
    <tr>
      <td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${s.color};margin-right:8px"></span><strong>${s.symbol}</strong></td>
      <td>$${s.price.toFixed(2)}</td>
      <td class="${Math.abs(s.zscore) > 2 ? 'negative' : 'neutral'}">${s.zscore >= 0 ? '+' : ''}${s.zscore}</td>
      <td><span class="signal-badge ${s.direction > 0 ? 'signal-long' : s.direction < 0 ? 'signal-short' : 'signal-hold'}">${s.signal}</span></td>
      <td>${s.shares > 0 ? s.shares.toLocaleString() : '—'}</td>
      <td>${s.exposure > 0 ? '$' + s.exposure.toLocaleString() : '—'}</td>
    </tr>
  `).join('');
  
  document.getElementById('update-time').textContent = 'Updated: ' + data.generated_at;
}

fetchData().then(render);
</script>
</body>
</html>"""

# Global state — refreshed on /api/refresh
_prices = generate_prices(60)
_zscores = calculate_zscores(_prices)
_signals = calculate_signals(_zscores)
_equity_data = simulate_equity(_signals, _prices)
_latest = get_latest_signals(_signals, _prices, _zscores)


def main():
    print("=" * 60)
    print("  📊 SWING TRADING BOT — Live Dashboard")
    print("=" * 60)
    print(f"\n  Opening: http://localhost:{PORT}")
    print(f"  Press Ctrl+C to stop\n")
    
    # Open browser
    webbrowser.open(f"http://localhost:{PORT}")
    
    # Start server
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n  Dashboard stopped.")


if __name__ == "__main__":
    main()
