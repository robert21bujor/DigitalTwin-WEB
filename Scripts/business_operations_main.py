"""
Main entry point for the BusinessDev and Operations Multi-Agent System

Features:
- Business Development: IPM, BDM, Presales engineering
- Operations: Client Success, Delivery Consulting, Legal, Custom Reporting
- Role-based access control with specialized agents
- Memory-enhanced conversations with persistent knowledge
- Multi-language support (EN, BG, HU) for delivery consulting
"""

import asyncio
import sys
import os
from typing import Optional, List
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Auth.User_management.user_models import UserRole, User
from Auth.User_management.auth_manager import AuthManager
from Auth.User_management.access_control import AccessController, MemoryAccessController
from Utils.logger import setup_main_logging
from Utils.config import Config
import semantic_kernel as sk
from semantic_kernel.contents import ChatHistory
from semantic_kernel.connectors.ai import PromptExecutionSettings
from semantic_kernel.connectors.ai.open_ai.services.azure_chat_completion import AzureChatCompletion
from Memory.memory_sync import GoogleDriveMemorySync
from Core.Tasks.task_manager import get_task_manager, TaskManager
from Core.Tasks.task import TaskStatus, TaskPriority
from Core.Tasks.orchestrator import Orchestrator

# Import our departments
from Departments.BusinessDev.business_dev_department import BusinessDevDepartment
from Departments.Operations.operations_department import OperationsDepartment

# Configure logging
logger = setup_main_logging(Config.get_log_config())


class BusinessOperationsSystem:
    """Business Development and Operations system management"""
    
    def __init__(self, kernel: sk.Kernel):
        self.kernel = kernel
        self.businessdev_department = None
        self.operations_department = None
        self.initialized = False
        
    def initialize_departments(self) -> bool:
        """Initialize BusinessDev and Operations departments"""
        try:
            logger.info("🚀 Initializing BusinessDev and Operations System...")
            
            # Initialize BusinessDev Department
            self.businessdev_department = BusinessDevDepartment(self.kernel)
            if not self.businessdev_department.setup_department():
                logger.error("❌ Failed to initialize BusinessDev department")
                return False
            logger.info("✅ BusinessDev department initialized successfully")
            
            # Initialize Operations Department
            self.operations_department = OperationsDepartment(self.kernel)
            if not self.operations_department.setup_department():
                logger.error("❌ Failed to initialize Operations department")
                return False
            logger.info("✅ Operations department initialized successfully")
            
            self.initialized = True
            logger.info("✅ BusinessDev and Operations system initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            return False
    
    def get_agent_for_role(self, user_role: UserRole):
        """Get the appropriate agent for a user role"""
        # BusinessDev agents
        if user_role == UserRole.BUSINESS_DEV_MANAGER:
            # Business Dev Manager gets access to BDM Agent as primary interface
            if self.businessdev_department:
                for agent in self.businessdev_department.agents:
                    if hasattr(agent, 'name') and 'BDM' in agent.name:
                        return agent
        elif user_role == UserRole.IPM_AGENT:
            if self.businessdev_department:
                # Get IPM agent from BusinessDev department
                for agent in self.businessdev_department.agents:
                    if hasattr(agent, 'name') and 'IPM' in agent.name:
                        return agent
        elif user_role == UserRole.BDM_AGENT:
            if self.businessdev_department:
                for agent in self.businessdev_department.agents:
                    if hasattr(agent, 'name') and 'BDM' in agent.name:
                        return agent
        elif user_role == UserRole.PRESALES_ENGINEER_AGENT:
            if self.businessdev_department:
                for agent in self.businessdev_department.agents:
                    if hasattr(agent, 'name') and 'Presales' in agent.name:
                        return agent
        
        # Operations agents
        elif user_role == UserRole.OPERATIONS_MANAGER:
            # Operations Manager gets access to Head of Operations Agent as primary interface
            if self.operations_department:
                for agent in self.operations_department.agents:
                    if hasattr(agent, 'name') and 'Head of Operations' in agent.name:
                        return agent
        elif user_role == UserRole.HEAD_OF_OPERATIONS_AGENT:
            if self.operations_department:
                for agent in self.operations_department.agents:
                    if hasattr(agent, 'name') and 'Head of Operations' in agent.name:
                        return agent
        elif user_role == UserRole.SENIOR_CSM_AGENT:
            if self.operations_department:
                for agent in self.operations_department.agents:
                    if hasattr(agent, 'name') and 'Senior CSM' in agent.name or 'Senior Customer Success' in agent.name:
                        return agent
        elif user_role == UserRole.SENIOR_DELIVERY_CONSULTANT_AGENT:
            if self.operations_department:
                for agent in self.operations_department.agents:
                    if hasattr(agent, 'name') and 'Senior Delivery' in agent.name:
                        return agent
        elif user_role == UserRole.DELIVERY_CONSULTANT_BG_AGENT:
            if self.operations_department:
                for agent in self.operations_department.agents:
                    if hasattr(agent, 'name') and 'BG' in agent.name:
                        return agent
        elif user_role == UserRole.DELIVERY_CONSULTANT_HU_AGENT:
            if self.operations_department:
                for agent in self.operations_department.agents:
                    if hasattr(agent, 'name') and 'HU' in agent.name:
                        return agent
        elif user_role == UserRole.DELIVERY_CONSULTANT_EN_AGENT:
            if self.operations_department:
                for agent in self.operations_department.agents:
                    if hasattr(agent, 'name') and 'EN' in agent.name:
                        return agent
        elif user_role == UserRole.REPORTING_MANAGER_AGENT:
            if self.operations_department:
                for agent in self.operations_department.agents:
                    if hasattr(agent, 'name') and 'Reporting Manager' in agent.name:
                        return agent
        elif user_role == UserRole.REPORTING_SPECIALIST_AGENT:
            if self.operations_department:
                for agent in self.operations_department.agents:
                    if hasattr(agent, 'name') and 'Reporting Specialist' in agent.name:
                        return agent
        elif user_role == UserRole.LEGAL_AGENT:
            if self.operations_department:
                for agent in self.operations_department.agents:
                    if hasattr(agent, 'name') and 'Legal' in agent.name:
                        return agent
        
        return None
    
    def is_initialized(self) -> bool:
        """Check if system is initialized"""
        return self.initialized


class RoleBasedBusinessOperationsInterface:
    """Chat interface for BusinessDev and Operations agents"""
    
    def __init__(self, user: User, business_ops_system, memory_controller):
        self.user = user
        self.business_ops_system = business_ops_system
        self.memory_controller = memory_controller
        self.display_role = self._get_display_role(user.role)
        self.agent = self.business_ops_system.get_agent_for_role(user.role)
        
        # Initialize chat history if we have an agent
        if self.agent:
            self.chat_history = ChatHistory()
            self.chat_history.add_system_message(self._get_system_prompt())
    
    def _get_display_role(self, user_role):
        """Map UserRole to display category"""
        if user_role in [UserRole.BUSINESS_DEV_MANAGER]:
            return "BUSINESS DEV MANAGER"
        elif user_role in [UserRole.IPM_AGENT, UserRole.BDM_AGENT, UserRole.PRESALES_ENGINEER_AGENT]:
            return "BUSINESS DEV AGENT"
        elif user_role in [UserRole.OPERATIONS_MANAGER]:
            return "OPERATIONS MANAGER"
        elif user_role in [UserRole.HEAD_OF_OPERATIONS_AGENT, UserRole.SENIOR_CSM_AGENT, UserRole.SENIOR_DELIVERY_CONSULTANT_AGENT,
                           UserRole.DELIVERY_CONSULTANT_BG_AGENT, UserRole.DELIVERY_CONSULTANT_HU_AGENT, UserRole.DELIVERY_CONSULTANT_EN_AGENT,
                           UserRole.REPORTING_MANAGER_AGENT, UserRole.REPORTING_SPECIALIST_AGENT, UserRole.LEGAL_AGENT]:
            return "OPERATIONS AGENT"
        else:
            return "SPECIALIST"
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the agent"""
        if self.agent and hasattr(self.agent, 'system_prompt'):
            return self.agent.system_prompt
        
        return f"""You are a {self.display_role} in a Business Development and Operations system.
        You have access to specialized knowledge and can help with tasks related to your role.
        Role: {self.user.role.value}
        Capabilities: Task execution, memory access, role-specific expertise"""
    
    async def process_input(self, user_input: str) -> str:
        """Process user input and return response"""
        try:
            # Handle special commands
            if user_input.upper().startswith("WHOAMI"):
                return self._handle_whoami_command()
            elif user_input.upper().startswith("MEMORY"):
                return self._handle_memory_command()
            elif user_input.upper().startswith("AGENTS"):
                return self._handle_agents_command()
            elif user_input.upper().startswith("HELP"):
                return self._handle_help_command()
            
            # Add user message to chat history
            if hasattr(self, 'chat_history'):
                self.chat_history.add_user_message(user_input)
            
            # Use AI to generate response regardless of agent availability
            response = await self._get_ai_response(user_input)
            
            # Add assistant response to chat history
            if hasattr(self, 'chat_history'):
                self.chat_history.add_assistant_message(response)
            
            return response
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            return f"[ERROR] Failed to process input: {str(e)}"
    
    async def _get_ai_response(self, user_input: str) -> str:
        """Get AI response using Semantic Kernel"""
        try:
            from semantic_kernel.connectors.ai import PromptExecutionSettings
            
            # Create settings for the AI call
            settings = PromptExecutionSettings(
                service_id="default",
                max_tokens=500,
                temperature=0.7
            )
            
            # Create the prompt with agent context
            agent_name = self.agent.name if self.agent else f"{self.display_role}"
            
            # Create a comprehensive system prompt based on role
            if "BUSINESS DEV" in self.display_role:
                role_context = """You are an expert Business Development Manager specializing in:
- Partnership strategy and development
- Market opportunity identification  
- Strategic alliance formation
- Revenue growth through partnerships
- Competitive analysis and positioning
- Go-to-market strategy development
- Stakeholder relationship management"""
            elif "OPERATIONS" in self.display_role:
                role_context = """You are an expert Operations Manager specializing in:
- Client success and retention strategies
- Service delivery optimization
- Multi-language customer support (EN/BG/HU)
- Process improvement and automation
- Legal compliance and risk management
- Custom reporting and analytics
- Quality assurance and performance management"""
            else:
                role_context = f"You are a {self.display_role} with expertise in business operations and development."
            
            prompt = f"""{role_context}

The user has asked: {user_input}

Please provide a professional, actionable response that demonstrates your expertise. Be specific, helpful, and offer concrete next steps where appropriate. Keep your response focused and valuable."""

            try:
                # Get the kernel from business ops system
                kernel = getattr(self.business_ops_system, 'kernel', None)
                
                if kernel and hasattr(kernel, 'services'):
                    # Try to get a chat completion service
                    chat_service = None
                    for service in kernel.services.values():
                        if hasattr(service, 'get_chat_message_contents'):
                            chat_service = service
                            break
                    
                    if chat_service:
                        # Use the chat service directly
                        from semantic_kernel.contents.chat_history import ChatHistory
                        from semantic_kernel.contents import ChatMessageContent, AuthorRole
                        
                        chat_history = ChatHistory()
                        chat_history.add_message(ChatMessageContent(role=AuthorRole.SYSTEM, content=role_context))
                        chat_history.add_message(ChatMessageContent(role=AuthorRole.USER, content=user_input))
                        
                        response = await chat_service.get_chat_message_contents(
                            chat_history=chat_history,
                            settings=settings
                        )
                        
                        if response and len(response) > 0:
                            return f"[{agent_name}] {response[0].content}"
                        
                # Fallback: Use intelligent template response
                return self._get_intelligent_response(user_input, agent_name, self.display_role)
                        
            except Exception as kernel_error:
                logger.warning(f"Kernel usage failed: {kernel_error}")
                return self._get_intelligent_response(user_input, agent_name, self.display_role)
                
        except Exception as e:
            logger.error(f"Error in AI response generation: {e}")
            return f"[{agent_name}] I'm here to help with your business development needs. Could you please provide more details about what you'd like to accomplish?"
    
    def _get_intelligent_response(self, user_input: str, agent_name: str, role: str) -> str:
        """Generate an intelligent response based on input keywords and role"""
        input_lower = user_input.lower()
        
        # Business Development responses
        if "BUSINESS DEV" in role:
            if any(word in input_lower for word in ["partnership", "partner", "alliance"]):
                return f"[{agent_name}] For partnership development, I recommend focusing on strategic alignment and mutual value creation. Let's identify target partners that complement our capabilities and share similar market objectives. I can help you develop a partnership strategy, create value propositions, and establish evaluation criteria. What specific type of partnership are you considering?"
            
            elif any(word in input_lower for word in ["strategy", "plan", "roadmap"]):
                return f"[{agent_name}] Strategic planning is crucial for business development success. I can help you create a comprehensive business development roadmap including market analysis, competitive positioning, partnership opportunities, and revenue growth strategies. What specific strategic area would you like to focus on first?"
            
            elif any(word in input_lower for word in ["market", "opportunity", "competition"]):
                return f"[{agent_name}] Market analysis and opportunity identification are key to successful business development. I can help you assess market size, identify growth opportunities, analyze competitive landscape, and develop market entry strategies. What market or opportunity are you evaluating?"
            
            elif any(word in input_lower for word in ["hello", "hi", "test", "testing"]):
                return f"[{agent_name}] Hello! I'm your Business Development Manager, ready to help you drive growth through strategic partnerships and market opportunities. I can assist with partnership strategy, market analysis, competitive positioning, and business development planning. What business development challenge can I help you tackle today?"
            
            else:
                return f"[{agent_name}] As your Business Development Manager, I can help you with partnership development, market analysis, strategic planning, and revenue growth initiatives. I'd be happy to discuss your specific business development goals and create an actionable plan. What business development area would you like to explore?"
        
        # Operations responses  
        elif "OPERATIONS" in role:
            if any(word in input_lower for word in ["client", "customer", "success"]):
                return f"[{agent_name}] Client success is at the heart of effective operations. I can help you develop client retention strategies, optimize service delivery, implement customer health scoring, and create escalation procedures. Our multi-language capabilities (EN/BG/HU) ensure global client support. What specific client success challenge are you facing?"
            
            elif any(word in input_lower for word in ["delivery", "project", "implementation"]):
                return f"[{agent_name}] Project delivery excellence requires structured methodologies and quality assurance. I can help you optimize delivery processes, manage complex implementations, coordinate multi-language support teams, and ensure client satisfaction. What delivery challenge can I help you address?"
            
            elif any(word in input_lower for word in ["report", "analytics", "dashboard"]):
                return f"[{agent_name}] Custom reporting and analytics drive operational excellence. I can help you design KPI dashboards, automate reporting processes, create executive summaries, and implement data-driven decision making. What reporting requirements do you have?"
            
            elif any(word in input_lower for word in ["hello", "hi", "test", "testing"]):
                return f"[{agent_name}] Hello! I'm your Operations Manager, here to help optimize your business operations. I specialize in client success, delivery management, legal compliance, and custom reporting with multi-language support (EN/BG/HU). What operational challenge can I help you solve today?"
            
            else:
                return f"[{agent_name}] As your Operations Manager, I can help you optimize client success, streamline delivery processes, ensure legal compliance, and implement effective reporting systems. Our team provides multi-language support for global operations. What operational area would you like to improve?"
        
        # Default response
        else:
            return f"[{agent_name}] I'm here to help with your business needs. Based on your request '{user_input}', I can provide strategic guidance and actionable recommendations. How can I assist you in achieving your business objectives?"
    
    def _handle_whoami_command(self) -> str:
        """Handle WHOAMI command"""
        agent_info = f"Agent: {self.agent.name}" if self.agent else "Agent: Not connected"
        
        return f"""🔍 USER PROFILE:
• User: {self.user.username}
• Role: {self.user.role.value}
• Display Role: {self.display_role}
• {agent_info}
• Department: {'BusinessDev' if 'BUSINESS' in self.display_role else 'Operations'}

✅ Authentication successful!"""
    
    def _handle_memory_command(self) -> str:
        """Handle MEMORY command"""
        readable = self.memory_controller.get_readable_collections() if self.memory_controller else []
        writable = self.memory_controller.get_writable_collections() if self.memory_controller else []
        
        return f"""💾 MEMORY ACCESS:
• Readable Collections: {len(readable)}
• Writable Collections: {len(writable)}
• Your Role: {self.user.role.value}

📚 Available Collections:
{chr(10).join(['  • ' + col for col in readable[:5]])}
{'  • ...' if len(readable) > 5 else ''}"""
    
    def _handle_agents_command(self) -> str:
        """Handle AGENTS command"""
        accessible_agents = self.user.get_accessible_agents()
        
        return f"""🤖 AGENT ACCESS:
• Total Accessible Agents: {len(accessible_agents)}
• Your Role: {self.user.role.value}
• Connected Agent: {self.agent.name if self.agent else 'None'}

🎯 Available Agents:
{chr(10).join(['  • ' + agent.value for agent in accessible_agents[:5]])}
{'  • ...' if len(accessible_agents) > 5 else ''}"""
    
    def _handle_help_command(self) -> str:
        """Handle HELP command"""
        commands = [
            "WHOAMI - View your profile and authentication status",
            "MEMORY - Check your memory access permissions",
            "AGENTS - View accessible agents and connections",
            "HELP - Show this help message",
            "quit/exit - Logout and return to main menu"
        ]
        
        role_specific_help = ""
        if 'BUSINESS' in self.display_role:
            role_specific_help = """
🏢 BUSINESS DEVELOPMENT CAPABILITIES:
• Project management and coordination
• Partnership development and management
• Presales engineering and solution design"""
        elif 'OPERATIONS' in self.display_role:
            role_specific_help = """
🔧 OPERATIONS CAPABILITIES:
• Client success management
• Delivery consulting (EN/BG/HU)
• Custom reporting and analytics
• Legal compliance and contract management"""
        
        return f"""🆘 HELP - BusinessDev & Operations System

📋 AVAILABLE COMMANDS:
{chr(10).join(['  • ' + cmd for cmd in commands])}
{role_specific_help}

💡 TIP: Simply type your request and the system will route it to the appropriate specialist."""


class RoleBasedBusinessOperationsSystem:
    """Main BusinessDev and Operations system with login functionality"""
    
    def __init__(self):
        self.business_ops_system = None
        self.auth_manager = AuthManager()
        self.access_controller = None
        self.memory_controller = None
        self.current_chat_interface = None
        self.running = False
    
    async def initialize(self):
        """Initialize the BusinessDev and Operations system"""
        try:
            # Initialize authentication system
            self.auth_manager._initialize_supabase()
            if not self.auth_manager.client:
                raise Exception("Failed to initialize authentication system")
            logger.info("Authentication system initialized successfully")
            
            # Perform startup sync with Google Drive
            await self._startup_sync()
            
            # Initialize kernel with Azure OpenAI
            try:
                kernel = self._init_kernel()
                logger.info("Kernel initialized successfully")
            except Exception as e:
                logger.warning(f"Kernel initialization failed: {e}")
                kernel = None
            
            # Initialize BusinessDev and Operations system
            try:
                if kernel:
                    self.business_ops_system = BusinessOperationsSystem(kernel)
                    if self.business_ops_system.initialize_departments():
                        logger.info("BusinessDev and Operations system initialized successfully")
                    else:
                        logger.warning("BusinessDev and Operations system initialization failed")
                else:
                    logger.warning("BusinessDev and Operations system skipped - no kernel")
            except Exception as e:
                logger.warning(f"BusinessDev and Operations system initialization failed: {e}")
                
        except Exception as e:
            logger.error(f"System initialization error: {e}")
            raise
    
    async def _startup_sync(self):
        """Perform startup memory sync"""
        try:
            logger.info("🔄 Starting memory sync...")
            # Skip memory sync if not configured
            if Config.is_memory_enabled():
                memory_sync = GoogleDriveMemorySync()
                await memory_sync.sync_all_to_local()
                logger.info("✅ Memory sync completed")
            else:
                logger.info("⏭️ Memory sync skipped (not enabled)")
        except Exception as e:
            logger.warning(f"Memory sync failed: {e}")
    
    def _init_kernel(self):
        """Initialize Semantic Kernel"""
        try:
            kernel = sk.Kernel()
            
            # Get Azure OpenAI configuration
            config = Config.get_azure_config()
            
            if config.get("api_key") and config.get("endpoint"):
                # Add Azure OpenAI chat completion service
                kernel.add_service(AzureChatCompletion(
                    service_id="default",
                    api_key=config["api_key"],
                    endpoint=config["endpoint"],
                    deployment_name=config.get("deployment_name", "gpt-4")
                ))
                logger.info("Azure OpenAI service added to kernel")
            else:
                logger.warning("Azure OpenAI configuration not found")
            
            return kernel
            
        except Exception as e:
            logger.error(f"Kernel initialization error: {e}")
            return None
    
    def display_welcome(self):
        """Display welcome message"""
        print("\n" + "="*70)
        print("🏢 BUSINESS DEVELOPMENT & OPERATIONS MULTI-AGENT SYSTEM")
        print("="*70)
        print("| 🔐 Secure Authentication: Supabase-powered")
        print("| 🤝 BusinessDev: IPM, BDM, Presales")
        print("| 🔧 Operations: Client Success, Delivery, Legal, Reporting")
        print("| 🌐 Multi-Language: English, Bulgarian, Hungarian")
        print("| 🧠 Memory Access Control: Role-based permissions")
        print("="*70)
        print("\n🔑 AUTHENTICATION REQUIRED")
        print("   Please login or register to access the system")
    
    def display_authentication_menu(self):
        """Display authentication options"""
        print("\n" + "="*50)
        print("🔐 BUSINESSDEV & OPERATIONS - AUTHENTICATION")
        print("="*50)
        print("1. 🔑 Login")
        print("2. 📝 Register New Account")
        print("3. 📋 View Available Roles")
        print("4. ❌ Exit")
        print("="*50)
    
    def display_available_roles(self):
        """Display available roles for BusinessDev and Operations"""
        print("\n" + "="*60)
        print("📋 AVAILABLE ROLES - BUSINESSDEV & OPERATIONS")
        print("="*60)
        
        print("\n🏢 BUSINESS DEVELOPMENT ROLES:")
        print("   • Business Development Manager - Strategic partnership oversight")
        print("   • IPM Agent - International Partnerships Manager")
        print("   • BDM Agent - Business Development Management")
        print("   • Presales Engineer Agent - Technical solution design")
        
        print("\n🔧 OPERATIONS ROLES:")
        print("   • Operations Manager - Overall operations oversight")
        print("   • Head of Operations Agent - Strategic operations management")
        print("   • Senior CSM Agent - Enterprise customer success")
        print("   • Senior Delivery Consultant Agent - Complex project delivery")
        print("   • Delivery Consultant BG Agent - Bulgarian market specialist")
        print("   • Delivery Consultant HU Agent - Hungarian market specialist")
        print("   • Delivery Consultant EN Agent - International market specialist")
        print("   • Reporting Manager Agent - BI strategy and management")
        print("   • Reporting Specialist Agent - Technical reporting development")
        print("   • Legal Agent - Legal compliance and contract management")
        
        print("\n💡 ROLE FEATURES:")
        print("   • Each role has access to specialized agents and tools")
        print("   • Memory access is controlled by role and department")
        print("   • Multi-language support for delivery consulting")
        print("   • Cross-department collaboration capabilities")
        print("="*60)
    
    async def authentication_menu(self):
        """Handle authentication menu"""
        while True:
            self.display_authentication_menu()
            choice = input("\n[INPUT] Select option (1-4): ").strip()
            
            if choice == '1':
                return await self.login_process()
            elif choice == '2':
                success = await self.register_user()
                if success:
                    print("\n[SUCCESS] Registration completed! Please login with your new account.")
                    continue
                else:
                    print("\n[ERROR] Registration failed. Please try again.")
                    continue
            elif choice == '3':
                self.display_available_roles()
                input("\n[PRESS] Press Enter to continue...")
                continue
            elif choice == '4':
                print("\n[EXIT] Goodbye!")
                return None
            else:
                print("\n[ERROR] Invalid option. Please select 1-4.")
                continue
    
    async def login_process(self):
        """Handle login process"""
        print("\n" + "="*40)
        print("🔑 LOGIN - BUSINESSDEV & OPERATIONS")
        print("="*40)
        
        email = input("📧 Email: ").strip()
        if not email:
            print("[ERROR] Email is required")
            return None
        
        import getpass
        password = getpass.getpass("🔐 Password: ")
        if not password:
            print("[ERROR] Password is required")
            return None
        
        try:
            user = await self.auth_manager.login(email, password)
            
            if user:
                # Check if user has BusinessDev or Operations role
                valid_roles = [
                    UserRole.BUSINESS_DEV_MANAGER, UserRole.IPM_AGENT, UserRole.BDM_AGENT, 
                    UserRole.PRESALES_ENGINEER_AGENT,
                    UserRole.OPERATIONS_MANAGER, UserRole.HEAD_OF_OPERATIONS_AGENT, UserRole.SENIOR_CSM_AGENT,
                    UserRole.SENIOR_DELIVERY_CONSULTANT_AGENT, UserRole.DELIVERY_CONSULTANT_BG_AGENT,
                    UserRole.DELIVERY_CONSULTANT_HU_AGENT, UserRole.DELIVERY_CONSULTANT_EN_AGENT,
                    UserRole.REPORTING_MANAGER_AGENT, UserRole.REPORTING_SPECIALIST_AGENT, UserRole.LEGAL_AGENT
                ]
                
                if user.role not in valid_roles:
                    print(f"\n[ERROR] Access denied. Your role '{user.role.value}' is not authorized for this system.")
                    print("[INFO] This system is for BusinessDev and Operations roles only.")
                    self.auth_manager.logout()
                    return None
                
                # Initialize access controllers
                self.access_controller = AccessController(self.auth_manager)
                self.memory_controller = MemoryAccessController(self.access_controller)
                
                print(f"\n[SUCCESS] Login successful!")
                print(f"User: {user.username}")
                print(f"Role: {user.role.value}")
                print(f"Department: {'BusinessDev' if 'BUSINESS' in user.role.value.upper() else 'Operations'}")
                
                return user
            else:
                print(f"[ERROR] Login failed. Invalid email or password.")
                return None
                
        except Exception as e:
            print(f"[ERROR] Login error: {str(e)}")
            logger.error(f"Login error for {email}: {e}")
            return None
    
    async def register_user(self):
        """Handle user registration"""
        print("\n" + "="*50)
        print("📝 REGISTER - BUSINESSDEV & OPERATIONS")
        print("="*50)
        
        email = input("📧 Email: ").strip()
        username = input("👤 Username: ").strip()
        
        import getpass
        password = getpass.getpass("🔐 Password: ")
        confirm_password = getpass.getpass("🔐 Confirm Password: ")
        
        if password != confirm_password:
            print("[ERROR] Passwords do not match")
            return False
        
        # Role selection for BusinessDev and Operations
        role = await self._select_business_operations_role()
        if not role:
            return False
        
        try:
            success = await self.auth_manager.register_user(email, password, username, role)
            return success
        except Exception as e:
            print(f"[ERROR] Registration error: {str(e)}")
            return False
    
    async def _select_business_operations_role(self):
        """Select role for BusinessDev and Operations"""
        print("\n🎭 SELECT YOUR ROLE:")
        print("="*40)
        
        # Import centralized role categories
        from Auth.User_management.role_constants import get_roles_by_category
        
        # Get roles from centralized categories
        businessdev_role_names = get_roles_by_category('business_dev') + ['business_dev_manager']
        operations_role_names = get_roles_by_category('operations') + ['operations_manager'] + get_roles_by_category('legal')
        
        # Convert to UserRole enums
        businessdev_roles = []
        operations_roles = []
        
        # Find matching UserRole enum members
        for role_name in businessdev_role_names:
            try:
                role_enum = UserRole(role_name)
                businessdev_roles.append(role_enum)
            except ValueError:
                pass
                
        for role_name in operations_role_names:
            try:
                role_enum = UserRole(role_name)
                operations_roles.append(role_enum)
            except ValueError:
                pass
        
        print("\n🏢 BUSINESS DEVELOPMENT ROLES:")
        for i, role in enumerate(businessdev_roles, 1):
            print(f"   {i}. {role.value.replace('_', ' ').title()}")
        
        print(f"\n🔧 OPERATIONS ROLES:")
        for i, role in enumerate(operations_roles, len(businessdev_roles) + 1):
            print(f"   {i}. {role.value.replace('_', ' ').title()}")
        
        all_roles = businessdev_roles + operations_roles
        
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
    
    async def start_chat_session(self, user_account):
        """Start role-specific chat session"""
        if self.business_ops_system and self.business_ops_system.is_initialized():
            try:
                self.current_chat_interface = RoleBasedBusinessOperationsInterface(
                    user_account, 
                    self.business_ops_system, 
                    self.memory_controller
                )
                print(f"[SUCCESS] Connected to BusinessDev/Operations system for {user_account.role.value}")
                
                if hasattr(self.current_chat_interface, 'agent') and self.current_chat_interface.agent:
                    print(f"[AGENT] Connected to: {self.current_chat_interface.agent.name}")
                else:
                    print(f"[WARNING] Agent not found for role {user_account.role.value}")
                
            except Exception as e:
                print(f"[ERROR] Failed to connect to agent: {e}")
                return
        else:
            print(f"[ERROR] BusinessDev/Operations system not available")
            return
        
        # Display role-specific welcome
        await self.display_role_welcome(user_account)
        
        # Start chat loop
        await self.chat_loop(user_account)
    
    async def display_role_welcome(self, user_account):
        """Display role-specific welcome message"""
        department = 'BusinessDev' if 'BUSINESS' in user_account.role.value.upper() else 'Operations'
        
        print("\n" + "="*60)
        print(f"🎯 {user_account.role.value.replace('_', ' ').title().upper()} DASHBOARD")
        print("="*60)
        print(f"👤 User: {user_account.username}")
        print(f"🎭 Role: {user_account.role.value.replace('_', ' ').title()}")
        print(f"🏢 Department: {department}")
        
        if department == 'BusinessDev':
            print(f"\n🤝 BUSINESS DEVELOPMENT CAPABILITIES:")
            print(f"   • Partnership development and management")
            print(f"   • Project management and coordination")
            print(f"   • Presales engineering and solution design")
        else:
            print(f"\n🔧 OPERATIONS CAPABILITIES:")
            print(f"   • Client success and relationship management")
            print(f"   • Multi-language delivery consulting (EN/BG/HU)")
            print(f"   • Custom reporting and business intelligence")
            print(f"   • Legal compliance and contract management")
        
        print(f"\n💡 SYSTEM FEATURES:")
        print(f"   • Type your requests in natural language")
        print(f"   • Access specialized knowledge and memory")
        print(f"   • Collaborate across departments")
        print(f"   • Use commands: WHOAMI, MEMORY, AGENTS, HELP")
        print("="*60)
    
    async def chat_loop(self, user_account):
        """Main chat interaction loop"""
        try:
            while True:
                user_input = input(f"\n[{user_account.role.value.upper()}]> ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'logout']:
                    print(f"[LOGOUT] Goodbye, {user_account.username}!")
                    self.auth_manager.logout()
                    break
                
                if not user_input:
                    continue
                
                try:
                    response = await self.current_chat_interface.process_input(user_input)
                    print(f"\n{response}")
                    
                except Exception as e:
                    print(f"\n[ERROR] Processing error: {str(e)}")
                    logger.error(f"Chat processing error: {e}")
                    
        except KeyboardInterrupt:
            print(f"\n[INTERRUPT] Goodbye, {user_account.username}!")
            self.auth_manager.logout()
        except Exception as e:
            print(f"\n[ERROR] Chat session error: {str(e)}")
            logger.error(f"Chat session error: {e}")
    
    async def run(self):
        """Main system execution"""
        try:
            await self.initialize()
            
            self.display_welcome()
            self.running = True
            
            while self.running:
                try:
                    # Login process
                    user_account = await self.authentication_menu()
                    
                    if not user_account:
                        print("\n[EXIT] System shutdown requested")
                        break
                    
                    # Start role-specific chat session
                    await self.start_chat_session(user_account)
            
                except KeyboardInterrupt:
                    print("\n[INTERRUPT] Use 'quit' during login to exit")
                    continue
                    
        except Exception as e:
            logger.error(f"System error: {str(e)}")
            print(f"\n[ERROR] System error: {str(e)}")
        finally:
            print("\n[SHUTDOWN] BusinessDev & Operations system shutdown complete")


async def main():
    """Main entry point"""
    system = RoleBasedBusinessOperationsSystem()
    await system.run()


if __name__ == "__main__":
    asyncio.run(main()) 