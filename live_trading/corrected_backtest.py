"""
═══════════════════════════════════════════════════════════════
NIFTY50 LOG-FIB STRATEGY - CORRECTED BACKTEST
═══════════════════════════════════════════════════════════════

FIXES:
1. Profit factor = gross_profit / gross_loss (not wins/losses)
2. Consistent swing detection logic
3. Proper win/loss tracking based on PnL, not count

This is the HONEST backtest with correct metrics.
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
    """Find swing high: current candle's high > previous lookback candles' highs"""
    if idx < lookback:
        return None
    current_high = candles[idx].high
    for i in range(1, lookback + 1):
        if candles[idx - i].high >= current_high:
            return None
    return current_high


def find_swing_low(idx: int, lookback: int, candles: List[Candle]) -> Optional[float]:
    """Find swing low: current candle's low < previous lookback candles' lows"""
    if idx < lookback:
        return None
    current_low = candles[idx].low
    for i in range(1, lookback + 1):
        if candles[idx - i].low <= current_low:
            return None
    return current_low


def run_backtest(candles: List[Candle], lookback: int, fib_mult: float = 0.786, sl_mult: float = 0.236) -> List[Trade]:
    """
    Run backtest with correct logic:
    
    LONG Setup:
    1. Swing high forms (peak)
    2. Price drops to make swing low (trough)
    3. Price retraces UP to 78.6% of the decline
    4. Enter LONG, target = swing high, stop = swing low - buffer
    
    SHORT Setup:
    1. Swing low forms (trough)
    2. Price rises to make swing high (peak)
    3. Price retraces DOWN to 78.6% of the rise
    4. Enter SHORT, target = swing low, stop = swing high + buffer
    """
    trades = []
    i = lookback
    in_trade = False
    
    while i < len(candles):
        candle = candles[i]
        
        # ===== SHORT SETUP =====
        # Sequence: Swing Low → Swing High → Retrace down to 78.6%
        swing_high = find_swing_high(i, lookback, candles)
        if swing_high and not in_trade:
            # Find the preceding swing low
            swing_low = None
            for j in range(i - 1, max(0, i - lookback * 3), -1):
                low = find_swing_low(j, lookback, candles)
                if low:
                    swing_low = low
                    break
            
            if swing_low and swing_low < swing_high:
                range_size = swing_high - swing_low
                entry_price = swing_low + fib_mult * range_size  # 78.6% retracement
                target = swing_low  # Continue down to original low
                stop_loss = swing_high + range_size * sl_mult  # 23.6% above high
                
                # Check if price touched entry
                if candle.low <= entry_price <= candle.high:
                    entry_date = candle.date
                    in_trade = True
                    trade_direction = 'SHORT'
                    trade_entry = entry_price
                    trade_target = target
                    trade_stop = stop_loss
        
        # ===== LONG SETUP =====
        # Sequence: Swing High → Swing Low → Retrace up to 78.6%
        swing_low = find_swing_low(i, lookback, candles)
        if swing_low and not in_trade:
            # Find the preceding swing high
            swing_high = None
            for j in range(i - 1, max(0, i - lookback * 3), -1):
                high = find_swing_high(j, lookback, candles)
                if high:
                    swing_high = high
                    break
            
            if swing_high and swing_high > swing_low:
                range_size = swing_high - swing_low
                entry_price = swing_low + fib_mult * range_size  # 78.6% retracement
                target = swing_high  # Continue up to original high
                stop_loss = swing_low - range_size * sl_mult  # 23.6% below low
                
                # Check if price touched entry
                if candle.low <= entry_price <= candle.high:
                    entry_date = candle.date
                    in_trade = True
                    trade_direction = 'LONG'
                    trade_entry = entry_price
                    trade_target = target
                    trade_stop = stop_loss
        
        # ===== MANAGE OPEN TRADE =====
        if in_trade:
            if trade_direction == 'SHORT':
                # SHORT: Profit when price goes DOWN to target
                if candle.low <= trade_target:
                    exit_price = trade_target
                    pnl = trade_entry - exit_price  # Positive if entry > exit
                    trades.append(Trade(entry_date, 'SHORT', trade_entry, exit_price, candle.date, pnl))
                    in_trade = False
                elif candle.high >= trade_stop:
                    exit_price = trade_stop
                    pnl = trade_entry - exit_price  # Negative if entry < stop
                    trades.append(Trade(entry_date, 'SHORT', trade_entry, exit_price, candle.date, pnl))
                    in_trade = False
            else:  # LONG
                # LONG: Profit when price goes UP to target
                if candle.high >= trade_target:
                    exit_price = trade_target
                    pnl = exit_price - trade_entry  # Positive if exit > entry
                    trades.append(Trade(entry_date, 'LONG', trade_entry, exit_price, candle.date, pnl))
                    in_trade = False
                elif candle.low <= trade_stop:
                    exit_price = trade_stop
                    pnl = exit_price - trade_entry  # Negative if exit < stop
                    trades.append(Trade(entry_date, 'LONG', trade_entry, exit_price, candle.date, pnl))
                    in_trade = False
        
        i += 1
    
    return trades


def analyze_trades(trades: List[Trade]) -> Dict:
    """Analyze trades with CORRECT metrics"""
    if not trades:
        return {'error': 'No trades'}
    
    # Separate winners and losers by PnL
    winning_trades = [t for t in trades if t.pnl > 0]
    losing_trades = [t for t in trades if t.pnl <= 0]
    
    total_trades = len(trades)
    wins = len(winning_trades)
    losses = len(losing_trades)
    win_rate = wins / total_trades * 100
    
    # PnL calculations
    total_pnl = sum(t.pnl for t in trades)
    avg_pnl = total_pnl / total_trades
    
    # CORRECT Profit Factor: gross profit / gross loss
    gross_profit = sum(t.pnl for t in winning_trades)
    gross_loss = abs(sum(t.pnl for t in losing_trades))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Drawdown
    peak = 0
    max_drawdown = 0
    cumulative = 0
    for t in trades:
        cumulative += t.pnl
        if cumulative > peak:
            peak = cumulative
        drawdown = peak - cumulative
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    # Streaks
    best_win_streak = 0
    max_loss_streak = 0
    current_win = 0
    current_loss = 0
    for t in trades:
        if t.pnl > 0:
            current_win += 1
            current_loss = 0
            best_win_streak = max(best_win_streak, current_win)
        else:
            current_loss += 1
            current_win = 0
            max_loss_streak = max(max_loss_streak, current_loss)
    
    # Direction breakdown
    long_trades = [t for t in trades if t.direction == 'LONG']
    short_trades = [t for t in trades if t.direction == 'SHORT']
    long_wins = sum(1 for t in long_trades if t.pnl > 0)
    short_wins = sum(1 for t in short_trades if t.pnl > 0)
    
    return {
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'avg_pnl': avg_pnl,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'best_win_streak': best_win_streak,
        'max_loss_streak': max_loss_streak,
        'long_trades': len(long_trades),
        'short_trades': len(short_trades),
        'long_wins': long_wins,
        'short_wins': short_wins,
        'long_wr': long_wins / len(long_trades) * 100 if long_trades else 0,
        'short_wr': short_wins / len(short_trades) * 100 if short_trades else 0
    }


def main():
    print("="*80)
    print("🧪 NIFTY50 LOG-FIB STRATEGY - CORRECTED BACKTEST")
    print("="*80)
    print()
    print("FIXES APPLIED:")
    print("  1. Profit Factor = Gross Profit / Gross Loss (not wins/losses)")
    print("  2. Win/Loss determined by PnL sign (not trade count)")
    print("  3. Consistent swing detection logic")
    print()
    
    # Load data
    data_file = 'zerodha_data/NIFTY_50_5minute_20260319_20260518.csv'
    candles = load_data(data_file)
    print(f"📁 Loaded {len(candles)} candles from {data_file}")
    print(f"   Range: {candles[0].date} to {candles[-1].date}")
    print(f"   Price: {min(c.low for c in candles):.2f} - {max(c.high for c in candles):.2f}")
    print()
    
    # Test multiple configurations
    configs = [
        {'lookback': 5, 'fib': 0.786},
        {'lookback': 10, 'fib': 0.786},
        {'lookback': 15, 'fib': 0.786},
        {'lookback': 10, 'fib': 0.618},
        {'lookback': 10, 'fib': 0.705},
        {'lookback': 10, 'fib': 0.886},
    ]
    
    print("="*80)
    print("📊 PARAMETER COMPARISON")
    print("="*80)
    
    results = []
    for cfg in configs:
        trades = run_backtest(candles, cfg['lookback'], cfg['fib'])
        metrics = analyze_trades(trades)
        
        if 'error' not in metrics:
            results.append({**cfg, **metrics})
            print(f"\nLookback={cfg['lookback']}, Fib={cfg['fib']:.3f}:")
            print(f"   Trades: {metrics['total_trades']} (L:{metrics['long_trades']} / S:{metrics['short_trades']})")
            print(f"   Win Rate: {metrics['win_rate']:.2f}% (L:{metrics['long_wr']:.1f}% / S:{metrics['short_wr']:.1f}%)")
            print(f"   PnL: {metrics['total_pnl']:+.2f} pts")
            print(f"   Avg PnL: {metrics['avg_pnl']:+.2f} pts/trade")
            print(f"   Profit Factor: {metrics['profit_factor']:.2f}")
            print(f"   Max DD: {metrics['max_drawdown']:.2f} pts")
    
    # Find best by profit factor
    if results:
        best_pf = max(results, key=lambda x: x['profit_factor'] if x['profit_factor'] != float('inf') else 0)
        best_wr = max(results, key=lambda x: x['win_rate'])
        best_pnl = max(results, key=lambda x: x['total_pnl'])
        
        print("\n" + "="*80)
        print("🏆 BEST CONFIGURATIONS")
        print("="*80)
        print(f"Best Profit Factor: LB={best_pf['lookback']}, Fib={best_pf['fib']:.3f} → PF={best_pf['profit_factor']:.2f}")
        print(f"Best Win Rate:      LB={best_wr['lookback']}, Fib={best_wr['fib']:.3f} → WR={best_wr['win_rate']:.2f}%")
        print(f"Best PnL:           LB={best_pnl['lookback']}, Fib={best_pnl['fib']:.3f} → PnL={best_pnl['total_pnl']:+.2f} pts")
        
        # Save results
        with open('corrected_backtest_results.json', 'w') as f:
            json.dump([{k: v for k, v in r.items() if k not in ['gross_profit', 'gross_loss']} for r in results], f, indent=2)
        print(f"\n💾 Saved to: corrected_backtest_results.json")
    
    print("\n" + "="*80)
    print("⚖️  HONEST VERDICT")
    print("="*80)
    
    # Check if any config achieves >70% WR with PF > 1.5
    viable = [r for r in results if r['win_rate'] >= 70 and r['profit_factor'] >= 1.5]
    
    if viable:
        print("✅ STRATEGY VIABLE - Multiple configurations profitable")
        best = max(viable, key=lambda x: x['profit_factor'])
        print(f"   Recommended: LB={best['lookback']}, Fib={best['fib']:.3f}")
        print(f"   Expected WR: {best['win_rate']:.1f}%, PF: {best['profit_factor']:.2f}")
    else:
        print("❌ STRATEGY NOT VIABLE - No configuration meets thresholds")
        print("   Required: WR ≥ 70%, PF ≥ 1.5")
        if results:
            best = max(results, key=lambda x: x['profit_factor'] if x['profit_factor'] != float('inf') else 0)
            print(f"   Best found: LB={best['lookback']}, Fib={best['fib']:.3f}")
            print(f"   Actual: WR={best['win_rate']:.1f}%, PF={best['profit_factor']:.2f}")
    
    print("="*80)


if __name__ == "__main__":
    main()
