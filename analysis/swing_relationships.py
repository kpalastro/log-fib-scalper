#!/usr/bin/env python3
"""
Log-Fib Scalper: Swing-to-Swing Relationship Analysis
======================================================

This script analyzes geometric patterns in swing timing and structure for the
Log-Fib scalper strategy. Focus is on PURE MATHEMATICS/GEOMETRY - NOT lagging indicators.

SWING DETECTION METHOD (Current Implementation):
-------------------------------------------------
The strategy uses a simple LOOKBACK FRACTAL method:
- lookback=6 means 6 candles on EACH side must be lower for a swing high
- For swing high: candle's high must be > all (lookback * 2 + 1) candles in window
- For swing low: candle's low must be < all (lookback * 2 + 1) candles in window
- This is a PURE FRACTAL pattern - no indicators, just price structure

ANALYSIS FOCUS:
---------------
1. Fractal symmetry in swing patterns
2. Fib number relationships (13, 21, 34, 55 candle counts)
3. Price-time squaring (Gann-style geometry)
4. Retracement depth clustering around Fib ratios (0.382, 0.5, 0.618, 0.786)

Author: Hermes Agent for Nous Research
Date: 2026-05-19
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from datetime import datetime
import json
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

DATA_DIR = Path("/home/palbot/Projects/log-fib-scalper/data")
OUTPUT_DIR = Path("/home/palbot/Projects/log-fib-scalper/analysis")
OUTPUT_DIR.mkdir(exist_ok=True)

INSTRUMENT_CONFIG = {
    'silver': {
        'file': 'OANDA_XAGUSD5.csv',
        'lookback': 6,
        'name': 'Silver (XAGUSD) 5-min',
        'color': '#C0C0C0'
    },
    'gold': {
        'file': 'OANDA_XAUUSD5.csv',
        'lookback': 8,
        'name': 'Gold (XAUUSD) 5-min',
        'color': '#FFD700'
    }
}

FIB_NUMBERS = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
FIB_RATIOS = [0.382, 0.5, 0.618, 0.786]

# =============================================================================
# SWING DETECTION (Matches visualizer.html implementation)
# =============================================================================

def detect_swings(df, lookback):
    """
    Detect swing highs and lows using the lookback fractal method.
    
    This matches the JavaScript implementation in visualizer.html:
    - Swing High: A candle where lookback candles on each side have lower highs
    - Swing Low: A candle where lookback candles on each side have higher lows
    
    Parameters:
    -----------
    df : pandas DataFrame with 'high' and 'low' columns
    lookback : int - number of candles on each side to compare
    
    Returns:
    --------
    dict with 'swing_highs' and 'swing_lows' DataFrames
    """
    swing_highs = []
    swing_lows = []
    
    highs = df['high'].values
    lows = df['low'].values
    times = df.index
    
    for i in range(lookback, len(df) - lookback):
        # Check for swing high
        is_swing_high = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i and highs[j] >= highs[i]:
                is_swing_high = False
                break
        
        if is_swing_high:
            swing_highs.append({
                'index': i,
                'time': times[i],
                'price': highs[i],
                'anchor_low': lows[i]
            })
        
        # Check for swing low
        is_swing_low = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i and lows[j] <= lows[i]:
                is_swing_low = False
                break
        
        if is_swing_low:
            swing_lows.append({
                'index': i,
                'time': times[i],
                'price': lows[i],
                'anchor_high': highs[i]
            })
    
    return {
        'swing_highs': pd.DataFrame(swing_highs),
        'swing_lows': pd.DataFrame(swing_lows)
    }


# =============================================================================
# SWING-TO-SWING ANALYSIS FUNCTIONS
# =============================================================================

def analyze_swing_sequences(swing_highs, swing_lows):
    """
    Analyze the sequence of swings to identify patterns.
    Merges swings into chronological order and identifies HH/HL vs LH/LL patterns.
    """
    if len(swing_highs) > 0:
        swing_highs = swing_highs.copy()
        swing_highs['type'] = 'H'
    
    if len(swing_lows) > 0:
        swing_lows = swing_lows.copy()
        swing_lows['type'] = 'L'
    
    all_swings = pd.concat([
        swing_highs[['index', 'time', 'price', 'type']] if len(swing_highs) > 0 else pd.DataFrame(),
        swing_lows[['index', 'time', 'price', 'type']] if len(swing_lows) > 0 else pd.DataFrame()
    ], ignore_index=True).sort_values('index').reset_index(drop=True)
    
    if len(all_swings) < 2:
        return all_swings, []
    
    patterns = []
    for i in range(1, len(all_swings)):
        prev = all_swings.iloc[i-1]
        curr = all_swings.iloc[i]
        
        if prev['type'] == 'H' and curr['type'] == 'L':
            pattern = 'H-L'
        elif prev['type'] == 'L' and curr['type'] == 'H':
            pattern = 'L-H'
        elif prev['type'] == 'H' and curr['type'] == 'H':
            pattern = 'HH' if curr['price'] > prev['price'] else 'LH'
        elif prev['type'] == 'L' and curr['type'] == 'L':
            pattern = 'HL' if curr['price'] > prev['price'] else 'LL'
        else:
            pattern = 'Unknown'
        
        patterns.append({
            'from_idx': i-1,
            'to_idx': i,
            'from_type': prev['type'],
            'to_type': curr['type'],
            'from_price': prev['price'],
            'to_price': curr['price'],
            'from_time': prev['time'],
            'to_time': curr['time'],
            'pattern': pattern,
            'bars': abs(curr['index'] - prev['index'])
        })
    
    return all_swings, patterns


def calculate_swing_metrics(swing_highs, swing_lows, all_swings, patterns):
    """
    Calculate comprehensive metrics for swing-to-swing relationships.
    """
    metrics = {
        'price_distances_pct': [],
        'price_distances_abs': [],
        'retracement_depths': [],
        'fib_ratio_hits': [],
        'impulse_moves': [],
        'high_to_high': [],
        'low_to_low': []
    }
    
    # Analyze H-L and L-H sequences (impulse moves)
    for p in patterns:
        if p['pattern'] in ['H-L', 'L-H']:
            price_diff = abs(p['to_price'] - p['from_price'])
            price_pct = (price_diff / p['from_price']) * 100
            metrics['price_distances_abs'].append(price_diff)
            metrics['price_distances_pct'].append(price_pct)
            metrics['impulse_moves'].append({
                'type': p['pattern'],
                'bars': p['bars'],
                'price_pct': price_pct
            })
    
    # Analyze same-type swings (HH, HL, LH, LL)
    for p in patterns:
        if p['pattern'] in ['HH', 'LH']:
            metrics['high_to_high'].append({
                'bars': p['bars'],
                'pattern': p['pattern'],
                'price_ratio': p['to_price'] / p['from_price']
            })
        elif p['pattern'] in ['HL', 'LL']:
            metrics['low_to_low'].append({
                'bars': p['bars'],
                'pattern': p['pattern'],
                'price_ratio': p['to_price'] / p['from_price']
            })
    
    # Analyze retracement depths
    for i, p in enumerate(patterns):
        if p['pattern'] in ['HH', 'HL', 'LH', 'LL']:
            retracement = None
            
            for j in range(i-1, -1, -1):
                prev_p = patterns[j]
                if prev_p['pattern'] == 'H-L' and p['pattern'] in ['HL', 'LL']:
                    impulse_range = prev_p['from_price'] - prev_p['to_price']
                    if impulse_range > 0:
                        if p['pattern'] == 'LL':
                            retracement = 0
                        else:
                            retracement = (p['to_price'] - prev_p['to_price']) / impulse_range
                    break
                elif prev_p['pattern'] == 'L-H' and p['pattern'] in ['HH', 'LH']:
                    impulse_range = prev_p['to_price'] - prev_p['from_price']
                    if impulse_range > 0:
                        if p['pattern'] == 'HH':
                            retracement = 0
                        else:
                            retracement = (prev_p['to_price'] - p['to_price']) / impulse_range
                    break
            
            if retracement is not None and retracement > 0:
                metrics['retracement_depths'].append(retracement)
                closest_fib = min(FIB_RATIOS, key=lambda x: abs(x - retracement))
                metrics['fib_ratio_hits'].append({
                    'depth': retracement,
                    'closest_fib': closest_fib,
                    'deviation': abs(retracement - closest_fib)
                })
    
    return metrics


def analyze_symmetry(swing_highs, swing_lows):
    """
    Analyze symmetry in swing patterns - do swings occur at regular intervals?
    """
    symmetry = {
        'swing_high_intervals': [],
        'swing_low_intervals': [],
        'price_symmetry': []
    }
    
    if len(swing_highs) >= 2:
        for i in range(1, len(swing_highs)):
            interval = swing_highs.iloc[i]['index'] - swing_highs.iloc[i-1]['index']
            symmetry['swing_high_intervals'].append(interval)
            price_rel = 'HH' if swing_highs.iloc[i]['price'] > swing_highs.iloc[i-1]['price'] else 'LH'
            symmetry['price_symmetry'].append({
                'type': 'high',
                'interval': interval,
                'pattern': price_rel,
                'price_ratio': swing_highs.iloc[i]['price'] / swing_highs.iloc[i-1]['price']
            })
    
    if len(swing_lows) >= 2:
        for i in range(1, len(swing_lows)):
            interval = swing_lows.iloc[i]['index'] - swing_lows.iloc[i-1]['index']
            symmetry['swing_low_intervals'].append(interval)
            price_rel = 'HL' if swing_lows.iloc[i]['price'] > swing_lows.iloc[i-1]['price'] else 'LL'
            symmetry['price_symmetry'].append({
                'type': 'low',
                'interval': interval,
                'pattern': price_rel,
                'price_ratio': swing_lows.iloc[i]['price'] / swing_lows.iloc[i-1]['price']
            })
    
    return symmetry


# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def plot_same_type_intervals(metrics, instrument_name, ax):
    """Histogram of candle counts between same-type swings"""
    h2h = [m['bars'] for m in metrics.get('high_to_high', [])]
    l2l = [m['bars'] for m in metrics.get('low_to_low', [])]
    all_counts = h2h + l2l
    
    if len(all_counts) == 0:
        ax.text(0.5, 0.5, 'No same-type swing intervals', ha='center', va='center', 
                transform=ax.transAxes)
        return
    
    ax.hist(all_counts, bins=range(0, max(all_counts)+2, 2),
            edgecolor='black', alpha=0.7, color='steelblue')
    ax.set_xlabel('Candle Count Between Same-Type Swings')
    ax.set_ylabel('Frequency')
    ax.set_title(f'Swing Interval Distribution\n{instrument_name}')
    ax.grid(True, alpha=0.3)
    
    fib_counts = [c for c in FIB_NUMBERS if c <= max(all_counts)]
    for fib in fib_counts:
        ax.axvline(fib, color='red', linestyle='--', alpha=0.7, linewidth=2)
        ax.text(fib, ax.get_ylim()[1]*0.9, f'{fib}', color='red', 
                ha='center', fontsize=9, fontweight='bold')
    
    if all_counts:
        mean_val = np.mean(all_counts)
        median_val = np.median(all_counts)
        fib_pct = sum(1 for c in all_counts if c in FIB_NUMBERS) / len(all_counts) * 100
        textstr = f'Mean: {mean_val:.1f}\nMedian: {median_val:.1f}\nFib%: {fib_pct:.1f}%'
        ax.text(0.98, 0.98, textstr, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))


def plot_impulse_duration(metrics, ax):
    """Duration of impulse moves (H-L and L-H)"""
    impulses = metrics.get('impulse_moves', [])
    if not impulses:
        ax.text(0.5, 0.5, 'No impulse moves', ha='center', va='center', 
                transform=ax.transAxes)
        return
    
    h_to_l = [m['bars'] for m in impulses if m['type'] == 'H-L']
    l_to_h = [m['bars'] for m in impulses if m['type'] == 'L-H']
    
    x = [1, 2]
    ax.boxplot([h_to_l if h_to_l else [0], l_to_h if l_to_h else [0]], 
               positions=x, widths=0.6, patch_artist=True,
               boxprops=dict(facecolor='lightblue', alpha=0.7),
               medianprops=dict(color='red', linewidth=2))
    ax.set_xticks(x)
    ax.set_xticklabels(['High→Low', 'Low→High'])
    ax.set_ylabel('Bars (Duration)')
    ax.set_title('Impulse Move Duration')
    ax.grid(True, alpha=0.3, axis='y')


def plot_pattern_frequency(patterns, ax):
    """Pattern frequency bar chart"""
    pattern_counts = {}
    for p in patterns:
        pattern_counts[p['pattern']] = pattern_counts.get(p['pattern'], 0) + 1
    
    if len(pattern_counts) == 0:
        ax.text(0.5, 0.5, 'No patterns found', ha='center', va='center', 
                transform=ax.transAxes)
        return
    
    sorted_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)
    labels = [p[0] for p in sorted_patterns]
    counts = [p[1] for p in sorted_patterns]
    
    colors = {'H-L': 'coral', 'L-H': 'steelblue', 'HH': 'green', 'HL': 'lightgreen', 
              'LH': 'orange', 'LL': 'red'}
    bar_colors = [colors.get(l, 'gray') for l in labels]
    
    bars = ax.bar(range(len(labels)), counts, color=bar_colors, edgecolor='black', alpha=0.8)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel('Frequency')
    ax.set_title('Swing Pattern Frequency')
    ax.grid(True, alpha=0.3, axis='y')
    
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                str(count), ha='center', va='bottom', fontsize=10)


def plot_retracement_distribution(metrics, ax):
    """Retracement depth distribution with Fib ratio markers"""
    depths = metrics.get('retracement_depths', [])
    
    if len(depths) == 0:
        ax.text(0.5, 0.5, 'No retracements found', ha='center', va='center', 
                transform=ax.transAxes)
        return
    
    ax.hist(depths, bins=20, edgecolor='black', alpha=0.7, color='mediumseagreen')
    ax.set_xlabel('Retracement Depth (ratio of prior impulse)')
    ax.set_ylabel('Frequency')
    ax.set_title('Retracement Depth Distribution')
    ax.grid(True, alpha=0.3)
    
    for fib in FIB_RATIOS:
        ax.axvline(fib, color='red', linestyle='--', alpha=0.8, linewidth=2)
        ax.text(fib, ax.get_ylim()[1]*0.95, f'{fib:.3f}', color='red', 
                ha='center', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))


def plot_fib_ratio_clustering(metrics, ax):
    """Show clustering of retracements around Fib ratios"""
    fib_hits = metrics.get('fib_ratio_hits', [])
    
    if len(fib_hits) == 0:
        ax.text(0.5, 0.5, 'No Fib ratio hits', ha='center', va='center', 
                transform=ax.transAxes)
        return
    
    ratio_counts = {}
    for hit in fib_hits:
        ratio = hit['closest_fib']
        ratio_counts[ratio] = ratio_counts.get(ratio, 0) + 1
    
    total_retracements = len(metrics['retracement_depths'])
    
    labels = [f'{r:.3f}' for r in sorted(ratio_counts.keys())]
    counts = [ratio_counts[r] for r in sorted(ratio_counts.keys())]
    percentages = [c/total_retracements*100 for c in counts]
    
    colors = ['gold' if r in FIB_RATIOS else 'gray' for r in sorted(ratio_counts.keys())]
    
    bars = ax.bar(range(len(labels)), percentages, color=colors, alpha=0.7, edgecolor='black')
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel('% of Retracement Moves')
    ax.set_title(f'Retracement Clustering Around Fib Ratios\n(Total: {total_retracements} retracements)')
    ax.grid(True, alpha=0.3, axis='y')
    
    for bar, pct in zip(bars, percentages):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f'{pct:.1f}%', ha='center', va='bottom', fontsize=9)


def plot_fib_number_analysis(metrics, ax):
    """Analyze if Fib numbers appear more frequently in candle counts"""
    h2h = [m['bars'] for m in metrics.get('high_to_high', [])]
    l2l = [m['bars'] for m in metrics.get('low_to_low', [])]
    counts = h2h + l2l
    
    if len(counts) == 0:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', 
                transform=ax.transAxes)
        return
    
    fib_occurrences = sum(1 for c in counts if c in FIB_NUMBERS)
    non_fib_occurrences = len(counts) - fib_occurrences
    
    labels = [f'Fib Numbers\n({fib_occurrences})', f'Non-Fib\n({non_fib_occurrences})']
    sizes = [fib_occurrences, non_fib_occurrences]
    colors = ['gold', 'lightgray']
    
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, 
                                       autopct='%1.1f%%', startangle=90)
    autotexts[0].set_color('black')
    autotexts[0].set_fontweight('bold')
    ax.set_title(f'Fib Number Occurrence in Swing Intervals\nTotal: {len(counts)} intervals')


def plot_price_distance_distribution(metrics, ax):
    """Distribution of price distances between swings"""
    distances = metrics.get('price_distances_pct', [])
    
    if len(distances) == 0:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', 
                transform=ax.transAxes)
        return
    
    ax.hist(distances, bins=30, edgecolor='black', alpha=0.7, color='darkorange')
    ax.set_xlabel('Price Change (%)')
    ax.set_ylabel('Frequency')
    ax.set_title('Price Distance Between Swings (Impulse Moves)')
    ax.grid(True, alpha=0.3)
    
    mean_dist = np.mean(distances)
    median_dist = np.median(distances)
    ax.axvline(mean_dist, color='red', linestyle='--', label=f'Mean: {mean_dist:.2f}%')
    ax.axvline(median_dist, color='green', linestyle='--', label=f'Median: {median_dist:.2f}%')
    ax.legend(fontsize=9)


def plot_hh_lh_comparison(metrics, ax):
    """Compare HH vs LH patterns"""
    h2h = metrics.get('high_to_high', [])
    if not h2h:
        ax.text(0.5, 0.5, 'No high-to-high data', ha='center', va='center', 
                transform=ax.transAxes)
        return
    
    hh_bars = [m['bars'] for m in h2h if m['pattern'] == 'HH']
    lh_bars = [m['bars'] for m in h2h if m['pattern'] == 'LH']
    
    data = [hh_bars if hh_bars else [0], lh_bars if lh_bars else [0]]
    labels = [f'HH (n={len(hh_bars)})', f'LH (n={len(lh_bars)})']
    colors = ['green', 'red']
    
    ax.hist(data, bins=15, histtype='bar', edgecolor='black', alpha=0.7, color=colors, label=labels)
    ax.set_xlabel('Bars Between Swing Highs')
    ax.set_ylabel('Frequency')
    ax.set_title('Higher Highs vs Lower Highs')
    ax.grid(True, alpha=0.3)
    if hh_bars and lh_bars:
        ax.legend(fontsize=8)


def plot_hl_ll_comparison(metrics, ax):
    """Compare HL vs LL patterns"""
    l2l = metrics.get('low_to_low', [])
    if not l2l:
        ax.text(0.5, 0.5, 'No low-to-low data', ha='center', va='center', 
                transform=ax.transAxes)
        return
    
    hl_bars = [m['bars'] for m in l2l if m['pattern'] == 'HL']
    ll_bars = [m['bars'] for m in l2l if m['pattern'] == 'LL']
    
    data = [hl_bars if hl_bars else [0], ll_bars if ll_bars else [0]]
    labels = [f'HL (n={len(hl_bars)})', f'LL (n={len(ll_bars)})']
    colors = ['green', 'red']
    
    ax.hist(data, bins=15, histtype='bar', edgecolor='black', alpha=0.7, color=colors, label=labels)
    ax.set_xlabel('Bars Between Swing Lows')
    ax.set_ylabel('Frequency')
    ax.set_title('Higher Lows vs Lower Lows')
    ax.grid(True, alpha=0.3)
    if hl_bars and ll_bars:
        ax.legend(fontsize=8)


# =============================================================================
# STATISTICAL ANALYSIS
# =============================================================================

def calculate_statistics(metrics):
    """Calculate comprehensive statistics for all metrics"""
    stats = {}
    
    # Same-type swing interval statistics
    h2h = metrics.get('high_to_high', [])
    l2l = metrics.get('low_to_low', [])
    
    hh_counts = [m['bars'] for m in h2h]
    ll_counts = [m['bars'] for m in l2l]
    
    if hh_counts:
        stats['high_to_high'] = {
            'mean': np.mean(hh_counts),
            'median': np.median(hh_counts),
            'std': np.std(hh_counts),
            'min': min(hh_counts),
            'max': max(hh_counts),
            'fib_count': sum(1 for c in hh_counts if c in FIB_NUMBERS),
            'fib_percentage': sum(1 for c in hh_counts if c in FIB_NUMBERS) / len(hh_counts) * 100,
            'total': len(hh_counts),
            'hh_count': sum(1 for m in h2h if m['pattern'] == 'HH'),
            'lh_count': sum(1 for m in h2h if m['pattern'] == 'LH')
        }
    
    if ll_counts:
        stats['low_to_low'] = {
            'mean': np.mean(ll_counts),
            'median': np.median(ll_counts),
            'std': np.std(ll_counts),
            'min': min(ll_counts),
            'max': max(ll_counts),
            'fib_count': sum(1 for c in ll_counts if c in FIB_NUMBERS),
            'fib_percentage': sum(1 for c in ll_counts if c in FIB_NUMBERS) / len(ll_counts) * 100,
            'total': len(ll_counts),
            'hl_count': sum(1 for m in l2l if m['pattern'] == 'HL'),
            'll_count': sum(1 for m in l2l if m['pattern'] == 'LL')
        }
    
    # Retracement statistics
    depths = metrics.get('retracement_depths', [])
    if depths:
        stats['retracements'] = {
            'mean': np.mean(depths),
            'median': np.median(depths),
            'std': np.std(depths),
            'min': min(depths),
            'max': max(depths),
            'total': len(depths)
        }
        
        fib_hits = metrics.get('fib_ratio_hits', [])
        for fib in FIB_RATIOS:
            hits = sum(1 for h in fib_hits if h['closest_fib'] == fib)
            stats['retracements'][f'fib_{fib}_hits'] = hits
            stats['retracements'][f'fib_{fib}_percentage'] = hits / len(depths) * 100 if depths else 0
    
    # Price distance statistics
    distances = metrics.get('price_distances_pct', [])
    if distances:
        stats['price_distances'] = {
            'mean': np.mean(distances),
            'median': np.median(distances),
            'std': np.std(distances),
            'min': min(distances),
            'max': max(distances),
            'total': len(distances)
        }
    
    return stats


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

def analyze_instrument(instrument_key, verbose=True):
    """Run complete swing-to-swing analysis for one instrument."""
    config = INSTRUMENT_CONFIG[instrument_key]
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"Analyzing: {config['name']}")
        print(f"Lookback: {config['lookback']} (fractal: {config['lookback']} candles each side)")
        print(f"{'='*70}")
    
    file_path = DATA_DIR / config['file']
    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    
    if verbose:
        print(f"\nData loaded: {len(df)} candles")
        print(f"Date range: {df.index[0]} to {df.index[-1]}")
    
    swings = detect_swings(df, config['lookback'])
    
    if verbose:
        print(f"\nSwings detected:")
        print(f"  - Swing Highs: {len(swings['swing_highs'])}")
        print(f"  - Swing Lows: {len(swings['swing_lows'])}")
    
    all_swings, patterns = analyze_swing_sequences(swings['swing_highs'], swings['swing_lows'])
    
    if verbose:
        print(f"\nPattern sequences: {len(patterns)}")
        pattern_counts = {}
        for p in patterns:
            pattern_counts[p['pattern']] = pattern_counts.get(p['pattern'], 0) + 1
        for pattern, count in sorted(pattern_counts.items()):
            print(f"  - {pattern}: {count}")
    
    metrics = calculate_swing_metrics(swings['swing_highs'], swings['swing_lows'], all_swings, patterns)
    symmetry = analyze_symmetry(swings['swing_highs'], swings['swing_lows'])
    metrics['symmetry'] = symmetry
    stats = calculate_statistics(metrics)
    
    if verbose:
        print(f"\n{'='*40}")
        print("STATISTICAL SUMMARY")
        print(f"{'='*40}")
        
        if 'high_to_high' in stats:
            sh = stats['high_to_high']
            print(f"\nHigh-to-High Intervals:")
            print(f"  Mean: {sh['mean']:.2f} bars | Median: {sh['median']:.2f}")
            print(f"  Range: {sh['min']} - {sh['max']}")
            print(f"  HH: {sh['hh_count']} | LH: {sh['lh_count']}")
            print(f"  Fib Numbers: {sh['fib_count']} ({sh['fib_percentage']:.1f}%)")
        
        if 'low_to_low' in stats:
            sl = stats['low_to_low']
            print(f"\nLow-to-Low Intervals:")
            print(f"  Mean: {sl['mean']:.2f} bars | Median: {sl['median']:.2f}")
            print(f"  Range: {sl['min']} - {sl['max']}")
            print(f"  HL: {sl['hl_count']} | LL: {sl['ll_count']}")
            print(f"  Fib Numbers: {sl['fib_count']} ({sl['fib_percentage']:.1f}%)")
        
        if 'retracements' in stats:
            sr = stats['retracements']
            print(f"\nRetracement Depths:")
            print(f"  Mean: {sr['mean']*100:.2f}% | Median: {sr['median']*100:.2f}%")
            print(f"  Range: {sr['min']*100:.2f}% - {sr['max']*100:.2f}%")
            for fib in FIB_RATIOS:
                if f'fib_{fib}_hits' in sr:
                    print(f"  {fib}: {sr[f'fib_{fib}_hits']} hits ({sr[f'fib_{fib}_percentage']:.1f}%)")
        
        if 'price_distances' in stats:
            sp = stats['price_distances']
            print(f"\nPrice Distances (Impulse Moves):")
            print(f"  Mean: {sp['mean']:.2f}%")
            print(f"  Median: {sp['median']:.2f}%")
            print(f"  Range: {sp['min']:.2f}% - {sp['max']:.2f}%")
    
    # Create visualizations
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle(f"Swing-to-Swing Analysis: {config['name']}\n"
                 f"Lookback={config['lookback']} | Swings: {len(swings['swing_highs'])}H / {len(swings['swing_lows'])}L",
                 fontsize=14, fontweight='bold')
    
    gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.3)
    
    ax1 = fig.add_subplot(gs[0, 0])
    plot_same_type_intervals(metrics, config['name'], ax1)
    
    ax2 = fig.add_subplot(gs[0, 1])
    plot_impulse_duration(metrics, ax2)
    
    ax3 = fig.add_subplot(gs[0, 2])
    plot_pattern_frequency(patterns, ax3)
    
    ax4 = fig.add_subplot(gs[1, 0])
    plot_retracement_distribution(metrics, ax4)
    
    ax5 = fig.add_subplot(gs[1, 1])
    plot_fib_ratio_clustering(metrics, ax5)
    
    ax6 = fig.add_subplot(gs[1, 2])
    plot_fib_number_analysis(metrics, ax6)
    
    ax7 = fig.add_subplot(gs[2, 0])
    plot_price_distance_distribution(metrics, ax7)
    
    ax8 = fig.add_subplot(gs[2, 1])
    plot_hh_lh_comparison(metrics, ax8)
    
    ax9 = fig.add_subplot(gs[2, 2])
    plot_hl_ll_comparison(metrics, ax9)
    
    output_path = OUTPUT_DIR / f"swing_analysis_{instrument_key}.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight', 
                facecolor='#1a1a2e', edgecolor='none')
    plt.close()
    
    if verbose:
        print(f"\nVisualization saved: {output_path}")
    
    return {
        'instrument': instrument_key,
        'config': config,
        'data_points': len(df),
        'swing_highs': len(swings['swing_highs']),
        'swing_lows': len(swings['swing_lows']),
        'patterns': patterns,
        'metrics': metrics,
        'symmetry': symmetry,
        'statistics': stats
    }


# =============================================================================
# COMPARATIVE ANALYSIS
# =============================================================================

def generate_comparative_report(results):
    """Generate a comparative report between instruments"""
    print(f"\n\n{'#'*70}")
    print("# COMPARATIVE ANALYSIS REPORT")
    print(f"{'#'*70}")
    
    report = {
        'generated_at': datetime.now().isoformat(),
        'instruments': {}
    }
    
    for result in results:
        inst = result['instrument']
        report['instruments'][inst] = {
            'statistics': result['statistics'],
            'swing_counts': {
                'highs': result['swing_highs'],
                'lows': result['swing_lows']
            }
        }
        
        print(f"\n{'-'*70}")
        print(f"{INSTRUMENT_CONFIG[inst]['name']}")
        print(f"{'-'*70}")
        
        if 'high_to_high' in result['statistics']:
            sh = result['statistics']['high_to_high']
            print(f"\n📊 HIGH-TO-HIGH INTERVALS")
            print(f"   Mean: {sh['mean']:.2f} bars | Median: {sh['median']:.2f}")
            print(f"   HH: {sh['hh_count']} | LH: {sh['lh_count']}")
            print(f"   Fib Number Occurrence: {sh['fib_percentage']:.1f}%")
        
        if 'low_to_low' in result['statistics']:
            sl = result['statistics']['low_to_low']
            print(f"\n📊 LOW-TO-LOW INTERVALS")
            print(f"   Mean: {sl['mean']:.2f} bars | Median: {sl['median']:.2f}")
            print(f"   HL: {sl['hl_count']} | LL: {sl['ll_count']}")
            print(f"   Fib Number Occurrence: {sl['fib_percentage']:.1f}%")
        
        if 'retracements' in result['statistics']:
            sr = result['statistics']['retracements']
            print(f"\n📐 RETRACEMENT DEPTHS")
            print(f"   Mean: {sr['mean']*100:.2f}% | Median: {sr['median']*100:.2f}%")
            print(f"   Closest Fib Ratios:")
            for fib in FIB_RATIOS:
                if f'fib_{fib}_hits' in sr:
                    print(f"     {fib}: {sr[f'fib_{fib}_hits']} hits ({sr[f'fib_{fib}_percentage']:.1f}%)")
    
    report_path = OUTPUT_DIR / "swing_analysis_report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n\n💾 Report saved: {report_path}")
    
    return report


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main entry point for swing-to-swing analysis"""
    print("="*70)
    print("LOG-FIB SCALPER: SWING-TO-SWING RELATIONSHIP ANALYSIS")
    print("="*70)
    print("\n📋 ANALYSIS OVERVIEW")
    print("-"*70)
    print("This analysis examines GEOMETRIC patterns in swing timing and structure.")
    print("Focus: Fractal symmetry, Fib numbers, Price-time geometry, NOT indicators.")
    print("\n📊 SWING DETECTION METHOD:")
    print("   Simple Lookback Fractal (matches visualizer.html)")
    print("   - lookback=N means N candles on EACH side must be lower/higher")
    print("   - Silver: lookback=6 (13-candle window)")
    print("   - Gold: lookback=8 (17-candle window)")
    print("\n🔢 FIB NUMBERS ANALYZED:", FIB_NUMBERS)
    print("📐 FIB RATIOS:", FIB_RATIOS)
    
    results = []
    
    for instrument in INSTRUMENT_CONFIG.keys():
        try:
            result = analyze_instrument(instrument, verbose=True)
            results.append(result)
        except Exception as e:
            print(f"\n❌ Error analyzing {instrument}: {e}")
            import traceback
            traceback.print_exc()
    
    if results:
        generate_comparative_report(results)
    
    print(f"\n{'='*70}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*70}")
    print(f"\n📁 Output files:")
    for r in results:
        print(f"   - {OUTPUT_DIR}/swing_analysis_{r['instrument']}.png")
    print(f"   - {OUTPUT_DIR}/swing_analysis_report.json")
    print(f"\n✨ Key insights focus on:")
    print(f"   1. Fractal symmetry in swing patterns")
    print(f"   2. Fib number relationships (13, 21, 34, 55)")
    print(f"   3. Retracement clustering around Fib ratios")
    print(f"   4. Price-time geometric relationships")


if __name__ == "__main__":
    main()
