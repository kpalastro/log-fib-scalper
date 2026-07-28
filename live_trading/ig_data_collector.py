#!/usr/bin/env python3
"""
IG Markets Historical Data Builder
Polls IG watchlist every 15 minutes and appends to historical CSV
Run via cron: */15 * * * * /path/to/ig_data_collector.py
"""

import os
import sys
from dotenv import load_dotenv
import requests
import pandas as pd
from datetime import datetime
import json

load_dotenv("/home/palbot/Projects/log-fib-scalper/live_trading/.env")

IG_API_KEY = os.getenv("IG_API_KEY")
IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")

# Output file
OUTPUT_CSV = "/home/palbot/Projects/log-fib-scalper/data/IG_GOLD_15min_live.csv"
WATCHLIST_ID = "2509953"

def login():
    """Login to IG and return session with auth headers"""
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
        print(f"❌ Login failed: {resp.status_code}", file=sys.stderr)
        return None, None
    
    CST = resp.headers.get("CST")
    TOKEN = resp.headers.get("X-SECURITY-TOKEN")
    
    auth_headers = {
        "X-IG-API-KEY": IG_API_KEY,
        "CST": CST,
        "X-SECURITY-TOKEN": TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    return session, auth_headers

def fetch_watchlist(session, auth_headers):
    """Fetch watchlist with live prices"""
    url = f"https://deal.ig.com/nwtpdeal/wtp/markets/watchlists/{WATCHLIST_ID}?priceInSizeFlag=true"
    
    r = session.get(url, headers=auth_headers)
    
    if r.status_code != 200:
        print(f"❌ Watchlist fetch failed: {r.status_code}", file=sys.stderr)
        return []
    
    data = r.json()
    
    # Parse watchlist data
    instruments = []
    for item in data:
        if "instrumentData" not in item or "marketSnapshotData" not in item:
            continue
        
        inst = item["instrumentData"]
        snap = item["marketSnapshotData"]
        
        instruments.append({
            "epic": inst.get("epic", ""),
            "name": inst.get("marketName", ""),
            "bid": snap.get("bidFormatted", ""),
            "offer": snap.get("offerFormatted", ""),
            "high": snap.get("highFormatted", ""),
            "low": snap.get("lowFormatted", ""),
            "netChange": snap.get("netChange", ""),
            "percentChange": snap.get("percentageChange", ""),
            "updateTime": snap.get("updateTime", ""),
            "snapshotTime": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return instruments

def append_to_csv(instruments, output_file):
    """Append new data to CSV file"""
    
    # Convert to DataFrame
    df_new = pd.DataFrame(instruments)
    
    # Load existing data if exists
    if os.path.exists(output_file):
        df_existing = pd.read_csv(output_file)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new
    
    # Remove exact duplicates (same epic + snapshotTime)
    df_combined = df_combined.drop_duplicates(subset=["epic", "snapshotTime"], keep="last")
    
    # Sort by snapshotTime
    df_combined = df_combined.sort_values("snapshotTime")
    
    # Save
    df_combined.to_csv(output_file, index=False)
    
    return len(df_new), len(df_combined)

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting IG data collection...")
    
    # Login
    session, auth_headers = login()
    if session is None:
        return 1
    
    print("✅ Logged in successfully")
    
    # Fetch watchlist
    instruments = fetch_watchlist(session, auth_headers)
    
    if not instruments:
        print("❌ No instruments fetched", file=sys.stderr)
        return 1
    
    print(f"✅ Fetched {len(instruments)} instruments")
    
    # Filter for gold/silver
    gold_instruments = [i for i in instruments if "gold" in i["name"].lower() or "silver" in i["name"].lower()]
    
    if gold_instruments:
        print(f"🥇🥈 Gold/Silver instruments: {len(gold_instruments)}")
        for inst in gold_instruments:
            print(f"   {inst['name']}: Bid={inst['bid']}, Change={inst['netChange']}")
    else:
        print("⚠️ No gold/silver in watchlist")
    
    # Append to CSV
    new_count, total_count = append_to_csv(instruments, OUTPUT_CSV)
    
    print(f"✅ Appended {new_count} new records")
    print(f"📊 Total records in CSV: {total_count}")
    print(f"💾 Output: {OUTPUT_CSV}")
    
    # Show last few records for gold
    if os.path.exists(OUTPUT_CSV):
        df = pd.read_csv(OUTPUT_CSV)
        gold_df = df[df["epic"] == "CS.D.CFAGOLD.CFA.IP"]
        
        if len(gold_df) > 0:
            print(f"\n🥇 Gold - Last 5 records:")
            print(gold_df.tail()[["snapshotTime", "bid", "offer", "high", "low"]].to_string(index=False))
    
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Collection complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())
