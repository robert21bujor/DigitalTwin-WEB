#!/usr/bin/env python3
"""
ClickUp Environment Setup Helper
Run this script to set up ClickUp OAuth environment variables
"""

import os
import secrets
import base64

def generate_encryption_key():
    """Generate a secure encryption key"""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

def main():
    print("🔧 ClickUp OAuth Environment Setup")
    print("=" * 50)
    
    print("\n📝 You need to create a ClickUp OAuth app first:")
    print("1. Go to ClickUp → Settings → Apps/Integrations → ClickUp API")
    print("2. Click 'Create App'")
    print("3. Set Redirect URL to: http://localhost:3001/auth/clickup/callback")
    print("4. Copy the Client ID and Client Secret")
    
    print("\n🔑 Enter your ClickUp OAuth credentials:")
    
    client_id = input("ClickUp Client ID: ").strip()
    if not client_id:
        print("❌ Client ID is required!")
        return
    
    client_secret = input("ClickUp Client Secret: ").strip()
    if not client_secret:
        print("❌ Client Secret is required!")
        return
    
    # Generate encryption key
    encryption_key = generate_encryption_key()
    print(f"\n🔐 Generated encryption key: {encryption_key}")
    
    # Create environment commands
    print("\n💻 Run these commands to set your environment variables:")
    print("=" * 50)
    
    if os.name == 'nt':  # Windows
        print("# Windows (PowerShell)")
        print(f'$env:CLICKUP_CLIENT_ID="{client_id}"')
        print(f'$env:CLICKUP_CLIENT_SECRET="{client_secret}"')
        print(f'$env:CLICKUP_REDIRECT_URI="http://localhost:3001/auth/clickup/callback"')
        print(f'$env:CLICKUP_ENCRYPTION_KEY="{encryption_key}"')
    else:  # Unix/Linux/Mac
        print("# Unix/Linux/Mac")
        print(f'export CLICKUP_CLIENT_ID="{client_id}"')
        print(f'export CLICKUP_CLIENT_SECRET="{client_secret}"')
        print(f'export CLICKUP_REDIRECT_URI="http://localhost:3001/auth/clickup/callback"')
        print(f'export CLICKUP_ENCRYPTION_KEY="{encryption_key}"')
    
    print("\n📋 Or create a .env file with:")
    print("-" * 30)
    print(f"CLICKUP_CLIENT_ID={client_id}")
    print(f"CLICKUP_CLIENT_SECRET={client_secret}")
    print(f"CLICKUP_REDIRECT_URI=http://localhost:3001/auth/clickup/callback")
    print(f"CLICKUP_ENCRYPTION_KEY={encryption_key}")
    
    print("\n✅ After setting environment variables, restart your application!")

if __name__ == "__main__":
    main()
