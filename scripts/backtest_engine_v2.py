import csv
import math
import os

def run_backtest_v2(csv_path, lookback=6, multiplier=0.618, entry_ratio=0.618, take_profit_ratio=1.0, stop_loss_ratio=1.272):
    """
    Backtests the Log-Fib Scalping Strategy - CORRECTED VERSION
    
    Entry: When price retraces to entry_ratio (e.g., 0.618) of the projection
    Exit (LONG): When price rises to take_profit_ratio extension ABOVE swing low
    Exit (SHORT): When price falls to take_profit_ratio extension BELOW swing high
    Stop Loss: When price breaches stop_loss_ratio
    """
    print("--- Log-Fib Scalping Backtest Engine V2 (Corrected) ---")
    print(f"Lookback: {lookback} | Entry@: {entry_ratio} | TP@: {take_profit_ratio} | SL@: {stop_loss_ratio}")
    
    if not os.path.exists(csv_path):
        print(f"ERROR: File {csv_path} not found.")
        return

    # Load all data
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
    
    print(f"Loaded {len(bars)} bars")
    
    # Track trades
    trades = []
    in_position = False
    position_type = None
    entry_price = 0.0
    entry_time = ""
    stop_loss = 0.0
    take_profit = 0.0
    
    # Detect swings and simulate trades
    for i in range(lookback, len(bars) - lookback):
        if in_position:
            current_bar = bars[i]
            
            if position_type == "SHORT":
                # SHORT profits when price goes DOWN
                # Check if TP hit (price dropped to target BELOW entry)
                if current_bar['low'] <= take_profit:
                    pnl = entry_price - take_profit
                    trades.append({
                        'type': 'SHORT',
                        'entry_time': entry_time,
                        'exit_time': current_bar['time'],
                        'entry_price': entry_price,
                        'exit_price': take_profit,
                        'pnl': pnl,
                        'outcome': 'WIN' if pnl > 0 else 'LOSS'
                    })
                    in_position = False
                
                # Check if SL hit (price went UP above stop)
                elif current_bar['high'] >= stop_loss:
                    pnl = entry_price - stop_loss
                    trades.append({
                        'type': 'SHORT',
                        'entry_time': entry_time,
                        'exit_time': current_bar['time'],
                        'entry_price': entry_price,
                        'exit_price': stop_loss,
                        'pnl': pnl,
                        'outcome': 'WIN' if pnl > 0 else 'LOSS'
                    })
                    in_position = False
            
            elif position_type == "LONG":
                # LONG profits when price goes UP
                # Check if TP hit (price rose to target ABOVE entry)
                if current_bar['high'] >= take_profit:
                    pnl = take_profit - entry_price
                    trades.append({
                        'type': 'LONG',
                        'entry_time': entry_time,
                        'exit_time': current_bar['time'],
                        'entry_price': entry_price,
                        'exit_price': take_profit,
                        'pnl': pnl,
                        'outcome': 'WIN' if pnl > 0 else 'LOSS'
                    })
                    in_position = False
                
                # Check if SL hit (price went DOWN below stop)
                elif current_bar['low'] <= stop_loss:
                    pnl = stop_loss - entry_price
                    trades.append({
                        'type': 'LONG',
                        'entry_time': entry_time,
                        'exit_time': current_bar['time'],
                        'entry_price': entry_price,
                        'exit_price': stop_loss,
                        'pnl': pnl,
                        'outcome': 'WIN' if pnl > 0 else 'LOSS'
                    })
                    in_position = False
        
        # If not in position, look for new swing setups
        if not in_position:
            # Swing High Detection (for SHORT setups - expecting price to fall after retracement)
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
                
                # SHORT: Entry at retracement (0.618), TP at extension BELOW (1.0+)
                entry_level = current_high - (entry_ratio * effective_range)
                take_profit_level = current_high - (take_profit_ratio * effective_range)  # BELOW entry
                stop_level = current_high + (stop_loss_ratio * effective_range)  # ABOVE entry
                
                # Check if price retraced to entry in subsequent bars (within 50 bars)
                for k in range(i + 1, min(i + 50, len(bars))):
                    if bars[k]['low'] <= entry_level:
                        in_position = True
                        position_type = "SHORT"
                        entry_price = entry_level
                        entry_time = bars[k]['time']
                        take_profit = take_profit_level
                        stop_loss = stop_level
                        break
            
            # Swing Low Detection (for LONG setups - expecting price to rise after retracement)
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
                
                # LONG: Entry at retracement (0.618), TP at extension ABOVE (1.0+)
                entry_level = current_low + (entry_ratio * effective_range)
                take_profit_level = current_low + (take_profit_ratio * effective_range)  # ABOVE entry
                stop_level = current_low - (stop_loss_ratio * effective_range)  # BELOW entry
                
                # Check if price retraced to entry in subsequent bars (within 50 bars)
                for k in range(i + 1, min(i + 50, len(bars))):
                    if bars[k]['high'] >= entry_level:
                        in_position = True
                        position_type = "LONG"
                        entry_price = entry_level
                        entry_time = bars[k]['time']
                        take_profit = take_profit_level
                        stop_loss = stop_level
                        break
    
    # Calculate statistics
    total_trades = len(trades)
    wins = sum(1 for t in trades if t['outcome'] == 'WIN')
    losses = sum(1 for t in trades if t['outcome'] == 'LOSS')
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    total_pnl = sum(t['pnl'] for t in trades)
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
    
    gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')
    
    # Find max drawdown
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
    
    # Print results
    print(f"\n" + "="*60)
    print("BACKTEST RESULTS - CORRECTED LOGIC")
    print("="*60)
    print(f"Total Trades: {total_trades}")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total P&L: {total_pnl:.5f}")
    print(f"Average P&L per Trade: {avg_pnl:.5f}")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Max Drawdown: {max_drawdown:.5f}")
    print("="*60)
    
    # Show last 5 trades
    print(f"\nLast 5 Trades:")
    for t in trades[-5:]:
        direction = "↑" if t['type'] == 'LONG' else "↓"
        result = "✓" if t['outcome'] == 'WIN' else "✗"
        print(f"  {direction} [{t['type']}] {result} | Entry: {t['entry_price']:.5f} | Exit: {t['exit_price']:.5f} | P&L: {t['pnl']:+.5f}")
    
    print(f"\n[TASK] Auditor Agent: Backtest V2 complete. Strategy metrics calculated.")
    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_pnl': avg_pnl,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown
    }

if __name__ == '__main__':
    data_file = "/Users/kpal/projects/hermese/data/OANDA_XAGUSD1.csv"
    run_backtest_v2(data_file, lookback=6, multiplier=0.618, entry_ratio=0.618, take_profit_ratio=1.0, stop_loss_ratio=1.272)
