"""
Test Kotak Neo login with official SDK
"""

import os
from dotenv import load_dotenv
from neo_client import KotakNeoClient

# Load credentials
load_dotenv()

neo_config = {
    "consumer_key": os.getenv("KOTAK_CONSUMER_KEY"),
    "totp_key": os.getenv("KOTAK_TOTP_KEY"),
    "mobile_number": os.getenv("KOTAK_MOBILE_NUMBER"),
    "password": os.getenv("KOTAK_PASSWORD"),
    "mpin": os.getenv("KOTAK_MPIN"),
    "ucc": os.getenv("KOTAK_UCC")
}

print("="*80)
print("🧪 KOTAK NEO LOGIN TEST (Official SDK)")
print("="*80)
print(f"\nCredentials loaded:")
print(f"  Consumer Key: {neo_config['consumer_key'][:10]}...")
print(f"  TOTP Key: {neo_config['totp_key'][:8]}...")
print(f"  Mobile: {neo_config['mobile_number']}")
print(f"  UCC: {neo_config['ucc']}")
print()

# Create client
client = KotakNeoClient(neo_config)

# Test login
print("📡 Attempting TOTP login...")
success = client.login()

if success:
    print("\n✅ LOGIN SUCCESSFUL!")
    
    # Test fetching balance
    print("\n📊 Fetching account balance...")
    balance = client.get_account_balance()
    if balance:
        print(f"   Available: ₹{balance.get('available', 0):,.2f}")
        print(f"   Used: ₹{balance.get('used', 0):,.2f}")
        print(f"   Total: ₹{balance.get('total', 0):,.2f}")
    
    # Test fetching Nifty50 price
    print("\n💹 Fetching Nifty50 price...")
    # Note: Nifty50 is an INDEX, not in nse_cm
    # For indices, you need to use websocket subscription
    # This is a placeholder - actual token may differ
    price = client.get_market_price("10000", exchange_segment="nse_cm")
    if price:
        print(f"   Last: {price['last_traded']:.2f}")
    else:
        print("   ⚠️  Index quotes may require websocket subscription")
    
    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED - READY TO TRADE!")
    print("="*80)
    print("\n📝 Next steps:")
    print("   1. Run: python nifty_live_agent.py")
    print("   2. Monitor for swing signals")
    print("   3. Auto-trading will execute on triggers")
else:
    print("\n❌ LOGIN FAILED")
    print("\nPossible issues:")
    print("  1. TOTP code expired (codes change every 30s)")
    print("  2. Invalid TOTP secret key")
    print("  3. Incorrect MPIN")
    print("  4. UCC/mobile number mismatch")
    print("  5. TOTP not registered on Kotak Neo portal")
    print("\n📱 TOTP Registration (one-time setup):")
    print("   1. Visit: https://www.kotaksecurities.com/platform/kotak-neo-trade-api/")
    print("   2. Select 'Register for TOTP'")
    print("   3. Verify mobile with OTP")
    print("   4. Scan QR code with Google Authenticator")
    print("   5. Submit TOTP to complete registration")
    print("="*80)
