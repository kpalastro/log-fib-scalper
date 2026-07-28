#!/usr/bin/env python3
"""
IG Markets Data Fetcher for Gold (XAUUSD) and Silver (XAGUSD)
Uses trading-ig library to fetch historical OHLCV data
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv('/home/palbot/Projects/log-fib-scalper/live_trading/.env')

# IG Markets credentials
IG_API_KEY = os.getenv('IG_API_KEY')
IG_USERNAME = os.getenv('IG_USERNAME')
IG_PASSWORD = os.getenv('IG_PASSWORD')
IG_ACCOUNT_ID = os.getenv('IG_ACCOUNT_ID', 'PS317')
IG_DEMO = os.getenv('IG_DEMO', 'false').lower() == 'true'

if not all([IG_API_KEY, IG_USERNAME, IG_PASSWORD]):
    print("❌ Missing IG Markets credentials in .env file")
    print(f"   IG_API_KEY: {'✓' if IG_API_KEY else '✗'}")
    print(f"   IG_USERNAME: {'✓' if IG_USERNAME else '✗'}")
    print(f"   IG_PASSWORD: {'✓' if IG_PASSWORD else '✗'}")
    sys.exit(1)

from trading_ig.client import RESTClient
from trading_ig.lightstreamer import Subscription

print("=" * 80)
print("📊 IG MARKETS DATA FETCHER - GOLD & SILVER")
print("=" * 80)
print()
print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============ LOGIN ============
print("=" * 80)
print("🔐 AUTHENTICATION")
print("=" * 80)
print()

try:
    # Create REST client
    ig_client = RESTClient(
        username=IG_USERNAME,
        password=IG_PASSWORD,
        api_key=IG_API_KEY,
        account_id=IG_ACCOUNT_ID,
        demo=IG_DEMO
    )
    
    print(f"✅ Logged in successfully")
    print(f"   Account ID: {IG_ACCOUNT_ID}")
    print(f"   Environment: {'DEMO' if IG_DEMO else 'LIVE'}")
    
except Exception as e:
    print(f"❌ Login failed: {e}")
    print("   Check credentials in /home/palbot/Projects/log-fib-scalper/live_trading/.env")
    sys.exit(1)

print()

# ============ FETCH ACCOUNT DETAILS ============
print("=" * 80)
print("📋 ACCOUNT DETAILS")
print("=" * 80)
print()

try:
    account_details = ig_client.fetch_accounts()
    print(f"   Account Type: {account_details.get('accountType', 'N/A')}")
    print(f"   Balance: {account_details.get('balance', 'N/A')}")
    print(f"   Currency: {account_details.get('currency', 'N/A')}")
except Exception as e:
    print(f"⚠️  Could not fetch account details: {e}")

print()

# ============ FETCH GOLD (XAUUSD) DATA ============
print("=" * 80)
print("🥇 GOLD (XAUUSD) - 5 Minute Data")
print("=" * 80)
print()

# IG Markets instrument ID for Gold
GOLD_EPIC = "IX.D.GOLD.IPV"  # Gold Spot (XAUUSD)

try:
    print(f"📡 Fetching market data for {GOLD_EPIC}...")
    
    # Fetch market data
    market_data = ig_client.fetch_market_by_epic(GOLD_EPIC)
    
    print(f"\n✅ Market Info:")
    print(f"   Instrument: {market_data.get('instrumentName', 'N/A')}")
    print(f"   Market Status: {market_data.get('marketStatus', 'N/A')}")
    
    # Get snapshot (current prices)
    snapshot = market_data.get('snapshot', {})
    print(f"\n💰 Current Prices:")
    print(f"   Bid: {snapshot.get('bid', 'N/A')}")
    print(f"   Offer (Ask): {snapshot.get('offer', 'N/A')}")
    print(f"   High: {snapshot.get('highPrice', 'N/A')}")
    print(f"   Low: {snapshot.get('lowPrice', 'N/A')}")
    print(f"   Change: {snapshot.get('netChange', 'N/A')} ({snapshot.get('percentageChange', 'N/A')}%)")
    
    gold_ltp = snapshot.get('offer', None)
    gold_high = snapshot.get('highPrice', None)
    gold_low = snapshot.get('lowPrice', None)
    
except Exception as e:
    print(f"⚠️  Could not fetch Gold data: {e}")
    gold_ltp = None

print()

# ============ FETCH SILVER (XAGUSD) DATA ============
print("=" * 80)
print("🥈 SILVER (XAGUSD) - 5 Minute Data")
print("=" * 80)
print()

# IG Markets instrument ID for Silver
SILVER_EPIC = "IX.D.SILVER.IPV"  # Silver Spot (XAGUSD)

try:
    print(f"📡 Fetching market data for {SILVER_EPIC}...")
    
    # Fetch market data
    market_data = ig_client.fetch_market_by_epic(SILVER_EPIC)
    
    print(f"\n✅ Market Info:")
    print(f"   Instrument: {market_data.get('instrumentName', 'N/A')}")
    print(f"   Market Status: {market_data.get('marketStatus', 'N/A')}")
    
    # Get snapshot (current prices)
    snapshot = market_data.get('snapshot', {})
    print(f"\n💰 Current Prices:")
    print(f"   Bid: {snapshot.get('bid', 'N/A')}")
    print(f"   Offer (Ask): {snapshot.get('offer', 'N/A')}")
    print(f"   High: {snapshot.get('highPrice', 'N/A')}")
    print(f"   Low: {snapshot.get('lowPrice', 'N/A')}")
    print(f"   Change: {snapshot.get('netChange', 'N/A')} ({snapshot.get('percentageChange', 'N/A')}%)")
    
    silver_ltp = snapshot.get('offer', None)
    silver_high = snapshot.get('highPrice', None)
    silver_low = snapshot.get('lowPrice', None)
    
except Exception as e:
    print(f"⚠️  Could not fetch Silver data: {e}")
    silver_ltp = None

print()

# ============ FETCH HISTORICAL DATA ============
print("=" * 80)
print("📊 HISTORICAL DATA (5-minute candles)")
print("=" * 80)
print()

def fetch_historical(epic, resolution="5", numpoints=100):
    """Fetch historical OHLCV data from IG Markets"""
    try:
        print(f"   Fetching {numpoints} bars of {resolution}-minute data for {epic}...")
        
        # Fetch historical data
        hist_data = ig_client.fetch_historical_prices_by_epic(
            epic=epic,
            resolution=resolution,
            numpoints=numpoints
        )
        
        return hist_data
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
        return None

# Fetch Gold historical data
print("\n🥇 GOLD Historical Data:")
gold_hist = fetch_historical(GOLD_EPIC, resolution="5", numpoints=500)

if gold_hist:
    df_gold = pd.DataFrame(gold_hist.get('prices', []))
    
    if len(df_gold) > 0:
        print(f"   ✅ Retrieved {len(df_gold)} candles")
        
        # Convert timestamps
        df_gold['datetime'] = pd.to_datetime(df_gold['snapshotTime'], unit='ms')
        
        # Extract OHLCV
        df_gold['open'] = df_gold['price'].apply(lambda x: x.get('open', 0))
        df_gold['high'] = df_gold['price'].apply(lambda x: x.get('high', 0))
        df_gold['low'] = df_gold['price'].apply(lambda x: x.get('low', 0))
        df_gold['close'] = df_gold['price'].apply(lambda x: x.get('close', 0))
        df_gold['volume'] = df_gold['price'].apply(lambda x: x.get('volume', 0))
        
        print(f"\n   📈 First candle: {df_gold['datetime'].iloc[0]}")
        print(f"   📈 Last candle: {df_gold['datetime'].iloc[-1]}")
        
        print(f"\n   📊 Last 10 candles:")
        print(f"   {'Date/Time':<22} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10}")
        print(f"   {'-'*66}")
        
        for idx, row in df_gold.tail(10).iterrows():
            time_str = row['datetime'].strftime('%Y-%m-%d %H:%M')
            print(f"   {time_str:<22} {row['open']:>10.2f} {row['high']:>10.2f} {row['low']:>10.2f} {row['close']:>10.2f}")
        
        # Save to CSV
        csv_file = "/home/palbot/Projects/log-fib-scalper/data/IG_XAUUSD5.csv"
        df_out = df_gold[['datetime', 'open', 'high', 'low', 'close', 'volume']].copy()
        df_out.to_csv(csv_file, index=False)
        
        print(f"\n   💾 Saved to: {csv_file}")
        print(f"   Total rows: {len(df_out)}")
        
        gold_hist_ltp = df_gold['close'].iloc[-1]
    else:
        print("   ⚠️  No data returned")
        gold_hist_ltp = None
else:
    gold_hist_ltp = None

print()

# Fetch Silver historical data
print("🥈 SILVER Historical Data:")
silver_hist = fetch_historical(SILVER_EPIC, resolution="5", numpoints=500)

if silver_hist:
    df_silver = pd.DataFrame(silver_hist.get('prices', []))
    
    if len(df_silver) > 0:
        print(f"   ✅ Retrieved {len(df_silver)} candles")
        
        # Convert timestamps
        df_silver['datetime'] = pd.to_datetime(df_silver['snapshotTime'], unit='ms')
        
        # Extract OHLCV
        df_silver['open'] = df_silver['price'].apply(lambda x: x.get('open', 0))
        df_silver['high'] = df_silver['price'].apply(lambda x: x.get('high', 0))
        df_silver['low'] = df_silver['price'].apply(lambda x: x.get('low', 0))
        df_silver['close'] = df_silver['price'].apply(lambda x: x.get('close', 0))
        df_silver['volume'] = df_silver['price'].apply(lambda x: x.get('volume', 0))
        
        print(f"\n   📈 First candle: {df_silver['datetime'].iloc[0]}")
        print(f"   📈 Last candle: {df_silver['datetime'].iloc[-1]}")
        
        print(f"\n   📊 Last 10 candles:")
        print(f"   {'Date/Time':<22} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10}")
        print(f"   {'-'*66}")
        
        for idx, row in df_silver.tail(10).iterrows():
            time_str = row['datetime'].strftime('%Y-%m-%d %H:%M')
            print(f"   {time_str:<22} {row['open']:>10.2f} {row['high']:>10.2f} {row['low']:>10.2f} {row['close']:>10.2f}")
        
        # Save to CSV
        csv_file = "/home/palbot/Projects/log-fib-scalper/data/IG_XAGUSD5.csv"
        df_out = df_silver[['datetime', 'open', 'high', 'low', 'close', 'volume']].copy()
        df_out.to_csv(csv_file, index=False)
        
        print(f"\n   💾 Saved to: {csv_file}")
        print(f"   Total rows: {len(df_out)}")
        
        silver_hist_ltp = df_silver['close'].iloc[-1]
    else:
        print("   ⚠️  No data returned")
        silver_hist_ltp = None
else:
    silver_hist_ltp = None

print()
print("=" * 80)
print("✅ DATA FETCH COMPLETE")
print("=" * 80)
print()
print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()
print("📁 Files saved:")
print("   - /home/palbot/Projects/log-fib-scalper/data/IG_XAUUSD5.csv")
print("   - /home/palbot/Projects/log-fib-scalper/data/IG_XAGUSD5.csv")
print()

# Summary
print("=" * 80)
print("📊 SUMMARY")
print("=" * 80)
if gold_ltp:
    print(f"🥇 GOLD (XAUUSD) Live:")
    print(f"   LTP: ${gold_ltp}")
    print(f"   Range: ${gold_low} - ${gold_high}")
if gold_hist_ltp:
    print(f"   Last 5-min close: ${gold_hist_ltp:.2f}")
print()
if silver_ltp:
    print(f"🥈 SILVER (XAGUSD) Live:")
    print(f"   LTP: ${silver_ltp}")
    print(f"   Range: ${silver_low} - ${silver_high}")
if silver_hist_ltp:
    print(f"   Last 5-min close: ${silver_hist_ltp:.2f}")
print()
