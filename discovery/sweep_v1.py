"""
═══════════════════════════════════════════════════════════════
LOG-FIB STRATEGY DISCOVERY - PARAMETER SWEEP
═══════════════════════════════════════════════════════════════

Systematically test ALL combinations of:
- Lookback periods
- Multiplier values
- Entry ratios
- Take-profit ratios
- Stop-loss ratios
- Direction filters (LONG only, SHORT only, both)

Goal: Find configuration with 90%+ WR and PF > 2.0
"""

import csv
import math
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple
from itertools import product
import itertools


class Candle:
    def __init__(self, date, open, high, low, close, volume=0):
        self.date = date
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume


def load_data(filepath: str) -> List[Candle]:
    """Load CSV data"""
    candles = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time_str = row.get('time', row.get('date', ''))
            try:
                if 'T' in time_str:
                    if '+' in time_str:
                        time_str = time_str.split('+')[0]
                    elif '-04:00' in time_str:
                        time_str = time_str.replace('-04:00', '')
                    elif '-05:00' in time_str:
                        time_str = time_str.replace('-05:00', '')
                    time_str = time_str.replace('T', ' ')
                date = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            except:
                continue
            
            try:
                candle = Candle(
                    date=date,
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row.get('volume', 0))
                )
                candles.append(candle)
            except:
                continue
    
    candles.sort(key=lambda c: c.date)
    return candles


def detect_swings(candles: List[Candle], lookback: int) -> Tuple[List[Dict], List[Dict]]:
    """Detect swing highs and lows with anchored points"""
    swing_highs = []
    swing_lows = []
    
    for i in range(lookback, len(candles) - lookback):
        # Swing High
        current_high = candles[i].high
        is_swing_high = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i and candles[j].high >= current_high:
                is_swing_high = False
                break
        if is_swing_high:
            swing_highs.append({
                'idx': i,
                'date': candles[i].date,
                'high': current_high,
                'low': candles[i].low  # Anchored low
            })
        
        # Swing Low
        current_low = candles[i].low
        is_swing_low = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i and candles[j].low <= current_low:
                is_swing_low = False
                break
        if is_swing_low:
            swing_lows.append({
                'idx': i,
                'date': candles[i].date,
                'low': current_low,
                'high': candles[i].high  # Anchored high
            })
    
    return swing_highs, swing_lows


def calc_effective_range(pivot: float, anchor: float, mult: float) -> float:
    """Log-Fib formula: log10(price) * |H-L| * mult * 4"""
    return math.log10(pivot) * abs(pivot - anchor) * mult * 4.0


def run_backtest(
    candles: List[Candle],
    lookback: int,
    mult: float,
    entry_ratio: float,
    tp_ratio: float,
    sl_ratio: float,
    direction: str = 'BOTH',  # 'LONG', 'SHORT', 'BOTH'
    max_bars_in_trade: int = 100
) -> Dict:
    """
    Run backtest with specific configuration
    
    Entry: Price retraces to entry_ratio level
    Exit: Price reaches tp_ratio level
    Stop: Price breaches sl_ratio level
    """
    if len(candles) < lookback * 3:
        return {'error': 'Insufficient data'}
    
    swing_highs, swing_lows = detect_swings(candles, lookback)
    
    if not swing_highs and not swing_lows:
        return {'error': 'No swings detected'}
    
    trades = []
    in_trade = False
    trade = None
    
    # Track active projections
    active_projections = []  # List of {type, entry, tp, sl, setup_idx}
    
    for i in range(len(candles)):
        candle = candles[i]
        
        # Add new projections from recent swings
        for sh in swing_highs:
            if sh['idx'] == i and (direction in ['SHORT', 'BOTH']):
                eff_range = calc_effective_range(sh['high'], sh['low'], mult)
                entry = sh['high'] - (entry_ratio * eff_range)
                tp = sh['high'] - (tp_ratio * eff_range)  # BELOW entry for SHORT
                sl = sh['high'] + (sl_ratio * eff_range)  # ABOVE entry for SHORT
                
                active_projections.append({
                    'type': 'SHORT',
                    'entry': entry,
                    'tp': tp,
                    'sl': sl,
                    'setup_idx': i,
                    'swing_price': sh['high']
                })
        
        for sl in swing_lows:
            if sl['idx'] == i and (direction in ['LONG', 'BOTH']):
                eff_range = calc_effective_range(sl['low'], sl['high'], mult)
                entry = sl['low'] + (entry_ratio * eff_range)
                tp = sl['low'] + (tp_ratio * eff_range)  # ABOVE entry for LONG
                sl_price = sl['low'] - (sl_ratio * eff_range)  # BELOW entry for LONG
                
                active_projections.append({
                    'type': 'LONG',
                    'entry': entry,
                    'tp': tp,
                    'sl': sl_price,
                    'setup_idx': i,
                    'swing_price': sl['low']
                })
        
        # Check exit conditions
        if in_trade and trade:
            bars_in_trade = i - trade['entry_idx']
            
            if trade['type'] == 'SHORT':
                # SHORT: Profit when price goes DOWN to TP
                if candle.low <= trade['tp']:
                    pnl = trade['entry'] - trade['tp']
                    trades.append({**trade, 'exit_idx': i, 'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_trade = False
                    trade = None
                # SHORT: Loss when price goes UP to SL
                elif candle.high >= trade['sl']:
                    pnl = trade['entry'] - trade['sl']
                    trades.append({**trade, 'exit_idx': i, 'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_trade = False
                    trade = None
                # Time-based exit
                elif bars_in_trade >= max_bars_in_trade:
                    # Exit at current price
                    pnl = trade['entry'] - candle.close
                    trades.append({**trade, 'exit_idx': i, 'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_trade = False
                    trade = None
            
            elif trade['type'] == 'LONG':
                # LONG: Profit when price goes UP to TP
                if candle.high >= trade['tp']:
                    pnl = trade['tp'] - trade['entry']
                    trades.append({**trade, 'exit_idx': i, 'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_trade = False
                    trade = None
                # LONG: Loss when price goes DOWN to SL
                elif candle.low <= trade['sl']:
                    pnl = trade['sl'] - trade['entry']
                    trades.append({**trade, 'exit_idx': i, 'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_trade = False
                    trade = None
                # Time-based exit
                elif bars_in_trade >= max_bars_in_trade:
                    pnl = candle.close - trade['entry']
                    trades.append({**trade, 'exit_idx': i, 'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_trade = False
                    trade = None
        
        # Check entry conditions (if not in trade)
        if not in_trade:
            # Keep only recent projections (last 20)
            active_projections = active_projections[-20:]
            
            for proj in active_projections:
                # Check if price touched entry
                if proj['type'] == 'SHORT':
                    if candle.low <= proj['entry'] and (i - proj['setup_idx']) < 50:
                        in_trade = True
                        trade = {
                            'type': 'SHORT',
                            'entry': proj['entry'],
                            'tp': proj['tp'],
                            'sl': proj['sl'],
                            'entry_idx': i,
                            'entry_date': candle.date
                        }
                        break
                elif proj['type'] == 'LONG':
                    if candle.high >= proj['entry'] and (i - proj['setup_idx']) < 50:
                        in_trade = True
                        trade = {
                            'type': 'LONG',
                            'entry': proj['entry'],
                            'tp': proj['tp'],
                            'sl': proj['sl'],
                            'entry_idx': i,
                            'entry_date': candle.date
                        }
                        break
    
    # Analyze results
    if not trades:
        return {'error': 'No trades'}
    
    winning = [t for t in trades if t['outcome'] == 'WIN']
    losing = [t for t in trades if t['outcome'] == 'LOSS']
    
    total_pnl = sum(t['pnl'] for t in trades)
    gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
    
    # Calculate streaks
    best_streak = 0
    current_streak = 0
    for t in trades:
        if t['outcome'] == 'WIN':
            current_streak += 1
            best_streak = max(best_streak, current_streak)
        else:
            current_streak = 0
    
    return {
        'total_trades': len(trades),
        'wins': len(winning),
        'losses': len(losing),
        'win_rate': len(winning) / len(trades) * 100,
        'total_pnl': total_pnl,
        'avg_pnl': total_pnl / len(trades),
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'profit_factor': gross_profit / gross_loss if gross_loss > 0 else float('inf'),
        'best_streak': best_streak,
        'long_trades': len([t for t in trades if t['type'] == 'LONG']),
        'short_trades': len([t for t in trades if t['type'] == 'SHORT'])
    }


def parameter_sweep(candles: List[Candle], instrument: str):
    """Run comprehensive parameter sweep"""
    print(f"\n{'='*80}")
    print(f"🔬 PARAMETER SWEEP: {instrument}")
    print(f"{'='*80}")
    print(f"   Candles: {len(candles)}")
    print(f"   Range: {candles[0].date} to {candles[-1].date}")
    print(f"   Price: {min(c.low for c in candles):.2f} - {max(c.high for c in candles):.2f}")
    
    # Parameter grid
    lookbacks = [6, 8, 10, 12, 15, 20]
    mults = [0.382, 0.5, 0.618, 0.786]
    entry_ratios = [0.382, 0.5, 0.618, 0.786]
    tp_ratios = [0.786, 1.0, 1.272, 1.618]
    sl_ratios = [1.0, 1.272, 1.618]
    directions = ['BOTH', 'LONG', 'SHORT']
    
    results = []
    total_configs = len(lookbacks) * len(mults) * len(entry_ratios) * len(tp_ratios) * len(sl_ratios) * len(directions)
    
    print(f"\n   Testing {total_configs} configurations...")
    
    count = 0
    for lb, mult, entry, tp, sl, direction in product(lookbacks, mults, entry_ratios, tp_ratios, sl_ratios, directions):
        count += 1
        if count % 500 == 0:
            print(f"   Progress: {count}/{total_configs} ({count/total_configs*100:.1f}%)")
        
        result = run_backtest(candles, lb, mult, entry, tp, sl, direction)
        
        if 'error' not in result and result['total_trades'] >= 10:
            results.append({
                'lookback': lb,
                'mult': mult,
                'entry': entry,
                'tp': tp,
                'sl': sl,
                'direction': direction,
                **result
            })
    
    # Sort by profit factor (primary) and win rate (secondary)
    results.sort(key=lambda x: (x['profit_factor'] if x['profit_factor'] != float('inf') else 0, x['win_rate']), reverse=True)
    
    print(f"\n{'='*80}")
    print(f"🏆 TOP 20 CONFIGURATIONS: {instrument}")
    print(f"{'='*80}")
    
    # Show top 20
    for i, r in enumerate(results[:20], 1):
        print(f"\n#{i}: WR={r['win_rate']:.1f}%, PF={r['profit_factor']:.2f}, Trades={r['total_trades']}, PnL={r['total_pnl']:+.2f}")
        print(f"    LB={r['lookback']}, Mult={r['mult']}, Entry={r['entry']}, TP={r['tp']}, SL={r['sl']}, Dir={r['direction']}")
    
    # Filter for high win rate
    high_wr = [r for r in results if r['win_rate'] >= 90 and r['profit_factor'] >= 2.0 and r['total_trades'] >= 20]
    
    print(f"\n{'='*80}")
    print(f"💎 HIGH WIN-RATE CONFIGS (WR≥90%, PF≥2.0, Trades≥20): {len(high_wr)} found")
    print(f"{'='*80}")
    
    for i, r in enumerate(high_wr[:10], 1):
        print(f"\n#{i}: WR={r['win_rate']:.1f}%, PF={r['profit_factor']:.2f}, Trades={r['total_trades']}")
        print(f"    LB={r['lookback']}, Mult={r['mult']:.3f}, Entry={r['entry']:.3f}, TP={r['tp']:.3f}, SL={r['sl']:.3f}, Dir={r['direction']}")
    
    # Save results
    output = {
        'instrument': instrument,
        'total_configs': total_configs,
        'valid_results': len(results),
        'high_wr_configs': high_wr[:20],
        'top_20': results[:20]
    }
    
    with open(f'discovery_{instrument.replace(" ", "_").replace("/", "_")}.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Saved to: discovery_{instrument.replace(' ', '_').replace('/', '_')}.json")
    
    return high_wr, results


def main():
    print("="*80)
    print("🧪 LOG-FIB STRATEGY DISCOVERY - COMPREHENSIVE SWEEP")
    print("="*80)
    print()
    print("Testing all combinations of:")
    print("  Lookback: 6, 8, 10, 12, 15, 20")
    print("  Multiplier: 0.382, 0.5, 0.618, 0.786")
    print("  Entry: 0.382, 0.5, 0.618, 0.786")
    print("  Take-Profit: 0.786, 1.0, 1.272, 1.618")
    print("  Stop-Loss: 1.0, 1.272, 1.618")
    print("  Direction: LONG, SHORT, BOTH")
    print()
    
    data_dir = Path('data')
    instruments = {
        'Silver': data_dir / 'OANDA_XAGUSD5.csv',
        'Gold': data_dir / 'OANDA_XAUUSD5.csv'
    }
    
    all_high_wr = {}
    
    for name, filepath in instruments.items():
        if not filepath.exists():
            print(f"❌ File not found: {filepath}")
            continue
        
        candles = load_data(str(filepath))
        if not candles:
            print(f"❌ No valid candles in {filepath}")
            continue
        
        high_wr, all_results = parameter_sweep(candles, name)
        all_high_wr[name] = high_wr
    
    # Cross-instrument comparison
    print(f"\n{'='*80}")
    print(f"📊 CROSS-INSTRUMENT COMPARISON")
    print(f"{'='*80}")
    
    for name, configs in all_high_wr.items():
        if configs:
            best = max(configs, key=lambda x: x['profit_factor'])
            print(f"\n{name}:")
            print(f"  Best: WR={best['win_rate']:.1f}%, PF={best['profit_factor']:.2f}, Trades={best['total_trades']}")
            print(f"  Config: LB={best['lookback']}, Mult={best['mult']}, Entry={best['entry']}, TP={best['tp']}, SL={best['sl']}")
        else:
            print(f"\n{name}: No high-win-rate configs found")
    
    print(f"\n{'='*80}")
    print(f"✅ Discovery complete")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
