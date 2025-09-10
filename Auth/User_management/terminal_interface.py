"""
Terminal Interface for Supabase Authentication System
"""

import asyncio
import getpass
import logging
from typing import Optional, List, Dict, Any

from .auth_manager import AuthManager
from .access_control import AccessController, MemoryAccessController
from .user_models import User, UserRole, AgentType

logger = logging.getLogger(__name__)


class TerminalAuthInterface:
    """Terminal-based authentication interface"""
    
    def __init__(self, auth_manager: AuthManager):
        self.auth_manager = auth_manager
        self.access_controller = AccessController(auth_manager)
        self.memory_controller = MemoryAccessController(self.access_controller)
        self.running = False
    
    def display_welcome(self):
        """Display welcome message"""
        print("\n" + "="*60)
        print("🚀 ROLE-BASED MULTI-AGENT MARKETING SYSTEM")
        print("="*60)
        print("| 🔐 Secure Authentication: Supabase-powered")
        print("| 🤖 Agent-Based Architecture: CMO, Positioning, SEO, Content...")
        print("| 🧠 Memory Access Control: Private & Shared collections")
        print("| 🎯 Role-Based Access: Each user accesses only their assigned agents")
        print("="*60)
        print("\n🔑 AUTHENTICATION REQUIRED")
        print("   Please login or register to access the system")
    
    def display_auth_menu(self):
        """Display authentication menu"""
        print("\n" + "="*40)
        print("🔐 AUTHENTICATION MENU")
        print("="*40)
        print("1. 🔑 Login")
        print("2. 📝 Register New Account")
        print("3. 📋 View Available Roles")
        print("4. ❌ Exit")
        print("="*40)
    
    def display_available_roles(self):
        """Display available user roles"""
        print("\n" + "="*50)
        print("📋 AVAILABLE ROLES")
        print("="*50)
        
        print("\n🏢 EXECUTIVE ROLES:")
        print("   • CMO - Full system access, all agents & private memory")
        
        print("\n👨‍💼 MANAGER ROLES:")
        print("   • Product Manager - Product marketing oversight")
        print("   • Digital Manager - Digital marketing oversight")
        print("   • Content Manager - Content marketing oversight")
        
        print("\n🤖 AGENT ROLES:")
        print("   • Positioning Agent - Product positioning & value props")
        print("   • Persona Agent - Customer research & segmentation")
        print("   • GTM Agent - Go-to-market strategy")
        print("   • SEO Agent - Search engine optimization")
        print("   • Content Agent - Content creation & strategy")
        print("   • And many more specialized agents...")
        
        print("\n💡 ROLE FEATURES:")
        print("   • Each role has access only to their assigned agent")
        print("   • CMO has full access to all agents and private memory")
        print("   • Agents can access their private memory + shared collections")
        print("   • Memory access is strictly controlled by role")
        print("="*50)
    
    async def handle_login(self) -> Optional[User]:
        """Handle user login"""
        print("\n" + "="*30)
        print("🔑 USER LOGIN")
        print("="*30)
        
        try:
            email = input("📧 Email: ").strip()
            if not email:
                print("❌ Email is required")
                return None
            
            password = getpass.getpass("🔐 Password: ")
            if not password:
                print("❌ Password is required")
                return None
            
            print("\n🔄 Authenticating...")
            user = await self.auth_manager.login(email, password)
            
            if user:
                print(f"\n✅ LOGIN SUCCESSFUL!")
                print(f"   👤 Welcome, {user.username}")
                print(f"   🎭 Role: {user.role.value}")
                print(f"   🤖 Accessible Agents: {[a.value for a in user.get_accessible_agents()]}")
                print(f"   🧠 Memory Collections: {len(user.get_accessible_memory_collections())}")
                
                # Display user's access summary
                access_summary = self.access_controller.get_user_access_summary()
                if access_summary.get('is_cmo'):
                    print(f"   🔥 CMO Access: Full system control")
                elif access_summary.get('is_manager'):
                    print(f"   👨‍💼 Manager Access: Division oversight")
                else:
                    print(f"   🎯 Agent Access: Specialized role")
                
                return user
            else:
                print("❌ LOGIN FAILED")
                print("   Invalid email or password")
                return None
                
        except Exception as e:
            print(f"❌ LOGIN ERROR: {str(e)}")
            return None
    
    async def handle_registration(self) -> bool:
        """Handle user registration"""
        print("\n" + "="*40)
        print("📝 NEW USER REGISTRATION")
        print("="*40)
        
        try:
            # Get user details
            email = input("📧 Email: ").strip()
            if not email:
                print("❌ Email is required")
                return False
            
            username = input("👤 Username: ").strip()
            if not username:
                print("❌ Username is required")
                return False
            
            password = getpass.getpass("🔐 Password: ")
            if not password:
                print("❌ Password is required")
                return False
            
            confirm_password = getpass.getpass("🔐 Confirm Password: ")
            if password != confirm_password:
                print("❌ Passwords do not match")
                return False
            
            # Select role
            role = await self._select_role()
            if not role:
                print("❌ Role selection cancelled")
                return False
            
            # Register user
            print("\n🔄 Creating account...")
            success = await self.auth_manager.register_user(email, password, username, role)
            
            if success:
                print("✅ REGISTRATION SUCCESSFUL!")
                print(f"   👤 Username: {username}")
                print(f"   🎭 Role: {role.value}")
                print("   🔑 You can now login with your credentials")
                return True
            else:
                print("❌ REGISTRATION FAILED")
                print("   Please try again or contact support")
                return False
                
        except Exception as e:
            print(f"❌ REGISTRATION ERROR: {str(e)}")
            return False
    
    async def _select_role(self) -> Optional[UserRole]:
        """Select user role during registration"""
        print("\n🎭 SELECT YOUR ROLE:")
        print("="*30)
        
        # Group roles by category using centralized constants
        from .role_constants import get_roles_by_category
        
        # Get leadership and management roles
        leadership_role_names = get_roles_by_category('leadership')
        management_role_names = get_roles_by_category('management')
        marketing_role_names = get_roles_by_category('marketing')[:7]  # Limit to first 7 for display
        
        # Convert to UserRole enums
        executive_roles = []
        manager_roles = []
        agent_roles = []
        
        # Find matching UserRole enum members
        for role_name in leadership_role_names[:1]:  # Just CMO for now
            try:
                role_enum = UserRole(role_name)
                executive_roles.append(role_enum)
            except ValueError:
                pass
                
        for role_name in management_role_names[:3]:  # First 3 managers
            try:
                role_enum = UserRole(role_name)
                manager_roles.append(role_enum)
            except ValueError:
                pass
                
        for role_name in marketing_role_names:
            try:
                role_enum = UserRole(role_name)
                agent_roles.append(role_enum)
            except ValueError:
                pass
        
        print("\n🏢 EXECUTIVE ROLES:")
        for i, role in enumerate(executive_roles, 1):
            print(f"   {i}. {role.value.replace('_', ' ').title()}")
        
        print(f"\n👨‍💼 MANAGER ROLES:")
        for i, role in enumerate(manager_roles, len(executive_roles) + 1):
            print(f"   {i}. {role.value.replace('_', ' ').title()}")
        
        print(f"\n🤖 AGENT ROLES:")
        for i, role in enumerate(agent_roles, len(executive_roles) + len(manager_roles) + 1):
            print(f"   {i}. {role.value.replace('_', ' ').title()}")
        
        all_roles = executive_roles + manager_roles + agent_roles
        
        while True:
            try:
                choice = input(f"\n🎯 Select role (1-{len(all_roles)}): ").strip()
                if not choice:
                    return None
                
                choice_num = int(choice) - 1
                if 0 <= choice_num < len(all_roles):
                    selected_role = all_roles[choice_num]
                    print(f"✅ Selected: {selected_role.value.replace('_', ' ').title()}")
                    return selected_role
                else:
                    print("❌ Invalid choice. Please try again.")
                    
            except ValueError:
                print("❌ Please enter a valid number.")
    
    async def display_user_dashboard(self, user: User):
        """Display user dashboard after login"""
        print("\n" + "="*60)
        print(f"🎯 {user.role.value.replace('_', ' ').title().upper()} DASHBOARD")
        print("="*60)
        
        # User info
        print(f"👤 User: {user.username}")
        print(f"🎭 Role: {user.role.value.replace('_', ' ').title()}")
        print(f"📧 Email: {user.email}")
        
        # Agent access
        accessible_agents = user.get_accessible_agents()
        print(f"\n🤖 Accessible Agents ({len(accessible_agents)}):")
        for agent in accessible_agents:
            agent_access = self.memory_controller.get_agent_memory_access(agent)
            access_level = agent_access.get('access_level', 'none')
            private_access = agent_access.get('private_memory_access', False)
            
            print(f"   • {agent.value.title()} Agent")
            print(f"     - Access Level: {access_level}")
            print(f"     - Private Memory: {'Yes' if private_access else 'No'}")
        
        # Memory collections
        memory_collections = user.get_accessible_memory_collections()
        readable_collections = self.memory_controller.get_readable_collections()
        writable_collections = self.memory_controller.get_writable_collections()
        
        print(f"\n🧠 Memory Collections ({len(memory_collections)}):")
        for collection in memory_collections:
            can_read = collection in readable_collections
            can_write = collection in writable_collections
            
            print(f"   • {collection}")
            print(f"     - Read: {'Yes' if can_read else 'No'}")
            print(f"     - Write: {'Yes' if can_write else 'No'}")
        
        # Role-specific features
        if user.is_cmo():
            print(f"\n🔥 CMO PRIVILEGES:")
            print(f"   • Full system access")
            print(f"   • All agent private memory access")
            print(f"   • User management capabilities")
            print(f"   • Access audit logs")
        elif user.is_manager():
            print(f"\n👨‍💼 MANAGER PRIVILEGES:")
            print(f"   • Division oversight")
            print(f"   • Cross-agent coordination")
            print(f"   • Team management")
        else:
            print(f"\n🎯 AGENT CAPABILITIES:")
            print(f"   • Specialized task execution")
            print(f"   • Private memory access")
            print(f"   • Knowledge base utilization")
        
        print("="*60)
    
    async def run_auth_flow(self) -> Optional[User]:
        """Run complete authentication flow"""
        self.display_welcome()
        
        while True:
            self.display_auth_menu()
            
            choice = input("\n🎯 Choose option (1-4): ").strip()
            
            if choice == "1":
                # Login
                user = await self.handle_login()
                if user:
                    await self.display_user_dashboard(user)
                    return user
                else:
                    print("\n⚠️  Login failed. Please try again.")
                    
            elif choice == "2":
                # Register
                success = await self.handle_registration()
                if success:
                    print("\n✅ Registration complete! Please login.")
                    continue
                else:
                    print("\n⚠️  Registration failed. Please try again.")
                    
            elif choice == "3":
                # View roles
                self.display_available_roles()
                
            elif choice == "4":
                # Exit
                print("\n👋 Goodbye!")
                return None
                
            else:
                print("❌ Invalid choice. Please try again.")
    
    async def display_post_login_menu(self, user: User):
        """Display menu after successful login"""
        print("\n" + "="*50)
        print("🎛️  MAIN MENU")
        print("="*50)
        print("1. 🤖 Access Agent")
        print("2. 🧠 Browse Memory Collections")
        print("3. 👤 View Profile")
        print("4. 📊 Access Summary")
        
        if user.is_cmo():
            print("5. 👥 Manage Users (CMO)")
            print("6. 📝 View Access Logs (CMO)")
            print("7. 🔓 Logout")
            print("8. ❌ Exit")
        else:
            print("5. 🔓 Logout")
            print("6. ❌ Exit")
        
        print("="*50)
    
    async def handle_post_login_flow(self, user: User):
        """Handle user interaction after login"""
        self.running = True
        
        while self.running:
            await self.display_post_login_menu(user)
            
            max_choice = 8 if user.is_cmo() else 6
            choice = input(f"\n🎯 Choose option (1-{max_choice}): ").strip()
            
            if choice == "1":
                await self._handle_agent_access(user)
            elif choice == "2":
                await self._handle_memory_browse(user)
            elif choice == "3":
                await self._handle_profile_view(user)
            elif choice == "4":
                await self._handle_access_summary(user)
            elif choice == "5":
                if user.is_cmo():
                    await self._handle_user_management(user)
                else:
                    # Logout
                    self.auth_manager.logout()
                    print("🔓 Logged out successfully!")
                    break
            elif choice == "6":
                if user.is_cmo():
                    await self._handle_access_logs(user)
                else:
                    # Exit
                    print("👋 Goodbye!")
                    self.running = False
                    break
            elif choice == "7" and user.is_cmo():
                # Logout
                self.auth_manager.logout()
                print("🔓 Logged out successfully!")
                break
            elif choice == "8" and user.is_cmo():
                # Exit
                print("👋 Goodbye!")
                self.running = False
                break
            else:
                print("❌ Invalid choice. Please try again.")
    
    async def _handle_agent_access(self, user: User):
        """Handle agent access selection"""
        accessible_agents = user.get_accessible_agents()
        
        if not accessible_agents:
            print("❌ No accessible agents found")
            return
        
        print("\n🤖 ACCESSIBLE AGENTS:")
        for i, agent in enumerate(accessible_agents, 1):
            print(f"   {i}. {agent.value.title()} Agent")
        
        choice = input(f"\n🎯 Select agent (1-{len(accessible_agents)}): ").strip()
        
        try:
            choice_num = int(choice) - 1
            if 0 <= choice_num < len(accessible_agents):
                selected_agent = accessible_agents[choice_num]
                print(f"\n✅ Accessing {selected_agent.value.title()} Agent...")
                print("🚀 Starting agent interaction...")
                print("   (This would connect to the actual agent system)")
                input("\n⏎ Press Enter to continue...")
            else:
                print("❌ Invalid choice")
        except ValueError:
            print("❌ Please enter a valid number")
    
    async def _handle_memory_browse(self, user: User):
        """Handle memory collection browsing"""
        collections = user.get_accessible_memory_collections()
        
        if not collections:
            print("❌ No accessible memory collections found")
            return
        
        print("\n🧠 ACCESSIBLE MEMORY COLLECTIONS:")
        for i, collection in enumerate(collections, 1):
            can_read = self.memory_controller.validate_memory_read(collection)
            can_write = self.memory_controller.validate_memory_write(collection)
            
            print(f"   {i}. {collection}")
            print(f"      Read: {'Yes' if can_read else 'No'} | Write: {'Yes' if can_write else 'No'}")
        
        input("\n⏎ Press Enter to continue...")
    
    async def _handle_profile_view(self, user: User):
        """Handle profile viewing"""
        await self.display_user_dashboard(user)
        input("\n⏎ Press Enter to continue...")
    
    async def _handle_access_summary(self, user: User):
        """Handle access summary display"""
        summary = self.access_controller.get_user_access_summary()
        
        print("\n📊 ACCESS SUMMARY:")
        print(f"   User ID: {summary.get('user_id')}")
        print(f"   Username: {summary.get('username')}")
        print(f"   Role: {summary.get('role')}")
        print(f"   Is CMO: {summary.get('is_cmo')}")
        print(f"   Is Manager: {summary.get('is_manager')}")
        print(f"   Accessible Agents: {summary.get('accessible_agents')}")
        print(f"   Memory Collections: {len(summary.get('accessible_memory_collections', []))}")
        
        input("\n⏎ Press Enter to continue...")
    
    async def _handle_user_management(self, user: User):
        """Handle user management (CMO only)"""
        print("\n👥 USER MANAGEMENT (CMO)")
        print("   This feature would allow:")
        print("   • View all users")
        print("   • Add/remove agent assignments")
        print("   • Deactivate users")
        print("   • Modify user roles")
        print("   (Implementation pending)")
        
        input("\n⏎ Press Enter to continue...")
    
    async def _handle_access_logs(self, user: User):
        """Handle access logs viewing (CMO only)"""
        logs = self.access_controller.get_access_log()
        
        print(f"\n📝 ACCESS LOGS ({len(logs)} entries):")
        if logs:
            for log in logs[-10:]:  # Show last 10 entries
                print(f"   {log['timestamp']}: {log['user']} -> {log['resource']} [{log['status']}]")
        else:
            print("   No access logs available")
        
        input("\n⏎ Press Enter to continue...") 