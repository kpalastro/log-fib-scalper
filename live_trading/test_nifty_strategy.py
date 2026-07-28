"""
═══════════════════════════════════════════════════════════════
NIFTY50 STRATEGY BACKTEST - KOTAK NEO DATA
═══════════════════════════════════════════════════════════════

Test the log-fib scalper strategy on Nifty50 using historical data
from Kotak Neo API.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
from collections import deque

from neo_client import KotakNeoClient
from nifty_config import NIFTY50_5MIN


class NiftyBacktester:
    def __init__(self, neo_config: Dict[str, str], config: Dict = None):
        self.neo = KotakNeoClient(neo_config)
        self.config = config or NIFTY50_5MIN
        self.lookback = self.config["config"]["lookback"]
        self.multiplier = self.config["config"]["multiplier"]
        
        # Results
        self.trades = []
        self.total_pnl = 0.0
        self.wins = 0
        self.losses = 0
        
    def fetch_historical_data(self, days: int = 5) -> List[Dict]:
        """Fetch historical data from Kotak Neo"""
        print(f"📥 Fetching {days} days of historical data...")
        
        if not self.neo.login():
            print("❌ Failed to login to Kotak Neo")
            return []
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        data = self.neo.get_historical_data(
            instrument_token=self.config["neo_instrument_token"],
            from_date=start_date.strftime("%Y-%m-%d"),
            to_date=end_date.strftime("%Y-%m-%d"),
            interval="5minute"
        )
        
        if data:
            print(f"✅ Fetched {len(data)} candles")
            return data
        
        print("❌ Failed to fetch historical data")
        return []
    
    def detect_swing_high(self, buffer: List[Dict], idx: int) -> bool:
        """Check if index is a swing high"""
        lookback = self.lookback
        
        if idx < lookback or idx >= len(buffer) - lookback:
            return False
        
        current_high = buffer[idx]["high"]
        
        for j in range(idx - lookback, idx + lookback + 1):
            if j != idx and buffer[j]["high"] >= current_high:
                return False
        
        return True
    
    def detect_swing_low(self, buffer: List[Dict], idx: int) -> bool:
        """Check if index is a swing low"""
        lookback = self.lookback
        
        if idx < lookback or idx >= len(buffer) - lookback:
            return False
        
        current_low = buffer[idx]["low"]
        
        for j in range(idx - lookback, idx + lookback + 1):
            if j != idx and buffer[j]["low"] <= current_low:
                return False
        
        return True
    
    def run_backtest(self, data: List[Dict]):
        """Run backtest on historical data"""
        print("\n" + "="*80)
        print("🚀 RUNNING BACKTEST")
        print("="*80)
        
        price_buffer = deque(maxlen=self.lookback * 3)
        in_position = False
        position_type = None
        entry_price = 0.0
        tp = 0.0
        sl = 0.0
        last_swing_high = None
        last_swing_low = None
        
        for i, candle in enumerate(data):
            # Add to buffer
            price_buffer.append(candle)
            
            if len(price_buffer) < self.lookback * 2:
                continue
            
            buffer = list(price_buffer)
            current_price = candle["close"]
            
            # Detect swings
            if self.detect_swing_high(buffer, len(buffer) - 1):
                last_swing_high = buffer[-1]["high"]
            
            if self.detect_swing_low(buffer, len(buffer) - 1):
                last_swing_low = buffer[-1]["low"]
            
            # Calculate Fib levels if we have both swings
            if last_swing_high and last_swing_low:
                range_size = last_swing_high - last_swing_low
                entry = last_swing_low + (range_size * self.multiplier)
                tp_level = last_swing_high
                sl_level = last_swing_low - (range_size * 0.236)
                
                # Check for LONG signal
                if not in_position and current_price <= entry * 1.001:
                    in_position = True
                    position_type = "LONG"
                    entry_price = entry
                    tp = tp_level
                    sl = sl_level
                    
                    self.trades.append({
                        "type": "LONG",
                        "entry_time": candle["timestamp"],
                        "entry_price": entry_price,
                        "tp": tp,
                        "sl": sl
                    })
                    
                    print(f"📊 LONG @ {entry_price:.2f} (Time: {candle['timestamp']})")
                
                # Check for exit
                if in_position and position_type == "LONG":
                    if candle["high"] >= tp:
                        # TP hit
                        pnl = tp - entry_price
                        self.total_pnl += pnl
                        self.wins += 1
                        
                        self.trades[-1]["exit_time"] = candle["timestamp"]
                        self.trades[-1]["exit_price"] = tp
                        self.trades[-1]["pnl"] = pnl
                        self.trades[-1]["outcome"] = "WIN"
                        
                        print(f"✅ TP HIT @ {tp:.2f} | PnL: +{pnl:.2f}")
                        in_position = False
                        position_type = None
                    
                    elif candle["low"] <= sl:
                        # SL hit
                        pnl = sl - entry_price
                        self.total_pnl += pnl
                        self.losses += 1
                        
                        self.trades[-1]["exit_time"] = candle["timestamp"]
                        self.trades[-1]["exit_price"] = sl
                        self.trades[-1]["pnl"] = pnl
                        self.trades[-1]["outcome"] = "LOSS"
                        
                        print(f"❌ SL HIT @ {sl:.2f} | PnL: {pnl:.2f}")
                        in_position = False
                        position_type = None
        
        # Print results
        print("\n" + "="*80)
        print("📊 BACKTEST RESULTS")
        print("="*80)
        print(f"Total Trades: {len(self.trades)}")
        print(f"Wins: {self.wins} | Losses: {self.losses}")
        
        if len(self.trades) > 0:
            win_rate = (self.wins / len(self.trades)) * 100
            print(f"Win Rate: {win_rate:.2f}%")
            print(f"Total PnL: {self.total_pnl:.2f} points")
            
            # Calculate profit factor
            gross_profit = sum(t["pnl"] for t in self.trades if t["pnl"] > 0)
            gross_loss = abs(sum(t["pnl"] for t in self.trades if t["pnl"] < 0))
            
            if gross_loss > 0:
                profit_factor = gross_profit / gross_loss
                print(f"Profit Factor: {profit_factor:.2f}")
            else:
                print(f"Profit Factor: N/A (no losses)")
        
        print("="*80)
        
        # Save results
        results = {
            "total_trades": len(self.trades),
            "wins": self.wins,
            "losses": self.losses,
            "total_pnl": self.total_pnl,
            "trades": self.trades
        }
        
        with open("backtest_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to backtest_results.json")
        
        return results


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Load Kotak Neo credentials
    neo_config = {
        "user_key": os.getenv("NEO_USER_KEY"),
        "api_key": os.getenv("NEO_API_KEY"),
        "token": os.getenv("NEO_TOKEN"),
        "source_id": os.getenv("NEO_SOURCE_ID", "WEB")
    }
    
    # Check if credentials are set
    if not all([neo_config["user_key"], neo_config["api_key"], neo_config["token"]]):
        print("❌ Missing Kotak Neo credentials!")
        print("Please set NEO_USER_KEY, NEO_API_KEY, and NEO_TOKEN in .env file")
        print("\nTo get credentials:")
        print("1. Login to https://neo.kotak.com")
        print("2. Go to Settings → API")
        print("3. Generate API key and token")
        print("4. Copy .env.neo to .env and fill in your credentials")
        exit(1)
    
    # Create backtester
    backtester = NiftyBacktester(neo_config)
    
    # Fetch historical data (last 5 days)
    data = backtester.fetch_historical_data(days=5)
    
    if data:
        # Run backtest
        results = backtester.run_backtest(data)
