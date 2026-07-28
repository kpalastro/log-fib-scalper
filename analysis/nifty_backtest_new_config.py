"""
Quick backtest of Nifty50 with NEW optimal parameters (mult=0.1)
"""

import pandas as pd
import numpy as np
import sys
sys.path.insert(0, '/home/palbot/Projects/log-fib-scalper/strategies')

from geometric_confluence_scalper import GeometricConfluenceScalper, OPTIMAL_CONFIGS

# Load Nifty data
df = pd.read_csv('/home/palbot/Projects/log-fib-scalper/zerodha_data/NIFTY_50_5minute_20260319_20260518.csv')
if 'date' in df.columns:
    df['datetime'] = pd.to_datetime(df['date'])
    df['time'] = df['datetime']  # Also add 'time' alias
df = df.dropna(subset=['high', 'low']).reset_index(drop=True)

print("=" * 80)
print("NIFTY50 BACKTEST - NEW OPTIMAL CONFIG (mult=0.1)")
print("=" * 80)

config = OPTIMAL_CONFIGS['nifty']['best']
print(f"\nConfiguration: {config}")

scalper = GeometricConfluenceScalper('nifty', config)
result = scalper._full_backtest(df)

print(f"\n📊 BACKTEST RESULTS")
print(f"  Total Trades: {result['stats'].get('total_trades', 0)}")
print(f"  Win Rate: {result['stats'].get('win_rate', 0):.2f}%")
print(f"  Profit Factor: {result['stats'].get('profit_factor', 0):.2f}")
print(f"  Total P&L: {result['stats'].get('total_pnl', 0):.4f}")

print(f"\n🎯 CONFLUENCE ANALYSIS")
print(f"  High Confluence (≥70): {result['stats'].get('high_confluence_trades', 0)} trades, {result['stats'].get('high_confluence_wr', 0):.1f}% WR")
print(f"  Medium Confluence (50-69): {result['stats'].get('med_confluence_trades', 0)} trades, {result['stats'].get('med_confluence_wr', 0):.1f}% WR")

# Show example trades
if result['trades']:
    print(f"\n📋 EXAMPLE TRADES (First 5):")
    for i, trade in enumerate(result['trades'][:5]):
        print(f"\n  Trade {i+1}:")
        print(f"    Bar {trade['entry_idx']}: {trade['direction']} @ {trade['entry_price']:.2f}")
        print(f"    Confluence Score: {trade['confluence_score']:.1f}")
        # Print all available keys
        print(f"    Keys: {list(trade.keys())}")
