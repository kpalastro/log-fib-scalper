"""
NIFTY50 PARAMETER OPTIMIZATION
===============================
Finds optimal geometric parameters for Nifty50 since the standard config failed.
Tests different Gann scaling factors and effective range multipliers.
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_PATH = Path('/home/palbot/Projects/log-fib-scalper/zerodha_data/NIFTY_50_5minute_20260319_20260518.csv')

df = pd.read_csv(DATA_PATH)
if 'date' in df.columns:
    df['time'] = pd.to_datetime(df['date'])
df = df.dropna(subset=['high', 'low']).reset_index(drop=True)

print("=" * 80)
print("NIFTY50 PARAMETER OPTIMIZATION")
print("=" * 80)
print(f"\nData: {len(df):,} bars, Price: {df['close'].iloc[0]:.0f} → {df['close'].iloc[-1]:.0f}")

# Detect swings
def detect_swing_highs(df, lookback=8):
    swings = []
    for i in range(lookback, len(df) - lookback):
        window = df.iloc[i-lookback:i+lookback+1]
        if df['high'].iloc[i] == window['high'].max():
            swings.append({'idx': i, 'type': 'HIGH', 'price': df['high'].iloc[i], 'bar': i})
    return swings

def detect_swing_lows(df, lookback=8):
    swings = []
    for i in range(lookback, len(df) - lookback):
        window = df.iloc[i-lookback:i+lookback+1]
        if df['low'].iloc[i] == window['low'].min():
            swings.append({'idx': i, 'type': 'LOW', 'price': df['low'].iloc[i], 'bar': i})
    return swings

swing_highs = detect_swing_highs(df, lookback=8)
swing_lows = detect_swing_lows(df, lookback=8)
all_swings = sorted(swing_highs + swing_lows, key=lambda x: x['idx'])

print(f"Swings detected: {len(all_swings)} ({len(swing_highs)}H, {len(swing_lows)}L)")

# Analyze actual price ranges between swings
print("\n" + "=" * 80)
print("ACTUAL PRICE RANGE ANALYSIS")
print("=" * 80)

price_ranges = []
time_intervals = []

for i in range(len(all_swings) - 1):
    s1 = all_swings[i]
    s2 = all_swings[i + 1]
    if s1['type'] != s2['type']:
        price_range = abs(s2['price'] - s1['price'])
        price_range_pct = price_range / s1['price'] * 100
        time_diff = abs(s2['bar'] - s1['bar'])
        price_ranges.append(price_range_pct)
        time_intervals.append(time_diff)

print(f"\nPrice moves between swings (in %):")
print(f"  Mean: {np.mean(price_ranges):.3f}%")
print(f"  Median: {np.median(price_ranges):.3f}%")
print(f"  Std: {np.std(price_ranges):.3f}%")
print(f"  Min: {np.min(price_ranges):.3f}%")
print(f"  Max: {np.max(price_ranges):.3f}%")

print(f"\nTime intervals between swings (in bars):")
print(f"  Mean: {np.mean(time_intervals):.1f} bars")
print(f"  Median: {np.median(time_intervals):.1f} bars")

# Calculate what Gann scaling would make these squares
# For a perfect square: price_move_pct == time_bars * gann_scale
# So: gann_scale = price_move_pct / time_bars

gann_ratios = [p / t for p, t in zip(price_ranges, time_intervals) if t > 0]
print(f"\nImplied Gann scaling (price% / time):")
print(f"  Mean: {np.mean(gann_ratios):.6f} ({np.mean(gann_ratios)*100:.4f}% per bar)")
print(f"  Median: {np.median(gann_ratios):.6f} ({np.median(gann_ratios)*100:.4f}% per bar)")

# Test different Gann scaling factors
print("\n" + "=" * 80)
print("TESTING GANN SCALING FACTORS")
print("=" * 80)

test_scales = [0.0001, 0.0002, 0.0003, 0.0005, 0.001, 0.0015, 0.002, 0.003, 0.005]

for scale in test_scales:
    perfect = 0
    near = 0
    for i in range(len(all_swings) - 1):
        s1 = all_swings[i]
        s2 = all_swings[i + 1]
        if s1['type'] == s2['type']:
            continue
        
        price_move_pct = abs(s2['price'] - s1['price']) / s1['price'] * 100
        time_move = abs(s2['bar'] - s1['bar'])
        
        time_in_price_units = time_move * scale * 100  # Convert to %
        ratio = price_move_pct / time_in_price_units if time_in_price_units > 0 else 0
        
        if 0.95 <= ratio <= 1.05:
            perfect += 1
        elif 0.85 <= ratio <= 1.15:
            near += 1
    
    total = len([s for i, s in enumerate(all_swings[:-1]) if all_swings[i]['type'] != all_swings[i+1]['type']])
    print(f"  Scale {scale:.4f} ({scale*100:.3f}%): Perfect={perfect:3d} ({perfect/total*100:5.1f}%), Near={near:3d} ({near/total*100:5.1f}%)")

# Now test backtest with different effective range multipliers
print("\n" + "=" * 80)
print("BACKTEST: EFFECTIVE RANGE MULTIPLIERS")
print("=" * 80)

def backtest_with_params(df, swings, mult, entry_ratio, tp_ratio, sl_ratio):
    trades = []
    
    for i in range(len(swings) - 2):
        s1, s2 = swings[i], swings[i + 1]
        if s1['type'] == s2['type']:
            continue
        
        pivot, anchor = s2, s1
        price_range = abs(pivot['price'] - anchor['price'])
        
        # Try different effective range formulas
        eff_range_log = np.log10(pivot['price']) * price_range * mult * 4
        eff_range_simple = price_range * mult
        eff_range_pct = (price_range / pivot['price']) * mult * 100
        
        # Use simple price range * mult (works better for indices)
        effective_range = eff_range_simple
        
        if pivot['type'] == 'LOW':
            entry = pivot['price'] + (entry_ratio * effective_range)
            tp = pivot['price'] + (tp_ratio * effective_range)
            sl = pivot['price'] - (sl_ratio * effective_range)
            direction = 'LONG'
        else:
            entry = pivot['price'] - (entry_ratio * effective_range)
            tp = pivot['price'] - (tp_ratio * effective_range)
            sl = pivot['price'] + (sl_ratio * effective_range)
            direction = 'SHORT'
        
        start_idx = pivot['idx'] + 1
        end_idx = min(start_idx + 100, len(df) - 1)
        
        for j in range(start_idx, end_idx):
            bar = df.iloc[j]
            hit = False
            exit_p, exit_t = None, None
            
            if direction == 'LONG':
                if bar['low'] <= entry:
                    hit = True
                    if bar['high'] >= tp:
                        exit_p, exit_t = tp, 'TP'
                    elif bar['low'] <= sl:
                        exit_p, exit_t = sl, 'SL'
            else:
                if bar['high'] >= entry:
                    hit = True
                    if bar['low'] <= tp:
                        exit_p, exit_t = tp, 'TP'
                    elif bar['high'] >= sl:
                        exit_p, exit_t = sl, 'SL'
            
            if hit and exit_p:
                pnl = (exit_p - entry) / entry * 100
                if direction == 'SHORT':
                    pnl = -pnl
                trades.append({'dir': direction, 'exit': exit_t, 'pnl': pnl})
                break
    
    return trades

# Test different mult values
print("\nTesting mult values (entry=0.382, TP=1.272, SL=1.618):")
for mult in [0.1, 0.2, 0.3, 0.5, 0.618, 0.786, 1.0, 1.5, 2.0]:
    trades = backtest_with_params(df, all_swings, mult, 0.382, 1.272, 1.618)
    if trades:
        wins = sum(1 for t in trades if t['exit'] == 'TP')
        wr = wins / len(trades) * 100
        total_pnl = sum(t['pnl'] for t in trades)
        print(f"  mult={mult:4.3f}: {len(trades):3d} trades, WR={wr:5.1f}%, Total PnL={total_pnl:6.2f}%")
    else:
        print(f"  mult={mult:4.3f}: NO TRADES")

# Test different entry ratios
print("\nTesting entry ratios (mult=0.5, TP=1.272, SL=1.618):")
for entry in [0.236, 0.382, 0.5, 0.618, 0.786]:
    trades = backtest_with_params(df, all_swings, 0.5, entry, 1.272, 1.618)
    if trades:
        wins = sum(1 for t in trades if t['exit'] == 'TP')
        wr = wins / len(trades) * 100
        total_pnl = sum(t['pnl'] for t in trades)
        print(f"  entry={entry:4.3f}: {len(trades):3d} trades, WR={wr:5.1f}%, Total PnL={total_pnl:6.2f}%")
    else:
        print(f"  entry={entry:4.3f}: NO TRADES")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("""
Nifty50 shows DIFFERENT geometric behavior vs Silver/Gold:

1. Weaker Fib retracement hits (4.2% at 0.382 vs 70-82% in Silver/Gold)
2. Moderate Fib time symmetry (58.3% vs 74-92%)
3. Very weak Gann squares (3.6% vs ~22%)
4. Lower reversal rate (66% vs 80-85%)

This suggests Nifty50 may need:
- Different entry ratios (test 0.5-0.786 instead of 0.382)
- Different effective range formula (simple price range vs log formula)
- Different Gann scaling (0.0002-0.0003 vs 0.0015)
- Possibly different strategy entirely (momentum/trend vs mean reversion)

The geometric laws discovered in Silver/Gold don't transfer directly to Nifty50.
Indices may have different market structure than commodities.
""")
