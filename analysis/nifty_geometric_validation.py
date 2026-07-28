"""
NIFTY50 GEOMETRIC LAW VALIDATION
=================================
Tests all 4 geometric laws discovered in deep_swing_research on Nifty50 5min data:
1. 0.382 Price Law - % of swings retracing to 0.382
2. Fib Time Law - % of swings occurring within ±1 bar of Fib numbers
3. Gann Square Law - % of transitions forming price-time squares
4. 82% Reversal Law - reversal probability after H-L or L-H patterns

Also tests optimal configuration (lookback=8, mult=0.5, entry=0.382)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime

# Load Nifty data
DATA_PATH = Path('/home/palbot/Projects/log-fib-scalper/zerodha_data/NIFTY_50_5minute_20260319_20260518.csv')

print("=" * 80)
print("NIFTY50 GEOMETRIC LAW VALIDATION")
print("=" * 80)

df = pd.read_csv(DATA_PATH)

# Handle Zerodha format
if 'date' in df.columns:
    df['time'] = pd.to_datetime(df['date'])
elif 'datetime' in df.columns:
    df['time'] = pd.to_datetime(df['datetime'])
elif 'time' not in df.columns:
    raise ValueError("No time/date column found")

df = df.dropna(subset=['high', 'low'])
df = df.reset_index(drop=True)

print(f"\n📊 NIFTY50 Data: {len(df):,} bars")
print(f"   Range: {df['time'].min()} to {df['time'].max()}")
print(f"   Price: {df['close'].iloc[0]:.2f} → {df['close'].iloc[-1]:.2f}")

# ============================================================================
# SWING DETECTION
# ============================================================================

def detect_swing_highs(df, lookback=8):
    """Detect swing highs using lookback fractal"""
    swings = []
    for i in range(lookback, len(df) - lookback):
        window = df.iloc[i-lookback:i+lookback+1]
        if df['high'].iloc[i] == window['high'].max():
            swings.append({
                'idx': i,
                'type': 'HIGH',
                'price': df['high'].iloc[i],
                'time': df['time'].iloc[i],
                'bar': i
            })
    return swings

def detect_swing_lows(df, lookback=8):
    """Detect swing lows using lookback fractal"""
    swings = []
    for i in range(lookback, len(df) - lookback):
        window = df.iloc[i-lookback:i+lookback+1]
        if df['low'].iloc[i] == window['low'].min():
            swings.append({
                'idx': i,
                'type': 'LOW',
                'price': df['low'].iloc[i],
                'time': df['time'].iloc[i],
                'bar': i
            })
    return swings

print("\n" + "=" * 80)
print("SWING DETECTION (lookback=8)")
print("=" * 80)

swing_highs = detect_swing_highs(df, lookback=8)
swing_lows = detect_swing_lows(df, lookback=8)

print(f"Swing Highs: {len(swing_highs)}")
print(f"Swing Lows: {len(swing_lows)}")

# Merge and sort all swings
all_swings = sorted(swing_highs + swing_lows, key=lambda x: x['idx'])

# ============================================================================
# LAW 1: 0.382 PRICE RETRACEMENT
# ============================================================================

print("\n" + "=" * 80)
print("LAW 1: 0.382 PRICE RETRACEMENT")
print("=" * 80)

fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
retracement_hits = {level: 0 for level in fib_levels}
total_retracements = 0

for i in range(len(all_swings) - 1):
    swing1 = all_swings[i]
    swing2 = all_swings[i + 1]
    
    # Skip same-type swings
    if swing1['type'] == swing2['type']:
        continue
    
    total_retracements += 1
    
    # Calculate retracement
    if swing1['type'] == 'HIGH' and swing2['type'] == 'LOW':
        move = swing1['price'] - swing2['price']
        # Check how much of the move happened before reversal
        # Look at the next swing to measure retracement
        if i + 2 < len(all_swings):
            swing3 = all_swings[i + 2]
            if swing3['type'] == 'HIGH':
                retracement = (swing3['price'] - swing2['price']) / move
                for level in fib_levels:
                    if abs(retracement - level) < 0.05:  # ±5% tolerance
                        retracement_hits[level] += 1
    elif swing1['type'] == 'LOW' and swing2['type'] == 'HIGH':
        move = swing2['price'] - swing1['price']
        if i + 2 < len(all_swings):
            swing3 = all_swings[i + 2]
            if swing3['type'] == 'LOW':
                retracement = (swing2['price'] - swing3['price']) / move
                for level in fib_levels:
                    if abs(retracement - level) < 0.05:
                        retracement_hits[level] += 1

print(f"\nTotal retracements measured: {total_retracements}")
print("\nFibonacci Retracement Hits:")
for level in fib_levels:
    hits = retracement_hits[level]
    pct = (hits / total_retracements * 100) if total_retracements > 0 else 0
    marker = " ← PRIMARY" if level == 0.382 else ""
    print(f"  {level:.3f}: {hits:4d} ({pct:5.1f}%){marker}")

# ============================================================================
# LAW 2: FIB TIME SYMMETRY
# ============================================================================

print("\n" + "=" * 80)
print("LAW 2: FIB TIME SYMMETRY")
print("=" * 80)

fib_numbers = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
time_hits = {fib: 0 for fib in fib_numbers}
total_intervals = 0

for i in range(len(all_swings) - 1):
    swing1 = all_swings[i]
    swing2 = all_swings[i + 1]
    
    bar_distance = abs(swing2['bar'] - swing1['bar'])
    total_intervals += 1
    
    # Check if distance is within ±1 of any Fib number
    for fib in fib_numbers:
        if abs(bar_distance - fib) <= 1:
            time_hits[fib] += 1
            break

# Count swings within ±1 of ANY Fib number
swings_near_fib = sum(1 for i in range(len(all_swings) - 1) 
                      if any(abs(all_swings[i+1]['bar'] - all_swings[i]['bar'] - fib) <= 1 
                            for fib in fib_numbers))

print(f"\nTotal swing intervals: {total_intervals}")
print(f"Swings within ±1 bar of Fib number: {swings_near_fib}")
print(f"Fib Time Occurrence: {swings_near_fib/total_intervals*100:.1f}%")

print("\nBreakdown by Fib number:")
for fib in fib_numbers:
    hits = time_hits[fib]
    pct = (hits / total_intervals * 100) if total_intervals > 0 else 0
    if hits > 0:
        print(f"  Fib {fib:3d}: {hits:4d} ({pct:5.1f}%)")

# ============================================================================
# LAW 3: GANN SQUARE FORMATION
# ============================================================================

print("\n" + "=" * 80)
print("LAW 3: GANN SQUARE FORMATION")
print("=" * 80)

# Gann scaling for Nifty: 1 bar ≈ 0.15% price move
GANN_SCALE = 0.0015  # 0.15%

perfect_squares = 0
near_squares = 0
total_transitions = 0

for i in range(len(all_swings) - 1):
    swing1 = all_swings[i]
    swing2 = all_swings[i + 1]
    
    if swing1['type'] == swing2['type']:
        continue
    
    total_transitions += 1
    
    # Calculate price move in %
    price_move_pct = abs(swing2['price'] - swing1['price']) / swing1['price']
    time_move = abs(swing2['bar'] - swing1['bar'])
    
    # Convert time to "price units" using Gann scaling
    time_in_price_units = time_move * GANN_SCALE
    
    # Check for square formation
    ratio = price_move_pct / time_in_price_units if time_in_price_units > 0 else 0
    
    if 0.95 <= ratio <= 1.05:
        perfect_squares += 1
    elif 0.85 <= ratio <= 1.15:
        near_squares += 1

print(f"\nTotal transitions: {total_transitions}")
print(f"Perfect squares (0.95-1.05): {perfect_squares} ({perfect_squares/total_transitions*100:.1f}%)")
print(f"Near squares (0.85-1.15): {near_squares} ({near_squares/total_transitions*100:.1f}%)")
print(f"Total square formations: {perfect_squares + near_squares} ({(perfect_squares+near_squares)/total_transitions*100:.1f}%)")

# ============================================================================
# LAW 4: 82% REVERSAL PATTERN
# ============================================================================

print("\n" + "=" * 80)
print("LAW 4: 82% REVERSAL PATTERN (H-L / L-H)")
print("=" * 80)

# Count H-L-H and L-H-L patterns (reversals) vs H-H and L-L (continuations)
reversal_count = 0
continuation_count = 0

for i in range(len(all_swings) - 2):
    s1 = all_swings[i]
    s2 = all_swings[i + 1]
    s3 = all_swings[i + 2]
    
    if s1['type'] != s2['type'] and s2['type'] != s3['type']:
        # This is a reversal pattern (H-L-H or L-H-L)
        reversal_count += 1
    elif s1['type'] == s2['type'] or s2['type'] == s3['type']:
        # This is a continuation pattern
        continuation_count += 1

total_patterns = reversal_count + continuation_count
reversal_rate = reversal_count / total_patterns * 100 if total_patterns > 0 else 0

print(f"\nReversal patterns (H-L-H, L-H-L): {reversal_count}")
print(f"Continuation patterns: {continuation_count}")
print(f"Reversal rate: {reversal_rate:.1f}%")

# ============================================================================
# OPTIMAL CONFIGURATION BACKTEST
# ============================================================================

print("\n" + "=" * 80)
print("OPTIMAL CONFIGURATION BACKTEST")
print("=" * 80)
print("Config: lookback=8, mult=0.5, entry=0.382, TP=1.272, SL=1.618")

def backtest_config(df, swings, lookback=8, mult=0.5, entry_ratio=0.382, tp_ratio=1.272, sl_ratio=1.618):
    """Backtest the optimal configuration on Nifty"""
    trades = []
    
    for i in range(len(swings) - 2):
        swing1 = swings[i]
        swing2 = swings[i + 1]
        swing3 = swings[i + 2]
        
        # Need opposite swings
        if swing1['type'] == swing2['type']:
            continue
        
        # Calculate effective range
        pivot = swing2
        anchor = swing1
        price_range = abs(pivot['price'] - anchor['price'])
        effective_range = np.log10(pivot['price']) * price_range * mult * 4
        
        # Determine direction
        if pivot['type'] == 'LOW':
            # Bullish setup - entry above pivot
            entry_price = pivot['price'] + (entry_ratio * effective_range)
            tp_price = pivot['price'] + (tp_ratio * effective_range)
            sl_price = pivot['price'] - (sl_ratio * effective_range)
            direction = 'LONG'
        else:
            # Bearish setup - entry below pivot
            entry_price = pivot['price'] - (entry_ratio * effective_range)
            tp_price = pivot['price'] - (tp_ratio * effective_range)
            sl_price = pivot['price'] + (sl_ratio * effective_range)
            direction = 'SHORT'
        
        # Find bars after swing2 where price could have entered
        start_idx = swing2['idx'] + 1
        end_idx = min(start_idx + 50, len(df) - 1)  # Look 50 bars forward
        
        entered = False
        exit_price = None
        exit_type = None
        
        for j in range(start_idx, end_idx):
            bar = df.iloc[j]
            
            if direction == 'LONG':
                if bar['low'] <= entry_price:
                    entered = True
                    # Check TP/SL
                    if bar['high'] >= tp_price:
                        exit_price = tp_price
                        exit_type = 'TP'
                    elif bar['low'] <= sl_price:
                        exit_price = sl_price
                        exit_type = 'SL'
            else:  # SHORT
                if bar['high'] >= entry_price:
                    entered = True
                    if bar['low'] <= tp_price:
                        exit_price = tp_price
                        exit_type = 'TP'
                    elif bar['high'] >= sl_price:
                        exit_price = sl_price
                        exit_type = 'SL'
            
            if entered and exit_price:
                break
        
        if entered and exit_price:
            pnl_pct = (exit_price - entry_price) / entry_price * 100
            if direction == 'SHORT':
                pnl_pct = -pnl_pct
            
            trades.append({
                'direction': direction,
                'entry': entry_price,
                'exit': exit_price,
                'exit_type': exit_type,
                'pnl_pct': pnl_pct,
                'bar': swing2['idx']
            })
    
    return trades

trades = backtest_config(df, all_swings)

if trades:
    wins = sum(1 for t in trades if t['exit_type'] == 'TP')
    losses = sum(1 for t in trades if t['exit_type'] == 'SL')
    total = len(trades)
    wr = wins / total * 100
    
    total_pnl = sum(t['pnl_pct'] for t in trades)
    avg_pnl = total_pnl / total
    
    print(f"\nTotal trades: {total}")
    print(f"Wins (TP): {wins}")
    print(f"Losses (SL): {losses}")
    print(f"Win rate: {wr:.1f}%")
    print(f"Total PnL: {total_pnl:.2f}%")
    print(f"Average PnL per trade: {avg_pnl:.3f}%")
else:
    print("\nNo trades generated with this configuration")

# ============================================================================
# SUMMARY COMPARISON
# ============================================================================

print("\n" + "=" * 80)
print("SUMMARY: NIFTY50 vs SILVER vs GOLD")
print("=" * 80)

print("""
Geometric Law          | Nifty50  | Silver   | Gold
-----------------------|----------|----------|----------
0.382 Retracement      | TBD      | 70-82%   | 70-82%
Fib Time (±1 bar)      | TBD      | 74-92%   | 74-92%
Gann Squares           | TBD      | ~22%     | ~22%
Reversal Rate          | TBD      | 80-85%   | 80-85%
""")

print("\n✅ Analysis complete!")
print(f"\nOutput saved to: analysis/nifty_geometric_validation.png")

# Create visualization
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('NIFTY50 Geometric Law Validation', fontsize=14, fontweight='bold')

# Plot 1: Retracement levels
ax1 = axes[0, 0]
levels = list(fib_levels)
pcts = [retracement_hits[l] / total_retracements * 100 for l in levels]
bars = ax1.bar([str(l) for l in levels], pcts, color='steelblue', alpha=0.7)
ax1.axhline(y=70, color='green', linestyle='--', alpha=0.5, label='70% threshold')
ax1.set_ylabel('Hit Rate (%)')
ax1.set_title('Law 1: Fibonacci Retracement')
ax1.tick_params(axis='x', rotation=45)
for bar, pct in zip(bars, pcts):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
             f'{pct:.1f}%', ha='center', va='bottom', fontsize=9)

# Plot 2: Fib time distribution
ax2 = axes[0, 1]
fib_hit_fibs = [f for f in fib_numbers if time_hits[f] > 0]
fib_hit_counts = [time_hits[f] for f in fib_hit_fibs]
ax2.bar([str(f) for f in fib_hit_fibs], fib_hit_counts, color='coral', alpha=0.7)
ax2.set_xlabel('Fibonacci Number (bars)')
ax2.set_ylabel('Count')
ax2.set_title('Law 2: Fib Time Symmetry')
ax2.tick_params(axis='x', rotation=45)

# Plot 3: Gann squares
ax3 = axes[1, 0]
categories = ['Perfect\n(0.95-1.05)', 'Near\n(0.85-1.15)', 'Non-Square']
counts = [perfect_squares, near_squares, total_transitions - perfect_squares - near_squares]
colors = ['darkgreen', 'lightgreen', 'lightgray']
ax3.bar(categories, counts, color=colors, alpha=0.7)
ax3.set_ylabel('Count')
ax3.set_title('Law 3: Gann Square Formation')
for i, c in enumerate(counts):
    pct = c / total_transitions * 100
    ax3.text(i, c + 5, f'{c}\n({pct:.1f}%)', ha='center', va='bottom')

# Plot 4: Reversal vs Continuation
ax4 = axes[1, 1]
ax4.pie([reversal_count, continuation_count], 
        labels=[f'Reversal\n({reversal_rate:.1f}%)', f'Continuation\n({100-reversal_rate:.1f}%)'],
        colors=['steelblue', 'lightgray'],
        autopct='%1.1f%%')
ax4.set_title('Law 4: Reversal Patterns')

plt.tight_layout()
plt.savefig('analysis/nifty_geometric_validation.png', dpi=150, bbox_inches='tight')
plt.close()

print(f"Visualization saved to: analysis/nifty_geometric_validation.png")
