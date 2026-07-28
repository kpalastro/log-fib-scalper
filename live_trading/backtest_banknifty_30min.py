"""
═══════════════════════════════════════════════════════════════
BANKNIFTY LOG-FIB STRATEGY TEST - 30 MINUTE TIMEFRAME
═══════════════════════════════════════════════════════════════

Tests the 78.6% Fibonacci retracement strategy on BankNifty futures data.
Compares lookback periods (5 vs 10 candles) to find optimal parameters.

Strategy Logic:
1. Detect swing highs/lows over lookback period
2. Wait for 78.6% retracement of the swing
3. Enter at 78.6% Fib level
4. Target: 100% (swing high/low)
5. Stop Loss: -23.6% beyond swing point

Data: BankNifty Futures (continuous/nearest expiry)
Timeframe: 30 minutes
Source: Zerodha Kite historical data
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


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
    direction: str  # 'LONG' or 'SHORT'
    entry_price: float
    exit_price: float
    exit_date: datetime
    pnl: float
    won: bool


class BankNiftyBacktester:
    """Backtester for BankNifty Log-Fib strategy"""
    
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.candles: List[Candle] = []
        self.trades: List[Trade] = []
        
    def load_data(self) -> bool:
        """Load BankNifty data from CSV"""
        print(f"📁 Using: {self.data_file}")
        print(f"📥 Loading Zerodha 30m data: {self.data_file}")
        
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
                
                # Calculate trading days
                dates = set(c.date.date() for c in self.candles)
                print(f"   Trading Days: {len(dates)}")
                print(f"   Avg candles/day: {len(self.candles) / len(dates):.1f}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False
    
    def find_swing_high(self, idx: int, lookback: int) -> Optional[float]:
        """Find swing high at index (higher than all lookback candles)"""
        if idx < lookback:
            return None
        
        current_high = self.candles[idx].high
        for i in range(1, lookback + 1):
            if self.candles[idx - i].high >= current_high:
                return None
        return current_high
    
    def find_swing_low(self, idx: int, lookback: int) -> Optional[float]:
        """Find swing low at index (lower than all lookback candles)"""
        if idx < lookback:
            return None
        
        current_low = self.candles[idx].low
        for i in range(1, lookback + 1):
            if self.candles[idx - i].low <= current_low:
                return None
        return current_low
    
    def calculate_fib_levels(self, swing_high: float, swing_low: float) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels"""
        range_size = swing_high - swing_low
        
        return {
            '0.0': swing_low,
            '0.236': swing_low + 0.236 * range_size,
            '0.382': swing_low + 0.382 * range_size,
            '0.5': swing_low + 0.5 * range_size,
            '0.618': swing_low + 0.618 * range_size,
            '0.705': swing_low + 0.705 * range_size,
            '0.786': swing_low + 0.786 * range_size,  # Entry
            '0.886': swing_low + 0.886 * range_size,
            '1.0': swing_high,  # Target
            'SL': swing_low - 0.236 * range_size  # Stop loss (23.6% beyond)
        }
    
    def run_backtest(self, lookback: int) -> List[Trade]:
        """Run backtest with given lookback period"""
        trades = []
        i = lookback
        in_trade = False
        
        while i < len(self.candles):
            candle = self.candles[i]
            
            # Check for swing high (potential SHORT setup)
            swing_high = self.find_swing_high(i, lookback)
            if swing_high and not in_trade:
                # Find the swing low that preceded this high
                swing_low = None
                for j in range(i - 1, max(0, i - lookback * 3), -1):
                    low = self.find_swing_low(j, lookback)
                    if low:
                        swing_low = low
                        break
                
                if swing_low and swing_low < swing_high:
                    # SHORT setup: price made a high, we short the retracement
                    fib = self.calculate_fib_levels(swing_high, swing_low)
                    entry_price = fib['0.786']
                    target = fib['0.0']  # Swing LOW (price continues down)
                    stop_loss = swing_high + (swing_high - swing_low) * 0.236  # 23.6% ABOVE swing high
                    
                    # Check if price retraces to 78.6%
                    if candle.low <= entry_price <= candle.high:
                        # Enter SHORT at 78.6%
                        entry_date = candle.date
                        in_trade = True
                        trade_direction = 'SHORT'
                        trade_entry = entry_price
                        trade_target = target
                        trade_stop = stop_loss
                        trade_swing = swing_low
            
            # Check for swing low (potential LONG setup)
            swing_low = self.find_swing_low(i, lookback)
            if swing_low and not in_trade:
                # Find the swing high that preceded this low
                swing_high = None
                for j in range(i - 1, max(0, i - lookback * 3), -1):
                    high = self.find_swing_high(j, lookback)
                    if high:
                        swing_high = high
                        break
                
                if swing_high and swing_high > swing_low:
                    # LONG setup: price made a low, we long the retracement
                    fib = self.calculate_fib_levels(swing_high, swing_low)
                    entry_price = fib['0.786']
                    target = fib['1.0']  # Swing HIGH (price continues up)
                    stop_loss = swing_low - (swing_high - swing_low) * 0.236  # 23.6% BELOW swing low
                    
                    # Check if price retraces to 78.6%
                    if candle.low <= entry_price <= candle.high:
                        # Enter LONG at 78.6%
                        entry_date = candle.date
                        in_trade = True
                        trade_direction = 'LONG'
                        trade_entry = entry_price
                        trade_target = target
                        trade_stop = stop_loss
                        trade_swing = swing_high
            
            # Manage open trade
            if in_trade:
                if trade_direction == 'SHORT':
                    # SHORT: Profit when price goes down
                    if candle.low <= trade_target:
                        # Hit target
                        exit_price = trade_target
                        pnl = trade_entry - exit_price
                        trades.append(Trade(
                            entry_date=entry_date,
                            direction='SHORT',
                            entry_price=trade_entry,
                            exit_price=exit_price,
                            exit_date=candle.date,
                            pnl=pnl,
                            won=True
                        ))
                        in_trade = False
                    elif candle.high >= trade_stop:
                        # Hit stop loss
                        exit_price = trade_stop
                        pnl = trade_entry - exit_price
                        trades.append(Trade(
                            entry_date=entry_date,
                            direction='SHORT',
                            entry_price=trade_entry,
                            exit_price=exit_price,
                            exit_date=candle.date,
                            pnl=pnl,
                            won=False
                        ))
                        in_trade = False
                else:  # LONG
                    # LONG: Profit when price goes up
                    if candle.high >= trade_target:
                        # Hit target
                        exit_price = trade_target
                        pnl = exit_price - trade_entry
                        trades.append(Trade(
                            entry_date=entry_date,
                            direction='LONG',
                            entry_price=trade_entry,
                            exit_price=exit_price,
                            exit_date=candle.date,
                            pnl=pnl,
                            won=True
                        ))
                        in_trade = False
                    elif candle.low <= trade_stop:
                        # Hit stop loss
                        exit_price = trade_stop
                        pnl = exit_price - trade_entry
                        trades.append(Trade(
                            entry_date=entry_date,
                            direction='LONG',
                            entry_price=trade_entry,
                            exit_price=exit_price,
                            exit_date=candle.date,
                            pnl=pnl,
                            won=False
                        ))
                        in_trade = False
            
            i += 1
        
        return trades
    
    def analyze_results(self, trades: List[Trade], lookback: int) -> Dict:
        """Analyze backtest results"""
        if not trades:
            return {'error': 'No trades generated'}
        
        wins = [t for t in trades if t.won]
        losses = [t for t in trades if not t.won]
        
        win_rate = len(wins) / len(trades) * 100
        total_pnl = sum(t.pnl for t in trades)
        avg_pnl = total_pnl / len(trades)
        
        # Profit factor
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
        
        # Win/loss streaks
        best_win_streak = 0
        max_loss_streak = 0
        current_win_streak = 0
        current_loss_streak = 0
        for t in trades:
            if t.won:
                current_win_streak += 1
                current_loss_streak = 0
                best_win_streak = max(best_win_streak, current_win_streak)
            else:
                current_loss_streak += 1
                current_win_streak = 0
                max_loss_streak = max(max_loss_streak, current_loss_streak)
        
        # Daily breakdown
        daily_results = {}
        for t in trades:
            date = t.exit_date.date()
            if date not in daily_results:
                daily_results[date] = {'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0}
            daily_results[date]['trades'] += 1
            if t.won:
                daily_results[date]['wins'] += 1
            else:
                daily_results[date]['losses'] += 1
            daily_results[date]['pnl'] += t.pnl
        
        profitable_days = sum(1 for d in daily_results.values() if d['pnl'] > 0)
        
        return {
            'lookback': lookback,
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'best_win_streak': best_win_streak,
            'max_loss_streak': max_loss_streak,
            'profitable_days': profitable_days,
            'total_days': len(daily_results),
            'daily_results': daily_results,
            'sample_trades': trades[:10] + trades[-10:] if len(trades) > 20 else trades
        }
    
    def print_results(self, results: Dict, lookback: int):
        """Print formatted results"""
        print(f"\n{'='*80}")
        print(f"📊 RESULTS (Lookback={lookback})")
        print(f"{'='*80}")
        print(f"Total Trades: {results['total_trades']}")
        print(f"  Wins: {results['wins']} ✅")
        print(f"  Losses: {results['losses']} ❌")
        print(f"  Win Rate: {results['win_rate']:.2f}%")
        print(f"  Best Win Streak: {results['best_win_streak']}")
        print()
        print(f"💰 PnL Analysis:")
        print(f"  Total PnL: {results['total_pnl']:+.2f} points")
        print(f"  Avg PnL/Trade: {results['avg_pnl']:+.2f} points")
        print(f"  Max Drawdown: {results['max_drawdown']:.2f} points")
        print(f"  Max Consecutive Losses: {results['max_loss_streak']}")
        print(f"  Profit Factor: {results['profit_factor']:.2f}")
        print(f"{'='*80}")
        
        # Daily breakdown
        print(f"\n📅 Daily Breakdown:")
        print(f"{'-'*80}")
        print(f"{'Date':<12} {'Trades':<8} {'Wins':<6} {'Losses':<8} {'PnL':<15} {'Status'}")
        print(f"{'-'*80}")
        
        for date in sorted(results['daily_results'].keys()):
            d = results['daily_results'][date]
            status = "✅ Profit" if d['pnl'] > 0 else "❌ Loss"
            print(f"{str(date):<12} {d['trades']:<8} {d['wins']:<6} {d['losses']:<8} {d['pnl']:+10.2f} pts  {status}")
        print(f"{'-'*80}")
        
        profitable_pct = results['profitable_days'] / results['total_days'] * 100
        print(f"\nProfitable Days: {results['profitable_days']}/{results['total_days']} ({profitable_pct:.1f}%)")
        
        # Sample trades
        print(f"\n📝 Sample Trades (first 10 and last 10):")
        print(f"{'-'*80}")
        for idx, t in enumerate(results['sample_trades'], 1):
            if idx <= 10 or idx > len(results['sample_trades']) - 10:
                won = "✅" if t.won else "❌"
                print(f"  {idx:2d}. {won} {t.direction:<6} | {t.entry_date.strftime('%Y-%m-%d %H:%M')} | Entry: {t.entry_price:.0f} | Exit: {t.exit_price:.0f} | PnL: {t.pnl:+.0f}")
            elif idx == 11:
                print(f"     ... ({len(results['sample_trades']) - 20} more trades) ...")
        print(f"{'-'*80}")


def main():
    print("="*80)
    print("🧪 BANKNIFTY LOG-FIB STRATEGY TEST - 30 MINUTE TIMEFRAME")
    print("="*80)
    print()
    print("Testing Parameters:")
    print("  • Timeframe: 30 minutes")
    print("  • Lookback: 5, 10 candles")
    print("  • Fib Entry: 78.6%")
    print("  • Stop Loss: 23.6% beyond swing")
    print("  • Target Win Rate: 98.43%")
    print()
    
    # Find BankNifty data file
    data_dir = Path("zerodha_data")
    data_files = list(data_dir.glob("BANKNIFTY*30minute*.csv"))
    
    if not data_files:
        print("❌ No BankNifty 30-minute data found in zerodha_data/")
        print("   Run: python zerodha_data_fetcher.py --symbol BANKNIFTY --interval 30minute")
        return
    
    # Use most recent file
    data_file = max(data_files, key=lambda f: f.stat().st_mtime)
    
    # Initialize backtester
    backtester = BankNiftyBacktester(str(data_file))
    
    if not backtester.load_data():
        return
    
    print()
    print("="*80)
    print("🔬 COMPARING LOOKBACK PERIODS (30-min Timeframe)")
    print("="*80)
    
    # Run backtests
    all_results = {}
    for lookback in [5, 10]:
        print(f"\n{'='*80}")
        print(f"🚀 RUNNING BACKTEST (30-min, Lookback={lookback})")
        print(f"{'='*80}")
        print(f"Strategy: 78.6% Fib Retracement")
        print(f"Lookback: {lookback} candles ({lookback * 30} minutes)")
        print(f"Data points: {len(backtester.candles)}")
        print(f"{'='*80}")
        print()
        
        trades = backtester.run_backtest(lookback)
        results = backtester.analyze_results(trades, lookback)
        backtester.print_results(results, lookback)
        all_results[lookback] = results
    
    # Comparison summary
    print(f"\n{'='*80}")
    print(f"📊 COMPARISON SUMMARY")
    print(f"{'='*80}")
    print(f"{'Lookback':<10} {'Trades':<10} {'Win Rate':<12} {'Total PnL':<15} {'Avg PnL':<12} {'Profit Factor':<15}")
    print(f"{'-'*80}")
    for lb in [5, 10]:
        r = all_results[lb]
        print(f"{lb:<10} {r['total_trades']:<10} {r['win_rate']:>8.2f}%    {r['total_pnl']:>+12.2f} pts  {r['avg_pnl']:>+8.2f} pts  {r['profit_factor']:>12.2f}")
    print(f"{'-'*80}")
    
    # Determine winner
    best_wr = max(all_results.keys(), key=lambda lb: all_results[lb]['win_rate'])
    best_pnl = max(all_results.keys(), key=lambda lb: all_results[lb]['total_pnl'])
    best_pf = max(all_results.keys(), key=lambda lb: all_results[lb]['profit_factor'])
    
    print(f"\n🏆 Best by Win Rate: Lookback {best_wr} ({all_results[best_wr]['win_rate']:.2f}%)")
    print(f"🏆 Best by Total PnL: Lookback {best_pnl} ({all_results[best_pnl]['total_pnl']:+.2f} pts)")
    print(f"🏆 Best by Profit Factor: Lookback {best_pf} ({all_results[best_pf]['profit_factor']:.2f})")
    print(f"{'='*80}")
    
    # vs target
    print(f"\n🎯 VS 98.43% TARGET:")
    for lb in [5, 10]:
        r = all_results[lb]
        gap = 98.43 - r['win_rate']
        status = "✅ AT/ABOVE" if r['win_rate'] >= 98.43 else "❌ BELOW"
        print(f"  Lookback {lb}: {status} TARGET ({r['win_rate']:.2f}%, gap: {gap:.2f}%)")
    print(f"{'='*80}")
    
    # Save results
    output_file = "backtest_banknifty_30min_comparison.json"
    save_results = {}
    for lb in [5, 10]:
        r = all_results[lb]
        save_results[lb] = {
            'total_trades': r['total_trades'],
            'win_rate': r['win_rate'],
            'total_pnl': r['total_pnl'],
            'avg_pnl': r['avg_pnl'],
            'profit_factor': r['profit_factor'],
            'max_drawdown': r['max_drawdown']
        }
    
    with open(output_file, 'w') as f:
        json.dump(save_results, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")
    
    # Final verdict
    print(f"\n{'='*80}")
    print(f"⚖️  FINAL VERDICT")
    print(f"{'='*80}")
    best = max(all_results.keys(), key=lambda lb: all_results[lb]['win_rate'])
    if all_results[best]['win_rate'] >= 98.43:
        print(f"✅ TARGET ACHIEVED - Lookback {best} at {all_results[best]['win_rate']:.2f}%")
    else:
        print(f"❌ BELOW EXPECTATIONS - Lookback {best} at {all_results[best]['win_rate']:.2f}%")
        print(f"   Strategy needs revision or 98.43% claim was from different data")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
