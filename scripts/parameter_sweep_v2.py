import csv
import math
import os
from itertools import product

def run_backtest(csv_path, lookback, multiplier, entry_ratio, take_profit_ratio, stop_loss_ratio):
    """Fast backtest engine for parameter sweeping"""
    
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
                'close': float(row['close']),
                'volume': int(row['Volume'])
            })
    
    if len(bars) < lookback * 3:
        return None
    
    trades = []
    in_position = False
    position_type = None
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    
    for i in range(lookback, len(bars) - lookback):
        if in_position:
            current_bar = bars[i]
            
            if position_type == "SHORT":
                if current_bar['low'] <= take_profit:
                    pnl = entry_price - take_profit
                    trades.append({'type': 'SHORT', 'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_position = False
                elif current_bar['high'] >= stop_loss:
                    pnl = entry_price - stop_loss
                    trades.append({'type': 'SHORT', 'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_position = False
            
            elif position_type == "LONG":
                if current_bar['high'] >= take_profit:
                    pnl = take_profit - entry_price
                    trades.append({'type': 'LONG', 'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_position = False
                elif current_bar['low'] <= stop_loss:
                    pnl = stop_loss - entry_price
                    trades.append({'type': 'LONG', 'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_position = False
        
        if not in_position:
            # Swing High Detection (SHORT)
            current_high = bars[i]['high']
            is_swing_high = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and bars[j]['high'] >= current_high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                anchored_low = bars[i]['low']
                log_sh = math.log10(current_high)
                range_diff = abs(current_high - anchored_low)
                effective_range = log_sh * range_diff * multiplier * 4.0
                
                entry_level = current_high - (entry_ratio * effective_range)
                take_profit_level = current_high - (take_profit_ratio * effective_range)
                stop_level = current_high + (stop_loss_ratio * effective_range)
                
                for k in range(i + 1, min(i + 50, len(bars))):
                    if bars[k]['low'] <= entry_level:
                        in_position = True
                        position_type = "SHORT"
                        entry_price = entry_level
                        take_profit = take_profit_level
                        stop_loss = stop_level
                        break
            
            # Swing Low Detection (LONG)
            current_low = bars[i]['low']
            is_swing_low = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and bars[j]['low'] <= current_low:
                    is_swing_low = False
                    break
            
            if is_swing_low and not in_position:
                anchored_high = bars[i]['high']
                log_sl = math.log10(current_low)
                range_diff = abs(current_low - anchored_high)
                effective_range = log_sl * range_diff * multiplier * 4.0
                
                entry_level = current_low + (entry_ratio * effective_range)
                take_profit_level = current_low + (take_profit_ratio * effective_range)
                stop_level = current_low - (stop_loss_ratio * effective_range)
                
                for k in range(i + 1, min(i + 50, len(bars))):
                    if bars[k]['high'] >= entry_level:
                        in_position = True
                        position_type = "LONG"
                        entry_price = entry_level
                        take_profit = take_profit_level
                        stop_loss = stop_level
                        break
    
    total_trades = len(trades)
    if total_trades == 0:
        return None
    
    wins = sum(1 for t in trades if t['outcome'] == 'WIN')
    losses = total_trades - wins
    win_rate = (wins / total_trades * 100)
    
    total_pnl = sum(t['pnl'] for t in trades)
    avg_pnl = total_pnl / total_trades
    
    gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
    
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
        'lookback': lookback,
        'multiplier': multiplier,
        'entry_ratio': entry_ratio,
        'take_profit_ratio': take_profit_ratio,
        'stop_loss_ratio': stop_loss_ratio,
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_pnl': avg_pnl,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown
    }

def run_parameter_sweep(csv_path):
    print("="*80)
    print("PARAMETER SWEEP OPTIMIZATION V2 - Log-Fib Scalping Strategy")
    print("="*80)
    
    lookbacks = [4, 6, 8, 10, 12]
    multipliers = [0.382, 0.5, 0.618, 0.786]
    entry_ratios = [0.5, 0.618, 0.786]
    tp_ratios = [0.786, 1.0, 1.272, 1.618]
    sl_ratios = [1.0, 1.272, 1.414, 1.618]
    
    total_combinations = len(lookbacks) * len(multipliers) * len(entry_ratios) * len(tp_ratios) * len(sl_ratios)
    print(f"Testing {total_combinations} parameter combinations...")
    print(f"Data: {csv_path}")
    print()
    
    results = []
    count = 0
    
    for lb, mult, entry, tp, sl in product(lookbacks, multipliers, entry_ratios, tp_ratios, sl_ratios):
        count += 1
        if count % 100 == 0:
            print(f"Progress: {count}/{total_combinations} combinations tested...")
        
        result = run_backtest(csv_path, lb, mult, entry, tp, sl)
        # FILTER: Only include configurations with actual winning trades
        if result and result['total_trades'] >= 50 and result['wins'] > 0 and result['total_pnl'] > 0:
            results.append(result)
    
    print()
    print("="*80)
    print(f"OPTIMIZATION COMPLETE - {len(results)} PROFITABLE configurations found")
    print("="*80)
    
    if not results:
        print("\n❌ No profitable configurations found with current parameter ranges.")
        return results
    
    # Sort by: Total P&L (primary), Win Rate (secondary), Profit Factor (tertiary)
    results.sort(key=lambda x: (x['total_pnl'], x['win_rate'], x['profit_factor']), reverse=True)
    
    print()
    print("🏆 TOP 10 OPTIMAL CONFIGURATIONS:")
    print("="*80)
    
    for i, r in enumerate(results[:10], 1):
        print(f"\n#{i} - Total P&L: {r['total_pnl']:.5f} | Win Rate: {r['win_rate']:.1f}% | PF: {r['profit_factor']:.2f}")
        print(f"    Lookback: {r['lookback']} | Multiplier: {r['multiplier']} | Entry: {r['entry_ratio']}")
        print(f"    Take Profit: {r['take_profit_ratio']} | Stop Loss: {r['stop_loss_ratio']}")
        print(f"    Trades: {r['total_trades']} | Avg P&L: {r['avg_pnl']:.5f} | Max DD: {r['max_drawdown']:.5f}")
    
    # Show the ABSOLUTE BEST
    best = results[0]
    print()
    print("="*80)
    print("🎯 RECOMMENDED BEST CONFIGURATION:")
    print("="*80)
    print(f"Lookback:        {best['lookback']} bars")
    print(f"Multiplier:      {best['multiplier']}")
    print(f"Entry Ratio:     {best['entry_ratio']} (Fibonacci level)")
    print(f"Take Profit:     {best['take_profit_ratio']} (Extension target)")
    print(f"Stop Loss:       {best['stop_loss_ratio']} (Extension stop)")
    print(f"---")
    print(f"Total Trades:    {best['total_trades']}")
    print(f"Win Rate:        {best['win_rate']:.2f}%")
    print(f"Profit Factor:   {best['profit_factor']:.2f}")
    print(f"Total P&L:       {best['total_pnl']:.5f}")
    print(f"Avg P&L/Trade:   {best['avg_pnl']:.5f}")
    print(f"Max Drawdown:    {best['max_drawdown']:.5f}")
    print("="*80)
    
    # Save best config to file
    config_path = "/Users/kpal/projects/hermese/scripts/best_config.txt"
    with open(config_path, 'w') as f:
        f.write(f"# BEST LOG-FIB SCALPING CONFIGURATION\n")
        f.write(f"# Optimized on OANDA_XAGUSD1.csv ({best['total_trades']} trades)\n\n")
        f.write(f"lookback={best['lookback']}\n")
        f.write(f"multiplier={best['multiplier']}\n")
        f.write(f"entry_ratio={best['entry_ratio']}\n")
        f.write(f"take_profit_ratio={best['take_profit_ratio']}\n")
        f.write(f"stop_loss_ratio={best['stop_loss_ratio']}\n\n")
        f.write(f"# Performance Metrics\n")
        f.write(f"win_rate={best['win_rate']:.2f}\n")
        f.write(f"profit_factor={best['profit_factor']:.2f}\n")
        f.write(f"total_pnl={best['total_pnl']:.5f}\n")
        f.write(f"avg_pnl={best['avg_pnl']:.5f}\n")
        f.write(f"max_drawdown={best['max_drawdown']:.5f}\n")
    print(f"\n✅ Best configuration saved to: {config_path}")
    
    return results

if __name__ == '__main__':
    data_file = "/Users/kpal/projects/hermese/data/OANDA_XAGUSD1.csv"
    run_parameter_sweep(data_file)
