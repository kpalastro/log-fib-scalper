#!/usr/bin/env python3
"""IG Markets Historical Price Fetcher - Working Version"""

import os
from dotenv import load_dotenv
import requests
import pandas as pd
import json
from datetime import datetime

load_dotenv("/home/palbot/Projects/log-fib-scalper/live_trading/.env")

IG_API_KEY = os.getenv("IG_API_KEY")
IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")

print("=" * 80)
print("📊 IG MARKETS - HISTORICAL PRICE FETCHER")
print("=" * 80)
print()

# Login
session = requests.Session()
headers = {
    "X-IG-API-KEY": IG_API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
    "VERSION": "2"
}

resp = session.post(
    "https://api.ig.com/gateway/deal/session",
    json={"identifier": IG_USERNAME, "password": IG_PASSWORD},
    headers=headers
)

if resp.status_code != 200:
    print(f"❌ Login failed: {resp.text}")
    exit(1)

CST = resp.headers.get("CST")
TOKEN = resp.headers.get("X-SECURITY-TOKEN")

auth_headers = {
    "X-IG-API-KEY": IG_API_KEY,
    "CST": CST,
    "X-SECURITY-TOKEN": TOKEN,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

print(f"✅ Logged in: Account {resp.json().get('currentAccountId')}")
print()

# ============ FETCH HISTORICAL PRICES ============
def fetch_ig_prices(epic, resolution="MINUTE_15", from_date="2026-05-01T00:00:00", max=100):
    """Fetch historical prices from IG API"""
    
    url = f"https://api.ig.com/gateway/deal/prices/{epic}"
    params = {
        "resolution": resolution,
        "from": from_date,
        "max": max,
        "pageSize": max
    }
    
    r = session.get(url, params=params, headers=auth_headers)
    
    if r.status_code == 200:
        data = r.json()
        return data.get("prices", [])
    else:
        print(f"❌ Error {r.status_code}: {r.text[:200]}")
        return []

# ============ PARSE PRICES ============
def parse_prices(prices):
    """Parse IG price data to DataFrame"""
    if not prices:
        return None
    
    rows = []
    for p in prices:
        row = {
            "datetime": p.get("snapshotTimeUTC", ""),
            "open": p.get("openPrice", {}).get("bid", 0),
            "high": p.get("highPrice", {}).get("bid", 0),
            "low": p.get("lowPrice", {}).get("bid", 0),
            "close": p.get("closePrice", {}).get("bid", 0),
            "volume": p.get("lastTradedVolume", 0)
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"])
    
    return df

# ============ FETCH GOLD DATA ============
print("=" * 80)
print("🥇 GOLD (CS.D.CFAGOLD.CFA.IP)")
print("=" * 80)

gold_prices = fetch_ig_prices(
    epic="CS.D.CFAGOLD.CFA.IP",
    resolution="MINUTE_15",
    from_date="2026-05-01T00:00:00",
    max=100
)

if gold_prices:
    print(f"✅ Retrieved {len(gold_prices)} candles")
    
    gold_df = parse_prices(gold_prices)
    
    if gold_df is not None:
        print(f"\n📈 {gold_df['datetime'].min()} → {gold_df['datetime'].max()}")
        print(f"   Bars: {len(gold_df)}")
        print(f"   Open: ${gold_df['open'].iloc[0]:.2f}")
        print(f"   High: ${gold_df['high'].max():.2f}")
        print(f"   Low: ${gold_df['low'].min():.2f}")
        print(f"   Close: ${gold_df['close'].iloc[-1]:.2f}")
        
        # Save to CSV
        csv_path = "/home/palbot/Projects/log-fib-scalper/data/IG_GOLD_15min.csv"
        gold_df.to_csv(csv_path, index=False)
        print(f"\n💾 Saved: {csv_path}")
        
        print(f"\n📊 Last 10 candles:")
        print(f"{'Time':<25} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10}")
        print("-" * 69)
        for _, row in gold_df.tail(10).iterrows():
            t = row["datetime"].strftime("%Y-%m-%d %H:%M")
            print(f"{t:<25} {row['open']:>10.2f} {row['high']:>10.2f} {row['low']:>10.2f} {row['close']:>10.2f}")

# ============ FETCH SILVER DATA ============
print()
print("=" * 80)
print("🥈 SILVER (CS.D.CFASILVER.CFA.IP)")
print("=" * 80)

silver_prices = fetch_ig_prices(
    epic="CS.D.CFASILVER.CFA.IP",
    resolution="MINUTE_15",
    from_date="2026-05-01T00:00:00",
    max=100
)

if silver_prices:
    print(f"✅ Retrieved {len(silver_prices)} candles")
    
    silver_df = parse_prices(silver_prices)
    
    if silver_df is not None:
        print(f"\n📈 {silver_df['datetime'].min()} → {silver_df['datetime'].max()}")
        print(f"   Bars: {len(silver_df)}")
        print(f"   Open: ${silver_df['open'].iloc[0]:.2f}")
        print(f"   High: ${silver_df['high'].max():.2f}")
        print(f"   Low: ${silver_df['low'].min():.2f}")
        print(f"   Close: ${silver_df['close'].iloc[-1]:.2f}")
        
        # Save to CSV
        csv_path = "/home/palbot/Projects/log-fib-scalper/data/IG_SILVER_15min.csv"
        silver_df.to_csv(csv_path, index=False)
        print(f"\n💾 Saved: {csv_path}")
        
        print(f"\n📊 Last 10 candles:")
        print(f"{'Time':<25} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10}")
        print("-" * 69)
        for _, row in silver_df.tail(10).iterrows():
            t = row["datetime"].strftime("%Y-%m-%d %H:%M")
            print(f"{t:<25} {row['open']:>10.2f} {row['high']:>10.2f} {row['low']:>10.2f} {row['close']:>10.2f}")

# ============ FETCH MORE DATA (PAGINATION) ============
print()
print("=" * 80)
print("📥 FETCHING EXTENDED HISTORY (Multiple Pages)")
print("=" * 80)

def fetch_all_pages(epic, resolution="MINUTE_15", from_date="2026-01-01T00:00:00", page_size=100):
    """Fetch all historical data with pagination"""
    all_prices = []
    page = 0
    max_pages = 50  # Safety limit
    
    while page < max_pages:
        # Calculate from date based on page
        # IG API doesn't have page param, so we need to use from date
        # Each page is page_size candles
        # We'll increment the from date
        
        url = f"https://api.ig.com/gateway/deal/prices/{epic}"
        params = {
            "resolution": resolution,
            "from": from_date,
            "max": page_size,
            "pageSize": page_size
        }
        
        r = session.get(url, params=params, headers=auth_headers)
        
        if r.status_code != 200:
            print(f"❌ Page {page} failed: {r.status_code}")
            break
        
        data = r.json()
        prices = data.get("prices", [])
        
        if not prices:
            print(f"✅ No more data at page {page}")
            break
        
        all_prices.extend(prices)
        print(f"   Page {page}: {len(prices)} candles (total: {len(all_prices)})")
        
        # Update from_date to continue from last candle + 1 minute
        last_time = prices[-1].get("snapshotTimeUTC", "")
        if last_time:
            try:
                last_dt = datetime.strptime(last_time, "%Y-%m-%dT%H:%M:%S")
                from_date = (last_dt).strftime("%Y-%m-%dT%H:%M:%S")
            except:
                break
        
        page += 1
        
        # Stop if we got less than page_size (end of data)
        if len(prices) < page_size:
            break
    
    return all_prices

# Fetch extended gold history
print("\n🥇 Gold - Extended history from 2026-01-01...")
gold_extended = fetch_all_pages(
    epic="CS.D.CFAGOLD.CFA.IP",
    resolution="MINUTE_15",
    from_date="2026-01-01T00:00:00",
    page_size=100
)

if gold_extended:
    print(f"\n✅ Total gold candles: {len(gold_extended)}")
    
    gold_ext_df = parse_prices(gold_extended)
    if gold_ext_df is not None:
        csv_path = "/home/palbot/Projects/log-fib-scalper/data/IG_GOLD_15min_extended.csv"
        gold_ext_df.to_csv(csv_path, index=False)
        print(f"💾 Saved extended: {csv_path}")
        print(f"📈 Range: {gold_ext_df['datetime'].min()} → {gold_ext_df['datetime'].max()}")

# Fetch extended silver history
print("\n🥈 Silver - Extended history from 2026-01-01...")
silver_extended = fetch_all_pages(
    epic="CS.D.CFASILVER.CFA.IP",
    resolution="MINUTE_15",
    from_date="2026-01-01T00:00:00",
    page_size=100
)

if silver_extended:
    print(f"\n✅ Total silver candles: {len(silver_extended)}")
    
    silver_ext_df = parse_prices(silver_extended)
    if silver_ext_df is not None:
        csv_path = "/home/palbot/Projects/log-fib-scalper/data/IG_SILVER_15min_extended.csv"
        silver_ext_df.to_csv(csv_path, index=False)
        print(f"💾 Saved extended: {csv_path}")
        print(f"📈 Range: {silver_ext_df['datetime'].min()} → {silver_ext_df['datetime'].max()}")

print()
print("=" * 80)
print("✅ COMPLETE")
print("=" * 80)
