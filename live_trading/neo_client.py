"""
═══════════════════════════════════════════════════════════════
KOTAK NEO API V2 CLIENT (Official SDK)
═══════════════════════════════════════════════════════════════

Wrapper around the official Kotak Neo Python SDK for easier integration
with the log-fib scalper strategy.

Official SDK: https://github.com/Kotak-Neo/Kotak-neo-api-v2
API Docs: https://dev.kotakneo.io/
"""

import time
from datetime import datetime
from typing import Optional, Dict, Any, List

try:
    from neo_api_client import NeoAPI
    HAS_SDK = True
except ImportError:
    HAS_SDK = False


class KotakNeoClient:
    def __init__(self, config: Dict[str, str]):
        """
        Initialize Kotak Neo API V2 Client using official SDK
        
        config: {
            "consumer_key": "YOUR_CONSUMER_KEY",
            "totp_key": "YOUR_TOTP_SECRET",
            "mobile_number": "+91XXXXXXXXXX",
            "password": "YOUR_PASSWORD",
            "mpin": "YOUR_MPIN",
            "ucc": "YOUR_UCC"
        }
        """
        if not HAS_SDK:
            raise ImportError(
                "neo_api_client not installed. "
                "Run: pip install 'git+https://github.com/Kotak-Neo/Kotak-neo-api-v2.git@v2.0.1#egg=neo_api_client'"
            )
        
        self.config = config
        self.client = NeoAPI(
            consumer_key=config.get("consumer_key", ""),
            environment="prod"
        )
        self.authenticated = False
        self.ucc = config.get("ucc", "")
        
    def login(self) -> bool:
        """
        Authenticate with Kotak Neo using TOTP
        
        Flow:
        1. Generate TOTP (user must provide from authenticator app)
        2. Call totp_login with mobile, UCC, TOTP
        3. Call totp_validate with MPIN
        """
        try:
            # Note: TOTP must be generated from Google Authenticator app
            # We cannot generate it programmatically without the secret
            # User should provide the current TOTP code
            print("ℹ️  TOTP login requires current 6-digit code from authenticator app")
            print("   The TOTP_KEY in config is for your reference only")
            print("   Please enter current TOTP when prompted...")
            
            # For automated trading, you need to:
            # 1. Store TOTP secret securely
            # 2. Use pyotp to generate codes (already installed)
            import pyotp
            totp_secret = self.config.get("totp_key", "")
            totp = pyotp.TOTP(totp_secret)
            current_totp = totp.now()
            
            print(f"📱 Generated TOTP: {current_totp}")
            
            # Step 1: TOTP Login (gets view token + session id)
            self.client.totp_login(
                mobile_number=self.config.get("mobile_number", ""),
                ucc=self.config.get("ucc", ""),
                totp=current_totp
            )
            
            # Step 2: TOTP Validate (gets trade token)
            self.client.totp_validate(
                mpin=self.config.get("mpin", "")
            )
            
            self.authenticated = True
            print(f"✅ Kotak Neo Login successful | UCC: {self.ucc}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Kotak Neo Login error: {error_msg}")
            
            # Common error handling
            if "Invalid TOTP" in error_msg:
                print("   → TOTP code expired or incorrect. Check time sync on authenticator app.")
            elif "Invalid MPIN" in error_msg:
                print("   → MPIN is incorrect.")
            elif "Invalid UCC" in error_msg or "Invalid mobile" in error_msg:
                print("   → UCC or mobile number mismatch.")
            
            return False
    
    def get_market_price(self, instrument_token: str, exchange_segment: str = "nse_cm") -> Optional[Dict[str, Any]]:
        """
        Fetch real-time market price for an instrument
        
        instrument_token: Kotak Neo instrument token (e.g., "10000" for Nifty50)
        exchange_segment: Default "nse_cm" for NSE cash/index
        """
        try:
            if not self.authenticated:
                if not self.login():
                    return None
            
            # Get quotes
            instrument_tokens = [
                {"instrument_token": instrument_token, "exchange_segment": exchange_segment}
            ]
            
            quote_data = self.client.quotes(
                instrument_tokens=instrument_tokens,
                quote_type="all"  # Get all data
            )
            
            if quote_data and isinstance(quote_data, list) and len(quote_data) > 0:
                quote = quote_data[0]
                # Handle different response formats
                ltp = quote.get("ltp") or quote.get("last_price") or quote.get("last_traded_price", 0)
                return {
                    "instrument_token": instrument_token,
                    "last_traded": float(ltp) if ltp else 0,
                    "bid": float(quote.get("buy_price1", quote.get("bid", 0))),
                    "ask": float(quote.get("sell_price1", quote.get("ask", 0))),
                    "high": float(quote.get("high", 0)),
                    "low": float(quote.get("low", 0)),
                    "timestamp": datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Price fetch error: {e}")
            return None
    
    def get_historical_data(self, instrument_token: str, from_date: str, to_date: str, interval: str = "5minute") -> Optional[list]:
        """
        Fetch historical OHLC data
        
        Note: Official SDK doesn't have direct historical API.
        This is a placeholder - you may need to use alternative data source.
        """
        print("⚠️  Historical data not available via Kotak Neo API v2 SDK")
        print("   Consider using: yfinance, broker historical API, or data vendor")
        return None
    
    def place_order(self,
                    exchange_segment: str,
                    product: str,
                    order_type: str,
                    quantity: int,
                    trading_symbol: str,
                    transaction_type: str,
                    price: Optional[float] = None,
                    trigger_price: Optional[float] = None,
                    validity: str = "DAY",
                    tag: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Place a trade order using official SDK
        
        exchange_segment: "nse_cm", "bse_cm", "nse_fo", "bse_fo", "cde_fo", "mcx_fo"
        product: "NRML", "CNC", "MIS", "CO", "BO"
        order_type: "L" (Limit), "MKT" (Market), "SL" (Stop Loss), "SL-M" (SL Market)
        quantity: Number of units
        trading_symbol: Scrip trading symbol from master file
        transaction_type: "B" (Buy), "S" (Sell)
        price: Limit price (for L/SL orders)
        trigger_price: Trigger price (for SL/SL-M orders)
        validity: "DAY", "IOC", "GTC", "EOS", "GTD"
        tag: Custom order tag for tracking
        """
        try:
            if not self.authenticated:
                if not self.login():
                    return None
            
            # Prepare order parameters
            order_params = {
                "exchange_segment": exchange_segment,
                "product": product,
                "order_type": order_type,
                "quantity": str(quantity),
                "trading_symbol": trading_symbol,
                "transaction_type": transaction_type,
                "validity": validity,
                "amo": "NO"
            }
            
            if price:
                order_params["price"] = str(price)
            
            if trigger_price:
                order_params["trigger_price"] = str(trigger_price)
            
            if tag:
                order_params["tag"] = tag
            
            # Place order
            response = self.client.place_order(**order_params)
            
            if response and isinstance(response, dict):
                if response.get("status") == "success" or response.get("order_id"):
                    print(f"✅ Order placed: {transaction_type} {quantity} | ID: {response.get('order_id', 'N/A')}")
                    return {
                        "success": True,
                        "order_id": response.get("order_id", ""),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    print(f"❌ Order failed: {response.get('message', 'Unknown error')}")
                    return {
                        "success": False,
                        "error": response.get("message", "Unknown error"),
                        "response": response
                    }
            
            return {
                "success": False,
                "error": "Empty response from API"
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Order error: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """Get account balance and margin"""
        try:
            if not self.authenticated:
                if not self.login():
                    return None
            
            # Get limits
            limits_data = self.client.limits(segment="ALL", exchange="NSE", product="ALL")
            
            if limits_data and isinstance(limits_data, dict):
                return {
                    "available": float(limits_data.get("available_balance", 0)),
                    "used": float(limits_data.get("used_balance", 0)),
                    "total": float(limits_data.get("total_balance", 0)),
                    "timestamp": datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Balance fetch error: {e}")
            return None
    
    def get_positions(self) -> Optional[List[Dict[str, Any]]]:
        """Get current positions"""
        try:
            if not self.authenticated:
                if not self.login():
                    return None
            
            positions_data = self.client.positions()
            
            if positions_data and isinstance(positions_data, list):
                return positions_data
            
            return None
            
        except Exception as e:
            print(f"❌ Positions fetch error: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            if not self.authenticated:
                if not self.login():
                    return False
            
            self.client.cancel_order(order_id=order_id)
            print(f"✅ Order {order_id} cancelled")
            return True
            
        except Exception as e:
            print(f"❌ Cancel order error: {e}")
            return False
