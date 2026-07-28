# Zerodha Free API MCP Server

Real-time Nifty/Banknifty data using Zerodha's free API (no paid Kite Connect required).

## ⚠️ Important Warning

This uses **unofficial API access** via enctoken authentication. Use at your own risk:
- Credentials stored in plaintext (secure your files!)
- API access may break if Zerodha changes their auth
- Not supported by Zerodha
- For personal use only

## 📋 Prerequisites

1. **Zerodha Kite Account** - Active trading account with login credentials
2. **Python 3.11+** with virtual environment
3. **kite_trade.py wrapper** - Located at `/home/palbot/Downloads/zerodhahistoricaldata/kite_trade.py`

## 🔧 Setup

### Step 1: Install Dependencies

```bash
cd /home/palbot/Projects/log-fib-scalper
.venv/bin/pip install mcp requests python-dateutil
```

### Step 2: Store Credentials

**Option A: Interactive Setup (Recommended)**

```bash
python /home/palbot/Projects/log-fib-scalper/mcp/setup-zerodha-creds.py
```

This will prompt for:
- User ID (e.g., `RD156567`)
- Password
- 2FA (PIN or TOTP)

Credentials saved to `~/.zerodha_credentials.json` with 600 permissions.

**Option B: Manual Config File**

Create `~/.zerodha_credentials.json`:

```json
{
  "user_id": "YOUR_USER_ID",
  "password": "YOUR_PASSWORD",
  "twofa": "YOUR_PIN_OR_TOTP"
}
```

Set permissions:
```bash
chmod 600 ~/.zerodha_credentials.json
```

**Option C: Environment Variables**

```bash
export ZERODHA_USER_ID=your_user_id
export ZERODHA_PASSWORD=your_password
export ZERODHA_TWOF A=your_pin
```

### Step 3: Add to Hermes Config

Edit `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  zerodha-free:
    command: python
    args:
      - /home/palbot/Projects/log-fib-scalper/mcp/zerodha_free_mcp.py
    timeout: 60
```

### Step 4: Restart Hermes

```bash
hermes gateway restart
```

## 🛠 Available Tools

| Tool | Description | Example |
|------|-------------|---------|
| `zerodha_get_ltp` | Get LTP for instruments | "Get Nifty LTP" |
| `zerodha_get_instruments` | List all instruments for exchange | "Show NFO instruments" |
| `zerodha_search_instrument` | Search by symbol name | "Find Nifty futures" |
| `zerodha_get_historical` | Get OHLCV candle data | "Get Nifty 5min candles" |
| `zerodha_get_margins` | Get trading margins | "Show my margins" |
| `zerodha_get_profile` | Get user profile | "Get my profile" |
| `zerodha_get_nifty_token` | Auto-detect current Nifty futures token | "Get Nifty token" |
| `zerodha_get_banknifty_token` | Auto-detect current Banknifty futures token | "Get Banknifty token" |

## 📊 Common Instruments

### Nifty 50
```python
# Cash Index (not directly tradable)
Symbol: NSE:NIFTY 50
Token: Not applicable

# Futures (Current Month)
Symbol: NFO:NIFTY26MAYFUT
Token: Auto-detected via zerodha_get_nifty_token

# Options
Symbol: NFO:NIFTY26MAY46000CE (46000 Call May 2026)
Format: NFO:NIFTY<DD><MON><STRIKE><CE/PE>
```

### Banknifty
```python
# Futures (Current Month)
Symbol: NFO:BANKNIFTY26MAYFUT
Token: Auto-detected via zerodha_get_banknifty_token

# Options
Symbol: NFO:BANKNIFTY26MAY48000CE (48000 Call May 2026)
```

### Instrument Tokens
```python
# Nifty 50 Index
Token: 256265

# Nifty Futures (varies by month)
Token: Auto-detect with zerodha_get_nifty_token

# Banknifty Futures (varies by month)
Token: Auto-detect with zerodha_get_banknifty_token
```

## 🎯 Usage Examples

### Get Real-Time LTP

```
Get LTP for Nifty 50
```

Hermes will:
1. Call `zerodha_get_nifty_token` → Get current futures token
2. Call `zerodha_get_ltp` → Get real-time price

### Get Historical Data

```
Get 5-minute candles for Nifty from 2026-05-20 to 2026-05-21
```

### Search Instruments

```
Find all Nifty option strikes for May 2026
Search for BANKNIFTY futures
```

### Multi-Timeframe Analysis

```
Analyze Nifty across timeframes:
1. Get current instrument token
2. Fetch 5-minute historical data
3. Fetch 15-minute historical data
4. Fetch 1-hour historical data
5. Calculate Log-Fib levels
```

## 🔍 Finding Instrument Tokens

Use the search tool:

```
Search for NIFTY in NFO exchange
```

Or get all instruments:

```
Show all NFO instruments
```

Common tokens:
- **Nifty 50 Index**: `256265`
- **Banknifty Index**: `29934084`
- **Nifty Futures**: Auto-detected (changes monthly)
- **Banknifty Futures**: Auto-detected (changes monthly)

## ⚙️ API Limits

- **3 requests per second**
- **60 requests per minute**
- Historical data: Max ~200 candles per request
- Enctoken expires after ~24 hours (auto-refreshes on next request)

## 🐛 Troubleshooting

### "Enctoken authentication failed"
- Check credentials are correct
- Ensure 2FA is correct (PIN or TOTP)
- Re-run setup script to update credentials

### "No module named 'kite_trade'"
- Verify wrapper exists: `/home/palbot/Downloads/zerodhahistoricaldata/kite_trade.py`
- Check PYTHONPATH includes wrapper directory

### "Instrument token not found"
- Use `zerodha_search_instrument` to find correct token
- Futures tokens change monthly (expiry)

### "API rate limit exceeded"
- Wait 60 seconds between requests
- Batch multiple symbols in single `zerodha_get_ltp` call

### "Market closed"
- Indian market hours: 9:15 AM - 3:30 PM IST
- Historical data still available outside market hours

## 📚 Files

```
/home/palbot/Projects/log-fib-scalper/mcp/
├── zerodha_free_mcp.py          # MCP server
├── setup-zerodha-creds.py       # Credential setup script
└── ZERODHA_FREE_README.md       # This file

/home/palbot/Downloads/zerodhahistoricaldata/
├── kite_trade.py                # Zerodha wrapper (enctoken auth)
└── historical.py                # Example usage
```

## 🆚 vs Paid Kite Connect API

| Feature | Free (Enctoken) | Paid (Kite Connect) |
|---------|----------------|---------------------|
| Cost | Free | ₹2000 + GST |
| Real-time LTP | ✅ | ✅ |
| Historical Data | ✅ | ✅ |
| Order Placement | ❌ | ✅ |
| Official Support | ❌ | ✅ |
| Rate Limits | 3 req/s | 3 req/s |
| Token Expiry | ~24 hours | Permanent |

## 🔐 Security

- Credentials stored in `~/.zerodha_credentials.json`
- File permissions set to `600` (owner read/write only)
- **DO NOT** commit credentials to Git
- **DO NOT** share credentials
- Consider using a dedicated trading account

## 📈 Integration with Log-Fib Scalper

Replace static CSV files with live data:

```python
# Before (static CSV)
import pandas as pd
df = pd.read_csv("data/OANDA_XAUUSD5.csv")

# After (live Zerodha data)
# 1. Get instrument token
token = zerodha_get_nifty_token()

# 2. Get historical candles
candles = zerodha_get_historical(
    instrument_token=token["instrument_token"],
    from_date="2026-05-20",
    to_date="2026-05-21",
    interval="5minute"
)

# 3. Run Log-Fib analysis on live data
```

## 🚀 Quick Start

```bash
# 1. Setup credentials
python /home/palbot/Projects/log-fib-scalper/mcp/setup-zerodha-creds.py

# 2. Add to Hermes config (see above)

# 3. Restart Hermes
hermes gateway restart

# 4. Test
Get Nifty LTP
```

---

**Created from**: `/home/palbot/Downloads/zerodhahistoricaldata/kite_trade.py` wrapper

**Note**: This is for educational purposes. Use official Kite Connect API for production trading.
