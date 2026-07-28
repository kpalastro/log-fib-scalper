# Kotak Neo API V2 Integration - Nifty50 Log-Fib Scalper

This module integrates the Kotak Neo API v2 with the log-fib scalper strategy for trading Nifty50 index.

## 📋 Prerequisites

1. **Kotak Neo Account**: You need an active Kotak Neo trading account
2. **API Access**: Enable API access in your Kotak Neo account
3. **Python 3.11+**: Required for running the agent

## 🔑 Getting API Credentials

### Step 1: Login to Kotak Neo
Go to https://neo.kotak.com and login with your credentials

### Step 2: Generate API Key
1. Navigate to **Settings** → **API Access** or **Developer Settings**
2. Click **"Generate API Key"**
3. Copy your **API Key** and **User Key/Consumer Secret**

### Step 3: Get Access Token
The access token is obtained via OAuth 2.0 flow:

```python
import requests

# Step 1: Get request token
auth_url = "https://gw.neotrade.kotak.com/v2/session"
headers = {
    "Content-Type": "application/json",
    "Consumer-Key": "YOUR_API_KEY",
    "Consumer-Secret": "YOUR_USER_KEY"
}

# Step 2: User authorization (manual step)
# Visit the authorization URL and approve

# Step 3: Exchange for access token
token_url = "https://gw.neotrade.kotak.com/v2/session/token"
response = requests.post(token_url, json={
    "request_token": "REQUEST_TOKEN_FROM_STEP_2"
}, headers=headers)

access_token = response.json()["data"]["access_token"]
```

**Note**: For now, you can get the token from the Kotak Neo web interface or contact Kotak Neo support for API access instructions.

## ⚙️ Configuration

### 1. Copy the environment template
```bash
cd /home/palbot/Projects/log-fib-scalper/live_trading
cp .env.neo .env
```

### 2. Fill in your credentials
Edit `.env` and add your credentials:
```bash
NEO_API_KEY=your_api_key_here
NEO_USER_KEY=your_user_key_here
NEO_TOKEN=your_access_token_here
NEO_SOURCE_ID=WEB
NEO_INSTRUMENT=NIFTY50_5MIN
```

## 🚀 Running the Live Agent

### Start Live Trading
```bash
cd /home/palbot/Projects/log-fib-scalper
python live_trading/nifty_live_agent.py
```

### Expected Output
```
📊 Using configuration: NIFTY50_5MIN
================================================================================
🚀 LOG-FIB NIFTY50 LIVE TRADING AGENT - STARTING
================================================================================
Instrument: NIFTY50 (5min)
Kotak Neo Token: 10000
Strategy Config: Lookback=10, Multiplier=0.786
Expected Performance: Win Rate=98.43%, PF=4.45
Poll Interval: 5 seconds
================================================================================
✅ Kotak Neo Login successful | User: Your Name

📡 Starting live data feed...

📊 NEW LONG SIGNAL @ 2026-05-18T10:30:00
   Swing High: 22500.00
   Swing Low: 22350.00
   Entry: 22467.90
   TP: 22500.00 | SL: 22314.60

🎯 SIGNAL TRIGGERED! Executing LONG...
📊 POSITION OPENED: LONG
   Entry: 22467.90
   TP: 22500.00 | SL: 22314.60
   Order ID: 26051800000123

💹 Price: 22470.50 | Position: IN | Trades Today: 1 | Win Rate: 0.0%
```

## 🧪 Backtesting the Strategy

### Run Backtest
```bash
cd /home/palbot/Projects/log-fib-scalper
python live_trading/test_nifty_strategy.py
```

This will:
1. Fetch 5 days of historical 5-minute Nifty50 data from Kotak Neo
2. Run the log-fib scalper strategy on the data
3. Calculate win rate, profit factor, and total PnL
4. Save results to `backtest_results.json`

### Example Backtest Results
```json
{
  "total_trades": 15,
  "wins": 14,
  "losses": 1,
  "total_pnl": 245.60,
  "trades": [...]
}
```

## 📊 Instrument Configurations

Available configurations in `nifty_config.py`:

| Instrument | Timeframe | Token | Win Rate | Profit Factor |
|------------|-----------|-------|----------|---------------|
| NIFTY50_5MIN | 5 min | 10000 | 98.43% | 4.45 |
| NIFTY50_1MIN | 1 min | 10000 | 93.48% | 3.21 |
| BANKNIFTY_5MIN | 5 min | 10001 | 96.21% | 3.87 |

Change instrument by setting `NEO_INSTRUMENT` in `.env`.

## 🎯 Strategy Logic

### Entry Signals
1. **Detect Swing High/Low**: Look for price pivots over `lookback` candles
2. **Calculate Fib Levels**: Entry at 78.6% retracement of the swing range
3. **Trigger**: Enter when price touches the entry level

### Exit Conditions
- **Take Profit**: At the swing high (for LONG) or swing low (for SHORT)
- **Stop Loss**: 23.6% beyond the swing low/high

### Example (LONG Trade)
```
Swing High: 22500
Swing Low:  22350
Range:      150 points

Entry (78.6%): 22350 + (150 × 0.786) = 22467.90
TP:            22500 (swing high)
SL:            22350 - (150 × 0.236) = 22314.60

Risk/Reward: 1:2.1
```

## 🔧 Troubleshooting

### Login Failed
```
❌ Kotak Neo Login failed: 401 - Unauthorized
```
**Solution**: Check your API key, user key, and token. Regenerate if expired.

### No Data Received
```
❌ Failed to fetch historical data
```
**Solution**: 
- Verify instrument token is correct (10000 for Nifty50)
- Check market hours (9:15 AM - 3:15 PM IST)
- Ensure API access is enabled on your account

### Order Rejected
```
❌ Order failed: 400 - Insufficient margin
```
**Solution**: Ensure you have sufficient trading capital in your account.

## 📚 API Reference

### KotakNeoClient Methods

- `login()` - Authenticate with Kotak Neo
- `get_market_price(instrument_token)` - Get real-time quote
- `get_historical_data(token, from_date, to_date, interval)` - Get OHLC data
- `place_order(instrument_token, transaction_type, quantity, ...)` - Place order
- `get_account_balance()` - Get margin and balance info

### NiftyLiveTradingAgent Methods

- `fetch_price()` - Fetch current market price
- `detect_swing_high()` / `detect_swing_low()` - Detect price swings
- `calculate_fib_levels()` - Calculate Fibonacci retracement
- `execute_trade()` - Place trade order
- `check_exit_conditions()` - Monitor TP/SL

## ⚠️ Risk Disclaimer

This software is for **educational and testing purposes only**. 

- Past performance does not guarantee future results
- Trading involves substantial risk of loss
- Always test strategies in a demo/simulation environment first
- Never trade with money you cannot afford to lose

## 📞 Support

For Kotak Neo API issues:
- Documentation: https://dev.kotakneo.io/
- Support: api.support@kotak.com

For strategy issues:
- Check the logs in `live_trading/` directory
- Review backtest results before live trading
