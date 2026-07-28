"""
COMPLETE LIVE MONITORING SYSTEM
================================
1. Fetches live Gold/Silver data from Yahoo Finance
2. Scans all 4 instruments for geometric confluence
3. Sends alerts when setups detected

Usage:
    python live_monitor.py                    # One-time scan with data refresh
    python live_monitor.py --live             # Continuous monitoring
    python live_monitor.py --interval 300     # Custom interval (seconds)
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path('/home/palbot/Projects/log-fib-scalper')
sys.path.insert(0, str(PROJECT_ROOT))

def fetch_live_data():
    """Fetch latest Gold & Silver data from Yahoo Finance."""
    print("=" * 70)
    print("📡 FETCHING LIVE DATA")
    print("=" * 70)
    
    # Fetch Gold
    print("\n🥇 GOLD...")
    result = subprocess.run([
        'python', str(PROJECT_ROOT / 'data/yahoo_live_fetcher.py'),
        '--instrument', 'gold',
        '--period', '5d',
        '--interval', '5m'
    ], capture_output=False)
    
    # Fetch Silver
    print("\n🥈 SILVER...")
    result = subprocess.run([
        'python', str(PROJECT_ROOT / 'data/yahoo_live_fetcher.py'),
        '--instrument', 'silver',
        '--period', '5d',
        '--interval', '5m'
    ], capture_output=False)
    
    return result.returncode == 0

def scan_instruments():
    """Scan all instruments for confluence setups."""
    print("\n" + "=" * 70)
    print("🔍 SCANNING FOR SETUPS")
    print("=" * 70)
    
    result = subprocess.run([
        'python', str(PROJECT_ROOT / 'scanner/real_time_scanner.py'),
        '--scan'
    ], capture_output=False)
    
    return result.returncode == 0

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Live Monitoring System')
    parser.add_argument('--live', action='store_true',
                        help='Run in continuous mode')
    parser.add_argument('--interval', type=int, default=300,
                        help='Update interval in seconds (default: 300)')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🎯 GEOMETRIC CONFLUENCE LIVE MONITOR")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'LIVE (continuous)' if args.live else 'ONE-TIME'}")
    
    if args.live:
        print(f"Update Interval: {args.interval} seconds")
        print(f"\nPress Ctrl+C to stop\n")
        
        try:
            iteration = 0
            while True:
                iteration += 1
                print(f"\n{'='*70}")
                print(f"🔄 ITERATION {iteration} - {datetime.now().strftime('%H:%M:%S')}")
                print(f"{'='*70}")
                
                # Fetch live data
                fetch_live_data()
                
                # Scan for setups
                scan_instruments()
                
                print(f"\n⏳ Next update in {args.interval} seconds...")
                import time
                time.sleep(args.interval)
                
        except KeyboardInterrupt:
            print("\n\n⏹️ Stopped by user")
    else:
        # One-time run
        fetch_live_data()
        scan_instruments()
        
        print("\n" + "=" * 70)
        print("✅ MONITORING COMPLETE")
        print("=" * 70)
        print(f"Finished: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == '__main__':
    main()
