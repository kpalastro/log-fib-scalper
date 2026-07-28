#!/usr/bin/env python3
"""IG Markets - Watchlist + Signals Data Fetcher"""

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
print("📊 IG MARKETS - WATCHLIST + SIGNALS")
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

DEAL_BASE = "https://deal.ig.com"

auth_headers = {
    "X-IG-API-KEY": IG_API_KEY,
    "CST": CST,
    "X-SECURITY-TOKEN": TOKEN,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# ============ WATCHLIST ============
print("=" * 80)
print("📋 WATCHLIST")
print("=" * 80)

WATCHLIST_ID = "2509953"
url = f"{DEAL_BASE}/nwtpdeal/wtp/markets/watchlists/{WATCHLIST_ID}?priceInSizeFlag=true"

wl_resp = session.get(url, headers=auth_headers)
print(f"Status: {wl_resp.status_code}")

gold_silver = []

if wl_resp.status_code == 200:
    data = wl_resp.json()
    
    if isinstance(data, list):
        print(f"✅ Retrieved {len(data)} instruments")
        
        for item in data:
            if "instrumentData" not in item:
                continue
            
            inst = item["instrumentData"]
            snap = item.get("marketSnapshotData", {})
            
            epic = inst.get("epic", "N/A")
            name = inst.get("marketName", "N/A")
            mtype = inst.get("instrumentType", "N/A")
            
            # Extract prices from marketSnapshotData
            bid = snap.get("bid", "N/A")
            offer = snap.get("offer", "N/A")
            ltp = snap.get("lastTradedPrice", "N/A")
            change = snap.get("netChangeAmount", "N/A")
            change_pct = snap.get("percentChange", "N/A")
            
            # Check for gold/silver
            if any(x in name.lower() for x in ["gold", "silver", "xau", "xag"]):
                gold_silver.append({
                    "epic": epic,
                    "name": name,
                    "type": mtype,
                    "bid": bid,
                    "offer": offer,
                    "ltp": ltp,
                    "change": change,
                    "change_pct": change_pct
                })
            
            print(f"\n  {epic} [{mtype}]")
            print(f"    {name}")
            print(f"    Bid: {bid} | Offer: {offer} | LTP: {ltp}")
            if change != "N/A":
                sign = "+" if float(change) > 0 else ""
                print(f"    Change: {sign}{change} ({change_pct}%)")
    
    # Show gold/silver summary
    if gold_silver:
        print()
        print("=" * 80)
        print("🥇🥈 GOLD/SILVER SUMMARY")
        print("=" * 80)
        for gs in gold_silver:
            print(f"\n  {gs['name']}")
            print(f"  EPIC: {gs['epic']}")
            print(f"  LTP: {gs['ltp']}")
            print(f"  Bid: {gs['bid']} | Offer: {gs['offer']}")
            if gs['change'] != "N/A":
                sign = "+" if float(gs['change']) > 0 else ""
                print(f"  Change: {sign}{gs['change']} ({gs['change_pct']}%)")

# ============ SIGNALS ============
print()
print("=" * 80)
print("📈 TRADING SIGNALS")
print("=" * 80)

signals_url = f"{DEAL_BASE}/signals-gateway/signalsFiltered/0/1000"
sig_resp = session.get(signals_url, headers=auth_headers)
print(f"Status: {sig_resp.status_code}")

if sig_resp.status_code == 200:
    signals = sig_resp.json()
    
    if isinstance(signals, list):
        print(f"✅ Retrieved {len(signals)} signals")
        
        # Filter for gold/silver
        gs_signals = []
        for sig in signals:
            instrument = sig.get("instrument", {})
            name = instrument.get("name", "") if isinstance(instrument, dict) else ""
            
            if any(x in name.lower() for x in ["gold", "silver", "xau", "xag"]):
                gs_signals.append(sig)
        
        if gs_signals:
            print()
            print("=" * 80)
            print("🥇🥈 GOLD/SILVER SIGNALS")
            print("=" * 80)
            
            for sig in gs_signals:
                instrument = sig.get("instrument", {})
                name = instrument.get("name", "N/A") if isinstance(instrument, dict) else "N/A"
                epic = instrument.get("epic", "N/A") if isinstance(instrument, dict) else "N/A"
                
                signal_type = sig.get("type", "N/A")
                direction = sig.get("direction", "N/A")
                strength = sig.get("strength", "N/A")
                price = sig.get("price", "N/A")
                timestamp = sig.get("timestamp", "N/A")
                
                # Convert timestamp
                if timestamp and timestamp != "N/A":
                    try:
                        ts = datetime.fromtimestamp(timestamp / 1000)
                        timestamp = ts.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                
                print(f"\n  {name} [{epic}]")
                print(f"  Type: {signal_type} | Direction: {direction} | Strength: {strength}")
                print(f"  Price: {price}")
                print(f"  Time: {timestamp}")
        else:
            print("\n⚠️ No gold/silver signals found")
    elif isinstance(signals, dict):
        print(f"Response keys: {list(signals.keys())}")
        if "signals" in signals:
            print(f"✅ Retrieved {len(signals['signals'])} signals")
else:
    print(f"Error: {sig_resp.text[:300]}")

# ============ FETCH HISTORICAL DATA ============
print()
print("=" * 80)
print("📊 FETCHING HISTORICAL DATA")
print("=" * 80)

for gs in gold_silver:
    epic = gs["epic"]
    name = gs["name"]
    
    print(f"\n{name} [{epic}]")
    
    # Try different price endpoints
    endpoints = [
        ("Prices (api.ig.com)", "https://api.ig.com/gateway/deal/prices/" + epic),
        ("Prices (deal.ig.com)", f"{DEAL_BASE}/nwtpdeal/wtp/prices/{epic}"),
        ("Historical (api.ig.com)", "https://api.ig.com/gateway/deal/historicalprices/" + epic),
        ("Historical (deal.ig.com)", f"{DEAL_BASE}/nwtpdeal/wtp/historicalprices/{epic}"),
    ]
    
    for ep_name, ep_url in endpoints:
        params = {
            "resolution": "MINUTE_15",
            "from": "2026-05-01T00:00:00",
            "priceInSizeFlag": "true"
        }
        
        api_headers = {
            "X-IG-API-KEY": IG_API_KEY,
            "CST": CST,
            "X-SECURITY-TOKEN": TOKEN,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "VERSION": "2"
        }
        
        r = session.get(ep_url, params=params, headers=api_headers)
        
        if r.status_code == 200:
            data = r.json()
            
            # Handle different response formats
            prices = None
            if isinstance(data, dict):
                prices = data.get("prices") or data.get("candles") or data.get("data")
            elif isinstance(data, list):
                prices = data
            
            if prices and len(prices) > 0:
                print(f"  ✅ {ep_name}: {len(prices)} candles")
                
                # Parse and save
                df = pd.DataFrame(prices)
                
                # Try to extract OHLC
                if "mid" in df.columns and isinstance(df["mid"].iloc[0], dict):
                    df_out = pd.DataFrame()
                    df_out["datetime"] = pd.to_datetime(df["snapshotTime"], unit="ms")
                    df_out["open"] = df["mid"].apply(lambda x: x.get("open", 0) if isinstance(x, dict) else 0)
                    df_out["high"] = df["mid"].apply(lambda x: x.get("high", 0) if isinstance(x, dict) else 0)
                    df_out["low"] = df["mid"].apply(lambda x: x.get("low", 0) if isinstance(x, dict) else 0)
                    df_out["close"] = df["mid"].apply(lambda x: x.get("close", 0) if isinstance(x, dict) else 0)
                elif "open" in df.columns:
                    df_out = df[["open", "high", "low", "close"]].copy()
                    if "snapshotTime" in df.columns:
                        df_out["datetime"] = pd.to_datetime(df["snapshotTime"], unit="ms")
                    elif "datetime" in df.columns:
                        df_out["datetime"] = df["datetime"]
                else:
                    print(f"     Unknown format: {list(df.columns)[:10]}")
                    continue
                
                # Save to CSV
                base_name = epic.replace(".", "_").replace("CS_D_", "").replace("IX_D_", "")
                csv_path = f"/home/palbot/Projects/log-fib-scalper/data/IG_{base_name}_15min.csv"
                df_out.to_csv(csv_path, index=False)
                print(f"     💾 Saved: {csv_path}")
                
                print(f"     📈 {df_out['datetime'].min()} → {df_out['datetime'].max()}")
                print(f"     💰 Current: {df_out['close'].iloc[-1]:.2f}")
                break
            else:
                print(f"  ⚠️ {ep_name}: Empty response")
        else:
            print(f"  ❌ {ep_name}: {r.status_code}")

print()
print("=" * 80)
print("✅ COMPLETE")
print("=" * 80)
