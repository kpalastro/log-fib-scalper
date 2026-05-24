#!/usr/bin/env python3
"""
Zerodha Kite Connect MCP Server

Provides real-time Nifty50/BankNifty data from Zerodha Kite API.

Prerequisites:
  1. Zerodha Kite Connect API key (get from https://kite.trade)
  2. Access token (generated via login flow)
  3. kiteconnect installed: pip install kiteconnect

Configuration:
  Set environment variables or pass as args:
  - ZERODHA_API_KEY: Your Kite Connect API key
  - ZERODHA_ACCESS_TOKEN: Your access token

Usage:
  export ZERODHA_API_KEY=your_api_key
  export ZERODHA_ACCESS_TOKEN=your_access_token
  python mcp/zerodha_kite_mcp.py
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("ERROR: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

try:
    from kiteconnect import KiteConnect
except ImportError:
    print("ERROR: kiteconnect not installed. Run: pip install kiteconnect", file=sys.stderr)
    sys.exit(1)

# Configuration from environment
API_KEY = os.environ.get("ZERODHA_API_KEY", "")
ACCESS_TOKEN = os.environ.get("ZERODHA_ACCESS_TOKEN", "")

# Create MCP server
app = Server("zerodha-kite")

# Kite Connect client
kite = None


def log(msg: str):
    """Log to stderr for debugging"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", file=sys.stderr)


def init_kite() -> KiteConnect:
    """Initialize Kite Connect client"""
    global kite
    
    if not API_KEY:
        raise ValueError("ZERODHA_API_KEY environment variable not set")
    if not ACCESS_TOKEN:
        raise ValueError("ZERODHA_ACCESS_TOKEN environment variable not set")
    
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(ACCESS_TOKEN)
    
    # Test connection
    try:
        profile = kite.profile()
        log(f"Connected as: {profile['user_id']}")
    except Exception as e:
        log(f"Connection test failed: {e}")
        raise
    
    return kite


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Zerodha Kite tools"""
    return [
        Tool(
            name="kite_get_quote",
            description="Get real-time quote for a trading symbol (NSE/BSE/BFO)",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Trading symbol (e.g., NSE:NIFTY 50, NSE:BANKNIFTY, NSE:RELIANCE)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        Tool(
            name="kite_get_ltp",
            description="Get last traded price for one or more symbols",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of trading symbols (e.g., ['NSE:NIFTY 50', 'NSE:BANKNIFTY'])"
                    }
                },
                "required": ["symbols"]
            }
        ),
        Tool(
            name="kite_get_ohlc",
            description="Get OHLC (Open, High, Low, Close) data for symbols",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of trading symbols"
                    }
                },
                "required": ["symbols"]
            }
        ),
        Tool(
            name="kite_get_depth",
            description="Get market depth (order book) for a symbol",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Trading symbol (e.g., NSE:NIFTY 50)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        Tool(
            name="kite_get_historical",
            description="Get historical candle data for a symbol",
            inputSchema={
                "type": "object",
                "properties": {
                    "instrument_token": {
                        "type": "integer",
                        "description": "Instrument token (e.g., 256265 for NIFTY 50)"
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)"
                    },
                    "to_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)"
                    },
                    "interval": {
                        "type": "string",
                        "enum": ["minute", "3minute", "5minute", "15minute", "30minute", "60minute", "day"],
                        "description": "Candle interval",
                        "default": "5minute"
                    }
                },
                "required": ["instrument_token", "from_date", "to_date"]
            }
        ),
        Tool(
            name="kite_get_instruments",
            description="Get list of all trading instruments or filter by exchange",
            inputSchema={
                "type": "object",
                "properties": {
                    "exchange": {
                        "type": "string",
                        "enum": ["NSE", "BSE", "BFO", "NFO", "CDS", "MCX"],
                        "description": "Filter by exchange (optional)"
                    }
                }
            }
        ),
        Tool(
            name="kite_search_instrument",
            description="Search for an instrument by symbol name",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'NIFTY', 'BANKNIFTY', 'RELIANCE')"
                    },
                    "exchange": {
                        "type": "string",
                        "enum": ["NSE", "BFO", "NFO"],
                        "description": "Filter by exchange"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="kite_get_trigger",
            description="Get latest tick/tick-by-tick data (LTP, volume, OI) for symbol",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Trading symbol (e.g., NFO:NIFTY26MAYFUT)"
                    }
                },
                "required": ["symbol"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls"""
    log(f"Tool call: {name} with args: {arguments}")
    
    try:
        # Initialize Kite on first call
        global kite
        if kite is None:
            init_kite()
        
        if name == "kite_get_quote":
            symbol = arguments.get("symbol")
            if not symbol:
                return [TextContent(type="text", text="❌ Error: symbol is required")]
            
            quote = kite.quote(symbol)
            return [TextContent(type="text", text=json.dumps(quote, indent=2))]
        
        elif name == "kite_get_ltp":
            symbols = arguments.get("symbols", [])
            if not symbols:
                return [TextContent(type="text", text="❌ Error: symbols array is required")]
            
            ltp_data = kite.ltp(symbols)
            return [TextContent(type="text", text=json.dumps(ltp_data, indent=2))]
        
        elif name == "kite_get_ohlc":
            symbols = arguments.get("symbols", [])
            if not symbols:
                return [TextContent(type="text", text="❌ Error: symbols array is required")]
            
            ohlc_data = kite.ohlc(symbols)
            return [TextContent(type="text", text=json.dumps(ohlc_data, indent=2))]
        
        elif name == "kite_get_depth":
            symbol = arguments.get("symbol")
            if not symbol:
                return [TextContent(type="text", text="❌ Error: symbol is required")]
            
            depth = kite.depth(symbol)
            return [TextContent(type="text", text=json.dumps(depth, indent=2))]
        
        elif name == "kite_get_historical":
            instrument_token = arguments.get("instrument_token")
            from_date = arguments.get("from_date")
            to_date = arguments.get("to_date")
            interval = arguments.get("interval", "5minute")
            
            if not all([instrument_token, from_date, to_date]):
                return [TextContent(type="text", text="❌ Error: instrument_token, from_date, and to_date are required")]
            
            candles = kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval
            )
            
            return [TextContent(type="text", text=json.dumps({
                "instrument_token": instrument_token,
                "interval": interval,
                "from": from_date,
                "to": to_date,
                "candles_count": len(candles),
                "candles": candles
            }, indent=2))]
        
        elif name == "kite_get_instruments":
            exchange = arguments.get("exchange")
            
            if exchange:
                instruments = kite.instruments(exchange)
            else:
                instruments = kite.instruments()
            
            # Convert to list of dicts (kite returns list of dicts)
            return [TextContent(type="text", text=json.dumps({
                "exchange": exchange or "all",
                "count": len(instruments),
                "instruments": instruments[:100]  # Limit to first 100
            }, indent=2))]
        
        elif name == "kite_search_instrument":
            query = arguments.get("query", "").upper()
            exchange_filter = arguments.get("exchange")
            
            if not query:
                return [TextContent(type="text", text="❌ Error: query is required")]
            
            # Get all instruments and filter
            if exchange_filter:
                instruments = kite.instruments(exchange_filter)
            else:
                instruments = kite.instruments()
            
            # Search
            matches = []
            for inst in instruments:
                symbol = inst.get("symbol", "").upper()
                tradingsymbol = inst.get("tradingsymbol", "").upper()
                name = inst.get("name", "").upper()
                
                if query in symbol or query in tradingsymbol or query in name:
                    matches.append(inst)
                    if len(matches) >= 20:
                        break
            
            return [TextContent(type="text", text=json.dumps({
                "query": query,
                "exchange": exchange_filter or "all",
                "matches_found": len(matches),
                "matches": matches
            }, indent=2))]
        
        elif name == "kite_get_trigger":
            symbol = arguments.get("symbol")
            if not symbol:
                return [TextContent(type="text", text="❌ Error: symbol is required")]
            
            # Get quote with full details
            quote = kite.quote(symbol)
            
            # Extract trigger/tick data
            trigger_data = {}
            if symbol in quote:
                data = quote[symbol]
                trigger_data = {
                    "symbol": symbol,
                    "last_price": data.get("last_price"),
                    "change": data.get("change"),
                    "change_percent": data.get("change") / data.get("ohlc", {}).get("open", 1) * 100 if data.get("ohlc", {}).get("open") else 0,
                    "volume": data.get("volume"),
                    "oi": data.get("oi"),
                    "oi_change": data.get("oi") - data.get("previous_oi", 0),
                    "timestamp": data.get("timestamp"),
                    "mode": "full"
                }
            
            return [TextContent(type="text", text=json.dumps(trigger_data, indent=2))]
        
        else:
            return [TextContent(type="text", text=f"❌ Error: Unknown tool '{name}'")]
    
    except Exception as e:
        log(f"Error in {name}: {e}")
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def main():
    """Run the MCP server"""
    log("=" * 60)
    log("Zerodha Kite Connect MCP Server")
    log("=" * 60)
    log(f"API Key: {API_KEY[:8]}..." if API_KEY else "API Key: NOT SET")
    log(f"Access Token: {ACCESS_TOKEN[:8]}..." if ACCESS_TOKEN else "Access Token: NOT SET")
    log("")
    
    if not API_KEY or not ACCESS_TOKEN:
        log("❌ ERROR: Missing credentials!")
        log("")
        log("Set environment variables:")
        log("  export ZERODHA_API_KEY=your_api_key")
        log("  export ZERODHA_ACCESS_TOKEN=your_access_token")
        log("")
        log("Get API key from: https://kite.trade")
        log("Generate access token via login flow: https://kite.trade/docs/connect/en/#311-login-flow")
        log("")
        log("Server will start but tools will fail until credentials are set.")
    
    log("Starting MCP server (stdio)...")
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
