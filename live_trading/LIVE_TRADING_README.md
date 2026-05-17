# 🚀 Live Trading Agent - IG Markets Integration

**Real-time automated trading using the Log-Fib Geometric Strategy**

---

## 📋 Prerequisites

### 1. IG Markets Account

You need an IG Markets account. **Strongly recommended to start with a DEMO account** for testing.

- Sign up: https://www.ig.com/uk/trading-api
- Get API credentials from your account dashboard

### 2. API Credentials

You'll need:
- **API Key** (from IG Developer Portal)
- **Username** (your IG username)
- **Password** (your IG password)
- **Account ID** (found in account settings)

---

## 🔧 Setup Instructions

### Step 1: Install Dependencies

```bash
cd /Users/kpal/projects/hermese
pip install -r requirements.txt
```

### Step 2: Configure IG Credentials

```bash
cd live_trading
cp .env.example .env
nano .env  # Edit with your actual credentials
```

**Fill in your credentials:**
```
IG_API_KEY=your_actual_api_key
IG_USERNAME=your_actual_username
IG_PASSWORD=your_actual_password
IG_ACCOUNT_ID=your_actual_account_id
IG_DEMO=true  # Start with demo!
IG_INSTRUMENT=IX.D.SILVER.IPV  # XAGUSD Silver
```

### Step 3: Test Connection

```bash
cd live_trading
python -c "from ig_client import IGClient; import os; from dotenv import load_dotenv; load_dotenv(); ig = IGClient({'api_key': os.getenv('IG_API_KEY'), 'username': os.getenv('IG_USERNAME'), 'password': os.getenv('IG_PASSWORD'), 'account_id': os.getenv('IG_ACCOUNT_ID'), 'demo': True}); print('Login:', ig.login()); print('Balance:', ig.get_account_balance())"
```

### Step 4: Run the Live Agent

```bash
python live_agent.py
```

---

## 🎯 How It Works

### Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  IG Markets     │────▶│  Live Agent      │────▶│  Log-Fib        │
│  Real-time API  │     │  (Price Monitor) │     │  Signal Engine  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                        │
                               ▼                        ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  Trade Execution │◀────│  Entry/TP/SL    │
                        │  (Buy/Sell)      │     │  Calculation    │
                        └──────────────────┘     └─────────────────┘
```

### Trading Flow

1. **Fetch Price** — Polls IG API every 5 seconds for latest XAGUSD price
2. **Update Buffer** — Stores price history for swing detection
3. **Detect Swings** — Identifies swing highs/lows using 12-bar lookback
4. **Calculate Levels** — Computes Log-Fib entry, TP, SL levels
5. **Check Trigger** — Monitors if price crosses entry level
6. **Execute Trade** — Places market order with stop loss via IG API
7. **Monitor Exit** — Watches for TP or SL hit
8. **Close Position** — Automatically closes trade when target hit

---

## 📊 Configuration

### Strategy Parameters (from `config.py`)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `lookback` | 12 | Bars for swing detection |
| `multiplier` | 0.382 | Log-Fib multiplier |
| `entry_ratio` | 0.5 | Entry at 50% retracement |
| `take_profit_ratio` | 0.786 | Exit at 0.786 extension |
| `stop_loss_ratio` | 1.0 | Stop at 1.0 extension |

### Risk Management (from `config.py`)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `max_concurrent_positions` | 1 | One trade at a time |
| `position_size_pct` | 0.02 | 2% of capital per trade |
| `max_daily_loss_pct` | 0.05 | 5% daily loss limit |
| `max_daily_trades` | 50 | Max trades per day |

---

## 🛡️ Safety Features

### Built-in Protections

1. **Demo Mode Default** — Starts with demo account (no real money)
2. **Daily Trade Limit** — Max 50 trades/day prevents overtrading
3. **Position Limit** — Only 1 concurrent position
4. **Stop Loss** — Every trade has automatic stop loss
5. **Error Handling** — Graceful handling of API failures

### Recommended Testing Workflow

1. **Week 1:** Run on DEMO account, monitor signals (no execution)
2. **Week 2:** Run on DEMO with small position sizes
3. **Week 3:** Review performance metrics
4. **Week 4:** Consider live account (start small)

---

## 📈 Monitoring

### Console Output

The agent prints real-time status:

```
📈 NEW LONG SIGNAL DETECTED @ 2026-05-15T16:06:00-04:00
   Swing Low: 75.73645
   Entry: 75.90709
   TP: 76.00470 | SL: 75.39516

💹 Price: 75.91234 | Position: IN | Trades Today: 3 | Win Rate: 85.7%

🎯 TRADE OPENED: LONG @ 75.90709
   TP: 76.00470 | SL: 75.39516

✅ TRADE CLOSED: Take Profit hit!
```

### Performance Tracking

At the end of each session:
- Total trades
- Wins / Losses
- Win rate percentage

---

## 🔧 Troubleshooting

### Issue: Login failed (403)

**Solution:** Check your API key and credentials in `.env`

### Issue: "Market not found"

**Solution:** Verify the instrument epic is correct for your region:
- UK: `IX.D.SILVER.IPV`
- US: May differ

### Issue: Order rejected

**Solution:** Check account has sufficient margin and instrument is tradable

### Issue: No signals detected

**Solution:** Ensure enough price data is collected (wait ~30 bars)

---

## 🚨 Important Warnings

1. **Start with DEMO** — Never test automated strategies with real money first
2. **Monitor regularly** — Don't leave unattended for long periods initially
3. **Set limits** — Use the risk management config to cap exposure
4. **Keep logs** — Review trade history to verify strategy performance
5. **API rate limits** — IG has rate limits; don't poll faster than 5 seconds

---

## 📞 IG API Documentation

- API Docs: https://www.ig.com/uk/trading-api
- Developer Portal: https://www.ig.com/uk/trading-api
- Support: api-support@ig.com

---

*Live Trading Agent created by Hermes Quant Squad*
