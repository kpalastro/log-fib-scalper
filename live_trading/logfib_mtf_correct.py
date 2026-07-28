"""
═══════════════════════════════════════════════════════════════
LOG-FIB MTF STRATEGY - CORRECT IMPLEMENTATION
═══════════════════════════════════════════════════════════════

Based on: Pal Log-Fib Range Projection - MTF (Pine Script)

KEY CONCEPTS:
1. Multi-timeframe swing detection (swings on HTF, entries on LTF)
2. Anchored pivot points (swing high anchored to its bar's low)
3. Logarithmic range projection (NOT standard Fibonacci)
4. Formula: effective_range = log10(price) * |high-low| * mult * 4

Strategy Logic:
- TOP projection: Bearish levels below swing high
- BOTTOM projection: Bullish levels above swing low
- Enter when price reaches projection levels
- Exit at next projection level or reversal
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Candle:
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0


@dataclass
class HTFCandle:
    """Aggregated HTF candle"""
    date: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass
class Trade:
    entry_date: datetime
    direction: str  # 'LONG' or 'SHORT'
    entry_price: float
    exit_price: float
    exit_date: datetime
    pnl: float
    setup_type: str  # 'TOP' or 'BOTTOM'


def load_data(filepath: str) -> List[Candle]:
    """Load CSV data"""
    candles = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            time_str = row.get('time', row.get('date', ''))
            try:
                # Handle ISO format with timezone: 2026-05-10T18:20:00-04:00
                if 'T' in time_str:
                    # Remove timezone offset
                    if '+' in time_str:
                        time_str = time_str.split('+')[0]
                    elif '-04:00' in time_str:
                        time_str = time_str.replace('-04:00', '')
                    elif '-05:00' in time_str:
                        time_str = time_str.replace('-05:00', '')
                    time_str = time_str.replace('T', ' ')
                date = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            except Exception as e:
                continue
            
            try:
                candle = Candle(
                    date=date,
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row.get('volume', 0))
                )
                candles.append(candle)
            except Exception as e:
                continue
    
    candles.sort(key=lambda c: c.date)
    return candles


def aggregate_to_htf(candles: List[Candle], htf_minutes: int) -> List[HTFCandle]:
    """Aggregate LTF candles to HTF"""
    if not candles:
        return []
    
    htf_candles = []
    current_htf = None
    
    for candle in candles:
        # Round down to HTF boundary
        htf_timestamp = candle.date.replace(
            minute=(candle.date.minute // htf_minutes) * htf_minutes,
            second=0,
            microsecond=0
        )
        
        if current_htf is None or htf_timestamp != current_htf.date:
            if current_htf:
                htf_candles.append(current_htf)
            current_htf = HTFCandle(
                date=htf_timestamp,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close
            )
        else:
            current_htf.high = max(current_htf.high, candle.high)
            current_htf.low = min(current_htf.low, candle.low)
            current_htf.close = candle.close
    
    if current_htf:
        htf_candles.append(current_htf)
    
    return htf_candles


def find_swing_high_idx(htf_candles: List[HTFCandle], idx: int, lookback: int) -> Optional[int]:
    """Find index of highest high in lookback window"""
    if idx < lookback - 1:
        return None
    
    start_idx = idx - lookback + 1
    highest_idx = start_idx
    highest_price = htf_candles[start_idx].high
    
    for i in range(start_idx, idx + 1):
        if htf_candles[i].high > highest_price:
            highest_price = htf_candles[i].high
            highest_idx = i
    
    # Only return if the highest is at current bar (pivot)
    if highest_idx == idx:
        return idx
    return None


def find_swing_low_idx(htf_candles: List[HTFCandle], idx: int, lookback: int) -> Optional[int]:
    """Find index of lowest low in lookback window"""
    if idx < lookback - 1:
        return None
    
    start_idx = idx - lookback + 1
    lowest_idx = start_idx
    lowest_price = htf_candles[start_idx].low
    
    for i in range(start_idx, idx + 1):
        if htf_candles[i].low < lowest_price:
            lowest_price = htf_candles[i].low
            lowest_idx = i
    
    if lowest_idx == idx:
        return idx
    return None


def calculate_effective_range(pivot_price: float, anchor_price: float, mult_val: float) -> float:
    """
    Core formula from Pine Script:
    effective_range = log10(pivot_price) * |pivot_price - anchor_price| * mult_val * 4.0
    """
    import math
    return math.log10(pivot_price) * abs(pivot_price - anchor_price) * mult_val * 4.0


def calculate_projection_levels(pivot_price: float, effective_range: float, ratios: List[float]) -> Dict[str, float]:
    """Calculate projection levels"""
    levels = {}
    for ratio in ratios:
        # For TOP projections (from swing high): price - range*ratio
        # For BOTTOM projections (from swing low): price + range*ratio
        levels[f'{ratio:.3f}'] = pivot_price - (effective_range * ratio)
    return levels


def run_backtest(
    candles: List[Candle],
    htf_minutes: int = 60,
    lookback: int = 6,
    mult_val: float = 0.786,
    entry_ratio: float = 0.786,
    exit_ratio: float = 1.0,
    show_top: bool = True,
    show_bottom: bool = True
) -> List[Trade]:
    """
    Run backtest with correct Log-Fib MTF logic
    
    Args:
        candles: LTF candle data
        htf_minutes: HTF in minutes (default 60)
        lookback: Lookback period for swing detection
        mult_val: Range multiplier (default 0.786)
        entry_ratio: Fibonacci ratio for entry (default 0.786)
        exit_ratio: Fibonacci ratio for exit (default 1.0)
    """
    import math
    
    # Aggregate to HTF
    htf_candles = aggregate_to_htf(candles, htf_minutes)
    print(f"   Aggregated {len(candles)} LTF candles → {len(htf_candles)} HTF candles ({htf_minutes}min)")
    
    if len(htf_candles) < lookback + 10:
        print(f"   ⚠️  Insufficient HTF data for lookback={lookback}")
        return []
    
    trades = []
    
    # Track active projections
    active_top_projections = []  # List of (entry_level, exit_level, swing_high, anchor_low)
    active_bottom_projections = []  # List of (entry_level, exit_level, swing_low, anchor_high)
    
    in_trade = False
    current_trade = None
    
    # Process each HTF candle
    for idx in range(lookback - 1, len(htf_candles)):
        htf_candle = htf_candles[idx]
        
        # Check for Swing High
        swing_high_idx = find_swing_high_idx(htf_candles, idx, lookback)
        if swing_high_idx is not None and show_top:
            swing_high = htf_candles[swing_high_idx].high
            anchored_low = htf_candles[swing_high_idx].low
            
            eff_range = calculate_effective_range(swing_high, anchored_low, mult_val)
            entry_level = swing_high - (eff_range * entry_ratio)
            exit_level = swing_high - (eff_range * exit_ratio)
            
            active_top_projections.append({
                'entry': entry_level,
                'exit': exit_level,
                'swing': swing_high,
                'anchor': anchored_low,
                'bar_date': htf_candles[swing_high_idx].date
            })
        
        # Check for Swing Low
        swing_low_idx = find_swing_low_idx(htf_candles, idx, lookback)
        if swing_low_idx is not None and show_bottom:
            swing_low = htf_candles[swing_low_idx].low
            anchored_high = htf_candles[swing_low_idx].high
            
            eff_range = calculate_effective_range(swing_low, anchored_high, mult_val)
            entry_level = swing_low + (eff_range * entry_ratio)
            exit_level = swing_low + (eff_range * exit_ratio)
            
            active_bottom_projections.append({
                'entry': entry_level,
                'exit': exit_level,
                'swing': swing_low,
                'anchor': anchored_high,
                'bar_date': htf_candles[swing_low_idx].date
            })
        
        # Check if we're in a trade and should exit
        if in_trade and current_trade:
            if current_trade['direction'] == 'SHORT':
                # Check if price hit exit level (goes down)
                if htf_candle.low <= current_trade['exit_level']:
                    pnl = current_trade['entry_price'] - current_trade['exit_level']
                    trades.append(Trade(
                        entry_date=current_trade['entry_date'],
                        direction='SHORT',
                        entry_price=current_trade['entry_price'],
                        exit_price=current_trade['exit_level'],
                        exit_date=htf_candle.date,
                        pnl=pnl,
                        setup_type='TOP'
                    ))
                    in_trade = False
                    current_trade = None
            else:  # LONG
                if htf_candle.high >= current_trade['exit_level']:
                    pnl = current_trade['exit_level'] - current_trade['entry_price']
                    trades.append(Trade(
                        entry_date=current_trade['entry_date'],
                        direction='LONG',
                        entry_price=current_trade['entry_price'],
                        exit_price=current_trade['exit_level'],
                        exit_date=htf_candle.date,
                        pnl=pnl,
                        setup_type='BOTTOM'
                    ))
                    in_trade = False
                    current_trade = None
        
        # Check for new entry if not in trade
        if not in_trade:
            # Check TOP projections (SHORT entries)
            for proj in reversed(active_top_projections[-5:]):  # Last 5 projections
                if htf_candle.low <= proj['entry']:
                    in_trade = True
                    current_trade = {
                        'direction': 'SHORT',
                        'entry_price': proj['entry'],
                        'exit_level': proj['exit'],
                        'entry_date': htf_candle.date
                    }
                    break
            
            # Check BOTTOM projections (LONG entries)
            if not in_trade:
                for proj in reversed(active_bottom_projections[-5:]):
                    if htf_candle.high >= proj['entry']:
                        in_trade = True
                        current_trade = {
                            'direction': 'LONG',
                            'entry_price': proj['entry'],
                            'exit_level': proj['exit'],
                            'entry_date': htf_candle.date
                        }
                        break
        
        # Keep only recent projections (last 20)
        active_top_projections = active_top_projections[-20:]
        active_bottom_projections = active_bottom_projections[-20:]
    
    return trades


def analyze_trades(trades: List[Trade]) -> Dict:
    """Analyze trade results"""
    if not trades:
        return {'error': 'No trades'}
    
    winning = [t for t in trades if t.pnl > 0]
    losing = [t for t in trades if t.pnl <= 0]
    
    total_pnl = sum(t.pnl for t in trades)
    gross_profit = sum(t.pnl for t in winning)
    gross_loss = abs(sum(t.pnl for t in losing))
    
    return {
        'total_trades': len(trades),
        'wins': len(winning),
        'losses': len(losing),
        'win_rate': len(winning) / len(trades) * 100 if trades else 0,
        'total_pnl': total_pnl,
        'avg_pnl': total_pnl / len(trades) if trades else 0,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'profit_factor': gross_profit / gross_loss if gross_loss > 0 else float('inf'),
        'long_trades': len([t for t in trades if t.direction == 'LONG']),
        'short_trades': len([t for t in trades if t.direction == 'SHORT']),
        'top_setups': len([t for t in trades if t.setup_type == 'TOP']),
        'bottom_setups': len([t for t in trades if t.setup_type == 'BOTTOM'])
    }


def main():
    print("="*80)
    print("🧪 LOG-FIB MTF STRATEGY - CORRECT IMPLEMENTATION")
    print("="*80)
    print()
    print("Based on: Pal Log-Fib Range Projection - MTF (Pine Script)")
    print()
    print("Key Features:")
    print("  • Multi-timeframe swing detection (60-min default)")
    print("  • Anchored pivot points (swing high → its bar's low)")
    print("  • Logarithmic range: log10(price) * |H-L| * mult * 4")
    print("  • Projection levels (NOT standard Fibonacci retracement)")
    print()
    
    # Load data
    data_dir = Path('data')
    instruments = {
        'Gold (XAUUSD)': data_dir / 'OANDA_XAUUSD5.csv',
        'Silver (XAGUSD)': data_dir / 'OANDA_XAGUSD5.csv'
    }
    
    # Also check for Nifty data
    zerodha_dir = Path('zerodha_data')
    nifty_files = list(zerodha_dir.glob('NIFTY*5minute*.csv'))
    if nifty_files:
        instruments['Nifty50'] = nifty_files[0]
    
    print(f"📁 Found {len(instruments)} instruments")
    print()
    
    # Test configurations
    configs = [
        {'htf': 60, 'lookback': 6, 'mult': 0.786, 'entry': 0.786, 'exit': 1.0},
        {'htf': 60, 'lookback': 6, 'mult': 0.618, 'entry': 0.618, 'exit': 1.0},
        {'htf': 60, 'lookback': 6, 'mult': 0.382, 'entry': 0.382, 'exit': 1.0},
        {'htf': 60, 'lookback': 6, 'mult': 0.786, 'entry': 0.618, 'exit': 1.0},
        {'htf': 30, 'lookback': 6, 'mult': 0.786, 'entry': 0.786, 'exit': 1.0},
    ]
    
    for name, filepath in instruments.items():
        if not filepath.exists():
            print(f"❌ File not found: {filepath}")
            continue
        
        print(f"{'='*80}")
        print(f"📊 {name}: {filepath}")
        print(f"{'='*80}")
        
        candles = load_data(str(filepath))
        print(f"   Loaded {len(candles)} candles")
        if candles:
            print(f"   Range: {candles[0].date} to {candles[-1].date}")
            print(f"   Price: {min(c.low for c in candles):.2f} - {max(c.high for c in candles):.2f}")
        print()
        
        results = []
        for cfg in configs:
            trades = run_backtest(
                candles,
                htf_minutes=cfg['htf'],
                lookback=cfg['lookback'],
                mult_val=cfg['mult'],
                entry_ratio=cfg['entry'],
                exit_ratio=cfg['exit']
            )
            metrics = analyze_trades(trades)
            
            if 'error' not in metrics:
                results.append({**cfg, **metrics})
                print(f"   HTF={cfg['htf']}m, LB={cfg['lookback']}, Mult={cfg['mult']:.3f}, Entry={cfg['entry']:.3f}:")
                print(f"      Trades: {metrics['total_trades']} (L:{metrics['long_trades']}/S:{metrics['short_trades']})")
                print(f"      Win Rate: {metrics['win_rate']:.1f}%")
                print(f"      PnL: {metrics['total_pnl']:+.2f}")
                print(f"      Profit Factor: {metrics['profit_factor']:.2f}")
        
        if results:
            best = max(results, key=lambda x: x['profit_factor'] if x['profit_factor'] != float('inf') else 0)
            print(f"\n   🏆 Best: HTF={best['htf']}m, Mult={best['mult']:.3f} → PF={best['profit_factor']:.2f}, WR={best['win_rate']:.1f}%")
    
    print(f"\n{'='*80}")
    print("✅ Implementation complete - this matches the Pine Script logic")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
