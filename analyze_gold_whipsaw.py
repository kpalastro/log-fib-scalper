"""
Analyze the Gold whipsaw alerts - why LONG/SHORT flipping?
"""

import pandas as pd
import numpy as np

# Load 1-minute Gold data
df = pd.read_csv('/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv')
df['datetime'] = pd.to_datetime(df['time'])

print("=" * 80)
print("GOLD PRICE ACTION ANALYSIS (1-minute data)")
print("=" * 80)
print(f"Total bars: {len(df)}")
print(f"Range: {df['datetime'].min()} to {df['datetime'].max()}")
print(f"Price: ${df['close'].iloc[0]:.2f} → ${df['close'].iloc[-1]:.2f}")

# Show price action around alert times
print("\n" + "=" * 80)
print("PRICE ACTION DURING ALERTS")
print("=" * 80)

alert_times = [
    ('16:15:02 SHORT', '2026-05-19 06:32:00'),  # Bar 152
    ('16:50:17 LONG', '2026-05-19 06:42:00'),   # Bar 159
    ('17:04:05 SHORT', '2026-05-19 06:46:00'),  # Bar 173
    ('17:07:57 LONG', '2026-05-19 06:47:00'),   # Bar 177
]

for alert_name, time_str in alert_times:
    # Find closest bar
    target_time = pd.to_datetime(time_str)
    idx = (df['datetime'] - target_time).abs().argmin()
    
    print(f"\n{alert_name} (bar {idx}):")
    print(f"  Time: {df['datetime'].iloc[idx]}")
    print(f"  Price: ${df['close'].iloc[idx]:.2f}")
    print(f"  High: ${df['high'].iloc[idx]:.2f}, Low: ${df['low'].iloc[idx]:.2f}")
    
    # Show 5 bars before and after
    start = max(0, idx - 5)
    end = min(len(df), idx + 6)
    
    print(f"  Context (5 bars before/after):")
    for i in range(start, end):
        marker = "← ALERT" if i == idx else ""
        direction = "↑" if df['close'].iloc[i] > df['open'].iloc[i] else "↓"
        print(f"    Bar {i:3d} {df['datetime'].iloc[i].strftime('%H:%M')} ${df['close'].iloc[i]:7.2f} {direction} {marker}")

# Detect swings
print("\n" + "=" * 80)
print("SWING DETECTION (lookback=8 on 1-min data)")
print("=" * 80)

lookback = 8
swing_highs = []
swing_lows = []

for i in range(lookback, len(df) - lookback):
    window = df.iloc[i-lookback:i+lookback+1]
    
    if df['high'].iloc[i] == window['high'].max():
        swing_highs.append({'idx': i, 'price': df['high'].iloc[i], 'type': 'H'})
    
    if df['low'].iloc[i] == window['low'].min():
        swing_lows.append({'idx': i, 'price': df['low'].iloc[i], 'type': 'L'})

print(f"Swing Highs: {len(swing_highs)}")
print(f"Swing Lows: {len(swing_lows)}")

# Show recent swings
print("\nRecent swings (last 10):")
all_swings = sorted(swing_highs + swing_lows, key=lambda x: x['idx'])[-10:]
for swing in all_swings:
    time_str = df['datetime'].iloc[swing['idx']].strftime('%H:%M:%S')
    print(f"  Bar {swing['idx']:3d} {time_str} - {swing['type']} @ ${swing['price']:.2f}")

# Check for swing flips
print("\n" + "=" * 80)
print("SWING FLIP ANALYSIS")
print("=" * 80)

for i in range(len(all_swings) - 1):
    s1 = all_swings[i]
    s2 = all_swings[i + 1]
    
    bar_diff = s2['idx'] - s1['idx']
    price_diff = abs(s2['price'] - s1['price']) / s1['price'] * 100
    
    if bar_diff < 10:  # Swings within 10 bars
        print(f"⚠️ RAPID SWING FLIP: {s1['type']}@{s1['idx']} → {s2['type']}@{s2['idx']} ({bar_diff} bars, {price_diff:.3f}%)")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("""
The LONG/SHORT flipping is caused by:

1. **1-minute data is NOISY** - lots of small swings forming
2. **Lookback=8 on 1-min** = only 8-minute window (too short!)
3. **Markov pattern flips** - HL → LH → HL as swings form rapidly
4. **Whipsaw market** - price oscillating in tight range

SOLUTIONS:
- Use 5-minute data instead of 1-minute (less noise)
- Increase lookback for 1-min (e.g., lookback=20 for 20-minute swings)
- Add minimum score threshold (only alert if score >= 65)
- Add time filter (don't alert opposite direction within N minutes)
""")
