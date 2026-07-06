#!/usr/bin/env python3
"""Trading Bot Dashboard — Candlestick Charts + Live Signals
Zero dependencies. Pure Python 3 + Chart.js financial plugin (CDN).
"""

import http.server, json, math, random, socketserver, webbrowser
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

PORT = 8765

SYMBOLS = ["SPY", "QQQ", "IWM", "XLF", "XLK", "XLE", "XLV", "XLI", "XLP", "XLY"]
BASE = {"SPY":580,"QQQ":480,"IWM":220,"XLF":50,"XLK":230,"XLE":95,"XLV":150,"XLI":135,"XLP":82,"XLY":210}
COLORS = dict(zip(SYMBOLS, ["#6366f1","#10b981","#f59e0b","#ef4444","#8b5cf6","#06b6d4","#ec4899","#84cc16","#f97316","#3b82f6"]))

def gen_ohlc(days=90):
    """Full OHLC candlestick data."""
    data = {}
    end = datetime.now()
    dates = [(end - timedelta(days=days-i)).strftime("%Y-%m-%d") for i in range(days)]
    for sym in SYMBOLS:
        b = BASE[sym]; c = [b]; o = [b]; h = [b]; l = [b]
        for i in range(1, days):
            chg = random.gauss(0, c[-1]*0.012)
            rev = (b - c[-1])*0.03
            cl = c[-1] + chg + rev
            rng = abs(cl-c[-1])*(1+random.random())
            op = c[-1] + random.gauss(0, c[-1]*0.003)
            hi = max(op,cl) + rng*random.random()*0.5
            lo = min(op,cl) - rng*random.random()*0.5
            c.append(cl); o.append(op); h.append(hi); l.append(lo)
        data[sym] = {"dates":dates,"opens":o,"highs":h,"lows":l,"closes":c}
    return data

def calc_zscores(data, lookback=20):
    zs = {}
    for sym in SYMBOLS:
        ps = data[sym]["closes"]; z = [None]*len(ps)
        for i in range(len(ps)):
            w = ps[max(0,i-lookback+1):i+1]
            if len(w) < lookback: continue
            mu = sum(w)/len(w)
            sd = math.sqrt(sum((v-mu)**2 for v in w)/len(w))
            z[i] = round((ps[i]-mu)/sd, 3) if sd>0 else 0
        zs[sym] = z
    return zs

def calc_signals(zscores, entry=2.0):
    sigs = {}
    for sym in SYMBOLS:
        s = [0]*len(zscores[sym])
        for i, z in enumerate(zscores[sym]):
            if z is None: continue
            if z <= -entry: s[i] = 1
            elif z >= entry: s[i] = -1
        sigs[sym] = s
    return sigs

def sim_equity(signals, data, cap=100000, risk=0.02):
    eq = [cap]; pk = cap; dd = 0; w = 0; l = 0
    ndays = len(data[SYMBOLS[0]]["closes"])
    for i in range(1, ndays):
        dc = 0
        for sym in SYMBOLS:
            sig = signals[sym][i] if i<len(signals[sym]) else 0
            if sig:
                p = data[sym]["closes"][i]; pp = data[sym]["closes"][i-1]
                dc += (p/pp-1)*sig*risk
        if dc>0: w+=1
        elif dc<0: l+=1
        eq.append(eq[-1]*(1+dc))
        if eq[-1]>pk: pk=eq[-1]
        ddi = (eq[-1]-pk)/pk
        if ddi<dd: dd=ddi
    rets = [(eq[i]/eq[i-1]-1) for i in range(1,len(eq))]
    mu = sum(rets)/len(rets) if rets else 0
    sd = math.sqrt(sum((r-mu)**2 for r in rets)/len(rets)) if len(rets)>1 else 1e-9
    sr = mu/sd*math.sqrt(252)
    tr = (eq[-1]/eq[0]-1)*100
    yrs = len(rets)/252
    cagr = ((1+tr/100)**(1/yrs)-1)*100 if yrs>0 else 0
    return {"equity":[round(e,2) for e in eq],"max_drawdown":round(dd*100,2),
            "sharpe":round(sr,2),"total_return":round(tr,2),"cagr":round(cagr,2),
            "win_rate":round(w/(w+l)*100,1) if w+l else 0,"trades":w+l}

def latest_signals(signals, data, zscores):
    out = []; n = len(data[SYMBOLS[0]]["closes"])-1
    for sym in SYMBOLS:
        s = signals[sym][n]; z = zscores[sym][n]; p = data[sym]["closes"][n]
        label = "📈 LONG" if s==1 else ("📉 SHORT" if s==-1 else "➖ HOLD")
        atr = p*0.015; risk = 100000*0.02; sh = int(risk/(atr*2)) if s else 0
        out.append({"symbol":sym,"price":round(p,2),"zscore":round(z,2) if z else 0,
                    "signal":label,"direction":s,"shares":sh,
                    "exposure":round(sh*p,2) if s else 0,"color":COLORS[sym]})
    out.sort(key=lambda x: abs(x["zscore"]), reverse=True)
    return out

def get_candles(data, symbol, days=90):
    p = data[symbol]
    return [{"t":p["dates"][i],"o":round(p["opens"][i],2),"h":round(p["highs"][i],2),
             "l":round(p["lows"][i],2),"c":round(p["closes"][i],2)} for i in range(len(p["dates"]))]

# Global state
_data = gen_ohlc(90)
_zs = calc_zscores(_data)
_sigs = calc_signals(_zs)
_eq = sim_equity(_sigs, _data)
_latest = latest_signals(_sigs, _data, _zs)

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global _data, _zs, _sigs, _eq, _latest
        q = parse_qs(urlparse(self.path).query)
        path = urlparse(self.path).path
        
        if path == "/api/data":
            sym = q.get("symbol",["SPY"])[0]
            self.send_json({
                "candles": get_candles(_data, sym),
                "candle_symbol": sym,
                "zscores": _zs,
                "signals": _sigs,
                "equity": _eq,
                "latest_signals": _latest,
                "symbol_colors": COLORS,
                "symbols": SYMBOLS,
                "time": datetime.now().strftime("%H:%M:%S"),
            })
        elif path == "/api/refresh":
            _data = gen_ohlc(90)
            _zs = calc_zscores(_data)
            _sigs = calc_signals(_zs)
            _eq = sim_equity(_sigs, _data)
            _latest = latest_signals(_sigs, _data, _zs)
            self.send_json({"ok": True, "time": datetime.now().strftime("%H:%M:%S")})
        else:
            self.send_html(HTML)
    
    def send_json(self, d):
        self.send_response(200); self.send_header("Content-Type","application/json")
        self.send_header("Access-Control-Allow-Origin","*"); self.end_headers()
        self.wfile.write(json.dumps(d).encode())
    
    def send_html(self, h):
        self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8")
        self.end_headers(); self.wfile.write(h.encode())
    
    def log_message(self, *a): pass

HTML = r"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>📊 Swing Trading Bot — Candlestick Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-chart-financial@0.2.1/dist/chartjs-chart-financial.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/luxon@3.4.4/build/global/luxon.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
.header{background:#1e293b;border-bottom:2px solid #334155;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
.header h1{font-size:1.3rem;font-weight:700}
.status{display:flex;gap:14px;align-items:center;font-size:0.85rem}
.live-dot{width:8px;height:8px;background:#10b981;border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}
.btn{background:#334155;border:1px solid #475569;color:#e2e8f0;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:0.82rem;transition:background .15s}
.btn:hover{background:#475569}
.btn.active{background:#6366f1;border-color:#818cf8}
.sym-select{display:flex;gap:4px;flex-wrap:wrap}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;padding:14px 20px}
.grid-3{grid-template-columns:1fr 1fr 1fr}
.card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px}
.card-title{font-size:0.85rem;font-weight:600;color:#94a3b8;margin-bottom:10px;text-transform:uppercase;letter-spacing:.05em}
.chart-container{position:relative;height:280px}
.chart-container-lg{height:380px}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.metric{background:#0f172a;border-radius:8px;padding:12px;text-align:center}
.metric-value{font-size:1.5rem;font-weight:700}
.metric-label{font-size:0.72rem;color:#64748b;margin-top:2px}
.pos{color:#10b981}.neg{color:#ef4444}.warn{color:#f59e0b}
.signals-table{width:100%;border-collapse:collapse;font-size:0.84rem}
.signals-table th{text-align:left;padding:8px 10px;border-bottom:1px solid #334155;color:#64748b;font-size:.72rem;text-transform:uppercase}
.signals-table td{padding:8px 10px;border-bottom:1px solid #1e293b}
.badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:.72rem;font-weight:600}
.badge-long{background:rgba(16,185,129,.15);color:#10b981}
.badge-short{background:rgba(239,68,68,.15);color:#ef4444}
.badge-hold{background:rgba(100,116,139,.15);color:#64748b}
.full{grid-column:1/-1}
.footer{text-align:center;padding:14px;color:#475569;font-size:.75rem}
</style></head><body>
<div class="header">
  <h1>🕯️ Swing Trading Bot</h1>
  <div class="sym-select" id="sym-btns"></div>
  <div class="status">
    <span class="live-dot"></span><span id="time">Loading...</span>
    <button class="btn" onclick="refresh()">🔄 New Data</button>
  </div>
</div>

<div class="grid grid-3">
  <div class="card full">
    <div class="card-title" id="candle-title">🕯️ SPY — Candlestick Chart</div>
    <div class="chart-container chart-container-lg"><canvas id="candleChart"></canvas></div>
  </div>
</div>

<div class="grid">
  <div class="card">
    <div class="card-title">📈 Portfolio Equity</div>
    <div class="chart-container"><canvas id="equityChart"></canvas></div>
  </div>
  <div class="card">
    <div class="card-title">🎯 Z-Score Signals</div>
    <div class="chart-container"><canvas id="zscoreChart"></canvas></div>
  </div>
</div>

<div class="grid">
  <div class="card full">
    <div class="card-title">🏆 Performance</div>
    <div class="metrics" id="metrics"></div>
  </div>
</div>

<div class="grid">
  <div class="card full">
    <div class="card-title">📋 Current Signals</div>
    <table class="signals-table"><thead><tr><th>Symbol</th><th>Price</th><th>Z-Score</th><th>Signal</th><th>Shares</th><th>Exposure</th></tr></thead><tbody id="sig-body"></tbody></table>
  </div>
</div>
<div class="footer">📡 <span id="foot-time"></span> · 🕯️ Candlestick OHLC · 10 ETFs · Mean Reversion z-score ±2.0</div>

<script>
let activeSym = 'SPY', currentData = null, charts = {};

Chart.register(ChartFinancial);
Chart.defaults.font.family = '-apple-system,BlinkMacSystemFont,sans-serif';

function destroyChart(id){if(charts[id]){charts[id].destroy();delete charts[id]}}

function candleChart(data, sym){
  destroyChart('candleChart');
  const candles = data.candles.map(c => ({x: luxon.DateTime.fromISO(c.t).valueOf(), o:c.o, h:c.h, l:c.l, c:c.c}));
  const green = c => c.o < c.c ? '#10b981' : '#ef4444';
  const ctx = document.getElementById('candleChart').getContext('2d');
  const greenUp = candles.filter(c => c.o < c.c).length > candles.length/2;
  
  charts.candleChart = new Chart(ctx, {
    type: 'candlestick',
    data: { datasets: [{
      label: sym,
      data: candles,
      color: { up: '#10b981', down: '#ef4444', unchanged: '#64748b' },
      borderColor: { up: '#10b981', down: '#ef4444' },
    }]},
    options: {
      responsive:true, maintainAspectRatio:false,
      plugins: { 
        legend: { display: false },
        tooltip: { 
          callbacks: {
            label: ctx => `${sym} · O:$${ctx.raw.o} H:$${ctx.raw.h} L:$${ctx.raw.l} C:$${ctx.raw.c}`
          }
        }
      },
      scales: {
        x: { 
          type:'time', time:{unit:'day',tooltipFormat:'MMM dd'}, 
          ticks:{color:'#475569',maxTicksLimit:10,font:{size:9}}, grid:{color:'#1e293b'} 
        },
        y: { ticks:{color:'#475569',font:{size:9}}, grid:{color:'#1e293b'} }
      }
    }
  });
  document.getElementById('candle-title').innerHTML = `🕯️ <strong>${sym}</strong> — Candlestick Chart`;
}

function lineChart(id, datasets, opts={}){
  destroyChart(id);
  const ctx = document.getElementById(id).getContext('2d');
  charts[id] = new Chart(ctx, {
    type:'line',
    data:{datasets},
    options:{
      responsive:true,maintainAspectRatio:false,
      plugins:{legend:{labels:{color:'#94a3b8',boxWidth:10,padding:8,font:{size:9}}}},
      scales:{
        x:{ticks:{color:'#475569',maxTicksLimit:8,font:{size:9}},grid:{color:'#1e293b'}},
        y:{ticks:{color:'#475569',font:{size:9}},grid:{color:'#1e293b'}}
      },
      ...opts
    }
  });
}

async function loadData(sym){
  const r = await fetch('/api/data?symbol='+sym);
  currentData = await r.json();
  render(currentData);
}

function render(d){
  document.getElementById('time').textContent = 'Updated: '+d.time;
  document.getElementById('foot-time').textContent = 'Generated at '+d.time;
  
  // Candlestick chart
  candleChart(d, d.candle_symbol);
  
  // Equity curve
  const eq = d.equity;
  const dates = d.candles.map(c => c.t.slice(5));
  lineChart('equityChart', [{
    label:'Portfolio',
    data: eq.equity.map((v,i) => ({x:dates[i],y:v})),
    borderColor:'#6366f1',backgroundColor:'rgba(99,102,241,.08)',borderWidth:2,pointRadius:0,fill:true
  }]);
  
  // Z-score chart
  const zDates = dates.slice(-30);
  const zDatasets = Object.entries(d.zscores)
    .filter(([sym,zs]) => zs.some(z => z!==null && Math.abs(z)>1))
    .slice(0,6)
    .map(([sym,zs]) => ({
      label:sym,
      data: zs.slice(-30).map((v,i) => ({x:zDates[i],y:v||0})),
      borderColor:d.symbol_colors[sym],borderWidth:1.5,pointRadius:0
    }));
  zDatasets.push(
    {label:'+2 SHORT',data:zDates.map(x=>({x,y:2})),borderColor:'#ef4444',borderWidth:1,borderDash:[4,4],pointRadius:0},
    {label:'-2 LONG',data:zDates.map(x=>({x,y:-2})),borderColor:'#10b981',borderWidth:1,borderDash:[4,4],pointRadius:0}
  );
  lineChart('zscoreChart', zDatasets, {plugins:{legend:{labels:{color:'#94a3b8',boxWidth:10,padding:6,font:{size:9}}}}});
  
  // Metrics
  const m = d.equity;
  document.getElementById('metrics').innerHTML = `
    <div class="metric"><div class="metric-value ${m.total_return>=0?'pos':'neg'}">${m.total_return}%</div><div class="metric-label">Total Return</div></div>
    <div class="metric"><div class="metric-value warn">${m.cagr}%</div><div class="metric-label">CAGR</div></div>
    <div class="metric"><div class="metric-value pos">${m.sharpe}</div><div class="metric-label">Sharpe</div></div>
    <div class="metric"><div class="metric-value neg">${m.max_drawdown}%</div><div class="metric-label">Max Drawdown</div></div>
    <div class="metric"><div class="metric-value warn">${m.win_rate}%</div><div class="metric-label">Win Rate</div></div>
    <div class="metric"><div class="metric-value warn">${m.trades}</div><div class="metric-label">Trades</div></div>
  `;
  
  // Signals
  document.getElementById('sig-body').innerHTML = d.latest_signals.map(s => `
    <tr>
      <td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${s.color};margin-right:8px"></span><strong>${s.symbol}</strong></td>
      <td>$${s.price}</td>
      <td class="${Math.abs(s.zscore)>2?'neg':'warn'}">${s.zscore>=0?'+':''}${s.zscore}</td>
      <td><span class="badge ${s.direction>0?'badge-long':s.direction<0?'badge-short':'badge-hold'}">${s.signal}</span></td>
      <td>${s.shares||'—'}</td>
      <td>${s.exposure?'$'+s.exposure.toLocaleString():'—'}</td>
    </tr>
  `).join('');
}

async function refresh(){
  await fetch('/api/refresh');
  loadData(activeSym);
}

function switchSymbol(sym){
  activeSym = sym;
  document.querySelectorAll('.sym-select .btn').forEach(b => b.classList.remove('active'));
  document.getElementById('btn-'+sym)?.classList.add('active');
  loadData(sym);
}

// Build symbol buttons
document.getElementById('sym-btns').innerHTML = ['SPY','QQQ','IWM','XLF','XLK','XLE','XLV','XLI','XLP','XLY']
  .map(s => `<button class="btn${s==='SPY'?' active':''}" id="btn-${s}" onclick="switchSymbol('${s}')">${s}</button>`).join('');

loadData('SPY');
</script></body></html>"""

def main():
    print("\n" + "="*60)
    print("  🕯️  SWING TRADING BOT — Candlestick Dashboard")
    print("="*60)
    print(f"\n  Opening: http://localhost:{PORT}")
    print("  Click ETF buttons to switch charts")
    print("  Press Ctrl+C to stop\n")
    webbrowser.open(f"http://localhost:{PORT}")
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try: httpd.serve_forever()
        except KeyboardInterrupt: print("\n  Dashboard stopped.")

if __name__ == "__main__":
    main()
