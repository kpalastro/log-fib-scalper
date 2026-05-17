"""
═══════════════════════════════════════════════════════════════
GATE.IO API CLIENT
═══════════════════════════════════════════════════════════════

Handles authentication, real-time price streaming, and order execution.
Supports spot and futures trading on Gate.io exchange.
"""

import requests
import hmac
import hashlib
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

class GateIOClient:
    def __init__(self, config: Dict[str, str]):
        """
        Initialize Gate.io API Client
        
        config: {
            "api_key": "YOUR_API_KEY",
            "api_secret": "YOUR_API_SECRET",
            "demo": False  # Gate.io doesn't have demo, use small positions for testing
        }
        """
        self.config = config
        self.api_key = config["api_key"]
        self.api_secret = config["api_secret"]
        self.base_url = "https://api.gateio.ws/api/v4"
        self.session = requests.Session()
        self.authenticated = False
        
    def _generate_signature(self, method: str, url: str, body: str = "") -> Dict[str, str]:
        """Generate Gate.io API signature"""
        t = str(int(time.time()))
        m = hashlib.sha512()
        m.update(body.encode("utf-8"))
        hashed_body = m.hexdigest()
        
        s = f"{method}\n{url}\n{hashed_body}\n{t}"
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            s.encode("utf-8"),
            hashlib.sha512
        ).hexdigest()
        
        return {
            "KEY": self.api_key,
            "SIGNATURE": signature,
            "Timestamp": t
        }
    
    def _request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Optional[Any]:
        """Make authenticated API request"""
        try:
            url = f"{self.base_url}{endpoint}"
            body = json.dumps(data) if data else ""
            
            headers = self._generate_signature(method, endpoint, body)
            headers["Content-Type"] = "application/json"
            
            if method == "GET":
                response = self.session.get(url, params=params, headers=headers)
            elif method == "POST":
                response = self.session.post(url, json=data, headers=headers)
            elif method == "DELETE":
                response = self.session.delete(url, json=data, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code in [200, 201]:
                self.authenticated = True
                return response.json()
            else:
                print(f"❌ Gate.io API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Gate.io request error: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            result = self._request("GET", "/spot/accounts")
            if result:
                print(f"✅ Gate.io connection successful")
                return True
            return False
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False
    
    def get_ticker(self, currency_pair: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time ticker for a trading pair
        
        currency_pair: e.g., "BTC_USDT", "ETH_USDT", "XRP_USDT"
        """
        try:
            result = self._request("GET", f"/spot/tickers", params={"currency_pair": currency_pair})
            
            if result and isinstance(result, list) and len(result) > 0:
                ticker = result[0]
                return {
                    "currency_pair": currency_pair,
                    "last": float(ticker.get("last", 0)),
                    "bid": float(ticker.get("bid", 0)),
                    "ask": float(ticker.get("ask", 0)),
                    "high_24h": float(ticker.get("high_24h", 0)),
                    "low_24h": float(ticker.get("low_24h", 0)),
                    "volume_24h": float(ticker.get("volume_24h", 0)),
                    "change_24h": float(ticker.get("change_24h", 0)),
                    "timestamp": datetime.now().isoformat()
                }
            return None
            
        except Exception as e:
            print(f"❌ Ticker fetch error: {e}")
            return None
    
    def get_candles(self, currency_pair: str, interval: str = "5m", limit: int = 100) -> Optional[List[Dict]]:
        """
        Get historical candlestick data
        
        currency_pair: e.g., "BTC_USDT"
        interval: "1m", "5m", "15m", "1h", "4h", "1d"
        limit: Number of candles (max 300)
        """
        try:
            result = self._request(
                "GET",
                f"/spot/candlesticks",
                params={
                    "currency_pair": currency_pair,
                    "interval": interval,
                    "limit": limit
                }
            )
            
            if result and isinstance(result, list):
                candles = []
                for c in result:
                    candles.append({
                        "time": datetime.fromtimestamp(int(c[0])).isoformat(),
                        "timestamp": int(c[0]),
                        "open": float(c[1]),
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4]),
                        "volume": float(c[5])
                    })
                return candles
            return None
            
        except Exception as e:
            print(f"❌ Candle fetch error: {e}")
            return None
    
    def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """Get account balance"""
        try:
            result = self._request("GET", "/spot/accounts")
            
            if result and isinstance(result, list):
                balances = {}
                total_usdt = 0
                
                for acc in result:
                    currency = acc.get("currency", "")
                    available = float(acc.get("available", 0))
                    locked = float(acc.get("locked", 0))
                    total = available + locked
                    
                    if total > 0:
                        balances[currency] = {
                            "available": available,
                            "locked": locked,
                            "total": total
                        }
                        if currency == "USDT":
                            total_usdt = total
                
                return {
                    "balances": balances,
                    "total_usdt": total_usdt,
                    "timestamp": datetime.now().isoformat()
                }
            return None
            
        except Exception as e:
            print(f"❌ Balance fetch error: {e}")
            return None
    
    def place_order(self,
                    currency_pair: str,
                    side: str,
                    amount: float,
                    price: float = None,
                    order_type: str = "market") -> Optional[Dict[str, Any]]:
        """
        Place a trade order
        
        currency_pair: e.g., "BTC_USDT"
        side: "buy" or "sell"
        amount: Amount of base currency (e.g., BTC amount)
        price: Limit price (optional for market orders)
        order_type: "market" or "limit"
        """
        try:
            data = {
                "currency_pair": currency_pair,
                "side": side,
                "amount": str(amount),
                "type": order_type
            }
            
            if price and order_type == "limit":
                data["price"] = str(price)
            
            result = self._request("POST", "/spot/orders", data=data)
            
            if result:
                print(f"✅ Order placed: {side.upper()} {amount} {currency_pair} @ {result.get('price', 'MARKET')}")
                return {
                    "success": True,
                    "order_id": result.get("id", ""),
                    "price": result.get("price", 0),
                    "amount": result.get("amount", 0),
                    "side": result.get("side", ""),
                    "status": result.get("status", ""),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": "Order failed"
                }
                
        except Exception as e:
            print(f"❌ Order error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def cancel_order(self, currency_pair: str, order_id: str) -> Optional[Dict[str, Any]]:
        """Cancel an order"""
        try:
            result = self._request("DELETE", f"/spot/orders/{order_id}", params={"currency_pair": currency_pair})
            
            if result:
                print(f"✅ Order cancelled: {order_id}")
                return {
                    "success": True,
                    "order_id": order_id,
                    "timestamp": datetime.now().isoformat()
                }
            return {
                "success": False,
                "error": "Cancel failed"
            }
            
        except Exception as e:
            print(f"❌ Cancel error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_open_orders(self, currency_pair: str = None) -> Optional[List[Dict]]:
        """Get open orders"""
        try:
            params = {"status": "open"}
            if currency_pair:
                params["currency_pair"] = currency_pair
            
            result = self._request("GET", "/spot/orders", params=params)
            
            if result and isinstance(result, list):
                orders = []
                for o in result:
                    orders.append({
                        "order_id": o.get("id", ""),
                        "currency_pair": o.get("currency_pair", ""),
                        "side": o.get("side", ""),
                        "price": float(o.get("price", 0)),
                        "amount": float(o.get("amount", 0)),
                        "filled": float(o.get("filled_total", 0)),
                        "status": o.get("status", ""),
                        "created_at": o.get("create_time", 0)
                    })
                return orders
            return []
            
        except Exception as e:
            print(f"❌ Open orders fetch error: {e}")
            return []
    
    def get_my_trades(self, currency_pair: str, limit: int = 50) -> Optional[List[Dict]]:
        """Get recent trades"""
        try:
            result = self._request(
                "GET",
                "/spot/my_trades",
                params={
                    "currency_pair": currency_pair,
                    "limit": limit
                }
            )
            
            if result and isinstance(result, list):
                trades = []
                for t in result:
                    trades.append({
                        "trade_id": t.get("id", ""),
                        "order_id": t.get("order_id", ""),
                        "currency_pair": t.get("currency_pair", ""),
                        "side": t.get("side", ""),
                        "price": float(t.get("price", 0)),
                        "amount": float(t.get("amount", 0)),
                        "fee": float(t.get("fee", 0)),
                        "fee_currency": t.get("fee_currency", ""),
                        "timestamp": datetime.fromtimestamp(t.get("create_time", 0)).isoformat()
                    })
                return trades
            return []
            
        except Exception as e:
            print(f"❌ Trades fetch error: {e}")
            return []
