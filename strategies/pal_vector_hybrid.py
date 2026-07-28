"""
Pal Vector + Log-Fib Hybrid - Optimized for Trend Following
============================================================

Key Insight: Vectors identify TREND DIRECTION, Log-Fib provides ENTRY/EXIT levels.

Architecture:
1. Vector Trend Filter (short lookback: 20-40 bars)
   - Determines if we're in bullish/bearish regime
   - Only take Log-Fib signals in direction of vector trend

2. Log-Fib Entry (validated configs)
   - Silver: LB=6, Mult=0.5, Entry=0.382, TP=1.272, SL=1.618
   - Gold: LB=8, Mult=0.618, Entry=0.5, TP=1.0, SL=1.618

3. Confluence Scoring
   - Vector trend alignment: +40 points
   - Price above/below key vector level: +30 points
   - Log-Fib setup quality: +30 points

Author: Hermes Quant Squad
Date: 2026-05-20
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import json


# ============================================================================
# VALIDATED CONFIGS (from Log-Fib walk-forward testing)
# ============================================================================

VALIDATED_CONFIGS = {
    'silver': {
        'lookback': 6,
        'mult': 0.5,
        'entry': 0.382,
        'tp': 1.272,
        'sl': 1.618,
        'win_rate': 99.37,
        'profit_factor': 46.35,
    },
    'gold': {
        'lookback': 8,
        'mult': 0.618,
        'entry': 0.5,
        'tp': 1.0,
        'sl': 1.618,
        'win_rate': 98.21,
        'profit_factor': 7.59,
    },
}

# Vector trend filter configs (optimized for 5-min)
VECTOR_CONFIGS = {
    'silver': {'lookback': 30},  # Shorter for faster trend detection
    'gold': {'lookback': 40},
}


# ============================================================================
# HYBRID STRATEGY ENGINE
# ============================================================================

class VectorLogFibHybrid:
    """
    Hybrid strategy: Vector trend filter + Log-Fib entries.
    
    Rules:
    - LONG only when Vector trend = BULLISH/STRONG_BULLISH
    - SHORT only when Vector trend = BEARISH/STRONG_BEARISH
    - Enter on Log-Fib retracement to optimal level
    - Exit at Log-Fib extension (TP) or stop (SL)
    """
    
    def __init__(self, instrument: str = 'silver'):
        self.instrument = instrument
        self.vector_lb = VECTOR_CONFIGS.get(instrument, {}).get('lookback', 30)
        self.logfib_config = VALIDATED_CONFIGS.get(instrument, VALIDATED_CONFIGS['silver'])
    
    def calculate_vector_trend(self, data: pd.DataFrame, idx: int) -> Dict:
        """Calculate vector trend at given index."""
        lookback = self.vector_lb
        
        if idx < lookback:
            return {'trend': 'NEUTRAL', 'score': 0}
        
        # Get swing high/low
        window_high = data['high'].iloc[idx-lookback:idx+1].max()
        window_low = data['low'].iloc[idx-lookback:idx+1].min()
        
        high_window = data['high'].iloc[idx-lookback:idx+1]
        low_window = data['low'].iloc[idx-lookback:idx+1]
        
        hb = int(abs(high_window[::-1].idxmax() - high_window.index[-1]))
        lb = int(abs(low_window[::-1].idxmin() - low_window.index[-1]))
        
        denominator = max(hb - lb, lb - hb) if hb != lb else 1
        demand_vector = (window_high - window_low) / max(denominator, 1)
        
        current_price = data['close'].iloc[idx]
        
        # Calculate projections
        main_high_vec = window_high - (demand_vector * hb)
        main_low_vec = window_low + (demand_vector * lb)
        
        # Determine trend
        if current_price > main_high_vec and current_price > main_low_vec:
            trend = 'STRONG_BULLISH'
            score = 100
        elif current_price > main_low_vec:
            trend = 'BULLISH'
            score = 70
        elif current_price < main_high_vec and current_price < main_low_vec:
            trend = 'STRONG_BEARISH'
            score = 100
        elif current_price < main_high_vec:
            trend = 'BEARISH'
            score = 70
        else:
            trend = 'NEUTRAL'
            score = 30
        
        return {
            'trend': trend,
            'score': score,
            'swing_high': window_high,
            'swing_low': window_low,
            'hb': hb,
            'lb': lb,
            'demand_vector': demand_vector,
            'main_high_vec': main_high_vec,
            'main_low_vec': main_low_vec,
        }
    
    def calculate_logfib_setup(self, data: pd.DataFrame, idx: int) -> Dict:
        """Calculate Log-Fib setup at given index."""
        lookback = self.logfib_config['lookback']
        mult = self.logfib_config['mult']
        
        if idx < lookback:
            return {'setup': None}
        
        # Find swing high/low
        swing_high = data['high'].iloc[idx-lookback:idx+1].max()
        swing_low = data['low'].iloc[idx-lookback:idx+1].min()
        
        # Determine pivot (most recent extreme)
        recent_high = data['high'].iloc[idx]
        recent_low = data['low'].iloc[idx]
        
        # Calculate effective range (Log-Fib formula)
        if recent_high > (swing_high + swing_low) / 2:
            pivot = swing_high
            anchor = swing_low
            direction = 'SHORT'
        else:
            pivot = swing_low
            anchor = swing_high
            direction = 'LONG'
        
        effective_range = np.log10(pivot) * abs(pivot - anchor) * mult * 4
        
        # Calculate levels
        entry_ratio = self.logfib_config['entry']
        tp_ratio = self.logfib_config['tp']
        sl_ratio = self.logfib_config['sl']
        
        if direction == 'SHORT':
            entry = pivot - (entry_ratio * effective_range)
            tp = pivot - (tp_ratio * effective_range)
            sl = pivot + (sl_ratio * effective_range)
        else:
            entry = pivot + (entry_ratio * effective_range)
            tp = pivot + (tp_ratio * effective_range)
            sl = pivot - (sl_ratio * effective_range)
        
        return {
            'direction': direction,
            'pivot': pivot,
            'anchor': anchor,
            'effective_range': effective_range,
            'entry': entry,
            'tp': tp,
            'sl': sl,
            'setup': 'READY',
        }
    
    def analyze(self, data: pd.DataFrame, idx: int) -> Dict:
        """Full hybrid analysis at given index."""
        vector = self.calculate_vector_trend(data, idx)
        logfib = self.calculate_logfib_setup(data, idx)
        
        current_price = data['close'].iloc[idx]
        
        # Determine if signals align
        signal = 'WAIT'
        direction = 'NEUTRAL'
        
        if vector['trend'] in ['STRONG_BULLISH', 'BULLISH'] and logfib.get('direction') == 'LONG':
            signal = 'ENTER'
            direction = 'LONG'
        elif vector['trend'] in ['STRONG_BEARISH', 'BEARISH'] and logfib.get('direction') == 'SHORT':
            signal = 'ENTER'
            direction = 'SHORT'
        
        # Calculate confluence score
        confluence = 0
        
        # Vector trend strength (0-40)
        confluence += vector['score'] * 0.4
        
        # Log-Fib setup quality (0-30)
        if logfib.get('setup') == 'READY':
            # Check if price is near entry
            entry = logfib.get('entry', current_price)
            price_diff = abs(current_price - entry) / current_price
            if price_diff < 0.001:  # Within 0.1%
                confluence += 30
            elif price_diff < 0.005:
                confluence += 20
            else:
                confluence += 10
        
        # Direction alignment (0-30)
        if direction != 'NEUTRAL':
            confluence += 30
        
        return {
            'vector': vector,
            'logfib': logfib,
            'signal': signal,
            'direction': direction,
            'confluence': min(confluence, 100),
            'current_price': current_price,
        }


# ============================================================================
# BACKTESTER
# ============================================================================

class HybridBacktester:
    """Backtest the hybrid strategy."""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
    
    def run(self, data: pd.DataFrame, instrument: str = 'silver') -> Dict:
        """Run backtest."""
        strategy = VectorLogFibHybrid(instrument=instrument)
        
        trades = []
        capital = self.initial_capital
        position = None
        
        # Warmup period
        warmup = max(strategy.vector_lb, strategy.logfib_config['lookback']) + 10
        
        for i in range(warmup, len(data)):
            analysis = strategy.analyze(data, i)
            current_price = data['close'].iloc[i]
            timestamp = data['datetime'].iloc[i]
            
            # Entry
            if position is None and analysis['signal'] == 'ENTER':
                # Only enter on high confluence
                if analysis['confluence'] >= 60:
                    logfib = analysis['logfib']
                    size = capital * 0.1 / current_price  # 10% position
                    
                    position = {
                        'direction': analysis['direction'],
                        'entry_price': logfib['entry'],
                        'size': size,
                        'tp': logfib['tp'],
                        'sl': logfib['sl'],
                        'entry_time': timestamp,
                        'confluence': analysis['confluence'],
                    }
            
            # Exit
            elif position is not None:
                pnl = 0
                exit_reason = None
                exit_price = 0
                
                if position['direction'] == 'LONG':
                    # Check TP
                    if data['high'].iloc[i] >= position['tp']:
                        exit_price = position['tp']
                        pnl = (exit_price - position['entry_price']) * position['size']
                        exit_reason = 'TP'
                    # Check SL
                    elif data['low'].iloc[i] <= position['sl']:
                        exit_price = position['sl']
                        pnl = (exit_price - position['entry_price']) * position['size']
                        exit_reason = 'SL'
                else:  # SHORT
                    # Check TP
                    if data['low'].iloc[i] <= position['tp']:
                        exit_price = position['tp']
                        pnl = (position['entry_price'] - exit_price) * position['size']
                        exit_reason = 'TP'
                    # Check SL
                    elif data['high'].iloc[i] >= position['sl']:
                        exit_price = position['sl']
                        pnl = (position['entry_price'] - exit_price) * position['size']
                        exit_reason = 'SL'
                
                if exit_reason:
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': timestamp,
                        'direction': position['direction'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'exit_reason': exit_reason,
                        'confluence': position['confluence'],
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
            'instrument': instrument,
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
    
    if 'time' in df.columns:
        df['datetime'] = pd.to_datetime(df['time'])
    elif 'datetime' not in df.columns:
        df['datetime'] = pd.to_datetime(df.iloc[:, 0])
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=['open', 'high', 'low', 'close'])
    return df


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    import sys
    
    SILVER_DATA = '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAGUSD5.csv'
    GOLD_DATA = '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv'
    
    print("=" * 80)
    print("PAL VECTOR + LOG-FIB HYBRID - Optimized Trend Following")
    print("=" * 80)
    
    # Test both instruments
    for instrument in ['silver', 'gold']:
        csv_path = GOLD_DATA if instrument == 'gold' else SILVER_DATA
        
        print(f"\n{'=' * 80}")
        print(f"INSTRUMENT: {instrument.upper()}")
        print(f"{'=' * 80}")
        
        try:
            data = load_data(csv_path)
            print(f"📈 Bars: {len(data)} | Range: {data['datetime'].iloc[0].date()} → {data['datetime'].iloc[-1].date()}")
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
        
        # Run backtest
        backtester = HybridBacktester(initial_capital=100000)
        results = backtester.run(data, instrument)
        
        if 'error' not in results:
            print(f"\n📊 PERFORMANCE METRICS:")
            print(f"   Total Trades: {results['total_trades']}")
            print(f"   Win Rate: {results['win_rate']:.2f}%")
            print(f"   Total P&L: ${results['total_pnl']:,.2f}")
            print(f"   Return: {results['return_pct']:.2f}%")
            print(f"   Profit Factor: {results['profit_factor']:.2f}")
            print(f"   Avg P&L/Trade: ${results['avg_pnl_per_trade']:.2f}")
            print(f"   Final Capital: ${results['final_capital']:,.2f}")
            
            # Save results
            output_file = f'/home/palbot/Projects/log-fib-scalper/hybrid_results_{instrument}.json'
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Saved: {output_file}")
        else:
            print(f"\n❌ {results['error']}")
    
    print("\n" + "=" * 80)
