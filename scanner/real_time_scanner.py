#!/usr/bin/env python3
"""
Geometric Confluence Real-Time Scanner
======================================

Scans live market data for high-confluence setups based on:
1. 0.382 Fib retracement
2. Fib number candle counts (13, 21, 34, 55)
3. Gann price-time squares
4. Markov reversal patterns (80-85% probability)

Generates alerts when confluence score ≥ 70/100.

Usage:
  python real_time_scanner.py --instrument silver --interval 5m
  python real_time_scanner.py --scan  # Scan all instruments
"""

import pandas as pd
import numpy as np
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Import from strategy
sys.path.insert(0, str(Path(__file__).parent.parent / 'strategies'))
from geometric_confluence_scalper import (
    GeometricConfluenceScalper, 
    SwingDetector,
    GeometricAnalyzer,
    load_data,
    OPTIMAL_CONFIGS,
    FIB_NUMBERS,
    MIN_CONFLUENCE_SCORE,
)

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_PATHS = {
    'silver': '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAGUSD5.csv',
    'gold': '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv',
    'nifty': '/home/palbot/Projects/log-fib-scalper/zerodha_data/NIFTY_50_5minute_20260319_20260518.csv',
    'banknifty': '/home/palbot/Projects/log-fib-scalper/zerodha_data/BANKNIFTY1_5minute_20260320_20260519.csv',
}

ALERT_LOG_PATH = '/home/palbot/Projects/log-fib-scalper/scanner/alerts.log'
ALERT_HISTORY_PATH = '/home/palbot/Projects/log-fib-scalper/scanner/alert_history.json'

# Alert thresholds
HIGH_CONFLUENCE = 70  # Send alert
MEDIUM_CONFLUENCE = 50  # Log only

# ============================================================================
# SCANNER ENGINE
# ============================================================================

class RealTimeScanner:
    """Real-time geometric confluence scanner."""
    
    def __init__(self, instrument: str = 'silver'):
        self.instrument = instrument
        self.config = OPTIMAL_CONFIGS.get(instrument, {}).get('best', {})
        self.scalper = GeometricConfluenceScalper(instrument, self.config)
        self.alerts = []
        self.load_alert_history()
    
    def load_alert_history(self):
        """Load previous alerts to avoid duplicates."""
        try:
            with open(ALERT_HISTORY_PATH, 'r') as f:
                self.alert_history = json.load(f)
        except:
            self.alert_history = []
        
        # Keep only last 1000 alerts
        self.alert_history = self.alert_history[-1000:]
        
        # Cleanup: Mark very old setups as expired (safety net)
        self._cleanup_old_setups()
    
    def _cleanup_old_setups(self):
        """Mark setups older than 100 bars as expired (safety cleanup)."""
        if not self.alert_history:
            return
        
        # Find current bar (max bar index in history for this instrument)
        current_bar = max([a.get('bar', 0) for a in self.alert_history if a.get('instrument') == self.instrument], default=0)
        expired_count = 0
        
        for alert in self.alert_history:
            if alert.get('instrument') != self.instrument:
                continue
            if alert.get('status') in ['resolved', 'expired']:
                continue
            
            bar_diff = current_bar - alert.get('bar', 0)
            if bar_diff > 100:  # Safety net: 100 bars = ~8 hours on 5m
                alert['status'] = 'expired'
                alert['exit_reason'] = 'timeout'
                expired_count += 1
        
        if expired_count > 0:
            print(f"  [CLEANUP] Marked {expired_count} old setups as expired")
            self.save_alert_history()
    
    def save_alert_history(self):
        """Save alert history."""
        Path(ALERT_HISTORY_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(ALERT_HISTORY_PATH, 'w') as f:
            json.dump(self.alert_history, f, indent=2)
    
    def check_setup_status(self, signal: dict, data: pd.DataFrame) -> dict:
        """
        Check if a setup is new, duplicate, expired, or resolved.
        Uses setup signature (not timestamps) for robust duplicate detection.
        Returns: {'status': 'new'|'duplicate'|'expired'|'resolved', 'reason': str}
        """
        current_bar = signal['bar']
        current_price = data['close'].iloc[current_bar]
        current_time = data['datetime'].iloc[current_bar]
        direction = signal['direction']
        entry_price = signal['entry_price']
        tp_price = signal['tp_price']
        sl_price = signal['sl_price']
        
        # Configuration
        MAX_AGE_BARS = 50  # Setup expires after 50 bars (~4 hours on 5m)
        COOLDOWN_BARS = 30  # Opposite direction cooldown (~2.5 hours)
        
        # Create setup signature for duplicate detection
        # Round entry to 0.1% for grouping similar setups
        entry_rounded = round(entry_price * 1000) / 1000
        setup_sig = f"{direction}_{entry_rounded}"
        
        for prev in self.alert_history[-100:]:  # Check last 100 alerts
            if prev['instrument'] != self.instrument:
                continue
            
            prev_direction = prev['direction']
            prev_entry = prev['entry']
            prev_tp = prev.get('tp', 0)
            prev_sl = prev.get('sl', 0)
            prev_bar = prev.get('bar', 0)
            prev_status = prev.get('status', 'active')  # Default to 'active' for old alerts
            
            # Calculate bar difference
            bar_diff = current_bar - prev_bar
            
            # === CHECK 0: Active Setup Tracking (by signature) ===
            # If there's an ACTIVE setup with same direction and similar entry, skip
            if prev_status == 'active' and prev_direction == direction:
                prev_entry_rounded = round(prev_entry * 1000) / 1000
                if abs(prev_entry_rounded - entry_rounded) < 0.5:  # 0.5% tolerance
                    return {'status': 'duplicate', 'reason': f'{direction} setup already active (entry: {prev_entry:.4f})'}
            
            # Skip already resolved/expired setups for remaining checks
            if prev_status in ['resolved', 'expired']:
                continue
            
            # === CHECK 1: Setup Expiration (by bar count) ===
            if bar_diff > MAX_AGE_BARS:
                # Mark old setup as expired
                prev['status'] = 'expired'
                prev['exit_reason'] = 'timeout'
                print(f"  [EXPIRED] {self.instrument.upper()} {prev_direction} setup from bar {prev_bar} expired (>50 bars)")
                continue
            
            # === CHECK 2: TP/SL Resolution ===
            if prev_tp > 0 and prev_sl > 0 and prev_bar < len(data):
                if prev_direction == 'SHORT':
                    # Check if SHORT hit TP (price went down) or SL (price went up)
                    min_price_since = data['low'].iloc[prev_bar:current_bar+1].min()
                    max_price_since = data['high'].iloc[prev_bar:current_bar+1].max()
                    
                    if min_price_since <= prev_tp:
                        prev['status'] = 'resolved'
                        prev['exit_reason'] = 'TP'
                        prev['exit_price'] = prev_tp
                        print(f"  [RESOLVED] {self.instrument.upper()} {prev_direction} hit TP @ {prev_tp:.4f}")
                        continue
                    if max_price_since >= prev_sl:
                        prev['status'] = 'resolved'
                        prev['exit_reason'] = 'SL'
                        prev['exit_price'] = prev_sl
                        print(f"  [RESOLVED] {self.instrument.upper()} {prev_direction} hit SL @ {prev_sl:.4f}")
                        continue
                else:  # LONG
                    # Check if LONG hit TP (price went up) or SL (price went down)
                    max_price_since = data['high'].iloc[prev_bar:current_bar+1].max()
                    min_price_since = data['low'].iloc[prev_bar:current_bar+1].min()
                    
                    if max_price_since >= prev_tp:
                        prev['status'] = 'resolved'
                        prev['exit_reason'] = 'TP'
                        prev['exit_price'] = prev_tp
                        print(f"  [RESOLVED] {self.instrument.upper()} {prev_direction} hit TP @ {prev_tp:.4f}")
                        continue
                    if min_price_since <= prev_sl:
                        prev['status'] = 'resolved'
                        prev['exit_reason'] = 'SL'
                        prev['exit_price'] = prev_sl
                        print(f"  [RESOLVED] {self.instrument.upper()} {prev_direction} hit SL @ {prev_sl:.4f}")
                        continue
            
            # === CHECK 3: Cooldown (opposite direction) ===
            if prev_direction != direction:
                if 0 < bar_diff < COOLDOWN_BARS:
                    return {'status': 'cooldown', 'reason': f'Opposite {prev_direction} setup {bar_diff} bars ago (cooldown: {COOLDOWN_BARS})'}
        
        return {'status': 'new', 'reason': 'Valid new setup'}
    
    def scan(self, data: pd.DataFrame) -> list:
        """Scan latest bar for confluence."""
        current_idx = len(data) - 1
        
        # Get signal
        signal = self.scalper._scan_bar(data, current_idx)
        
        if signal.get('ready') and signal['score'] >= MIN_CONFLUENCE_SCORE:
            # Check setup status (new, duplicate, expired, resolved)
            status = self.check_setup_status(signal, data)
            
            if status['status'] != 'new':
                # Setup not valid - log reason
                print(f"  [SKIP] {self.instrument.upper()} {signal['direction']} @ {data['close'].iloc[current_idx]:.4f} - {status['reason']} (Score: {signal['score']:.1f})")
                return []
            
            alert = {
                'timestamp': datetime.now().isoformat(),
                'instrument': self.instrument,
                'bar': current_idx,
                'datetime': data['datetime'].iloc[current_idx].isoformat(),
                'price': data['close'].iloc[current_idx],
                'direction': signal['direction'],
                'score': signal['score'],
                'entry': signal['entry_price'],
                'tp': signal['tp_price'],
                'sl': signal['sl_price'],
                'breakdown': signal['breakdown'],
                'status': 'active',  # Track setup lifecycle
            }
            
            self.alerts.append(alert)
            self.alert_history.append(alert)
            self.save_alert_history()
            
            return [alert]
        
        return []
    
    def scan_file(self, filepath: str) -> list:
        """Scan latest bar only for confluence setups."""
        data = load_data(filepath)
        alerts = []
        
        print(f"Scanning latest bar of {self.instrument.upper()} (bar {len(data)-1})...")
        
        # Only scan the latest bar
        signals = self.scan(data)
        alerts.extend(signals)
        
        return alerts


# ============================================================================
# ALERT FORMATTING
# ============================================================================

def format_alert_telegram(alert: dict) -> str:
    """Format alert for Telegram."""
    breakdown = alert['breakdown']
    
    msg = f"""🎯 *GEOMETRIC CONFLUENCE ALERT*

📊 Instrument: {alert['instrument'].upper()}
⏰ Time: {alert['datetime'].split('T')[0]} {alert['datetime'].split('T')[1][:8]}
💰 Price: {alert['price']:.4f}

📈 Direction: *{alert['direction']}*
🎯 Entry: {alert['entry']:.4f}
🎯 TP: {alert['tp']:.4f}
🛑 SL: {alert['sl']:.4f}

🔮 *Confluence Score: {alert['score']:.1f}/100*

📐 *Geometric Breakdown:*
• Fib Time: {breakdown['fib_time']['candle_count']} bars (near {breakdown['fib_time']['nearest_fib']}) - {breakdown['fib_time']['score']:.0f}/100
• Gann Square: {breakdown['gann_square']['ratio']:.2f}x ({breakdown['gann_square']['ratio_type']}) - {breakdown['gann_square']['score']:.0f}/100
• Markov: Pattern {breakdown['markov_pattern']['pattern']} ({breakdown['markov_pattern']['reversal_prob']*100:.0f}% rev) - {breakdown['markov_pattern']['score']:.0f}/100
• Fib Retrace: {breakdown['fib_retracement']['ratio']:.3f} (dist: {breakdown['fib_retracement']['distance_to_0.382']:.3f}) - {breakdown['fib_retracement']['score']:.0f}/100

⚡ *Action:* Watch for entry at {alert['entry']:.4f}"""
    
    return msg


def format_alert_console(alert: dict) -> str:
    """Format alert for console output."""
    return f"""
{'='*70}
🎯 GEOMETRIC CONFLUENCE ALERT
{'='*70}
Instrument: {alert['instrument'].upper()}
Time: {alert['datetime']}
Price: {alert['price']:.4f}

Direction: {alert['direction']}
Entry: {alert['entry']:.4f}
TP: {alert['tp']:.4f}
SL: {alert['sl']:.4f}

Confluence Score: {alert['score']:.1f}/100

Geometric Breakdown:
  Fib Time: {alert['breakdown']['fib_time']['candle_count']} bars (near {alert['breakdown']['fib_time']['nearest_fib']})
  Gann Ratio: {alert['breakdown']['gann_square']['ratio']:.2f}x ({alert['breakdown']['gann_square']['ratio_type']})
  Markov Pattern: {alert['breakdown']['markov_pattern']['pattern']} ({alert['breakdown']['markov_pattern']['reversal_prob']*100:.0f}% reversal prob)
  Fib Retracement: {alert['breakdown']['fib_retracement']['ratio']:.3f} (dist to 0.382: {alert['breakdown']['fib_retracement']['distance_to_0.382']:.3f})
{'='*70}
"""


# ============================================================================
# LOGGING
# ============================================================================

def log_alert(alert: dict):
    """Log alert to file."""
    Path(ALERT_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    with open(ALERT_LOG_PATH, 'a') as f:
        f.write(f"\n{alert['timestamp']} | {alert['instrument'].upper()} | {alert['direction']} | Score: {alert['score']:.1f} | Price: {alert['price']:.4f}\n")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Geometric Confluence Scanner')
    parser.add_argument('--instrument', type=str, default='all',
                        choices=['silver', 'gold', 'nifty', 'banknifty', 'all'],
                        help='Instrument to scan')
    parser.add_argument('--scan', action='store_true',
                        help='Scan all instruments')
    parser.add_argument('--live', action='store_true',
                        help='Run in live mode (continuous scanning)')
    parser.add_argument('--interval', type=int, default=300,
                        help='Scan interval in seconds (for live mode)')
    
    args = parser.parse_args()
    
    print("="*70)
    print("GEOMETRIC CONFLUENCE REAL-TIME SCANNER")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Determine which instruments to scan
    if args.instrument == 'all' or args.scan:
        instruments = ['silver', 'gold', 'nifty', 'banknifty']
    else:
        instruments = [args.instrument]
    
    all_alerts = []
    
    for inst in instruments:
        scanner = RealTimeScanner(inst)
        alerts = scanner.scan_file(DATA_PATHS[inst])
        all_alerts.extend(alerts)
        
        # Print alerts
        for alert in alerts:
            print(format_alert_console(alert))
            log_alert(alert)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"SCAN COMPLETE")
    print(f"{'='*70}")
    print(f"Total Alerts: {len(all_alerts)}")
    
    if all_alerts:
        high_score = [a for a in all_alerts if a['score'] >= 70]
        med_score = [a for a in all_alerts if 50 <= a['score'] < 70]
        
        print(f"High Confluence (≥70): {len(high_score)}")
        print(f"Medium Confluence (50-69): {len(med_score)}")
        
        # Show best alert
        if high_score:
            best = max(high_score, key=lambda x: x['score'])
            print(f"\n🏆 Best Setup: {best['instrument'].upper()} {best['direction']} @ {best['price']:.4f} (Score: {best['score']:.1f})")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Alert log: {ALERT_LOG_PATH}")
    print(f"Alert history: {ALERT_HISTORY_PATH}")
    
    return all_alerts


if __name__ == '__main__':
    main()
