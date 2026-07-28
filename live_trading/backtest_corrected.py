"""
═══════════════════════════════════════════════════════════════
NIFTY50 STRATEGY BACKTEST - CORRECTED LOGIC
═══════════════════════════════════════════════════════════════

Backtest the log-fib scalper strategy with CORRECT entry logic.

Strategy Logic (from nifty_live_agent.py):
1. Detect swing HIGH → price falls → detect swing LOW
2. Calculate range = swing_high - swing_low
3. LONG Entry = swing_low + (range × 0.786) ← 78.6% retracement UP
4. TP = swing_high (100% retracement)
5. SL = swing_low - (range × 0.236) ← 23.6% below swing low

Reverse for SHORT:
1. Detect swing LOW → price rises → detect swing HIGH
2. Calculate range = swing_high - swing_low
3. SHORT Entry = swing_low + (range × 0.786) ← 78.6% retracement UP
4. TP = swing_low (100% retracement down)
5. SL = swing_high + (range × 0.236) ← 23.6% above swing high
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque
import json


class NiftyBacktester:
    def __init__(self, config: Dict = None):
        self.config = config or {
            "lookback": 10,
            "multiplier": 0.786,
            "sl_multiplier": 0.236,
            "instrument": "^NSEI"
        }
        self.lookback = self.config["lookback"]
        self.multiplier = self.config["multiplier"]
        self.sl_multiplier = self.config["sl_multiplier"]
        
        self.trades = []
        self.wins = 0
        self.losses = 0
        self.total_pnl = 0.0
        
    def fetch_historical_data(self, days: int = 30, interval: str = "5m") -> pd.DataFrame:
        print(f"📥 Fetching {days} days of {interval} data for Nifty50...")
        
        ticker = yf.Ticker(self.config["instrument"])
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        df = ticker.history(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval=interval
        )
        
        if df.empty:
            print("❌ No data fetched.")
            return df
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df = df.dropna()
        
        print(f"✅ Fetched {len(df)} candles")
        print(f"   Range: {df.index[0].strftime('%Y-%m-%d %H:%M')} to {df.index[-1].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Price: {df['Low'].min():.2f} - {df['High'].max():.2f}")
        
        return df
    
    def detect_swing_high(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """Detect swing high at index"""
        if idx < self.lookback or idx >= len(df) - self.lookback:
            return None
        
        current_high = df.iloc[idx]['High']
        
        for j in range(idx - self.lookback, idx + self.lookback + 1):
            if j != idx and df.iloc[j]['High'] >= current_high:
                return None
        
        return {
            "idx": idx,
            "high": current_high,
            "low": df.iloc[idx]['Low'],
            "time": df.index[idx]
        }
    
    def detect_swing_low(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """Detect swing low at index"""
        if idx < self.lookback or idx >= len(df) - self.lookback:
            return None
        
        current_low = df.iloc[idx]['Low']
        
        for j in range(idx - self.lookback, idx + self.lookback + 1):
            if j != idx and df.iloc[j]['Low'] <= current_low:
                return None
        
        return {
            "idx": idx,
            "low": current_low,
            "high": df.iloc[idx]['High'],
            "time": df.index[idx]
        }
    
    def run_backtest(self, df: pd.DataFrame, verbose: bool = False):
        """
        Run backtest with CORRECT strategy logic
        
        LONG Setup:
        - Swing High forms at price H
        - Price falls, Swing Low forms at price L (after the high)
        - Range = H - L
        - Entry = L + (Range × 0.786)
        - Wait for price to rise back to entry
        - TP = H, SL = L - (Range × 0.236)
        
        SHORT Setup:
        - Swing Low forms at price L
        - Price rises, Swing High forms at price H (after the low)
        - Range = H - L
        - Entry = L + (Range × 0.786)
        - Wait for price to rise to entry, then SHORT
        - TP = L, SL = H + (Range × 0.236)
        """
        print("\n" + "="*80)
        print("🚀 RUNNING BACKTEST (Corrected Logic)")
        print("="*80)
        print(f"Strategy: {self.multiplier*100:.1f}% Fib Retracement")
        print(f"Lookback: {self.lookback} candles")
        print(f"Data points: {len(df)}")
        print("="*80 + "\n")
        
        in_position = False
        position_type = None
        entry_price = 0.0
        tp = 0.0
        sl = 0.0
        
        last_swing_high = None  # Most recent swing high
        last_swing_low = None   # Most recent swing low
        
        # For LONG: need swing high → swing low sequence, then entry on retracement up
        # For SHORT: need swing low → swing high sequence, then entry on retracement up
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            current_price = row['Close']
            timestamp = row.name
            
            # Detect new swings
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
            
            # Exit logic
            if in_position:
                if position_type == 'LONG':
                    if row['High'] >= tp:
                        pnl = tp - entry_price
                        self.wins += 1
                        self.total_pnl += pnl
                        self.trades.append({
                            'type': 'LONG', 'entry': entry_price, 'exit': tp,
                            'pnl': pnl, 'result': 'WIN', 'timestamp': str(timestamp)
                        })
                        if verbose:
                            print(f"✅ [{timestamp}] LONG TP @ {tp:.2f} | +{pnl:.2f}")
                        in_position = False
                    elif row['Low'] <= sl:
                        pnl = sl - entry_price
                        self.losses += 1
                        self.total_pnl += pnl
                        self.trades.append({
                            'type': 'LONG', 'entry': entry_price, 'exit': sl,
                            'pnl': pnl, 'result': 'LOSS', 'timestamp': str(timestamp)
                        })
                        if verbose:
                            print(f"❌ [{timestamp}] LONG SL @ {sl:.2f} | {pnl:.2f}")
                        in_position = False
                
                elif position_type == 'SHORT':
                    if row['Low'] <= tp:
                        pnl = entry_price - tp
                        self.wins += 1
                        self.total_pnl += pnl
                        self.trades.append({
                            'type': 'SHORT', 'entry': entry_price, 'exit': tp,
                            'pnl': pnl, 'result': 'WIN', 'timestamp': str(timestamp)
                        })
                        if verbose:
                            print(f"✅ [{timestamp}] SHORT TP @ {tp:.2f} | +{pnl:.2f}")
                        in_position = False
                    elif row['High'] >= sl:
                        pnl = entry_price - sl
                        self.losses += 1
                        self.total_pnl += pnl
                        self.trades.append({
                            'type': 'SHORT', 'entry': entry_price, 'exit': sl,
                            'pnl': pnl, 'result': 'LOSS', 'timestamp': str(timestamp)
                        })
                        if verbose:
                            print(f"❌ [{timestamp}] SHORT SL @ {sl:.2f} | {pnl:.2f}")
                        in_position = False
            
            # Entry logic (only if not in position)
            if not in_position:
                # LONG Entry: swing high → swing low → retracement to 78.6%
                if last_swing_high and last_swing_low:
                    # Ensure swing low came AFTER swing high
                    if last_swing_low['idx'] > last_swing_high['idx']:
                        swing_high_price = last_swing_high['high']
                        swing_low_price = last_swing_low['low']
                        range_size = swing_high_price - swing_low_price
                        
                        if range_size > 0:
                            fib_entry = swing_low_price + (range_size * self.multiplier)
                            tp_price = swing_high_price
                            sl_price = swing_low_price - (range_size * self.sl_multiplier)
                            
                            # Check if price touched entry level
                            if row['Low'] <= fib_entry <= row['High']:
                                in_position = True
                                position_type = 'LONG'
                                entry_price = fib_entry
                                tp = tp_price
                                sl = sl_price
                                if verbose:
                                    print(f"📈 [{timestamp}] LONG @ {entry_price:.2f} | TP: {tp:.2f} | SL: {sl:.2f}")
                
                # SHORT Entry: swing low → swing high → retracement to 78.6%
                if last_swing_low and last_swing_high:
                    # Ensure swing high came AFTER swing low
                    if last_swing_high['idx'] > last_swing_low['idx']:
                        swing_low_price = last_swing_low['low']
                        swing_high_price = last_swing_high['high']
                        range_size = swing_high_price - swing_low_price
                        
                        if range_size > 0:
                            fib_entry = swing_low_price + (range_size * self.multiplier)
                            tp_price = swing_low_price
                            sl_price = swing_high_price + (range_size * self.sl_multiplier)
                            
                            # Check if price touched entry level
                            if row['Low'] <= fib_entry <= row['High']:
                                in_position = True
                                position_type = 'SHORT'
                                entry_price = fib_entry
                                tp = tp_price
                                sl = sl_price
                                if verbose:
                                    print(f"📉 [{timestamp}] SHORT @ {entry_price:.2f} | TP: {tp:.2f} | SL: {sl:.2f}")
        
        # Calculate stats
        total_trades = self.wins + self.losses
        self.win_rate = (self.wins / total_trades * 100) if total_trades > 0 else 0
        self.avg_pnl = self.total_pnl / total_trades if total_trades > 0 else 0
    
    def print_results(self):
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
        
        if self.trades:
            print("\n📝 Last 10 Trades:")
            print("-" * 80)
            for trade in self.trades[-10:]:
                icon = "✅" if trade['result'] == 'WIN' else "❌"
                print(f"{icon} {trade['type']} | Entry: {trade['entry']:.2f} | Exit: {trade['exit']:.2f} | PnL: {trade['pnl']:+.2f}")
            print("-" * 80)
        
        print("\n📈 Assessment:")
        if self.win_rate >= 95:
            print(f"   ⭐ EXCELLENT - {self.win_rate:.1f}% (target: 98.43%)")
        elif self.win_rate >= 80:
            print(f"   ✅ GOOD - {self.win_rate:.1f}%")
        elif self.win_rate >= 60:
            print(f"   ⚠️  MODERATE - {self.win_rate:.1f}%")
        else:
            print(f"   ❌ POOR - {self.win_rate:.1f}%")
        print("="*80)


def main():
    print("="*80)
    print("🧪 NIFTY50 LOG-FIB SCALPER BACKTEST (Corrected)")
    print("="*80)
    print()
    
    backtester = NiftyBacktester()
    df = backtester.fetch_historical_data(days=30, interval="5m")
    
    if df.empty:
        print("\n❌ No data. Trying daily...")
        df = backtester.fetch_historical_data(days=365, interval="1d")
    
    if df.empty:
        return
    
    backtester.run_backtest(df, verbose=False)
    backtester.print_results()
    
    # Save results
    results = {
        "total_trades": len(backtester.trades),
        "wins": backtester.wins,
        "losses": backtester.losses,
        "win_rate": backtester.win_rate,
        "total_pnl": backtester.total_pnl,
        "avg_pnl": backtester.avg_pnl,
        "trades": backtester.trades[-20:]
    }
    
    with open("backtest_results_corrected.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: backtest_results_corrected.json")


if __name__ == "__main__":
    main()
