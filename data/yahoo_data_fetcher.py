"""
FREE ALTERNATIVE: Fetch Gold/Silver prices from public APIs
Options:
1. MetalpriceAPI (free tier)
2. GoldAPI.io (free tier)
3. Yahoo Finance (free, no auth)

Let's try Yahoo Finance - it's free and reliable
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

print("=" * 70)
print("YAHOO FINANCE - GOLD & SILVER PRICES")
print("=" * 70)

# Yahoo Finance tickers
# GC=F = Gold futures
# SI=F = Silver futures

tickers = {
    'gold': 'GC=F',
    'silver': 'SI=F',
}

for name, ticker in tickers.items():
    print(f"\n📊 {name.upper()} ({ticker})")
    
    try:
        # Fetch 5-minute data
        data = yf.download(ticker, period='5d', interval='5m', progress=False)
        
        if len(data) == 0:
            print(f"⚠️ No data returned")
            continue
        
        # Handle multi-level columns (Yahoo format)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
        
        print(f"✅ Fetched {len(data)} candles")
        print(f"   Range: {data.index.min()} to {data.index.max()}")
        print(f"   Price: ${data['Close'].iloc[0]:.2f} → ${data['Close'].iloc[-1]:.2f}")
        
        # Save to CSV
        df = data.reset_index()
        df.columns = ['time', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
        df['time'] = pd.to_datetime(df['time'])
        
        csv_path = f'/home/palbot/Projects/log-fib-scalper/data/YAHOO_{name.upper()}_5min.csv'
        df.to_csv(csv_path, index=False)
        print(f"💾 Saved to {csv_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

# Also try to get current price
print("\n" + "=" * 70)
print("CURRENT PRICES")
print("=" * 70)

for name, ticker in tickers.items():
    try:
        t = yf.Ticker(ticker)
        info = t.info
        current = info.get('regularMarketPrice', info.get('previousClose', 'N/A'))
        print(f"{name.upper()}: ${current:.2f}" if isinstance(current, (int, float)) else f"{name.upper()}: {current}")
    except Exception as e:
        print(f"{name.upper()}: Error - {e}")
