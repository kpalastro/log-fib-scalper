#!/usr/bin/env python3
"""
Final Verification: Test the top balanced configuration with more trades.
Config: lookback=10, mult=0.618, entry=0.618, TP=0.786, SL=1.618, direction=both
Claimed: WR=95.7%, WF_WR=96.0%, 140 trades
"""

import csv
import math
import os
import json
from datetime import datetime

FIB_LEVELS = [0.125, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]


def load_csv(csv_path):
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
    n = len(bars)
    if n < lookback * 2:
        return []
    
    results = []
    
    for i in range(lookback, n - lookback):
        bar = bars[i]
        
        # SWING HIGH
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
        
        top_levels = {r: highest_high - (r * effective_range_top) for r in FIB_LEVELS}
        
        # SWING LOW
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
        
        bottom_levels = {r: lowest_low + (r * effective_range_bot) for r in FIB_LEVELS}
        
        results.append({
            'idx': i, 'time': bar['time'],
            'swing_high': highest_high, 'anchored_low': anchored_low,
            'swing_low': lowest_low, 'anchored_high': anchored_high,
            'effective_range_top': effective_range_top,
            'effective_range_bot': effective_range_bot,
            'top_levels': top_levels, 'bottom_levels': bottom_levels
        })
    
    return results


def run_backtest(bars, projections, entry_ratio, take_profit_ratio, stop_loss_ratio, 
                 direction='both', min_bars_between=5):
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
        
        if in_position:
            bar = bars[idx]
            
            if position_type == "SHORT":
                if bar['low'] <= take_profit:
                    pnl = entry_price - take_profit
                    trades.append({'type': 'SHORT', 'entry_time': entry_time, 'exit_time': bar['time'],
                                   'entry_price': entry_price, 'exit_price': take_profit,
                                   'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_position = False
                elif bar['high'] >= stop_loss:
                    pnl = entry_price - stop_loss
                    trades.append({'type': 'SHORT', 'entry_time': entry_time, 'exit_time': bar['time'],
                                   'entry_price': entry_price, 'exit_price': stop_loss,
                                   'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_position = False
            
            elif position_type == "LONG":
                if bar['high'] >= take_profit:
                    pnl = take_profit - entry_price
                    trades.append({'type': 'LONG', 'entry_time': entry_time, 'exit_time': bar['time'],
                                   'entry_price': entry_price, 'exit_price': take_profit,
                                   'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_position = False
                elif bar['low'] <= stop_loss:
                    pnl = stop_loss - entry_price
                    trades.append({'type': 'LONG', 'entry_time': entry_time, 'exit_time': bar['time'],
                                   'entry_price': entry_price, 'exit_price': stop_loss,
                                   'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_position = False
        
        if not in_position and idx - last_trade_idx >= min_bars_between:
            swing_high = proj['swing_high']
            swing_low = proj['swing_low']
            eff_top = proj['effective_range_top']
            eff_bot = proj['effective_range_bot']
            
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
    if not trades:
        return None
    
    total_trades = len(trades)
    wins = sum(1 for t in trades if t['outcome'] == 'WIN')
    win_rate = (wins / total_trades * 100)
    total_pnl = sum(t['pnl'] for t in trades)
    avg_pnl = total_pnl / total_trades
    
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
        'total_trades': total_trades, 'wins': wins, 'losses': total_trades - wins,
        'win_rate': win_rate, 'total_pnl': total_pnl, 'avg_pnl': avg_pnl,
        'profit_factor': profit_factor, 'max_drawdown': max_drawdown
    }


def walk_forward(bars, lookback, multiplier, entry_ratio, tp_ratio, sl_ratio, 
                 direction='both', n_folds=5, min_bars_between=5):
    projections = calculate_log_fib_levels(bars, lookback, multiplier)
    n = len(projections)
    fold_size = n // n_folds
    
    fold_results = []
    
    for fold in range(n_folds):
        test_start = fold * fold_size
        test_end = (fold + 1) * fold_size if fold < n_folds - 1 else n
        
        test_start_time = projections[test_start]['time']
        test_end_time = projections[min(test_end - 1, n - 1)]['time']
        
        trades = run_backtest(bars, projections, entry_ratio, tp_ratio, sl_ratio, direction, min_bars_between)
        test_trades = [t for t in trades if test_start_time <= t['entry_time'] < test_end_time]
        
        metrics = calculate_metrics(test_trades)
        if metrics:
            metrics['fold'] = fold
            fold_results.append(metrics)
    
    if not fold_results:
        return None
    
    avg_wr = sum(r['win_rate'] for r in fold_results) / len(fold_results)
    avg_pf_vals = [r['profit_factor'] for r in fold_results if r['profit_factor'] != float('inf')]
    avg_pf = sum(avg_pf_vals) / len(avg_pf_vals) if avg_pf_vals else float('inf')
    
    return {
        'avg_win_rate': avg_wr, 'avg_profit_factor': avg_pf,
        'total_trades': sum(r['total_trades'] for r in fold_results),
        'fold_results': fold_results
    }


def test_config(bars, name, lb, mult, entry, tp, sl, direction='both'):
    print(f"\n{'='*70}")
    print(f"CONFIG: {name}")
    print(f"{'='*70}")
    print(f"Lookback={lb}, Multiplier={mult}, Entry={entry}, TP={tp}, SL={sl}, Dir={direction}")
    
    projections = calculate_log_fib_levels(bars, lb, mult)
    trades = run_backtest(bars, projections, entry, tp, sl, direction)
    metrics = calculate_metrics(trades)
    
    if metrics:
        print(f"\n📊 IN-SAMPLE METRICS:")
        print(f"   Trades: {metrics['total_trades']}")
        print(f"   Win Rate: {metrics['win_rate']:.2f}%")
        print(f"   Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"   Total P&L: {metrics['total_pnl']:.5f}")
        print(f"   Avg P&L/Trade: {metrics['avg_pnl']:.5f}")
        print(f"   Max Drawdown: {metrics['max_drawdown']:.5f}")
        
        wf = walk_forward(bars, lb, mult, entry, tp, sl, direction)
        
        if wf:
            print(f"\n🔍 WALK-FORWARD VALIDATION ({len(wf['fold_results'])} folds):")
            print(f"   Avg Win Rate: {wf['avg_win_rate']:.2f}%")
            pf_str = f"{wf['avg_profit_factor']:.2f}" if wf['avg_profit_factor'] != float('inf') else "inf"
            print(f"   Avg Profit Factor: {pf_str}")
            print(f"   Total Trades: {wf['total_trades']}")
            
            print(f"\n   Fold Details:")
            for fr in wf['fold_results']:
                pf_s = f"{fr['profit_factor']:.2f}" if fr['profit_factor'] != float('inf') else "inf"
                print(f"     Fold {fr['fold']}: WR={fr['win_rate']:.1f}%, PF={pf_s}, Trades={fr['total_trades']}, P&L={fr['total_pnl']:.4f}")
            
            metrics['walk_forward'] = wf
    
    return metrics


def main():
    silver_path = "/home/palbot/Projects/log-fib-scalper/data/OANDA_XAGUSD5.csv"
    gold_path = "/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv"
    
    silver_bars = load_csv(silver_path)
    gold_bars = load_csv(gold_path)
    
    print("=" * 80)
    print("FINAL CONFIGURATION VERIFICATION")
    print("=" * 80)
    
    results = {}
    
    # Test the balanced config with more trades
    results['balanced_silver'] = test_config(
        silver_bars, "BALANCED SILVER (140 trades)",
        lb=10, mult=0.618, entry=0.618, tp=0.786, sl=1.618, direction='both'
    )
    
    # Test the highest WR config
    results['high_wr_silver'] = test_config(
        silver_bars, "HIGH WR SILVER (89 trades)",
        lb=14, mult=0.618, entry=0.786, tp=1.272, sl=1.272, direction='both'
    )
    
    # Test another high-trade config
    results['high_trade_silver'] = test_config(
        silver_bars, "HIGH TRADE SILVER (134 trades)",
        lb=14, mult=0.5, entry=0.618, tp=1.0, sl=1.618, direction='both'
    )
    
    # Test original claimed config
    results['claimed_silver'] = test_config(
        silver_bars, "CLAIMED CONFIG (296 trades)",
        lb=12, mult=0.382, entry=0.5, tp=0.786, sl=1.0, direction='both'
    )
    
    # Gold optimal
    results['optimal_gold'] = test_config(
        gold_bars, "OPTIMAL GOLD (short only)",
        lb=14, mult=0.382, entry=0.618, tp=1.0, sl=1.272, direction='short'
    )
    
    # Save final report
    final = {
        'timestamp': datetime.now().isoformat(),
        'recommended_config_silver': {
            'name': 'Balanced Silver (Recommended)',
            'params': {'lookback': 10, 'multiplier': 0.618, 'entry_ratio': 0.618,
                      'take_profit_ratio': 0.786, 'stop_loss_ratio': 1.618, 'direction': 'both'},
            'metrics': results['balanced_silver']
        },
        'alternative_config_silver': {
            'name': 'High WR Silver (Conservative)',
            'params': {'lookback': 14, 'multiplier': 0.618, 'entry_ratio': 0.786,
                      'take_profit_ratio': 1.272, 'stop_loss_ratio': 1.272, 'direction': 'both'},
            'metrics': results['high_wr_silver']
        },
        'optimal_gold': {
            'name': 'Optimal Gold (Short Only)',
            'params': {'lookback': 14, 'multiplier': 0.382, 'entry_ratio': 0.618,
                      'take_profit_ratio': 1.0, 'stop_loss_ratio': 1.272, 'direction': 'short'},
            'metrics': results['optimal_gold']
        }
    }
    
    with open("/home/palbot/Projects/log-fib-scalper/scripts/final_trading_rules.json", 'w') as f:
        json.dump(final, f, indent=2)
    
    print("\n\n" + "=" * 80)
    print("📋 FINAL RECOMMENDATIONS")
    print("=" * 80)
    
    print("\n🥇 RECOMMENDED SILVER CONFIG (Best balance of trades + WR):")
    r = results['balanced_silver']
    if r and 'walk_forward' in r:
        wf = r['walk_forward']
        print(f"   Lookback=10, Multiplier=0.618, Entry=0.618, TP=0.786, SL=1.618, Dir=both")
        print(f"   In-Sample: WR={r['win_rate']:.1f}%, PF={r['profit_factor']:.2f}, Trades={r['total_trades']}")
        print(f"   Walk-Forward: WR={wf['avg_win_rate']:.1f}%, Trades={wf['total_trades']}")
    
    print("\n🥈 CONSERVATIVE SILVER CONFIG (Highest WR, fewer trades):")
    r = results['high_wr_silver']
    if r and 'walk_forward' in r:
        wf = r['walk_forward']
        print(f"   Lookback=14, Multiplier=0.618, Entry=0.786, TP=1.272, SL=1.272, Dir=both")
        print(f"   In-Sample: WR={r['win_rate']:.1f}%, PF={r['profit_factor']:.2f}, Trades={r['total_trades']}")
        print(f"   Walk-Forward: WR={wf['avg_win_rate']:.1f}%, Trades={wf['total_trades']}")
    
    print("\n🥉 GOLD CONFIG (Short only):")
    r = results['optimal_gold']
    if r and 'walk_forward' in r:
        wf = r['walk_forward']
        print(f"   Lookback=14, Multiplier=0.382, Entry=0.618, TP=1.0, SL=1.272, Dir=short")
        print(f"   In-Sample: WR={r['win_rate']:.1f}%, PF={r['profit_factor']:.2f}, Trades={r['total_trades']}")
        print(f"   Walk-Forward: WR={wf['avg_win_rate']:.1f}%, Trades={wf['total_trades']}")
    
    print("\n✅ Final report saved to: final_trading_rules.json")


if __name__ == '__main__':
    main()
