"""
Simple test to verify swing detection logic
"""

from collections import deque
from datetime import datetime, timedelta

# Simple swing detector
class SwingDetector:
    def __init__(self, lookback=10):
        self.lookback = lookback
        self.buffer = deque(maxlen=lookback * 3)
    
    def detect_swing_high(self, idx):
        if idx < self.lookback or idx >= len(self.buffer) - self.lookback:
            return False
        
        current_high = self.buffer[idx]["high"]
        
        for j in range(idx - self.lookback, idx + self.lookback + 1):
            if j != idx and self.buffer[j]["high"] >= current_high:
                return False
        
        return True
    
    def detect_swing_low(self, idx):
        if idx < self.lookback or idx >= len(self.buffer) - self.lookback:
            return False
        
        current_low = self.buffer[idx]["low"]
        
        for j in range(idx - self.lookback, idx + self.lookback + 1):
            if j != idx and self.buffer[j]["low"] <= current_low:
                return False
        
        return True

# Create test data with OBVIOUS swings
print("Creating test data with clear swing patterns...\n")

buffer = []

# Uptrend creating swing high at index 20
for i in range(20):
    buffer.append({
        "high": 22400 + i * 10,
        "low": 22390 + i * 10,
    })

# Downtrend creating swing low at index 40
for i in range(20, 40):
    buffer.append({
        "high": 22600 - (i-20) * 15,
        "low": 22590 - (i-20) * 15,
    })

# Uptrend again
for i in range(40, 60):
    buffer.append({
        "high": 22300 + (i-40) * 12,
        "low": 22290 + (i-40) * 12,
    })

# Add timestamps
for i, candle in enumerate(buffer):
    candle["timestamp"] = (datetime(2026, 5, 18, 9, 15) + timedelta(minutes=5*i)).isoformat()
    candle["close"] = (candle["high"] + candle["low"]) / 2

print(f"Created {len(buffer)} candles")
print(f"Price range: {min(c['low'] for c in buffer):.2f} - {max(c['high'] for c in buffer):.2f}\n")

# Test swing detection
detector = SwingDetector(lookback=10)
detector.buffer = deque(buffer)

print("Detecting swings with lookback=10:\n")

for i in range(len(buffer)):
    if detector.detect_swing_high(i):
        print(f"✓ Candle {i}: SWING HIGH @ {buffer[i]['high']:.2f}")
    if detector.detect_swing_low(i):
        print(f"✓ Candle {i}: SWING LOW @ {buffer[i]['low']:.2f}")

print("\n" + "="*80)

# Now test Fib calculation
print("\nCalculating Fibonacci levels:\n")

# Find the first swing high and low
swing_high_idx = None
swing_low_idx = None

for i in range(len(buffer)):
    if detector.detect_swing_high(i) and swing_high_idx is None:
        swing_high_idx = i
    if detector.detect_swing_low(i) and swing_low_idx is None:
        swing_low_idx = i

if swing_high_idx and swing_low_idx:
    high = buffer[swing_high_idx]["high"]
    low = buffer[swing_low_idx]["low"]
    range_size = high - low
    
    entry = low + (range_size * 0.786)
    tp = high
    sl = low - (range_size * 0.236)
    
    print(f"Swing High: {high:.2f} (candle {swing_high_idx})")
    print(f"Swing Low:  {low:.2f} (candle {swing_low_idx})")
    print(f"Range: {range_size:.2f} points")
    print(f"\nFibonacci Levels:")
    print(f"  Entry (78.6%): {entry:.2f}")
    print(f"  TP (100%):     {tp:.2f}")
    print(f"  SL (-23.6%):   {sl:.2f}")
    print(f"\nRisk/Reward: 1:{(tp-entry)/(entry-sl):.2f}")
    
    # Check if price would trigger
    print(f"\nChecking for trigger...")
    for i in range(max(swing_high_idx, swing_low_idx), len(buffer)):
        current = buffer[i]["close"]
        if current <= entry * 1.002 and current >= low * 1.001:
            print(f"  ✓ TRIGGER at candle {i}: price={current:.2f}, entry={entry:.2f}")
            break
    else:
        print(f"  ✗ No trigger - price never retraced to entry level")
        print(f"     Entry: {entry:.2f}")
        print(f"     Price range after swing: {min(buffer[max(swing_high_idx, swing_low_idx):], key=lambda x: x['close'])['close']:.2f} - {max(buffer[max(swing_high_idx, swing_low_idx):], key=lambda x: x['close'])['close']:.2f}")

else:
    print("No swings detected!")
