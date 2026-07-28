"""
NIFTY50: OLD vs NEW CONFIGURATION COMPARISON
Compares Silver config (mult=0.5) vs Nifty-optimal config (mult=0.1)
"""

import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/home/palbot/Projects/log-fib-scalper/strategies')

from geometric_confluence_scalper import GeometricConfluenceScalper

# Load Nifty data
df = pd.read_csv('/home/palbot/Projects/log-fib-scalper/zerodha_data/NIFTY_50_5minute_20260319_20260518.csv')
if 'date' in df.columns:
    df['datetime'] = pd.to_datetime(df['date'])
    df['time'] = df['datetime']
df = df.dropna(subset=['high', 'low']).reset_index(drop=True)

print("=" * 80)
print("NIFTY50: OLD vs NEW CONFIGURATION COMPARISON")
print("=" * 80)

configs = {
    'OLD (Silver config)': {'lookback': 8, 'mult': 0.5, 'entry': 0.382, 'tp': 1.272, 'sl': 1.618},
    'NEW (Nifty-optimal)': {'lookback': 8, 'mult': 0.1, 'entry': 0.382, 'tp': 1.272, 'sl': 1.618},
}

results = []

for name, config in configs.items():
    print(f"\n{'='*80}")
    print(f"{name}: {config}")
    print('='*80)
    
    scalper = GeometricConfluenceScalper('nifty', config)
    result = scalper._full_backtest(df)
    
    stats = result['stats']
    results.append({
        'name': name,
        'trades': stats.get('total_trades', 0),
        'wins': int(stats.get('win_rate', 0) * stats.get('total_trades', 0) / 100),
        'wr': stats.get('win_rate', 0),
        'pf': stats.get('profit_factor', 0),
        'pnl': stats.get('total_pnl', 0),
    })
    
    print(f"\n📊 RESULTS:")
    print(f"  Trades: {stats.get('total_trades', 0)}")
    print(f"  Win Rate: {stats.get('win_rate', 0):.2f}%")
    print(f"  Profit Factor: {stats.get('profit_factor', 0):.2f}")
    print(f"  Total P&L: {stats.get('total_pnl', 0):.2f} points")

# Summary table
print("\n" + "=" * 80)
print("SUMMARY COMPARISON")
print("=" * 80)
print(f"\n{'Metric':<20} | {'OLD (mult=0.5)':<15} | {'NEW (mult=0.1)':<15} | {'Change':<15}")
print("-" * 80)

old = results[0]
new = results[1]

print(f"{'Trades':<20} | {old['trades']:>15} | {new['trades']:>15} | {new['trades'] - old['trades']:>+15}")
print(f"{'Win Rate (%)':<20} | {old['wr']:>15.2f} | {new['wr']:>15.2f} | {new['wr'] - old['wr']:>+15.2f}")
print(f"{'Profit Factor':<20} | {old['pf']:>15.2f} | {new['pf']:>15.2f} | {new['pf'] - old['pf']:>+15.2f}")
print(f"{'Total P&L (pts)':<20} | {old['pnl']:>15.2f} | {new['pnl']:>15.2f} | {new['pnl'] - old['pnl']:>+15.2f}")

print("\n" + "=" * 80)
print("VERDICT")
print("=" * 80)

if new['wr'] > old['wr'] and new['pf'] > old['pf'] and new['pnl'] > old['pnl']:
    print("\n✅ NEW CONFIG IS SUPERIOR in ALL metrics!")
    print(f"   +{new['wr'] - old['wr']:.1f}% Win Rate")
    print(f"   +{new['pf'] - old['pf']:.2f} Profit Factor")
    print(f"   +{new['pnl'] - old['pnl']:.2f} points P&L")
else:
    print("\n⚠️ Mixed results - review trade-offs")

print("\n" + "=" * 80)
