"""
═══════════════════════════════════════════════════════════════
WALK-FORWARD VALIDATION - DISCOVERED CONFIGS
═══════════════════════════════════════════════════════════════

Validate the discovered high-win-rate configurations with 
proper walk-forward testing to ensure they're not overfit.

Best configs to validate:
- Silver: LB=6, Mult=0.5, Entry=0.382, TP=1.272, SL=1.618
- Gold: LB=8, Mult=0.618, Entry=0.5, TP=1.0, SL=1.618
"""

import csv
import math
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple


class Candle:
    def __init__(self, date, open, high, low, close, volume=0):
        self.date = date
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume


def load_data(filepath: str) -> List[Candle]:
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
    swing_highs = []
    swing_lows = []
    
    for i in range(lookback, len(candles) - lookback):
        current_high = candles[i].high
        is_swing_high = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i and candles[j].high >= current_high:
                is_swing_high = False
                break
        if is_swing_high:
            swing_highs.append({'idx': i, 'high': current_high, 'low': candles[i].low})
        
        current_low = candles[i].low
        is_swing_low = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i and candles[j].low <= current_low:
                is_swing_low = False
                break
        if is_swing_low:
            swing_lows.append({'idx': i, 'low': current_low, 'high': candles[i].high})
    
    return swing_highs, swing_lows


def calc_effective_range(pivot: float, anchor: float, mult: float) -> float:
    return math.log10(pivot) * abs(pivot - anchor) * mult * 4.0


def run_backtest_config(candles: List[Candle], config: Dict) -> Dict:
    lb = config['lookback']
    mult = config['mult']
    entry_ratio = config['entry']
    tp_ratio = config['tp']
    sl_ratio = config['sl']
    direction = config.get('direction', 'BOTH')
    
    swing_highs, swing_lows = detect_swings(candles, lb)
    
    trades = []
    in_trade = False
    trade = None
    active_projections = []
    
    for i in range(len(candles)):
        candle = candles[i]
        
        for sh in swing_highs:
            if sh['idx'] == i and direction in ['SHORT', 'BOTH']:
                eff_range = calc_effective_range(sh['high'], sh['low'], mult)
                entry = sh['high'] - (entry_ratio * eff_range)
                tp = sh['high'] - (tp_ratio * eff_range)
                sl = sh['high'] + (sl_ratio * eff_range)
                active_projections.append({'type': 'SHORT', 'entry': entry, 'tp': tp, 'sl': sl, 'setup_idx': i})
        
        for sl in swing_lows:
            if sl['idx'] == i and direction in ['LONG', 'BOTH']:
                eff_range = calc_effective_range(sl['low'], sl['high'], mult)
                entry = sl['low'] + (entry_ratio * eff_range)
                tp = sl['low'] + (tp_ratio * eff_range)
                sl_price = sl['low'] - (sl_ratio * eff_range)
                active_projections.append({'type': 'LONG', 'entry': entry, 'tp': tp, 'sl': sl_price, 'setup_idx': i})
        
        if in_trade and trade:
            if trade['type'] == 'SHORT':
                if candle.low <= trade['tp']:
                    pnl = trade['entry'] - trade['tp']
                    trades.append({**trade, 'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_trade = False
                elif candle.high >= trade['sl']:
                    pnl = trade['entry'] - trade['sl']
                    trades.append({**trade, 'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_trade = False
            elif trade['type'] == 'LONG':
                if candle.high >= trade['tp']:
                    pnl = trade['tp'] - trade['entry']
                    trades.append({**trade, 'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_trade = False
                elif candle.low <= trade['sl']:
                    pnl = trade['sl'] - trade['entry']
                    trades.append({**trade, 'pnl': pnl, 'outcome': 'WIN' if pnl > 0 else 'LOSS'})
                    in_trade = False
        
        if not in_trade:
            active_projections = active_projections[-20:]
            for proj in active_projections:
                if proj['type'] == 'SHORT' and candle.low <= proj['entry'] and (i - proj['setup_idx']) < 50:
                    in_trade = True
                    trade = {'type': 'SHORT', 'entry': proj['entry'], 'tp': proj['tp'], 'sl': proj['sl'], 'entry_idx': i}
                    break
                elif proj['type'] == 'LONG' and candle.high >= proj['entry'] and (i - proj['setup_idx']) < 50:
                    in_trade = True
                    trade = {'type': 'LONG', 'entry': proj['entry'], 'tp': proj['tp'], 'sl': proj['sl'], 'entry_idx': i}
                    break
    
    if not trades:
        return {'error': 'No trades'}
    
    winning = [t for t in trades if t['outcome'] == 'WIN']
    gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
    
    return {
        'trades': len(trades),
        'wins': len(winning),
        'win_rate': len(winning) / len(trades) * 100,
        'total_pnl': sum(t['pnl'] for t in trades),
        'profit_factor': gross_profit / gross_loss if gross_loss > 0 else float('inf')
    }


def walk_forward(candles: List[Candle], config: Dict, n_folds: int = 5):
    """Run walk-forward with discovered config"""
    total = len(candles)
    fold_size = total // n_folds
    
    print(f"\n{'='*80}")
    print(f"🔄 WALK-FORWARD VALIDATION")
    print(f"{'='*80}")
    print(f"Config: LB={config['lookback']}, Mult={config['mult']}, Entry={config['entry']}, TP={config['tp']}, SL={config['sl']}")
    print(f"Folds: {n_folds}")
    print(f"Total candles: {total}")
    
    fold_results = []
    
    for fold in range(n_folds):
        test_start = fold * fold_size
        test_end = (fold + 1) * fold_size
        test_candles = candles[test_start:test_end]
        
        result = run_backtest_config(test_candles, config)
        
        if 'error' not in result:
            fold_results.append({
                'fold': fold + 1,
                'start': test_start,
                'end': test_end,
                **result
            })
            print(f"\nFold {fold+1}/{n_folds}: Trades={result['trades']}, WR={result['win_rate']:.1f}%, PF={result['profit_factor']:.2f}, PnL={result['total_pnl']:+.2f}")
    
    # Aggregate
    if fold_results:
        total_trades = sum(r['trades'] for r in fold_results)
        total_wins = sum(r['wins'] for r in fold_results)
        total_pnl = sum(r['total_pnl'] for r in fold_results)
        agg_wr = total_wins / total_trades * 100
        
        pfs = [r['profit_factor'] for r in fold_results if r['profit_factor'] != float('inf')]
        avg_pf = sum(pfs) / len(pfs) if pfs else 0
        
        profitable_folds = sum(1 for r in fold_results if r['total_pnl'] > 0)
        
        print(f"\n{'='*80}")
        print(f"📈 AGGREGATE WALK-FORWARD RESULTS")
        print(f"{'='*80}")
        print(f"Total Trades: {total_trades}")
        print(f"Aggregate WR: {agg_wr:.2f}%")
        print(f"Total PnL: {total_pnl:+.2f}")
        print(f"Avg PF: {avg_pf:.2f}")
        print(f"Profitable Folds: {profitable_folds}/{n_folds} ({profitable_folds/n_folds*100:.1f}%)")
        
        # Stability assessment
        if agg_wr >= 90 and profitable_folds >= n_folds * 0.8:
            print(f"\n✅ STABLE EDGE - Walk-forward VALIDATED")
        elif agg_wr >= 70 and profitable_folds >= n_folds * 0.6:
            print(f"\n⚠️  MODERATE EDGE - Some degradation but viable")
        else:
            print(f"\n❌ UNSTABLE - Likely overfit, not recommended for live trading")
        
        return {
            'agg_wr': agg_wr,
            'total_pnl': total_pnl,
            'avg_pf': avg_pf,
            'profitable_folds': profitable_folds,
            'folds': fold_results
        }
    
    return None


def main():
    print("="*80)
    print("🧪 WALK-FORWARD VALIDATION - DISCOVERED HIGH-WR CONFIGS")
    print("="*80)
    
    # Configs to validate
    configs = {
        'Silver_Best': {
            'lookback': 6, 'mult': 0.5, 'entry': 0.382, 'tp': 1.272, 'sl': 1.618, 'direction': 'BOTH'
        },
        'Gold_Best': {
            'lookback': 8, 'mult': 0.618, 'entry': 0.5, 'tp': 1.0, 'sl': 1.618, 'direction': 'BOTH'
        },
        'Silver_Alternative': {
            'lookback': 6, 'mult': 0.382, 'entry': 0.382, 'tp': 1.272, 'sl': 1.0, 'direction': 'BOTH'
        }
    }
    
    data_dir = Path('data')
    instruments = {
        'Silver': data_dir / 'OANDA_XAGUSD5.csv',
        'Gold': data_dir / 'OANDA_XAUUSD5.csv'
    }
    
    all_results = {}
    
    for inst_name, filepath in instruments.items():
        if not filepath.exists():
            continue
        
        candles = load_data(str(filepath))
        if not candles:
            continue
        
        print(f"\n{'='*80}")
        print(f"📊 {inst_name}")
        print(f"{'='*80}")
        
        # Test relevant configs for this instrument
        for config_name, config in configs.items():
            if config_name.startswith(inst_name) or config_name == 'Gold_Best' and inst_name == 'Gold':
                print(f"\n🔬 Testing: {config_name}")
                result = walk_forward(candles, config, n_folds=5)
                if result:
                    all_results[f"{inst_name}_{config_name}"] = result
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📊 FINAL SUMMARY")
    print(f"{'='*80}")
    
    for name, result in all_results.items():
        stability = "✅ VALIDATED" if result['agg_wr'] >= 90 and result['profitable_folds'] >= 4 else "⚠️  DEGRADED" if result['agg_wr'] >= 70 else "❌ OVERFIT"
        print(f"{name}: WR={result['agg_wr']:.1f}%, PF={result['avg_pf']:.2f}, Folds={result['profitable_folds']}/5 → {stability}")
    
    # Save
    with open('walk_forward_validation.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n💾 Saved to: walk_forward_validation.json")


if __name__ == "__main__":
    main()
