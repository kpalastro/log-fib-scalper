#!/usr/bin/env python3
"""
CFD SCALPING SCANNER - Gold & Silver
=====================================
Optimized for quick scalping with tight stops targeting $700-1000 AUD per trade.

Key differences from swing scanner:
- Tighter stops (0.5-0.8% Gold, 1-2% Silver)
- Quick targets (1:1.5 to 1:2 R:R)
- Position sizing for target profit
- Higher frequency setups

Usage:
  python scalping_scanner.py --scan
  python scalping_scanner.py --instrument gold --show-position
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent.parent / 'strategies'))
from geometric_confluence_scalper import (
    GeometricConfluenceScalper,
    OPTIMAL_CONFIGS,
    MIN_CONFLUENCE_SCORE,
)

# ============================================================================
# SCALPING CONFIGURATION
# ============================================================================

# Account settings
ACCOUNT_SIZE_AUD = 10000  # Assumed account size
TARGET_PROFIT_AUD = 800   # Target per trade ($700-1000 range)
MAX_RISK_PER_TRADE = 0.02  # 2% max risk

# Scalping-specific thresholds
SCALPING_MIN_SCORE = 25  # Lower threshold for more frequent setups

# Instrument specs (CFD contract details)
INSTRUMENT_SPECS = {
    'gold': {
        'contract_size': 100,      # 100 oz per standard lot
        'tick_value': 0.10,         # $0.10 per 0.10 move
        'currency': 'USD',
        'aud_usd_rate': 0.66,       # Convert USD to AUD
        'typical_spread': 0.30,     # $0.30 typical spread
        'min_stop_pct': 0.003,      # 0.3% minimum stop
        'max_stop_pct': 0.015,      # 1.5% maximum stop for scalping (increased)
    },
    'silver': {
        'contract_size': 5000,      # 5000 oz per standard lot
        'tick_value': 0.005,        # $0.005 per 0.005 move
        'currency': 'USD',
        'aud_usd_rate': 0.66,
        'typical_spread': 0.02,     # $0.02 typical spread
        'min_stop_pct': 0.005,      # 0.5% minimum stop (reduced from 1%)
        'max_stop_pct': 0.03,       # 3% maximum stop for scalping
    }
}

# ============================================================================
# POSITION SIZING CALCULATOR
# ============================================================================

class PositionSizer:
    """Calculate optimal position size for scalping targets."""
    
    def __init__(self, account_size: float = ACCOUNT_SIZE_AUD, target_profit: float = TARGET_PROFIT_AUD):
        self.account_size = account_size
        self.target_profit = target_profit
    
    def calculate(self, instrument: str, entry: float, tp: float, sl: float) -> dict:
        """
        Calculate position size for target profit.
        
        Returns:
            dict with lots, risk_aud, reward_aud, r_ratio, position_value
        """
        specs = INSTRUMENT_SPECS[instrument]
        
        # Calculate stop distance
        stop_distance = abs(entry - sl)
        stop_distance_pct = stop_distance / entry
        
        # Check if stop is within acceptable scalping range
        if stop_distance_pct < specs['min_stop_pct']:
            status = 'TOO_TIGHT'
            reason = f"Stop {stop_distance_pct:.2%} < min {specs['min_stop_pct']:.2%}"
        elif stop_distance_pct > specs['max_stop_pct']:
            status = 'TOO_WIDE'
            reason = f"Stop {stop_distance_pct:.2%} > max {specs['max_stop_pct']:.2%} for scalping"
        else:
            status = 'OK'
            reason = 'Stop within scalping range'
        
        # Calculate reward:risk distance
        reward_distance = abs(tp - entry)
        
        # Position size to achieve target profit
        if reward_distance > 0:
            # For Gold: 1 lot = 100 oz, $1 move = $100
            # For Silver: 1 lot = 5000 oz, $0.01 move = $50
            lots_needed = self.target_profit / (reward_distance * specs['contract_size'] * specs['aud_usd_rate'])
        else:
            lots_needed = 0
        
        # Round to practical lot sizes
        if instrument == 'gold':
            lots = round(lots_needed, 2)  # Gold: 0.01 lot precision
        else:
            lots = round(lots_needed, 1)  # Silver: 0.1 lot precision
        
        # Calculate actual risk and reward
        risk_per_lot = stop_distance * specs['contract_size']
        reward_per_lot = reward_distance * specs['contract_size']
        
        risk_aud = risk_per_lot * lots * specs['aud_usd_rate']
        reward_aud = reward_per_lot * lots * specs['aud_usd_rate']
        
        # Position value (margin required)
        position_value = entry * specs['contract_size'] * lots
        margin_required = position_value * 0.02  # Assuming 50:1 leverage (2% margin)
        
        # Risk as % of account
        risk_pct = risk_aud / self.account_size
        
        return {
            'status': status,
            'reason': reason,
            'lots': lots,
            'risk_aud': round(risk_aud, 2),
            'reward_aud': round(reward_aud, 2),
            'r_ratio': round(reward_distance / stop_distance, 2) if stop_distance > 0 else 0,
            'position_value': round(position_value, 2),
            'margin_required': round(margin_required, 2),
            'risk_pct': round(risk_pct * 100, 2),
            'stop_distance': round(stop_distance, 4),
            'stop_distance_pct': round(stop_distance_pct * 100, 3),
            'reward_distance': round(reward_distance, 4),
        }


# ============================================================================
# SCALPING SCANNER
# ============================================================================

class ScalpingScanner:
    """Scan for scalping setups with tight stops."""
    
    def __init__(self, instrument: str = 'gold'):
        self.instrument = instrument
        self.config = OPTIMAL_CONFIGS.get(instrument, {}).get('scalping', {})
        self.scalper = GeometricConfluenceScalper(instrument, self.config)
        self.sizer = PositionSizer()
    
    def scan(self, data: pd.DataFrame) -> dict:
        """Scan latest bar for scalping setup."""
        current_idx = len(data) - 1
        signal = self.scalper._scan_bar(data, current_idx)
        
        result = {
            'found': False,
            'signal': signal,
            'position': None,
        }
        
        # Override 'ready' check - use scalping threshold instead of MIN_CONFLUENCE_SCORE
        # Signal is valid if score >= SCALPING_MIN_SCORE (25)
        if signal.get('score', 0) >= SCALPING_MIN_SCORE:
            # Calculate position sizing
            position = self.sizer.calculate(
                self.instrument,
                signal['entry_price'],
                signal['tp_price'],
                signal['sl_price']
            )
            
            # Only valid if stop is acceptable for scalping
            if position['status'] == 'OK':
                result['found'] = True
                result['position'] = position
        
        return result


# ============================================================================
# REPORT FORMATTING
# ============================================================================

def format_scalping_alert(instrument: str, signal: dict, position: dict) -> str:
    """Format scalping alert with position sizing."""
    specs = INSTRUMENT_SPECS[instrument]
    
    msg = f"""🎯 *CFD SCALPING ALERT* - {instrument.upper()}

📊 *Setup Details:*
• Direction: **{signal['direction']}**
• Entry: ${signal['entry_price']:.4f}
• TP: ${signal['tp_price']:.4f}
• SL: ${signal['sl_price']:.4f}
• Score: {signal['score']:.1f}/100

💰 *Position Sizing (Target: ${TARGET_PROFIT_AUD} AUD):*
• Lots: **{position['lots']}**
• Risk: ${position['risk_aud']:.2f} AUD ({position['risk_pct']:.1f}% account)
• Reward: ${position['reward_aud']:.2f} AUD
• R:R: 1:{position['r_ratio']}
• Margin: ${position['margin_required']:.2f} AUD

📐 *Stop Analysis:*
• Stop Distance: ${position['stop_distance']:.4f} ({position['stop_distance_pct']:.2f}%)
• Range: {specs['min_stop_pct']*100:.1f}% - {specs['max_stop_pct']*100:.1f}% ✓

⚡ *Action:* Enter {signal['direction']} at {signal['entry_price']:.4f}"""

    return msg


def format_console_report(instrument: str, signal: dict, position: dict) -> str:
    """Console format for scalping alert."""
    return f"""
{'='*70}
🎯 CFD SCALPING ALERT - {instrument.upper()}
{'='*70}

Setup Details:
  Direction: {signal['direction']}
  Entry: ${signal['entry_price']:.4f}
  TP: ${signal['tp_price']:.4f}
  SL: ${signal['sl_price']:.4f}
  Score: {signal['score']:.1f}/100

Position Sizing (Target: ${TARGET_PROFIT_AUD} AUD):
  Lots: {position['lots']}
  Risk: ${position['risk_aud']:.2f} AUD ({position['risk_pct']:.1f}% of account)
  Reward: ${position['reward_aud']:.2f} AUD
  R:R Ratio: 1:{position['r_ratio']}
  Margin Required: ${position['margin_required']:.2f} AUD

Stop Analysis:
  Stop Distance: ${position['stop_distance']:.4f} ({position['stop_distance_pct']:.2f}%)
  Acceptable Range: {INSTRUMENT_SPECS[instrument]['min_stop_pct']*100:.1f}% - {INSTRUMENT_SPECS[instrument]['max_stop_pct']*100:.1f}%
  Status: {position['status']} - {position['reason']}
{'='*70}
"""


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def load_data(filepath: str) -> pd.DataFrame:
    """Load data from CSV."""
    df = pd.read_csv(filepath)
    df['datetime'] = pd.to_datetime(df['time'])
    return df


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='CFD Scalping Scanner')
    parser.add_argument('--instrument', type=str, default='all',
                        choices=['gold', 'silver', 'all'],
                        help='Instrument to scan')
    parser.add_argument('--scan', action='store_true',
                        help='Scan for setups')
    parser.add_argument('--account-size', type=float, default=ACCOUNT_SIZE_AUD,
                        help=f'Account size in AUD (default: {ACCOUNT_SIZE_AUD})')
    parser.add_argument('--target', type=float, default=TARGET_PROFIT_AUD,
                        help=f'Target profit in AUD (default: {TARGET_PROFIT_AUD})')
    
    args = parser.parse_args()
    
    print("="*70)
    print("CFD SCALPING SCANNER - Gold & Silver")
    print("="*70)
    print(f"Account: ${args.account_size:.2f} AUD | Target: ${args.target:.2f} AUD/trade")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if args.instrument == 'all' or args.scan:
        instruments = ['gold', 'silver']
    else:
        instruments = [args.instrument]
    
    alerts = []
    
    for inst in instruments:
        # Load latest data
        if inst == 'gold':
            data_path = '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv'
        else:
            data_path = '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAGUSD5.csv'
        
        data = load_data(data_path)
        current_price = data['close'].iloc[-1]
        
        print(f"Scanning {inst.upper()} @ ${current_price:.4f}...")
        
        # Scan
        scanner = ScalpingScanner(inst)
        result = scanner.scan(data)
        
        if result['found']:
            signal = result['signal']
            position = result['position']
            
            print(format_console_report(inst, signal, position))
            
            alerts.append({
                'instrument': inst,
                'signal': signal,
                'position': position,
            })
        else:
            if result['signal'].get('ready'):
                # Setup found but stop too wide/tight
                pos = scanner.sizer.calculate(
                    inst,
                    result['signal']['entry_price'],
                    result['signal']['tp_price'],
                    result['signal']['sl_price']
                )
                print(f"  ⚠️ Setup found but {pos['status']}: {pos['reason']}")
            else:
                print(f"  No valid scalping setup (Score: {result['signal'].get('score', 0):.1f})")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"SCAN COMPLETE")
    print(f"{'='*70}")
    print(f"Total Scalping Alerts: {len(alerts)}")
    
    if alerts:
        print(f"\n💰 Combined Target Profit: ${sum(a['position']['reward_aud'] for a in alerts):.2f} AUD")
        print(f"📊 Combined Risk: ${sum(a['position']['risk_aud'] for a in alerts):.2f} AUD")
        print(f"📈 Total Margin Required: ${sum(a['position']['margin_required'] for a in alerts):.2f} AUD")
    else:
        print("\nNo valid scalping setups found.")
        print("   - Swing scanner may have setups with wider stops")
        print("   - Wait for tighter consolidation patterns")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return alerts


if __name__ == '__main__':
    main()
