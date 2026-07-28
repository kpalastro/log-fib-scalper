#!/usr/bin/env python3
"""
Multi-Timeframe Analysis for Gold & Silver (Yahoo Finance data)
Analyzes 5min, 30min, 1H, 4H timeframes with Log-Fib geometric patterns
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# Load data
data_dir = Path("/home/palbot/Projects/log-fib-scalper/data")

print("=" * 80)
print("📊 MULTI-TIMEFRAME ANALYSIS - GOLD & SILVER")
print("=" * 80)
print()

# ============ GOLD ANALYSIS ============
print("=" * 80)
print("🥇 GOLD (XAUUSD) ANALYSIS")
print("=" * 80)
print()

df_5min = pd.read_csv(data_dir / "YF_XAUUSD5.csv", index_col=0, parse_dates=True)
df_5min = df_5min.sort_index()

print(f"Data Range: {df_5min.index.min()} to {df_5min.index.max()}")
print(f"Total 5-min Bars: {len(df_5min):,}")
print(f"Price Range: ${df_5min['Low'].min():.2f} - ${df_5min['High'].max():.2f}")
print(f"Current Price: ${df_5min['Close'].iloc[-1]:.2f}")
print()

# Resample to higher timeframes
df_30min = df_5min.resample('30T').agg({
    'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
}).dropna()

df_1h = df_5min.resample('1H').agg({
    'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
}).dropna()

df_4h = df_5min.resample('4H').agg({
    'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
}).dropna()

print("📊 TIMEFRAME SUMMARY")
print("-" * 80)
print(f"5-minute:  {len(df_5min):,} bars | {len(df_5min)/60:.1f} hours | ~{len(df_5min)/60/24:.1f} days")
print(f"30-minute: {len(df_30min):,} bars | {len(df_30min)*30/60:.1f} hours")
print(f"1-hour:    {len(df_1h):,} bars | {len(df_1h):.1f} hours")
print(f"4-hour:    {len(df_4h):,} bars | {len(df_4h)*4:.1f} hours")
print()

def detect_swings(df, lookback=8, timeframe_name="5min"):
    """Detect swing highs and lows using pivot detection"""
    swings = []
    
    for i in range(lookback, len(df) - lookback):
        window_high = df['High'].iloc[i-lookback:i+lookback+1]
        window_low = df['Low'].iloc[i-lookback:i+lookback+1]
        
        # Swing High
        if df['High'].iloc[i] == window_high.max() and df['High'].iloc[i] > df['High'].iloc[i-1]:
            swings.append({
                'index': i,
                'time': df.index[i],
                'type': 'HIGH',
                'price': df['High'].iloc[i],
                'anchored': df['Low'].iloc[i],
                'timeframe': timeframe_name
            })
        
        # Swing Low
        if df['Low'].iloc[i] == window_low.min() and df['Low'].iloc[i] < df['Low'].iloc[i-1]:
            swings.append({
                'index': i,
                'time': df.index[i],
                'type': 'LOW',
                'price': df['Low'].iloc[i],
                'anchored': df['High'].iloc[i],
                'timeframe': timeframe_name
            })
    
    return swings

print("🔍 SWING DETECTION (Lookback=8)")
print("-" * 80)

swings_5min = detect_swings(df_5min, lookback=8, timeframe_name="5min")
swings_30min = detect_swings(df_30min, lookback=8, timeframe_name="30min")
swings_1h = detect_swings(df_1h, lookback=8, timeframe_name="1h")
swings_4h = detect_swings(df_4h, lookback=8, timeframe_name="4h")

print(f"5-min swings:  {len(swings_5min)} ({sum(1 for s in swings_5min if s['type']=='HIGH')} highs, {sum(1 for s in swings_5min if s['type']=='LOW')} lows)")
print(f"30-min swings: {len(swings_30min)}")
print(f"1H swings:     {len(swings_1h)}")
print(f"4H swings:     {len(swings_4h)}")
print()

# Log-Fib calculations
print("📐 LOG-FIB GEOMETRIC PROJECTIONS")
print("-" * 80)

# Get recent swings for each timeframe
recent_5min = [s for s in swings_5min if s['index'] > len(df_5min) - 100][-5:]
recent_30min = [s for s in swings_30min if s['index'] > len(df_30min) - 50][-5:]

if recent_5min:
    print("\n5-minute timeframe:")
    for swing in recent_5min[-3:]:
        pivot = swing['price']
        anchor = swing['anchored']
        log_range = np.log10(pivot) * abs(pivot - anchor)
        
        # Core formula: effective_range = log10(pivot) * |pivot - anchor| * mult * 4
        for mult in [0.382, 0.5, 0.618]:
            eff_range = log_range * mult * 4
            
            if swing['type'] == 'HIGH':
                entry = pivot - (0.382 * eff_range)
                tp = pivot - (1.272 * eff_range)
                sl = pivot + (1.618 * eff_range)
                direction = "SHORT"
            else:
                entry = pivot + (0.382 * eff_range)
                tp = pivot + (1.272 * eff_range)
                sl = pivot - (1.618 * eff_range)
                direction = "LONG"
            
            print(f"  {swing['type']} @ ${pivot:.2f} (anchored: ${anchor:.2f})")
            print(f"    mult={mult}: {direction} Entry ${entry:.2f} | TP ${tp:.2f} | SL ${sl:.2f}")

print()

# Confluence analysis
print("🎯 MULTI-TIMEFRAME CONFLUENCE")
print("-" * 80)

current_price = df_5min['Close'].iloc[-1]
print(f"Current Gold Price: ${current_price:.2f}")
print()

# Find key levels from each timeframe
def get_key_levels(swings, df):
    """Get key support/resistance levels from swings"""
    levels = []
    for swing in swings[-10:]:
        levels.append(swing['price'])
    return sorted(set(round(l, 2) for l in levels))

levels_5min = get_key_levels(swings_5min, df_5min)
levels_30min = get_key_levels(swings_30min, df_30min)
levels_1h = get_key_levels(swings_1h, df_1h)

print("Key Levels by Timeframe:")
print(f"  5-min:  {levels_5min[-5:]}")
print(f"  30-min: {levels_30min[-5:]}")
print(f"  1H:     {levels_1h[-5:]}")

# Find confluence zones (levels within $2 of each other)
print("\nConfluence Zones (±$2):")
all_levels = levels_5min + levels_30min + levels_1h
confluence = []
for i, l1 in enumerate(all_levels):
    count = 1
    timeframes = set()
    if l1 in levels_5min: timeframes.add('5min')
    if l1 in levels_30min: timeframes.add('30min')
    if l1 in levels_1h: timeframes.add('1h')
    
    for l2 in all_levels[i+1:]:
        if abs(l1 - l2) <= 2:
            count += 1
            if l2 in levels_5min: timeframes.add('5min')
            if l2 in levels_30min: timeframes.add('30min')
            if l2 in levels_1h: timeframes.add('1h')
    
    if count >= 2 and len(timeframes) >= 2:
        confluence.append((round(l1, 2), count, tuple(sorted(timeframes))))

confluence = list(set(confluence))
for level, count, tfs in sorted(confluence, key=lambda x: abs(x[0] - current_price))[:5]:
    print(f"  ${level:.2f} - {count} touches across {', '.join(tfs)}")

print()

# ============ SILVER ANALYSIS ============
print("=" * 80)
print("🥈 SILVER (XAGUSD) ANALYSIS")
print("=" * 80)
print()

df_5min_ag = pd.read_csv(data_dir / "YF_XAGUSD5.csv", index_col=0, parse_dates=True)
df_5min_ag = df_5min_ag.sort_index()

print(f"Data Range: {df_5min_ag.index.min()} to {df_5min_ag.index.max()}")
print(f"Total 5-min Bars: {len(df_5min_ag):,}")
print(f"Price Range: ${df_5min_ag['Low'].min():.2f} - ${df_5min_ag['High'].max():.2f}")
print(f"Current Price: ${df_5min_ag['Close'].iloc[-1]:.2f}")
print()

# Resample
df_30min_ag = df_5min_ag.resample('30T').agg({
    'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
}).dropna()

df_1h_ag = df_5min_ag.resample('1H').agg({
    'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
}).dropna()

print("📊 TIMEFRAME SUMMARY")
print("-" * 80)
print(f"5-minute:  {len(df_5min_ag):,} bars")
print(f"30-minute: {len(df_30min_ag):,} bars")
print(f"1-hour:    {len(df_1h_ag):,} bars")
print()

print("🔍 SWING DETECTION")
print("-" * 80)
swings_ag_5min = detect_swings(df_5min_ag, lookback=8, timeframe_name="5min")
swings_ag_30min = detect_swings(df_30min_ag, lookback=8, timeframe_name="30min")

print(f"5-min swings:  {len(swings_ag_5min)}")
print(f"30-min swings: {len(swings_ag_30min)}")
print()

print("📐 LOG-FIB PROJECTIONS (Silver)")
print("-" * 80)

recent_ag = [s for s in swings_ag_5min if s['index'] > len(df_5min_ag) - 100][-3:]
if recent_ag:
    for swing in recent_ag:
        pivot = swing['price']
        anchor = swing['anchored']
        log_range = np.log10(pivot) * abs(pivot - anchor)
        mult = 0.618
        eff_range = log_range * mult * 4
        
        if swing['type'] == 'HIGH':
            entry = pivot - (0.382 * eff_range)
            tp = pivot - (1.272 * eff_range)
            sl = pivot + (1.618 * eff_range)
            direction = "SHORT"
        else:
            entry = pivot + (0.382 * eff_range)
            tp = pivot + (1.272 * eff_range)
            sl = pivot - (1.618 * eff_range)
            direction = "LONG"
        
        print(f"  {swing['type']} @ ${pivot:.2f}")
        print(f"    {direction}: Entry ${entry:.2f} | TP ${tp:.2f} | SL ${sl:.2f}")

print()
print("=" * 80)
print("✅ ANALYSIS COMPLETE")
print("=" * 80)
