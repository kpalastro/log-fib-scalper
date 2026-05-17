import csv
import math
import os

def calculate_log_fib_projection(csv_path, lookback=6, multiplier=0.618):
    """
    Implements the Pal Log-Fib Range Projection formula.
    Core Formula: Effective_Range = log10(Swing_Price) * |Swing - Anchored| * multiplier * 4.0
    """
    print("--- Log-Fib Projection Engine Started ---")
    print(f"Lookback: {lookback} bars | Multiplier: {multiplier}")
    
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
    
    print(f"Loaded {len(bars)} bars from {csv_path}")
    
    if len(bars) < lookback:
        print(f"ERROR: Not enough bars ({len(bars)}) for lookback ({lookback})")
        return

    # Fibonacci ratios
    fib_ratios = [0.0, 0.125, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.125, 1.272, 1.414, 1.618]
    
    # Scan for Swing Highs and Swing Lows
    swing_highs = []
    swing_lows = []
    
    for i in range(lookback, len(bars) - lookback):
        # Swing High Detection
        current_high = bars[i]['high']
        is_swing_high = True
        swing_high_idx = i
        
        for j in range(i - lookback, i + lookback + 1):
            if j != i and bars[j]['high'] >= current_high:
                is_swing_high = False
                break
        
        if is_swing_high:
            # Anchored Low = Low of the exact bar that produced the Swing High
            anchored_low = bars[i]['low']
            swing_highs.append({
                'idx': i,
                'time': bars[i]['time'],
                'swing_high': current_high,
                'anchored_low': anchored_low
            })
        
        # Swing Low Detection
        current_low = bars[i]['low']
        is_swing_low = True
        swing_low_idx = i
        
        for j in range(i - lookback, i + lookback + 1):
            if j != i and bars[j]['low'] <= current_low:
                is_swing_low = False
                break
        
        if is_swing_low:
            # Anchored High = High of the exact bar that produced the Swing Low
            anchored_high = bars[i]['high']
            swing_lows.append({
                'idx': i,
                'time': bars[i]['time'],
                'swing_low': current_low,
                'anchored_high': anchored_high
            })
    
    print(f"\n--- Detected Swing Points ---")
    print(f"Swing Highs Found: {len(swing_highs)}")
    print(f"Swing Lows Found: {len(swing_lows)}")
    
    # Calculate Projections for the last 3 swing points
    print(f"\n--- Projection Calculations (Last 3 Swings) ---")
    
    # Top Projections
    for swing in swing_highs[-3:]:
        sh = swing['swing_high']
        al = swing['anchored_low']
        log_sh = math.log10(sh)
        range_diff = abs(sh - al)
        effective_range_top = log_sh * range_diff * multiplier * 4.0
        
        print(f"\n[SWING HIGH] @ {swing['time']}")
        print(f"  Swing High: {sh:.5f} | Anchored Low: {al:.5f}")
        print(f"  log10(SH): {log_sh:.5f} | Range Diff: {range_diff:.5f}")
        print(f"  Effective Range (Top): {effective_range_top:.5f}")
        print(f"  Projection Levels:")
        for ratio in fib_ratios:
            level = sh - (ratio * effective_range_top)
            print(f"    {ratio:.3f}: {level:.5f}")
    
    # Bottom Projections
    for swing in swing_lows[-3:]:
        sl = swing['swing_low']
        ah = swing['anchored_high']
        log_sl = math.log10(sl)
        range_diff = abs(sl - ah)
        effective_range_bot = log_sl * range_diff * multiplier * 4.0
        
        print(f"\n[SWING LOW] @ {swing['time']}")
        print(f"  Swing Low: {sl:.5f} | Anchored High: {ah:.5f}")
        print(f"  log10(SL): {log_sl:.5f} | Range Diff: {range_diff:.5f}")
        print(f"  Effective Range (Bot): {effective_range_bot:.5f}")
        print(f"  Projection Levels:")
        for ratio in fib_ratios:
            level = sl + (ratio * effective_range_bot)
            print(f"    {ratio:.3f}: {level:.5f}")
    
    print(f"\n[TASK] Statistician Agent: Geometric projections complete. Ready for strategy backtesting.")

if __name__ == '__main__':
    data_file = "/Users/kpal/projects/hermese/data/OANDA_XAGUSD1.csv"
    calculate_log_fib_projection(data_file, lookback=6, multiplier=0.618)
