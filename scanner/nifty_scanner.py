#!/usr/bin/env python3
"""
NIFTY GEOMETRIC SCANNER
=======================
Scans NIFTY 50 for geometric confluence setups using the validated strategy.

Usage:
  python nifty_scanner.py --scan
  python nifty_scanner.py --show-signals
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import sys
import json
import glob

sys.path.insert(0, str(Path(__file__).parent.parent / 'strategies'))
from geometric_confluence_scalper import (
    GeometricConfluenceScalper,
    OPTIMAL_CONFIGS,
    MIN_CONFLUENCE_SCORE,
)

# ============================================================================
# NIFTY CONFIGURATION
# ============================================================================

# Nifty-specific Gann scaling (from strategy)
GANN_SCALING = 0.0002  # 1 bar ≈ 0.02% price move

# Optimal config for indices (using Silver's config as baseline, adjusted for Nifty volatility)
NIFTY_CONFIG = {
    'lookback': 6,
    'mult': 0.5,
    'entry': 0.382,
    'tp': 1.272,
    'sl': 1.618,
}

# Contract specs
CONTRACT_SIZE = 75  # Nifty lot size
TICK_VALUE = 0.05   # 0.05 index points
AUD_USD_RATE = 0.66

# ============================================================================
# SCANNER
# ============================================================================

class NiftyScanner:
    def __init__(self):
        self.scalper = GeometricConfluenceScalper()
        self.data_file = self._find_latest_data()
        
    def _find_latest_data(self):
        """Find the latest Nifty 5min data file."""
        data_dir = Path(__file__).parent.parent / 'zerodha_data'
        pattern = str(data_dir / 'NIFTY_50_5minute_*.csv')
        files = glob.glob(pattern)
        if not files:
            raise FileNotFoundError("No NIFTY_50_5minute_*.csv found in zerodha_data/")
        return max(files, key=lambda f: datetime.fromtimestamp(Path(f).stat().st_mtime))
    
    def load_data(self):
        """Load Nifty data."""
        df = pd.read_csv(self.data_file)
        
        # Standardize column names - Zerodha format: date, open, high, low, close, volume
        # Strategy expects: datetime, open, high, low, close
        if 'date' in df.columns and 'datetime' not in df.columns:
            df['datetime'] = pd.to_datetime(df['date'])
        elif 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        
        df = df.sort_values('datetime').reset_index(drop=True)
        return df
    
    def scan(self, min_score=MIN_CONFLUENCE_SCORE):
        """Scan for signals."""
        df = self.load_data()
        config = NIFTY_CONFIG
        
        # Get latest swing
        last_row = df.iloc[-1]
        current_price = last_row['close']
        current_idx = len(df) - 1
        
        # Run scalper analysis on latest bar
        signal = self.scalper._scan_bar(df, current_idx)
        
        # Check for signals
        signals = []
        if signal and signal.get('score', 0) >= min_score:
            signals.append({
                'direction': signal.get('direction', 'UNKNOWN'),
                'entry': signal.get('entry_price', 0),
                'tp': signal.get('tp_price', 0),
                'sl': signal.get('sl_price', 0),
                'score': signal.get('score', 0),
                'current_price': current_price,
                'timestamp': datetime.now().isoformat(),
            })
        
        return signals, current_price


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Nifty Geometric Scanner')
    parser.add_argument('--scan', action='store_true', help='Run scan')
    parser.add_argument('--show-signals', action='store_true', help='Show recent signals')
    args = parser.parse_args()
    
    scanner = NiftyScanner()
    
    print("=" * 70)
    print("NIFTY GEOMETRIC SCANNER")
    print("=" * 70)
    print(f"Data: {scanner.data_file}")
    print(f"Config: lookback={NIFTY_CONFIG['lookback']}, mult={NIFTY_CONFIG['mult']}, entry={NIFTY_CONFIG['entry']}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if args.scan:
        signals, current_price = scanner.scan()
        
        print(f"Scanning NIFTY @ {current_price:.2f}...")
        print()
        
        if signals:
            for sig in signals:
                print("=" * 70)
                print(f"🎯 NIFTY GEOMETRIC ALERT - {sig['direction']}")
                print("=" * 70)
                print(f"Setup Details:")
                print(f"  Direction: {sig['direction']}")
                print(f"  Entry: {sig['entry']:.2f}")
                print(f"  TP: {sig['tp']:.2f}")
                print(f"  SL: {sig['sl']:.2f}")
                print(f"  Score: {sig['score']:.1f}/100")
                print(f"  Current: {sig['current_price']:.2f}")
                print()
                
                # Position sizing
                if sig['direction'] == 'LONG':
                    risk_pts = sig['current_price'] - sig['sl']
                    reward_pts = sig['tp'] - sig['current_price']
                else:
                    risk_pts = sig['sl'] - sig['current_price']
                    reward_pts = sig['current_price'] - sig['tp']
                
                lots = 1  # 1 lot = 75 shares
                risk_inr = risk_pts * CONTRACT_SIZE * lots
                reward_inr = reward_pts * CONTRACT_SIZE * lots
                
                print(f"Position Sizing (1 lot = 75 shares):")
                print(f"  Risk: ₹{risk_inr:.2f} INR")
                print(f"  Reward: ₹{reward_inr:.2f} INR")
                print(f"  R:R: 1:{reward_inr/risk_inr:.2f}" if risk_inr > 0 else "  R:R: N/A")
                print("=" * 70)
        else:
            print("No signals found meeting minimum score threshold.")
            print("Scan completed successfully.")
    
    elif args.show_signals:
        # Show alert history
        history_file = Path(__file__).parent / 'alert_history.json'
        if history_file.exists():
            with open(history_file) as f:
                history = json.load(f)
            nifty_signals = [s for s in history if s.get('instrument') == 'nifty']
            print(f"Recent Nifty signals: {len(nifty_signals)}")
            for sig in nifty_signals[-5:]:
                print(f"  {sig['timestamp']}: {sig['direction']} @ {sig['entry']}")
        else:
            print("No alert history found.")


if __name__ == '__main__':
    main()
