# Scanner Duplicate Alert Fix

## Problem
The scanner was generating multiple alerts for the same trade setup because:
1. It scanned every bar in the dataset
2. Geometric confluence conditions can persist for 20-50+ bars while price hovers near the 0.382 entry level
3. The old duplicate check only looked at the last 10 alerts within 5 bars

### Example of Duplicate Alerts (BEFORE):
```
2026-05-18T02:55:00 - LONG @ 75.6393 (Score: 55.5)
2026-05-18T03:20:00 - LONG @ 75.6393 (Score: 55.5)  ← Same setup!
2026-05-18T03:45:00 - LONG @ 75.9250 (Score: 65.5)  ← Same setup!
2026-05-18T04:05:00 - SHORT @ 75.8828 (Score: 65.5) ← New setup
```

## Solution

### 1. Improved Duplicate Detection
The scanner now checks:
- **Same instrument** (silver/gold)
- **Same direction** (LONG/SHORT)
- **Same entry price** (within 0.1% tolerance)
- **Within 50 bars** (same swing setup)

```python
def is_duplicate_alert(self, signal: dict) -> bool:
    for prev in self.alert_history[-50:]:
        if (prev['instrument'] == self.instrument and
            prev['direction'] == signal['direction'] and
            abs(prev['entry'] - signal['entry_price']) / signal['entry_price'] < 0.001 and
            signal['bar'] - prev['bar'] < 50):
            return True  # Duplicate
    return False
```

### 2. Scan Only Latest Bar
Changed from scanning 100 bars to scanning **only the latest bar**:
- Much faster (instant vs minutes)
- No historical duplicates
- Real-time focus

### 3. Skip Message for Active Setups
When a setup is already active, the scanner prints:
```
[SKIP] SILVER LONG @ 76.1548 - Setup already active (Score: 55.5)
```

## Usage

### Scan Current Bar (Recommended)
```bash
# Scan all instruments (Silver, Gold, Nifty, BankNifty)
python scanner/real_time_scanner.py --scan

# Scan specific instrument
python scanner/real_time_scanner.py --instrument silver
python scanner/real_time_scanner.py --instrument nifty
python scanner/real_time_scanner.py --instrument banknifty
```

### Live Mode (Continuous Monitoring)
```bash
# Scan every 5 minutes
python scanner/real_time_scanner.py --live --interval 300
```

## Alert Output

### When NEW Setup Detected:
```
======================================================================
🎯 GEOMETRIC CONFLUENCE ALERT
======================================================================
Instrument: SILVER
Time: 2026-05-18T04:05:00
Price: 75.8995

Direction: SHORT
Entry: 75.8828
TP: 74.9285
SL: 78.0273

Confluence Score: 65.5/100

Geometric Breakdown:
  Fib Time: 7 bars (near 8)
  Gann Ratio: 1.36x (2x1 Time Speed)
  Markov Pattern: LH (82% reversal prob)
  Fib Retracement: 1.380 (dist to 0.382: 0.998)
======================================================================
```

### When Setup Already Active:
```
[SKIP] SILVER SHORT @ 75.9250 - Setup already active (Score: 65.5)
```

## Files Modified
- `scanner/real_time_scanner.py` - Fixed duplicate detection and scan logic
- `scanner/alert_history.json` - Stores last 1000 alerts for deduplication
- `scanner/alerts.log` - Human-readable alert log

## Testing
```bash
# Clear history and test
rm scanner/alert_history.json scanner/alerts.log
python scanner/real_time_scanner.py --scan
```

## Expected Behavior
- **1 alert per unique setup** (not per bar)
- **No alerts** if confluence conditions not met on latest bar
- **Fast execution** (< 1 second per instrument)
- **Automatic deduplication** for 50 bars or ~4 hours on 5min chart
