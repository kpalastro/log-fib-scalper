#!/usr/bin/env python3
"""IG Markets Gold/Silver Data Fetcher"""

import os
from dotenv import load_dotenv
import requests
import pandas as pd
from datetime import datetime

load_dotenv("/home/palbot/Projects/log-fib-scalper/live_trading/.env")

IG_API_KEY = os.getenv("IG_API_KEY")
IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")

print("=" * 80)
print("📊 IG MARKETS - GOLD DATA")
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

print(f"Login: {resp.status_code}")

if resp.status_code != 200:
    print(f"Error: {resp.text}")
    exit(1)

CST = resp.headers.get("CST")
TOKEN = resp.headers.get("X-SECURITY-TOKEN")

auth_headers = {
    "X-IG-API-KEY": IG_API_KEY,
    "CST": CST,
    "X-SECURITY-TOKEN": TOKEN,
    "Content-Type": "application/json",
    "Accept": "application/json",
    "VERSION": "2"
}

# Gold
print("🥇 GOLD - Fetching 15-min data...")
GOLD_EPIC = "CS.D.CFAGOLD.CFA.IP"

price_resp = session.get(
    f"https://api.ig.com/gateway/deal/prices/{GOLD_EPIC}",
    params={"resolution": "MINUTE_15", "from": "2026-05-01T00:00:00"},
    headers=auth_headers
)
print(f"Status: {price_resp.status_code}")

if price_resp.status_code == 200:
    data = price_resp.json()
    
    if "prices" in data:
        prices = data["prices"]
        print(f"✅ Retrieved {len(prices)} candles")
        
        df = pd.DataFrame(prices)
        df_out = pd.DataFrame()
        df_out["datetime"] = pd.to_datetime(df["snapshotTime"], unit="ms")
        df_out["open"] = df["mid"].apply(lambda x: x.get("open", 0) if pd.notna(x) and isinstance(x, dict) else 0)
        df_out["high"] = df["mid"].apply(lambda x: x.get("high", 0) if pd.notna(x) and isinstance(x, dict) else 0)
        df_out["low"] = df["mid"].apply(lambda x: x.get("low", 0) if pd.notna(x) and isinstance(x, dict) else 0)
        df_out["close"] = df["mid"].apply(lambda x: x.get("close", 0) if pd.notna(x) and isinstance(x, dict) else 0)
        
        print(f"\n📈 {df_out['datetime'].min()} → {df_out['datetime'].max()}")
        print(f"Total bars: {len(df_out)}")
        
        df_out.to_csv("/home/palbot/Projects/log-fib-scalper/data/IG_GOLD_15min.csv", index=False)
        print(f"💾 Saved: data/IG_GOLD_15min.csv")
        
        print(f"\nLast 10 candles:")
        print(f"{'Time':<22} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10}")
        print("-" * 66)
        for _, row in df_out.tail(10).iterrows():
            t = row["datetime"].strftime("%Y-%m-%d %H:%M")
            print(f"{t:<22} {row['open']:>10.2f} {row['high']:>10.2f} {row['low']:>10.2f} {row['close']:>10.2f}")
        
        print(f"\n💰 Current Gold: ${df_out['close'].iloc[-1]:.2f}")
        
    elif "errorCode" in data:
        print(f"❌ API Error: {data['errorCode']}")
    else:
        print(f"Response: {data}")
else:
    print(f"HTTP Error: {price_resp.status_code}")
    print(f"Response: {price_resp.text[:500]}")

print()
print("🥈 SILVER - Fetching 15-min data...")
SILVER_EPIC = "CS.D.CFASILVER.CFA.IP"

price_resp_ag = session.get(
    f"https://api.ig.com/gateway/deal/prices/{SILVER_EPIC}",
    params={"resolution": "MINUTE_15", "from": "2026-05-01T00:00:00"},
    headers=auth_headers
)
print(f"Status: {price_resp_ag.status_code}")

if price_resp_ag.status_code == 200:
    data = price_resp_ag.json()
    
    if "prices" in data:
        prices = data["prices"]
        print(f"✅ Retrieved {len(prices)} candles")
        
        df = pd.DataFrame(prices)
        df_out = pd.DataFrame()
        df_out["datetime"] = pd.to_datetime(df["snapshotTime"], unit="ms")
        df_out["open"] = df["mid"].apply(lambda x: x.get("open", 0) if pd.notna(x) and isinstance(x, dict) else 0)
        df_out["high"] = df["mid"].apply(lambda x: x.get("high", 0) if pd.notna(x) and isinstance(x, dict) else 0)
        df_out["low"] = df["mid"].apply(lambda x: x.get("low", 0) if pd.notna(x) and isinstance(x, dict) else 0)
        df_out["close"] = df["mid"].apply(lambda x: x.get("close", 0) if pd.notna(x) and isinstance(x, dict) else 0)
        
        print(f"\n📈 {df_out['datetime'].min()} → {df_out['datetime'].max()}")
        
        df_out.to_csv("/home/palbot/Projects/log-fib-scalper/data/IG_SILVER_15min.csv", index=False)
        print(f"💾 Saved: data/IG_SILVER_15min.csv")
        
        print(f"\n💰 Current Silver: ${df_out['close'].iloc[-1]:.2f}")
    elif "errorCode" in data:
        print(f"❌ API Error: {data['errorCode']}")
else:
    print(f"HTTP Error: {price_resp_ag.status_code}")

print()
print("=" * 80)
print("✅ COMPLETE")
print("=" * 80)
