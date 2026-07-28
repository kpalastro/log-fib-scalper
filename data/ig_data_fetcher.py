"""
IG MARKETS LIVE DATA FETCHER
=============================
Fetches real-time Gold (XAUUSD) and Silver (XAGUSD) prices from IG Markets API.
Updates CSV files for the geometric confluence scanner.

Usage:
    python ig_data_fetcher.py --instrument gold    # Fetch Gold
    python ig_data_fetcher.py --instrument silver  # Fetch Silver
    python ig_data_fetcher.py --both               # Fetch both
    python ig_data_fetcher.py --live --interval 60 # Live mode, update every 60s
"""

import os
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load IG credentials
load_dotenv(Path('/home/palbot/Projects/log-fib-scalper/live_trading/.env'))

IG_API_KEY = os.getenv('IG_API_KEY')
IG_USERNAME = os.getenv('IG_USERNAME')
IG_PASSWORD = os.getenv('IG_PASSWORD')
IG_ACCOUNT_ID = os.getenv('IG_ACCOUNT_ID')
IG_DEMO = os.getenv('IG_DEMO', 'false').lower() == 'true'

# IG API endpoints
BASE_URL = 'https://api.ig.com' if not IG_DEMO else 'https://demo-api.ig.com'
SESSION_ENDPOINT = f'{BASE_URL}/v1/session'
PRICES_ENDPOINT = f'{BASE_URL}/gateway/deal/prices'

# Instrument epics
INSTRUMENT_EPICS = {
    'gold': 'CS.D.CFAGOLD.CFA.IP',
    'silver': 'CS.D.CFASILVER.CFA.IP',
}

# Output CSV paths
CSV_PATHS = {
    'gold': '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv',
    'silver': '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAGUSD5.csv',
}

class IGDataFetcher:
    """Fetch live data from IG Markets API."""
    
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json; charset=utf-8',
            'X-IG-API-KEY': IG_API_KEY,
            'X-SECURITY-TOKEN': '',
            'X-SPREAD-PREMIUM': 'false',
        }
        self.authenticated = False
        
    def create_session(self):
        """Authenticate with IG API and create session."""
        print(f"🔐 Authenticating with IG Markets ({'LIVE' if not IG_DEMO else 'DEMO'} account)...")
        
        payload = {
            'identifier': IG_USERNAME,
            'password': IG_PASSWORD,
        }
        
        response = self.session.post(
            SESSION_ENDPOINT,
            json=payload,
            headers={
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/json; charset=utf-8',
                'X-IG-API-KEY': IG_API_KEY,
                'VERSION': '2',
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.headers['X-SECURITY-TOKEN'] = data.get('securityToken', '')
            self.authenticated = True
            print(f"✅ Authentication successful!")
            print(f"   Account: {IG_ACCOUNT_ID}")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    
    def fetch_prices(self, instrument: str, resolution: str = 'MINUTE_5', numpoints: int = 100):
        """
        Fetch historical prices for an instrument.
        
        Args:
            instrument: 'gold' or 'silver'
            resolution: 'MINUTE_1', 'MINUTE_5', 'MINUTE_15', etc.
            numpoints: Number of candles to fetch
        
        Returns:
            DataFrame with OHLCV data
        """
        if not self.authenticated:
            if not self.create_session():
                return None
        
        epic = INSTRUMENT_EPICS.get(instrument)
        if not epic:
            print(f"❌ Unknown instrument: {instrument}")
            return None
        
        # Calculate from date (numpoints * resolution in minutes ago)
        resolution_minutes = int(resolution.split('_')[1])
        from_date = datetime.utcnow() - timedelta(minutes=resolution_minutes * numpoints * 1.2)
        from_date_str = from_date.strftime('%Y-%m-%dT%H:%M:%S')
        
        url = f'{PRICES_ENDPOINT}/{epic}'
        params = {
            'resolution': resolution,
            'from': from_date_str,
            'max': numpoints,
        }
        
        print(f"📊 Fetching {numpoints} x {resolution} candles for {instrument.upper()}...")
        
        response = self.session.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return self._parse_ig_response(data, instrument)
        else:
            print(f"❌ API error: {response.status_code}")
            print(f"   Response: {response.text[:300]}")
            return None
    
    def _parse_ig_response(self, data: dict, instrument: str) -> pd.DataFrame:
        """Parse IG API response into DataFrame."""
        if 'prices' not in data or not data['prices']:
            print("⚠️ No price data returned")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(data['prices'])
        
        # Extract OHLCV
        df = pd.DataFrame([{
            'time': pd.to_datetime(item['snapshotTime'], utc=True).tz_localize(None),
            'open': item['mid']['open'],
            'high': item['mid']['high'],
            'low': item['mid']['low'],
            'close': item['mid']['close'],
            'volume': 0  # IG doesn't provide volume for CFDs
        } for item in data['prices']])
        
        # Sort by time
        df = df.sort_values('time').reset_index(drop=True)
        
        print(f"✅ Fetched {len(df)} candles")
        print(f"   Range: {df['time'].min()} to {df['time'].max()}")
        print(f"   Price: {df['close'].iloc[0]:.2f} → {df['close'].iloc[-1]:.2f}")
        
        return df
    
    def save_to_csv(self, df: pd.DataFrame, instrument: str):
        """Save DataFrame to CSV file (append or create)."""
        csv_path = CSV_PATHS.get(instrument)
        if not csv_path:
            print(f"❌ No CSV path for {instrument}")
            return False
        
        # Create directory if needed
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists
        if csv_path.exists():
            # Load existing data
            existing_df = pd.read_csv(csv_path)
            if 'time' in existing_df.columns:
                existing_df['time'] = pd.to_datetime(existing_df['time'])
            elif 'datetime' in existing_df.columns:
                existing_df['time'] = pd.to_datetime(existing_df['datetime'])
            
            # Remove duplicates (keep only bars not in new data)
            if len(df) > 0:
                latest_time = df['time'].max()
                existing_df = existing_df[existing_df['time'] < latest_time]
            
            # Combine
            combined = pd.concat([existing_df, df], ignore_index=True)
            combined = combined.drop_duplicates(subset=['time'], keep='last')
            combined = combined.sort_values('time').reset_index(drop=True)
        else:
            combined = df
        
        # Save
        combined.to_csv(csv_path, index=False)
        print(f"💾 Saved to {csv_path}")
        print(f"   Total bars: {len(combined):,}")
        
        return True
    
    def fetch_and_save(self, instrument: str, resolution: str = 'MINUTE_5', numpoints: int = 200):
        """Fetch data and save to CSV."""
        df = self.fetch_prices(instrument, resolution, numpoints)
        if df is not None and len(df) > 0:
            return self.save_to_csv(df, instrument)
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='IG Markets Live Data Fetcher')
    parser.add_argument('--instrument', type=str, default='both',
                        choices=['gold', 'silver', 'both'],
                        help='Instrument to fetch')
    parser.add_argument('--resolution', type=str, default='MINUTE_5',
                        choices=['MINUTE_1', 'MINUTE_5', 'MINUTE_15', 'MINUTE_30', 'HOUR'],
                        help='Candle resolution')
    parser.add_argument('--numpoints', type=int, default=200,
                        help='Number of candles to fetch')
    parser.add_argument('--live', action='store_true',
                        help='Run in live mode (continuous updates)')
    parser.add_argument('--interval', type=int, default=300,
                        help='Update interval in seconds (for live mode)')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("IG MARKETS LIVE DATA FETCHER")
    print("=" * 70)
    print(f"Account: {IG_ACCOUNT_ID} ({'LIVE' if not IG_DEMO else 'DEMO'})")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    fetcher = IGDataFetcher()
    
    # Determine instruments
    if args.instrument == 'both':
        instruments = ['gold', 'silver']
    else:
        instruments = [args.instrument]
    
    if args.live:
        # Live mode - continuous updates
        print(f"\n🔴 LIVE MODE: Updating every {args.interval} seconds")
        print(f"   Instruments: {', '.join(instruments)}")
        print(f"   Resolution: {args.resolution}")
        print(f"   Press Ctrl+C to stop\n")
        
        try:
            while True:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Fetching data...")
                for inst in instruments:
                    fetcher.fetch_and_save(inst, args.resolution, args.numpoints)
                
                print(f"\n⏳ Next update in {args.interval} seconds...")
                import time
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n\n⏹️ Stopped by user")
    else:
        # One-time fetch
        print(f"\n📥 One-time fetch for: {', '.join(instruments)}")
        
        for inst in instruments:
            print(f"\n{'='*70}")
            fetcher.fetch_and_save(inst, args.resolution, args.numpoints)
        
        print(f"\n{'='*70}")
        print("✅ FETCH COMPLETE")
        print(f"{'='*70}")


if __name__ == '__main__':
    main()
