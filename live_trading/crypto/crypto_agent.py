"""
═══════════════════════════════════════════════════════════════
CRYPTO LIVE TRADING AGENT (Gate.io)
═══════════════════════════════════════════════════════════════

Real-time trading agent for crypto markets using Gate.io API.
Supports BTC, ETH, and all future crypto pairs.
"""

import time
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from collections import deque

from gate_client import GateIOClient

# Import multi-instrument configs (includes crypto)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_instrument_config import ALL_CONFIGS, CRYPTO_CONFIGS

class CryptoTradingAgent:
    def __init__(self, gate_config: Dict[str, str], instrument_config: Dict):
        """
        Initialize Crypto Trading Agent
        
        gate_config: Gate.io API credentials
        instrument_config: Configuration for specific crypto instrument
        """
        self.gate = GateIOClient(gate_config)
        self.config = instrument_config
        self.instrument_name = self.config["instrument"]
        self.timeframe = self.config["timeframe"]
        self.currency_pair = self.config["gate_pair"]  # e.g., "BTC_USDT"
        self.strategy_config = self.config["config"]
        self.performance_config = self.config["performance"]
        
        # Price history buffer
        self.lookback = self.strategy_config["lookback"]
        self.price_buffer = deque(maxlen=self.lookback * 3)
        
        # Trading state
        self.in_position = False
        self.position_type = None
        self.position_order_id = None
        self.position_entry_price = 0.0
        self.position_tp = 0.0
        self.position_sl = 0.0
        self.position_amount = 0.0
        
        # Statistics
        self.trades_today = 0
        self.total_trades = 0
        self.total_wins = 0
        self.total_losses = 0
        self.total_pnl = 0.0
        
        # Signal levels
        self.current_signal = None
        
    def fetch_candles(self, interval: str = "5m", limit: int = 200) -> Optional[List[Dict]]:
        """Fetch candlestick data from Gate.io"""
        return self.gate.get_candles(self.currency_pair, interval=interval, limit=limit)
    
    def update_price_buffer(self, candles: List[Dict]):
        """Add candles to buffer for swing detection"""
        for candle in candles[-self.lookback * 3:]:
            self.price_buffer.append({
                "time": candle["time"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"]
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
                    "low": buffer[i]["low"]
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
                    "high": buffer[i]["high"]
                }
        
        return None
    
    def calculate_signal_levels(self, swing: Dict) -> Dict:
        """Calculate Log-Fib entry, TP, SL levels"""
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
        else:
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
        """Check if price triggers entry"""
        if self.current_signal is None:
            return False
        
        signal = self.current_signal
        if signal["type"] == "SHORT":
            return current_price <= signal["entry"]
        else:
            return current_price >= signal["entry"]
    
    def check_exit_conditions(self, current_price: float) -> Optional[str]:
        """Check if TP or SL hit"""
        if not self.in_position:
            return None
        
        if self.position_type == "SHORT":
            if current_price <= self.position_tp:
                return "TP"
            elif current_price >= self.position_sl:
                return "SL"
        else:
            if current_price >= self.position_tp:
                return "TP"
            elif current_price <= self.position_sl:
                return "SL"
        
        return None
    
    def execute_trade(self, signal: Dict, usdt_amount: float) -> bool:
        """Execute trade based on signal"""
        current_price = signal["entry"]
        amount = usdt_amount / current_price  # Convert USDT to base currency
        
        direction = "buy" if signal["type"] == "LONG" else "sell"
        
        result = self.gate.place_order(
            currency_pair=self.currency_pair,
            side=direction,
            amount=amount,
            order_type="market"
        )
        
        if result and result.get("success"):
            self.in_position = True
            self.position_type = signal["type"]
            self.position_order_id = result.get("order_id", "")
            self.position_entry_price = signal["entry"]
            self.position_tp = signal["tp"]
            self.position_sl = signal["sl"]
            self.position_amount = amount
            self.trades_today += 1
            self.total_trades += 1
            
            print(f"🎯 TRADE OPENED: {signal['type']} {self.instrument_name} @ {signal['entry']:.5f}")
            print(f"   Amount: {amount:.6f} | TP: {signal['tp']:.5f} | SL: {signal['sl']:.5f}")
            return True
        else:
            print(f"❌ Trade execution failed: {result}")
            return False
    
    def close_trade(self, reason: str) -> bool:
        """Close open position"""
        if not self.in_position or self.position_amount <= 0:
            return False
        
        direction = "sell" if self.position_type == "LONG" else "buy"
        
        result = self.gate.place_order(
            currency_pair=self.currency_pair,
            side=direction,
            amount=self.position_amount,
            order_type="market"
        )
        
        if result and result.get("success"):
            # Calculate P&L (simplified)
            if self.position_type == "LONG":
                pnl = (result.get("price", 0) - self.position_entry_price) * self.position_amount
            else:
                pnl = (self.position_entry_price - result.get("price", 0)) * self.position_amount
            
            self.total_pnl += pnl
            
            if reason == "TP":
                self.total_wins += 1
                print(f"✅ TRADE CLOSED: Take Profit hit! P&L: +${pnl:.2f}")
            else:
                self.total_losses += 1
                print(f"🛑 TRADE CLOSED: Stop Loss hit! P&L: ${pnl:.2f}")
            
            self.in_position = False
            self.position_type = None
            self.position_order_id = None
            self.position_entry_price = 0.0
            self.position_tp = 0.0
            self.position_sl = 0.0
            self.position_amount = 0.0
            
            return True
        else:
            print(f"❌ Close failed: {result}")
            return False
    
    def run(self, poll_interval: int = 30):
        """Main trading loop"""
        print("="*80)
        print("🚀 CRYPTO LIVE TRADING AGENT (Gate.io) - STARTING")
        print("="*80)
        print(f"Instrument: {self.instrument_name} ({self.timeframe})")
        print(f"Gate.io Pair: {self.currency_pair}")
        print(f"Strategy Config: Lookback={self.lookback}, Multiplier={self.strategy_config['multiplier']}")
        print(f"Expected Performance: Win Rate={self.performance_config['win_rate']}%, PF={self.performance_config['profit_factor']}")
        print(f"Poll Interval: {poll_interval} seconds")
        print("="*80)
        
        # Test connection
        if not self.gate.test_connection():
            print("❌ Failed to connect to Gate.io. Exiting.")
            return
        
        # Get account balance
        balance = self.gate.get_account_balance()
        if balance:
            print(f"💰 Account Balance: ${balance['total_usdt']:.2f} USDT")
        
        print()
        print("📡 Starting live candlestick monitoring...")
        print()
        
        last_swing_high = None
        last_swing_low = None
        
        try:
            while True:
                # Fetch candles
                candles = self.fetch_candles(interval=self.timeframe, limit=200)
                if not candles:
                    print(f"⚠️  Candle fetch failed, retrying in {poll_interval}s...")
                    time.sleep(poll_interval)
                    continue
                
                current_price = candles[-1]["close"]
                timestamp = candles[-1]["time"]
                
                # Update price buffer
                self.update_price_buffer(candles)
                
                # Check exit conditions first
                if self.in_position:
                    exit_reason = self.check_exit_conditions(current_price)
                    if exit_reason:
                        self.close_trade(exit_reason)
                
                # Detect new swings (only if not in position)
                if not self.in_position:
                    swing_high = self.detect_swing_high()
                    swing_low = self.detect_swing_low()
                    
                    if swing_high and (last_swing_high is None or swing_high["time"] != last_swing_high["time"]):
                        self.current_signal = self.calculate_signal_levels(swing_high)
                        last_swing_high = swing_high
                        print(f"📉 NEW SHORT SIGNAL: {self.instrument_name} @ {timestamp}")
                        print(f"   Swing High: {swing_high['high']:.5f}")
                        print(f"   Entry: {self.current_signal['entry']:.5f}")
                        print(f"   TP: {self.current_signal['tp']:.5f} | SL: {self.current_signal['sl']:.5f}")
                    
                    if swing_low and (last_swing_low is None or swing_low["time"] != last_swing_low["time"]):
                        self.current_signal = self.calculate_signal_levels(swing_low)
                        last_swing_low = swing_low
                        print(f"📈 NEW LONG SIGNAL: {self.instrument_name} @ {timestamp}")
                        print(f"   Swing Low: {swing_low['low']:.5f}")
                        print(f"   Entry: {self.current_signal['entry']:.5f}")
                        print(f"   TP: {self.current_signal['tp']:.5f} | SL: {self.current_signal['sl']:.5f}")
                    
                    if self.current_signal and self.check_signal_trigger(current_price):
                        if self.trades_today >= 50:
                            print(f"⚠️  Daily trade limit reached ({self.trades_today}/50)")
                        else:
                            usdt_amount = balance['total_usdt'] * 0.02  # 2% per trade
                            self.execute_trade(self.current_signal, usdt_amount)
                
                # Log status
                win_rate = (self.total_wins / self.total_trades * 100) if self.total_trades > 0 else 0
                print(f"💹 Price: {current_price:.5f} | Position: {'IN' if self.in_position else 'OUT'} | Trades: {self.trades_today} | Win Rate: {win_rate:.1f}% | Total P&L: ${self.total_pnl:.2f}")
                
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            print()
            print("="*80)
            print("🛑 Trading agent stopped by user")
            print("="*80)
            print(f"Total Trades: {self.total_trades}")
            print(f"Wins: {self.total_wins} | Losses: {self.total_losses}")
            print(f"Win Rate: {win_rate:.1f}%")
            print(f"Total P&L: ${self.total_pnl:.2f}")
            print("="*80)
        
        except Exception as e:
            print(f"❌ Critical error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    gate_config = {
        "api_key": os.getenv("GATE_API_KEY", "YOUR_API_KEY"),
        "api_secret": os.getenv("GATE_API_SECRET", "YOUR_API_SECRET"),
        "demo": False
    }
    
    # Select crypto instrument
    instrument_choice = os.getenv("CRYPTO_INSTRUMENT", "BTCUSDT_5MIN")
    
    if instrument_choice in CRYPTO_CONFIGS:
        instrument_config = CRYPTO_CONFIGS[instrument_choice]
        print(f"📊 Using configuration: {instrument_choice}")
    else:
        print(f"⚠️  Unknown instrument '{instrument_choice}', using default (BTCUSDT_5MIN)")
        instrument_config = CRYPTO_CONFIGS["BTCUSDT_5MIN"]
    
    agent = CryptoTradingAgent(gate_config, instrument_config=instrument_config)
    agent.run(poll_interval=30)
