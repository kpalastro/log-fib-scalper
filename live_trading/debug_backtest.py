"""
Debug script to verify backtest logic and investigate the walk-forward discrepancy
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Candle:
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass  
class Trade:
    entry_date: datetime
    direction: str
    entry_price: float
    exit_price: float
    exit_date: datetime
    pnl: float
    won: bool


def load_data(filepath: str) -> List[Candle]:
    candles = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            candles.append(Candle(
                date=datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S'),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row['volume'])
            ))
    return candles


def find_swing_high(idx: int, lookback: int, candles: List[Candle]) -> Optional[float]:
    if idx < lookback:
        return None
    current_high = candles[idx].high
    for i in range(1, lookback + 1):
        if candles[idx - i].high >= current_high:
            return None
    return current_high


def find_swing_low(idx: int, lookback: int, candles: List[Candle]) -> Optional[float]:
    if idx < lookback:
        return None
    current_low = candles[idx].low
    for i in range(1, lookback + 1):
        if candles[idx - i].low <= current_low:
            return None
    return current_low


def run_backtest(candles: List[Candle], lookback: int, fib_mult: float = 0.786, verbose: bool = False) -> List[Trade]:
    trades = []
    i = lookback
    in_trade = False
    
    while i < len(candles):
        candle = candles[i]
        
        # Check for swing high (SHORT setup)
        swing_high = find_swing_high(i, lookback, candles)
        if swing_high and not in_trade:
            swing_low = None
            for j in range(i - 1, max(0, i - lookback * 3), -1):
                low = find_swing_low(j, lookback, candles)
                if low:
                    swing_low = low
                    break
            
            if swing_low and swing_low < swing_high:
                range_size = swing_high - swing_low
                entry_price = swing_low + fib_mult * range_size
                target = swing_low  # Continue down
                stop_loss = swing_high + range_size * 0.236
                
                if candle.low <= entry_price <= candle.high:
                    entry_date = candle.date
                    in_trade = True
                    trade_direction = 'SHORT'
                    trade_entry = entry_price
                    trade_target = target
                    trade_stop = stop_loss
                    
                    if verbose:
                        print(f"  SHORT setup @ {entry_date}: Entry={entry_price:.0f}, Target={target:.0f}, Stop={stop_loss:.0f}")
        
        # Check for swing low (LONG setup)
        swing_low = find_swing_low(i, lookback, candles)
        if swing_low and not in_trade:
            swing_high = None
            for j in range(i - 1, max(0, i - lookback * 3), -1):
                high = find_swing_high(j, lookback, candles)
                if high:
                    swing_high = high
                    break
            
            if swing_high and swing_high > swing_low:
                range_size = swing_high - swing_low
                entry_price = swing_low + fib_mult * range_size
                target = swing_high  # Continue up
                stop_loss = swing_low - range_size * 0.236
                
                if candle.low <= entry_price <= candle.high:
                    entry_date = candle.date
                    in_trade = True
                    trade_direction = 'LONG'
                    trade_entry = entry_price
                    trade_target = target
                    trade_stop = stop_loss
                    
                    if verbose:
                        print(f"  LONG setup @ {entry_date}: Entry={entry_price:.0f}, Target={target:.0f}, Stop={stop_loss:.0f}")
        
        # Manage open trade
        if in_trade:
            if trade_direction == 'SHORT':
                if candle.low <= trade_target:
                    exit_price = trade_target
                    pnl = trade_entry - exit_price
                    trades.append(Trade(
                        entry_date=entry_date, direction='SHORT',
                        entry_price=trade_entry, exit_price=exit_price,
                        exit_date=candle.date, pnl=pnl, won=True
                    ))
                    in_trade = False
                elif candle.high >= trade_stop:
                    exit_price = trade_stop
                    pnl = trade_entry - exit_price
                    trades.append(Trade(
                        entry_date=entry_date, direction='SHORT',
                        entry_price=trade_entry, exit_price=exit_price,
                        exit_date=candle.date, pnl=pnl, won=False
                    ))
                    in_trade = False
            else:  # LONG
                if candle.high >= trade_target:
                    exit_price = trade_target
                    pnl = exit_price - trade_entry
                    trades.append(Trade(
                        entry_date=entry_date, direction='LONG',
                        entry_price=trade_entry, exit_price=exit_price,
                        exit_date=candle.date, pnl=pnl, won=True
                    ))
                    in_trade = False
                elif candle.low <= trade_stop:
                    exit_price = trade_stop
                    pnl = exit_price - trade_entry
                    trades.append(Trade(
                        entry_date=entry_date, direction='LONG',
                        entry_price=trade_entry, exit_price=exit_price,
                        exit_date=candle.date, pnl=pnl, won=False
                    ))
                    in_trade = False
        
        i += 1
    
    return trades


def analyze(trades: List[Trade]) -> Dict:
    if not trades:
        return {'error': 'No trades'}
    
    wins = [t for t in trades if t.won]
    losses = [t for t in trades if not t.won]
    
    return {
        'total_trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': len(wins) / len(trades) * 100,
        'total_pnl': sum(t.pnl for t in trades),
        'avg_pnl': sum(t.pnl for t in trades) / len(trades),
        'profit_factor': sum(t.pnl for t in wins) / abs(sum(t.pnl for t in losses)) if sum(t.pnl for t in losses) != 0 else float('inf')
    }


def main():
    print("="*80)
    print("🔍 DEBUG: Verifying Backtest Logic")
    print("="*80)
    
    # Load full data
    candles = load_data('zerodha_data/NIFTY_50_5minute_20260319_20260518.csv')
    print(f"\n✅ Loaded {len(candles)} candles")
    print(f"   Range: {candles[0].date} to {candles[-1].date}")
    
    # Test on different periods
    print("\n" + "="*80)
    print("📊 TESTING ON DIFFERENT TIME PERIODS")
    print("="*80)
    
    periods = {
        'Full (Mar 19 - May 18)': (None, None),
        'Period 1 (Mar 19 - Apr 10)': (datetime(2026, 3, 19), datetime(2026, 4, 10)),
        'Period 2 (Apr 11 - Apr 24)': (datetime(2026, 4, 11), datetime(2026, 4, 24)),
        'Period 3 (Apr 25 - May 7)': (datetime(2026, 4, 25), datetime(2026, 5, 7)),
        'Period 4 (May 8 - May 18)': (datetime(2026, 5, 8), datetime(2026, 5, 18)),
    }
    
    results = {}
    for name, (start, end) in periods.items():
        if start and end:
            period_candles = [c for c in candles if start <= c.date < end]
        else:
            period_candles = candles
        
        if len(period_candles) < 50:
            continue
        
        trades = run_backtest(period_candles, lookback=10, fib_mult=0.786)
        metrics = analyze(trades)
        results[name] = metrics
        
        if 'error' not in metrics:
            print(f"\n{name}:")
            print(f"   Candles: {len(period_candles)}")
            print(f"   Trades: {metrics['total_trades']}")
            print(f"   Win Rate: {metrics['win_rate']:.2f}%")
            print(f"   PnL: {metrics['total_pnl']:+.2f} pts")
            print(f"   Profit Factor: {metrics['profit_factor']:.2f}")
        else:
            print(f"\n{name}: ❌ No trades")
    
    # Detailed analysis of worst period
    print("\n" + "="*80)
    print("🔬 DEEP DIVE: Period 3 (Walk-Forward Test Period)")
    print("="*80)
    
    start = datetime(2026, 4, 25)
    end = datetime(2026, 5, 7)
    period3 = [c for c in candles if start <= c.date < end]
    
    print(f"\nCandles: {len(period3)}")
    print(f"Price range: {min(c.low for c in period3):.2f} - {max(c.high for c in period3):.2f}")
    
    # Run with verbose output
    print("\n📝 First 20 trades:")
    trades = run_backtest(period3, lookback=10, fib_mult=0.786, verbose=True)
    
    print(f"\n📊 Results:")
    metrics = analyze(trades)
    if 'error' not in metrics:
        print(f"   Trades: {metrics['total_trades']}")
        print(f"   Win Rate: {metrics['win_rate']:.2f}%")
        print(f"   PnL: {metrics['total_pnl']:+.2f} pts")
        
        # Show trade distribution
        print(f"\n📝 Trade breakdown:")
        long_trades = [t for t in trades if t.direction == 'LONG']
        short_trades = [t for t in trades if t.direction == 'SHORT']
        long_wins = sum(1 for t in long_trades if t.won)
        short_wins = sum(1 for t in short_trades if t.won)
        
        print(f"   LONG: {len(long_trades)} trades, {long_wins} wins ({long_wins/len(long_trades)*100:.1f}% if long_trades else 0)")
        print(f"   SHORT: {len(short_trades)} trades, {short_wins} wins ({short_wins/len(short_trades)*100:.1f}% if short_trades else 0)")
    
    # Save detailed results
    with open('debug_period_analysis.json', 'w') as f:
        json.dump({k: {kk: vv for kk, vv in v.items() if kk != 'error'} for k, v in results.items()}, f, indent=2)
    print(f"\n💾 Saved to: debug_period_analysis.json")


if __name__ == "__main__":
    main()
