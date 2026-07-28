#!/usr/bin/env python3
"""
Zerodha Credentials Setup Script

Securely stores Zerodha login credentials for the MCP server.
Creates ~/.zerodha_credentials.json with restrictive permissions.

Usage:
  python setup-zerodha-creds.py
"""

import json
import os
import sys
from pathlib import Path

CREDENTIALS_FILE = Path.home() / ".zerodha_credentials.json"

def main():
    print("=" * 60)
    print("Zerodha Credentials Setup")
    print("=" * 60)
    print()
    print("Enter your Zerodha Kite login credentials:")
    print()
    print("⚠️  WARNING: These are stored in plaintext.")
    print("    Only use on a secure, private machine.")
    print()
    
    user_id = input("User ID (e.g., RD156567): ").strip()
    if not user_id:
        print("❌ User ID is required")
        sys.exit(1)
    
    password = input("Password: ").strip()
    if not password:
        print("❌ Password is required")
        sys.exit(1)
    
    twofa = input("2FA (PIN or TOTP): ").strip()
    if not twofa:
        print("❌ 2FA is required")
        sys.exit(1)
    
    creds = {
        "user_id": user_id,
        "password": password,
        "twofa": twofa
    }
    
    try:
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(creds, f, indent=2)
        
        # Set restrictive permissions (owner read/write only)
        os.chmod(CREDENTIALS_FILE, 0o600)
        
        print()
        print("✅ Credentials saved successfully!")
        print(f"   Location: {CREDENTIALS_FILE}")
        print(f"   Permissions: 600 (owner read/write only)")
        print()
        print("Next steps:")
        print("  1. Add to ~/.hermes/config.yaml:")
        print()
        print("     mcp_servers:")
        print("       zerodha-free:")
        print("         command: python")
        print("         args: [/home/palbot/Projects/log-fib-scalper/mcp/zerodha_free_mcp.py]")
        print("         timeout: 60")
        print()
        print("  2. Restart Hermes:")
        print("     hermes gateway restart")
        print()
        print("  3. Test with:")
        print("     Get Nifty LTP")
        print("     Search for BANKNIFTY instruments")
        print()
        
    except Exception as e:
        print(f"❌ Error saving credentials: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
