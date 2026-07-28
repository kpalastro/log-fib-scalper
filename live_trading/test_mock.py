"""
═══════════════════════════════════════════════════════════════
KOTAK NEO API - MOCK TEST (NO CREDENTIALS REQUIRED)
═══════════════════════════════════════════════════════════════

Test the strategy logic with simulated Nifty50 price data.
This validates the swing detection and Fibonacci calculations
without needing real API credentials.
"""

import random
import math
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, List, Optional

# Import config
from nifty_config import NIFTY50_5MIN


class MockNiftyData:
    """Generate realistic mock Nifty50 price data with clear swings"""
    
    def __init__(self, start_price: float = 22400.0, volatility: float = 0.002):
        self.price = start_price
        self.volatility = volatility
        self.trend_direction = 1
        self.trend_counter = 0
        
    def generate_candle(self, timestamp: datetime) -> Dict:
        """Generate a single 5-minute candle with trending behavior"""
        # Create trending moves with reversals to form swings
        self.trend_counter += 1
        
        # Change trend every 20-30 candles to create swings
        if self.trend_counter > random.randint(20, 30):
            self.trend_direction *= -1
            self.trend_counter = 0
        
        # Trending move + noise
        trend_move = self.trend_direction * random.uniform(0.0005, 0.0015)
        noise = random.gauss(0, self.volatility * 0.3)
        change = trend_move + noise
        
        open_price = self.price
        close_price = self.price * (1 + change)
        
        # High and low with more range for swing detection
        range_size = abs(close_price - open_price) * random.uniform(1.5, 3.0)
        high_price = max(open_price, close_price) + range_size
        low_price = min(open_price, close_price) - range_size
        
        self.price = close_price
        
        return {
            "timestamp": timestamp.isoformat(),
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": random.randint(100000, 500000)
        }


class StrategyTester:
    """Test the log-fib scalper strategy logic"""
    
    def __init__(self, config: Dict = None):
        self.config = config or NIFTY50_5MIN
        self.lookback = self.config["config"]["lookback"]
        self.multiplier = self.config["config"]["multiplier"]
        
        # Results
        self.trades = []
        self.total_pnl = 0.0
        self.wins = 0
        self.losses = 0
        
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
    
    def run_test(self, data: List[Dict], verbose: bool = True):
        """Run strategy test on data"""
        if verbose:
            print("\n" + "="*80)
            print("🧪 RUNNING STRATEGY TEST (MOCK DATA)")
            print("="*80)
            print(f"Instrument: {self.config['instrument']}")
            print(f"Timeframe: {self.config['timeframe']}")
            print(f"Lookback: {self.lookback} | Multiplier: {self.multiplier}")
            print(f"Data Points: {len(data)} candles")
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
                if verbose:
                    print(f"📈 Swing High detected @ {last_swing_high:.2f} (candle {i})")
            
            if self.detect_swing_low(buffer, len(buffer) - 1):
                last_swing_low = buffer[-1]["low"]
                if verbose:
                    print(f"📉 Swing Low detected @ {last_swing_low:.2f} (candle {i})")
            
            # Calculate Fib levels if we have both swings
            if last_swing_high and last_swing_low:
                range_size = last_swing_high - last_swing_low
                entry = last_swing_low + (range_size * self.multiplier)
                tp_level = last_swing_high
                sl_level = last_swing_low - (range_size * 0.236)
                
                # Debug: print levels occasionally
                if verbose and i % 50 == 0:
                    print(f"\n[Candle {i}] Price: {current_price:.2f} | Entry: {entry:.2f} | Range: {range_size:.2f}")
                    print(f"  Swing H/L: {last_swing_high:.2f} / {last_swing_low:.2f}")
                
                # Check for LONG signal (price retracing down to entry)
                # Only trigger if we're in a retracement phase
                if not in_position and current_price <= entry * 1.002 and current_price >= last_swing_low * 1.001:
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
                    
                    if verbose:
                        print(f"\n📊 LONG SIGNAL @ {entry_price:.2f}")
                        print(f"   Current: {current_price:.2f} | Entry: {entry:.2f}")
                        print(f"   TP: {tp:.2f} | SL: {sl:.2f}")
                        print(f"   R:R = 1:{(tp-entry)/(entry-sl):.2f}")
                
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
                        
                        if verbose:
                            print(f"✅ TP HIT @ {tp:.2f} | PnL: +{pnl:.2f} points\n")
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
                        
                        if verbose:
                            print(f"❌ SL HIT @ {sl:.2f} | PnL: {pnl:.2f} points\n")
                        in_position = False
                        position_type = None
        
        # Print results
        self.print_results()
        
        return {
            "total_trades": len(self.trades),
            "wins": self.wins,
            "losses": self.losses,
            "total_pnl": self.total_pnl,
            "trades": self.trades
        }
    
    def print_results(self):
        """Print test results"""
        print("\n" + "="*80)
        print("📊 TEST RESULTS")
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
            
            # Average win/loss
            if self.wins > 0:
                avg_win = gross_profit / self.wins
                print(f"Average Win: {avg_win:.2f} points")
            
            if self.losses > 0:
                avg_loss = gross_loss / self.losses
                print(f"Average Loss: {avg_loss:.2f} points")
        
        print("="*80)


def main():
    """Run mock test"""
    print("\n" + "="*80)
    print("🧪 KOTAK NEO - NIFTY50 STRATEGY TEST (MOCK DATA)")
    print("="*80)
    print("\nThis test simulates Nifty50 price data to validate the strategy logic.")
    print("No API credentials required.\n")
    
    # Generate mock data (300 candles = ~3 full days of 5-min data for more swings)
    print("📊 Generating mock Nifty50 data (300 candles)...")
    mock_data = MockNiftyData(start_price=22400.0, volatility=0.0015)
    
    candles = []
    current_time = datetime(2026, 5, 18, 9, 15)
    
    for i in range(300):
        candle = mock_data.generate_candle(current_time)
        candles.append(candle)
        current_time += timedelta(minutes=5)
    
    print(f"✅ Generated {len(candles)} candles")
    print(f"   Price range: {min(c['low'] for c in candles):.2f} - {max(c['high'] for c in candles):.2f}")
    
    # Run strategy test
    tester = StrategyTester()
    results = tester.run_test(candles, verbose=True)
    
    # Save results
    import json
    with open("mock_test_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to mock_test_results.json")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("1. Get your Kotak Neo API credentials from https://neo.kotak.com")
    print("2. Copy .env.neo to .env and fill in credentials")
    print("3. Run: python live_trading/test_nifty_strategy.py (real data backtest)")
    print("4. Run: python live_trading/nifty_live_agent.py (live trading)")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
