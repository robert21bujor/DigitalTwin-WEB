"""
Account Type System for Role-based Multi-Agent Architecture
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AccountType(Enum):
    """Account types with different permissions and capabilities"""
    EXECUTIVE = "executive"
    MANAGER = "manager"
    AGENT = "agent"


class Division(Enum):
    """Marketing divisions"""
    PRODUCT_MARKETING = "product_marketing"
    DIGITAL_MARKETING = "digital_marketing"
    CONTENT_MARKETING = "content_marketing"


@dataclass
class UserAccount:
    """User account with role-based permissions"""
    username: str
    account_type: AccountType
    division: Optional[Division] = None  # Only for Manager and Agent types
    agent_name: Optional[str] = None     # Only for Agent type
    permissions: List[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.permissions is None:
            self.permissions = self._get_default_permissions()
    
    def _get_default_permissions(self) -> List[str]:
        """Get default permissions based on account type"""
        if self.account_type == AccountType.EXECUTIVE:
            return [
                "global_access",
                "cross_division_oversight", 
                "strategic_planning",
                "create_tasks_any_division",
                "view_all_tasks",
                "approve_high_priority_tasks",
                "access_global_memory",
                "coordinate_divisions"
            ]
        elif self.account_type == AccountType.MANAGER:
            return [
                "division_oversight",
                "assign_tasks_within_division",
                "view_division_tasks",
                "communicate_with_agents",
                "access_division_memory",
                "approve_division_tasks",
                "manage_division_resources"
            ]
        else:  # AGENT
            return [
                "execute_assigned_tasks",
                "update_task_progress",
                "chat_with_task_assistant",
                "access_task_context",
                "access_agent_memory",
                "communicate_within_task"
            ]
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions
    
    def can_access_division(self, division: Division) -> bool:
        """Check if user can access specific division"""
        if self.account_type == AccountType.EXECUTIVE:
            return True  # Executive can access all divisions
        return self.division == division
    
    def get_memory_collections(self) -> List[str]:
        """Get accessible memory collections based on role"""
        collections = []
        
        if self.account_type == AccountType.EXECUTIVE:
            # Executive has global access
            collections.append("global-shared-memory")
            collections.extend([
                "agent-product-private",
                "agent-digital-private", 
                "agent-content-private"
            ])
        elif self.account_type == AccountType.MANAGER:
            # Manager has division access
            if self.division == Division.PRODUCT_MARKETING:
                collections.extend(["global-shared-memory", "agent-product-private"])
            elif self.division == Division.DIGITAL_MARKETING:
                collections.extend(["global-shared-memory", "agent-digital-private"])
            elif self.division == Division.CONTENT_MARKETING:
                collections.extend(["global-shared-memory", "agent-content-private"])
        else:  # AGENT
            # Agent has specific collection access
            collections.append("global-shared-memory")  # Shared knowledge
            if self.division == Division.PRODUCT_MARKETING:
                collections.append("agent-product-private")
            elif self.division == Division.DIGITAL_MARKETING:
                collections.append("agent-digital-private")
            elif self.division == Division.CONTENT_MARKETING:
                collections.append("agent-content-private")
        
        return collections


class AccountManager:
    """Manages user accounts and authentication"""
    
    def __init__(self):
        self.accounts: Dict[str, UserAccount] = {}
        self.current_session: Optional[UserAccount] = None
        self._initialize_default_accounts()
    
    def _initialize_default_accounts(self):
        """Initialize default accounts for testing"""
        
        # Executive Account (CMO)
        self.accounts["cmo"] = UserAccount(
            username="cmo",
            account_type=AccountType.EXECUTIVE
        )
        
        # Manager Accounts
        self.accounts["product_manager"] = UserAccount(
            username="product_manager",
            account_type=AccountType.MANAGER,
            division=Division.PRODUCT_MARKETING
        )
        
        self.accounts["digital_manager"] = UserAccount(
            username="digital_manager", 
            account_type=AccountType.MANAGER,
            division=Division.DIGITAL_MARKETING
        )
        
        self.accounts["content_manager"] = UserAccount(
            username="content_manager",
            account_type=AccountType.MANAGER,
            division=Division.CONTENT_MARKETING
        )
        
        # Agent Accounts
        agent_configs = [
            # Product Marketing Agents
            ("positioning_agent", Division.PRODUCT_MARKETING, "PositioningAgent"),
            ("persona_agent", Division.PRODUCT_MARKETING, "PersonaAgent"), 
            ("gtm_agent", Division.PRODUCT_MARKETING, "GTMAgent"),
            ("competitor_agent", Division.PRODUCT_MARKETING, "CompetitorAgent"),
            ("launch_agent", Division.PRODUCT_MARKETING, "LaunchAgent"),
            
            # Digital Marketing Agents  
            ("seo_agent", Division.DIGITAL_MARKETING, "SEOAgent"),
            ("sem_agent", Division.DIGITAL_MARKETING, "SEMAgent"),
            ("landing_agent", Division.DIGITAL_MARKETING, "LandingAgent"),
            ("analytics_agent", Division.DIGITAL_MARKETING, "AnalyticsAgent"),
            ("funnel_agent", Division.DIGITAL_MARKETING, "FunnelAgent"),
            
            # Content Marketing Agents
            ("content_agent", Division.CONTENT_MARKETING, "ContentAgent"),
            ("brand_agent", Division.CONTENT_MARKETING, "BrandAgent"), 
            ("social_agent", Division.CONTENT_MARKETING, "SocialAgent"),
            ("community_agent", Division.CONTENT_MARKETING, "CommunityAgent")
        ]
        
        for username, division, agent_name in agent_configs:
            self.accounts[username] = UserAccount(
                username=username,
                account_type=AccountType.AGENT,
                division=division,
                agent_name=agent_name
            )
    
    def login(self, username: str) -> Optional[UserAccount]:
        """Authenticate user and start session"""
        if username in self.accounts:
            self.current_session = self.accounts[username]
            logger.info(f"User '{username}' logged in as {self.current_session.account_type.value}")
            return self.current_session
        else:
            logger.warning(f"Login failed for username: {username}")
            return None
    
    def logout(self):
        """End current session"""
        if self.current_session:
            logger.info(f"User '{self.current_session.username}' logged out")
            self.current_session = None
    
    def get_current_user(self) -> Optional[UserAccount]:
        """Get currently logged in user"""
        return self.current_session
    
    def create_account(self, username: str, account_type: AccountType, 
                      division: Optional[Division] = None, 
                      agent_name: Optional[str] = None) -> UserAccount:
        """Create new user account"""
        account = UserAccount(
            username=username,
            account_type=account_type,
            division=division,
            agent_name=agent_name
        )
        self.accounts[username] = account
        logger.info(f"Created new {account_type.value} account: {username}")
        return account
    
    def list_accounts_by_type(self, account_type: AccountType) -> List[UserAccount]:
        """Get all accounts of specific type"""
        return [acc for acc in self.accounts.values() if acc.account_type == account_type]
    
    def get_accounts_by_division(self, division: Division) -> List[UserAccount]:
        """Get all accounts in specific division"""
        return [acc for acc in self.accounts.values() if acc.division == division]
    
    async def start_role_based_interface(self):
        """Start the role-based interface system"""
        try:
            from Core.Interfaces.chat_interfaces import ExecutiveChatInterface, ManagerChatInterface, AgentChatInterface
            from Core.Departments.company_system import CompanySystem
            import semantic_kernel as sk
            
            # Initialize required systems
            kernel = sk.Kernel()
            company_system = CompanySystem(kernel)
            company_system.initialize_all_departments()
            
            # Role selection
            print("\n👤 Available Roles:")
            print("1. 🏆 Executive (CMO)")
            print("2. 👥 Manager (Department Head)")
            print("3. 🤖 Agent (Specialist)")
            
            role_choice = input("\nSelect your role (1-3): ").strip()
            
            if role_choice == "1":
                # Executive login
                user_account = self.login("cmo")
                if user_account:
                    chat_interface = ExecutiveChatInterface(user_account, kernel, company_system)
                    print(f"✅ Logged in as Executive: {user_account.username}")
                    print("💼 You have cross-department access and strategic oversight")
                    
                    # Interactive executive interface
                    while True:
                        user_input = input("\n🏆 Executive> ").strip()
                        if user_input.lower() in ['quit', 'exit']:
                            break
                        
                        try:
                            response = await chat_interface.process_input(user_input)
                            print(f"📋 {response}")
                        except Exception as e:
                            print(f"❌ Error: {e}")
                            
            elif role_choice == "2":
                # Manager selection
                print("\n👥 Available Manager Roles:")
                print("1. Product Marketing Manager")
                print("2. Digital Marketing Manager") 
                print("3. Content Marketing Manager")
                
                mgr_choice = input("\nSelect department (1-3): ").strip()
                manager_accounts = {
                    "1": "product_manager",
                    "2": "digital_manager", 
                    "3": "content_manager"
                }
                
                if mgr_choice in manager_accounts:
                    user_account = self.login(manager_accounts[mgr_choice])
                    if user_account:
                        chat_interface = ManagerChatInterface(user_account, kernel, company_system)
                        print(f"✅ Logged in as Manager: {user_account.username}")
                        print(f"📊 Division: {user_account.division.value}")
                        
                        # Interactive manager interface
                        while True:
                            user_input = input(f"\n👥 {user_account.username}> ").strip()
                            if user_input.lower() in ['quit', 'exit']:
                                break
                                
                            try:
                                response = await chat_interface.process_input(user_input)
                                print(f"📋 {response}")
                            except Exception as e:
                                print(f"❌ Error: {e}")
                                
            elif role_choice == "3":
                # Agent selection
                print("\n🤖 Available Agent Roles:")
                agents = self.list_accounts_by_type(AccountType.AGENT)
                for i, agent in enumerate(agents[:10], 1):  # Show first 10
                    print(f"{i}. {agent.agent_name} ({agent.division.value})")
                
                agent_choice = input(f"\nSelect agent (1-{min(10, len(agents))}): ").strip()
                try:
                    agent_idx = int(agent_choice) - 1
                    if 0 <= agent_idx < len(agents):
                        selected_agent = agents[agent_idx]
                        user_account = self.login(selected_agent.username)
                        if user_account:
                            chat_interface = AgentChatInterface(user_account, kernel)
                            print(f"✅ Logged in as Agent: {user_account.agent_name}")
                            print(f"🎯 Specialization: {user_account.division.value}")
                            
                            # Interactive agent interface
                            while True:
                                user_input = input(f"\n🤖 {user_account.agent_name}> ").strip()
                                if user_input.lower() in ['quit', 'exit']:
                                    break
                                    
                                try:
                                    response = await chat_interface.process_input(user_input)
                                    print(f"📋 {response}")
                                except Exception as e:
                                    print(f"❌ Error: {e}")
                except ValueError:
                    print("❌ Invalid selection")
            else:
                print("❌ Invalid role selection")
                
        except Exception as e:
            print(f"❌ Role-based interface error: {e}")
            logger.error(f"Role-based interface error: {e}", exc_info=True) 