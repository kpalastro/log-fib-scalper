#!/usr/bin/env python3
"""IG Markets Watchlist - Get Available Epics"""

import os
from dotenv import load_dotenv
import requests
import json

load_dotenv("/home/palbot/Projects/log-fib-scalper/live_trading/.env")

IG_API_KEY = os.getenv("IG_API_KEY")
IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")

print("=" * 80)
print("📋 IG MARKETS - WATCHLIST EPICS")
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

# Use deal.ig.com base URL for watchlist endpoint
DEAL_BASE = "https://deal.ig.com"

auth_headers = {
    "X-IG-API-KEY": IG_API_KEY,
    "CST": CST,
    "X-SECURITY-TOKEN": TOKEN,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Try watchlist endpoint
WATCHLIST_ID = "2505333"

print(f"\n📡 Fetching watchlist {WATCHLIST_ID}...")
url = f"{DEAL_BASE}/nwtpdeal/wtp/markets/watchlists/{WATCHLIST_ID}?priceInSizeFlag=true"

wl_resp = session.get(url, headers=auth_headers)
print(f"Status: {wl_resp.status_code}")

if wl_resp.status_code == 200:
    data = wl_resp.json()
    print(f"✅ Success!")
    
    # Handle list or dict response
    if isinstance(data, list):
        print(f"Response type: list ({len(data)} items)")
        # Show structure of first item
        if data and isinstance(data[0], dict):
            first = data[0]
            if "instrumentData" in first:
                print(f"\n📊 Parsing instrumentData structure...")
                markets = []
                for item in data:
                    if "instrumentData" in item:
                        inst = item["instrumentData"]
                        snap = item.get("marketSnapshotData", {})
                        markets.append({
                            "epic": inst.get("epic", "N/A"),
                            "name": inst.get("marketName", "N/A"),
                            "bid": snap.get("bid", "N/A"),
                            "offer": snap.get("offer", "N/A"),
                            "type": inst.get("instrumentType", "N/A")
                        })
            else:
                markets = data
        else:
            markets = data
    elif isinstance(data, dict):
        print(f"Response keys: {list(data.keys())}")
        markets = data.get("markets", data.get("marketData", []))
    else:
        print(f"Unknown type: {type(data)}")
        markets = []
    print()
    
    # Find markets/epics
    if markets:
        print(f"📊 Markets in watchlist: {len(markets)}")
        print()
        
        gold_silver = []
        
        for m in markets:
            epic = m.get("epic", "N/A") if isinstance(m, dict) else "N/A"
            name = m.get("name", "N/A") if isinstance(m, dict) else "N/A"
            bid = m.get("bid", "N/A") if isinstance(m, dict) else "N/A"
            offer = m.get("offer", "N/A") if isinstance(m, dict) else "N/A"
            mtype = m.get("type", "N/A") if isinstance(m, dict) else "N/A"
            
            # Check if gold/silver
            if any(x in str(name).lower() for x in ["gold", "silver", "xau", "xag"]):
                gold_silver.append((epic, name, bid, offer, mtype))
            
            print(f"  {epic} [{mtype}]")
            print(f"    {name}")
            print(f"    Bid: {bid} | Offer: {offer}")
            print()
        
        if gold_silver:
            print("=" * 80)
            print("🥇🥈 GOLD/SILVER EPICS FOUND")
            print("=" * 80)
            for epic, name, bid, offer, mtype in gold_silver:
                print(f"\n  EPIC: {epic}")
                print(f"  Name: {name}")
                print(f"  Type: {mtype}")
                print(f"  Bid: {bid} | Offer: {offer}")
                
                # Try to fetch historical data for this epic
                print(f"\n  Fetching 15-min data...")
                api_url = f"https://api.ig.com/gateway/deal/prices/{epic}"
                params = {
                    "resolution": "MINUTE_15",
                    "from": "2026-05-01T00:00:00"
                }
                
                # Need to re-auth for api.ig.com
                api_headers = {
                    "X-IG-API-KEY": IG_API_KEY,
                    "CST": CST,
                    "X-SECURITY-TOKEN": TOKEN,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "VERSION": "2"
                }
                
                price_resp = session.get(api_url, params=params, headers=api_headers)
                if price_resp.status_code == 200:
                    pdata = price_resp.json()
                    if "prices" in pdata:
                        print(f"  ✅ Got {len(pdata['prices'])} candles!")
                    else:
                        print(f"  Response: {pdata}")
                else:
                    print(f"  ❌ Status: {price_resp.status_code}")
                    if price_resp.text:
                        print(f"  Error: {price_resp.text[:200]}")
        else:
            print("\n⚠️ No gold/silver markets in this watchlist")
    
    elif "marketData" in data:
        print(f"\n📊 Market Data: {json.dumps(data['marketData'], indent=2)[:2000]}")
    else:
        print(f"\nFull response: {json.dumps(data, indent=2)[:3000]}")
        
elif wl_resp.status_code == 401:
    print("❌ Authentication failed - trying different auth method...")
    
    # Try without VERSION header
    auth_headers = {
        "X-IG-API-KEY": IG_API_KEY,
        "CST": CST,
        "X-SECURITY-TOKEN": TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    wl_resp2 = session.get(url, headers=auth_headers)
    print(f"Retry status: {wl_resp2.status_code}")
    if wl_resp2.status_code == 200:
        print(f"✅ Success with modified headers!")
        data = wl_resp2.json()
        print(f"Keys: {list(data.keys())}")
else:
    print(f"❌ Error: {wl_resp.text[:500]}")

print()
print("=" * 80)
print("✅ COMPLETE")
print("=" * 80)
