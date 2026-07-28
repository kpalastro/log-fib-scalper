"""
Simple analysis - why LONG/SHORT flipping?
"""

import pandas as pd

# Load 1-minute Gold data
df = pd.read_csv('/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv')

print("=" * 80)
print("GOLD WHIPSAW ANALYSIS - WHY LONG/SHORT FLIPPING?")
print("=" * 80)

print(f"\nData: {len(df)} bars (1-minute candles)")
print(f"Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
print(f"Total range: ${df['high'].max() - df['low'].min():.2f} ({(df['high'].max() - df['low'].min())/df['low'].min()*100:.2f}%)")

print("\n" + "=" * 80)
print("THE PROBLEM")
print("=" * 80)
print("""
1-minute data creates TOO MANY swings with lookback=8:
- Lookback=8 on 1-min = 8-minute swing window (TOO SHORT!)
- Market oscillates in tight range (~$10-15 on Gold)
- Each small swing triggers opposite signal
- Results in LONG/SHORT whipsaw

Example from your alerts:
  16:50 LONG @ 4554 (Markov=HL pattern)
  17:04 SHORT @ 4548 (Markov=LH pattern) ← 14 min later!
  17:07 LONG @ 4551 (Markov=HL pattern) ← 3 min later!
  
This is MARKET NOISE, not real geometric setups.
""")

print("=" * 80)
print("SOLUTIONS")
print("=" * 80)
print("""
OPTION 1: Use 5-minute data (RECOMMENDED)
  - More stable swings
  - Less noise
  - Fewer false signals
  Command: python data/yahoo_live_fetcher.py --interval 5m

OPTION 2: Increase lookback for 1-min data
  - Change lookback from 8 to 20-30
  - Creates longer swing windows
  - File: strategies/geometric_confluence_scalper.py

OPTION 3: Add minimum score threshold
  - Only alert if score >= 65 (not 50)
  - Filters weak setups
  - File: scanner/real_time_scanner.py

OPTION 4: Add cooldown period
  - Don't alert opposite direction within 30 min
  - Prevents whipsaw
""")

print("\n" + "=" * 80)
print("RECOMMENDED FIX")
print("=" * 80)
print("""
Change cron job to use 5-minute data instead of 1-minute:

Current (1-min, noisy):
  Schedule: */1 * * * *
  Interval: 1m

Recommended (5-min, stable):
  Schedule: */5 * * * *
  Interval: 5m

This matches the original backtested configuration and reduces noise.
""")
