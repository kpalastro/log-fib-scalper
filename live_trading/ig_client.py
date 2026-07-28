"""
═══════════════════════════════════════════════════════════════
IG MARKETS API CLIENT
═══════════════════════════════════════════════════════════════

Handles authentication, real-time price streaming, and order execution.
"""

import requests
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any

class IGClient:
    def __init__(self, config: Dict[str, str]):
        """
        Initialize IG Markets API Client
        
        config: {
            "api_key": "YOUR_API_KEY",
            "username": "YOUR_USERNAME",
            "password": "YOUR_PASSWORD",
            "account_id": "YOUR_ACCOUNT_ID",
            "demo": True  # Use demo account (recommended for PoC)
        }
        """
        self.config = config
        self.base_url = "https://api.ig.com" if not config.get("demo", True) else "https://demo-api.ig.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-IG-API-KEY": config["api_key"],
            "X-SECURITY-TOKEN": "",
            "CST": ""
        })
        self.authenticated = False
        self.account_id = config.get("account_id", "")
        
    def login(self) -> bool:
        """Authenticate with IG API"""
        try:
            payload = {
                "identifier": self.config["username"],
                "password": self.config["password"]
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-IG-API-KEY": self.config["api_key"],
                "VERSION": "2"
            }
            
            response = self.session.post(
                f"{self.base_url}/v1/session",
                json=payload,
                headers=headers
            )
            
            # Check if we got HTML instead of JSON (invalid API key or endpoint)
            content_type = response.headers.get("Content-Type", "")
            if response.status_code == 200 and "text/html" in content_type:
                print(f"❌ IG Login error: Invalid API key or wrong endpoint. Received HTML instead of JSON.")
                print(f"   Make sure your API key is valid and not expired.")
                print(f"   Generate a new key at: https://www.ig.com/uk/trading-api")
                return False
            
            if response.status_code == 200:
                data = response.json()
                # Update session tokens
                self.session.headers.update({
                    "X-SECURITY-TOKEN": data.get("securityToken", ""),
                    "CST": data.get("clientToken", "")
                })
                self.authenticated = True
                print(f"✅ IG Login successful | Account: {self.account_id}")
                return True
            else:
                print(f"❌ IG Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ IG Login error: {e}")
            return False
    
    def get_market_price(self, epic: str) -> Optional[Dict[str, Any]]:
        """
        Fetch real-time market price for an instrument
        
        epic: Instrument epic (e.g., "IX.D.SILVER.IPV" for XAGUSD)
        """
        try:
            if not self.authenticated:
                if not self.login():
                    return None
            
            headers = self.session.headers.copy()
            headers["VERSION"] = "1"
            
            response = self.session.get(
                f"{self.base_url}/v1/prices/{epic}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "epic": epic,
                    "bid": data.get("bid", 0),
                    "ask": data.get("offer", 0),
                    "high": data.get("highPrice", {}).get("ask", 0),
                    "low": data.get("lowPrice", {}).get("bid", 0),
                    "last_traded": data.get("lastTraded", 0),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                print(f"❌ Price fetch failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Price fetch error: {e}")
            return None
    
    def place_order(self, 
                    epic: str, 
                    direction: str, 
                    size: float, 
                    order_type: str = "MARKET",
                    limit: Optional[float] = None,
                    stop: Optional[float] = None,
                    currency_code: str = "USD") -> Optional[Dict[str, Any]]:
        """
        Place a trade order
        
        epic: Instrument epic
        direction: "BUY" or "SELL"
        size: Trade size (in units)
        order_type: "MARKET" or "LIMIT"
        limit: Limit price (for LIMIT orders)
        stop: Stop loss price
        """
        try:
            if not self.authenticated:
                if not self.login():
                    return None
            
            payload = {
                "epic": epic,
                "expiry": "DFB",  # Daily funded bet (no expiry)
                "direction": direction,
                "orderType": order_type,
                "size": size,
                "level": limit if order_type == "LIMIT" else None,
                "currencyCode": currency_code,
                "timeInForce": "EXECUTE_AND_ELIMINATE"
            }
            
            # Add stop loss if provided
            if stop:
                payload["stopLevel"] = stop
            
            headers = self.session.headers.copy()
            headers["VERSION"] = "1"
            
            response = self.session.post(
                f"{self.base_url}/v1/positions/otc",
                json=payload,
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                print(f"✅ Order placed: {direction} {size} {epic} @ {data.get('dealId', 'N/A')}")
                return {
                    "success": True,
                    "deal_id": data.get("dealId", ""),
                    "reason": data.get("reason", ""),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                print(f"❌ Order failed: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code
                }
                
        except Exception as e:
            print(f"❌ Order error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def close_position(self, deal_id: str, epic: str, direction: str, size: float) -> Optional[Dict[str, Any]]:
        """Close an existing position"""
        try:
            if not self.authenticated:
                if not self.login():
                    return None
            
            # Reverse direction to close
            close_direction = "SELL" if direction == "BUY" else "BUY"
            
            payload = {
                "dealId": deal_id,
                "epic": epic,
                "expiry": "DFB",
                "direction": close_direction,
                "orderType": "MARKET",
                "size": size,
                "timeInForce": "EXECUTE_AND_ELIMINATE"
            }
            
            headers = self.session.headers.copy()
            headers["VERSION"] = "1"
            
            response = self.session.delete(
                f"{self.base_url}/v1/positions/otc",
                json=payload,
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                print(f"✅ Position closed: {deal_id}")
                return {
                    "success": True,
                    "deal_id": data.get("dealId", ""),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                print(f"❌ Close failed: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": response.text
                }
                
        except Exception as e:
            print(f"❌ Close error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """Get account balance and equity"""
        try:
            if not self.authenticated:
                if not self.login():
                    return None
            
            headers = self.session.headers.copy()
            headers["VERSION"] = "1"
            
            response = self.session.get(
                f"{self.base_url}/v1/accounts/{self.account_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                account_info = data.get("account", {})
                return {
                    "balance": account_info.get("balance", 0),
                    "deposit": account_info.get("deposit", 0),
                    "available": account_info.get("available", 0),
                    "equity": account_info.get("equity", 0),
                    "pnl": account_info.get("pnl", 0),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                print(f"❌ Balance fetch failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Balance fetch error: {e}")
            return None
