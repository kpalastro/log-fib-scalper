#!/usr/bin/env python3
"""
MCP Market Data Server
Provides real-time market data via yfinance (no API key required)

Instruments:
- GOLD: GC=F (Gold futures)
- SILVER: SI=F (Silver futures)
- BTCUSD: BTC-USD (Bitcoin)
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Any

# Try to import MCP SDK
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("ERROR: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("ERROR: yfinance not installed. Run: pip install yfinance pandas", file=sys.stderr)
    sys.exit(1)

# Create MCP server
app = Server("market-data")

# Instrument mapping
INSTRUMENTS = {
    "gold": "GC=F",
    "silver": "SI=F",
    "bitcoin": "BTC-USD",
    "ethereum": "ETH-USD",
    "crude_oil": "CL=F",
    "natural_gas": "NG=F",
}

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available market data tools"""
    return [
        Tool(
            name="get_price",
            description="Get current price for an instrument (gold, silver, bitcoin, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "instrument": {
                        "type": "string",
                        "description": "Instrument name: gold, silver, bitcoin, ethereum, crude_oil, natural_gas",
                        "enum": list(INSTRUMENTS.keys())
                    }
                },
                "required": ["instrument"]
            }
        ),
        Tool(
            name="get_historical_data",
            description="Get historical OHLCV data for an instrument",
            inputSchema={
                "type": "object",
                "properties": {
                    "instrument": {
                        "type": "string",
                        "description": "Instrument name",
                        "enum": list(INSTRUMENTS.keys())
                    },
                    "period": {
                        "type": "string",
                        "description": "Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max",
                        "default": "1mo"
                    },
                    "interval": {
                        "type": "string",
                        "description": "Data interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo",
                        "default": "1d"
                    }
                },
                "required": ["instrument"]
            }
        ),
        Tool(
            name="get_multi_timeframe_analysis",
            description="Get multi-timeframe analysis with swing detection and Log-Fib levels",
            inputSchema={
                "type": "object",
                "properties": {
                    "instrument": {
                        "type": "string",
                        "description": "Instrument name",
                        "enum": list(INSTRUMENTS.keys())
                    },
                    "lookback": {
                        "type": "integer",
                        "description": "Swing detection lookback period",
                        "default": 12
                    },
                    "multiplier": {
                        "type": "number",
                        "description": "Log-Fib multiplier",
                        "default": 0.618
                    }
                },
                "required": ["instrument"]
            }
        ),
        Tool(
            name="list_instruments",
            description="List all available instruments",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls"""
    
    if name == "list_instruments":
        result = {
            "instruments": [
                {"name": k, "ticker": v, "type": "commodity" if k in ["gold", "silver", "crude_oil", "natural_gas"] else "crypto"}
                for k, v in INSTRUMENTS.items()
            ]
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    if name == "get_price":
        instrument = arguments.get("instrument")
        if instrument not in INSTRUMENTS:
            return [TextContent(type="text", text=f"Error: Unknown instrument '{instrument}'")]
        
        ticker = yf.Ticker(INSTRUMENTS[instrument])
        info = ticker.fast_info
        
        result = {
            "instrument": instrument,
            "ticker": INSTRUMENTS[instrument],
            "price": float(info.last_price),
            "currency": "USD",
            "timestamp": datetime.now().isoformat(),
            "change": float(info.last_price - info.previous_close),
            "change_percent": float((info.last_price - info.previous_close) / info.previous_close * 100)
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    if name == "get_historical_data":
        instrument = arguments.get("instrument")
        period = arguments.get("period", "1mo")
        interval = arguments.get("interval", "1d")
        
        if instrument not in INSTRUMENTS:
            return [TextContent(type="text", text=f"Error: Unknown instrument '{instrument}'")]
        
        ticker = yf.Ticker(INSTRUMENTS[instrument])
        df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            return [TextContent(type="text", text="Error: No data available")]
        
        # Convert to serializable format
        result = {
            "instrument": instrument,
            "ticker": INSTRUMENTS[instrument],
            "period": period,
            "interval": interval,
            "bars": len(df),
            "data": []
        }
        
        for idx, row in df.iterrows():
            result["data"].append({
                "time": idx.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]) if "Volume" in df.columns else 0
            })
        
        # Limit to last 100 bars for response size
        result["data"] = result["data"][-100:]
        result["note"] = f"Showing last {len(result['data'])} of {len(df)} bars"
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    if name == "get_multi_timeframe_analysis":
        instrument = arguments.get("instrument")
        lookback = arguments.get("lookback", 12)
        multiplier = arguments.get("multiplier", 0.618)
        
        if instrument not in INSTRUMENTS:
            return [TextContent(type="text", text=f"Error: Unknown instrument '{instrument}'")]
        
        # Fetch 5-day 5-minute data
        ticker = yf.Ticker(INSTRUMENTS[instrument])
        df = ticker.history(period="5d", interval="5m")
        
        if df.empty:
            return [TextContent(type="text", text="Error: No data available")]
        
        # Simple swing detection
        swings = []
        for i in range(lookback, len(df) - lookback):
            window_high = df['High'].iloc[i-lookback:i+lookback+1]
            window_low = df['Low'].iloc[i-lookback:i+lookback+1]
            
            if df['High'].iloc[i] == window_high.max():
                swings.append({
                    "type": "HIGH",
                    "price": float(df['High'].iloc[i]),
                    "anchored": float(df['Low'].iloc[i]),
                    "index": i
                })
            elif df['Low'].iloc[i] == window_low.min():
                swings.append({
                    "type": "LOW",
                    "price": float(df['Low'].iloc[i]),
                    "anchored": float(df['High'].iloc[i]),
                    "index": i
                })
        
        # Calculate Log-Fib levels for recent swings
        def calc_levels(swing):
            price = swing["price"]
            anchored = swing["anchored"]
            eff_range = np.log10(price) * abs(price - anchored) * multiplier * 4.0
            
            if swing["type"] == "HIGH":
                return {
                    "entry_0.5": price - 0.5 * eff_range,
                    "tp_1.0": price - 1.0 * eff_range,
                    "sl_1.618": price - 1.618 * eff_range
                }
            else:
                return {
                    "entry_0.5": price + 0.5 * eff_range,
                    "tp_1.0": price + 1.0 * eff_range,
                    "sl_1.618": price + 1.618 * eff_range
                }
        
        import numpy as np
        
        recent_swings = swings[-5:] if len(swings) > 5 else swings
        for swing in recent_swings:
            swing["levels"] = calc_levels(swing)
        
        current_price = float(df['Close'].iloc[-1])
        
        result = {
            "instrument": instrument,
            "ticker": INSTRUMENTS[instrument],
            "current_price": current_price,
            "timeframe": "5-minute",
            "total_swings": len(swings),
            "recent_swings": recent_swings,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
