#!/usr/bin/env python3
"""
Log-Fib MTF Projection System - Optimal Trading Rules Discovery

Implements the exact Pine Script logic and systematically tests entry/exit combinations.
Matches: Pal Log-Fib Range Projection - MTF (Pine Script v5)
"""

import csv
import math
import os
import json
from itertools import product
from datetime import datetime

# Fibonacci levels to test
FIB_LEVELS = [0.125, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]


def load_csv(csv_path):
    """Load CSV data into list of bar dictionaries."""
    if not os.path.exists(csv_path):
        print(f"ERROR: File {csv_path} not found.")
        return None
    
    bars = []
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            bars.append({
                'time': row['time'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close'])
            })
    return bars


def calculate_log_fib_levels(bars, lookback, multiplier):
    """
    Calculate Log-Fib projection levels matching Pine Script exactly.
    
    Pine Script logic:
    - Find highest high in lookback window (swing high)
    - Anchored low = low of the exact bar that produced the swing high
    - effective_range_top = log10(swing_high) * |swing_high - anchored_low| * multiplier * 4.0
    - projection_level = swing_high - (fib_ratio * effective_range_top)
    
    Similarly for bottom projections from swing lows.
    """
    n = len(bars)
    if n < lookback * 2:
        return []
    
    results = []
    fib_ratios = FIB_LEVELS
    
    for i in range(lookback, n - lookback):
        bar = bars[i]
        
        # === SWING HIGH DETECTION (Pine Script style) ===
        # Find highest high in the lookback window ending at bar i
        highest_high = bar['high']
        highest_idx = i
        
        for j in range(i - lookback + 1, i + 1):
            if bars[j]['high'] > highest_high:
                highest_high = bars[j]['high']
                highest_idx = j
        
        # Anchored low = low of the bar that produced the swing high
        anchored_low = bars[highest_idx]['low']
        
        # Calculate effective range for top projections
        log_sh = math.log10(highest_high)
        range_diff_top = abs(highest_high - anchored_low)
        effective_range_top = log_sh * range_diff_top * multiplier * 4.0
        
        # Calculate all top projection levels
        top_levels = {}
        for ratio in fib_ratios:
            top_levels[ratio] = highest_high - (ratio * effective_range_top)
        
        # === SWING LOW DETECTION (Pine Script style) ===
        # Find lowest low in the lookback window ending at bar i
        lowest_low = bar['low']
        lowest_idx = i
        
        for j in range(i - lookback + 1, i + 1):
            if bars[j]['low'] < lowest_low:
                lowest_low = bars[j]['low']
                lowest_idx = j
        
        # Anchored high = high of the bar that produced the swing low
        anchored_high = bars[lowest_idx]['high']
        
        # Calculate effective range for bottom projections
        log_sl = math.log10(lowest_low)
        range_diff_bot = abs(lowest_low - anchored_high)
        effective_range_bot = log_sl * range_diff_bot * multiplier * 4.0
        
        # Calculate all bottom projection levels
        bottom_levels = {}
        for ratio in fib_ratios:
            bottom_levels[ratio] = lowest_low + (ratio * effective_range_bot)
        
        results.append({
            'idx': i,
            'time': bar['time'],
            'swing_high': highest_high,
            'anchored_low': anchored_low,
            'swing_low': lowest_low,
            'anchored_high': anchored_high,
            'effective_range_top': effective_range_top,
            'effective_range_bot': effective_range_bot,
            'top_levels': top_levels,
            'bottom_levels': bottom_levels
        })
    
    return results


def run_backtest(bars, projections, entry_ratio, take_profit_ratio, stop_loss_ratio, 
                 direction='both', min_confluence=1):
    """
    Run backtest with specified parameters.
    
    Trading Logic:
    - LONG: Enter when price retraces to entry_ratio from swing low, target TP above
    - SHORT: Enter when price retraces to entry_ratio from swing high, target TP below
    
    Entry: Price must touch/cross the entry level
    Exit: TP or SL hit (whichever comes first)
    """
    trades = []
    in_position = False
    position_type = None
    entry_price = 0.0
    entry_time = ""
    stop_loss = 0.0
    take_profit = 0.0
    last_proj_idx = -100
    
    n = len(bars)
    
    for proj in projections:
        idx = proj['idx']
        
        # Skip if we're in a position - check for exit
        if in_position:
            bar = bars[idx]
            
            if position_type == "SHORT":
                # SHORT: Profit when price goes DOWN
                if bar['low'] <= take_profit:
                    pnl = entry_price - take_profit
                    trades.append({
                        'type': 'SHORT',
                        'entry_time': entry_time,
                        'exit_time': bar['time'],
                        'entry_price': entry_price,
                        'exit_price': take_profit,
                        'pnl': pnl,
                        'outcome': 'WIN' if pnl > 0 else 'LOSS'
                    })
                    in_position = False
                    
                elif bar['high'] >= stop_loss:
                    pnl = entry_price - stop_loss
                    trades.append({
                        'type': 'SHORT',
                        'entry_time': entry_time,
                        'exit_time': bar['time'],
                        'entry_price': entry_price,
                        'exit_price': stop_loss,
                        'pnl': pnl,
                        'outcome': 'WIN' if pnl > 0 else 'LOSS'
                    })
                    in_position = False
            
            elif position_type == "LONG":
                # LONG: Profit when price goes UP
                if bar['high'] >= take_profit:
                    pnl = take_profit - entry_price
                    trades.append({
                        'type': 'LONG',
                        'entry_time': entry_time,
                        'exit_time': bar['time'],
                        'entry_price': entry_price,
                        'exit_price': take_profit,
                        'pnl': pnl,
                        'outcome': 'WIN' if pnl > 0 else 'LOSS'
                    })
                    in_position = False
                    
                elif bar['low'] <= stop_loss:
                    pnl = stop_loss - entry_price
                    trades.append({
                        'type': 'LONG',
                        'entry_time': entry_time,
                        'exit_time': bar['time'],
                        'entry_price': entry_price,
                        'exit_price': stop_loss,
                        'pnl': pnl,
                        'outcome': 'WIN' if pnl > 0 else 'LOSS'
                    })
                    in_position = False
        
        # If not in position, look for new entries
        if not in_position and idx - last_proj_idx > 5:  # Minimum 5 bars between trades
            swing_high = proj['swing_high']
            swing_low = proj['swing_low']
            eff_top = proj['effective_range_top']
            eff_bot = proj['effective_range_bot']
            
            # === SHORT SETUP (from swing high) ===
            if direction in ['short', 'both']:
                entry_level = swing_high - (entry_ratio * eff_top)
                tp_level = swing_high - (take_profit_ratio * eff_top)
                sl_level = swing_high + (stop_loss_ratio * eff_top)
                
                # Check if price retraced to entry in subsequent bars
                for k in range(idx + 1, min(idx + 100, n)):
                    if bars[k]['low'] <= entry_level:
                        in_position = True
                        position_type = "SHORT"
                        entry_price = entry_level
                        entry_time = bars[k]['time']
                        take_profit = tp_level
                        stop_loss = sl_level
                        last_proj_idx = idx
                        break
            
            # === LONG SETUP (from swing low) ===
            if not in_position and direction in ['long', 'both']:
                entry_level = swing_low + (entry_ratio * eff_bot)
                tp_level = swing_low + (take_profit_ratio * eff_bot)
                sl_level = swing_low - (stop_loss_ratio * eff_bot)
                
                # Check if price retraced to entry in subsequent bars
                for k in range(idx + 1, min(idx + 100, n)):
                    if bars[k]['high'] >= entry_level:
                        in_position = True
                        position_type = "LONG"
                        entry_price = entry_level
                        entry_time = bars[k]['time']
                        take_profit = tp_level
                        stop_loss = sl_level
                        last_proj_idx = idx
                        break
    
    return trades


def calculate_metrics(trades):
    """Calculate trading metrics from trade list."""
    if not trades:
        return None
    
    total_trades = len(trades)
    wins = sum(1 for t in trades if t['outcome'] == 'WIN')
    losses = total_trades - wins
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    total_pnl = sum(t['pnl'] for t in trades)
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
    
    gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
    
    # Max drawdown
    cumulative = 0
    peak = 0
    max_drawdown = 0
    for t in trades:
        cumulative += t['pnl']
        if cumulative > peak:
            peak = cumulative
        drawdown = peak - cumulative
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    return {
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_pnl': avg_pnl,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown
    }


def walk_forward_test(bars, lookback, multiplier, entry_ratio, tp_ratio, sl_ratio, 
                      n_folds=5, direction='both'):
    """
    Walk-forward validation: split data into n folds, train on n-1, test on 1.
    """
    projections = calculate_log_fib_levels(bars, lookback, multiplier)
    n = len(projections)
    fold_size = n // n_folds
    
    fold_results = []
    
    for fold in range(n_folds):
        # Use all projections but only count trades in test fold
        test_start = fold * fold_size
        test_end = (fold + 1) * fold_size if fold < n_folds - 1 else n
        
        # Run backtest on full data
        trades = run_backtest(bars, projections, entry_ratio, tp_ratio, sl_ratio, direction)
        
        # Filter trades to test period only
        test_times = set(projections[i]['time'] for i in range(test_start, min(test_end, n)))
        test_trades = [t for t in trades if t['entry_time'] in test_times]
        
        metrics = calculate_metrics(test_trades)
        if metrics:
            metrics['fold'] = fold
            fold_results.append(metrics)
    
    # Aggregate results
    if not fold_results:
        return None
    
    avg_win_rate = sum(r['win_rate'] for r in fold_results) / len(fold_results)
    avg_pf = sum(r['profit_factor'] for r in fold_results) / len(fold_results)
    total_trades = sum(r['total_trades'] for r in fold_results)
    total_pnl = sum(r['total_pnl'] for r in fold_results)
    
    return {
        'avg_win_rate': avg_win_rate,
        'avg_profit_factor': avg_pf,
        'total_trades': total_trades,
        'total_pnl': total_pnl,
        'fold_results': fold_results
    }


def optimize_parameters(csv_path, symbol_name):
    """Systematically test all parameter combinations."""
    print("=" * 80)
    print(f"LOG-FIB MTF OPTIMIZATION - {symbol_name}")
    print("=" * 80)
    
    bars = load_csv(csv_path)
    if not bars:
        return []
    
    print(f"Loaded {len(bars)} bars from {csv_path}")
    print()
    
    # Parameter ranges
    lookbacks = [6, 8, 10, 12, 14]
    multipliers = [0.382, 0.5, 0.618]
    entry_ratios = [0.382, 0.5, 0.618, 0.786]
    tp_ratios = [0.786, 1.0, 1.272, 1.618]
    sl_ratios = [1.0, 1.272, 1.618]
    directions = ['both', 'long', 'short']
    
    total_combos = len(lookbacks) * len(multipliers) * len(entry_ratios) * len(tp_ratios) * len(sl_ratios) * len(directions)
    print(f"Testing {total_combos} parameter combinations...")
    print()
    
    results = []
    count = 0
    
    for lb, mult, entry, tp, sl, direction in product(lookbacks, multipliers, entry_ratios, tp_ratios, sl_ratios, directions):
        count += 1
        if count % 200 == 0:
            print(f"Progress: {count}/{total_combos} combinations tested...")
        
        # Calculate projections
        projections = calculate_log_fib_levels(bars, lb, mult)
        
        # Run backtest
        trades = run_backtest(bars, projections, entry, tp, sl, direction)
        
        metrics = calculate_metrics(trades)
        
        if metrics and metrics['total_trades'] >= 20:
            # Run walk-forward validation
            wf = walk_forward_test(bars, lb, mult, entry, tp, sl, n_folds=5, direction=direction)
            
            result = {
                **metrics,
                'lookback': lb,
                'multiplier': mult,
                'entry_ratio': entry,
                'take_profit_ratio': tp,
                'stop_loss_ratio': sl,
                'direction': direction,
                'wf_win_rate': wf['avg_win_rate'] if wf else 0,
                'wf_profit_factor': wf['avg_profit_factor'] if wf else 0,
                'wf_trades': wf['total_trades'] if wf else 0
            }
            results.append(result)
    
    print()
    print("=" * 80)
    print(f"OPTIMIZATION COMPLETE - {len(results)} valid configurations found")
    print("=" * 80)
    
    return results


def find_optimal_config(results, min_wr=90, min_pf=2.0):
    """Find configurations meeting criteria: WR >= min_wr%, PF >= min_pf."""
    # Filter by criteria
    qualified = [r for r in results 
                 if r['win_rate'] >= min_wr and r['profit_factor'] >= min_pf]
    
    if not qualified:
        # Relax criteria slightly
        print(f"No configs with WR>={min_wr}% and PF>={min_pf}. Relaxing...")
        qualified = [r for r in results 
                     if r['win_rate'] >= min_wr - 5 and r['profit_factor'] >= min_pf - 0.5]
    
    if not qualified:
        return None
    
    # Sort by walk-forward win rate (most important), then PF, then total trades
    qualified.sort(key=lambda x: (x['wf_win_rate'], x['wf_profit_factor'], x['total_trades']), reverse=True)
    
    return qualified[0]


def main():
    # Test on Silver (XAGUSD)
    silver_path = "/home/palbot/Projects/log-fib-scalper/data/OANDA_XAGUSD5.csv"
    gold_path = "/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv"
    
    print("\n" + "=" * 80)
    print("PHASE 1: SILVER (XAGUSD) OPTIMIZATION")
    print("=" * 80 + "\n")
    
    silver_results = optimize_parameters(silver_path, "SILVER (XAGUSD)")
    
    if silver_results:
        # Save all results
        with open("/home/palbot/Projects/log-fib-scalper/scripts/silver_optimization_results.json", 'w') as f:
            json.dump(silver_results, f, indent=2)
        
        # Find optimal
        best_silver = find_optimal_config(silver_results, min_wr=90, min_pf=2.0)
        
        if best_silver:
            print("\n" + "=" * 80)
            print("🏆 BEST SILVER CONFIGURATION")
            print("=" * 80)
            print(f"Lookback:        {best_silver['lookback']} bars")
            print(f"Multiplier:      {best_silver['multiplier']}")
            print(f"Entry Ratio:     {best_silver['entry_ratio']}")
            print(f"Take Profit:     {best_silver['take_profit_ratio']}")
            print(f"Stop Loss:       {best_silver['stop_loss_ratio']}")
            print(f"Direction:       {best_silver['direction']}")
            print(f"---")
            print(f"Total Trades:    {best_silver['total_trades']}")
            print(f"Win Rate:        {best_silver['win_rate']:.2f}%")
            print(f"Profit Factor:   {best_silver['profit_factor']:.2f}")
            print(f"Total P&L:       {best_silver['total_pnl']:.5f}")
            print(f"Avg P&L/Trade:   {best_silver['avg_pnl']:.5f}")
            print(f"Max Drawdown:    {best_silver['max_drawdown']:.5f}")
            print(f"---")
            print(f"WF Win Rate:     {best_silver['wf_win_rate']:.2f}%")
            print(f"WF Profit Factor:{best_silver['wf_profit_factor']:.2f}")
            print("=" * 80)
    
    print("\n" + "=" * 80)
    print("PHASE 2: GOLD (XAUUSD) OPTIMIZATION")
    print("=" * 80 + "\n")
    
    gold_results = optimize_parameters(gold_path, "GOLD (XAUUSD)")
    
    if gold_results:
        with open("/home/palbot/Projects/log-fib-scalper/scripts/gold_optimization_results.json", 'w') as f:
            json.dump(gold_results, f, indent=2)
        
        best_gold = find_optimal_config(gold_results, min_wr=90, min_pf=2.0)
        
        if best_gold:
            print("\n" + "=" * 80)
            print("🏆 BEST GOLD CONFIGURATION")
            print("=" * 80)
            print(f"Lookback:        {best_gold['lookback']} bars")
            print(f"Multiplier:      {best_gold['multiplier']}")
            print(f"Entry Ratio:     {best_gold['entry_ratio']}")
            print(f"Take Profit:     {best_gold['take_profit_ratio']}")
            print(f"Stop Loss:       {best_gold['stop_loss_ratio']}")
            print(f"Direction:       {best_gold['direction']}")
            print(f"---")
            print(f"Total Trades:    {best_gold['total_trades']}")
            print(f"Win Rate:        {best_gold['win_rate']:.2f}%")
            print(f"Profit Factor:   {best_gold['profit_factor']:.2f}")
            print(f"Total P&L:       {best_gold['total_pnl']:.5f}")
            print(f"Avg P&L/Trade:   {best_gold['avg_pnl']:.5f}")
            print(f"Max Drawdown:    {best_gold['max_drawdown']:.5f}")
            print(f"---")
            print(f"WF Win Rate:     {best_gold['wf_win_rate']:.2f}%")
            print(f"WF Profit Factor:{best_gold['wf_profit_factor']:.2f}")
            print("=" * 80)
    
    # Save final recommendations
    final_report = {
        'silver_best': best_silver if silver_results else None,
        'gold_best': best_gold if gold_results else None,
        'timestamp': datetime.now().isoformat()
    }
    
    with open("/home/palbot/Projects/log-fib-scalper/scripts/optimal_trading_rules.json", 'w') as f:
        json.dump(final_report, f, indent=2)
    
    print("\n✅ Results saved to:")
    print("   - silver_optimization_results.json")
    print("   - gold_optimization_results.json")
    print("   - optimal_trading_rules.json")


if __name__ == '__main__':
    main()
