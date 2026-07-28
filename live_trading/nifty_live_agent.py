"""
═══════════════════════════════════════════════════════════════
LOG-FIB NIFTY50 LIVE TRADING AGENT - KOTAK NEO V2
═══════════════════════════════════════════════════════════════

Live trading agent for Nifty50 index using Kotak Neo API v2.
Implements the log-fib scalper strategy with swing detection
and Fibonacci retracement levels.
"""

import time
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import deque

# Import Kotak Neo client
from neo_client import KotakNeoClient

# Import Nifty50 configs
from nifty_config import ALL_CONFIGS, DEFAULT_CONFIG, NIFTY50_5MIN


class NiftyLiveTradingAgent:
    def __init__(self, neo_config: Dict[str, str], instrument_config: Dict = None):
        """
        Initialize Nifty50 Live Trading Agent
        
        neo_config: Kotak Neo API credentials
        instrument_config: Configuration for specific instrument (from nifty_config.py)
        """
        self.neo = KotakNeoClient(neo_config)
        self.config = instrument_config if instrument_config else DEFAULT_CONFIG
        self.instrument_name = self.config["instrument"]
        self.timeframe = self.config["timeframe"]
        self.neo_token = self.config["neo_instrument_token"]
        self.strategy_config = self.config["config"]
        self.performance_config = self.config["performance"]
        
        # Price history buffer (for swing detection)
        self.lookback = self.strategy_config["lookback"]
        self.price_buffer = deque(maxlen=self.lookback * 3)  # 3x lookback for safety
        
        # Trading state
        self.in_position = False
        self.position_type = None  # "LONG" or "SHORT"
        self.position_order_id = None
        self.position_entry_price = 0.0
        self.position_tp = 0.0
        self.position_sl = 0.0
        
        # Statistics
        self.trades_today = 0
        self.daily_pnl = 0.0
        self.total_trades = 0
        self.total_wins = 0
        self.total_losses = 0
        
        # Signal levels (calculated from swings)
        self.current_signal = None
        
    def fetch_price(self) -> Optional[Dict]:
        """Fetch latest price from Kotak Neo"""
        return self.neo.get_market_price(self.neo_token)
    
    def update_price_buffer(self, price_data: Dict):
        """Add new price to buffer for swing detection"""
        self.price_buffer.append({
            "time": price_data["timestamp"],
            "high": price_data["high"],
            "low": price_data["low"],
            "bid": price_data["bid"],
            "ask": price_data["ask"]
        })
    
    def detect_swing_high(self) -> Optional[Dict]:
        """Detect swing high in price buffer"""
        if len(self.price_buffer) < self.lookback * 2:
            return None
        
        buffer = list(self.price_buffer)
        lookback = self.lookback
        
        for i in range(lookback, len(buffer) - lookback):
            current_high = buffer[i]["high"]
            is_swing_high = True
            
            for j in range(i - lookback, i + lookback + 1):
                if j != i and buffer[j]["high"] >= current_high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                return {
                    "type": "HIGH",
                    "idx": i,
                    "time": buffer[i]["time"],
                    "high": current_high,
                    "low": buffer[i]["low"]  # Anchored low
                }
        
        return None
    
    def detect_swing_low(self) -> Optional[Dict]:
        """Detect swing low in price buffer"""
        if len(self.price_buffer) < self.lookback * 2:
            return None
        
        buffer = list(self.price_buffer)
        lookback = self.lookback
        
        for i in range(lookback, len(buffer) - lookback):
            current_low = buffer[i]["low"]
            is_swing_low = True
            
            for j in range(i - lookback, i + lookback + 1):
                if j != i and buffer[j]["low"] <= current_low:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                return {
                    "type": "LOW",
                    "idx": i,
                    "time": buffer[i]["time"],
                    "low": current_low,
                    "high": buffer[i]["high"]  # Anchored high
                }
        
        return None
    
    def calculate_fib_levels(self, swing_high: Dict, swing_low: Dict) -> Dict:
        """Calculate Fibonacci retracement levels"""
        high = swing_high["high"]
        low = swing_low["low"]
        range_size = high - low
        
        return {
            "entry": low + (range_size * self.strategy_config["multiplier"]),
            "tp": high,
            "sl": low - (range_size * 0.236)  # 23.6% below swing low
        }
    
    def check_signal_trigger(self, current_price: float) -> bool:
        """Check if current price triggers the signal"""
        if not self.current_signal:
            return False
        
        if self.current_signal["type"] == "LONG":
            # Price should touch or cross the entry level
            return current_price <= self.current_signal["entry"] * 1.001  # 0.1% tolerance
        
        elif self.current_signal["type"] == "SHORT":
            return current_price >= self.current_signal["entry"] * 0.999
        
        return False
    
    def execute_trade(self, signal: Dict, size: float):
        """Execute a trade based on signal"""
        try:
            if signal["type"] == "LONG":
                transaction_type = "BUY"
            else:
                transaction_type = "SELL"
            
            # Place order via Kotak Neo
            order_result = self.neo.place_order(
                instrument_token=self.neo_token,
                transaction_type=transaction_type,
                quantity=int(size),
                order_type="MARKET",
                product_type="INTRADAY"
            )
            
            if order_result and order_result.get("success"):
                self.in_position = True
                self.position_type = signal["type"]
                self.position_order_id = order_result.get("order_id")
                self.position_entry_price = signal["entry"]
                self.position_tp = signal["tp"]
                self.position_sl = signal["sl"]
                
                print(f"📊 POSITION OPENED: {signal['type']}")
                print(f"   Entry: {self.position_entry_price:.2f}")
                print(f"   TP: {self.position_tp:.2f} | SL: {self.position_sl:.2f}")
                print(f"   Order ID: {self.position_order_id}")
                
                self.total_trades += 1
                self.trades_today += 1
            else:
                print(f"❌ Trade execution failed: {order_result}")
                
        except Exception as e:
            print(f"❌ Trade execution error: {e}")
    
    def check_exit_conditions(self, current_price: float):
        """Check if we should exit the current position"""
        if not self.in_position:
            return
        
        if self.position_type == "LONG":
            # Check TP
            if current_price >= self.position_tp:
                print(f"✅ TP HIT! Closing LONG @ {current_price:.2f}")
                self.close_position("TARGET")
                self.total_wins += 1
            # Check SL
            elif current_price <= self.position_sl:
                print(f"❌ SL HIT! Closing LONG @ {current_price:.2f}")
                self.close_position("STOPLOSS")
                self.total_losses += 1
        
        elif self.position_type == "SHORT":
            # Check TP
            if current_price <= self.position_tp:
                print(f"✅ TP HIT! Closing SHORT @ {current_price:.2f}")
                self.close_position("TARGET")
                self.total_wins += 1
            # Check SL
            elif current_price >= self.position_sl:
                print(f"❌ SL HIT! Closing SHORT @ {current_price:.2f}")
                self.close_position("STOPLOSS")
                self.total_losses += 1
    
    def close_position(self, reason: str):
        """Close the current position"""
        try:
            if self.position_type == "LONG":
                transaction_type = "SELL"
            else:
                transaction_type = "BUY"
            
            # For index, we use quantity=1
            close_result = self.neo.place_order(
                instrument_token=self.neo_token,
                transaction_type=transaction_type,
                quantity=1,
                order_type="MARKET",
                product_type="INTRADAY"
            )
            
            if close_result and close_result.get("success"):
                print(f"📊 POSITION CLOSED: {reason}")
                self.in_position = False
                self.position_type = None
                self.position_order_id = None
                self.position_entry_price = 0.0
                self.position_tp = 0.0
                self.position_sl = 0.0
            else:
                print(f"❌ Close position failed: {close_result}")
                
        except Exception as e:
            print(f"❌ Close position error: {e}")
    
    def run(self, poll_interval: int = 5):
        """Main trading loop"""
        print("="*80)
        print(f"🚀 LOG-FIB NIFTY50 LIVE TRADING AGENT - STARTING")
        print("="*80)
        print(f"Instrument: {self.instrument_name} ({self.timeframe})")
        print(f"Kotak Neo Token: {self.neo_token}")
        print(f"Strategy Config: Lookback={self.lookback}, Multiplier={self.strategy_config['multiplier']}")
        print(f"Expected Performance: Win Rate={self.performance_config['expected_win_rate']*100:.2f}%, PF={self.performance_config['expected_profit_factor']:.2f}")
        print(f"Poll Interval: {poll_interval} seconds")
        print("="*80)
        
        try:
            # Login to Kotak Neo
            if not self.neo.login():
                print("❌ Failed to login to Kotak Neo. Exiting.")
                return
            
            print("\n📡 Starting live data feed...\n")
            
            while True:
                # Fetch current price
                price_data = self.fetch_price()
                
                if not price_data:
                    print("⚠️  Failed to fetch price, retrying...")
                    time.sleep(poll_interval)
                    continue
                
                current_price = price_data["last_traded"]
                timestamp = price_data["timestamp"]
                
                # Update price buffer
                self.update_price_buffer(price_data)
                
                # Detect swings
                swing_high = self.detect_swing_high()
                swing_low = self.detect_swing_low()
                
                # Update signals
                if swing_high and swing_low:
                    fib_levels = self.calculate_fib_levels(swing_high, swing_low)
                    
                    # Determine signal type based on current price position
                    if current_price < fib_levels["entry"]:
                        signal_type = "LONG"
                    else:
                        signal_type = "SHORT"
                    
                    self.current_signal = {
                        "type": signal_type,
                        "entry": fib_levels["entry"],
                        "tp": fib_levels["tp"],
                        "sl": fib_levels["sl"],
                        "swing_high": swing_high["high"],
                        "swing_low": swing_low["low"]
                    }
                    
                    # Print signal if changed
                    if not hasattr(self, '_last_signal_type') or self._last_signal_type != signal_type:
                        print(f"📊 NEW {signal_type} SIGNAL @ {timestamp}")
                        print(f"   Swing High: {swing_high['high']:.2f}")
                        print(f"   Swing Low: {swing_low['low']:.2f}")
                        print(f"   Entry: {fib_levels['entry']:.2f}")
                        print(f"   TP: {fib_levels['tp']:.2f} | SL: {fib_levels['sl']:.2f}")
                        self._last_signal_type = signal_type
                
                # Check for trade entry
                if not self.in_position and self.current_signal:
                    if self.check_signal_trigger(current_price):
                        size = 1  # 1 unit for index
                        print(f"\n🎯 SIGNAL TRIGGERED! Executing {self.current_signal['type']}...")
                        self.execute_trade(self.current_signal, size)
                
                # Check for exit
                if self.in_position:
                    self.check_exit_conditions(current_price)
                
                # Log status
                win_rate = (self.total_wins / self.total_trades * 100) if self.total_trades > 0 else 0
                print(f"💹 Price: {current_price:.2f} | Position: {'IN' if self.in_position else 'OUT'} | "
                      f"Trades Today: {self.trades_today} | Win Rate: {win_rate:.1f}%")
                
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            print("\n" + "="*80)
            print("🛑 Trading agent stopped by user")
            print("="*80)
            print(f"Total Trades: {self.total_trades}")
            print(f"Wins: {self.total_wins} | Losses: {self.total_losses}")
            print(f"Win Rate: {win_rate:.1f}%")
            print("="*80)
        
        except Exception as e:
            print(f"❌ Critical error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # Load Kotak Neo config from environment
    from dotenv import load_dotenv
    load_dotenv()
    
    neo_config = {
        "consumer_key": os.getenv("KOTAK_CONSUMER_KEY"),
        "totp_key": os.getenv("KOTAK_TOTP_KEY"),
        "mobile_number": os.getenv("KOTAK_MOBILE_NUMBER"),
        "password": os.getenv("KOTAK_PASSWORD"),
        "mpin": os.getenv("KOTAK_MPIN"),
        "ucc": os.getenv("KOTAK_UCC")
    }
    
    # Select instrument from environment variable or default to Nifty50 5-min
    instrument_choice = os.getenv("NEO_INSTRUMENT", "NIFTY50_5MIN")
    instrument_config = ALL_CONFIGS.get(instrument_choice, DEFAULT_CONFIG)
    
    print(f"📊 Using configuration: {instrument_choice}")
    
    # Create and run agent
    agent = NiftyLiveTradingAgent(neo_config, instrument_config)
    agent.run(poll_interval=5)
