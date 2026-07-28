"""
═══════════════════════════════════════════════════════════════
WALK-FORWARD ANALYSIS - GOLD (XAUUSD) & SILVER (XAGUSD)
═══════════════════════════════════════════════════════════════

Tests the Log-Fib strategy on precious metals using OANDA 5-minute data.
Walk-forward validation with corrected profit factor calculation.

Data: OANDA XAUUSD5, XAGUSD5 (5-minute candles)
Windows: 5-fold walk-forward (60% train, 20% test, 20% step)
Parameters: Lookback (5, 10, 15, 20), Fib (0.618, 0.705, 0.786, 0.886)
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import itertools


@dataclass
class Candle:
    date: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass
class Trade:
    entry_date: datetime
    direction: str
    entry_price: float
    exit_price: float
    exit_date: datetime
    pnl: float


def load_data(filepath: str) -> List[Candle]:
    """Load CSV data with standard OHLC format"""
    candles = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse timestamp (ISO format with timezone)
            time_str = row.get('time', row.get('date', row.get('timestamp', '')))
            try:
                # Handle ISO format with timezone
                if 'T' in time_str:
                    time_str = time_str.split('+')[0].split('-04:00')[0].replace('T', ' ')
                date = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            except:
                continue
            
            try:
                candle = Candle(
                    date=date,
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close'])
                )
                candles.append(candle)
            except (KeyError, ValueError) as e:
                continue
    
    # Sort by date
    candles.sort(key=lambda c: c.date)
    return candles


def find_swing_high(idx: int, lookback: int, candles: List[Candle]) -> Optional[float]:
    if idx < lookback:
        return None
    current_high = candles[idx].high
    for i in range(1, lookback + 1):
        if candles[idx - i].high >= current_high:
            return None
    return current_high


def find_swing_low(idx: int, lookback: int, candles: List[Candle]) -> Optional[float]:
    if idx < lookback:
        return None
    current_low = candles[idx].low
    for i in range(1, lookback + 1):
        if candles[idx - i].low <= current_low:
            return None
    return current_low


def run_backtest(candles: List[Candle], lookback: int, fib_mult: float = 0.786, sl_mult: float = 0.236) -> List[Trade]:
    trades = []
    i = lookback
    in_trade = False
    
    while i < len(candles):
        candle = candles[i]
        
        # SHORT setup: Swing Low → Swing High → Retrace down
        swing_high = find_swing_high(i, lookback, candles)
        if swing_high and not in_trade:
            swing_low = None
            for j in range(i - 1, max(0, i - lookback * 3), -1):
                low = find_swing_low(j, lookback, candles)
                if low:
                    swing_low = low
                    break
            
            if swing_low and swing_low < swing_high:
                range_size = swing_high - swing_low
                entry_price = swing_low + fib_mult * range_size
                target = swing_low
                stop_loss = swing_high + range_size * sl_mult
                
                if candle.low <= entry_price <= candle.high:
                    entry_date = candle.date
                    in_trade = True
                    trade_direction = 'SHORT'
                    trade_entry = entry_price
                    trade_target = target
                    trade_stop = stop_loss
        
        # LONG setup: Swing High → Swing Low → Retrace up
        swing_low = find_swing_low(i, lookback, candles)
        if swing_low and not in_trade:
            swing_high = None
            for j in range(i - 1, max(0, i - lookback * 3), -1):
                high = find_swing_high(j, lookback, candles)
                if high:
                    swing_high = high
                    break
            
            if swing_high and swing_high > swing_low:
                range_size = swing_high - swing_low
                entry_price = swing_low + fib_mult * range_size
                target = swing_high
                stop_loss = swing_low - range_size * sl_mult
                
                if candle.low <= entry_price <= candle.high:
                    entry_date = candle.date
                    in_trade = True
                    trade_direction = 'LONG'
                    trade_entry = entry_price
                    trade_target = target
                    trade_stop = stop_loss
        
        # Manage trade
        if in_trade:
            if trade_direction == 'SHORT':
                if candle.low <= trade_target:
                    pnl = trade_entry - trade_target
                    trades.append(Trade(entry_date, 'SHORT', trade_entry, trade_target, candle.date, pnl))
                    in_trade = False
                elif candle.high >= trade_stop:
                    pnl = trade_entry - trade_stop
                    trades.append(Trade(entry_date, 'SHORT', trade_entry, trade_stop, candle.date, pnl))
                    in_trade = False
            else:  # LONG
                if candle.high >= trade_target:
                    pnl = trade_target - trade_entry
                    trades.append(Trade(entry_date, 'LONG', trade_entry, trade_target, candle.date, pnl))
                    in_trade = False
                elif candle.low <= trade_stop:
                    pnl = trade_stop - trade_entry
                    trades.append(Trade(entry_date, 'LONG', trade_entry, trade_stop, candle.date, pnl))
                    in_trade = False
        
        i += 1
    
    return trades


def analyze_trades(trades: List[Trade]) -> Dict:
    if not trades:
        return {'error': 'No trades'}
    
    winning = [t for t in trades if t.pnl > 0]
    losing = [t for t in trades if t.pnl <= 0]
    
    total_pnl = sum(t.pnl for t in trades)
    gross_profit = sum(t.pnl for t in winning)
    gross_loss = abs(sum(t.pnl for t in losing))
    
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
        'max_dd': 0  # Simplified
    }


def walk_forward_split(candles: List[Candle], n_folds: int = 5) -> List[Tuple[List[Candle], List[Candle]]]:
    total = len(candles)
    train_pct = 0.6
    test_pct = 0.2
    
    splits = []
    step = int(total * 0.2)
    
    for fold in range(n_folds):
        train_end = int(total * train_pct) + (fold * step)
        test_start = train_end
        test_end = test_start + int(total * test_pct)
        
        if test_end > total:
            test_end = total
        if train_end > total:
            break
        
        train = candles[:train_end]
        test = candles[test_start:test_end]
        
        if len(train) > 100 and len(test) > 50:
            splits.append((train, test))
    
    return splits


def optimize_params(train_candles: List[Candle]) -> Dict:
    lookbacks = [5, 10, 15, 20]
    fibs = [0.618, 0.705, 0.786, 0.886]
    
    best = None
    best_score = -float('inf')
    all_results = []
    
    for lb, fib in itertools.product(lookbacks, fibs):
        trades = run_backtest(train_candles, lb, fib)
        metrics = analyze_trades(trades)
        
        if 'error' not in metrics:
            score = metrics['win_rate'] * metrics['profit_factor']
            all_results.append({
                'lookback': lb, 'fib': fib,
                'wr': metrics['win_rate'], 'pnl': metrics['total_pnl'],
                'pf': metrics['profit_factor'], 'score': score
            })
            
            if score > best_score:
                best_score = score
                best = {'lookback': lb, 'fib': fib}
    
    return {
        'best': best,
        'all': sorted(all_results, key=lambda x: x['score'], reverse=True)[:5]
    }


def run_walk_forward(instrument: str, data_file: str, n_folds: int = 5):
    print(f"\n{'='*80}")
    print(f"🔄 WALK-FORWARD: {instrument}")
    print(f"{'='*80}")
    
    candles = load_data(data_file)
    print(f"📁 Loaded {len(candles)} candles from {data_file}")
    if candles:
        print(f"   Range: {candles[0].date} to {candles[-1].date}")
        print(f"   Price: {min(c.low for c in candles):.2f} - {max(c.high for c in candles):.2f}")
    
    if len(candles) < 500:
        print(f"⚠️  Insufficient data for walk-forward (need 500+, have {len(candles)})")
        return None
    
    splits = walk_forward_split(candles, n_folds)
    print(f"\n✅ Created {len(splits)} walk-forward windows")
    
    fold_results = []
    
    for fold_idx, (train, test) in enumerate(splits, 1):
        print(f"\n{'='*80}")
        print(f"📊 FOLD {fold_idx}/{len(splits)}")
        print(f"{'='*80}")
        print(f"   Train: {len(train)} candles ({train[0].date.date()} to {train[-1].date.date()})")
        print(f"   Test:  {len(test)} candles ({test[0].date.date()} to {test[-1].date.date()})")
        
        # Optimize on training
        opt = optimize_params(train)
        best = opt['best']
        
        print(f"\n🔧 Best params: LB={best['lookback']}, Fib={best['fib']:.3f}")
        print(f"   Top 3:")
        for i, r in enumerate(opt['all'][:3], 1):
            print(f"      {i}. LB={r['lookback']}, Fib={r['fib']:.3f} → WR={r['wr']:.1f}%, PF={r['pf']:.2f}")
        
        # Test OOS
        oos_trades = run_backtest(test, best['lookback'], best['fib'])
        oos = analyze_trades(oos_trades)
        
        # Fixed params for comparison
        fixed_trades = run_backtest(test, 10, 0.786)
        fixed = analyze_trades(fixed_trades)
        
        print(f"\n   OOS (Optimized):")
        if 'error' not in oos:
            print(f"      Trades: {oos['total_trades']}, WR: {oos['win_rate']:.1f}%, PnL: {oos['total_pnl']:+.2f}, PF: {oos['profit_factor']:.2f}")
        else:
            print(f"      ❌ No trades")
        
        print(f"   OOS (Fixed LB=10, Fib=0.786):")
        if 'error' not in fixed:
            print(f"      Trades: {fixed['total_trades']}, WR: {fixed['win_rate']:.1f}%, PnL: {fixed['total_pnl']:+.2f}, PF: {fixed['profit_factor']:.2f}")
        
        fold_results.append({
            'fold': fold_idx,
            'opt_params': best,
            'opt_metrics': oos if 'error' not in oos else None,
            'fixed_metrics': fixed if 'error' not in fixed else None
        })
    
    # Aggregate
    print(f"\n{'='*80}")
    print(f"📈 AGGREGATE RESULTS: {instrument}")
    print(f"{'='*80}")
    
    valid = [r for r in fold_results if r['opt_metrics']]
    if valid:
        total_trades = sum(r['opt_metrics']['total_trades'] for r in valid)
        total_wins = sum(r['opt_metrics']['wins'] for r in valid)
        total_pnl = sum(r['opt_metrics']['total_pnl'] for r in valid)
        agg_wr = total_wins / total_trades * 100 if total_trades > 0 else 0
        
        pfs = [r['opt_metrics']['profit_factor'] for r in valid if r['opt_metrics']['profit_factor'] != float('inf')]
        avg_pf = sum(pfs) / len(pfs) if pfs else 0
        
        profitable = sum(1 for r in valid if r['opt_metrics']['total_pnl'] > 0)
        
        print(f"\n   Folds: {len(valid)}/{len(fold_results)}")
        print(f"   Total Trades: {total_trades}")
        print(f"   Aggregate WR: {agg_wr:.2f}%")
        print(f"   Total PnL: {total_pnl:+.2f}")
        print(f"   Avg PF: {avg_pf:.2f}")
        print(f"   Profitable Folds: {profitable}/{len(valid)} ({profitable/len(valid)*100:.1f}%)")
        
        return {
            'instrument': instrument,
            'candles': len(candles),
            'folds': len(valid),
            'agg_wr': agg_wr,
            'total_pnl': total_pnl,
            'avg_pf': avg_pf,
            'profitable_folds': profitable,
            'per_fold': fold_results
        }
    
    return None


def main():
    print("="*80)
    print("🧪 WALK-FORWARD ANALYSIS - PRECIOUS METALS")
    print("="*80)
    print()
    print("Testing Parameters:")
    print("  • Lookback: 5, 10, 15, 20 candles")
    print("  • Fib Entry: 0.618, 0.705, 0.786, 0.886")
    print("  • Stop Loss: 23.6% beyond swing")
    print("  • Walk-Forward: 5 folds (60% train, 20% test)")
    print()
    
    data_dir = Path('data')
    instruments = {
        'Gold (XAUUSD)': data_dir / 'OANDA_XAUUSD5.csv',
        'Silver (XAGUSD)': data_dir / 'OANDA_XAGUSD5.csv'
    }
    
    all_results = {}
    
    for name, filepath in instruments.items():
        if filepath.exists():
            result = run_walk_forward(name, str(filepath), n_folds=5)
            if result:
                all_results[name] = result
        else:
            print(f"❌ File not found: {filepath}")
    
    # Comparison summary
    print(f"\n{'='*80}")
    print(f"📊 CROSS-INSTRUMENT COMPARISON")
    print(f"{'='*80}")
    print(f"{'Instrument':<20} {'Candles':<10} {'Folds':<8} {'Agg WR':<12} {'Total PnL':<15} {'Avg PF':<10} {'Stability':<12}")
    print(f"{'-'*80}")
    
    for name, r in all_results.items():
        stability = "✅ Stable" if r['profitable_folds'] >= r['folds'] * 0.8 else "⚠️ Mixed" if r['profitable_folds'] >= r['folds'] * 0.5 else "❌ Unstable"
        print(f"{name:<20} {r['candles']:<10} {r['folds']:<8} {r['agg_wr']:>8.2f}%    {r['total_pnl']:>+12.2f}  {r['avg_pf']:>8.2f}  {stability:<12}")
    
    print(f"{'-'*80}")
    
    # Save results
    with open('walk_forward_metals_results.json', 'w') as f:
        # Simplify for JSON
        save_data = {}
        for name, r in all_results.items():
            save_data[name] = {k: v for k, v in r.items() if k != 'per_fold'}
            save_data[name]['fold_summary'] = [
                {
                    'fold': fr['fold'],
                    'params': fr['opt_params'],
                    'oos_wr': fr['opt_metrics']['win_rate'] if fr['opt_metrics'] else None,
                    'oos_pnl': fr['opt_metrics']['total_pnl'] if fr['opt_metrics'] else None
                }
                for fr in r['per_fold']
            ]
        json.dump(save_data, f, indent=2)
    
    print(f"\n💾 Saved to: walk_forward_metals_results.json")
    
    # Final verdict
    print(f"\n{'='*80}")
    print(f"⚖️  FINAL VERDICT")
    print(f"{'='*80}")
    
    viable = [name for name, r in all_results.items() if r['agg_wr'] >= 50 and r['avg_pf'] >= 1.0]
    
    if viable:
        print(f"✅ VIABLE STRATEGY on: {', '.join(viable)}")
        best = max(viable, key=lambda n: all_results[n]['avg_pf'])
        print(f"   Best: {best} (PF={all_results[best]['avg_pf']:.2f}, WR={all_results[best]['agg_wr']:.1f}%)")
    else:
        print(f"❌ NO VIABLE STRATEGY found")
        print(f"   Required: WR ≥ 50%, PF ≥ 1.0, 80% profitable folds")
        if all_results:
            best = max(all_results.keys(), key=lambda n: all_results[n]['avg_pf'])
            print(f"   Best found: {best} (PF={all_results[best]['avg_pf']:.2f}, WR={all_results[best]['agg_wr']:.1f}%)")
    
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
