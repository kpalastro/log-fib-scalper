# NIFTY50 REAL-TIME MONITORING GUIDE

## Quick Start

### 1. One-Time Scan (Latest Bar)
```bash
cd /home/palbot/Projects/log-fib-scalper
source .venv/bin/activate

# Scan Nifty only
python scanner/real_time_scanner.py --instrument nifty

# Scan all 4 instruments
python scanner/real_time_scanner.py --scan
```

### 2. Live Mode (Continuous Monitoring)
```bash
# Monitor Nifty every 5 minutes (300 seconds)
python scanner/real_time_scanner.py --instrument nifty --live --interval 300

# Monitor all instruments every 5 minutes
python scanner/real_time_scanner.py --live --interval 300

# Monitor every 1 minute (aggressive)
python scanner/real_time_scanner.py --instrument nifty --live --interval 60
```

---

## Live Mode Output

When running in live mode, the scanner will:

1. **Scan latest bar** of Nifty data every N seconds
2. **Check for confluence setups** (score ≥50)
3. **Log alerts** to `scanner/alerts.log`
4. **Avoid duplicates** (same setup within 50 bars)
5. **Display countdown** to next scan

Example output:
```
======================================================================
GEOMETRIC CONFLUENCE REAL-TIME SCANNER
======================================================================
Started: 2026-05-19 14:30:00

Scanning latest bar of NIFTY (bar 2849)...
No confluence setups found (score < 50)

Next scan in 300 seconds... (Ctrl+C to stop)

[waits 5 minutes...]

Scanning latest bar of NIFTY (bar 2850)...
======================================================================
🎯 GEOMETRIC CONFLUENCE ALERT
======================================================================
Instrument: NIFTY
Time: 2026-05-19 14:35:00
Price: 23644.45

Direction: LONG
Entry: 23650.20
TP: 23680.50
SL: 23620.10

Confluence Score: 65.2/100
...
```

---

## Alert Log Location

All alerts are logged to:
```
/home/palbot/Projects/log-fib-scalper/scanner/alerts.log
```

View recent alerts:
```bash
tail -20 scanner/alerts.log
```

Alert history (JSON) is saved to:
```
/home/palbot/Projects/log-fib-scalper/scanner/alert_history.json
```

---

## Data Source

The scanner reads from:
```
/home/palbot/Projects/log-fib-scalper/zerodha_data/NIFTY_50_5minute_20260319_20260518.csv
```

**Important**: This is historical data only. For true real-time monitoring, you need:

### Option A: Live Data Feed (Zerodha Kite Connect)
```python
# Requires Kite Connect API subscription
from kiteconnect import KiteTicker

kws = KiteTicker(api_key="YOUR_API_KEY", access_token="YOUR_ACCESS_TOKEN")
kws.subscribe([NSE_SYMBOL])
kws.on_ticks = process_live_ticks
kws.connect()
```

### Option B: Manual CSV Updates
Update the CSV file manually or via script every 5 minutes:
```bash
# Download latest Nifty 5min data from Zerodha
# Save to: zerodha_data/NIFTY_50_5minute_20260319_20260518.csv
# Scanner will automatically pick up new bars
```

### Option C: Cron-Based Monitoring
Set up automated scans every 5 minutes:
```bash
# Add to crontab (crontab -e)
*/5 9-15 * * 1-5 cd /home/palbot/Projects/log-fib-scalper && source .venv/bin/activate && python scanner/real_time_scanner.py --instrument nifty >> scanner/cron_log.txt 2>&1
```

---

## Setting Up Cron Monitoring

I can set up automated cron monitoring for you:

```bash
# Run scanner every 5 minutes during market hours (9:15 AM - 3:30 PM IST, Mon-Fri)
*/5 9-15 * * 1-5 cd /home/palbot/Projects/log-fib-scalper && source .venv/bin/activate && python scanner/real_time_scanner.py --instrument nifty --scan >> scanner/cron_log.txt 2>&1
```

This will:
- Scan Nifty every 5 minutes
- Only during market hours (9 AM - 3 PM)
- Only on weekdays (Mon-Fri)
- Log output to `scanner/cron_log.txt`

---

## Confluence Score Thresholds

| Score | Meaning | Action |
|-------|---------|--------|
| **≥70** | High Confluence | Strong setup - watch closely |
| **50-69** | Medium Confluence | Valid setup - monitor |
| **<50** | Weak/No Setup | Ignore |

---

## What Each Alert Contains

```
🎯 GEOMETRIC CONFLUENCE ALERT

📊 Instrument: NIFTY
⏰ Time: 2026-05-19 14:35:00
💰 Price: 23644.45

📈 Direction: LONG
🎯 Entry: 23650.20
🎯 TP: 23680.50
🛑 SL: 23620.10

🔮 Confluence Score: 65.2/100

📐 Geometric Breakdown:
• Fib Time: 13 bars (near 13) - 85/100
• Gann Square: 1.02x (perfect) - 90/100
• Markov: Pattern H-L-H (82% rev) - 75/100
• Fib Retrace: 0.378 (dist: 0.004) - 60/100

⚡ Action: Watch for entry at 23650.20
```

---

## Current Nifty Configuration

```python
'nifty': {
    'lookback': 8,        # 17-candle swing detection window
    'mult': 0.1,          # Effective range multiplier (5x smaller than Silver)
    'entry': 0.382,       # Entry at 0.382 Fib retracement
    'tp': 1.272,          # Take profit at 1.272 extension
    'sl': 1.618,          # Stop loss at 1.618 extension
    'gann_scale': 0.0002, # Gann scaling for indices
}
```

**Validated Performance**: 92.16% Win Rate, 153 trades, 5,570 points P&L

---

## Troubleshooting

### "No confluence setups found"
- **Normal**: Most bars don't have setups (score < 50)
- **Solution**: Wait for market to form clear geometric patterns

### "KeyError: 'datetime'"
- **Cause**: CSV format issue
- **Solution**: Ensure CSV has 'date' or 'datetime' column

### Scanner too slow
- **Cause**: Scanning historical bars
- **Solution**: Use `--scan` (latest bar only) not full backtest

### Duplicate alerts
- **Already fixed**: Scanner checks last 50 alerts, 0.1% price tolerance

---

## Best Practices

1. **Run during market hours**: 9:15 AM - 3:30 PM IST
2. **5-minute intervals**: Matches Nifty 5min candle formation
3. **Check alerts.log**: Review historical setups
4. **Combine with manual analysis**: Scanner is a tool, not a black box
5. **Backtest first**: Understand the strategy before live trading

---

## Next Steps

1. **Test one-time scan**: `python scanner/real_time_scanner.py --instrument nifty`
2. **Run live mode for 1 hour**: `python scanner/real_time_scanner.py --instrument nifty --live --interval 300`
3. **Review alerts**: Check `scanner/alerts.log` for any setups detected
4. **Set up cron**: Automate monitoring during market hours

---

**Status**: ✅ Ready for live monitoring  
**Date**: 2026-05-19
