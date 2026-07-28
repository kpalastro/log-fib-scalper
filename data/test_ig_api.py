"""
Test IG Markets API connection
"""

import requests
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path('/home/palbot/Projects/log-fib-scalper/live_trading/.env'))

IG_API_KEY = os.getenv('IG_API_KEY')
IG_USERNAME = os.getenv('IG_USERNAME')
IG_PASSWORD = os.getenv('IG_PASSWORD')

print("=" * 70)
print("IG MARKETS API TEST")
print("=" * 70)
print(f"API Key: {IG_API_KEY[:8]}...{IG_API_KEY[-8:]}")
print(f"Username: {IG_USERNAME}")
print(f"Password: {IG_PASSWORD[:3]}...")

# Try authentication
BASE_URL = 'https://api.ig.com'

print(f"\n🔐 Attempting authentication...")
print(f"Endpoint: {BASE_URL}/v1/session")

headers = {
    'Content-Type': 'application/json; charset=utf-8',
    'Accept': 'application/json; charset=utf-8',
    'X-IG-API-KEY': IG_API_KEY,
    'VERSION': '2',
}

payload = {
    'identifier': IG_USERNAME,
    'password': IG_PASSWORD,
}

import json
print(f"\nPayload: {json.dumps(payload, indent=2)}")

session = requests.Session()
response = session.post(
    f'{BASE_URL}/v1/session',
    json=payload,
    headers=headers
)

print(f"\n📊 Response:")
print(f"Status Code: {response.status_code}")
print(f"Headers: {dict(response.headers)}")
print(f"Body: {response.text[:500]}")

if response.status_code == 200:
    print("\n✅ SUCCESS!")
    data = response.json()
    print(f"Security Token: {data.get('securityToken', '')[:20]}...")
    print(f"Account ID: {data.get('accountId', 'N/A')}")
else:
    print(f"\n❌ FAILED")
    print(f"Error: {response.status_code}")
    
    # Try with VERSION 1
    print(f"\n🔄 Trying with VERSION=1...")
    headers['VERSION'] = '1'
    response2 = session.post(
        f'{BASE_URL}/v1/session',
        json=payload,
        headers=headers
    )
    print(f"Status: {response2.status_code}")
    print(f"Body: {response2.text[:300]}")
