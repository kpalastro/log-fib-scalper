"""
Pal Vector Scalper - Python Implementation
==========================================

Converted from Pine Script "Pal Vector 3" indicator.

Core Concept: Demand/Supply Velocity Vectors

The vector slope represents the rate of price change per bar:
    demand_vector = (hv - lv) / max(hb - lb, lb - hb)

Where:
- hv/lv = highest/lowest price over lookback window
- hb/lb = bars ago since highest/lowest (absolute values)

This creates a PRICE-PER-BAR slope (velocity) that projects:
- DOWN from swing highs (resistance vectors)
- UP from swing lows (support vectors)

Fractal subdivisions (1/3, 2/3, 1/9, 1/27) create confluence zones.

Author: Kul Deep (Pine Script) → Hermes AI (Python)
Date: 2026-05-20
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import json


# ============================================================================
# CONSTANTS
# ============================================================================

DEFAULT_CONFIG = {
    'lookback': 100,  # Window length for swing detection
}

# Vector projection ratios (from Pine Script)
VECTOR_RATIOS = {
    'main': 1.0,        # Full vector (blue)
    'third_1': 1/3,     # 1/3 retracement (green)
    'third_2': 2/3,     # 2/3 retracement (red)
    'ninth': 1/9,       # 1/9 subdivision (yellow dotted)
    'twenty_seventh': 1/27,  # 1/27 subdivision (yellow dotted)
}

# Trend detection thresholds
TREND_THRESHOLDS = {
    'strong_bullish': 0.7,   # Vector confluence score for strong uptrend
    'strong_bearish': 0.7,   # Vector confluence score for strong downtrend
    'neutral': 0.3,          # Below this = no clear trend
}


# ============================================================================
# PAL VECTOR CALCULATOR
# ============================================================================

class PalVectorCalculator:
    """
    Calculate demand/supply vectors from swing points.
    
    Implements the Pine Script formula:
        demand_vector = (hv - lv) / max(hb - lb, lb - hb)
    """
    
    def __init__(self, lookback: int = 100):
        self.lookback = lookback
    
    def calculate_vectors(self, data: pd.DataFrame) -> Dict:
        """
        Calculate vector projections for each bar.
        
        Returns:
            Dict with vector levels for each bar
        """
        n = len(data)
        results = {
            'high_vectors': [],  # Downward vectors from swing highs
            'low_vectors': [],   # Upward vectors from swing lows
            'demand_vector': [], # The slope value
        }
        
        for i in range(self.lookback, n):
            # Get lookback window
            window_high = data['high'].iloc[i-self.lookback:i+1].max()
            window_low = data['low'].iloc[i-self.lookback:i+1].min()
            
            # Find bars ago since high/low
            high_window = data['high'].iloc[i-self.lookback:i+1]
            low_window = data['low'].iloc[i-self.lookback:i+1]
            
            hb = abs(high_window[::-1].idxmax() - high_window.index[-1])  # Bars ago since high
            lb = abs(low_window[::-1].idxmin() - low_window.index[-1])    # Bars ago since low
            
            # Convert to integer bar counts
            hb = int(hb)
            lb = int(lb)
            
            # Calculate demand vector (price-per-bar slope)
            denominator = max(hb - lb, lb - hb) if hb != lb else 1
            demand_vector = (window_high - window_low) / max(denominator, 1)
            
            # Project vectors from swing high (downward)
            high_vec = {
                'bar': i,
                'swing_high': window_high,
                'swing_low_anchor': data['low'].iloc[i - hb] if i >= hb else window_low,
                'hb': hb,
                'demand_vector': demand_vector,
                'projections': {}
            }
            
            for name, ratio in VECTOR_RATIOS.items():
                # Project downward from high
                high_vec['projections'][name] = window_high - (demand_vector * ratio * hb)
            
            # Project vectors from swing low (upward)
            low_vec = {
                'bar': i,
                'swing_low': window_low,
                'swing_high_anchor': data['high'].iloc[i - lb] if i >= lb else window_high,
                'lb': lb,
                'demand_vector': demand_vector,
                'projections': {}
            }
            
            for name, ratio in VECTOR_RATIOS.items():
                # Project upward from low
                low_vec['projections'][name] = window_low + (demand_vector * ratio * lb)
            
            results['high_vectors'].append(high_vec)
            results['low_vectors'].append(low_vec)
            results['demand_vector'].append(demand_vector)
        
        return results
    
    def get_current_vector_levels(self, data: pd.DataFrame) -> Dict:
        """
        Get vector levels for the most recent bar.
        
        Returns:
            Dict with current vector projections and trend signal
        """
        if len(data) < self.lookback:
            return {'error': 'Insufficient data'}
        
        # Calculate for last bar
        window_high = data['high'].iloc[-self.lookback:].max()
        window_low = data['low'].iloc[-self.lookback:].min()
        
        high_window = data['high'].iloc[-self.lookback:]
        low_window = data['low'].iloc[-self.lookback:]
        
        hb = int(abs(high_window[::-1].idxmax() - high_window.index[-1]))
        lb = int(abs(low_window[::-1].idxmin() - low_window.index[-1]))
        
        denominator = max(hb - lb, lb - hb) if hb != lb else 1
        demand_vector = (window_high - window_low) / max(denominator, 1)
        
        current_price = data['close'].iloc[-1]
        
        # Calculate all vector levels
        high_projections = {}
        low_projections = {}
        
        for name, ratio in VECTOR_RATIOS.items():
            high_projections[name] = window_high - (demand_vector * ratio * hb)
            low_projections[name] = window_low + (demand_vector * ratio * lb)
        
        # Determine trend based on price position relative to vectors
        above_high_vectors = sum(1 for v in high_projections.values() if current_price > v)
        above_low_vectors = sum(1 for v in low_projections.values() if current_price > v)
        
        bullish_score = above_low_vectors / len(VECTOR_RATIOS)
        bearish_score = (len(VECTOR_RATIOS) - above_high_vectors) / len(VECTOR_RATIOS)
        
        if bullish_score >= TREND_THRESHOLDS['strong_bullish']:
            trend = 'STRONG_BULLISH'
        elif bearish_score >= TREND_THRESHOLDS['strong_bearish']:
            trend = 'STRONG_BEARISH'
        elif bullish_score > TREND_THRESHOLDS['neutral']:
            trend = 'BULLISH'
        elif bearish_score > TREND_THRESHOLDS['neutral']:
            trend = 'BEARISH'
        else:
            trend = 'NEUTRAL'
        
        return {
            'timestamp': data['datetime'].iloc[-1],
            'current_price': current_price,
            'swing_high': window_high,
            'swing_low': window_low,
            'hb': hb,
            'lb': lb,
            'demand_vector': demand_vector,
            'high_projections': high_projections,  # Resistance levels (above price = bearish)
            'low_projections': low_projections,    # Support levels (below price = bullish)
            'bullish_score': bullish_score * 100,
            'bearish_score': bearish_score * 100,
            'trend': trend,
        }


# ============================================================================
# TREND CONFLUENCE ENGINE
# ============================================================================

class VectorLogFibConfluence:
    """
    Combine Pal Vector projections with Log-Fib levels for high-probability trend following.
    
    Entry Rules:
    - LONG: Price above vector support + Log-Fib bullish confluence
    - SHORT: Price below vector resistance + Log-Fib bearish confluence
    
    Exit Rules:
    - TP: Next vector projection level OR Log-Fib extension
    - SL: Below/above key vector level
    """
    
    def __init__(self, vector_lookback: int = 100, logfib_config: Optional[Dict] = None):
        self.vector_calc = PalVectorCalculator(lookback=vector_lookback)
        
        # Default Log-Fib config (Silver optimal)
        self.logfib_config = logfib_config or {
            'lookback': 6,
            'mult': 0.5,
            'entry': 0.382,
            'tp': 1.272,
            'sl': 1.618,
        }
    
    def analyze(self, data: pd.DataFrame) -> Dict:
        """
        Full confluence analysis combining Vector + Log-Fib.
        
        Returns:
            Dict with trend signal, entry/exit levels, confluence score
        """
        # Get vector analysis
        vector_analysis = self.vector_calc.get_current_vector_levels(data)
        
        if 'error' in vector_analysis:
            return vector_analysis
        
        # Get Log-Fib analysis (simplified - full implementation in geometric_confluence_scalper.py)
        logfib_analysis = self._analyze_logfib(data)
        
        # Combine signals
        confluence_score = self._calculate_confluence(vector_analysis, logfib_analysis)
        
        # Generate trading signal
        signal = self._generate_signal(vector_analysis, logfib_analysis, confluence_score)
        
        return {
            'timestamp': vector_analysis['timestamp'],
            'current_price': vector_analysis['current_price'],
            'vector_analysis': vector_analysis,
            'logfib_analysis': logfib_analysis,
            'confluence_score': confluence_score,
            'signal': signal,
        }
    
    def _analyze_logfib(self, data: pd.DataFrame) -> Dict:
        """Simplified Log-Fib analysis."""
        lookback = self.logfib_config['lookback']
        mult = self.logfib_config['mult']
        
        if len(data) < lookback:
            return {'error': 'Insufficient data for Log-Fib'}
        
        # Find swing high/low
        swing_high = data['high'].iloc[-lookback:].max()
        swing_low = data['low'].iloc[-lookback:].min()
        
        # Calculate effective range (Log-Fib formula)
        pivot = swing_high if data['close'].iloc[-1] > (swing_high + swing_low) / 2 else swing_low
        anchor = swing_low if pivot == swing_high else swing_high
        
        effective_range = np.log10(pivot) * abs(pivot - anchor) * mult * 4
        
        # Calculate levels
        entry_ratio = self.logfib_config['entry']
        tp_ratio = self.logfib_config['tp']
        sl_ratio = self.logfib_config['sl']
        
        if pivot == swing_high:  # Bearish setup
            entry = pivot - (entry_ratio * effective_range)
            tp = pivot - (tp_ratio * effective_range)
            sl = pivot + (sl_ratio * effective_range)
            direction = 'SHORT'
        else:  # Bullish setup
            entry = pivot + (entry_ratio * effective_range)
            tp = pivot + (tp_ratio * effective_range)
            sl = pivot - (sl_ratio * effective_range)
            direction = 'LONG'
        
        return {
            'swing_high': swing_high,
            'swing_low': swing_low,
            'pivot': pivot,
            'anchor': anchor,
            'effective_range': effective_range,
            'entry': entry,
            'tp': tp,
            'sl': sl,
            'direction': direction,
        }
    
    def _calculate_confluence(self, vector: Dict, logfib: Dict) -> float:
        """
        Calculate confluence score (0-100).
        
        Factors:
        - Vector trend strength (0-40 points)
        - Log-Fib direction alignment (0-30 points)
        - Price proximity to key levels (0-30 points)
        """
        score = 0
        
        # Vector trend strength (0-40)
        if vector['trend'] in ['STRONG_BULLISH', 'STRONG_BEARISH']:
            score += 40
        elif vector['trend'] in ['BULLISH', 'BEARISH']:
            score += 25
        else:
            score += 10
        
        # Log-Fib alignment (0-30)
        current_price = vector['current_price']
        logfib_direction = logfib.get('direction', 'NEUTRAL')
        
        if logfib_direction == 'LONG' and vector['trend'] in ['BULLISH', 'STRONG_BULLISH']:
            score += 30
        elif logfib_direction == 'SHORT' and vector['trend'] in ['BEARISH', 'STRONG_BEARISH']:
            score += 30
        elif logfib_direction == 'LONG' and vector['trend'] == 'NEUTRAL':
            score += 15
        elif logfib_direction == 'SHORT' and vector['trend'] == 'NEUTRAL':
            score += 15
        
        # Price proximity to key levels (0-30)
        # Check if price is near vector support/resistance
        main_high_vec = vector['high_projections'].get('main', current_price)
        main_low_vec = vector['low_projections'].get('main', current_price)
        
        price_range = vector['swing_high'] - vector['swing_low']
        if price_range > 0:
            dist_to_high = abs(current_price - main_high_vec) / price_range
            dist_to_low = abs(current_price - main_low_vec) / price_range
            
            if min(dist_to_high, dist_to_low) < 0.1:  # Within 10% of range
                score += 30
            elif min(dist_to_high, dist_to_low) < 0.2:
                score += 20
            else:
                score += 10
        
        return min(score, 100)
    
    def _generate_signal(self, vector: Dict, logfib: Dict, confluence: float) -> Dict:
        """Generate trading signal."""
        current_price = vector['current_price']
        
        # Determine direction
        if vector['trend'] in ['STRONG_BULLISH', 'BULLISH']:
            direction = 'LONG'
        elif vector['trend'] in ['STRONG_BEARISH', 'BEARISH']:
            direction = 'SHORT'
        else:
            direction = 'NEUTRAL'
        
        # Entry/Exit levels
        if direction == 'LONG':
            entry = vector['low_projections'].get('third_1', current_price)
            tp = vector['high_projections'].get('main', logfib.get('tp', current_price * 1.01))
            sl = vector['low_projections'].get('main', logfib.get('sl', current_price * 0.99))
        elif direction == 'SHORT':
            entry = vector['high_projections'].get('third_1', current_price)
            tp = vector['low_projections'].get('main', logfib.get('tp', current_price * 0.99))
            sl = vector['high_projections'].get('main', logfib.get('sl', current_price * 1.01))
        else:
            entry = tp = sl = current_price
        
        # Signal strength
        if confluence >= 70:
            strength = 'STRONG'
        elif confluence >= 50:
            strength = 'MODERATE'
        else:
            strength = 'WEAK'
        
        return {
            'direction': direction,
            'entry': entry,
            'tp': tp,
            'sl': sl,
            'strength': strength,
            'confluence_score': confluence,
            'action': 'ENTER' if confluence >= 50 and direction != 'NEUTRAL' else 'WAIT',
        }


# ============================================================================
# BACKTEST ENGINE
# ============================================================================

class VectorBacktester:
    """Backtest Pal Vector strategy."""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
    
    def run(self, data: pd.DataFrame, config: Optional[Dict] = None) -> Dict:
        """
        Run backtest on historical data.
        
        Returns:
            Dict with performance metrics and trade log
        """
        confluence_engine = VectorLogFibConfluence(
            vector_lookback=config.get('lookback', 100) if config else 100,
            logfib_config=config
        )
        
        trades = []
        capital = self.initial_capital
        position = None  # {'direction': 'LONG'/'SHORT', 'entry_price': float, 'size': float}
        
        for i in range(100, len(data)):  # Warmup period
            slice_data = data.iloc[:i+1].copy()
            analysis = confluence_engine.analyze(slice_data)
            
            current_price = data['close'].iloc[i]
            timestamp = data['datetime'].iloc[i]
            
            # Check for entry
            if position is None and analysis['signal']['action'] == 'ENTER':
                signal = analysis['signal']
                size = capital * 0.1 / current_price  # 10% position size
                
                position = {
                    'direction': signal['direction'],
                    'entry_price': signal['entry'],
                    'size': size,
                    'tp': signal['tp'],
                    'sl': signal['sl'],
                    'entry_time': timestamp,
                }
            
            # Check for exit
            elif position is not None:
                pnl = 0
                exit_reason = None
                
                if position['direction'] == 'LONG':
                    if current_price >= position['tp']:
                        pnl = (position['tp'] - position['entry_price']) * position['size']
                        exit_reason = 'TP'
                    elif current_price <= position['sl']:
                        pnl = (position['sl'] - position['entry_price']) * position['size']
                        exit_reason = 'SL'
                else:  # SHORT
                    if current_price <= position['tp']:
                        pnl = (position['entry_price'] - position['tp']) * position['size']
                        exit_reason = 'TP'
                    elif current_price >= position['sl']:
                        pnl = (position['entry_price'] - position['sl']) * position['size']
                        exit_reason = 'SL'
                
                if exit_reason:
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': timestamp,
                        'direction': position['direction'],
                        'entry_price': position['entry_price'],
                        'exit_price': position['tp'] if exit_reason == 'TP' else position['sl'],
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': exit_reason,
                        'confluence': analysis['confluence_score'],
                    })
                    capital += pnl
                    position = None
        
        # Calculate metrics
        if not trades:
            return {'error': 'No trades executed'}
        
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] <= 0]
        
        total_pnl = sum(t['pnl'] for t in trades)
        gross_profit = sum(t['pnl'] for t in wins)
        gross_loss = abs(sum(t['pnl'] for t in losses))
        
        return {
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(trades) * 100 if trades else 0,
            'total_pnl': total_pnl,
            'final_capital': capital,
            'return_pct': (capital - self.initial_capital) / self.initial_capital * 100,
            'profit_factor': gross_profit / gross_loss if gross_loss > 0 else float('inf'),
            'avg_pnl_per_trade': total_pnl / len(trades),
            'trades': trades,
        }


# ============================================================================
# DATA LOADER
# ============================================================================

def load_data(csv_path: str) -> pd.DataFrame:
    """Load OANDA CSV data."""
    df = pd.read_csv(csv_path)
    
    # Ensure datetime column
    if 'time' in df.columns:
        df['datetime'] = pd.to_datetime(df['time'])
    elif 'datetime' not in df.columns:
        df['datetime'] = pd.to_datetime(df.iloc[:, 0])
    
    # Ensure numeric columns
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Drop rows with NaN
    df = df.dropna(subset=['open', 'high', 'low', 'close'])
    
    return df


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    import sys
    
    # Default data paths
    SILVER_DATA = '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAGUSD5.csv'
    GOLD_DATA = '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv'
    
    print("=" * 80)
    print("PAL VECTOR SCALPER - Backtest & Analysis")
    print("=" * 80)
    
    # Load data
    instrument = sys.argv[1] if len(sys.argv) > 1 else 'silver'
    csv_path = GOLD_DATA if instrument.lower() == 'gold' else SILVER_DATA
    
    print(f"\n📊 Instrument: {instrument.upper()}")
    print(f"📁 Data: {csv_path}")
    
    try:
        data = load_data(csv_path)
        print(f"📈 Bars loaded: {len(data)}")
        print(f"📅 Range: {data['datetime'].iloc[0]} → {data['datetime'].iloc[-1]}")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        sys.exit(1)
    
    # Current analysis
    print("\n" + "=" * 80)
    print("CURRENT VECTOR ANALYSIS")
    print("=" * 80)
    
    vector_calc = PalVectorCalculator(lookback=100)
    current = vector_calc.get_current_vector_levels(data)
    
    if 'error' not in current:
        print(f"\n💰 Current Price: {current['current_price']:.4f}")
        print(f"📊 Swing High: {current['swing_high']:.4f} ({current['hb']} bars ago)")
        print(f"📊 Swing Low: {current['swing_low']:.4f} ({current['lb']} bars ago)")
        print(f"📐 Demand Vector: {current['demand_vector']:.6f}")
        print(f"📈 Trend: {current['trend']}")
        print(f"   Bullish Score: {current['bullish_score']:.1f}%")
        print(f"   Bearish Score: {current['bearish_score']:.1f}%")
        
        print("\n🔮 Vector Projections (from High - Resistance):")
        for name, level in current['high_projections'].items():
            print(f"   {name:15s}: {level:.4f}")
        
        print("\n🔮 Vector Projections (from Low - Support):")
        for name, level in current['low_projections'].items():
            print(f"   {name:15s}: {level:.4f}")
    
    # Confluence analysis
    print("\n" + "=" * 80)
    print("VECTOR + LOG-FIB CONFLUENCE")
    print("=" * 80)
    
    confluence_engine = VectorLogFibConfluence(vector_lookback=100)
    analysis = confluence_engine.analyze(data)
    
    print(f"\n🎯 Confluence Score: {analysis['confluence_score']:.1f}/100")
    print(f"📈 Signal: {analysis['signal']['direction']} ({analysis['signal']['strength']})")
    print(f"⚡ Action: {analysis['signal']['action']}")
    
    if analysis['signal']['action'] == 'ENTER':
        print(f"\n💼 Trade Setup:")
        print(f"   Entry: {analysis['signal']['entry']:.4f}")
        print(f"   TP:    {analysis['signal']['tp']:.4f}")
        print(f"   SL:    {analysis['signal']['sl']:.4f}")
    
    # Backtest
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    
    backtester = VectorBacktester(initial_capital=100000)
    results = backtester.run(data)
    
    if 'error' not in results:
        print(f"\n📊 Performance Metrics:")
        print(f"   Total Trades: {results['total_trades']}")
        print(f"   Win Rate: {results['win_rate']:.2f}%")
        print(f"   Total P&L: ${results['total_pnl']:,.2f}")
        print(f"   Return: {results['return_pct']:.2f}%")
        print(f"   Profit Factor: {results['profit_factor']:.2f}")
        print(f"   Avg P&L/Trade: ${results['avg_pnl_per_trade']:.2f}")
        print(f"   Final Capital: ${results['final_capital']:,.2f}")
        
        # Save results
        output_file = f'/home/palbot/Projects/log-fib-scalper/pal_vector_results_{instrument}.json'
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {output_file}")
    else:
        print(f"\n❌ Backtest error: {results['error']}")
    
    print("\n" + "=" * 80)
