"""
═══════════════════════════════════════════════════════════════
NIFTY50 WALK-FORWARD ANALYSIS - 5 MINUTE TIMEFRAME
═══════════════════════════════════════════════════════════════

Walk-forward testing validates strategy robustness by:
1. Splitting data into multiple training/testing windows
2. Optimizing parameters on in-sample data
3. Testing on out-of-sample (forward) data
4. Rolling the window forward and repeating

This proves the strategy works across different market regimes
and is not curve-fitted to specific data.

Data: Nifty50 5-minute (60 days, 2,850 candles)
Windows: 5 folds (20% training, 10% testing each)
Parameters Tested: Lookback (5, 10, 15, 20), Fib (0.618, 0.705, 0.786, 0.886)
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
    """OHLC candle representation"""
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class Trade:
    """Trade record"""
    entry_date: datetime
    direction: str
    entry_price: float
    exit_price: float
    exit_date: datetime
    pnl: float
    won: bool


class WalkForwardAnalyzer:
    """Walk-forward analysis for Nifty50 Log-Fib strategy"""
    
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.candles: List[Candle] = []
        
    def load_data(self) -> bool:
        """Load Nifty50 data from CSV"""
        print(f"📁 Using: {self.data_file}")
        print(f"📥 Loading Zerodha 5m data: {self.data_file}")
        
        try:
            with open(self.data_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    candle = Candle(
                        date=datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S'),
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=int(row['volume'])
                    )
                    self.candles.append(candle)
            
            print(f"✅ Loaded {len(self.candles)} candles")
            if self.candles:
                print(f"   Range: {self.candles[0].date} to {self.candles[-1].date}")
                print(f"   Price: {min(c.low for c in self.candles):.2f} - {max(c.high for c in self.candles):.2f}")
                dates = set(c.date.date() for c in self.candles)
                print(f"   Trading Days: {len(dates)}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False
    
    def find_swing_high(self, idx: int, lookback: int, candles: List[Candle]) -> Optional[float]:
        """Find swing high at index"""
        if idx < lookback:
            return None
        current_high = candles[idx].high
        for i in range(1, lookback + 1):
            if candles[idx - i].high >= current_high:
                return None
        return current_high
    
    def find_swing_low(self, idx: int, lookback: int, candles: List[Candle]) -> Optional[float]:
        """Find swing low at index"""
        if idx < lookback:
            return None
        current_low = candles[idx].low
        for i in range(1, lookback + 1):
            if candles[idx - i].low <= current_low:
                return None
        return current_low
    
    def calculate_fib_levels(self, swing_high: float, swing_low: float, fib_mult: float = 0.786) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels"""
        range_size = swing_high - swing_low
        
        return {
            '0.0': swing_low,
            '0.236': swing_low + 0.236 * range_size,
            '0.382': swing_low + 0.382 * range_size,
            '0.5': swing_low + 0.5 * range_size,
            '0.618': swing_low + 0.618 * range_size,
            '0.705': swing_low + 0.705 * range_size,
            '0.786': swing_low + 0.786 * range_size,
            '0.886': swing_low + 0.886 * range_size,
            '1.0': swing_high,
            'SL': swing_low - 0.236 * range_size
        }
    
    def run_backtest(self, candles: List[Candle], lookback: int, fib_mult: float = 0.786) -> List[Trade]:
        """Run backtest with given parameters"""
        trades = []
        i = lookback
        in_trade = False
        
        while i < len(candles):
            candle = candles[i]
            
            # Check for swing high (SHORT setup)
            swing_high = self.find_swing_high(i, lookback, candles)
            if swing_high and not in_trade:
                swing_low = None
                for j in range(i - 1, max(0, i - lookback * 3), -1):
                    low = self.find_swing_low(j, lookback, candles)
                    if low:
                        swing_low = low
                        break
                
                if swing_low and swing_low < swing_high:
                    fib = self.calculate_fib_levels(swing_high, swing_low, fib_mult)
                    entry_price = fib.get(f'{fib_mult:.3f}', fib['0.786'])
                    target = fib['0.0']
                    stop_loss = swing_high + (swing_high - swing_low) * 0.236
                    
                    if candle.low <= entry_price <= candle.high:
                        entry_date = candle.date
                        in_trade = True
                        trade_direction = 'SHORT'
                        trade_entry = entry_price
                        trade_target = target
                        trade_stop = stop_loss
            
            # Check for swing low (LONG setup)
            swing_low = self.find_swing_low(i, lookback, candles)
            if swing_low and not in_trade:
                swing_high = None
                for j in range(i - 1, max(0, i - lookback * 3), -1):
                    high = self.find_swing_high(j, lookback, candles)
                    if high:
                        swing_high = high
                        break
                
                if swing_high and swing_high > swing_low:
                    fib = self.calculate_fib_levels(swing_high, swing_low, fib_mult)
                    entry_price = fib.get(f'{fib_mult:.3f}', fib['0.786'])
                    target = fib['1.0']
                    stop_loss = swing_low - (swing_high - swing_low) * 0.236
                    
                    if candle.low <= entry_price <= candle.high:
                        entry_date = candle.date
                        in_trade = True
                        trade_direction = 'LONG'
                        trade_entry = entry_price
                        trade_target = target
                        trade_stop = stop_loss
            
            # Manage open trade
            if in_trade:
                if trade_direction == 'SHORT':
                    if candle.low <= trade_target:
                        exit_price = trade_target
                        pnl = trade_entry - exit_price
                        trades.append(Trade(
                            entry_date=entry_date, direction='SHORT',
                            entry_price=trade_entry, exit_price=exit_price,
                            exit_date=candle.date, pnl=pnl, won=True
                        ))
                        in_trade = False
                    elif candle.high >= trade_stop:
                        exit_price = trade_stop
                        pnl = trade_entry - exit_price
                        trades.append(Trade(
                            entry_date=entry_date, direction='SHORT',
                            entry_price=trade_entry, exit_price=exit_price,
                            exit_date=candle.date, pnl=pnl, won=False
                        ))
                        in_trade = False
                else:  # LONG
                    if candle.high >= trade_target:
                        exit_price = trade_target
                        pnl = exit_price - trade_entry
                        trades.append(Trade(
                            entry_date=entry_date, direction='LONG',
                            entry_price=trade_entry, exit_price=exit_price,
                            exit_date=candle.date, pnl=pnl, won=True
                        ))
                        in_trade = False
                    elif candle.low <= trade_stop:
                        exit_price = trade_stop
                        pnl = exit_price - trade_entry
                        trades.append(Trade(
                            entry_date=entry_date, direction='LONG',
                            entry_price=trade_entry, exit_price=exit_price,
                            exit_date=candle.date, pnl=pnl, won=False
                        ))
                        in_trade = False
            
            i += 1
        
        return trades
    
    def analyze_trades(self, trades: List[Trade]) -> Dict:
        """Analyze trade results"""
        if not trades:
            return {'error': 'No trades'}
        
        wins = [t for t in trades if t.won]
        losses = [t for t in trades if not t.won]
        
        win_rate = len(wins) / len(trades) * 100
        total_pnl = sum(t.pnl for t in trades)
        avg_pnl = total_pnl / len(trades)
        
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Drawdown
        peak = 0
        max_drawdown = 0
        cumulative = 0
        for t in trades:
            cumulative += t.pnl
            if cumulative > peak:
                peak = cumulative
            drawdown = peak - cumulative
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return {
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown
        }
    
    def walk_forward_split(self, n_folds: int = 5) -> List[Tuple[List[Candle], List[Candle]]]:
        """Split data into walk-forward windows"""
        total = len(self.candles)
        train_pct = 0.6  # 60% training
        test_pct = 0.2   # 20% testing (forward)
        
        splits = []
        step = int(total * 0.2)  # 20% step forward
        
        for fold in range(n_folds):
            train_start = 0
            train_end = int(total * train_pct) + (fold * step)
            test_start = train_end
            test_end = test_start + int(total * test_pct)
            
            if test_end > total:
                test_end = total
            
            if train_end > total:
                break
            
            train_candles = self.candles[train_start:train_end]
            test_candles = self.candles[test_start:test_end]
            
            if len(train_candles) > 100 and len(test_candles) > 50:
                splits.append((train_candles, test_candles))
        
        return splits
    
    def optimize_parameters(self, train_candles: List[Candle]) -> Dict:
        """Find best parameters on training data"""
        lookbacks = [5, 10, 15, 20]
        fib_mults = [0.618, 0.705, 0.786, 0.886]
        
        best_params = None
        best_score = -float('inf')
        all_results = []
        
        for lb, fib in itertools.product(lookbacks, fib_mults):
            trades = self.run_backtest(train_candles, lb, fib)
            metrics = self.analyze_trades(trades)
            
            if 'error' not in metrics:
                # Score = win_rate * profit_factor (balanced metric)
                score = metrics['win_rate'] * metrics['profit_factor']
                all_results.append({
                    'lookback': lb,
                    'fib': fib,
                    'win_rate': metrics['win_rate'],
                    'pnl': metrics['total_pnl'],
                    'pf': metrics['profit_factor'],
                    'score': score
                })
                
                if score > best_score:
                    best_score = score
                    best_params = {'lookback': lb, 'fib': fib}
        
        return {
            'best_params': best_params,
            'all_results': sorted(all_results, key=lambda x: x['score'], reverse=True)
        }
    
    def run_walk_forward(self, n_folds: int = 5):
        """Run complete walk-forward analysis"""
        print(f"\n{'='*80}")
        print(f"🔄 WALK-FORWARD ANALYSIS ({n_folds} folds)")
        print(f"{'='*80}")
        print(f"Data: {len(self.candles)} candles")
        print(f"Training: 60% | Testing: 20% | Step: 20%")
        print(f"{'='*80}")
        
        splits = self.walk_forward_split(n_folds)
        
        print(f"\n✅ Created {len(splits)} walk-forward windows")
        
        # Store results
        fold_results = []
        out_of_sample_results = []
        
        for fold_idx, (train_candles, test_candles) in enumerate(splits, 1):
            print(f"\n{'='*80}")
            print(f"📊 FOLD {fold_idx}/{len(splits)}")
            print(f"{'='*80}")
            print(f"   Training: {len(train_candles)} candles ({train_candles[0].date.date()} to {train_candles[-1].date.date()})")
            print(f"   Testing:  {len(test_candles)} candles ({test_candles[0].date.date()} to {test_candles[-1].date.date()})")
            
            # Optimize on training
            print(f"\n🔧 Optimizing parameters on training data...")
            opt_result = self.optimize_parameters(train_candles)
            best_params = opt_result['best_params']
            
            print(f"   Best Parameters: Lookback={best_params['lookback']}, Fib={best_params['fib']}")
            print(f"   Top 3 Configurations:")
            for i, res in enumerate(opt_result['all_results'][:3], 1):
                print(f"      {i}. LB={res['lookback']}, Fib={res['fib']:.3f} → WR={res['win_rate']:.1f}%, PF={res['pf']:.2f}")
            
            # Test on out-of-sample data
            print(f"\n🧪 Testing on out-of-sample (forward) data...")
            oos_trades = self.run_backtest(test_candles, best_params['lookback'], best_params['fib'])
            oos_metrics = self.analyze_trades(oos_trades)
            
            # Also test fixed params (LB=10, Fib=0.786) for comparison
            fixed_trades = self.run_backtest(test_candles, 10, 0.786)
            fixed_metrics = self.analyze_trades(fixed_trades)
            
            print(f"\n   Out-of-Sample Results (Optimized Params):")
            if 'error' not in oos_metrics:
                print(f"      Trades: {oos_metrics['total_trades']}")
                print(f"      Win Rate: {oos_metrics['win_rate']:.2f}%")
                print(f"      PnL: {oos_metrics['total_pnl']:+.2f} pts")
                print(f"      Profit Factor: {oos_metrics['profit_factor']:.2f}")
                print(f"      Max DD: {oos_metrics['max_drawdown']:.2f} pts")
                
                out_of_sample_results.append({
                    'fold': fold_idx,
                    'params': best_params,
                    'metrics': oos_metrics
                })
            else:
                print(f"      ❌ No trades generated")
                out_of_sample_results.append({
                    'fold': fold_idx,
                    'params': best_params,
                    'metrics': {'error': 'No trades'}
                })
            
            print(f"\n   Out-of-Sample Results (Fixed Params: LB=10, Fib=0.786):")
            if 'error' not in fixed_metrics:
                print(f"      Trades: {fixed_metrics['total_trades']}")
                print(f"      Win Rate: {fixed_metrics['win_rate']:.2f}%")
                print(f"      PnL: {fixed_metrics['total_pnl']:+.2f} pts")
                print(f"      Profit Factor: {fixed_metrics['profit_factor']:.2f}")
            
            fold_results.append({
                'fold': fold_idx,
                'optimized': oos_metrics if 'error' not in oos_metrics else None,
                'fixed': fixed_metrics if 'error' not in fixed_metrics else None
            })
        
        # Aggregate results
        print(f"\n{'='*80}")
        print(f"📈 WALK-FORWARD SUMMARY")
        print(f"{'='*80}")
        
        # Calculate aggregate metrics
        valid_folds = [r for r in out_of_sample_results if 'error' not in r['metrics']]
        
        if valid_folds:
            total_trades = sum(r['metrics']['total_trades'] for r in valid_folds)
            total_wins = sum(r['metrics']['wins'] for r in valid_folds)
            total_pnl = sum(r['metrics']['total_pnl'] for r in valid_folds)
            total_dd = max(r['metrics']['max_drawdown'] for r in valid_folds)
            
            aggregate_wr = total_wins / total_trades * 100 if total_trades > 0 else 0
            
            # Calculate average profit factor
            pfs = [r['metrics']['profit_factor'] for r in valid_folds if r['metrics']['profit_factor'] != float('inf')]
            avg_pf = sum(pfs) / len(pfs) if pfs else 0
            
            print(f"\n📊 AGGREGATE OUT-OF-SAMPLE PERFORMANCE:")
            print(f"   Total Folds: {len(valid_folds)}/{len(out_of_sample_results)}")
            print(f"   Total Trades: {total_trades}")
            print(f"   Aggregate Win Rate: {aggregate_wr:.2f}%")
            print(f"   Total PnL: {total_pnl:+.2f} pts")
            print(f"   Avg Profit Factor: {avg_pf:.2f}")
            print(f"   Max Drawdown: {total_dd:.2f} pts")
            
            # Per-fold breakdown
            print(f"\n📅 PER-FOLD BREAKDOWN:")
            print(f"{'-'*80}")
            print(f"{'Fold':<6} {'Lookback':<10} {'Fib':<8} {'Trades':<8} {'Win Rate':<12} {'PnL':<15} {'Profit Factor':<15}")
            print(f"{'-'*80}")
            for r in out_of_sample_results:
                if 'error' not in r['metrics']:
                    m = r['metrics']
                    p = r['params']
                    print(f"{r['fold']:<6} {p['lookback']:<10} {p['fib']:<8.3f} {m['total_trades']:<8} {m['win_rate']:>8.2f}%    {m['total_pnl']:>+12.2f} pts  {m['profit_factor']:>12.2f}")
            print(f"{'-'*80}")
            
            # Consistency check
            profitable_folds = sum(1 for r in valid_folds if r['metrics']['total_pnl'] > 0)
            print(f"\n✅ CONSISTENCY METRICS:")
            print(f"   Profitable Folds: {profitable_folds}/{len(valid_folds)} ({profitable_folds/len(valid_folds)*100:.1f}%)")
            print(f"   Avg Win Rate: {aggregate_wr:.2f}%")
            print(f"   Strategy Stability: {'✅ STABLE' if aggregate_wr > 60 else '⚠️ VARIABLE' if aggregate_wr > 40 else '❌ UNSTABLE'}")
            
            # Save results
            results = {
                'aggregate': {
                    'total_trades': total_trades,
                    'win_rate': aggregate_wr,
                    'total_pnl': total_pnl,
                    'avg_profit_factor': avg_pf,
                    'max_drawdown': total_dd,
                    'profitable_folds': profitable_folds,
                    'total_folds': len(valid_folds)
                },
                'per_fold': out_of_sample_results
            }
            
            with open('walk_forward_results.json', 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n💾 Results saved to: walk_forward_results.json")
            
            # Final verdict
            print(f"\n{'='*80}")
            print(f"⚖️  WALK-FORWARD VERDICT")
            print(f"{'='*80}")
            
            if aggregate_wr >= 70 and profitable_folds >= len(valid_folds) * 0.8:
                print(f"✅ STRATEGY VALIDATED - Robust across market regimes")
                print(f"   Out-of-sample win rate: {aggregate_wr:.2f}%")
                print(f"   Consistency: {profitable_folds}/{len(valid_folds)} folds profitable")
            elif aggregate_wr >= 55 and profitable_folds >= len(valid_folds) * 0.6:
                print(f"⚠️  STRATEGY VIABLE - Moderate robustness")
                print(f"   Out-of-sample win rate: {aggregate_wr:.2f}%")
                print(f"   Some regime dependency detected")
            else:
                print(f"❌ STRATEGY UNSTABLE - Overfit or regime-dependent")
                print(f"   Out-of-sample win rate: {aggregate_wr:.2f}%")
                print(f"   Poor consistency across folds")
            
            print(f"{'='*80}")
        
        return fold_results


def main():
    print("="*80)
    print("🧪 NIFTY50 LOG-FIB STRATEGY - WALK-FORWARD ANALYSIS")
    print("="*80)
    print()
    print("Testing Parameters:")
    print("  • Timeframe: 5 minutes")
    print("  • Walk-Forward: 5 folds (60% train, 20% test)")
    print("  • Parameter Search:")
    print("    - Lookback: 5, 10, 15, 20 candles")
    print("    - Fib Entry: 0.618, 0.705, 0.786, 0.886")
    print("  • Fixed Comparison: Lookback=10, Fib=0.786")
    print()
    
    # Find Nifty50 data file
    data_dir = Path("zerodha_data")
    data_files = list(data_dir.glob("NIFTY*5minute*.csv"))
    
    if not data_files:
        print("❌ No Nifty50 5-minute data found in zerodha_data/")
        return
    
    data_file = max(data_files, key=lambda f: f.stat().st_mtime)
    
    # Initialize analyzer
    analyzer = WalkForwardAnalyzer(str(data_file))
    
    if not analyzer.load_data():
        return
    
    # Run walk-forward
    analyzer.run_walk_forward(n_folds=5)


if __name__ == "__main__":
    main()
