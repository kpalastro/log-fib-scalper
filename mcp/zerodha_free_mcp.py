#!/usr/bin/env python3
"""
Zerodha Free API MCP Server (via Enctoken Wrapper)

Uses the kite_trade.py wrapper to access Zerodha data without paid API key.
Generates enctoken from login credentials and uses Kite OMS endpoints.

WARNING: This uses unofficial API access. Use at your own risk.
Credentials are stored in plaintext - secure them properly.

Usage:
  python mcp/zerodha_free_mcp.py
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Any
from pathlib import Path

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("ERROR: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Add parent directory to path to import kite_trade
SCRIPT_DIR = Path(__file__).parent
WRAPPER_DIR = Path("/home/palbot/Downloads/zerodhahistoricaldata")
sys.path.insert(0, str(WRAPPER_DIR))

try:
    from kite_trade import KiteApp, get_enctoken
except ImportError as e:
    print(f"ERROR: Cannot import kite_trade wrapper: {e}", file=sys.stderr)
    print(f"Wrapper location: {WRAPPER_DIR}", file=sys.stderr)
    sys.exit(1)

# Configuration
# Option 1: Environment variables
USER_ID = os.environ.get("ZERODHA_USER_ID", "")
PASSWORD = os.environ.get("ZERODHA_PASSWORD", "")
TWOFA = os.environ.get("ZERODHA_TWOF A", "")

# Option 2: Config file (~/.zerodha_credentials.json)
CREDENTIALS_FILE = Path.home() / ".zerodha_credentials.json"

# Create MCP server
app = Server("zerodha-free")

# Kite App instance
kite = None
enctoken = None
enctoken_expiry = None


def log(msg: str):
    """Log to stderr for debugging"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", file=sys.stderr)


def load_credentials() -> dict:
    """Load credentials from environment or config file"""
    # Check environment first
    if all([USER_ID, PASSWORD, TWOFA]):
        log("Using credentials from environment variables")
        return {
            "user_id": USER_ID,
            "password": PASSWORD,
            "twofa": TWOFA
        }
    
    # Check config file
    if CREDENTIALS_FILE.exists():
        try:
            with open(CREDENTIALS_FILE, 'r') as f:
                creds = json.load(f)
            log("Using credentials from config file")
            
            # Check if enctoken is still valid
            if creds.get("enctoken") and creds.get("enctoken_expiry"):
                try:
                    expiry = datetime.fromisoformat(creds["enctoken_expiry"])
                    if datetime.now() < expiry:
                        log(f"✅ Enctoken valid until {expiry.strftime('%Y-%m-%d %H:%M')}")
                        creds["_enctoken_valid"] = True
                    else:
                        log("⚠️  Enctoken expired, will regenerate")
                        creds["_enctoken_valid"] = False
                except:
                    creds["_enctoken_valid"] = False
            else:
                creds["_enctoken_valid"] = False
            
            return creds
        except Exception as e:
            log(f"Error reading config file: {e}")
    
    # No credentials found
    return {}


def save_credentials(creds: dict):
    """Save credentials to config file"""
    try:
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(creds, f, indent=2)
        # Set restrictive permissions
        os.chmod(CREDENTIALS_FILE, 0o600)
        log("Credentials saved to config file")
    except Exception as e:
        log(f"Error saving credentials: {e}")


def init_kite() -> KiteApp:
    """Initialize Kite App with enctoken"""
    global kite, enctoken, enctoken_expiry
    
    creds = load_credentials()
    
    if not creds:
        raise ValueError(
            "No Zerodha credentials found. "
            "Set environment variables (ZERODHA_USER_ID, ZERODHA_PASSWORD, ZERODHA_TWOF A) "
            f"or create config file at {CREDENTIALS_FILE}"
        )
    
    # Check if we have a valid saved enctoken
    if creds.get("_enctoken_valid") and creds.get("enctoken"):
        log("Using saved enctoken...")
        enctoken = creds["enctoken"]
        kite = KiteApp(enctoken=enctoken)
        enctoken_expiry = datetime.fromisoformat(creds["enctoken_expiry"])
        
        # Test if enctoken still works
        try:
            profile = kite.profile()
            log(f"✅ Connected as: {profile.get('user_id', 'unknown')} (using saved enctoken)")
            return kite
        except Exception as e:
            log(f"Saved enctoken failed: {e}. Regenerating...")
            # Fall through to regenerate
    
    # Generate new enctoken
    try:
        log("Getting new enctoken from credentials...")
        enctoken = get_enctoken(
            userid=creds["user_id"],
            password=creds["password"],
            twofa=creds["twofa"]
        )
        log(f"✅ Enctoken obtained: {enctoken[:20]}...")
        
        kite = KiteApp(enctoken=enctoken)
        
        # Set expiry to 24 hours from now
        enctoken_expiry = datetime.now() + timedelta(hours=24)
        
        # Save enctoken for future use
        save_enctoken(creds, enctoken, enctoken_expiry)
        
        # Test connection
        profile = kite.profile()
        log(f"✅ Connected as: {profile.get('user_id', 'unknown')}")
        
        return kite
    
    except Exception as e:
        log(f"Initialization failed: {e}")
        raise


def save_enctoken(creds: dict, enctoken: str, expiry: datetime):
    """Save enctoken to credentials file for reuse"""
    try:
        creds["enctoken"] = enctoken
        creds["enctoken_expiry"] = expiry.isoformat()
        
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(creds, f, indent=2)
        os.chmod(CREDENTIALS_FILE, 0o600)
        log(f"💾 Enctoken saved (valid until {expiry.strftime('%Y-%m-%d %H:%M')})")
    except Exception as e:
        log(f"Error saving enctoken: {e}")


def ensure_kite():
    """Ensure Kite is initialized and enctoken is valid"""
    global kite, enctoken_expiry
    
    if kite is None:
        init_kite()
    elif enctoken_expiry and datetime.now() > enctoken_expiry:
        log("Enctoken expired, re-initializing...")
        init_kite()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Zerodha tools"""
    return [
        Tool(
            name="zerodha_get_ltp",
            description="Get last traded price for Nifty/Banknifty or any instrument",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Instrument tokens or trading symbols (e.g., ['256265', '29934084'])"
                    }
                },
                "required": ["symbols"]
            }
        ),
        Tool(
            name="zerodha_get_instruments",
            description="Get list of all trading instruments for an exchange (NSE, NFO, BFO, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "exchange": {
                        "type": "string",
                        "enum": ["NSE", "NFO", "BFO", "BSE", "MCX", "CDS"],
                        "description": "Exchange to fetch instruments for",
                        "default": "NSE"
                    }
                },
                "required": ["exchange"]
            }
        ),
        Tool(
            name="zerodha_search_instrument",
            description="Search for an instrument by symbol name (e.g., NIFTY, BANKNIFTY)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'NIFTY', 'BANKNIFTY', 'RELIANCE')"
                    },
                    "exchange": {
                        "type": "string",
                        "enum": ["NSE", "NFO", "BFO"],
                        "description": "Filter by exchange"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="zerodha_get_historical",
            description="Get historical candle data (OHLCV) for an instrument token",
            inputSchema={
                "type": "object",
                "properties": {
                    "instrument_token": {
                        "type": "integer",
                        "description": "Instrument token (e.g., 256265 for NIFTY 50)"
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD or ISO format)"
                    },
                    "to_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD or ISO format)"
                    },
                    "interval": {
                        "type": "string",
                        "enum": ["minute", "3minute", "5minute", "15minute", "30minute", "60minute", "day"],
                        "description": "Candle interval",
                        "default": "5minute"
                    },
                    "continuous": {
                        "type": "boolean",
                        "description": "Get continuous futures data",
                        "default": False
                    },
                    "oi": {
                        "type": "boolean",
                        "description": "Include open interest data",
                        "default": False
                    }
                },
                "required": ["instrument_token", "from_date", "to_date"]
            }
        ),
        Tool(
            name="zerodha_get_margins",
            description="Get trading margins available in the account",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="zerodha_get_profile",
            description="Get user profile information",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="zerodha_get_nifty_token",
            description="Get the current instrument token for Nifty futures (auto-detects current month)",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="zerodha_get_banknifty_token",
            description="Get the current instrument token for Banknifty futures (auto-detects current month)",
            inputSchema={"type": "object", "properties": {}}
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls"""
    log(f"Tool call: {name} with args: {arguments}")
    
    try:
        ensure_kite()
        
        if name == "zerodha_get_ltp":
            symbols = arguments.get("symbols", [])
            if not symbols:
                return [TextContent(type="text", text="❌ Error: symbols array is required")]
            
            # Convert to format expected by wrapper (exchange:token)
            formatted = []
            for sym in symbols:
                if ":" not in str(sym):
                    # Assume it's a token, default to NFO
                    formatted.append(f"NFO:{sym}")
                else:
                    formatted.append(sym)
            
            ltp_data = kite.quote_ltp(formatted)
            return [TextContent(type="text", text=json.dumps(ltp_data, indent=2, default=str))]
        
        elif name == "zerodha_get_instruments":
            exchange = arguments.get("exchange", "NSE")
            
            instruments = kite.instruments(exchange)
            
            return [TextContent(type="text", text=json.dumps({
                "exchange": exchange,
                "count": len(instruments),
                "instruments": instruments[:200]  # Limit response size
            }, indent=2, default=str))]
        
        elif name == "zerodha_search_instrument":
            query = arguments.get("query", "").upper()
            exchange_filter = arguments.get("exchange")
            
            if not query:
                return [TextContent(type="text", text="❌ Error: query is required")]
            
            # Get instruments from specified exchange or all
            if exchange_filter:
                instruments = kite.instruments(exchange_filter)
            else:
                # Search across major exchanges
                instruments = kite.instruments("NFO") + kite.instruments("NSE")
            
            # Search in symbol, tradingsymbol, and name
            matches = []
            for inst in instruments:
                symbol = str(inst.get("symbol", "")).upper()
                tradingsymbol = str(inst.get("tradingsymbol", "")).upper()
                name = str(inst.get("name", "")).upper()
                
                if query in symbol or query in tradingsymbol or query in name:
                    matches.append(inst)
                    if len(matches) >= 50:
                        break
            
            return [TextContent(type="text", text=json.dumps({
                "query": query,
                "exchange": exchange_filter or "all",
                "matches_found": len(matches),
                "matches": matches
            }, indent=2, default=str))]
        
        elif name == "zerodha_get_historical":
            instrument_token = arguments.get("instrument_token")
            from_date = arguments.get("from_date")
            to_date = arguments.get("to_date")
            interval = arguments.get("interval", "5minute")
            continuous = arguments.get("continuous", False)
            oi = arguments.get("oi", False)
            
            if not all([instrument_token, from_date, to_date]):
                return [TextContent(type="text", text="❌ Error: instrument_token, from_date, and to_date are required")]
            
            candles = kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=interval,
                continuous=continuous,
                oi=oi
            )
            
            return [TextContent(type="text", text=json.dumps({
                "instrument_token": instrument_token,
                "interval": interval,
                "from": from_date,
                "to": to_date,
                "candles_count": len(candles),
                "candles": candles
            }, indent=2, default=str))]
        
        elif name == "zerodha_get_margins":
            margins = kite.margins()
            return [TextContent(type="text", text=json.dumps(margins, indent=2, default=str))]
        
        elif name == "zerodha_get_profile":
            profile = kite.profile()
            return [TextContent(type="text", text=json.dumps(profile, indent=2, default=str))]
        
        elif name == "zerodha_get_nifty_token":
            # Search for current month Nifty futures
            now = datetime.now()
            month_code = now.strftime("%b").upper()[:3]
            year_suffix = now.strftime("%y")
            
            # Search NFO instruments
            instruments = kite.instruments("NFO")
            
            # Find Nifty futures for current month
            nifty_fut = None
            for inst in instruments:
                ts = inst.get("tradingsymbol", "")
                if f"NIFTY{now.day:02d}{month_code}" in str(ts).upper() and inst.get("instrument_type") == "FUT":
                    nifty_fut = inst
                    break
            
            if not nifty_fut:
                # Fallback: search for any Nifty FUT
                for inst in instruments:
                    ts = str(inst.get("tradingsymbol", "")).upper()
                    if "NIFTY" in ts and "FUT" in ts:
                        nifty_fut = inst
                        break
            
            if nifty_fut:
                return [TextContent(type="text", text=json.dumps({
                    "symbol": nifty_fut.get("tradingsymbol"),
                    "instrument_token": nifty_fut.get("instrument_token"),
                    "exchange": nifty_fut.get("exchange"),
                    "lot_size": nifty_fut.get("lot_size"),
                    "expiry": str(nifty_fut.get("expiry")) if nifty_fut.get("expiry") else None
                }, indent=2, default=str))]
            else:
                return [TextContent(type="text", text="❌ Could not find Nifty futures instrument")]
        
        elif name == "zerodha_get_banknifty_token":
            # Search for current month Banknifty futures
            now = datetime.now()
            month_code = now.strftime("%b").upper()[:3]
            
            instruments = kite.instruments("NFO")
            
            banknifty_fut = None
            for inst in instruments:
                ts = inst.get("tradingsymbol", "")
                if f"BANKNIFTY{now.day:02d}{month_code}" in str(ts).upper() and inst.get("instrument_type") == "FUT":
                    banknifty_fut = inst
                    break
            
            if not banknifty_fut:
                for inst in instruments:
                    ts = str(inst.get("tradingsymbol", "")).upper()
                    if "BANKNIFTY" in ts and "FUT" in ts:
                        banknifty_fut = inst
                        break
            
            if banknifty_fut:
                return [TextContent(type="text", text=json.dumps({
                    "symbol": banknifty_fut.get("tradingsymbol"),
                    "instrument_token": banknifty_fut.get("instrument_token"),
                    "exchange": banknifty_fut.get("exchange"),
                    "lot_size": banknifty_fut.get("lot_size"),
                    "expiry": str(banknifty_fut.get("expiry")) if banknifty_fut.get("expiry") else None
                }, indent=2, default=str))]
            else:
                return [TextContent(type="text", text="❌ Could not find Banknifty futures instrument")]
        
        else:
            return [TextContent(type="text", text=f"❌ Error: Unknown tool '{name}'")]
    
    except Exception as e:
        log(f"Error in {name}: {e}")
        import traceback
        traceback.print_exc()
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]


async def main():
    """Run the MCP server"""
    log("=" * 60)
    log("Zerodha Free API MCP Server (Enctoken Wrapper)")
    log("=" * 60)
    log(f"Wrapper location: {WRAPPER_DIR}")
    log(f"Credentials file: {CREDENTIALS_FILE}")
    log("")
    
    creds = load_credentials()
    if creds:
        log(f"Credentials found for user: {creds.get('user_id', 'unknown')}")
    else:
        log("❌ No credentials found!")
        log("")
        log("Set up credentials using ONE of these methods:")
        log("")
        log("Method 1 - Environment variables:")
        log("  export ZERODHA_USER_ID=your_user_id")
        log("  export ZERODHA_PASSWORD=your_password")
        log("  export ZERODHA_TWOF A=your_pin_or_totp")
        log("")
        log(f"Method 2 - Config file ({CREDENTIALS_FILE}):")
        log('  {"user_id": "YOUR_ID", "password": "YOUR_PASS", "twofa": "YOUR_PIN"}')
        log("")
        log("⚠️  WARNING: Credentials stored in plaintext. Secure your files!")
        log("")
    
    log("Starting MCP server (stdio)...")
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
