import csv
import math
import os

def run_backtest(csv_path, lookback=6, multiplier=0.618, entry_ratio=0.618, exit_ratio=0.0, stop_loss_ratio=1.272):
    """
    Backtests the Log-Fib Scalping Strategy.
    
    Entry: When price retraces to entry_ratio (e.g., 0.618) of the projection
    Exit: When price reaches exit_ratio (e.g., 0.0 = swing high/low origin)
    Stop Loss: When price breaches stop_loss_ratio (e.g., 1.272 extension)
    """
    print("--- Log-Fib Scalping Backtest Engine ---")
    print(f"Lookback: {lookback} | Entry@: {entry_ratio} | Exit@: {exit_ratio} | SL@: {stop_loss_ratio}")
    
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
    
    fib_ratios = [0.0, 0.125, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.125, 1.272, 1.414, 1.618]
    
    # Track trades
    trades = []
    in_position = False
    position_type = None  # "LONG" or "SHORT"
    entry_price = 0.0
    entry_time = ""
    stop_loss = 0.0
    take_profit = 0.0
    swing_reference = None
    
    # Detect swings and simulate trades
    for i in range(lookback, len(bars) - lookback):
        if in_position:
            # Check exit conditions
            current_bar = bars[i]
            
            if position_type == "SHORT":
                # Check if TP hit (price dropped to target)
                if current_bar['low'] <= take_profit:
                    pnl = entry_price - take_profit
                    trades.append({
                        'type': 'SHORT',
                        'entry_time': entry_time,
                        'exit_time': current_bar['time'],
                        'entry_price': entry_price,
                        'exit_price': take_profit,
                        'pnl': pnl,
                        'outcome': 'WIN'
                    })
                    in_position = False
                
                # Check if SL hit
                elif current_bar['high'] >= stop_loss:
                    pnl = entry_price - stop_loss
                    trades.append({
                        'type': 'SHORT',
                        'entry_time': entry_time,
                        'exit_time': current_bar['time'],
                        'entry_price': entry_price,
                        'exit_price': stop_loss,
                        'pnl': pnl,
                        'outcome': 'LOSS'
                    })
                    in_position = False
            
            elif position_type == "LONG":
                # Check if TP hit (price rose to target)
                if current_bar['high'] >= take_profit:
                    pnl = take_profit - entry_price
                    trades.append({
                        'type': 'LONG',
                        'entry_time': entry_time,
                        'exit_time': current_bar['time'],
                        'entry_price': entry_price,
                        'exit_price': take_profit,
                        'pnl': pnl,
                        'outcome': 'WIN'
                    })
                    in_position = False
                
                # Check if SL hit
                elif current_bar['low'] <= stop_loss:
                    pnl = stop_loss - entry_price
                    trades.append({
                        'type': 'LONG',
                        'entry_time': entry_time,
                        'exit_time': current_bar['time'],
                        'entry_price': entry_price,
                        'exit_price': stop_loss,
                        'pnl': pnl,
                        'outcome': 'LOSS'
                    })
                    in_position = False
        
        # If not in position, look for new swing setups
        if not in_position:
            # Swing High Detection (for SHORT setups)
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
                
                # Calculate entry and exit levels
                entry_level = current_high - (entry_ratio * effective_range)
                exit_level = current_high - (exit_ratio * effective_range)  # Usually 0.0 = swing origin
                stop_level = current_high + (stop_loss_ratio * effective_range)
                
                # Check if price retraced to entry in subsequent bars
                for k in range(i + 1, min(i + 50, len(bars))):  # Look ahead 50 bars
                    if bars[k]['low'] <= entry_level and bars[k]['high'] >= entry_level:
                        in_position = True
                        position_type = "SHORT"
                        entry_price = entry_level
                        entry_time = bars[k]['time']
                        take_profit = exit_level
                        stop_loss = stop_level
                        swing_reference = current_high
                        break
            
            # Swing Low Detection (for LONG setups)
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
                
                # Calculate entry and exit levels
                entry_level = current_low + (entry_ratio * effective_range)
                exit_level = current_low + (exit_ratio * effective_range)  # Usually 0.0 = swing origin
                stop_level = current_low - (stop_loss_ratio * effective_range)
                
                # Check if price retraced to entry in subsequent bars
                for k in range(i + 1, min(i + 50, len(bars))):
                    if bars[k]['high'] >= entry_level and bars[k]['low'] <= entry_level:
                        in_position = True
                        position_type = "LONG"
                        entry_price = entry_level
                        entry_time = bars[k]['time']
                        take_profit = exit_level
                        stop_loss = stop_level
                        swing_reference = current_low
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
    
    # Print results
    print(f"\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    print(f"Total Trades: {total_trades}")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total P&L: {total_pnl:.5f}")
    print(f"Average P&L per Trade: {avg_pnl:.5f}")
    print(f"Profit Factor: {profit_factor:.2f}")
    print("="*60)
    
    # Show last 5 trades
    print(f"\nLast 5 Trades:")
    for t in trades[-5:]:
        print(f"  [{t['type']}] {t['outcome']} | Entry: {t['entry_price']:.5f} | Exit: {t['exit_price']:.5f} | P&L: {t['pnl']:.5f}")
    
    print(f"\n[TASK] Auditor Agent: Backtest complete. Strategy metrics calculated.")

if __name__ == '__main__':
    data_file = "/Users/kpal/projects/hermese/data/OANDA_XAGUSD1.csv"
    run_backtest(data_file, lookback=6, multiplier=0.618, entry_ratio=0.618, exit_ratio=0.0, stop_loss_ratio=1.272)
