"""
═══════════════════════════════════════════════════════════════
NIFTY50 STRATEGY BACKTEST - YAHOO FINANCE DATA
═══════════════════════════════════════════════════════════════

Backtest the log-fib scalper strategy on Nifty50 using historical 
data from Yahoo Finance (free, no API limits).

Strategy: 78.6% Fibonacci retracement with 10-candle lookback
Expected Win Rate: 98.43%
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
from collections import deque
import json


class NiftyBacktester:
    def __init__(self, config: Dict = None):
        """
        Initialize backtester
        
        config: {
            "lookback": 10,          # Candle lookback for swing detection
            "multiplier": 0.786,     # 78.6% Fib retracement
            "sl_multiplier": 0.236,  # 23.6% stop loss beyond swing
            "instrument": "^NSEI"    # Nifty50 Yahoo Finance symbol
        }
        """
        self.config = config or {
            "lookback": 10,
            "multiplier": 0.786,
            "sl_multiplier": 0.236,
            "instrument": "^NSEI"
        }
        self.lookback = self.config["lookback"]
        self.multiplier = self.config["multiplier"]
        self.sl_multiplier = self.config["sl_multiplier"]
        
        # Results tracking
        self.trades = []
        self.total_pnl = 0.0
        self.wins = 0
        self.losses = 0
        self.win_rate = 0.0
        
    def fetch_historical_data(self, days: int = 30, interval: str = "5m") -> pd.DataFrame:
        """
        Fetch historical data from Yahoo Finance
        
        days: Number of days to fetch (max 60 for 5m interval)
        interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        """
        print(f"📥 Fetching {days} days of {interval} data for Nifty50...")
        
        ticker = yf.Ticker(self.config["instrument"])
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Download data (new yfinance API)
        df = ticker.history(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval=interval
        )
        
        if df.empty:
            print("❌ No data fetched. Yahoo Finance may have limits on intraday data.")
            print("   Try using interval='1d' for daily data instead.")
            return df
        
        # Clean data - handle multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        
        # Keep only OHLCV columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        available_cols = [c for c in required_cols if c in df.columns]
        df = df[available_cols]
        
        # Drop any rows with NaN
        df = df.dropna()
        
        print(f"✅ Fetched {len(df)} candles")
        print(f"   Date range: {df.index[0].strftime('%Y-%m-%d %H:%M')} to {df.index[-1].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Price range: {df['Low'].min():.2f} - {df['High'].max():.2f}")
        
        return df
    
    def detect_swing_high(self, df: pd.DataFrame, idx: int) -> bool:
        """Check if index is a swing high"""
        lookback = self.lookback
        
        if idx < lookback or idx >= len(df) - lookback:
            return False
        
        current_high = df.iloc[idx]['High']
        
        for j in range(idx - lookback, idx + lookback + 1):
            if j != idx and df.iloc[j]['High'] >= current_high:
                return False
        
        return True
    
    def detect_swing_low(self, df: pd.DataFrame, idx: int) -> bool:
        """Check if index is a swing low"""
        lookback = self.lookback
        
        if idx < lookback or idx >= len(df) - lookback:
            return False
        
        current_low = df.iloc[idx]['Low']
        
        for j in range(idx - lookback, idx + lookback + 1):
            if j != idx and df.iloc[j]['Low'] <= current_low:
                return False
        
        return True
    
    def run_backtest(self, df: pd.DataFrame, verbose: bool = False):
        """
        Run backtest on historical data
        
        Strategy Logic:
        1. Detect swing high/low with 10-candle lookback
        2. Calculate 78.6% retracement level
        3. Enter when price touches 78.6% level
        4. TP at 100% (swing point), SL at -23.6% beyond swing
        """
        print("\n" + "="*80)
        print("🚀 RUNNING BACKTEST")
        print("="*80)
        print(f"Strategy: {self.multiplier*100:.1f}% Fib Retracement")
        print(f"Lookback: {self.lookback} candles")
        print(f"Data points: {len(df)}")
        print("="*80 + "\n")
        
        in_position = False
        position_type = None  # 'LONG' or 'SHORT'
        entry_price = 0.0
        tp = 0.0
        sl = 0.0
        last_swing_high = None
        last_swing_low = None
        swing_high_price = 0.0
        swing_low_price = 0.0
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            current_price = row['Close']
            timestamp = row.name
            
            # Detect new swings
            if self.detect_swing_high(df, idx):
                swing_high_price = row['High']
                last_swing_high = idx
                if verbose:
                    print(f"📍 [{timestamp}] Swing High detected @ {swing_high_price:.2f}")
            
            if self.detect_swing_low(df, idx):
                swing_low_price = row['Low']
                last_swing_low = idx
                if verbose:
                    print(f"📍 [{timestamp}] Swing Low detected @ {swing_low_price:.2f}")
            
            # Exit conditions (if in position)
            if in_position:
                if position_type == 'LONG':
                    # Check TP hit (price rises to TP)
                    if row['High'] >= tp:
                        pnl = tp - entry_price
                        self.wins += 1
                        self.total_pnl += pnl
                        self.trades.append({
                            'type': 'LONG',
                            'entry': entry_price,
                            'exit': tp,
                            'pnl': pnl,
                            'result': 'WIN',
                            'timestamp': str(timestamp)
                        })
                        if verbose:
                            print(f"✅ [{timestamp}] LONG TP hit @ {tp:.2f} | PnL: +{pnl:.2f}")
                        in_position = False
                        position_type = None
                    
                    # Check SL hit (price falls to SL)
                    elif row['Low'] <= sl:
                        pnl = sl - entry_price
                        self.losses += 1
                        self.total_pnl += pnl
                        self.trades.append({
                            'type': 'LONG',
                            'entry': entry_price,
                            'exit': sl,
                            'pnl': pnl,
                            'result': 'LOSS',
                            'timestamp': str(timestamp)
                        })
                        if verbose:
                            print(f"❌ [{timestamp}] LONG SL hit @ {sl:.2f} | PnL: {pnl:.2f}")
                        in_position = False
                        position_type = None
                
                elif position_type == 'SHORT':
                    # Check TP hit (price falls to TP)
                    if row['Low'] <= tp:
                        pnl = entry_price - tp
                        self.wins += 1
                        self.total_pnl += pnl
                        self.trades.append({
                            'type': 'SHORT',
                            'entry': entry_price,
                            'exit': tp,
                            'pnl': pnl,
                            'result': 'WIN',
                            'timestamp': str(timestamp)
                        })
                        if verbose:
                            print(f"✅ [{timestamp}] SHORT TP hit @ {tp:.2f} | PnL: +{pnl:.2f}")
                        in_position = False
                        position_type = None
                    
                    # Check SL hit (price rises to SL)
                    elif row['High'] >= sl:
                        pnl = entry_price - sl
                        self.losses += 1
                        self.total_pnl += pnl
                        self.trades.append({
                            'type': 'SHORT',
                            'entry': entry_price,
                            'exit': sl,
                            'pnl': pnl,
                            'result': 'LOSS',
                            'timestamp': str(timestamp)
                        })
                        if verbose:
                            print(f"❌ [{timestamp}] SHORT SL hit @ {sl:.2f} | PnL: {pnl:.2f}")
                        in_position = False
                        position_type = None
            
            # Entry conditions (if not in position)
            if not in_position:
                # LONG Setup: Wait for pullback to 78.6% of swing high
                if last_swing_high is not None and swing_high_price > 0:
                    # Calculate retracement level (price fell from swing high)
                    swing_point_idx = last_swing_high
                    # Find the swing low after the swing high
                    subsequent_lows = df.iloc[swing_point_idx:idx]['Low']
                    if len(subsequent_lows) > 0:
                        recent_low = subsequent_lows.min()
                        retracement_depth = swing_high_price - recent_low
                        
                        if retracement_depth > 0:
                            fib_entry = swing_high_price - (retracement_depth * self.multiplier)
                            
                            # Check if price touched the Fib level
                            if row['High'] >= fib_entry and row['Low'] <= fib_entry:
                                in_position = True
                                position_type = 'LONG'
                                entry_price = fib_entry
                                tp = swing_high_price  # 100% retracement
                                # SL is 23.6% BELOW the swing low (failed setup)
                                sl = recent_low - (retracement_depth * self.sl_multiplier)
                                
                                if verbose:
                                    print(f"📈 [{timestamp}] LONG entry @ {entry_price:.2f} | TP: {tp:.2f} | SL: {sl:.2f}")
                
                # SHORT Setup: Wait for pullback to 78.6% of swing low
                if last_swing_low is not None and swing_low_price > 0:
                    # Calculate retracement level (price rose from swing low)
                    swing_point_idx = last_swing_low
                    # Find the swing high after the swing low
                    subsequent_highs = df.iloc[swing_point_idx:idx]['High']
                    if len(subsequent_highs) > 0:
                        recent_high = subsequent_highs.max()
                        retracement_depth = recent_high - swing_low_price
                        
                        if retracement_depth > 0:
                            fib_entry = swing_low_price + (retracement_depth * self.multiplier)
                            
                            # Check if price touched the Fib level
                            if row['High'] >= fib_entry and row['Low'] <= fib_entry:
                                in_position = True
                                position_type = 'SHORT'
                                entry_price = fib_entry
                                tp = swing_low_price  # 100% retracement
                                # SL is 23.6% ABOVE the swing high (failed setup)
                                sl = recent_high + (retracement_depth * self.sl_multiplier)
                                
                                if verbose:
                                    print(f"📉 [{timestamp}] SHORT entry @ {entry_price:.2f} | TP: {tp:.2f} | SL: {sl:.2f}")
        
        # Calculate final statistics
        total_trades = self.wins + self.losses
        if total_trades > 0:
            self.win_rate = (self.wins / total_trades) * 100
            self.avg_pnl = self.total_pnl / total_trades
        else:
            self.win_rate = 0.0
            self.avg_pnl = 0.0
    
    def print_results(self):
        """Print backtest results"""
        print("\n" + "="*80)
        print("📊 BACKTEST RESULTS")
        print("="*80)
        print(f"Total Trades: {len(self.trades)}")
        print(f"  Wins: {self.wins} ✅")
        print(f"  Losses: {self.losses} ❌")
        print(f"  Win Rate: {self.win_rate:.2f}%")
        print(f"  Total PnL: {self.total_pnl:.2f} points")
        print(f"  Avg PnL per Trade: {self.avg_pnl:.2f} points")
        print("="*80)
        
        # Show last 10 trades
        if self.trades:
            print("\n📝 Last 10 Trades:")
            print("-" * 80)
            for trade in self.trades[-10:]:
                result_icon = "✅" if trade['result'] == 'WIN' else "❌"
                print(f"{result_icon} {trade['type']} | Entry: {trade['entry']:.2f} | Exit: {trade['exit']:.2f} | PnL: {trade['pnl']:+.2f}")
            print("-" * 80)
        
        # Win rate assessment
        print("\n📈 Strategy Assessment:")
        if self.win_rate >= 95:
            print(f"   ⭐ EXCELLENT - Win rate {self.win_rate:.1f}% exceeds target (98.43%)")
        elif self.win_rate >= 80:
            print(f"   ✅ GOOD - Win rate {self.win_rate:.1f}% is solid")
        elif self.win_rate >= 60:
            print(f"   ⚠️  MODERATE - Win rate {self.win_rate:.1f}% needs improvement")
        else:
            print(f"   ❌ POOR - Win rate {self.win_rate:.1f}% below acceptable threshold")
        
        print("="*80)


def main():
    print("="*80)
    print("🧪 NIFTY50 LOG-FIB SCALPER BACKTEST")
    print("="*80)
    print()
    
    # Initialize backtester
    backtester = NiftyBacktester()
    
    # Fetch data (max 60 days for 5m interval on Yahoo Finance free tier)
    df = backtester.fetch_historical_data(days=30, interval="5m")
    
    if df.empty:
        print("\n❌ No data available. Trying daily data instead...")
        df = backtester.fetch_historical_data(days=365, interval="1d")
    
    if df.empty:
        print("\n❌ Failed to fetch any data. Check internet connection.")
        return
    
    # Run backtest
    backtester.run_backtest(df, verbose=False)
    
    # Print results
    backtester.print_results()
    
    # Save results to JSON
    results = {
        "total_trades": len(backtester.trades),
        "wins": backtester.wins,
        "losses": backtester.losses,
        "win_rate": backtester.win_rate,
        "total_pnl": backtester.total_pnl,
        "avg_pnl": backtester.avg_pnl,
        "trades": backtester.trades[-20:]  # Last 20 trades
    }
    
    with open("backtest_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: backtest_results.json")


if __name__ == "__main__":
    main()
