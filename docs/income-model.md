# Income Model — The Real Math of Making Money With a Trading Bot

> **Brutal honesty about what's possible, what's required, and what's fantasy.**

---

## The Target: $5-15K/Year Supplemental Income

This is achievable. It's not glamorous. It won't replace your job. But it's real.

### The Math

| Scenario | Conservative | Realistic | Optimistic |
|----------|-------------|-----------|------------|
| **Account size** | $50,000 | $75,000 | $100,000 |
| **Annual return** | 10% | 12% | 15% |
| **Annual income** | **$5,000** | **$9,000** | **$15,000** |
| **Monthly income** | $417 | $750 | $1,250 |

### Why 10-15% Is the Realistic Ceiling

- Renaissance Technologies (best quant fund in history): ~40-70% annualized (Medallion, closed to outside capital)
- Top quant hedge funds: 15-25% in good years
- Professional prop traders: 10-20%
- **Successful retail algo trader: 8-15%**
- S&P 500 long-term average: ~10% nominal

**If you think you can make 50-100%+ annually, you're in the fantasy zone.** Anyone claiming that is either lying, lucky (temporarily), or taking risks that will eventually blow up.

---

## Capital Required — The Real Numbers

### Minimum Viable Account

| Requirement | Amount | Why |
|-------------|--------|-----|
| **Base capital** | $50,000 | Enough to generate meaningful income without excessive position concentration |
| **PDT minimum** (if margin account) | $25,000 | FINRA requirement — below this you can't day trade |
| **Cash account alternative** | $10,000+ | No PDT rule but T+1 settlement limits turnover |
| **Recommended starting capital** | **$50,000-75,000** | Comfortably above PDT threshold, diversified positions |

### The $25,000 Trap

The PDT rule says you need $25K minimum equity. But:
- You need $25,001 at all times — one bad trade puts you below
- Margin calls happen fast on drawdowns
- Realistically, you need $30K+ to day trade without PDT anxiety
- For swing trading (our approach), **a cash account with $15-50K works fine**

### Position Sizing Example

| Capital | Max Position Size (5% risk per trade) |
|---------|--------------------------------------|
| $10,000 | $500 per position |
| $25,000 | $1,250 per position |
| $50,000 | $2,500 per position |
| $100,000 | $5,000 per position |

---

## The Cost Structure

### Year 1 Costs

| Item | Budget Approach | Serious Approach |
|------|----------------|-----------------|
| Alpaca data (free tier) | $0 | $0 |
| Yahoo Finance (supplement) | $0 | $0 |
| Cloud compute (AWS/GCP) | $0 (local dev) | $240-600/year |
| Broker commissions | $0 (Alpaca commission-free) | $0 |
| **Total year 1 cost** | **$0** | **$600** |

### Real Cost: Your Time

| Phase | Hours | Value at $50/hr |
|-------|-------|----------------|
| Learning (finance + coding) | 100-200 | $5,000-10,000 |
| Architecture & data pipeline | 100-150 | $5,000-7,500 |
| Strategy development & backtesting | 200-400 | $10,000-20,000 |
| Paper trading & validation | 200-300 | $10,000-15,000 |
| **Total opportunity cost** | **600-1,050 hours** | **$30,000-52,500** |

---

## Break-Even Analysis

### When Does the Bot Pay Back Your Time?

| Annual Return | On $50K Capital | Hours to Break-Even (at $50/hr) |
|--------------|-----------------|-------------------------------|
| 5% | $2,500 | 12-21 years |
| 10% | $5,000 | 6-10 years |
| 15% | $7,500 | 4-7 years |
| 20% | $10,000 | 3-5 years |
| 30% | $15,000 | 2-3.5 years |

**Key insight:** At realistic returns (10-15%), you will NEVER break even on the opportunity cost of your time. The educational value and the engineering experience are the real return — the trading profits are a bonus.

### When Does the Bot Pay Back Your Capital?

Assuming 10% annual return on $50,000: **5 years to double your initial capital** (rule of 72: 72 ÷ 10 = 7.2 years for 2x at 10%).

The first year, you make $5,000 on $50,000 of capital. That's a 10% return — great for investing, terrible for "I quit my job to trade."

---

## The Compounding Path (Realistic)

| Year | Starting Capital | Return | Income | Cumulative Income | Notes |
|------|-----------------|--------|--------|-------------------|-------|
| 1 | $50,000 | 10% | $5,000 | $5,000 | Learning year — probably negative |
| 2 | $55,000 | 10% | $5,500 | $10,500 | Maybe break-even on costs |
| 3 | $60,500 | 12% | $7,260 | $17,760 | Strategy maturing |
| 4 | $67,760 | 12% | $8,131 | $25,891 | Supplemental income real |
| 5 | $75,891 | 15% | $11,384 | $37,275 | Not bad for extra income |
| 10 | $155,000 | 15% | $23,250 | ~$150,000 | Now we're talking |

This assumes NO withdrawals and consistent positive returns — both heroic assumptions.

---

## What $5-15K/Year Looks Like

### Monthly Cash Flow (Realistic Scenario)

| Month | Net P&L | Notes |
|-------|---------|-------|
| January | +$1,200 | Good momentum month |
| February | -$400 | Choppy — mean reversion bleed |
| March | +$800 | Trend resumed |
| April | +$300 | Flat month |
| May | -$600 | Regime change — strategy underperformed |
| June | +$1,500 | Strong momentum |
| July | +$200 | Summer doldrums |
| August | -$300 | Low volume |
| September | +$900 | Fall trend |
| October | +$1,100 | Earnings season tailwind |
| November | +$400 | Flat |
| December | +$500 | Year-end drift |
| **Year Total** | **+$5,600** | **11.2% on $50K** |

Notice: 5 positive months, 3 negative months. Consistent wins don't happen. Surviving the losing months IS the strategy.

---

## Comparison: Alternatives to $5-15K/Year

| Activity | Time Invested | Expected Return | Risk |
|----------|-------------|-----------------|------|
| Trading bot on $50K | 600-1000 hours | $5-15K/year | High — could lose money |
| S&P 500 buy-and-hold ($50K) | 0 hours | ~$5K/year (avg) | Medium — market risk |
| Freelance programming ($50/hr) | 100-300 hours | $5-15K/year | Low — reliable |
| Contract work (20 hrs/month) | 240 hours | $12-24K/year | Very low |
| SaaS side project | 500-1000 hours | $0-50K+ | Very high variance |
| High-yield savings (5% on $50K) | 0 hours | $2,500/year | Near zero |

---

## The TL;DR

**Making $5-15K/year from a trading bot is achievable** IF you:
- Have $50K-100K in risk capital you can afford to lose
- Target 10-15% annual returns (not 50%+)
- Commit to a multi-year development journey
- View trading profits as a bonus, not the primary return on your time

**Making $5-15K/year is NOT a good reason to build a trading bot** — freelancing pays better for less risk. But if you want the engineering challenge AND the income potential together, this is the realistic path.

### The honest advice:

> Build the bot for the engineering challenge. The income is gravy. If you need income, freelance. If you want to learn ML + finance + systems engineering, build the bot. Combining both is valid — just don't confuse which one pays the bills.
