"""
═══════════════════════════════════════════════════════════════
NIFTY50 LOG-FIB STRATEGY TEST - 30 MINUTE TIMEFRAME
═══════════════════════════════════════════════════════════════

Test the strategy on 30-minute bars with different lookback periods.

Parameters to Test:
- Lookback: 5, 10 candles
- Fib Multiplier: 0.786 (78.6%)
- SL Multiplier: 0.236 (23.6%)
- Timeframe: 30 minutes

Data Source: Zerodha Kite CSV (or Yahoo Finance fallback)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import glob

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False


class Nifty30MinBacktester:
    """Backtest log-fib strategy on 30-minute Nifty50 data"""
    
    def __init__(self, lookback: int = 10, multiplier: float = 0.786, sl_multiplier: float = 0.236):
        self.lookback = lookback
        self.multiplier = multiplier
        self.sl_multiplier = sl_multiplier
        
        self.trades = []
        self.wins = 0
        self.losses = 0
        
    def load_zerodha_csv(self, filepath: str) -> pd.DataFrame:
        """Load data from Zerodha Kite CSV"""
        print(f"📥 Loading Zerodha data: {filepath}")
        
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
        
        return df
    
    def load_yahoo_data(self, days: int = 60) -> pd.DataFrame:
        """Fallback: Load from Yahoo Finance (limited to 60 days for 30m)"""
        print(f"📥 Fetching 30-minute data from Yahoo Finance...")
        
        ticker = yf.Ticker("^NSEI")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        df = ticker.history(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval="30m"
        )
        
        if df.empty:
            print("❌ No data from Yahoo Finance")
            return df
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df = df.dropna()
        
        # Rename to lowercase
        df.columns = df.columns.str.lower()
        
        print(f"✅ Fetched {len(df)} candles")
        print(f"   Range: {df.index[0]} to {df.index[-1]}")
        
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
        print(f"🚀 RUNNING BACKTEST (30-min, Lookback={self.lookback})")
        print("="*80)
        print(f"Strategy: {self.multiplier*100:.1f}% Fib Retracement")
        print(f"Lookback: {self.lookback} candles ({self.lookback * 30 / 60:.1f} hours)")
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
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            timestamp = row.name
            
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
            'profit_factor': abs(wins / losses) if losses > 0 else float('inf')
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
        print(f"\n💰 PnL Analysis:")
        print(f"  Total PnL: {result['total_pnl']:+.2f} points")
        print(f"  Avg PnL/Trade: {result['avg_pnl']:+.2f} points")
        print(f"  Max Drawdown: {result['max_drawdown']:.2f} points")
        print(f"  Max Consecutive Losses: {result['max_consecutive_losses']}")
        print(f"  Profit Factor: {result['profit_factor']:.2f}")
        print("="*80)
        
        if result['trades']:
            print(f"\n📝 All {len(result['trades'])} Trades:")
            print("-" * 80)
            for i, trade in enumerate(result['trades'], 1):
                icon = "✅" if trade['result'] == 'WIN' else "❌"
                ts = trade['timestamp'][:16] if isinstance(trade['timestamp'], str) else str(trade['timestamp'])[:16]
                print(f"{i:3d}. {icon} {trade['type']:<6} | {ts} | Entry: {trade['entry']:.2f} | Exit: {trade['exit']:.2f} | PnL: {trade['pnl']:+.2f}")
            print("-" * 80)


def compare_lookbacks(df: pd.DataFrame) -> Dict:
    """Test multiple lookback values and compare"""
    print("\n" + "="*80)
    print("🔬 COMPARING LOOKBACK PERIODS (30-min Timeframe)")
    print("="*80)
    
    lookbacks = [5, 10]
    results = {}
    
    for lb in lookbacks:
        backtester = Nifty30MinBacktester(lookback=lb)
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
    
    return results


def main():
    print("="*80)
    print("🧪 NIFTY50 LOG-FIB STRATEGY TEST - 30 MINUTE TIMEFRAME")
    print("="*80)
    print()
    print("Testing Parameters:")
    print("  • Timeframe: 30 minutes")
    print("  • Lookback: 5, 10 candles")
    print("  • Fib Entry: 78.6%")
    print("  • Stop Loss: 23.6% beyond swing")
    print()
    
    # Try to load Zerodha CSV first
    zerodha_files = glob.glob("zerodha_data/*.csv")
    
    if not zerodha_files:
        zerodha_files = glob.glob("/home/palbot/Projects/log-fib-scalper/zerodha_data/*.csv")
    
    if zerodha_files:
        print(f"📁 Found Zerodha data files:")
        for i, f in enumerate(zerodha_files, 1):
            print(f"  {i}. {Path(f).name}")
        print()
        
        # Use most recent NIFTY file
        nifty_files = [f for f in zerodha_files if 'NIFTY' in f.upper()]
        if nifty_files:
            data_file = sorted(nifty_files)[-1]  # Most recent
            print(f"✅ Using: {Path(data_file).name}")
            
            backtester = Nifty30MinBacktester(lookback=10)
            df = backtester.load_zerodha_csv(data_file)
            
            if not df.empty:
                # Run comparison
                results = compare_lookbacks(df)
                
                # Save results
                with open("backtest_30min_comparison.json", "w") as f:
                    json.dump({str(k): v for k, v in results.items()}, f, indent=2, default=str)
                
                print(f"\n💾 Results saved to: backtest_30min_comparison.json")
                return
    
    # Fallback to Yahoo Finance
    print("⚠️  No Zerodha CSV found. Using Yahoo Finance fallback...")
    print("   (Limited to 60 days of 30m data)")
    print()
    
    if not HAS_YF:
        print("❌ yfinance not installed. Run: pip install yfinance")
        return
    
    backtester = Nifty30MinBacktester(lookback=10)
    df = backtester.load_yahoo_data(days=60)
    
    if df.empty:
        print("\n❌ Failed to fetch data.")
        print("\n📝 To use Zerodha data:")
        print("   1. Run: python zerodha_data_fetcher.py")
        print("   2. Enter your credentials and 2FA")
        print("   3. Fetch NIFTY 50 with 30minute interval")
        print("   4. Re-run this script")
        return
    
    # Run comparison
    results = compare_lookbacks(df)
    
    # Save results
    with open("backtest_30min_yahoo.json", "w") as f:
        json.dump({str(k): v for k, v in results.items()}, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: backtest_30min_yahoo.json")


if __name__ == "__main__":
    main()
