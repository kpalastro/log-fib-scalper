"""
IG Markets API has TWO different APIs:
1. REST API (older) - uses different auth
2. Stream API (newer) - uses bearer tokens

Let's try the correct REST API format
"""

import requests
import os
from dotenv import load_dotenv
from pathlib import Path
import base64

load_dotenv(Path('/home/palbot/Projects/log-fib-scalper/live_trading/.env'))

IG_API_KEY = os.getenv('IG_API_KEY')
IG_USERNAME = os.getenv('IG_USERNAME')
IG_PASSWORD = os.getenv('IG_PASSWORD')

print("=" * 70)
print("IG MARKETS API - CORRECT FORMAT TEST")
print("=" * 70)

# IG REST API v1 uses BASIC auth with API key as username, empty password
# OR uses X-IG-API-KEY header with JSON body

# Method 1: Basic Auth
print("\n📌 Method 1: Basic Auth (API key as username)")
BASE_URL = 'https://api.ig.com'

auth = (IG_API_KEY, '')
headers = {
    'Content-Type': 'application/json; charset=utf-8',
    'Accept': 'application/json; charset=utf-8',
    'VERSION': '1',
}

# Try to get account info
response = requests.get(
    f'{BASE_URL}/v1/accounts',
    auth=auth,
    headers=headers
)

print(f"GET /v1/accounts")
print(f"Status: {response.status_code}")
print(f"Body: {response.text[:300]}")

if response.status_code == 200:
    print("\n✅ Method 1 WORKS!")
    try:
        data = response.json()
        print(f"Accounts: {data}")
    except:
        print(f"Response: {response.text[:200]}")
else:
    print("\n❌ Method 1 failed")

# Method 2: Session-based with VERSION=1
print("\n" + "=" * 70)
print("\n📌 Method 2: Session POST with VERSION=1")

headers2 = {
    'Content-Type': 'application/json; charset=utf-8',
    'Accept': 'application/json; charset=utf-8',
    'X-IG-API-KEY': IG_API_KEY,
    'VERSION': '1',
}

payload = {
    'identifier': IG_USERNAME,
    'password': IG_PASSWORD,
}

response2 = requests.post(
    f'{BASE_URL}/v1/session',
    json=payload,
    headers=headers2
)

print(f"POST /v1/session")
print(f"Status: {response2.status_code}")
print(f"Content-Type: {response2.headers.get('Content-Type', 'N/A')}")

if 'application/json' in response2.headers.get('Content-Type', ''):
    try:
        data = response2.json()
        print(f"✅ JSON response!")
        print(f"Data: {data}")
    except Exception as e:
        print(f"❌ JSON parse error: {e}")
        print(f"Body: {response2.text[:300]}")
else:
    print(f"❌ Not JSON - got: {response2.headers.get('Content-Type')}")
    print(f"Body: {response2.text[:300]}")

# Method 3: Try demo API
print("\n" + "=" * 70)
print("\n📌 Method 3: Demo API endpoint")
DEMO_BASE = 'https://demo-api.ig.com'

response3 = requests.post(
    f'{DEMO_BASE}/v1/session',
    json=payload,
    headers=headers2
)

print(f"POST {DEMO_BASE}/v1/session")
print(f"Status: {response3.status_code}")
print(f"Content-Type: {response3.headers.get('Content-Type', 'N/A')}")
print(f"Body: {response3.text[:300]}")
