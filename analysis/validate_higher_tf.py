#!/usr/bin/env python3
"""
Higher Timeframe Validation Analysis
=====================================

Validate the finding that 1H/4H timeframes show stronger Fib number symmetry
than 5min timeframes.
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from collections import Counter
import matplotlib.pyplot as plt

FIB_NUMBERS = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]

DATA_PATHS = {
    'silver': '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAGUSD5.csv',
    'gold': '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv',
}

OUTPUT_DIR = '/home/palbot/Projects/log-fib-scalper/analysis'


def load_data(filepath):
    """Load CSV data."""
    df = pd.read_csv(filepath)
    time_values = df['time'].astype(str)
    time_values = time_values.str.replace(r'[+-]\d{2}:\d{2}$', '', regex=True)
    time_values = time_values.str.replace('T', ' ')
    df['datetime'] = pd.to_datetime(time_values)
    df = df[['datetime', 'open', 'high', 'low', 'close']].copy().dropna()
    df = df.drop_duplicates(subset=['datetime'], keep='first')
    df = df.sort_values('datetime').reset_index(drop=True)
    return df


def aggregate_tf(df, tf='1h'):
    """Aggregate to higher timeframe."""
    df = df.set_index('datetime')
    ohlc = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}
    agg = df.resample(tf).agg(ohlc).dropna().reset_index()
    return agg


def detect_swings(data, lookback):
    """Detect swings."""
    highs, lows = [], []
    for i in range(lookback, len(data) - lookback):
        is_high = all(data['high'].iloc[j] < data['high'].iloc[i] 
                      for j in range(i-lookback, i+lookback+1) if j != i)
        if is_high:
            highs.append({'idx': i, 'price': data['high'].iloc[i], 'type': 'H'})
        
        is_low = all(data['low'].iloc[j] > data['low'].iloc[i] 
                     for j in range(i-lookback, i+lookback+1) if j != i)
        if is_low:
            lows.append({'idx': i, 'price': data['low'].iloc[i], 'type': 'L'})
    
    return highs, lows


def analyze_tf_fib_symmetry(instrument):
    """Analyze Fib symmetry across timeframes."""
    print(f"\n{'='*70}")
    print(f"Analyzing {instrument.upper()}")
    print(f"{'='*70}")
    
    df_5min = load_data(DATA_PATHS[instrument])
    df_1h = aggregate_tf(df_5min, '1h')
    df_4h = aggregate_tf(df_5min, '4h')
    
    results = {}
    
    for name, df, lb in [
        ('5min', df_5min, 6 if instrument == 'silver' else 8),
        ('1h', df_1h, 3),
        ('4h', df_4h, 3)
    ]:
        highs, lows = detect_swings(df, lb)
        all_swings = sorted(highs + lows, key=lambda x: x['idx'])
        
        # Calculate intervals
        intervals = [all_swings[i]['idx'] - all_swings[i-1]['idx'] 
                     for i in range(1, len(all_swings))]
        
        # Fib analysis
        exact_fib = sum(1 for i in intervals if i in FIB_NUMBERS)
        near_fib = sum(1 for i in intervals if any(abs(i - f) <= 1 for f in FIB_NUMBERS))
        
        # Alternation rate
        alternations = sum(1 for i in range(1, len(all_swings)) 
                           if all_swings[i]['type'] != all_swings[i-1]['type'])
        
        results[name] = {
            'candles': len(df),
            'swings': len(all_swings),
            'intervals': len(intervals),
            'exact_fib': exact_fib,
            'exact_fib_pct': exact_fib / len(intervals) * 100 if intervals else 0,
            'near_fib': near_fib,
            'near_fib_pct': near_fib / len(intervals) * 100 if intervals else 0,
            'alternations': alternations,
            'alternation_pct': alternations / len(intervals) * 100 if intervals else 0,
            'mean_interval': np.mean(intervals) if intervals else 0,
            'median_interval': np.median(intervals) if intervals else 0,
        }
        
        print(f"\n{name.upper()} Timeframe:")
        print(f"  Candles: {results[name]['candles']:,}")
        print(f"  Swings: {results[name]['swings']} (H: {len(highs)}, L: {len(lows)})")
        print(f"  Intervals: {results[name]['intervals']}")
        print(f"  Exact Fib: {exact_fib} ({results[name]['exact_fib_pct']:.1f}%)")
        print(f"  Near Fib (±1): {near_fib} ({results[name]['near_fib_pct']:.1f}%)")
        print(f"  Alternation Rate: {results[name]['alternation_pct']:.1f}%")
        print(f"  Mean Interval: {results[name]['mean_interval']:.2f} bars")
        print(f"  Median Interval: {results[name]['median_interval']:.1f} bars")
    
    return results


def create_comparison_chart(all_results):
    """Create comparison visualization."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Higher Timeframe Fib Symmetry Validation', fontsize=16, fontweight='bold')
    
    instruments = ['silver', 'gold']
    timeframes = ['5min', '1h', '4h']
    colors = ['#58a6ff', '#a371f7', '#3fb950']
    
    # Plot 1: Fib % by TF
    ax = axes[0, 0]
    for i, inst in enumerate(instruments):
        fib_pcts = [all_results[inst][tf]['near_fib_pct'] for tf in timeframes]
        ax.plot(range(len(timeframes)), fib_pcts, marker='o', linewidth=2, 
                label=inst.capitalize(), color=colors[i])
    ax.set_xticks(range(len(timeframes)))
    ax.set_xticklabels(timeframes)
    ax.set_ylabel('Fib Number Occurrence (%)')
    ax.set_title('Fib Symmetry by Timeframe')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Swings count
    ax = axes[0, 1]
    for i, inst in enumerate(instruments):
        swing_counts = [all_results[inst][tf]['swings'] for tf in timeframes]
        ax.bar([j + i*0.35 for j in range(len(timeframes))], swing_counts, 
               width=0.35, label=inst.capitalize(), color=colors[i])
    ax.set_xticks([j + 0.175 for j in range(len(timeframes))])
    ax.set_xticklabels(timeframes)
    ax.set_ylabel('Number of Swings')
    ax.set_title('Swing Count by Timeframe')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Plot 3: Alternation rate
    ax = axes[1, 0]
    for i, inst in enumerate(instruments):
        alt_rates = [all_results[inst][tf]['alternation_pct'] for tf in timeframes]
        ax.plot(range(len(timeframes)), alt_rates, marker='s', linewidth=2,
                label=inst.capitalize(), color=colors[i])
    ax.set_xticks(range(len(timeframes)))
    ax.set_xticklabels(timeframes)
    ax.set_ylabel('Alternation Rate (%)')
    ax.set_title('Market Alternation (HLH + LHL Patterns)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 4: Mean interval
    ax = axes[1, 1]
    for i, inst in enumerate(instruments):
        mean_ints = [all_results[inst][tf]['mean_interval'] for tf in timeframes]
        ax.bar([j + i*0.35 for j in range(len(timeframes))], mean_ints,
               width=0.35, label=inst.capitalize(), color=colors[i])
    ax.set_xticks([j + 0.175 for j in range(len(timeframes))])
    ax.set_xticklabels(timeframes)
    ax.set_ylabel('Mean Interval (bars)')
    ax.set_title('Average Swing Duration')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    output_path = f'{OUTPUT_DIR}/higher_tf_validation.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#0d1117')
    print(f"\nSaved: {output_path}")
    plt.close()
    
    return output_path


def main():
    print("="*70)
    print("HIGHER TIMEFRAME FIB SYMMETRY VALIDATION")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = {}
    
    for inst in ['silver', 'gold']:
        all_results[inst] = analyze_tf_fib_symmetry(inst)
    
    # Create visualization
    create_comparison_chart(all_results)
    
    # Save JSON report
    report_path = f'{OUTPUT_DIR}/higher_tf_validation.json'
    with open(report_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=float)
    print(f"Saved: {report_path}")
    
    # Summary
    print(f"\n{'='*70}")
    print("VALIDATION SUMMARY")
    print(f"{'='*70}")
    
    for inst in ['silver', 'gold']:
        print(f"\n{inst.upper()}:")
        for tf in ['5min', '1h', '4h']:
            r = all_results[inst][tf]
            print(f"  {tf}: {r['near_fib_pct']:.1f}% Fib, {r['alternation_pct']:.1f}% Alt, {r['swings']} swings")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return all_results


if __name__ == '__main__':
    main()
