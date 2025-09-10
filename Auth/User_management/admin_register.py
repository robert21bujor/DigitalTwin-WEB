#!/usr/bin/env python3
"""
Admin User Registration Script
Run this script to register new users in the platform
"""

import sys
import os
from pathlib import Path
import hashlib
import secrets
from typing import Optional, Dict, Any
from supabase import create_client, Client
import logging
from datetime import datetime
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from Auth.User_management.role_constants import (
    get_all_roles, 
    get_all_admin_rights, 
    get_role_description, 
    get_admin_description,
    validate_role,
    validate_admin_rights
)

logger = logging.getLogger(__name__)


class UserRegistrationService:
    """Service for registering new platform users"""
    
    def __init__(self):
        self.supabase_client = None
        self._init_supabase()
    
    def _init_supabase(self):
        """Initialize Supabase client"""
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Use service role for admin operations
            
            if supabase_url and supabase_key:
                self.supabase_client = create_client(supabase_url, supabase_key)
                logger.info("✅ User registration service connected to Supabase")
            else:
                logger.error("❌ Missing Supabase credentials for user registration")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase for user registration: {e}")
    
    def create_user_account(self, 
                        email: str, 
                        password: str, 
                        username: str, 
                        role: str,
                        admin_rights: str = 'none') -> Dict[str, Any]:
        """
        Create a new user account using existing user_profiles table
        
        Args:
            email: Work email (e.g., "user.name@company.com")
            password: Plain text password (will be hashed)
            username: Username (will be email prefix like "user.name")
            role: Company role/position (e.g., 'cmo', 'product_manager')
            admin_rights: Admin privileges level ('none', 'admin', 'super_admin', 'system_admin')
            
        Returns:
            Dict with success status and user info
        """
        try:
            if not self.supabase_client:
                return {"success": False, "error": "Supabase not connected"}
            
            # Validate email format
            if '@' not in email:
                return {"success": False, "error": "Invalid email format"}
            
            # Use email prefix as username if not provided
            if not username:
                username = email.split('@')[0]
            
            # Validate username format (alphanumeric, dots, hyphens only)
            if not username.replace('.', '').replace('-', '').replace('_', '').isalnum():
                return {"success": False, "error": "Invalid username format"}
            
            # Validate role using centralized constants
            if not validate_role(role):
                valid_roles = get_all_roles()
                return {"success": False, "error": f"Invalid role. Must be one of: {', '.join(valid_roles)}"}
            
            # Check if user already exists
            existing_username = self.supabase_client.table('user_profiles').select('username, auth_user_id').eq('username', username).execute()
            if existing_username.data:
                return {"success": False, "error": f"Username {username} already exists. Use delete_user() first if you want to recreate."}
            
            existing_email = self.supabase_client.table('user_profiles').select('email, auth_user_id').eq('email', email).execute()
            if existing_email.data:
                return {"success": False, "error": f"Email {email} already registered. Use delete_user() first if you want to recreate."}
            
            # 🔐 CREATE SUPABASE AUTH USER FOR ALL USERS (including admins)
            auth_user = None
            try:
                # Create user in Supabase Auth - this is now required for ALL users
                # Generate a temporary password for first-time setup
                temp_password = f"TempPass_{username}_{hash(email) % 10000:04d}!"
                
                # ONLY username "admin" gets auto-confirm (no password reset)
                # ALL other users (including system_admin, super_admin) require email confirmation and password reset
                auto_confirm = username == 'admin'
                
                auth_response = self.supabase_client.auth.admin.create_user({
                    "email": email,
                    "password": password,  # Use the actual password provided
                    "email_confirm": auto_confirm,  # Auto-confirm for admin accounts
                    "user_metadata": {
                        "username": username,
                        "role": role,
                        "full_name": email.split('@')[0].replace('.', ' ').title(),
                        "created_via": "admin_registration",
                        "requires_password_reset": not auto_confirm,  # Only username "admin" doesn't need to reset
                        "temp_password_generated": not auto_confirm,  # Only username "admin" doesn't get temp password
                        "admin_username_exception": username == 'admin'  # Track if admin username exception was applied
                    }
                })
                
                if auth_response.user:
                    auth_user = auth_response.user
                    logger.info(f"✅ Supabase Auth user created: {email}")
                else:
                    logger.error(f"❌ Supabase Auth user creation failed for: {email}")
                    return {"success": False, "error": "Failed to create authentication user"}
                    
            except Exception as e:
                logger.error(f"❌ Supabase Auth error: {e}")
                return {"success": False, "error": f"Authentication creation failed: {str(e)}"}
            
            # Create user record in user_profiles table
            user_data = {
                'auth_user_id': auth_user.id,  # Link to Supabase auth user
                'email': email,
                'username': username,
                'role': role,
                'admin_rights': admin_rights,  # New admin rights field
                'is_active': True,
                'metadata': {
                    'created_via': 'admin_registration',
                    'uses_supabase_auth': True,  # All users use Supabase Auth
                    'created_by_admin': True,
                    'dual_role_system': True,  # Indicates v2 system with separate admin_rights
                    'temp_password': temp_password if not auto_confirm else None,  # Only for employees
                    'requires_password_reset': not auto_confirm,  # Only username "admin" doesn't need to reset
                    'email_confirmation_sent': not auto_confirm,  # Only employees need confirmation
                    'auto_confirmed': auto_confirm,  # Track if account was auto-confirmed
                    'admin_username_exception': username == 'admin'  # Track if admin username exception was applied
                }
            }
            
            result = self.supabase_client.table('user_profiles').insert(user_data).execute()
            
            if result.data:
                user_record = result.data[0]
                logger.info(f"✅ User account created: {username} ({email}) with role {role}")
                
                # Create corresponding Google Drive folder structure if needed
                self._create_user_drive_structure(username)
                
                # Different messages based on username "admin" exception
                if auto_confirm:  # Only username "admin" gets auto_confirm
                    message = f"Admin account created for {username}. Account is ready for immediate use (username exception applied)."
                    email_sent = False  # No confirmation needed for username "admin"
                else:
                    message = f"Account created for {username}. Confirmation email sent to {email}. User must verify email and set their own password."
                    email_sent = True  # Confirmation email will be sent by Supabase
                
                return {
                    "success": True,
                    "user_id": user_record['id'],  # UUID from database (id column)
                    "username": username,  # Email prefix for folder matching
                    "email": email,
                    "role": role,
                    "admin_rights": admin_rights,
                    "expected_folder": f"DigitalTwin_Brain/Users/{username}",
                    "message": message,
                    "email_sent": email_sent,
                    "auth_user_id": auth_user.id if auth_user else None,
                    "temp_password": temp_password if not auto_confirm else None,  # Only for employees
                    "requires_password_reset": not auto_confirm,
                    "auto_confirmed": auto_confirm
                }
            else:
                return {"success": False, "error": "Failed to create user record"}
                
        except Exception as e:
            logger.error(f"❌ Error creating user account: {e}")
            return {"success": False, "error": str(e)}
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(32)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return salt + password_hash.hex()
    
    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash"""
        try:
            salt = stored_hash[:64]
            stored_password = stored_hash[64:]
            password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return password_hash.hex() == stored_password
        except:
            return False
    
    def _create_user_drive_structure(self, username: str):
        """Create user folder structure in Google Drive (placeholder)"""
        # This would integrate with Google Drive API to create:
        # DigitalTwin_Brain/Users/{username}/
        # DigitalTwin_Brain/Users/{username}/Emails/Internal/
        # DigitalTwin_Brain/Users/{username}/Emails/Business/
        # DigitalTwin_Brain/Users/{username}/Emails/Clients/
        # etc.
        logger.info(f"📁 TODO: Create Google Drive structure for user: {username}")
    
    def link_gmail_tokens(self, username: str, gmail_tokens_id: str) -> Dict[str, Any]:
        """Link Gmail tokens to a platform user account"""
        try:
            if not self.supabase_client:
                return {"success": False, "error": "Supabase not connected"}
            
            # Verify user exists
            user = self.supabase_client.table('user_profiles').select('username').eq('username', username).execute()
            if not user.data:
                return {"success": False, "error": f"User {username} not found"}
            
            # Update gmail_tokens record
            result = self.supabase_client.table('gmail_tokens').update({
                'platform_user_id': username  # Use username as platform_user_id
            }).eq('id', gmail_tokens_id).execute()
            
            if result.data:
                logger.info(f"✅ Gmail tokens linked to user: {username}")
                return {"success": True, "message": f"Gmail tokens linked to {username}"}
            else:
                return {"success": False, "error": "Failed to link Gmail tokens"}
                
        except Exception as e:
            logger.error(f"❌ Error linking Gmail tokens: {e}")
            return {"success": False, "error": str(e)}
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email for login"""
        try:
            if not self.supabase_client:
                return None
            
            result = self.supabase_client.table('user_profiles').select('*').eq('email', email).execute()
            if result.data:
                user = result.data[0]
                # Extract password hash from metadata
                if user.get('metadata') and 'password_hash' in user['metadata']:
                    user['password_hash'] = user['metadata']['password_hash']
                return user
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user by email: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        try:
            if not self.supabase_client:
                return None
            
            result = self.supabase_client.table('user_profiles').select('*').eq('username', username).execute()
            if result.data:
                user = result.data[0]
                # Extract password hash from metadata
                if user.get('metadata') and 'password_hash' in user['metadata']:
                    user['password_hash'] = user['metadata']['password_hash']
                return user
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user by username: {e}")
            return None
    
    def delete_user(self, email: str) -> Dict[str, Any]:
        """Delete a user account (both auth and profile)"""
        try:
            if not self.supabase_client:
                return {"success": False, "error": "Supabase not connected"}
            
            # Get user profile
            result = self.supabase_client.table('user_profiles').select('auth_user_id, username').eq('email', email).execute()
            
            if not result.data:
                return {"success": False, "error": f"User {email} not found"}
            
            user_data = result.data[0]
            auth_user_id = user_data.get('auth_user_id')
            username = user_data.get('username')
            
            auth_deletion_success = False
            auth_deletion_error = None
            
            # Delete from Supabase Auth FIRST (if auth_user_id exists)
            if auth_user_id:
                try:
                    print(f"🔄 Attempting to delete auth user: {auth_user_id}")
                    
                    # Use admin.delete_user() method
                    auth_response = self.supabase_client.auth.admin.delete_user(auth_user_id)
                    
                    print(f"✅ Auth deletion response: {auth_response}")
                    logger.info(f"✅ Deleted auth user: {auth_user_id}")
                    auth_deletion_success = True
                    
                except Exception as auth_error:
                    auth_deletion_error = str(auth_error)
                    print(f"❌ Auth deletion failed: {auth_error}")
                    logger.error(f"Failed to delete auth user {auth_user_id}: {auth_error}")
                    
                    # Try alternative method - get user first then delete
                    try:
                        print(f"🔄 Trying alternative auth deletion method...")
                        
                        # First try to get the user to verify it exists
                        user_info = self.supabase_client.auth.admin.get_user_by_id(auth_user_id)
                        print(f"📋 Found auth user: {user_info.user.email if user_info.user else 'None'}")
                        
                        # Try delete again
                        delete_response = self.supabase_client.auth.admin.delete_user(auth_user_id)
                        print(f"✅ Alternative auth deletion successful: {delete_response}")
                        auth_deletion_success = True
                        auth_deletion_error = None
                        
                    except Exception as alt_error:
                        print(f"❌ Alternative auth deletion also failed: {alt_error}")
                        auth_deletion_error = f"Primary: {auth_error}, Alternative: {alt_error}"
            else:
                print("⚠️ No auth_user_id found in profile")
            
            # Delete from user_profiles table
            print(f"🔄 Deleting from user_profiles table...")
            delete_result = self.supabase_client.table('user_profiles').delete().eq('email', email).execute()
            
            if delete_result.data:
                print(f"✅ User profile deleted successfully")
            else:
                print(f"⚠️ User profile deletion result: {delete_result}")
            
            logger.info(f"✅ User profile deleted: {email} ({username})")
            
            # Prepare response with detailed info
            message_parts = [f"User {email} ({username}) profile deleted successfully"]
            
            if auth_user_id:
                if auth_deletion_success:
                    message_parts.append("✅ Supabase Auth user also deleted")
                else:
                    message_parts.append(f"❌ Supabase Auth deletion failed: {auth_deletion_error}")
            else:
                message_parts.append("⚠️ No linked Supabase Auth user found")
            
            return {
                "success": True,
                "message": " | ".join(message_parts),
                "deleted_auth_user": auth_deletion_success,
                "auth_deletion_error": auth_deletion_error if not auth_deletion_success else None,
                "auth_user_id": auth_user_id
            }
            
        except Exception as e:
            logger.error(f"Delete user error: {e}")
            return {"success": False, "error": f"Delete error: {str(e)}"}

def register_user():
    """Interactive user registration"""
    print("🏢 RepsMate Platform - User Registration")
    print("=" * 50)
    
    # Show available roles and admin rights from centralized constants
    print("\n📋 Available Company Roles:")
    company_roles = get_all_roles()
    
    for i, role in enumerate(company_roles, 1):
        description = get_role_description(role)
        print(f"   {i:2d}. {role:<30} - {description}")
    
    print(f"\n🔐 Available Admin Rights:")
    admin_rights_options = get_all_admin_rights()
    for i, rights in enumerate(admin_rights_options, 1):
        description = get_admin_description(rights)
        print(f"   {i}. {rights:<15} - {description}")
    
    print(f"\n💡 Note: Users can have both a company role AND admin rights.")
    print(f"   Example: role='cmo' + admin_rights='super_admin'")
    
    # Get user input
    email = input("\nWork Email: ").strip()
    password = input("Password: ").strip()
    role = input("Company Role (from list above): ").strip()
    admin_rights = input("Admin Rights (none/admin/super_admin/system_admin) [default: none]: ").strip() or 'none'
    
    if not all([email, password, role]):
        print("❌ All fields are required!")
        return
    
    # Validate email format
    if '@' not in email:
        print("❌ Invalid email format!")
        return
    
    # Validate role using centralized validation
    if not validate_role(role):
        print(f"❌ Invalid role! Must be one of: {', '.join(company_roles)}")
        return
    
    # Validate admin rights using centralized validation
    if not validate_admin_rights(admin_rights):
        print(f"❌ Invalid admin rights! Must be one of: {', '.join(admin_rights_options)}")
        return
    
    username = email.split('@')[0]
    print(f"\n📋 Registration Summary:")
    print(f"   Username: {username}")
    print(f"   Email: {email}")
    print(f"   Company Role: {role}")
    print(f"   Admin Rights: {admin_rights}")
    print(f"   Expected Folder: DigitalTwin_Brain/Users/{username}")
    
    confirm = input("\n✅ Create this account? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Registration cancelled.")
        return
    
    # Create user
    result = user_registration_service.create_user_account(
        email=email,
        password=password,
        username=username,
        role=role,
        admin_rights=admin_rights
    )
    
    if result['success']:
        print(f"\n🎉 SUCCESS! User {result['username']} created successfully!")
        print(f"   UUID: {result['user_id']}")
        print(f"   Username: {result['username']}")
        print(f"   Email: {result['email']}")
        print(f"   Role: {result['role']}")
        
        if result.get('email_sent', False):
                    print(f"\n📧 EMPLOYEE ONBOARDING:")
        print(f"   ✅ Confirmation email sent to: {result['email']}")
        print(f"   🔑 Temporary password (for emergency access): {result.get('temp_password', 'N/A')}")
        print(f"   📝 Employee MUST verify email and set their own password")
        print(f"   🔐 Cannot login until email is confirmed and password is reset")
        print(f"   ⚠️ Temporary password should only be used for initial setup if needed")
        
        print(f"\n📁 SYSTEM INTEGRATION:")
        print(f"   🔗 When they connect Gmail, tokens will auto-link to: {result['username']}")
        print(f"   📂 Email search will target: {result['expected_folder']}")
    else:
        print(f"\n❌ FAILED: {result['error']}")

def delete_user():
    """Delete a user account"""
    print("🗑️ RepsMate Platform - Delete User")
    print("=" * 50)
    
    email = input("\nEmail to delete: ").strip()
    if not email:
        print("❌ Email is required!")
        return
    
    if '@' not in email:
        print("❌ Invalid email format!")
        return
    
    confirm = input(f"\n⚠️ Are you sure you want to delete {email}? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Deletion cancelled.")
        return
    
    print(f"\n🔄 Deleting user {email}...")
    result = user_registration_service.delete_user(email)
    
    if result['success']:
        print(f"\n🎉 DELETION SUMMARY:")
        print(f"   📧 Email: {email}")
        print(f"   📝 Status: {result['message']}")
        
        if result.get('auth_user_id'):
            print(f"   🆔 Auth User ID: {result['auth_user_id']}")
            
        if result.get('deleted_auth_user'):
            print(f"   🔐 Supabase Auth: ✅ DELETED")
        elif result.get('auth_deletion_error'):
            print(f"   🔐 Supabase Auth: ❌ FAILED")
            print(f"      Error: {result['auth_deletion_error']}")
        else:
            print(f"   🔐 Supabase Auth: ⚠️ NO AUTH USER FOUND")
            
        print(f"   📋 User Profile: ✅ DELETED")
        
    else:
        print(f"\n❌ DELETION FAILED: {result['error']}")

def list_users():
    """List all registered users"""
    try:
        if not user_registration_service.supabase_client:
            print("❌ Database not connected")
            return
        
        result = user_registration_service.supabase_client.table('user_profiles').select('*').execute()
        
        if not result.data:
            print("📝 No users registered yet.")
            return
        
        print(f"\n👥 Registered Users ({len(result.data)}):")
        print("=" * 120)
        print(f"{'Status':<8} {'Username':<20} {'Email':<30} {'Company Role':<25} {'Admin Rights':<15}")
        print("=" * 120)
        
        for user in result.data:
            status = "🟢" if user.get('is_active') else "🔴"
            admin_rights = user.get('admin_rights', 'none')
            print(f"{status:<8} {user['username']:<20} {user['email']:<30} {user['role']:<25} {admin_rights:<15}")
            
    except Exception as e:
        print(f"❌ Error listing users: {e}")

def main():
    """Main menu"""
    while True:
        print("\n🏢 RepsMate Platform - Admin Tools")
        print("=" * 40)
        print("1. Register New User")
        print("2. List Users")
        print("3. Delete User")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            register_user()
        elif choice == '2':
            list_users()
        elif choice == '3':
            delete_user()
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please select 1-4.")

# Global instance
user_registration_service = UserRegistrationService()

if __name__ == "__main__":
    main()