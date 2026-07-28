"""
Debug the Entry=TP bug for Gold
"""

import pandas as pd
import numpy as np

# Load Gold data
df = pd.read_csv('/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv')
df['datetime'] = pd.to_datetime(df['time'])

# Get latest bar
current_idx = len(df) - 1
current_price = df['close'].iloc[current_idx]

print("=" * 80)
print("GOLD SETUP DEBUG")
print("=" * 80)
print(f"Current bar: {current_idx}")
print(f"Current price: ${current_price:.2f}")
print(f"Time: {df['datetime'].iloc[current_idx]}")

# Detect last swing high
lookback = 8
last_swing_high = None
for i in range(lookback, current_idx):
    window = df.iloc[i-lookback:i+lookback+1]
    if df['high'].iloc[i] == window['high'].max():
        last_swing_high = {
            'idx': i,
            'price': df['high'].iloc[i],
            'anchor': df['low'].iloc[i],  # Opposite extreme
            'type': 'H'
        }

print(f"\nLast swing high:")
print(f"  Index: {last_swing_high['idx']}")
print(f"  Price (pivot): ${last_swing_high['price']:.2f}")
print(f"  Anchor (low): ${last_swing_high['anchor']:.2f}")

# Calculate effective range
mult = 0.618  # Gold config
pivot = last_swing_high['price']
anchor = last_swing_high['anchor']

eff_range = np.log10(pivot) * abs(pivot - anchor) * mult * 4

print(f"\nEffective Range Calculation:")
print(f"  log10(pivot) = log10({pivot:.2f}) = {np.log10(pivot):.4f}")
print(f"  |pivot - anchor| = |{pivot:.2f} - {anchor:.2f}| = {abs(pivot - anchor):.2f}")
print(f"  mult = {mult}")
print(f"  eff_range = {np.log10(pivot):.4f} * {abs(pivot - anchor):.2f} * {mult} * 4")
print(f"  eff_range = {eff_range:.4f}")

# Calculate Entry, TP, SL
entry_ratio = 0.5  # Gold config
tp_ratio = 1.0     # Gold config - THIS IS THE BUG!
sl_ratio = 1.618

print(f"\nPrice Levels (SHORT from swing high):")
print(f"  Entry ratio: {entry_ratio}")
print(f"  TP ratio: {tp_ratio}")
print(f"  SL ratio: {sl_ratio}")

entry_price = pivot - (entry_ratio * eff_range)
tp_price = pivot - (tp_ratio * eff_range)
sl_price = pivot + (sl_ratio * eff_range)

print(f"\n  Entry = {pivot:.2f} - ({entry_ratio} * {eff_range:.4f}) = ${entry_price:.2f}")
print(f"  TP    = {pivot:.2f} - ({tp_ratio} * {eff_range:.4f}) = ${tp_price:.2f}")
print(f"  SL    = {pivot:.2f} + ({sl_ratio} * {eff_range:.4f}) = ${sl_price:.2f}")

print(f"\n⚠️  BUG FOUND!")
print(f"   Gold config has tp=1.0, but entry=0.5")
print(f"   For SHORT trades: Entry and TP are on SAME side of pivot")
print(f"   Entry is CLOSER to pivot than TP")
print(f"   Price must pass through Entry to reach TP")
print(f"   This means TP is BEYOND entry (further down)")
print(f"\n✅ FIX: Change Gold TP to 1.272 (standard) or keep 1.0 but document it's a tight TP")

print("\n" + "=" * 80)
print("CORRECTED CALCULATION (tp=1.272)")
print("=" * 80)

tp_ratio_fixed = 1.272
tp_price_fixed = pivot - (tp_ratio_fixed * eff_range)

print(f"  Entry = ${entry_price:.2f}")
print(f"  TP    = ${tp_price_fixed:.2f} (using 1.272)")
print(f"  SL    = ${sl_price:.2f}")
print(f"\n  Risk/Reward: {(entry_price - tp_price_fixed) / (sl_price - entry_price):.2f}")
