"""
═══════════════════════════════════════════════════════════════
ZERODHA KITE HISTORICAL DATA FETCHER
═══════════════════════════════════════════════════════════════

Download historical data for Indian stocks (NSE/NFO) using Zerodha Kite API.
Supports 5m, 15m, 30m, 60m, and daily intervals.

Usage:
    python zerodha_data_fetcher.py

For 2FA, you'll be prompted to enter:
- TOTP code (from Google Authenticator)
- Or PIN (if not using TOTP)

Credentials are loaded from .env.zerodha or entered interactively.
"""

import os
import sys
import json
import csv
import datetime
from pathlib import Path
from typing import Optional, Dict, List
import requests
import dateutil.parser

# Try to import dotenv for .env file support
try:
    from dotenv import load_dotenv
    load_dotenv()
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


class ZerodhaKiteClient:
    """Zerodha Kite API client for historical data"""
    
    def __init__(self, user_id: str = None, password: str = None):
        self.user_id = user_id or os.getenv("ZERODHA_USER_ID")
        self.password = password or os.getenv("ZERODHA_PASSWORD")
        self.enctoken = None
        self.session = requests.Session()
        self.root_url = "https://kite.zerodha.com/oms"
        
    def get_enctoken(self, twofa: str) -> str:
        """
        Login and get enctoken
        
        Args:
            twofa: TOTP code or PIN
        
        Returns:
            enctoken for API authentication
        """
        print("📡 Logging in to Zerodha Kite...")
        
        # Step 1: Login with user_id and password
        response = self.session.post('https://kite.zerodha.com/api/login', data={
            "user_id": self.user_id,
            "password": self.password
        })
        
        if response.status_code != 200:
            raise Exception(f"Login failed: {response.status_code} - {response.text}")
        
        response_data = response.json()
        
        if response_data.get('status') != 'success':
            raise Exception(f"Login failed: {response_data.get('message', 'Unknown error')}")
        
        request_id = response_data['data']['request_id']
        user_id = response_data['data']['user_id']
        
        # Step 2: Submit 2FA (TOTP or PIN)
        response = self.session.post('https://kite.zerodha.com/api/twofa', data={
            "request_id": request_id,
            "twofa_value": twofa,
            "user_id": user_id
        })
        
        if response.status_code != 200:
            raise Exception(f"2FA failed: {response.status_code} - {response.text}")
        
        response_data = response.json()
        
        if response_data.get('status') != 'success':
            raise Exception(f"2FA failed: {response_data.get('message', 'Unknown error')}")
        
        # Get enctoken from cookies
        enctoken = response.cookies.get('enctoken')
        
        if not enctoken:
            raise Exception("Failed to get enctoken. Check credentials.")
        
        self.enctoken = enctoken
        self.headers = {"Authorization": f"enctoken {self.enctoken}"}
        
        # Initialize session
        self.session.get(self.root_url, headers=self.headers)
        
        print(f"✅ Login successful | User: {self.user_id}")
        return enctoken
    
    def instruments(self, exchange: str = "NSE") -> List[Dict]:
        """
        Fetch list of instruments
        
        Args:
            exchange: NSE, NFO, BSE, etc.
        
        Returns:
            List of instrument dictionaries
        """
        print(f"📥 Fetching {exchange} instruments...")
        
        response = self.session.get("https://api.kite.trade/instruments")
        data = response.text.split("\n")
        
        instruments = []
        for row in data[1:-1]:
            fields = row.split(",")
            if len(fields) >= 12:
                if exchange is None or exchange == fields[11]:
                    instruments.append({
                        'instrument_token': int(fields[0]),
                        'exchange_token': fields[1],
                        'tradingsymbol': fields[2],
                        'name': fields[3][1:-1] if fields[3] else '',
                        'last_price': float(fields[4]) if fields[4] else 0,
                        'expiry': dateutil.parser.parse(fields[5]).date() if fields[5] else None,
                        'strike': float(fields[6]) if fields[6] else 0,
                        'tick_size': float(fields[7]) if fields[7] else 0,
                        'lot_size': int(fields[8]) if fields[8] else 0,
                        'instrument_type': fields[9],
                        'segment': fields[10],
                        'exchange': fields[11]
                    })
        
        print(f"✅ Fetched {len(instruments)} instruments")
        return instruments
    
    def historical_data(
        self,
        instrument_token: int,
        from_date: datetime.datetime,
        to_date: datetime.datetime,
        interval: str = "5minute",
        continuous: bool = False,
        oi: bool = False
    ) -> List[Dict]:
        """
        Fetch historical candle data
        
        Args:
            instrument_token: Token from instruments list
            from_date: Start datetime
            to_date: End datetime
            interval: 5minute, 15minute, 30minute, 60minute, day, etc.
            continuous: For futures (continuous contracts)
            oi: Include open interest data
        
        Returns:
            List of candle dictionaries with OHLCV data
        """
        params = {
            "from": from_date.strftime("%Y-%m-%d %H:%M:%S"),
            "to": to_date.strftime("%Y-%m-%d %H:%M:%S"),
            "interval": interval,
            "continuous": 1 if continuous else 0,
            "oi": 1 if oi else 0
        }
        
        url = f"{self.root_url}/instruments/historical/{instrument_token}/{interval}"
        
        try:
            response = self.session.get(url, params=params, headers=self.headers)
            
            if response.status_code != 200:
                print(f"❌ API Error: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                return []
            
            data = response.json()
            
            if 'data' not in data or 'candles' not in data['data']:
                print(f"❌ No data in response")
                return []
            
            candles = data['data']['candles']
            records = []
            
            for candle in candles:
                record = {
                    "date": dateutil.parser.parse(candle[0]),
                    "open": candle[1],
                    "high": candle[2],
                    "low": candle[3],
                    "close": candle[4],
                    "volume": candle[5] if len(candle) > 5 else 0
                }
                
                # Include OI if available
                if len(candle) == 7:
                    record["oi"] = candle[6]
                
                records.append(record)
            
            print(f"✅ Fetched {len(records)} candles")
            return records
            
        except Exception as e:
            print(f"❌ Error fetching historical data: {e}")
            return []
    
    def save_to_csv(self, data: List[Dict], filename: str):
        """Save historical data to CSV"""
        if not data:
            print("❌ No data to save")
            return
        
        fieldnames = list(data[0].keys())
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in data:
                # Convert datetime to string
                row_copy = row.copy()
                if 'date' in row_copy and isinstance(row_copy['date'], datetime.datetime):
                    row_copy['date'] = row_copy['date'].strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow(row_copy)
        
        print(f"💾 Saved to: {filename}")
    
    def search_instrument(self, exchange: str, query: str) -> List[Dict]:
        """Search for instrument by trading symbol"""
        instruments = self.instruments(exchange)
        
        # Case-insensitive search
        query_lower = query.lower()
        matches = [
            inst for inst in instruments
            if query_lower in inst['tradingsymbol'].lower() or
               query_lower in inst['name'].lower()
        ]
        
        return matches


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Zerodha Kite Historical Data Fetcher')
    parser.add_argument('--user-id', type=str, help='Zerodha User ID')
    parser.add_argument('--password', type=str, help='Zerodha Password')
    parser.add_argument('--2fa', type=str, dest='twofa', help='2FA/TOTP code')
    parser.add_argument('--exchange', type=str, default='NSE', help='Exchange (NSE/NFO)')
    parser.add_argument('--symbol', type=str, help='Instrument symbol to search')
    parser.add_argument('--interval', type=str, default='5minute', help='Candle interval')
    parser.add_argument('--days', type=int, default=60, help='Days of data')
    parser.add_argument('--non-interactive', action='store_true', help='Run without prompts (use all args)')
    args = parser.parse_args()
    
    print("="*80)
    print("📊 ZERODHA KITE HISTORICAL DATA FETCHER")
    print("="*80)
    print()
    
    # Load credentials from args, env, or prompt
    user_id = args.user_id or os.getenv("ZERODHA_USER_ID")
    password = args.password or os.getenv("ZERODHA_PASSWORD")
    twofa = args.twofa
    
    if not user_id:
        user_id = input("Enter Zerodha User ID (e.g., RD156567): ").strip()
    
    if not password:
        password = input("Enter Zerodha Password: ").strip()
    
    # Initialize client
    client = ZerodhaKiteClient(user_id, password)
    
    # Get 2FA code
    if not twofa:
        print()
        print("📱 2FA Authentication")
        print("   Enter the TOTP code from Google Authenticator")
        print("   Or enter your PIN if not using TOTP")
        print()
        twofa = input("Enter 2FA code: ").strip()
    
    if not twofa:
        print("❌ 2FA code required")
        return
    
    # Login
    try:
        client.get_enctoken(twofa)
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return
    
    # If non-interactive mode, use args directly
    if args.non_interactive:
        exchange = args.exchange or "NSE"
        query = args.symbol or "NIFTY 50"
        interval = args.interval or "30minute"
        days = args.days or 60
    else:
        # Search for instrument
        print()
        print("🔍 Search for Instrument")
        exchange = input("Exchange (NSE/NFO): ").strip().upper() or "NSE"
        query = input("Search (e.g., NIFTY, BANKNIFTY, RELIANCE): ").strip().upper()
    
    matches = client.search_instrument(exchange, query)
    
    if not matches:
        print(f"❌ No instruments found for '{query}' on {exchange}")
        return
    
    print(f"\n✅ Found {len(matches)} matches:")
    for i, inst in enumerate(matches[:10], 1):
        expiry_str = f" (Exp: {inst['expiry']})" if inst.get('expiry') else ""
        print(f"  {i}. {inst['tradingsymbol']}{expiry_str} | Token: {inst['instrument_token']}")
    
    if len(matches) > 10:
        print(f"  ... and {len(matches) - 10} more")
    
    # Select instrument
    print()
    if args.non_interactive:
        # Auto-select first match in non-interactive mode
        selected = matches[0]
        print(f"✅ Auto-selected: {selected['tradingsymbol']}")
    elif len(matches) == 1:
        selected = matches[0]
        print(f"✅ Selected: {selected['tradingsymbol']}")
    else:
        choice = input(f"Select instrument (1-{min(10, len(matches))}): ").strip()
        try:
            idx = int(choice) - 1
            selected = matches[idx]
        except (ValueError, IndexError):
            print("❌ Invalid choice")
            return
    
    # Get date range
    print()
    print("📅 Date Range")
    
    if args.non_interactive:
        days = args.days or 60
        interval = args.interval or "30minute"
        print(f"Days: {days}")
        print(f"Interval: {interval}")
    else:
        days = input("Days of data (max 200 for intraday): ").strip() or "60"
        days = int(days)
        
        interval = input("Interval (5minute/15minute/30minute/60minute/day): ").strip() or "5minute"
    
    # Calculate dates
    to_date = datetime.datetime.now()
    from_date = to_date - datetime.timedelta(days=days)
    
    # Set to market open time
    from_date = from_date.replace(hour=9, minute=15, second=0, microsecond=0)
    to_date = to_date.replace(hour=15, minute=30, second=0, microsecond=0)
    
    print(f"\n📊 Fetching Data")
    print(f"   Instrument: {selected['tradingsymbol']} (Token: {selected['instrument_token']})")
    print(f"   From: {from_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"   To: {to_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Interval: {interval}")
    print()
    
    # Fetch data
    data = client.historical_data(
        instrument_token=selected['instrument_token'],
        from_date=from_date,
        to_date=to_date,
        interval=interval,
        continuous=False,
        oi=False
    )
    
    if not data:
        print("❌ No data fetched")
        return
    
    # Save to CSV
    output_dir = Path("zerodha_data")
    output_dir.mkdir(exist_ok=True)
    
    symbol = selected['tradingsymbol'].replace(" ", "_").replace("-", "_")
    filename = output_dir / f"{symbol}_{interval}_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}.csv"
    
    client.save_to_csv(data, str(filename))
    
    # Print summary
    print()
    print("="*80)
    print("📊 DATA SUMMARY")
    print("="*80)
    print(f"Total Candles: {len(data)}")
    print(f"Date Range: {data[0]['date'].strftime('%Y-%m-%d')} to {data[-1]['date'].strftime('%Y-%m-%d')}")
    print(f"Price Range: {min(c['low'] for c in data):.2f} - {max(c['high'] for c in data):.2f}")
    print(f"Avg Volume: {sum(c['volume'] for c in data) / len(data):.0f}")
    print("="*80)
    
    print(f"\n💾 File saved to: {filename.absolute()}")
    print(f"\n✅ Ready for backtesting!")


if __name__ == "__main__":
    main()
