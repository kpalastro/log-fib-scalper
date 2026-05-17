"""
═══════════════════════════════════════════════════════════════
LOG-FIB LIVE TRADING AGENT V2
═══════════════════════════════════════════════════════════════

Multi-instrument support with instrument-specific optimal configurations.
Supports: XAGUSD 1-min, XAUUSD 5-min, XAUUSD 1-min
"""

import time
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from collections import deque

# Import our IG client
from ig_client import IGClient

# Import multi-instrument configs
from multi_instrument_config import ALL_CONFIGS, DEFAULT_CONFIG, XAUUSD_5MIN

class LiveTradingAgent:
    def __init__(self, ig_config: Dict[str, str], instrument_config: Dict = None):
        """
        Initialize Live Trading Agent
        
        ig_config: IG Markets API credentials
        instrument_config: Configuration for specific instrument (from multi_instrument_config.py)
        """
        self.ig = IGClient(ig_config)
        self.config = instrument_config if instrument_config else DEFAULT_CONFIG
        self.instrument_name = self.config["instrument"]
        self.timeframe = self.config["timeframe"]
        self.ig_epic = self.config["ig_epic"]
        self.strategy_config = self.config["config"]
        self.performance_config = self.config["performance"]
        
        # Price history buffer (for swing detection)
        self.lookback = self.strategy_config["lookback"]
        self.price_buffer = deque(maxlen=self.lookback * 3)  # 3x lookback for safety
        
        # Trading state
        self.in_position = False
        self.position_type = None  # "LONG" or "SHORT"
        self.position_deal_id = None
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
        """Fetch latest price from IG"""
        return self.ig.get_market_price(self.ig_epic)
    
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
    
    def calculate_signal_levels(self, swing: Dict) -> Dict:
        """Calculate Log-Fib entry, TP, SL levels from swing point"""
        import math
        
        multiplier = self.strategy_config["multiplier"]
        entry_ratio = self.strategy_config["entry_ratio"]
        tp_ratio = self.strategy_config["take_profit_ratio"]
        sl_ratio = self.strategy_config["stop_loss_ratio"]
        
        if swing["type"] == "HIGH":
            price = swing["high"]
            anchor = swing["low"]
            log_val = math.log10(price)
            range_diff = abs(price - anchor)
            effective_range = log_val * range_diff * multiplier * 4.0
            
            entry = price - (entry_ratio * effective_range)
            tp = price - (tp_ratio * effective_range)
            sl = price + (sl_ratio * effective_range)
            
            return {
                "type": "SHORT",
                "swing_time": swing["time"],
                "swing_price": price,
                "anchor_price": anchor,
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "effective_range": effective_range
            }
        else:  # LOW
            price = swing["low"]
            anchor = swing["high"]
            log_val = math.log10(price)
            range_diff = abs(price - anchor)
            effective_range = log_val * range_diff * multiplier * 4.0
            
            entry = price + (entry_ratio * effective_range)
            tp = price + (tp_ratio * effective_range)
            sl = price - (sl_ratio * effective_range)
            
            return {
                "type": "LONG",
                "swing_time": swing["time"],
                "swing_price": price,
                "anchor_price": anchor,
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "effective_range": effective_range
            }
    
    def check_signal_trigger(self, current_price: float) -> bool:
        """Check if current price triggers entry on active signal"""
        if self.current_signal is None:
            return False
        
        signal = self.current_signal
        
        # Check if price crossed entry level
        if signal["type"] == "SHORT":
            return current_price <= signal["entry"]
        else:  # LONG
            return current_price >= signal["entry"]
    
    def check_exit_conditions(self, price_data: Dict) -> Optional[str]:
        """Check if TP or SL hit for open position"""
        if not self.in_position:
            return None
        
        if self.position_type == "SHORT":
            # Check TP (price went down)
            if price_data["bid"] <= self.position_tp:
                return "TP"
            # Check SL (price went up)
            elif price_data["ask"] >= self.position_sl:
                return "SL"
        else:  # LONG
            # Check TP (price went up)
            if price_data["ask"] >= self.position_tp:
                return "TP"
            # Check SL (price went down)
            elif price_data["bid"] <= self.position_sl:
                return "SL"
        
        return None
    
    def execute_trade(self, signal: Dict, size: float) -> bool:
        """Execute a trade based on signal"""
        direction = "BUY" if signal["type"] == "LONG" else "SELL"
        
        # Place order with stop loss
        result = self.ig.place_order(
            epic=self.ig_epic,
            direction=direction,
            size=size,
            order_type="MARKET",
            stop=signal["sl"]
        )
        
        if result and result.get("success"):
            self.in_position = True
            self.position_type = signal["type"]
            self.position_deal_id = result.get("deal_id", "")
            self.position_entry_price = signal["entry"]
            self.position_tp = signal["tp"]
            self.position_sl = signal["sl"]
            self.trades_today += 1
            self.total_trades += 1
            
            print(f"🎯 TRADE OPENED: {signal['type']} @ {signal['entry']:.5f}")
            print(f"   TP: {signal['tp']:.5f} | SL: {signal['sl']:.5f}")
            return True
        else:
            print(f"❌ Trade execution failed: {result}")
            return False
    
    def close_trade(self, reason: str) -> bool:
        """Close open position"""
        if not self.in_position or not self.position_deal_id:
            return False
        
        direction = "BUY" if self.position_type == "SHORT" else "SELL"
        
        result = self.ig.close_position(
            deal_id=self.position_deal_id,
            epic=self.ig_epic,
            direction=direction,
            size=0.02  # Default 2% of capital
        )
        
        if result and result.get("success"):
            # Update statistics
            if reason == "TP":
                self.total_wins += 1
                print(f"✅ TRADE CLOSED: Take Profit hit!")
            else:
                self.total_losses += 1
                print(f"🛑 TRADE CLOSED: Stop Loss hit!")
            
            # Reset position state
            self.in_position = False
            self.position_type = None
            self.position_deal_id = None
            self.position_entry_price = 0.0
            self.position_tp = 0.0
            self.position_sl = 0.0
            
            return True
        else:
            print(f"❌ Close failed: {result}")
            return False
    
    def run(self, poll_interval: int = 5):
        """Main trading loop"""
        print("="*80)
        print("🚀 LOG-FIB LIVE TRADING AGENT V2 - STARTING")
        print("="*80)
        print(f"Instrument: {self.instrument_name} ({self.timeframe})")
        print(f"IG Epic: {self.ig_epic}")
        print(f"Strategy Config: Lookback={self.lookback}, Multiplier={self.strategy_config['multiplier']}")
        print(f"Expected Performance: Win Rate={self.performance_config['win_rate']}%, PF={self.performance_config['profit_factor']}")
        print(f"Poll Interval: {poll_interval} seconds")
        print("="*80)
        
        # Login to IG
        if not self.ig.login():
            print("❌ Failed to login to IG. Exiting.")
            return
        
        # Get account balance
        balance = self.ig.get_account_balance()
        if balance:
            print(f"💰 Account Balance: ${balance['balance']:.2f} | Available: ${balance['available']:.2f}")
        
        print()
        print("📡 Starting live price monitoring...")
        print()
        
        last_swing_high = None
        last_swing_low = None
        
        try:
            while True:
                # Fetch price
                price_data = self.fetch_price()
                if not price_data:
                    print(f"⚠️  Price fetch failed, retrying in {poll_interval}s...")
                    time.sleep(poll_interval)
                    continue
                
                current_price = price_data["last_traded"]
                timestamp = price_data["timestamp"]
                
                # Update price buffer
                self.update_price_buffer(price_data)
                
                # Check exit conditions first (if in position)
                if self.in_position:
                    exit_reason = self.check_exit_conditions(price_data)
                    if exit_reason:
                        self.close_trade(exit_reason)
                
                # Detect new swings (only if not in position)
                if not self.in_position:
                    swing_high = self.detect_swing_high()
                    swing_low = self.detect_swing_low()
                    
                    # Update signal if new swing detected
                    if swing_high and (last_swing_high is None or swing_high["time"] != last_swing_high["time"]):
                        self.current_signal = self.calculate_signal_levels(swing_high)
                        last_swing_high = swing_high
                        print(f"📉 NEW SHORT SIGNAL DETECTED @ {timestamp}")
                        print(f"   Swing High: {swing_high['high']:.5f}")
                        print(f"   Entry: {self.current_signal['entry']:.5f}")
                        print(f"   TP: {self.current_signal['tp']:.5f} | SL: {self.current_signal['sl']:.5f}")
                    
                    if swing_low and (last_swing_low is None or swing_low["time"] != last_swing_low["time"]):
                        self.current_signal = self.calculate_signal_levels(swing_low)
                        last_swing_low = swing_low
                        print(f"📈 NEW LONG SIGNAL DETECTED @ {timestamp}")
                        print(f"   Swing Low: {swing_low['low']:.5f}")
                        print(f"   Entry: {self.current_signal['entry']:.5f}")
                        print(f"   TP: {self.current_signal['tp']:.5f} | SL: {self.current_signal['sl']:.5f}")
                    
                    # Check if signal triggered
                    if self.current_signal and self.check_signal_trigger(current_price):
                        # Execute trade
                        size = 0.02  # 2% of capital
                        self.execute_trade(self.current_signal, size)
                
                # Log status
                win_rate = (self.total_wins / self.total_trades * 100) if self.total_trades > 0 else 0
                print(f"💹 Price: {current_price:.5f} | Position: {'IN' if self.in_position else 'OUT'} | Trades Today: {self.trades_today} | Win Rate: {win_rate:.1f}%")
                
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            print()
            print("="*80)
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
    # Load IG config from environment or config file
    import os
    from dotenv import load_dotenv
    
    load_dotenv()  # Load .env file if exists
    
    ig_config = {
        "api_key": os.getenv("IG_API_KEY", "YOUR_API_KEY"),
        "username": os.getenv("IG_USERNAME", "YOUR_USERNAME"),
        "password": os.getenv("IG_PASSWORD", "YOUR_PASSWORD"),
        "account_id": os.getenv("IG_ACCOUNT_ID", "YOUR_ACCOUNT_ID"),
        "demo": os.getenv("IG_DEMO", "true").lower() == "true"
    }
    
    # Select instrument from environment variable or default to Gold 5-min
    instrument_choice = os.getenv("IG_INSTRUMENT", "XAUUSD_5MIN")
    
    # Get configuration for selected instrument
    if instrument_choice in ALL_CONFIGS:
        instrument_config = ALL_CONFIGS[instrument_choice]
        print(f"📊 Using configuration: {instrument_choice}")
    else:
        print(f"⚠️  Unknown instrument '{instrument_choice}', using default (XAUUSD_5MIN)")
        instrument_config = ALL_CONFIGS["XAUUSD_5MIN"]
    
    # Create and run agent
    agent = LiveTradingAgent(ig_config, instrument_config=instrument_config)
    agent.run(poll_interval=5)  # Poll every 5 seconds
