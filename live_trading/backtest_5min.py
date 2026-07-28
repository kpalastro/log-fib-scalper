"""
═══════════════════════════════════════════════════════════════
NIFTY50 LOG-FIB STRATEGY TEST - 5 MINUTE TIMEFRAME
═══════════════════════════════════════════════════════════════

Test the strategy on 5-minute bars with different lookback periods.
This is the ORIGINAL strategy specification (98.43% win rate claim).

Parameters to Test:
- Lookback: 5, 10 candles
- Fib Multiplier: 0.786 (78.6%)
- SL Multiplier: 0.236 (23.6%)
- Timeframe: 5 minutes

Data Source: Zerodha Kite CSV (60 days, 5-minute)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json
import glob
import sys


class Nifty5MinBacktester:
    """Backtest log-fib strategy on 5-minute Nifty50 data"""
    
    def __init__(self, lookback: int = 10, multiplier: float = 0.786, sl_multiplier: float = 0.236):
        self.lookback = lookback
        self.multiplier = multiplier
        self.sl_multiplier = sl_multiplier
        
        self.trades = []
        self.wins = 0
        self.losses = 0
        
    def load_zerodha_csv(self, filepath: str) -> pd.DataFrame:
        """Load data from Zerodha Kite CSV"""
        print(f"📥 Loading Zerodha 5m data: {filepath}")
        
        df = pd.read_csv(filepath)
        
        # Parse date column
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
        
        # Ensure required columns
        required = ['open', 'high', 'low', 'close', 'volume']
        available = [c for c in required if c in df.columns]
        
        if len(available) < 4:
            print(f"❌ Missing required columns. Found: {df.columns.tolist()}")
            return pd.DataFrame()
        
        df = df[available]
        df = df.dropna()
        
        print(f"✅ Loaded {len(df)} candles")
        print(f"   Range: {df.index[0]} to {df.index[-1]}")
        print(f"   Price: {df['low'].min():.2f} - {df['high'].max():.2f}")
        
        # Calculate trading days
        unique_days = df.index.date.astype('datetime64[D]').astype('datetime64[s]').astype('int64') // 86400
        trading_days = len(set(df.index.date))
        print(f"   Trading Days: {trading_days}")
        print(f"   Avg candles/day: {len(df) / trading_days:.0f}")
        
        return df
    
    def detect_swing_high(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """Detect swing high with given lookback"""
        if idx < self.lookback or idx >= len(df) - self.lookback:
            return None
        
        current_high = df.iloc[idx]['high']
        
        for j in range(idx - self.lookback, idx + self.lookback + 1):
            if j != idx and df.iloc[j]['high'] >= current_high:
                return None
        
        return {
            "idx": idx,
            "high": current_high,
            "low": df.iloc[idx]['low'],
            "time": df.index[idx]
        }
    
    def detect_swing_low(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """Detect swing low with given lookback"""
        if idx < self.lookback or idx >= len(df) - self.lookback:
            return None
        
        current_low = df.iloc[idx]['low']
        
        for j in range(idx - self.lookback, idx + self.lookback + 1):
            if j != idx and df.iloc[j]['low'] <= current_low:
                return None
        
        return {
            "idx": idx,
            "low": current_low,
            "high": df.iloc[idx]['high'],
            "time": df.index[idx]
        }
    
    def run_backtest(self, df: pd.DataFrame, verbose: bool = False) -> Dict:
        """Run backtest on data"""
        print("\n" + "="*80)
        print(f"🚀 RUNNING BACKTEST (5-min, Lookback={self.lookback})")
        print("="*80)
        print(f"Strategy: {self.multiplier*100:.1f}% Fib Retracement")
        print(f"Lookback: {self.lookback} candles ({self.lookback * 5} minutes)")
        print(f"Data points: {len(df)}")
        print("="*80 + "\n")
        
        trades = []
        wins = 0
        losses = 0
        total_pnl = 0.0
        
        in_position = False
        position_type = None
        entry_price = 0.0
        tp = 0.0
        sl = 0.0
        
        last_swing_high = None
        last_swing_low = None
        
        # Track metrics
        peak_pnl = 0.0
        max_drawdown = 0.0
        consecutive_losses = 0
        max_consecutive_losses = 0
        
        # Track daily stats
        daily_trades = {}
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            timestamp = row.name
            current_date = timestamp.date()
            
            swing_high = self.detect_swing_high(df, idx)
            swing_low = self.detect_swing_low(df, idx)
            
            if swing_high:
                last_swing_high = swing_high
                if verbose:
                    print(f"📍 [{timestamp}] Swing High @ {swing_high['high']:.2f}")
            
            if swing_low:
                last_swing_low = swing_low
                if verbose:
                    print(f"📍 [{timestamp}] Swing Low @ {swing_low['low']:.2f}")
            
            # EXIT LOGIC
            if in_position:
                if position_type == 'LONG':
                    if row['high'] >= tp:
                        pnl = tp - entry_price
                        wins += 1
                        total_pnl += pnl
                        trades.append({
                            'type': 'LONG', 'entry': entry_price, 'exit': tp,
                            'pnl': pnl, 'result': 'WIN', 'timestamp': str(timestamp)
                        })
                        
                        # Track daily
                        if current_date not in daily_trades:
                            daily_trades[current_date] = {'wins': 0, 'losses': 0, 'pnl': 0}
                        daily_trades[current_date]['wins'] += 1
                        daily_trades[current_date]['pnl'] += pnl
                        
                        in_position = False
                        position_type = None
                        consecutive_losses = 0
                    
                    elif row['low'] <= sl:
                        pnl = sl - entry_price
                        losses += 1
                        total_pnl += pnl
                        trades.append({
                            'type': 'LONG', 'entry': entry_price, 'exit': sl,
                            'pnl': pnl, 'result': 'LOSS', 'timestamp': str(timestamp)
                        })
                        
                        if current_date not in daily_trades:
                            daily_trades[current_date] = {'wins': 0, 'losses': 0, 'pnl': 0}
                        daily_trades[current_date]['losses'] += 1
                        daily_trades[current_date]['pnl'] += pnl
                        
                        in_position = False
                        position_type = None
                        consecutive_losses += 1
                    
                    if total_pnl > peak_pnl:
                        peak_pnl = total_pnl
                    drawdown = peak_pnl - total_pnl
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown
                
                elif position_type == 'SHORT':
                    if row['low'] <= tp:
                        pnl = entry_price - tp
                        wins += 1
                        total_pnl += pnl
                        trades.append({
                            'type': 'SHORT', 'entry': entry_price, 'exit': tp,
                            'pnl': pnl, 'result': 'WIN', 'timestamp': str(timestamp)
                        })
                        
                        if current_date not in daily_trades:
                            daily_trades[current_date] = {'wins': 0, 'losses': 0, 'pnl': 0}
                        daily_trades[current_date]['wins'] += 1
                        daily_trades[current_date]['pnl'] += pnl
                        
                        in_position = False
                        position_type = None
                        consecutive_losses = 0
                    
                    elif row['high'] >= sl:
                        pnl = entry_price - sl
                        losses += 1
                        total_pnl += pnl
                        trades.append({
                            'type': 'SHORT', 'entry': entry_price, 'exit': sl,
                            'pnl': pnl, 'result': 'LOSS', 'timestamp': str(timestamp)
                        })
                        
                        if current_date not in daily_trades:
                            daily_trades[current_date] = {'wins': 0, 'losses': 0, 'pnl': 0}
                        daily_trades[current_date]['losses'] += 1
                        daily_trades[current_date]['pnl'] += pnl
                        
                        in_position = False
                        position_type = None
                        consecutive_losses += 1
                    
                    if total_pnl > peak_pnl:
                        peak_pnl = total_pnl
                    drawdown = peak_pnl - total_pnl
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown
            
            # ENTRY LOGIC
            if not in_position:
                # LONG: swing high → swing low → 78.6% retracement up
                if last_swing_high and last_swing_low:
                    if last_swing_low['idx'] > last_swing_high['idx']:
                        high_price = last_swing_high['high']
                        low_price = last_swing_low['low']
                        range_size = high_price - low_price
                        
                        if range_size > 0:
                            fib_entry = low_price + (range_size * self.multiplier)
                            tp_price = high_price
                            sl_price = low_price - (range_size * self.sl_multiplier)
                            
                            if row['low'] <= fib_entry <= row['high']:
                                in_position = True
                                position_type = 'LONG'
                                entry_price = fib_entry
                                tp = tp_price
                                sl = sl_price
                                if verbose:
                                    print(f"📈 [{timestamp}] LONG @ {entry_price:.2f} | TP: {tp:.2f} | SL: {sl:.2f}")
                
                # SHORT: swing low → swing high → 78.6% retracement up, then short
                if last_swing_low and last_swing_high:
                    if last_swing_high['idx'] > last_swing_low['idx']:
                        low_price = last_swing_low['low']
                        high_price = last_swing_high['high']
                        range_size = high_price - low_price
                        
                        if range_size > 0:
                            fib_entry = low_price + (range_size * self.multiplier)
                            tp_price = low_price
                            sl_price = high_price + (range_size * self.sl_multiplier)
                            
                            if row['low'] <= fib_entry <= row['high']:
                                in_position = True
                                position_type = 'SHORT'
                                entry_price = fib_entry
                                tp = tp_price
                                sl = sl_price
                                if verbose:
                                    print(f"📉 [{timestamp}] SHORT @ {entry_price:.2f} | TP: {tp:.2f} | SL: {sl:.2f}")
        
        if consecutive_losses > max_consecutive_losses:
            max_consecutive_losses = consecutive_losses
        
        total_trades = wins + losses
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        # Calculate win streak
        best_win_streak = 0
        current_win_streak = 0
        for trade in trades:
            if trade['result'] == 'WIN':
                current_win_streak += 1
                if current_win_streak > best_win_streak:
                    best_win_streak = current_win_streak
            else:
                current_win_streak = 0
        
        return {
            'lookback': self.lookback,
            'trades': trades,
            'wins': wins,
            'losses': losses,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'max_drawdown': max_drawdown,
            'max_consecutive_losses': max_consecutive_losses,
            'best_win_streak': best_win_streak,
            'profit_factor': abs(wins / losses) if losses > 0 else float('inf'),
            'daily_stats': daily_trades
        }
    
    def print_results(self, result: Dict):
        """Print backtest results"""
        print("\n" + "="*80)
        print(f"📊 RESULTS (Lookback={result['lookback']})")
        print("="*80)
        print(f"Total Trades: {result['total_trades']}")
        print(f"  Wins: {result['wins']} ✅")
        print(f"  Losses: {result['losses']} ❌")
        print(f"  Win Rate: {result['win_rate']:.2f}%")
        print(f"  Best Win Streak: {result['best_win_streak']}")
        print(f"\n💰 PnL Analysis:")
        print(f"  Total PnL: {result['total_pnl']:+.2f} points")
        print(f"  Avg PnL/Trade: {result['avg_pnl']:+.2f} points")
        print(f"  Max Drawdown: {result['max_drawdown']:.2f} points")
        print(f"  Max Consecutive Losses: {result['max_consecutive_losses']}")
        print(f"  Profit Factor: {result['profit_factor']:.2f}")
        print("="*80)
        
        # Daily breakdown
        if result['daily_stats']:
            print(f"\n📅 Daily Breakdown:")
            print("-" * 80)
            print(f"{'Date':<12} {'Trades':<8} {'Wins':<6} {'Losses':<8} {'PnL':<12} {'Status'}")
            print("-" * 80)
            
            for date, stats in sorted(result['daily_stats'].items()):
                total_daily = stats['wins'] + stats['losses']
                status = "✅ Profit" if stats['pnl'] > 0 else "❌ Loss" if stats['pnl'] < 0 else "⚖️  Break-even"
                print(f"{str(date):<12} {total_daily:<8} {stats['wins']:<6} {stats['losses']:<8} {stats['pnl']:>+10.2f} pts  {status}")
            print("-" * 80)
            
            # Profitable days
            profitable_days = sum(1 for s in result['daily_stats'].values() if s['pnl'] > 0)
            losing_days = sum(1 for s in result['daily_stats'].values() if s['pnl'] < 0)
            total_days = len(result['daily_stats'])
            print(f"\nProfitable Days: {profitable_days}/{total_days} ({profitable_days/total_days*100:.1f}%)")
        
        # Show sample trades
        if result['trades']:
            print(f"\n📝 Sample Trades (first 10 and last 10):")
            print("-" * 80)
            for i, trade in enumerate(result['trades'][:10], 1):
                icon = "✅" if trade['result'] == 'WIN' else "❌"
                ts = trade['timestamp'][:16]
                print(f"{i:3d}. {icon} {trade['type']:<6} | {ts} | Entry: {trade['entry']:.0f} | Exit: {trade['exit']:.0f} | PnL: {trade['pnl']:+.0f}")
            
            if len(result['trades']) > 20:
                print(f"     ... ({len(result['trades']) - 20} more trades) ...")
                for i, trade in enumerate(result['trades'][-10:], len(result['trades'])-9):
                    icon = "✅" if trade['result'] == 'WIN' else "❌"
                    ts = trade['timestamp'][:16]
                    print(f"{i:3d}. {icon} {trade['type']:<6} | {ts} | Entry: {trade['entry']:.0f} | Exit: {trade['exit']:.0f} | PnL: {trade['pnl']:+.0f}")
            print("-" * 80)


def compare_lookbacks(df: pd.DataFrame) -> Dict:
    """Test multiple lookback values and compare"""
    print("\n" + "="*80)
    print("🔬 COMPARING LOOKBACK PERIODS (5-min Timeframe)")
    print("="*80)
    
    lookbacks = [5, 10]
    results = {}
    
    for lb in lookbacks:
        backtester = Nifty5MinBacktester(lookback=lb)
        result = backtester.run_backtest(df, verbose=False)
        results[lb] = result
        backtester.print_results(result)
    
    # Comparison summary
    print("\n" + "="*80)
    print("📊 COMPARISON SUMMARY")
    print("="*80)
    print(f"{'Lookback':<12} {'Trades':<10} {'Win Rate':<12} {'Total PnL':<15} {'Avg PnL':<12} {'Profit Factor':<15}")
    print("-" * 80)
    
    for lb in lookbacks:
        r = results[lb]
        print(f"{lb:<12} {r['total_trades']:<10} {r['win_rate']:>8.2f}%    {r['total_pnl']:>+12.2f} pts  {r['avg_pnl']:>+10.2f} pts  {r['profit_factor']:>12.2f}")
    
    print("-" * 80)
    
    # Find best
    best_by_winrate = max(lookbacks, key=lambda lb: results[lb]['win_rate'])
    best_by_pnl = max(lookbacks, key=lambda lb: results[lb]['total_pnl'])
    best_by_pf = max(lookbacks, key=lambda lb: results[lb]['profit_factor'])
    
    print(f"\n🏆 Best by Win Rate: Lookback {best_by_winrate} ({results[best_by_winrate]['win_rate']:.2f}%)")
    print(f"🏆 Best by Total PnL: Lookback {best_by_pnl} ({results[best_by_pnl]['total_pnl']:+.2f} pts)")
    print(f"🏆 Best by Profit Factor: Lookback {best_by_pf} ({results[best_by_pf]['profit_factor']:.2f})")
    print("="*80)
    
    # Honesty check against 98.43% claim
    print(f"\n🎯 VS 98.43% TARGET:")
    for lb in lookbacks:
        wr = results[lb]['win_rate']
        gap = 98.43 - wr
        if wr >= 98.43:
            print(f"  Lookback {lb}: ⭐ EXCEEDS TARGET ({wr:.2f}% vs 98.43%)")
        elif wr >= 95:
            print(f"  Lookback {lb}: ✅ VERY CLOSE ({wr:.2f}%, gap: {gap:.2f}%)")
        elif wr >= 90:
            print(f"  Lookback {lb}: ⚠️  GOOD ({wr:.2f}%, gap: {gap:.2f}%)")
        else:
            print(f"  Lookback {lb}: ❌ BELOW TARGET ({wr:.2f}%, gap: {gap:.2f}%)")
    
    print("="*80)
    
    return results


def main():
    print("="*80)
    print("🧪 NIFTY50 LOG-FIB STRATEGY TEST - 5 MINUTE TIMEFRAME")
    print("="*80)
    print()
    print("Testing Parameters:")
    print("  • Timeframe: 5 minutes (ORIGINAL SPEC)")
    print("  • Lookback: 5, 10 candles")
    print("  • Fib Entry: 78.6%")
    print("  • Stop Loss: 23.6% beyond swing")
    print("  • Target Win Rate: 98.43%")
    print()
    
    # Find Zerodha 5m CSV
    zerodha_files = glob.glob("zerodha_data/*5minute*.csv")
    
    if not zerodha_files:
        zerodha_files = glob.glob("/home/palbot/Projects/log-fib-scalper/zerodha_data/*5minute*.csv")
    
    if not zerodha_files:
        print("❌ No 5-minute Zerodha data found.")
        print("\n📝 To fetch 5m data:")
        print("   python zerodha_data_fetcher.py --interval 5minute --days 60")
        return
    
    # Use most recent NIFTY file
    nifty_files = [f for f in zerodha_files if 'NIFTY' in f.upper()]
    if not nifty_files:
        print("❌ No NIFTY 5m data found.")
        return
    
    data_file = sorted(nifty_files)[-1]
    print(f"📁 Using: {Path(data_file).name}")
    
    backtester = Nifty5MinBacktester(lookback=10)
    df = backtester.load_zerodha_csv(data_file)
    
    if df.empty:
        print("\n❌ Failed to load data.")
        return
    
    # Run comparison
    results = compare_lookbacks(df)
    
    # Save results
    with open("backtest_5min_comparison.json", "w") as f:
        # Convert for JSON serialization
        json_results = {}
        for k, v in results.items():
            v_copy = v.copy()
            v_copy['daily_stats'] = {str(dk): dv for dk, dv in v['daily_stats'].items()}
            json_results[str(k)] = v_copy
        json.dump(json_results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: backtest_5min_comparison.json")
    
    # Final verdict
    print("\n" + "="*80)
    print("⚖️  FINAL VERDICT")
    print("="*80)
    
    best_wr = max(results[5]['win_rate'], results[10]['win_rate'])
    best_lb = 5 if results[5]['win_rate'] > results[10]['win_rate'] else 10
    
    if best_wr >= 98.43:
        print(f"✅ STRATEGY VALIDATED - Lookback {best_lb} achieves {best_wr:.2f}% (exceeds 98.43% target)")
        print(f"   Ready for LIVE TRADING")
    elif best_wr >= 95:
        print(f"✅ STRONG PERFORMANCE - Lookback {best_lb} at {best_wr:.2f}%")
        print(f"   Close to target, viable for live trading")
    elif best_wr >= 85:
        print(f"⚠️  GOOD BUT NOT EXCEPTIONAL - Lookback {best_lb} at {best_wr:.2f}%")
        print(f"   Profitable but below 98.43% claim")
    else:
        print(f"❌ BELOW EXPECTATIONS - Lookback {best_lb} at {best_wr:.2f}%")
        print(f"   Strategy needs revision or 98.43% claim was from different data")
    
    print("="*80)


if __name__ == "__main__":
    main()
