"""
═══════════════════════════════════════════════════════════════
MULTI-INSTRUMENT TRADING DASHBOARD
═══════════════════════════════════════════════════════════════

Monitors multiple instruments simultaneously and displays
real-time signals, positions, and performance metrics.
"""

import time
import os
from datetime import datetime
from typing import Dict, List
from collections import deque

from ig_client import IGClient
from multi_instrument_config import ALL_CONFIGS

class MultiInstrumentDashboard:
    def __init__(self, ig_config: Dict[str, str], instruments: List[str] = None):
        """
        Initialize Dashboard
        
        ig_config: IG Markets API credentials
        instruments: List of instrument configs to monitor (e.g., ["XAUUSD_5MIN", "XAGUSD_1MIN"])
        """
        self.ig = IGClient(ig_config)
        self.instruments = instruments if instruments else ["XAUUSD_5MIN", "XAGUSD_1MIN"]
        self.instrument_data = {}
        
        # Initialize data structures for each instrument
        for inst_name in self.instruments:
            config = ALL_CONFIGS[inst_name]
            self.instrument_data[inst_name] = {
                "config": config,
                "price_buffer": deque(maxlen=config["config"]["lookback"] * 3),
                "current_signal": None,
                "last_price": None,
                "last_update": None,
            }
    
    def fetch_all_prices(self) -> Dict[str, Dict]:
        """Fetch prices for all instruments"""
        prices = {}
        for inst_name in self.instruments:
            config = ALL_CONFIGS[inst_name]
            epic = config["ig_epic"]
            price_data = self.ig.get_market_price(epic)
            if price_data:
                prices[inst_name] = price_data
                # Update buffer
                self.instrument_data[inst_name]["last_price"] = price_data
                self.instrument_data[inst_name]["last_update"] = datetime.now().isoformat()
                self.instrument_data[inst_name]["price_buffer"].append({
                    "time": price_data["timestamp"],
                    "high": price_data["high"],
                    "low": price_data["low"],
                })
        return prices
    
    def detect_signals(self, inst_name: str) -> Dict:
        """Detect signals for a specific instrument"""
        data = self.instrument_data[inst_name]
        config = data["config"]["config"]
        buffer = list(data["price_buffer"])
        lookback = config["lookback"]
        
        if len(buffer) < lookback * 2:
            return None
        
        import math
        
        # Detect swing high
        for i in range(lookback, len(buffer) - lookback):
            current_high = buffer[i]["high"]
            is_swing_high = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and buffer[j]["high"] >= current_high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                anchored_low = buffer[i]["low"]
                log_val = math.log10(current_high)
                range_diff = abs(current_high - anchored_low)
                effective_range = log_val * range_diff * config["multiplier"] * 4.0
                
                entry = current_high - (config["entry_ratio"] * effective_range)
                tp = current_high - (config["take_profit_ratio"] * effective_range)
                sl = current_high + (config["stop_loss_ratio"] * effective_range)
                
                return {
                    "type": "SHORT",
                    "instrument": inst_name,
                    "swing_price": current_high,
                    "entry": entry,
                    "tp": tp,
                    "sl": sl,
                }
        
        # Detect swing low
        for i in range(lookback, len(buffer) - lookback):
            current_low = buffer[i]["low"]
            is_swing_low = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and buffer[j]["low"] <= current_low:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                anchored_high = buffer[i]["high"]
                log_val = math.log10(current_low)
                range_diff = abs(current_low - anchored_high)
                effective_range = log_val * range_diff * config["multiplier"] * 4.0
                
                entry = current_low + (config["entry_ratio"] * effective_range)
                tp = current_low + (config["take_profit_ratio"] * effective_range)
                sl = current_low - (config["stop_loss_ratio"] * effective_range)
                
                return {
                    "type": "LONG",
                    "instrument": inst_name,
                    "swing_price": current_low,
                    "entry": entry,
                    "tp": tp,
                    "sl": sl,
                }
        
        return None
    
    def display_dashboard(self):
        """Display current dashboard state"""
        os.system("clear" if os.name != "nt" else "cls")
        print("="*100)
        print("🎯 LOG-FIB MULTI-INSTRUMENT DASHBOARD")
        print("="*100)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Instruments: {', '.join(self.instruments)}")
        print("="*100)
        print()
        
        for inst_name in self.instruments:
            data = self.instrument_data[inst_name]
            config = data["config"]
            last_price = data["last_price"]
            
            print(f"📊 {config['instrument']} ({config['timeframe']}) - {config['ig_epic']}")
            print("-"*100)
            
            if last_price:
                print(f"  Last Price: {last_price['last_traded']:.5f}")
                print(f"  Bid/Ask: {last_price['bid']:.5f} / {last_price['ask']:.5f}")
                print(f"  High/Low: {last_price['high']:.5f} / {last_price['low']:.5f}")
                print(f"  Updated: {data['last_update']}")
            else:
                print("  ⏳ Waiting for price data...")
            
            # Show expected performance
            perf = config["performance"]
            print(f"  Expected: Win Rate {perf['win_rate']}% | PF {perf['profit_factor']} | Avg P&L ${perf['avg_pnl_per_trade']:.2f}")
            print()
        
        print("="*100)
        print("💡 Tip: Run live_agent.py for a specific instrument to enable auto-trading")
        print("="*100)
    
    def run(self, poll_interval: int = 10):
        """Run dashboard monitoring loop"""
        print("="*100)
        print("🚀 MULTI-INSTRUMENT DASHBOARD - STARTING")
        print("="*100)
        print(f"Monitoring: {', '.join(self.instruments)}")
        print(f"Poll Interval: {poll_interval} seconds")
        print("="*100)
        
        # Login to IG
        if not self.ig.login():
            print("❌ Failed to login to IG. Exiting.")
            return
        
        print("✅ IG Login successful")
        print()
        
        try:
            while True:
                # Fetch all prices
                prices = self.fetch_all_prices()
                
                # Detect signals for each instrument
                for inst_name in self.instruments:
                    signal = self.detect_signals(inst_name)
                    if signal:
                        self.instrument_data[inst_name]["current_signal"] = signal
                
                # Display dashboard
                self.display_dashboard()
                
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            print()
            print("="*100)
            print("🛑 Dashboard stopped by user")
            print("="*100)
        
        except Exception as e:
            print(f"❌ Critical error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    ig_config = {
        "api_key": os.getenv("IG_API_KEY", "YOUR_API_KEY"),
        "username": os.getenv("IG_USERNAME", "YOUR_USERNAME"),
        "password": os.getenv("IG_PASSWORD", "YOUR_PASSWORD"),
        "account_id": os.getenv("IG_ACCOUNT_ID", "YOUR_ACCOUNT_ID"),
        "demo": os.getenv("IG_DEMO", "true").lower() == "true"
    }
    
    # Monitor all instruments by default
    instruments = ["XAUUSD_5MIN", "XAGUSD_1MIN", "XAUUSD_1MIN"]
    
    dashboard = MultiInstrumentDashboard(ig_config, instruments=instruments)
    dashboard.run(poll_interval=10)
