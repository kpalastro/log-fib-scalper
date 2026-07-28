"""
Geometric Confluence Scalper v2.0
==================================

A next-generation trading strategy combining:
1. 0.382 Fibonacci retracement (price geometry)
2. Fib number candle counts (time geometry)
3. Gann price-time squares (spatial geometry)
4. Markov pattern probabilities (sequence geometry)

Based on deep swing research findings:
- 70.5% of Silver swings retrace to 0.382
- 70% of Silver swings occur within ±1 bar of Fib numbers (13, 21, 34, 55)
- 21.9% of swing transitions form perfect Gann squares (time ≈ price)
- 80-85% reversal probability after H-L or L-H patterns

Author: Hermes Research Team
Date: 2026-05-19
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import json

# ============================================================================
# CONSTANTS
# ============================================================================

FIB_NUMBERS = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
FIB_RATIOS = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]

# Instrument-specific scaling for Gann calculations
GANN_SCALING = {
    'silver': 0.1,    # 1 bar ≈ 0.1% price move
    'gold': 0.05,     # 1 bar ≈ 0.05% price move
    'nifty': 0.0002,  # 1 bar ≈ 0.02% price move (index - much tighter)
    'banknifty': 0.0002,  # Same as Nifty
}

# Validated optimal configurations from walk-forward testing
OPTIMAL_CONFIGS = {
    'silver': {
        'best': {
            'lookback': 6,
            'mult': 0.5,
            'entry': 0.382,
            'tp': 1.272,
            'sl': 1.618,
            'win_rate': 99.37,
            'profit_factor': 46.35,
        },
        'alternative': {
            'lookback': 6,
            'mult': 0.382,
            'entry': 0.382,
            'tp': 1.272,
            'sl': 1.0,
            'win_rate': 98.85,
            'profit_factor': 49.17,
        },
        # NEW: CFD Scalping configuration (tight stops, quick targets)
        'scalping': {
            'lookback': 5,        # Faster swing detection
            'mult': 0.25,         # Smaller effective range (tighter clustering)
            'entry': 0.382,       # Same Fib entry
            'tp': 2.0,            # 2.0x range for 1:2 R:R (with SL=1.0)
            'sl': 1.0,            # 1.0x range (tight stop ~1-2% for Silver)
            'target_profit_aud': 500,  # Per trade target
        }
    },
    'gold': {
        'best': {
            'lookback': 8,
            'mult': 0.618,
            'entry': 0.5,
            'tp': 1.272,      # ← Changed from 1.0 (was causing Entry≈TP bug)
            'sl': 1.618,
            'win_rate': 98.21,
            'profit_factor': 7.59,
        },
        # NEW: CFD Scalping configuration (tight stops, quick targets)
        'scalping': {
            'lookback': 5,        # Faster swing detection
            'mult': 0.25,         # Smaller effective range
            'entry': 0.5,         # 50% retrace for gold
            'tp': 2.0,            # 2.0x range for 1:2 R:R
            'sl': 1.0,            # 1.0x range (tight stop ~0.5-0.8% for Gold)
            'target_profit_aud': 500,  # Per trade target
        }
    },
    'nifty': {
        'best': {
            'lookback': 8,
            'mult': 0.1,       # Nifty-specific: 5x smaller than Silver (index vs commodity)
            'entry': 0.382,
            'tp': 1.272,
            'sl': 1.618,
        }
    },
    'banknifty': {
        'best': {
            'lookback': 8,
            'mult': 0.1,       # Same as Nifty - indices need smaller mult
            'entry': 0.382,
            'tp': 1.272,
            'sl': 1.618,
        }
    }
}

# Confluence scoring weights
CONFLUENCE_WEIGHTS = {
    'fib_time': 30,      # Fib number candle count
    'gann_square': 25,   # Gann price-time square
    'markov_reversal': 25,  # Markov pattern probability
    'fib_retracement': 20,  # 0.382 retracement quality
}

MIN_CONFLUENCE_SCORE = 50  # Minimum score to take trade (out of 100)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def is_fib_number(n: int, tolerance: int = 1) -> Tuple[bool, int, int]:
    """
    Check if n is a Fib number or within tolerance of one.
    Returns: (is_near_fib, nearest_fib, distance)
    """
    nearest_fib = min(FIB_NUMBERS, key=lambda x: abs(x - n))
    distance = abs(n - nearest_fib)
    return distance <= tolerance, nearest_fib, distance


def calc_gann_ratio(time_dist: int, price_pct: float, instrument: str) -> float:
    """Calculate Gann price-time ratio."""
    scaling = GANN_SCALING.get(instrument, 0.1)
    normalized_price = price_pct / scaling
    return time_dist / normalized_price if normalized_price > 0 else 0


def is_gann_square(ratio: float, tolerance: float = 0.2) -> Tuple[bool, str]:
    """
    Check if ratio forms a Gann square.
    Returns: (is_square, ratio_type)
    """
    if 0.8 <= ratio <= 1.2:
        return True, "1x1 (Perfect Square)"
    elif 0.4 <= ratio < 0.8:
        return True, "1x2 (Price Speed)"
    elif 1.2 < ratio <= 1.6:
        return True, "2x1 (Time Speed)"
    elif 0.2 <= ratio < 0.4 or 2.0 < ratio <= 2.4:
        return True, "1x4 or 4x1 (Extreme)"
    return False, f"{ratio:.2f}x (No Match)"


def calc_retracement_quality(current_price: float, swing_price: float, anchor_price: float) -> Tuple[float, float]:
    """
    Calculate how close current price is to optimal Fib retracement.
    Returns: (retracement_ratio, distance_to_0.382)
    """
    total_range = abs(swing_price - anchor_price)
    if total_range == 0:
        return 0, 1.0
    
    current_retracement = abs(current_price - swing_price) / total_range
    distance_to_optimal = abs(current_retracement - 0.382)
    
    return current_retracement, distance_to_optimal


# ============================================================================
# SWING DETECTION
# ============================================================================

class SwingDetector:
    """Detect swing highs and lows using lookback fractal method."""
    
    def __init__(self, lookback: int = 6):
        self.lookback = lookback
    
    def detect(self, data: pd.DataFrame) -> Dict:
        """Detect all swings in the data."""
        swing_highs = []
        swing_lows = []
        
        for i in range(self.lookback, len(data) - self.lookback):
            # Swing High
            is_swing_high = True
            for j in range(i - self.lookback, i + self.lookback + 1):
                if j != i and data['high'].iloc[j] >= data['high'].iloc[i]:
                    is_swing_high = False
                    break
            if is_swing_high:
                swing_highs.append({
                    'index': i,
                    'time': data['datetime'].iloc[i],
                    'price': data['high'].iloc[i],
                    'anchor': data['low'].iloc[i],
                    'type': 'H',
                    'bar_num': i
                })
            
            # Swing Low
            is_swing_low = True
            for j in range(i - self.lookback, i + self.lookback + 1):
                if j != i and data['low'].iloc[j] <= data['low'].iloc[i]:
                    is_swing_low = False
                    break
            if is_swing_low:
                swing_lows.append({
                    'index': i,
                    'time': data['datetime'].iloc[i],
                    'price': data['low'].iloc[i],
                    'anchor': data['high'].iloc[i],
                    'type': 'L',
                    'bar_num': i
                })
        
        return {
            'swing_highs': swing_highs,
            'swing_lows': swing_lows,
            'all_swings': sorted(swing_highs + swing_lows, key=lambda x: x['index'])
        }


# ============================================================================
# GEOMETRIC ANALYZER
# ============================================================================

class GeometricAnalyzer:
    """Analyze geometric patterns in swing data."""
    
    def __init__(self, instrument: str = 'silver'):
        self.instrument = instrument
    
    def analyze_confluence(self, 
                          current_idx: int,
                          swing_highs: List[Dict],
                          swing_lows: List[Dict],
                          data: pd.DataFrame,
                          config: Dict) -> Dict:
        """
        Analyze geometric confluence at current bar.
        Returns confluence score and detailed breakdown.
        """
        all_swings = sorted(swing_highs + swing_lows, key=lambda x: x['index'])
        
        # Find most recent swing
        prev_swing = None
        for swing in reversed(all_swings):
            if swing['index'] < current_idx:
                prev_swing = swing
                break
        
        if not prev_swing:
            return {'score': 0, 'ready': False, 'reason': 'No previous swing'}
        
        # Get config values with defaults
        entry_ratio = config.get('entry', 0.382)
        tp_ratio = config.get('tp', 1.272)
        sl_ratio = config.get('sl', 1.618)
        mult = config.get('mult', 0.5)
        
        # 1. Fib Time Analysis
        candle_count = current_idx - prev_swing['index']
        is_fib, nearest_fib, fib_distance = is_fib_number(candle_count)
        fib_score = max(0, (1 - fib_distance / 3) * 100)  # Score 0-100
        
        # 2. Gann Square Analysis
        price_change = abs(data['close'].iloc[current_idx] - prev_swing['price'])
        price_pct = (price_change / prev_swing['price']) * 100
        gann_ratio = calc_gann_ratio(candle_count, price_pct, self.instrument)
        is_square, ratio_type = is_gann_square(gann_ratio)
        gann_score = 100 if is_square else max(0, (1 - abs(gann_ratio - 1.0)) * 50)
        
        # 3. Markov Pattern Analysis
        # Get last 3 swings for pattern
        recent_swings = [s for s in all_swings if s['index'] < current_idx][-3:]
        if len(recent_swings) >= 2:
            pattern = ''.join([s['type'] for s in recent_swings[-2:]])
            # After H-L or L-H, 80-85% reverse
            if pattern in ['HL', 'LH']:
                markov_prob = 0.82  # 82% average reversal probability
                markov_score = markov_prob * 100
            else:
                markov_prob = 0.50  # No edge
                markov_score = 50
        else:
            pattern = '??'
            markov_prob = 0.50
            markov_score = 50
        
        # 4. Fib Retracement Quality
        eff_range = self._calc_eff_range(prev_swing['price'], prev_swing['anchor'], mult)
        
        if prev_swing['type'] == 'H':
            # Looking for SHORT - price should be retracing up
            optimal_entry = prev_swing['price'] - (entry_ratio * eff_range)
            current_price = data['close'].iloc[current_idx]
            retracement_ratio, dist_to_optimal = calc_retracement_quality(
                current_price, prev_swing['price'], prev_swing['anchor'])
        else:
            # Looking for LONG - price should be retracing down
            optimal_entry = prev_swing['price'] + (entry_ratio * eff_range)
            current_price = data['close'].iloc[current_idx]
            retracement_ratio, dist_to_optimal = calc_retracement_quality(
                current_price, prev_swing['price'], prev_swing['anchor'])
        
        retracement_score = max(0, (1 - dist_to_optimal * 2) * 100)
        
        # Calculate weighted confluence score
        total_score = (
            fib_score * CONFLUENCE_WEIGHTS['fib_time'] +
            gann_score * CONFLUENCE_WEIGHTS['gann_square'] +
            markov_score * CONFLUENCE_WEIGHTS['markov_reversal'] +
            retracement_score * CONFLUENCE_WEIGHTS['fib_retracement']
        ) / 100
        
        # Determine trade direction
        if prev_swing['type'] == 'H':
            direction = 'SHORT'
            entry_price = optimal_entry
            tp_price = prev_swing['price'] - (tp_ratio * eff_range)
            sl_price = prev_swing['price'] + (sl_ratio * eff_range)
        else:
            direction = 'LONG'
            entry_price = optimal_entry
            tp_price = prev_swing['price'] + (tp_ratio * eff_range)
            sl_price = prev_swing['price'] - (sl_ratio * eff_range)
        
        return {
            'score': total_score,
            'ready': total_score >= MIN_CONFLUENCE_SCORE,
            'direction': direction,
            'entry_price': entry_price,
            'tp_price': tp_price,
            'sl_price': sl_price,
            'breakdown': {
                'fib_time': {
                    'score': fib_score,
                    'candle_count': candle_count,
                    'nearest_fib': nearest_fib,
                    'distance': fib_distance,
                    'is_fib': is_fib,
                },
                'gann_square': {
                    'score': gann_score,
                    'ratio': gann_ratio,
                    'ratio_type': ratio_type,
                    'is_square': is_square,
                },
                'markov_pattern': {
                    'score': markov_score,
                    'pattern': pattern,
                    'reversal_prob': markov_prob,
                },
                'fib_retracement': {
                    'score': retracement_score,
                    'ratio': retracement_ratio,
                    'distance_to_0.382': dist_to_optimal,
                }
            }
        }
    
    def _calc_eff_range(self, pivot: float, anchor: float, mult: float) -> float:
        """Calculate effective range using log-Fib formula."""
        return np.log10(pivot) * abs(pivot - anchor) * mult * 4


# ============================================================================
# SIGNAL GENERATOR
# ============================================================================

class GeometricConfluenceScalper:
    """Main strategy engine."""
    
    def __init__(self, instrument: str = 'silver', config: Optional[Dict] = None):
        self.instrument = instrument
        self.config = config or OPTIMAL_CONFIGS.get(instrument, {}).get('best', {})
        self.swing_detector = SwingDetector(self.config.get('lookback', 6))
        self.analyzer = GeometricAnalyzer(instrument)
        self.signals = []
    
    def scan(self, data: pd.DataFrame, current_idx: Optional[int] = None) -> Dict:
        """
        Scan for high-confluence setups.
        If current_idx is None, scan entire dataset.
        """
        if current_idx is None:
            # Full backtest mode
            return self._full_backtest(data)
        else:
            # Real-time scan mode
            return self._scan_bar(data, current_idx)
    
    def _scan_bar(self, data: pd.DataFrame, idx: int) -> Dict:
        """Scan single bar for setup."""
        swings = self.swing_detector.detect(data.iloc[:idx+1])
        analysis = self.analyzer.analyze_confluence(
            idx, swings['swing_highs'], swings['swing_lows'], data, self.config)
        
        signal = {
            'bar': idx,
            'datetime': data['datetime'].iloc[idx],
            'price': data['close'].iloc[idx],
            **analysis
        }
        
        if analysis['ready']:
            self.signals.append(signal)
        
        return signal
    
    def _full_backtest(self, data: pd.DataFrame) -> Dict:
        """Run full backtest."""
        swings = self.swing_detector.detect(data)
        trades = []
        
        in_trade = False
        current_trade = None
        
        for i in range(self.config.get('lookback', 6), len(data)):
            if in_trade:
                # Check exit
                if current_trade['direction'] == 'SHORT':
                    if data['low'].iloc[i] <= current_trade['tp']:
                        pnl = current_trade['entry_price'] - current_trade['tp']
                        trades.append({
                            **current_trade,
                            'exit_idx': i,
                            'exit_price': current_trade['tp'],
                            'pnl': pnl,
                            'outcome': 'WIN' if pnl > 0 else 'LOSS'
                        })
                        in_trade = False
                    elif data['high'].iloc[i] >= current_trade['sl']:
                        pnl = current_trade['entry_price'] - current_trade['sl']
                        trades.append({
                            **current_trade,
                            'exit_idx': i,
                            'exit_price': current_trade['sl'],
                            'pnl': pnl,
                            'outcome': 'WIN' if pnl > 0 else 'LOSS'
                        })
                        in_trade = False
                else:  # LONG
                    if data['high'].iloc[i] >= current_trade['tp']:
                        pnl = current_trade['tp'] - current_trade['entry_price']
                        trades.append({
                            **current_trade,
                            'exit_idx': i,
                            'exit_price': current_trade['tp'],
                            'pnl': pnl,
                            'outcome': 'WIN' if pnl > 0 else 'LOSS'
                        })
                        in_trade = False
                    elif data['low'].iloc[i] <= current_trade['sl']:
                        pnl = current_trade['sl'] - current_trade['entry_price']
                        trades.append({
                            **current_trade,
                            'exit_idx': i,
                            'exit_price': current_trade['sl'],
                            'pnl': pnl,
                            'outcome': 'WIN' if pnl > 0 else 'LOSS'
                        })
                        in_trade = False
            else:
                # Check entry
                analysis = self.analyzer.analyze_confluence(
                    i, swings['swing_highs'], swings['swing_lows'], data, self.config)
                
                if analysis['ready']:
                    in_trade = True
                    current_trade = {
                        'entry_idx': i,
                        'entry_price': analysis['entry_price'],
                        'direction': analysis['direction'],
                        'tp': analysis['tp_price'],
                        'sl': analysis['sl_price'],
                        'confluence_score': analysis['score'],
                        'breakdown': analysis['breakdown'],
                    }
        
        # Calculate statistics
        if trades:
            wins = [t for t in trades if t['outcome'] == 'WIN']
            win_rate = len(wins) / len(trades) * 100
            total_pnl = sum(t['pnl'] for t in trades)
            gross_profit = sum(t['pnl'] for t in wins)
            gross_loss = abs(sum(t['pnl'] for t in trades if t['outcome'] == 'LOSS'))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Confluence score analysis
            high_confluence = [t for t in trades if t['confluence_score'] >= 70]
            med_confluence = [t for t in trades if 50 <= t['confluence_score'] < 70]
            
            high_wr = len([t for t in high_confluence if t['outcome'] == 'WIN']) / len(high_confluence) * 100 if high_confluence else 0
            med_wr = len([t for t in med_confluence if t['outcome'] == 'WIN']) / len(med_confluence) * 100 if med_confluence else 0
            
            stats = {
                'total_trades': len(trades),
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'total_pnl': total_pnl,
                'high_confluence_trades': len(high_confluence),
                'high_confluence_wr': high_wr,
                'med_confluence_trades': len(med_confluence),
                'med_confluence_wr': med_wr,
            }
        else:
            stats = {'total_trades': 0}
        
        return {
            'trades': trades,
            'stats': stats,
            'swings': swings,
        }


# ============================================================================
# DATA LOADING
# ============================================================================

def load_data(filepath: str) -> pd.DataFrame:
    """Load CSV data into DataFrame."""
    df = pd.read_csv(filepath)
    
    # Parse datetime - handle various column names
    if 'time' in df.columns:
        time_col = 'time'
    elif 'datetime' in df.columns:
        time_col = 'datetime'
    elif 'date' in df.columns:
        time_col = 'date'
    else:
        raise ValueError("No time column found")
    
    # Handle ISO format with timezone offset
    time_values = df[time_col].astype(str)
    # Remove timezone offset for parsing
    time_values = time_values.str.replace(r'[+-]\d{2}:\d{2}$', '', regex=True)
    time_values = time_values.str.replace('T', ' ')
    df['datetime'] = pd.to_datetime(time_values)
    
    # Select only OHLC columns (avoid duplicate column names from strategy columns)
    # Map exact column names only
    if 'open' in df.columns and 'high' in df.columns and 'low' in df.columns and 'close' in df.columns:
        df = df[['datetime', 'open', 'high', 'low', 'close']].copy()
    else:
        raise ValueError("Missing OHLC columns")
    
    df = df.dropna()
    df = df.drop_duplicates(subset=['datetime'], keep='first')
    df = df.sort_values('datetime').reset_index(drop=True)
    
    return df


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run backtest on Silver and Gold."""
    print("="*70)
    print("GEOMETRIC CONFLUENCE SCALPER v2.0")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    for instrument in ['silver', 'gold']:
        print(f"\n{'#'*70}")
        print(f"# INSTRUMENT: {instrument.upper()}")
        print(f"{'#'*70}")
        
        # Map instrument names to data file prefixes
        file_prefix = 'XAG' if instrument == 'silver' else 'XAU'
        filepath = f'/home/palbot/Projects/log-fib-scalper/data/OANDA_{file_prefix}USD5.csv'
        
        try:
            df = load_data(filepath)
            print(f"Loaded {len(df):,} candles")
            
            # Run backtest with optimal config
            config = OPTIMAL_CONFIGS.get(instrument, {}).get('best', {})
            scalper = GeometricConfluenceScalper(instrument, config)
            result = scalper._full_backtest(df)
            
            print(f"\n📊 BACKTEST RESULTS")
            print(f"  Total Trades: {result['stats'].get('total_trades', 0)}")
            print(f"  Win Rate: {result['stats'].get('win_rate', 0):.2f}%")
            print(f"  Profit Factor: {result['stats'].get('profit_factor', 0):.2f}")
            print(f"  Total P&L: {result['stats'].get('total_pnl', 0):.4f}")
            
            print(f"\n🎯 CONFLUENCE ANALYSIS")
            print(f"  High Confluence (≥70): {result['stats'].get('high_confluence_trades', 0)} trades, {result['stats'].get('high_confluence_wr', 0):.1f}% WR")
            print(f"  Medium Confluence (50-69): {result['stats'].get('med_confluence_trades', 0)} trades, {result['stats'].get('med_confluence_wr', 0):.1f}% WR")
            
            # Show example trades
            if result['trades']:
                print(f"\n📋 EXAMPLE TRADES (First 5):")
                for i, trade in enumerate(result['trades'][:5]):
                    print(f"\n  Trade {i+1}:")
                    print(f"    Bar {trade['entry_idx']}: {trade['direction']} @ {trade['entry_price']:.4f}")
                    print(f"    Confluence Score: {trade['confluence_score']:.1f}")
                    print(f"    Fib Time: {trade['breakdown']['fib_time']['candle_count']} bars (near {trade['breakdown']['fib_time']['nearest_fib']})")
                    print(f"    Gann Ratio: {trade['breakdown']['gann_square']['ratio']:.2f}x ({trade['breakdown']['gann_square']['ratio_type']})")
                    print(f"    Markov Pattern: {trade['breakdown']['markov_pattern']['pattern']} ({trade['breakdown']['markov_pattern']['reversal_prob']*100:.0f}% reversal prob)")
                    print(f"    Outcome: {trade['outcome']} ({trade['pnl']:.4f})")
            
            results[instrument] = result
            
        except Exception as e:
            print(f"Error processing {instrument}: {e}")
            results[instrument] = {'error': str(e)}
    
    # Save results
    output_path = f'/home/palbot/Projects/log-fib-scalper/analysis/geometric_confluence_backtest.json'
    
    # Convert to JSON-serializable format
    def convert(obj):
        if isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [convert(i) for i in obj]
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        return obj
    
    with open(output_path, 'w') as f:
        json.dump(convert(results), f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"Results saved to: {output_path}")
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    
    return results


if __name__ == '__main__':
    main()
