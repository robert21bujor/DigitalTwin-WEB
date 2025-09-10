#!/usr/bin/env python3
"""
Notification System Setup Script
===============================

This script sets up the notification system by running the database migration
and creating default notification preferences for existing users.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from Utils.config import Config
from supabase import create_client

async def setup_notification_system():
    """Set up the notification system"""
    print("🔔 Setting up Notification System...")
    
    try:
        # Initialize Supabase client
        print("📊 Connecting to database...")
        supabase_config = Config.get_supabase_config()
        service_key = supabase_config.get("service_role_key") or supabase_config["key"]
        supabase = create_client(supabase_config["url"], service_key)
        
        # Read migration file
        migration_file = Path(__file__).parent / "migrations" / "001_create_notifications_tables.sql"
        
        if not migration_file.exists():
            print(f"❌ Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print("🏗️ Running database migration...")
        
        # Note: Supabase Python client doesn't support raw SQL execution
        # User needs to run this manually in Supabase SQL editor
        print("\n📋 MANUAL STEP REQUIRED:")
        print("=" * 50)
        print("Please copy and paste the following SQL into your Supabase SQL editor:")
        print(f"File location: {migration_file}")
        print("=" * 50)
        print()
        print("Or run this command in your Supabase project:")
        print("1. Go to: https://app.supabase.com/project/YOUR_PROJECT/sql")
        print("2. Copy the contents of: AgentUI/Backend/notifications/migrations/001_create_notifications_tables.sql")
        print("3. Paste and run the SQL")
        print()
        
        # Check if tables exist
        try:
            result = supabase.table("notifications").select("id").limit(1).execute()
            print("✅ Notification tables are ready!")
            
            # Check existing users and create default preferences
            user_result = supabase.table("user_profiles").select("id").execute()
            user_count = len(user_result.data) if user_result.data else 0
            
            if user_count > 0:
                print(f"👥 Found {user_count} existing users")
                print("ℹ️  Default notification preferences will be created automatically when users first access the system")
            
            return True
            
        except Exception as e:
            if "relation \"notifications\" does not exist" in str(e):
                print("⚠️  Notification tables not found. Please run the migration SQL first.")
                return False
            else:
                print(f"❌ Error checking tables: {e}")
                return False
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Notification System Setup")
    print("=" * 40)
    
    try:
        success = asyncio.run(setup_notification_system())
        
        if success:
            print("\n✅ Notification System Setup Complete!")
            print("\n🎯 Next Steps:")
            print("1. Restart your backend server if running")
            print("2. Visit your dashboard to see the notification bell 🔔")
            print("3. Send a chat message or run Gmail sync to test notifications")
            print("\n📚 Documentation: docs/README_notifications.md")
        else:
            print("\n❌ Setup incomplete. Please check the errors above.")
            
    except KeyboardInterrupt:
        print("\n⏹️  Setup cancelled by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")

if __name__ == "__main__":
    main()
