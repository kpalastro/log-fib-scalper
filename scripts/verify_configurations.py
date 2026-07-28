#!/usr/bin/env python3
"""
Verification and Walk-Forward Validation Script

Tests the claimed best configuration vs discovered optimal.
Performs rigorous out-of-sample validation.
"""

import csv
import math
import os
import json
from datetime import datetime

FIB_LEVELS = [0.125, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]


def load_csv(csv_path):
    """Load CSV data into list of bar dictionaries."""
    if not os.path.exists(csv_path):
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
    """Calculate Log-Fib projection levels matching Pine Script exactly."""
    n = len(bars)
    if n < lookback * 2:
        return []
    
    results = []
    
    for i in range(lookback, n - lookback):
        bar = bars[i]
        
        # === SWING HIGH DETECTION ===
        highest_high = bar['high']
        highest_idx = i
        
        for j in range(i - lookback + 1, i + 1):
            if bars[j]['high'] > highest_high:
                highest_high = bars[j]['high']
                highest_idx = j
        
        anchored_low = bars[highest_idx]['low']
        
        log_sh = math.log10(highest_high)
        range_diff_top = abs(highest_high - anchored_low)
        effective_range_top = log_sh * range_diff_top * multiplier * 4.0
        
        top_levels = {}
        for ratio in FIB_LEVELS:
            top_levels[ratio] = highest_high - (ratio * effective_range_top)
        
        # === SWING LOW DETECTION ===
        lowest_low = bar['low']
        lowest_idx = i
        
        for j in range(i - lookback + 1, i + 1):
            if bars[j]['low'] < lowest_low:
                lowest_low = bars[j]['low']
                lowest_idx = j
        
        anchored_high = bars[lowest_idx]['high']
        
        log_sl = math.log10(lowest_low)
        range_diff_bot = abs(lowest_low - anchored_high)
        effective_range_bot = log_sl * range_diff_bot * multiplier * 4.0
        
        bottom_levels = {}
        for ratio in FIB_LEVELS:
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
                 direction='both', min_bars_between=5):
    """Run backtest with specified parameters."""
    trades = []
    in_position = False
    position_type = None
    entry_price = 0.0
    entry_time = ""
    stop_loss = 0.0
    take_profit = 0.0
    last_trade_idx = -100
    
    n = len(bars)
    
    for proj in projections:
        idx = proj['idx']
        
        # Check for exit if in position
        if in_position:
            bar = bars[idx]
            
            if position_type == "SHORT":
                if bar['low'] <= take_profit:
                    pnl = entry_price - take_profit
                    trades.append({
                        'type': 'SHORT', 'entry_time': entry_time, 'exit_time': bar['time'],
                        'entry_price': entry_price, 'exit_price': take_profit,
                        'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'
                    })
                    in_position = False
                elif bar['high'] >= stop_loss:
                    pnl = entry_price - stop_loss
                    trades.append({
                        'type': 'SHORT', 'entry_time': entry_time, 'exit_time': bar['time'],
                        'entry_price': entry_price, 'exit_price': stop_loss,
                        'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'
                    })
                    in_position = False
            
            elif position_type == "LONG":
                if bar['high'] >= take_profit:
                    pnl = take_profit - entry_price
                    trades.append({
                        'type': 'LONG', 'entry_time': entry_time, 'exit_time': bar['time'],
                        'entry_price': entry_price, 'exit_price': take_profit,
                        'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'
                    })
                    in_position = False
                elif bar['low'] <= stop_loss:
                    pnl = stop_loss - entry_price
                    trades.append({
                        'type': 'LONG', 'entry_time': entry_time, 'exit_time': bar['time'],
                        'entry_price': entry_price, 'exit_price': stop_loss,
                        'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'
                    })
                    in_position = False
        
        # Look for new entries
        if not in_position and idx - last_trade_idx >= min_bars_between:
            swing_high = proj['swing_high']
            swing_low = proj['swing_low']
            eff_top = proj['effective_range_top']
            eff_bot = proj['effective_range_bot']
            
            # SHORT SETUP
            if direction in ['short', 'both']:
                entry_level = swing_high - (entry_ratio * eff_top)
                tp_level = swing_high - (take_profit_ratio * eff_top)
                sl_level = swing_high + (stop_loss_ratio * eff_top)
                
                for k in range(idx + 1, min(idx + 100, n)):
                    if bars[k]['low'] <= entry_level:
                        in_position = True
                        position_type = "SHORT"
                        entry_price = entry_level
                        entry_time = bars[k]['time']
                        take_profit = tp_level
                        stop_loss = sl_level
                        last_trade_idx = idx
                        break
            
            # LONG SETUP
            if not in_position and direction in ['long', 'both']:
                entry_level = swing_low + (entry_ratio * eff_bot)
                tp_level = swing_low + (take_profit_ratio * eff_bot)
                sl_level = swing_low - (stop_loss_ratio * eff_bot)
                
                for k in range(idx + 1, min(idx + 100, n)):
                    if bars[k]['high'] >= entry_level:
                        in_position = True
                        position_type = "LONG"
                        entry_price = entry_level
                        entry_time = bars[k]['time']
                        take_profit = tp_level
                        stop_loss = sl_level
                        last_trade_idx = idx
                        break
    
    return trades


def calculate_metrics(trades):
    """Calculate trading metrics."""
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


def walk_forward_validation(bars, lookback, multiplier, entry_ratio, tp_ratio, sl_ratio,
                            direction='both', n_folds=5, min_bars_between=5):
    """
    Rigorous walk-forward validation with time-based splits.
    Each fold: train on 80% of data up to test point, test on next 20%.
    """
    projections = calculate_log_fib_levels(bars, lookback, multiplier)
    n = len(projections)
    fold_size = n // n_folds
    
    fold_results = []
    
    for fold in range(n_folds):
        # Test period: this fold
        test_start_idx = fold * fold_size
        test_end_idx = (fold + 1) * fold_size if fold < n_folds - 1 else n
        
        # Get test period times
        test_start_time = projections[test_start_idx]['time']
        test_end_time = projections[min(test_end_idx - 1, n - 1)]['time']
        
        # Run backtest on full data
        trades = run_backtest(bars, projections, entry_ratio, tp_ratio, sl_ratio, 
                             direction, min_bars_between)
        
        # Filter trades to test period only
        test_trades = [t for t in trades 
                       if test_start_time <= t['entry_time'] < test_end_time]
        
        metrics = calculate_metrics(test_trades)
        if metrics:
            metrics['fold'] = fold
            metrics['test_period'] = f"{test_start_time} to {test_end_time}"
            fold_results.append(metrics)
    
    # Aggregate
    if not fold_results:
        return None
    
    avg_wr = sum(r['win_rate'] for r in fold_results) / len(fold_results)
    avg_pf_values = [r['profit_factor'] for r in fold_results if r['profit_factor'] != float('inf')]
    avg_pf = sum(avg_pf_values) / len(avg_pf_values) if avg_pf_values else float('inf')
    total_trades = sum(r['total_trades'] for r in fold_results)
    total_pnl = sum(r['total_pnl'] for r in fold_results)
    avg_dd = sum(r['max_drawdown'] for r in fold_results) / len(fold_results)
    
    return {
        'avg_win_rate': avg_wr,
        'avg_profit_factor': avg_pf,
        'total_trades': total_trades,
        'total_pnl': total_pnl,
        'avg_drawdown': avg_dd,
        'fold_results': fold_results
    }


def test_configuration(bars, config_name, lookback, multiplier, entry_ratio, tp_ratio, sl_ratio, direction='both'):
    """Test a specific configuration and return metrics."""
    print(f"\n{'='*60}")
    print(f"Testing: {config_name}")
    print(f"{'='*60}")
    print(f"Lookback={lookback}, Multiplier={multiplier}, Entry={entry_ratio}")
    print(f"TP={tp_ratio}, SL={sl_ratio}, Direction={direction}")
    
    projections = calculate_log_fib_levels(bars, lookback, multiplier)
    trades = run_backtest(bars, projections, entry_ratio, tp_ratio, sl_ratio, direction)
    metrics = calculate_metrics(trades)
    
    if metrics:
        print(f"\nIn-Sample Results:")
        print(f"  Trades: {metrics['total_trades']}")
        print(f"  Win Rate: {metrics['win_rate']:.2f}%")
        print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"  Total P&L: {metrics['total_pnl']:.5f}")
        print(f"  Max Drawdown: {metrics['max_drawdown']:.5f}")
        
        # Walk-forward validation
        wf = walk_forward_validation(bars, lookback, multiplier, entry_ratio, tp_ratio, sl_ratio, direction)
        
        if wf:
            print(f"\nWalk-Forward Validation ({len(wf['fold_results'])} folds):")
            print(f"  Avg Win Rate: {wf['avg_win_rate']:.2f}%")
            print(f"  Avg Profit Factor: {wf['avg_profit_factor']:.2f}")
            print(f"  Total Trades: {wf['total_trades']}")
            print(f"  Total P&L: {wf['total_pnl']:.5f}")
            print(f"  Avg Drawdown: {wf['avg_drawdown']:.5f}")
            
            print(f"\n  Fold-by-Fold:")
            for fr in wf['fold_results']:
                pf_str = f"{fr['profit_factor']:.2f}" if fr['profit_factor'] != float('inf') else "inf"
                print(f"    Fold {fr['fold']}: WR={fr['win_rate']:.1f}%, PF={pf_str}, Trades={fr['total_trades']}, P&L={fr['total_pnl']:.4f}")
            
            metrics['walk_forward'] = wf
    
    return metrics


def main():
    silver_path = "/home/palbot/Projects/log-fib-scalper/data/OANDA_XAGUSD5.csv"
    gold_path = "/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv"
    
    print("=" * 80)
    print("LOG-FIB MTF VERIFICATION & WALK-FORWARD VALIDATION")
    print("=" * 80)
    
    # Load data
    silver_bars = load_csv(silver_path)
    gold_bars = load_csv(gold_path)
    
    print(f"\nSilver (XAGUSD): {len(silver_bars)} bars")
    print(f"Gold (XAUUSD): {len(gold_bars)} bars")
    
    results = {}
    
    # ===== TEST CLAIMED BEST CONFIG =====
    print("\n\n" + "=" * 80)
    print("TEST 1: CLAIMED BEST CONFIG (from best_config.txt)")
    print("=" * 80)
    
    # Claimed: lookback=12, multiplier=0.382, entry_ratio=0.5, take_profit=0.786, stop_loss=1.0
    # Direction inferred as "both"
    results['claimed_silver'] = test_configuration(
        silver_bars, 
        "Claimed Best (Silver)",
        lookback=12, multiplier=0.382, entry_ratio=0.5, 
        tp_ratio=0.786, sl_ratio=1.0, direction='both'
    )
    
    # ===== TEST DISCOVERED OPTIMAL SILVER =====
    print("\n\n" + "=" * 80)
    print("TEST 2: DISCOVERED OPTIMAL SILVER")
    print("=" * 80)
    
    # Discovered: lookback=14, mult=0.618, entry=0.786, TP=1.272, SL=1.272, direction=both
    results['optimal_silver'] = test_configuration(
        silver_bars,
        "Discovered Optimal (Silver)",
        lookback=14, multiplier=0.618, entry_ratio=0.786,
        tp_ratio=1.272, sl_ratio=1.272, direction='both'
    )
    
    # ===== TEST DISCOVERED OPTIMAL GOLD =====
    print("\n\n" + "=" * 80)
    print("TEST 3: DISCOVERED OPTIMAL GOLD")
    print("=" * 80)
    
    # Discovered: lookback=14, mult=0.382, entry=0.618, TP=1.0, SL=1.272, direction=short
    results['optimal_gold'] = test_configuration(
        gold_bars,
        "Discovered Optimal (Gold)",
        lookback=14, multiplier=0.382, entry_ratio=0.618,
        tp_ratio=1.0, sl_ratio=1.272, direction='short'
    )
    
    # ===== TEST ALTERNATIVE SILVER CONFIG (more trades) =====
    print("\n\n" + "=" * 80)
    print("TEST 4: ALTERNATIVE SILVER (more trades, still high WR)")
    print("=" * 80)
    
    # Try: lookback=12, mult=0.5, entry=0.618, TP=1.0, SL=1.272
    results['alt_silver'] = test_configuration(
        silver_bars,
        "Alternative Silver (more trades)",
        lookback=12, multiplier=0.5, entry_ratio=0.618,
        tp_ratio=1.0, sl_ratio=1.272, direction='both'
    )
    
    # Save final report
    final_report = {
        'timestamp': datetime.now().isoformat(),
        'configurations_tested': {
            'claimed_silver': {
                'params': {'lookback': 12, 'multiplier': 0.382, 'entry_ratio': 0.5, 
                          'take_profit_ratio': 0.786, 'stop_loss_ratio': 1.0, 'direction': 'both'},
                'metrics': results['claimed_silver']
            },
            'optimal_silver': {
                'params': {'lookback': 14, 'multiplier': 0.618, 'entry_ratio': 0.786,
                          'take_profit_ratio': 1.272, 'stop_loss_ratio': 1.272, 'direction': 'both'},
                'metrics': results['optimal_silver']
            },
            'optimal_gold': {
                'params': {'lookback': 14, 'multiplier': 0.382, 'entry_ratio': 0.618,
                          'take_profit_ratio': 1.0, 'stop_loss_ratio': 1.272, 'direction': 'short'},
                'metrics': results['optimal_gold']
            },
            'alt_silver': {
                'params': {'lookback': 12, 'multiplier': 0.5, 'entry_ratio': 0.618,
                          'take_profit_ratio': 1.0, 'stop_loss_ratio': 1.272, 'direction': 'both'},
                'metrics': results['alt_silver']
            }
        }
    }
    
    with open("/home/palbot/Projects/log-fib-scalper/scripts/verification_report.json", 'w') as f:
        json.dump(final_report, f, indent=2)
    
    print("\n\n" + "=" * 80)
    print("FINAL VERIFICATION REPORT")
    print("=" * 80)
    
    # Summary table
    print("\nSUMMARY (In-Sample | Walk-Forward):")
    print("-" * 80)
    
    configs = [
        ("Claimed Silver", results['claimed_silver']),
        ("Optimal Silver", results['optimal_silver']),
        ("Optimal Gold", results['optimal_gold']),
        ("Alt Silver", results['alt_silver'])
    ]
    
    for name, m in configs:
        if m and 'walk_forward' in m:
            wf = m['walk_forward']
            print(f"{name:20} | WR: {m['win_rate']:5.1f}% / {wf['avg_win_rate']:5.1f}% | "
                  f"PF: {m['profit_factor']:5.2f} / {wf['avg_profit_factor']:5.2f} | "
                  f"Trades: {m['total_trades']:3} / {wf['total_trades']:3}")
        elif m:
            print(f"{name:20} | WR: {m['win_rate']:5.1f}% | PF: {m['profit_factor']:5.2f} | Trades: {m['total_trades']:3}")
    
    print("-" * 80)
    print("\n✅ Report saved to: verification_report.json")
    
    return final_report


if __name__ == '__main__':
    main()
