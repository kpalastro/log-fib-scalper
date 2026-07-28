"""
YAHOO FINANCE LIVE DATA FETCHER FOR GOLD & SILVER
==================================================
Fetches real-time Gold (GC=F) and Silver (SI=F) prices from Yahoo Finance.
Updates CSV files for the geometric confluence scanner.

Usage:
    python yahoo_live_fetcher.py --instrument gold    # Fetch Gold
    python yahoo_live_fetcher.py --instrument silver  # Fetch Silver
    python yahoo_live_fetcher.py --both               # Fetch both
    python yahoo_live_fetcher.py --live --interval 60 # Live mode, update every 60s

Current Prices (live):
    Gold: ~$4,538/oz
    Silver: ~$76.25/oz
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time
import argparse

# Output CSV paths (overwrite existing OANDA files)
CSV_PATHS = {
    'gold': '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAUUSD5.csv',
    'silver': '/home/palbot/Projects/log-fib-scalper/data/OANDA_XAGUSD5.csv',
}

# Yahoo Finance tickers
TICKERS = {
    'gold': 'GC=F',      # Gold futures
    'silver': 'SI=F',    # Silver futures
}

class YahooDataFetcher:
    """Fetch live data from Yahoo Finance."""
    
    def __init__(self):
        pass
    
    def fetch_prices(self, instrument: str, period: str = '5d', interval: str = '5m'):
        """
        Fetch historical prices for an instrument.
        
        Args:
            instrument: 'gold' or 'silver'
            period: '1d', '5d', '1mo', etc.
            interval: '1m', '5m', '15m', '30m', '1h', etc.
        
        Returns:
            DataFrame with OHLCV data
        """
        ticker = TICKERS.get(instrument)
        if not ticker:
            print(f"❌ Unknown instrument: {instrument}")
            return None
        
        print(f"📊 Fetching {period} {interval} data for {instrument.upper()} ({ticker})...")
        
        try:
            data = yf.download(ticker, period=period, interval=interval, progress=False)
            
            if len(data) == 0:
                print(f"⚠️ No data returned")
                return None
            
            # Handle multi-level columns (Yahoo format)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.droplevel(1)
            
            # Convert to standard format
            df = data.reset_index()
            
            # Handle different column formats from Yahoo
            expected_cols = ['time', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
            if len(df.columns) == 7:
                df.columns = expected_cols
            elif len(df.columns) == 6:
                # No adj_close
                df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
            else:
                print(f"⚠️ Unexpected column count: {len(df.columns)}")
                print(f"   Columns: {list(df.columns)}")
                # Try to use whatever we have
                df = df.iloc[:, :6]
                df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
            
            df['time'] = pd.to_datetime(df['time'])
            df = df[['time', 'open', 'high', 'low', 'close', 'volume']]
            df = df.sort_values('time').reset_index(drop=True)
            
            print(f"✅ Fetched {len(df)} candles")
            print(f"   Range: {df['time'].min()} to {df['time'].max()}")
            print(f"   Price: ${df['close'].iloc[0]:.2f} → ${df['close'].iloc[-1]:.2f}")
            
            return df
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def get_current_price(self, instrument: str) -> float:
        """Get current/latest price for an instrument."""
        ticker = TICKERS.get(instrument)
        if not ticker:
            return None
        
        try:
            t = yf.Ticker(ticker)
            info = t.info
            return info.get('regularMarketPrice', info.get('previousClose'))
        except:
            return None
    
    def save_to_csv(self, df: pd.DataFrame, instrument: str):
        """Save DataFrame to CSV file."""
        csv_path = CSV_PATHS.get(instrument)
        if not csv_path:
            print(f"❌ No CSV path for {instrument}")
            return False
        
        # Create directory if needed
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save (overwrite existing file)
        df.to_csv(csv_path, index=False)
        print(f"💾 Saved to {csv_path}")
        print(f"   Total bars: {len(df):,}")
        
        return True
    
    def fetch_and_save(self, instrument: str, period: str = '5d', interval: str = '5m'):
        """Fetch data and save to CSV."""
        df = self.fetch_prices(instrument, period, interval)
        if df is not None and len(df) > 0:
            return self.save_to_csv(df, instrument)
        return False


def main():
    parser = argparse.ArgumentParser(description='Yahoo Finance Live Data Fetcher')
    parser.add_argument('--instrument', type=str, default='both',
                        choices=['gold', 'silver', 'both'],
                        help='Instrument to fetch')
    parser.add_argument('--period', type=str, default='5d',
                        help='Data period (1d, 5d, 1mo, etc.)')
    parser.add_argument('--interval', type=str, default='5m',
                        choices=['1m', '5m', '15m', '30m', '1h'],
                        help='Candle interval')
    parser.add_argument('--live', action='store_true',
                        help='Run in live mode (continuous updates)')
    parser.add_argument('--interval-sec', type=int, default=300,
                        help='Update interval in seconds (for live mode)')
    parser.add_argument('--show-price', action='store_true',
                        help='Show current prices and exit')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("YAHOO FINANCE LIVE DATA FETCHER")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    fetcher = YahooDataFetcher()
    
    # Show current prices
    if args.show_price:
        print("\n💰 CURRENT PRICES")
        print("=" * 70)
        for inst in ['gold', 'silver']:
            price = fetcher.get_current_price(inst)
            if price:
                print(f"{inst.upper():8s}: ${price:.2f}")
        return
    
    # Determine instruments
    if args.instrument == 'both':
        instruments = ['gold', 'silver']
    else:
        instruments = [args.instrument]
    
    if args.live:
        # Live mode - continuous updates
        print(f"\n🔴 LIVE MODE: Updating every {args.interval_sec} seconds")
        print(f"   Instruments: {', '.join(instruments)}")
        print(f"   Interval: {args.interval}")
        print(f"   Press Ctrl+C to stop\n")
        
        try:
            while True:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Fetching data...")
                for inst in instruments:
                    fetcher.fetch_and_save(inst, args.period, args.interval)
                
                # Show current prices
                print("\n💰 Current Prices:")
                for inst in instruments:
                    price = fetcher.get_current_price(inst)
                    if price:
                        print(f"   {inst.upper()}: ${price:.2f}")
                
                print(f"\n⏳ Next update in {args.interval_sec} seconds...")
                time.sleep(args.interval_sec)
        except KeyboardInterrupt:
            print("\n\n⏹️ Stopped by user")
    else:
        # One-time fetch
        print(f"\n📥 One-time fetch for: {', '.join(instruments)}")
        
        for inst in instruments:
            print(f"\n{'='*70}")
            fetcher.fetch_and_save(inst, args.period, args.interval)
        
        print(f"\n{'='*70}")
        print("✅ FETCH COMPLETE")
        print(f"{'='*70}")
        
        # Show current prices
        print("\n💰 Current Prices:")
        for inst in instruments:
            price = fetcher.get_current_price(inst)
            if price:
                print(f"   {inst.upper()}: ${price:.2f}")


if __name__ == '__main__':
    main()
