#!/usr/bin/env python3
"""
Deep Swing Research - Geometric Pattern Discovery
==================================================

Research Questions:
1. Multi-timeframe swing structure (5min → 1H → 4H)
2. Candle count patterns (Fib numbers: 13, 21, 34, 55)
3. Price-time squaring (Gann-style geometry)
4. Swing sequence patterns (Markov chain analysis)

Author: Hermes Research Team
Date: 2026-05-19
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.gridspec import GridSpec

# ============================================================================
# CONFIGURATION
# ============================================================================

FIB_NUMBERS = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
FIB_RATIOS = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]

DATA_PATHS = {
    'silver': '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAGUSD5.csv',
    'gold': '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv',
}

OUTPUT_DIR = '/home/palbot/Projects/log-fib-scalper/analysis'

# ============================================================================
# DATA LOADING & TIMEFRAME AGGREGATION
# ============================================================================

def load_data(filepath):
    """Load CSV data with proper parsing."""
    df = pd.read_csv(filepath)
    
    # Handle various datetime formats
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
    elif 'time' in df.columns:
        # Try parsing as datetime
        try:
            df['datetime'] = pd.to_datetime(df['time'])
        except:
            df['datetime'] = pd.to_datetime(df['time'], format='%Y-%m-%d %H:%M:%S')
    
    # Select only OHLC columns (avoid duplicate column issues)
    if 'time' in df.columns:
        df = df[['time', 'open', 'high', 'low', 'close']].copy()
        df = df.rename(columns={'time': 'datetime'})
    elif 'datetime' in df.columns:
        df = df[['datetime', 'open', 'high', 'low', 'close']].copy()
    
    df = df.dropna()
    
    # Remove duplicate datetimes, keep first
    df = df.drop_duplicates(subset=['datetime'], keep='first')
    df = df.sort_values('datetime').reset_index(drop=True)
    return df


def aggregate_timeframe(df, timeframe='1h'):
    """Aggregate 5-min data to higher timeframes."""
    df = df.copy()
    # Ensure datetime is datetime type and set as index
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.set_index('datetime')
    
    ohlc_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
    }
    
    if timeframe == '1h':
        agg_df = df.resample('1h').agg(ohlc_dict).dropna()
    elif timeframe == '4h':
        agg_df = df.resample('4h').agg(ohlc_dict).dropna()
    elif timeframe == '1D':
        agg_df = df.resample('1D').agg(ohlc_dict).dropna()
    else:
        agg_df = df
    
    agg_df = agg_df.reset_index()
    return agg_df


def detect_swings(data, lookback):
    """Detect swing highs and lows using lookback fractal method."""
    swing_highs = []
    swing_lows = []
    
    for i in range(lookback, len(data) - lookback):
        # Swing High
        is_swing_high = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i and data['high'].iloc[j] >= data['high'].iloc[i]:
                is_swing_high = False
                break
        if is_swing_high:
            swing_highs.append({
                'index': i,
                'datetime': data['datetime'].iloc[i],
                'price': data['high'].iloc[i],
                'anchor': data['low'].iloc[i],
                'type': 'H'
            })
        
        # Swing Low
        is_swing_low = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i and data['low'].iloc[j] <= data['low'].iloc[i]:
                is_swing_low = False
                break
        if is_swing_low:
            swing_lows.append({
                'index': i,
                'datetime': data['datetime'].iloc[i],
                'price': data['low'].iloc[i],
                'anchor': data['high'].iloc[i],
                'type': 'L'
            })
    
    return swing_highs, swing_lows


# ============================================================================
# RESEARCH 1: MULTI-TIMEFRAME SWING STRUCTURE
# ============================================================================

def analyze_multi_timeframe_swings(df, instrument):
    """Analyze how swing structure changes across timeframes."""
    print(f"\n{'='*70}")
    print(f"RESEARCH 1: Multi-Timeframe Swing Structure - {instrument.upper()}")
    print(f"{'='*70}")
    
    results = {}
    
    for tf in ['5min', '1H', '4H']:
        if tf == '5min':
            tf_df = df
            lookback = 6 if instrument == 'silver' else 8
        else:
            tf_df = aggregate_timeframe(df, tf)
            lookback = 3  # Smaller lookback for higher TFs
        
        swing_highs, swing_lows = detect_swings(tf_df, lookback)
        
        # Combine and sort
        all_swings = sorted(swing_highs + swing_lows, key=lambda x: x['index'])
        
        # Calculate swing-to-swing metrics
        intervals = []
        price_changes = []
        for i in range(1, len(all_swings)):
            prev = all_swings[i-1]
            curr = all_swings[i]
            interval = curr['index'] - prev['index']
            price_change = ((curr['price'] - prev['price']) / prev['price']) * 100
            intervals.append(interval)
            price_changes.append(price_change)
        
        # Fib number occurrence
        fib_count = sum(1 for i in intervals if i in FIB_NUMBERS)
        fib_pct = (fib_count / len(intervals) * 100) if intervals else 0
        
        results[tf] = {
            'num_candles': len(tf_df),
            'num_swings': len(all_swings),
            'swing_highs': len(swing_highs),
            'swing_lows': len(swing_lows),
            'mean_interval': np.mean(intervals) if intervals else 0,
            'median_interval': np.median(intervals) if intervals else 0,
            'std_interval': np.std(intervals) if intervals else 0,
            'fib_occurrence_pct': fib_pct,
            'mean_price_change_pct': np.mean(price_changes) if price_changes else 0,
            'intervals': intervals,
        }
        
        print(f"\n{tf} Timeframe (lookback={lookback}):")
        print(f"  Candles: {results[tf]['num_candles']:,}")
        print(f"  Total Swings: {results[tf]['num_swings']} (H: {results[tf]['swing_highs']}, L: {results[tf]['swing_lows']})")
        print(f"  Mean Interval: {results[tf]['mean_interval']:.2f} bars")
        print(f"  Median Interval: {results[tf]['median_interval']:.1f} bars")
        print(f"  Fib Number Occurrence: {results[tf]['fib_occurrence_pct']:.1f}%")
        print(f"  Mean Price Change: {results[tf]['mean_price_change_pct']:.3f}%")
    
    return results


# ============================================================================
# RESEARCH 2: CANDLE COUNT PATTERNS (FIB NUMBERS)
# ============================================================================

def analyze_fib_candle_counts(df, instrument, lookback):
    """Analyze if swings occur at Fib number candle counts from previous swings."""
    print(f"\n{'='*70}")
    print(f"RESEARCH 2: Fib Candle Count Patterns - {instrument.upper()}")
    print(f"{'='*70}")
    
    swing_highs, swing_lows = detect_swings(df, lookback)
    
    # Analyze high-to-high and low-to-low intervals
    hh_intervals = []
    ll_intervals = []
    hl_intervals = []  # High to next Low
    lh_intervals = []  # Low to next High
    
    # Sort swings by index
    all_swings = sorted(swing_highs + swing_lows, key=lambda x: x['index'])
    
    prev_high_idx = None
    prev_low_idx = None
    
    for swing in all_swings:
        if swing['type'] == 'H':
            if prev_high_idx is not None:
                hh_intervals.append(swing['index'] - prev_high_idx)
            if prev_low_idx is not None:
                lh_intervals.append(swing['index'] - prev_low_idx)
            prev_high_idx = swing['index']
        else:  # 'L'
            if prev_low_idx is not None:
                ll_intervals.append(swing['index'] - prev_low_idx)
            if prev_high_idx is not None:
                hl_intervals.append(swing['index'] - prev_high_idx)
            prev_low_idx = swing['index']
    
    # Analyze Fib number clustering
    def analyze_fib_clustering(intervals, name):
        if not intervals:
            return {}
        
        # Count exact Fib matches
        exact_fib = sum(1 for i in intervals if i in FIB_NUMBERS)
        
        # Count near-Fib (within ±1)
        near_fib = sum(1 for i in intervals if any(abs(i - fib) <= 1 for fib in FIB_NUMBERS))
        
        # Distribution around Fib numbers
        fib_distances = []
        for i in intervals:
            min_dist = min(abs(i - fib) for fib in FIB_NUMBERS)
            fib_distances.append(min_dist)
        
        # Most common intervals
        counter = Counter(intervals)
        top_10 = counter.most_common(10)
        
        return {
            'total': len(intervals),
            'exact_fib_count': exact_fib,
            'exact_fib_pct': (exact_fib / len(intervals)) * 100,
            'near_fib_count': near_fib,
            'near_fib_pct': (near_fib / len(intervals)) * 100,
            'mean_distance_to_fib': np.mean(fib_distances),
            'top_intervals': top_10,
        }
    
    results = {
        'HH': analyze_fib_clustering(hh_intervals, 'High-to-High'),
        'LL': analyze_fib_clustering(ll_intervals, 'Low-to-Low'),
        'HL': analyze_fib_clustering(hl_intervals, 'High-to-Low'),
        'LH': analyze_fib_clustering(lh_intervals, 'Low-to-High'),
    }
    
    for pattern, data in results.items():
        if data:
            print(f"\n{pattern} Intervals:")
            print(f"  Total: {data['total']}")
            print(f"  Exact Fib Numbers: {data['exact_fib_count']} ({data['exact_fib_pct']:.1f}%)")
            print(f"  Near Fib (±1): {data['near_fib_count']} ({data['near_fib_pct']:.1f}%)")
            print(f"  Mean Distance to Fib: {data['mean_distance_to_fib']:.2f}")
            print(f"  Top Intervals: {data['top_intervals'][:5]}")
    
    return results


# ============================================================================
# RESEARCH 3: PRICE-TIME SQUARING (GANN-STYLE GEOMETRY)
# ============================================================================

def analyze_price_time_squaring(df, instrument, lookback):
    """Analyze price-time geometric relationships (Gann-style)."""
    print(f"\n{'='*70}")
    print(f"RESEARCH 3: Price-Time Squaring - {instrument.upper()}")
    print(f"{'='*70}")
    
    swing_highs, swing_lows = detect_swings(df, lookback)
    all_swings = sorted(swing_highs + swing_lows, key=lambda x: x['index'])
    
    squares = []
    rectangles = []
    
    for i in range(1, len(all_swings)):
        prev = all_swings[i-1]
        curr = all_swings[i]
        
        time_distance = curr['index'] - prev['index']
        price_distance = abs(curr['price'] - prev['price'])
        
        # Normalize price to comparable scale (percentage change)
        price_pct = (price_distance / prev['price']) * 100
        
        # Gann square: time ≈ price (in appropriate units)
        # For this analysis, we check if time_distance ≈ price_distance * scaling_factor
        # Scaling factor depends on instrument volatility
        
        if instrument == 'silver':
            # Silver: ~1 bar ≈ 0.1% price move
            scaling = 0.1
        else:
            # Gold: ~1 bar ≈ 0.05% price move
            scaling = 0.05
        
        normalized_price = price_pct / scaling
        ratio = time_distance / normalized_price if normalized_price > 0 else 0
        
        # Check for square (ratio ≈ 1)
        is_square = 0.8 <= ratio <= 1.2
        
        # Check for common Gann ratios (1x1, 1x2, 2x1, etc.)
        gann_ratios = [0.5, 1.0, 2.0, 4.0]
        matched_ratio = None
        for gr in gann_ratios:
            if abs(ratio - gr) / gr < 0.2:  # Within 20%
                matched_ratio = gr
                break
        
        squares.append({
            'from_idx': prev['index'],
            'to_idx': curr['index'],
            'time_dist': time_distance,
            'price_dist': price_pct,
            'ratio': ratio,
            'is_square': is_square,
            'gann_ratio': matched_ratio,
            'from_type': prev['type'],
            'to_type': curr['type'],
        })
    
    # Analyze square occurrences
    square_count = sum(1 for s in squares if s['is_square'])
    square_pct = (square_count / len(squares) * 100) if squares else 0
    
    gann_ratio_counts = Counter(s['gann_ratio'] for s in squares if s['gann_ratio'])
    
    print(f"\nTotal Swing Transitions: {len(squares)}")
    print(f"Price-Time Squares (ratio 0.8-1.2): {square_count} ({square_pct:.1f}%)")
    print(f"\nGann Ratio Distribution:")
    for ratio, count in sorted(gann_ratio_counts.items()):
        pct = (count / len(squares) * 100) if squares else 0
        print(f"  {ratio}x: {count} ({pct:.1f}%)")
    
    # Find strongest squares
    perfect_squares = [s for s in squares if s['is_square']]
    if perfect_squares:
        print(f"\nExample Perfect Squares (time ≈ price):")
        for s in perfect_squares[:5]:
            print(f"  Bar {s['from_idx']}→{s['to_idx']}: {s['time_dist']} bars, {s['price_dist']:.2f}%, ratio={s['ratio']:.2f}")
    
    return {
        'total': len(squares),
        'square_count': square_count,
        'square_percentage': square_pct,
        'gann_ratios': dict(gann_ratio_counts),
        'squares': perfect_squares[:20],  # Top 20 examples
    }


# ============================================================================
# RESEARCH 4: SWING SEQUENCE PATTERNS (MARKOV CHAIN)
# ============================================================================

def analyze_swing_sequences(df, instrument, lookback):
    """Analyze swing sequence patterns using Markov chain analysis."""
    print(f"\n{'='*70}")
    print(f"RESEARCH 4: Swing Sequence Patterns (Markov Chain) - {instrument.upper()}")
    print(f"{'='*70}")
    
    swing_highs, swing_lows = detect_swings(df, lookback)
    all_swings = sorted(swing_highs + swing_lows, key=lambda x: x['index'])
    
    # Create sequence of swing types
    sequence = [s['type'] for s in all_swings]
    
    # Analyze transitions
    transitions = defaultdict(Counter)
    for i in range(len(sequence) - 1):
        current = sequence[i]
        next_type = sequence[i + 1]
        transitions[current][next_type] += 1
    
    # Calculate transition probabilities
    transition_probs = {}
    for current, next_counts in transitions.items():
        total = sum(next_counts.values())
        transition_probs[current] = {
            next_type: (count / total * 100)
            for next_type, count in next_counts.items()
        }
    
    print(f"\nTotal Swings: {len(sequence)}")
    print(f"Sequence: {''.join(sequence[:50])}... ({len(sequence)} total)")
    print(f"\nTransition Probabilities:")
    for current, probs in transition_probs.items():
        print(f"\n  From {current}:")
        for next_type, prob in sorted(probs.items(), key=lambda x: -x[1]):
            print(f"    → {next_type}: {prob:.1f}%")
    
    # Analyze 3-swing patterns
    patterns_3 = Counter()
    for i in range(len(sequence) - 2):
        pattern = ''.join(sequence[i:i+3])
        patterns_3[pattern] += 1
    
    print(f"\nTop 3-Swing Patterns:")
    total_3 = sum(patterns_3.values())
    for pattern, count in patterns_3.most_common(10):
        pct = (count / total_3 * 100)
        print(f"  {pattern}: {count} ({pct:.1f}%)")
    
    # Analyze 4-swing patterns
    patterns_4 = Counter()
    for i in range(len(sequence) - 3):
        pattern = ''.join(sequence[i:i+4])
        patterns_4[pattern] += 1
    
    print(f"\nTop 4-Swing Patterns:")
    total_4 = sum(patterns_4.values())
    for pattern, count in patterns_4.most_common(10):
        pct = (count / total_4 * 100)
        print(f"  {pattern}: {count} ({pct:.1f}%)")
    
    # Predictive power analysis
    # After H-L pattern, what's probability of H vs L?
    hl_transitions = Counter()
    for i in range(len(sequence) - 2):
        if sequence[i:i+2] == ['H', 'L']:
            hl_transitions[sequence[i+2]] += 1
    
    print(f"\nAfter H-L Pattern:")
    total_hl = sum(hl_transitions.values())
    for next_type, count in hl_transitions.items():
        pct = (count / total_hl * 100) if total_hl > 0 else 0
        print(f"  Next: {next_type} = {count} ({pct:.1f}%)")
    
    # After L-H pattern
    lh_transitions = Counter()
    for i in range(len(sequence) - 2):
        if sequence[i:i+2] == ['L', 'H']:
            lh_transitions[sequence[i+2]] += 1
    
    print(f"\nAfter L-H Pattern:")
    total_lh = sum(lh_transitions.values())
    for next_type, count in lh_transitions.items():
        pct = (count / total_lh * 100) if total_lh > 0 else 0
        print(f"  Next: {next_type} = {count} ({pct:.1f}%)")
    
    return {
        'total_swings': len(sequence),
        'sequence': ''.join(sequence),
        'transition_probs': transition_probs,
        'patterns_3': dict(patterns_3.most_common(20)),
        'patterns_4': dict(patterns_4.most_common(20)),
        'hl_next': dict(hl_transitions),
        'lh_next': dict(lh_transitions),
    }


# ============================================================================
# VISUALIZATION
# ============================================================================

def create_deep_research_visuals(results, instrument):
    """Create comprehensive visualization of all 4 research areas."""
    print(f"\n{'='*70}")
    print(f"Creating Visualizations - {instrument.upper()}")
    print(f"{'='*70}")
    
    fig = plt.figure(figsize=(20, 24))
    gs = GridSpec(4, 2, figure=fig, hspace=0.35, wspace=0.3)
    
    # Colors
    colors = {'H': '#f85149', 'L': '#3fb950', 'fib': '#58a6ff'}
    
    # ---------------------------------------------------------------------
    # Plot 1: Multi-Timeframe Swing Count
    # ---------------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0])
    tf_data = results.get('multi_timeframe', {})
    if tf_data:
        tfs = list(tf_data.keys())
        swing_counts = [tf_data[tf]['num_swings'] for tf in tfs]
        bars = ax1.bar(tfs, swing_counts, color=colors['fib'], edgecolor='white', linewidth=2)
        ax1.set_ylabel('Number of Swings', fontsize=11)
        ax1.set_title('Swing Count by Timeframe', fontsize=13, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        
        for bar, count in zip(bars, swing_counts):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    str(count), ha='center', va='bottom', fontsize=10)
    
    # ---------------------------------------------------------------------
    # Plot 2: Fib Number Occurrence by Timeframe
    # ---------------------------------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    if tf_data:
        tfs = list(tf_data.keys())
        fib_pcts = [tf_data[tf]['fib_occurrence_pct'] for tf in tfs]
        bars = ax2.bar(tfs, fib_pcts, color=colors['fib'], edgecolor='white', linewidth=2)
        ax2.set_ylabel('Fib Number Occurrence (%)', fontsize=11)
        ax2.set_title('Swing Intervals at Fib Numbers by Timeframe', fontsize=13, fontweight='bold')
        ax2.axhline(y=20, color='orange', linestyle='--', alpha=0.7, label='20% threshold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        for bar, pct in zip(bars, fib_pcts):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{pct:.1f}%', ha='center', va='bottom', fontsize=10)
    
    # ---------------------------------------------------------------------
    # Plot 3: Fib Candle Count Distribution
    # ---------------------------------------------------------------------
    ax3 = fig.add_subplot(gs[1, 0])
    fib_results = results.get('fib_candle_counts', {})
    if fib_results:
        all_intervals = []
        for pattern in ['HH', 'LL', 'HL', 'LH']:
            if pattern in fib_results and fib_results[pattern]:
                # Reconstruct intervals from top_intervals
                for interval, count in fib_results[pattern].get('top_intervals', []):
                    all_intervals.extend([interval] * count)
        
        if all_intervals:
            ax3.hist(all_intervals, bins=30, color=colors['fib'], alpha=0.7, edgecolor='white')
            # Mark Fib numbers
            for fib in FIB_NUMBERS[:8]:  # First 8 Fib numbers
                ax3.axvline(x=fib, color='orange', linestyle='--', alpha=0.7, linewidth=2)
            ax3.set_xlabel('Candle Count Between Swings', fontsize=11)
            ax3.set_ylabel('Frequency', fontsize=11)
            ax3.set_title('Distribution of Swing Intervals with Fib Number Markers', fontsize=13, fontweight='bold')
            ax3.grid(True, alpha=0.3)
    
    # ---------------------------------------------------------------------
    # Plot 4: Gann Ratio Distribution
    # ---------------------------------------------------------------------
    ax4 = fig.add_subplot(gs[1, 1])
    gann_results = results.get('price_time_squaring', {})
    if gann_results:
        ratios = list(gann_results.get('gann_ratios', {}).keys())
        counts = list(gann_results.get('gann_ratios', {}).values())
        if ratios:
            bars = ax4.bar([str(r) for r in ratios], counts, color=colors['fib'], edgecolor='white', linewidth=2)
            ax4.set_xlabel('Gann Ratio (Time/Price)', fontsize=11)
            ax4.set_ylabel('Count', fontsize=11)
            ax4.set_title('Price-Time Squaring: Gann Ratio Distribution', fontsize=13, fontweight='bold')
            ax4.grid(True, alpha=0.3)
            
            for bar, count in zip(bars, counts):
                ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        str(count), ha='center', va='bottom', fontsize=10)
    
    # ---------------------------------------------------------------------
    # Plot 5: Markov Transition Matrix
    # ---------------------------------------------------------------------
    ax5 = fig.add_subplot(gs[2, 0])
    markov_results = results.get('swing_sequences', {})
    if markov_results:
        trans_probs = markov_results.get('transition_probs', {})
        if trans_probs:
            # Create transition matrix
            states = ['H', 'L']
            matrix = np.zeros((2, 2))
            for i, from_state in enumerate(states):
                for j, to_state in enumerate(states):
                    if from_state in trans_probs and to_state in trans_probs[from_state]:
                        matrix[i, j] = trans_probs[from_state][to_state]
            
            im = ax5.imshow(matrix, cmap='Blues', vmin=0, vmax=100)
            ax5.set_xticks([0, 1])
            ax5.set_yticks([0, 1])
            ax5.set_xticklabels(['→H', '→L'])
            ax5.set_yticklabels(['H→', 'L→'])
            ax5.set_title('Swing Transition Probability Matrix (%)', fontsize=13, fontweight='bold')
            
            # Add text annotations
            for i in range(2):
                for j in range(2):
                    ax5.text(j, i, f'{matrix[i, j]:.1f}%', ha='center', va='center',
                            fontsize=14, fontweight='bold',
                            color='white' if matrix[i, j] > 50 else 'black')
            
            plt.colorbar(im, ax=ax5, label='Probability (%)')
    
    # ---------------------------------------------------------------------
    # Plot 6: 3-Swing Pattern Frequencies
    # ---------------------------------------------------------------------
    ax6 = fig.add_subplot(gs[2, 1])
    if markov_results:
        patterns_3 = markov_results.get('patterns_3', {})
        if patterns_3:
            top_patterns = sorted(patterns_3.items(), key=lambda x: -x[1])[:8]
            patterns = [p[0] for p in top_patterns]
            counts = [p[1] for p in top_patterns]
            
            colors_pattern = [colors['H'] if p.count('H') > p.count('L') else colors['L'] for p in patterns]
            bars = ax6.bar(patterns, counts, color=colors_pattern, edgecolor='white', linewidth=2)
            ax6.set_xlabel('3-Swing Pattern', fontsize=11)
            ax6.set_ylabel('Frequency', fontsize=11)
            ax6.set_title('Top 3-Swing Sequence Patterns', fontsize=13, fontweight='bold')
            ax6.grid(True, alpha=0.3, axis='y')
            
            for bar, count in zip(bars, counts):
                ax6.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        str(count), ha='center', va='bottom', fontsize=10)
    
    # ---------------------------------------------------------------------
    # Plot 7: After H-L Pattern - Next Swing
    # ---------------------------------------------------------------------
    ax7 = fig.add_subplot(gs[3, 0])
    if markov_results:
        hl_next = markov_results.get('hl_next', {})
        if hl_next:
            states = list(hl_next.keys())
            counts = [hl_next[s] for s in states]
            total = sum(counts)
            pcts = [(c / total * 100) if total > 0 else 0 for c in counts]
            
            colors_hl = [colors['H'] if s == 'H' else colors['L'] for s in states]
            bars = ax7.bar(states, pcts, color=colors_hl, edgecolor='white', linewidth=2)
            ax7.set_ylabel('Probability (%)', fontsize=11)
            ax7.set_title('After H-L Pattern: Next Swing Probability', fontsize=13, fontweight='bold')
            ax7.grid(True, alpha=0.3, axis='y')
            
            for bar, pct in zip(bars, pcts):
                ax7.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f'{pct:.1f}%', ha='center', va='bottom', fontsize=10)
    
    # ---------------------------------------------------------------------
    # Plot 8: After L-H Pattern - Next Swing
    # ---------------------------------------------------------------------
    ax8 = fig.add_subplot(gs[3, 1])
    if markov_results:
        lh_next = markov_results.get('lh_next', {})
        if lh_next:
            states = list(lh_next.keys())
            counts = [lh_next[s] for s in states]
            total = sum(counts)
            pcts = [(c / total * 100) if total > 0 else 0 for c in counts]
            
            colors_lh = [colors['H'] if s == 'H' else colors['L'] for s in states]
            bars = ax8.bar(states, pcts, color=colors_lh, edgecolor='white', linewidth=2)
            ax8.set_ylabel('Probability (%)', fontsize=11)
            ax8.set_title('After L-H Pattern: Next Swing Probability', fontsize=13, fontweight='bold')
            ax8.grid(True, alpha=0.3, axis='y')
            
            for bar, pct in zip(bars, pcts):
                ax8.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f'{pct:.1f}%', ha='center', va='bottom', fontsize=10)
    
    # Save figure
    plt.suptitle(f'Deep Swing Research - {instrument.upper()}', fontsize=16, fontweight='bold', y=0.995)
    output_path = f'{OUTPUT_DIR}/deep_swing_research_{instrument}.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='#0d1117')
    print(f"Saved: {output_path}")
    plt.close()
    
    return output_path


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("="*70)
    print("DEEP SWING RESEARCH - Geometric Pattern Discovery")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = {}
    
    for instrument in ['silver', 'gold']:
        print(f"\n{'#'*70}")
        print(f"# INSTRUMENT: {instrument.upper()}")
        print(f"{'#'*70}")
        
        # Load data
        df = load_data(DATA_PATHS[instrument])
        print(f"Loaded {len(df):,} candles from {DATA_PATHS[instrument]}")
        
        lookback = 6 if instrument == 'silver' else 8
        
        # Run all 4 research analyses
        results = {}
        
        # Research 1: Multi-timeframe
        results['multi_timeframe'] = analyze_multi_timeframe_swings(df, instrument)
        
        # Research 2: Fib candle counts
        results['fib_candle_counts'] = analyze_fib_candle_counts(df, instrument, lookback)
        
        # Research 3: Price-time squaring
        results['price_time_squaring'] = analyze_price_time_squaring(df, instrument, lookback)
        
        # Research 4: Swing sequences
        results['swing_sequences'] = analyze_swing_sequences(df, instrument, lookback)
        
        # Create visualizations
        create_deep_research_visuals(results, instrument)
        
        all_results[instrument] = results
        
        # Save JSON report
        report_path = f'{OUTPUT_DIR}/deep_swing_research_{instrument}.json'
        with open(report_path, 'w') as f:
            # Convert numpy types to Python types for JSON serialization
            def convert(obj):
                if isinstance(obj, np.integer): return int(obj)
                if isinstance(obj, np.floating): return float(obj)
                if isinstance(obj, np.ndarray): return obj.tolist()
                if isinstance(obj, dict): return {k: convert(v) for k, v in obj.items()}
                if isinstance(obj, list): return [convert(i) for i in obj]
                return obj
            
            json.dump(convert(results), f, indent=2, default=str)
        print(f"Saved: {report_path}")
    
    print(f"\n{'='*70}")
    print(f"Research Complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    
    return all_results


if __name__ == '__main__':
    main()
