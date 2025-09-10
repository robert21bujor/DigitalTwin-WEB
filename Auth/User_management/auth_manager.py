"""
Authentication Manager for Supabase Integration
"""

import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from supabase import create_client, Client
from gotrue.errors import AuthApiError

from .user_models import User, UserRole, AgentType, AgentAssignment
from Utils.config import Config

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages user authentication and authorization using Supabase"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.current_user: Optional[User] = None
        self.session_token: Optional[str] = None
        self._initialize_supabase()
    
    def _initialize_supabase(self):
        """Initialize Supabase client"""
        try:
            # Get Supabase configuration
            config = Config.get_supabase_config()
            
            supabase_url = config.get("url")
            supabase_key = config.get("key")
            
            if not supabase_url or not supabase_key:
                logger.error("Supabase credentials not found in environment")
                return None
            
            # Create Supabase client
            self.client = create_client(supabase_url, supabase_key)
            
            logger.info("Supabase client initialized successfully")
            return self.client
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            return None
    
    async def register_user(self, email: str, password: str, username: str, role: UserRole) -> bool:
        """Register new user with email and password - manual profile creation"""
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return False
            
            logger.info(f"Starting registration for user: {email}")
            
            # Step 1: Create user in Supabase Auth (without metadata to avoid trigger issues)
            print("🔄 Creating user account...")
            try:
                response = self.client.auth.sign_up({
                    "email": email,
                    "password": password
                })
                print("✅ User account created in Supabase Auth")
                
            except Exception as auth_error:
                logger.error(f"Auth signup failed: {auth_error}")
                print(f"❌ Failed to create user account: {auth_error}")
                return False
            
            if not response.user:
                logger.error("No user object returned from registration")
                print("❌ No user object returned from registration")
                return False
            
            # Step 2: Create proper agent assignments based on role
            print("🔄 Creating agent assignments...")
            agent_assignments = self._get_default_agent_assignments(role)
            
            # Step 3: Create user profile manually
            print("🔄 Creating user profile...")
            try:
                user_data = {
                    'auth_user_id': response.user.id,
                    'email': email,
                    'username': username,
                    'role': role.value,
                    'agent_assignments': agent_assignments,
                    'is_active': True,
                    'metadata': {}
                }
                
                result = self.client.table("user_profiles").insert(user_data).execute()
                
                if result.data and len(result.data) > 0:
                    print("✅ User profile created successfully")
                    print(f"🤖 Agent assignments: {len(agent_assignments)} agents accessible")
                    logger.info(f"User registered successfully: {email} ({role.value})")
                    return True
                else:
                    # Profile creation failed - clean up auth user
                    logger.error(f"Failed to create user profile: {result}")
                    print("❌ Failed to create user profile")
                    
                    # Try to delete the auth user (best effort)
                    try:
                        print("🔄 Cleaning up failed registration...")
                        # Note: We can't delete auth users as regular user, but we log the issue
                        logger.warning(f"Auth user {response.user.id} exists without profile")
                    except Exception as cleanup_error:
                        logger.warning(f"Cleanup warning: {cleanup_error}")
                    
                    return False
                        
            except Exception as db_error:
                logger.error(f"Database error during profile creation: {db_error}")
                print(f"❌ Database error: {db_error}")
                
                # Try to clean up the auth user
                try:
                    print("🔄 Cleaning up failed registration...")
                    logger.warning(f"Auth user {response.user.id} exists without profile due to: {db_error}")
                except Exception as cleanup_error:
                    logger.warning(f"Cleanup warning: {cleanup_error}")
                
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error during registration: {e}")
            print(f"❌ Registration error: {e}")
            return False
    
    def _get_default_agent_assignments(self, role: UserRole) -> List[Dict[str, Any]]:
        """Get default agent assignments based on user role for database storage"""
        from datetime import datetime
        
        # All public memories that everyone can READ
        all_public_memories = [
            'executive-shared-memory',
            'digital-shared-memory',
            'product-shared-memory',
            'content-shared-memory'
        ]
        
        # Base agent assignments - everyone gets READ access to all public memories
        base_assignments = [
            {
                'agent_type': 'cmo',
                'access_level': 'full',
                'memory_read_access': all_public_memories.copy(),
                'memory_write_access': [],  # Will be populated based on role
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'system'
            },
            {
                'agent_type': 'positioning',
                'access_level': 'full',
                'memory_read_access': all_public_memories.copy(),
                'memory_write_access': [],
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'system'
            },
            {
                'agent_type': 'persona',
                'access_level': 'full',
                'memory_read_access': all_public_memories.copy(),
                'memory_write_access': [],
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'system'
            },
            {
                'agent_type': 'gtm',
                'access_level': 'full',
                'memory_read_access': all_public_memories.copy(),
                'memory_write_access': [],
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'system'
            },
            {
                'agent_type': 'competitor',
                'access_level': 'full',
                'memory_read_access': all_public_memories.copy(),
                'memory_write_access': [],
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'system'
            },
            {
                'agent_type': 'launch',
                'access_level': 'full',
                'memory_read_access': all_public_memories.copy(),
                'memory_write_access': [],
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'system'
            },
            {
                'agent_type': 'seo',
                'access_level': 'full',
                'memory_read_access': all_public_memories.copy(),
                'memory_write_access': [],
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'system'
            },
            {
                'agent_type': 'sem',
                'access_level': 'full',
                'memory_read_access': all_public_memories.copy(),
                'memory_write_access': [],
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'system'
            },
            {
                'agent_type': 'landing',
                'access_level': 'full',
                'memory_read_access': all_public_memories.copy(),
                'memory_write_access': [],
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'system'
            },
            {
                'agent_type': 'analytics',
                'access_level': 'full',
                'memory_read_access': all_public_memories.copy(),
                'memory_write_access': [],
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'system'
            },
            {
                'agent_type': 'funnel',
                'access_level': 'full',
                'memory_read_access': all_public_memories.copy(),
                'memory_write_access': [],
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'system'
            },
            {
                'agent_type': 'content',
                'access_level': 'full',
                'memory_read_access': all_public_memories.copy(),
                'memory_write_access': [],
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'system'
            },
            {
                'agent_type': 'brand',
                'access_level': 'full',
                'memory_read_access': all_public_memories.copy(),
                'memory_write_access': [],
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'system'
            },
            {
                'agent_type': 'social',
                'access_level': 'full',
                'memory_read_access': all_public_memories.copy(),
                'memory_write_access': [],
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'system'
            },
            {
                'agent_type': 'community',
                'access_level': 'full',
                'memory_read_access': all_public_memories.copy(),
                'memory_write_access': [],
                'assigned_at': datetime.now().isoformat(),
                'assigned_by': 'system'
            }
        ]
        
        # Role-specific write permissions and private memory access
        if role == UserRole.CMO:
            # CMO gets WRITE access to CMO public memory + READ/WRITE to CMO private memory
            for assignment in base_assignments:
                if assignment['agent_type'] == 'cmo':
                    assignment['memory_write_access'].append('cmo-public-memory')
                    assignment['memory_read_access'].append('cmo-private-memory')
                    assignment['memory_write_access'].append('cmo-private-memory')
                    break
        
        elif role == UserRole.PRODUCT_MANAGER:
            # Product Manager gets WRITE access to product public memories ONLY (NO private access)
            for assignment in base_assignments:
                if assignment['agent_type'] in ['positioning', 'persona', 'gtm']:
                    # Write access to public memory only
                    assignment['memory_write_access'].append(f"{assignment['agent_type']}-public-memory")
        
        elif role == UserRole.DIGITAL_MANAGER:
            # Digital Manager gets WRITE access to digital public memories ONLY (NO private access)
            for assignment in base_assignments:
                if assignment['agent_type'] in ['seo', 'sem', 'landing', 'analytics', 'funnel']:
                    assignment['memory_write_access'].append(f"{assignment['agent_type']}-public-memory")
        
        elif role == UserRole.CONTENT_MANAGER:
            # Content Manager gets WRITE access to content public memories ONLY (NO private access)
            for assignment in base_assignments:
                if assignment['agent_type'] in ['content', 'brand', 'social', 'community']:
                    assignment['memory_write_access'].append(f"{assignment['agent_type']}-public-memory")
        
        # Individual agent roles get WRITE access to their own public memory + READ/WRITE to their private memory
        elif role == UserRole.POSITIONING_AGENT:
            for assignment in base_assignments:
                if assignment['agent_type'] == 'positioning':
                    assignment['memory_write_access'].append('positioning-public-memory')
                    assignment['memory_read_access'].append('positioning-private-memory')
                    assignment['memory_write_access'].append('positioning-private-memory')
                    break
        
        elif role == UserRole.PERSONA_AGENT:
            for assignment in base_assignments:
                if assignment['agent_type'] == 'persona':
                    assignment['memory_write_access'].append('persona-public-memory')
                    assignment['memory_read_access'].append('persona-private-memory')
                    assignment['memory_write_access'].append('persona-private-memory')
                    break
        
        elif role == UserRole.GTM_AGENT:
            for assignment in base_assignments:
                if assignment['agent_type'] == 'gtm':
                    assignment['memory_write_access'].append('gtm-public-memory')
                    assignment['memory_read_access'].append('gtm-private-memory')
                    assignment['memory_write_access'].append('gtm-private-memory')
                    break
        
        elif role == UserRole.COMPETITOR_AGENT:
            for assignment in base_assignments:
                if assignment['agent_type'] == 'competitor':
                    assignment['memory_write_access'].append('competitor-public-memory')
                    assignment['memory_read_access'].append('competitor-private-memory')
                    assignment['memory_write_access'].append('competitor-private-memory')
                    break
        
        elif role == UserRole.LAUNCH_AGENT:
            for assignment in base_assignments:
                if assignment['agent_type'] == 'launch':
                    assignment['memory_write_access'].append('launch-public-memory')
                    assignment['memory_read_access'].append('launch-private-memory')
                    assignment['memory_write_access'].append('launch-private-memory')
                    break
        
        elif role == UserRole.SEO_AGENT:
            for assignment in base_assignments:
                if assignment['agent_type'] == 'seo':
                    assignment['memory_write_access'].append('seo-public-memory')
                    assignment['memory_read_access'].append('seo-private-memory')
                    assignment['memory_write_access'].append('seo-private-memory')
                    break
        
        elif role == UserRole.SEM_AGENT:
            for assignment in base_assignments:
                if assignment['agent_type'] == 'sem':
                    assignment['memory_write_access'].append('sem-public-memory')
                    assignment['memory_read_access'].append('sem-private-memory')
                    assignment['memory_write_access'].append('sem-private-memory')
                    break
        
        elif role == UserRole.LANDING_AGENT:
            for assignment in base_assignments:
                if assignment['agent_type'] == 'landing':
                    assignment['memory_write_access'].append('landing-public-memory')
                    assignment['memory_read_access'].append('landing-private-memory')
                    assignment['memory_write_access'].append('landing-private-memory')
                    break
        
        elif role == UserRole.ANALYTICS_AGENT:
            for assignment in base_assignments:
                if assignment['agent_type'] == 'analytics':
                    assignment['memory_write_access'].append('analytics-public-memory')
                    assignment['memory_read_access'].append('analytics-private-memory')
                    assignment['memory_write_access'].append('analytics-private-memory')
                    break
        
        elif role == UserRole.FUNNEL_AGENT:
            for assignment in base_assignments:
                if assignment['agent_type'] == 'funnel':
                    assignment['memory_write_access'].append('funnel-public-memory')
                    assignment['memory_read_access'].append('funnel-private-memory')
                    assignment['memory_write_access'].append('funnel-private-memory')
                    break
        
        elif role == UserRole.CONTENT_AGENT:
            for assignment in base_assignments:
                if assignment['agent_type'] == 'content':
                    assignment['memory_write_access'].append('content-public-memory')
                    assignment['memory_read_access'].append('content-private-memory')
                    assignment['memory_write_access'].append('content-private-memory')
                    break
        
        elif role == UserRole.BRAND_AGENT:
            for assignment in base_assignments:
                if assignment['agent_type'] == 'brand':
                    assignment['memory_write_access'].append('brand-public-memory')
                    assignment['memory_read_access'].append('brand-private-memory')
                    assignment['memory_write_access'].append('brand-private-memory')
                    break
        
        elif role == UserRole.SOCIAL_AGENT:
            for assignment in base_assignments:
                if assignment['agent_type'] == 'social':
                    assignment['memory_write_access'].append('social-public-memory')
                    assignment['memory_read_access'].append('social-private-memory')
                    assignment['memory_write_access'].append('social-private-memory')
                    break
        
        elif role == UserRole.COMMUNITY_AGENT:
            for assignment in base_assignments:
                if assignment['agent_type'] == 'community':
                    assignment['memory_write_access'].append('community-public-memory')
                    assignment['memory_read_access'].append('community-private-memory')
                    assignment['memory_write_access'].append('community-private-memory')
                    break
        
        # Maintain backward compatibility with old memory_access field
        for assignment in base_assignments:
            assignment['memory_access'] = list(set(assignment['memory_read_access'] + assignment['memory_write_access']))
        
        return base_assignments
    

    
    async def login(self, email: str, password: str) -> Optional[User]:
        """Authenticate user and return user object"""
        try:
            if not self.client:
                logger.error("Supabase client not initialized")
                return None
            
            # Sign in with Supabase
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user and response.session:
                # Get user profile from database using auth_user_id
                try:
                    result = self.client.table("user_profiles").select("*").eq("auth_user_id", response.user.id).execute()
                    
                    if result.data and len(result.data) > 0:
                        user_data = result.data[0]
                        
                        # Map database fields to User model
                        user_dict = {
                            'id': user_data['id'],  # Use id from database
                            'email': user_data['email'],
                            'username': user_data['username'],
                            'role': user_data['role'],
                            'agent_assignments': user_data.get('agent_assignments', []),
                            'created_at': user_data['created_at'],
                            'updated_at': user_data['updated_at'],
                            'is_active': user_data['is_active'],
                            'metadata': user_data.get('metadata', {})
                        }
                        
                        user = User.from_dict(user_dict)
                        
                        # Set current user and session
                        self.current_user = user
                        self.session_token = response.session.access_token
                        
                        logger.info(f"User '{user.username}' logged in successfully as {user.role.value}")
                        return user
                    else:
                        logger.error("User profile not found in database")
                        return None
                        
                except Exception as db_error:
                    logger.error(f"Database error during login: {db_error}")
                    return None
                    
            else:
                logger.warning(f"Invalid credentials for email: {email}")
                return None
                
        except AuthApiError as e:
            logger.error(f"Authentication error during login: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            return None
    
    def logout(self):
        """Logout current user"""
        try:
            if self.client and self.current_user:
                self.client.auth.sign_out()
                logger.info(f"User '{self.current_user.username}' logged out")
            
            self.current_user = None
            self.session_token = None
            
        except Exception as e:
            logger.error(f"Error during logout: {e}")
    
    def get_current_user(self) -> Optional[User]:
        """Get currently authenticated user"""
        return self.current_user
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        return self.current_user is not None
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            if not self.client:
                return None
            
            result = self.client.table("user_profiles").select("*").eq("username", username).execute()
            
            if result.data and len(result.data) > 0:
                user_data = result.data[0]
                # Map database fields to User model
                user_dict = {
                    'id': user_data['user_id'],  # Map user_id to id for User model
                    'email': user_data['email'],
                    'username': user_data['username'],
                    'role': user_data['role'],
                    'agent_assignments': user_data.get('agent_assignments', []),
                    'created_at': user_data['created_at'],
                    'updated_at': user_data['updated_at'],
                    'is_active': user_data['is_active'],
                    'metadata': user_data.get('metadata', {})
                }
                return User.from_dict(user_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by user ID"""
        try:
            if not self.client:
                return None
            
            result = self.client.table("user_profiles").select("*").eq("id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                user_data = result.data[0]
                # Map database fields to User model
                user_dict = {
                    'id': user_data['id'],  # Use id from database
                    'email': user_data['email'],
                    'username': user_data['username'],
                    'role': user_data['role'],
                    'agent_assignments': user_data.get('agent_assignments', []),
                    'created_at': user_data['created_at'],
                    'updated_at': user_data['updated_at'],
                    'is_active': user_data['is_active'],
                    'metadata': user_data.get('metadata', {})
                }
                return User.from_dict(user_dict)
            
            return None
                
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            if not self.client:
                return None
            
            result = self.client.table("user_profiles").select("*").eq("email", email).execute()
            
            if result.data and len(result.data) > 0:
                user_data = result.data[0]
                # Map database fields to User model
                user_dict = {
                    'id': user_data['user_id'],  # Map user_id to id for User model
                    'email': user_data['email'],
                    'username': user_data['username'],
                    'role': user_data['role'],
                    'agent_assignments': user_data.get('agent_assignments', []),
                    'created_at': user_data['created_at'],
                    'updated_at': user_data['updated_at'],
                    'is_active': user_data['is_active'],
                    'metadata': user_data.get('metadata', {})
                }
                return User.from_dict(user_dict)
            
            return None
                
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None
    
    async def update_user_agent_assignments(self, user_id: str, assignments: List[AgentAssignment]) -> bool:
        """Update user's agent assignments (admin function)"""
        try:
            if not self.client:
                return False
            
            # Check if current user has permission to update assignments
            if not self.current_user or not self.current_user.is_cmo():
                logger.warning("Insufficient permissions to update agent assignments")
                return False
            
            # Get current user data
            user = await self.get_user_by_id(user_id)
            if not user:
                logger.error(f"User not found: {user_id}")
                return False
            
            # Prepare update data
            update_data = {
                'agent_assignments': [
                    {
                        'agent_type': a.agent_type.value,
                        'access_level': a.access_level,
                        'memory_access': a.memory_access,
                        'assigned_at': a.assigned_at.isoformat(),
                        'assigned_by': a.assigned_by
                    }
                    for a in assignments
                ],
                'updated_at': datetime.now().isoformat()
            }
            
            # Save to database using id
            result = self.client.table("user_profiles").update(update_data).eq("id", user_id).execute()
            
            if result.data:
                logger.info(f"Agent assignments updated for user: {user_id}")
                return True
            else:
                logger.error("Failed to update agent assignments in database")
                return False
                
        except Exception as e:
            logger.error(f"Error updating agent assignments: {e}")
            return False
    
    async def add_agent_assignment(self, user_id: str, agent_type: AgentType, 
                                 access_level: str = 'full') -> bool:
        """Add agent assignment to user"""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False
            
            # Create memory access based on agent type
            memory_access = self._get_agent_memory_collections(agent_type, access_level)
            
            # Create new assignment
            assignment = AgentAssignment(
                agent_type=agent_type,
                access_level=access_level,
                memory_access=memory_access,
                assigned_by=self.current_user.id if self.current_user else 'system'
            )
            
            # Add assignment to user
            user.add_agent_assignment(assignment)
            
            # Update in database
            return await self.update_user_agent_assignments(user_id, user.agent_assignments)
            
        except Exception as e:
            logger.error(f"Error adding agent assignment: {e}")
            return False
    
    def _get_agent_memory_collections(self, agent_type: AgentType, access_level: str) -> List[str]:
        """Get memory collections based on agent type and access level"""
        base_collections = ['global-shared-memory']
        
        if agent_type == AgentType.CMO:
            if access_level == 'full':
                return base_collections + [
                    'cmo-private-memory',
                    'cmo-strategic-memory',
                    'executive-private-memory'
                ]
            else:
                return base_collections + ['cmo-strategic-memory']
        
        elif agent_type == AgentType.POSITIONING:
            if access_level == 'full':
                return base_collections + [
                    'positioning-private-memory',
                    'product-marketing-shared-memory'
                ]
            else:
                return base_collections + ['product-marketing-shared-memory']
        
        elif agent_type == AgentType.SEO:
            if access_level == 'full':
                return base_collections + [
                    'seo-private-memory',
                    'digital-marketing-shared-memory'
                ]
            else:
                return base_collections + ['digital-marketing-shared-memory']
        
        elif agent_type == AgentType.CONTENT:
            if access_level == 'full':
                return base_collections + [
                    'content-private-memory',
                    'content-marketing-shared-memory'
                ]
            else:
                return base_collections + ['content-marketing-shared-memory']
        
        else:
            # Default for other agents
            agent_name = agent_type.value
            if access_level == 'full':
                return base_collections + [f'{agent_name}-private-memory']
            else:
                return base_collections
    
    async def list_users(self) -> List[User]:
        """List all users (admin function)"""
        try:
            if not self.client:
                return []
            
            # Check if current user has permission to list users
            if not self.current_user or not self.current_user.is_cmo():
                logger.warning("Insufficient permissions to list users")
                return []
            
            result = self.client.table("user_profiles").select("*").execute()
            
            if result.data:
                users = []
                for user_data in result.data:
                    # Map database fields to User model
                    user_dict = {
                        'id': user_data['user_id'],  # Map user_id to id for User model
                        'email': user_data['email'],
                        'username': user_data['username'],
                        'role': user_data['role'],
                        'agent_assignments': user_data.get('agent_assignments', []),
                        'created_at': user_data['created_at'],
                        'updated_at': user_data['updated_at'],
                        'is_active': user_data['is_active'],
                        'metadata': user_data.get('metadata', {})
                    }
                    users.append(User.from_dict(user_dict))
                return users
            
            return []
            
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user (admin function)"""
        try:
            if not self.client:
                return False
            
            # Check if current user has permission to deactivate users
            if not self.current_user or not self.current_user.is_cmo():
                logger.warning("Insufficient permissions to deactivate users")
                return False
            
            # Check if user exists
            user = await self.get_user_by_id(user_id)
            if not user:
                logger.error(f"User not found: {user_id}")
                return False
            
            # Update user status using id
            result = self.client.table("user_profiles").update({
                'is_active': False,
                'updated_at': datetime.now().isoformat()
            }).eq("id", user_id).execute()
            
            if result.data:
                logger.info(f"User deactivated: {user_id}")
                return True
            else:
                logger.error("Failed to deactivate user in database")
                return False
                
        except Exception as e:
            logger.error(f"Error deactivating user: {e}")
            return False
    
    def validate_agent_access(self, agent_type: AgentType) -> bool:
        """Validate if current user has access to specified agent"""
        if not self.current_user:
            return False
        
        return self.current_user.has_agent_access(agent_type)
    
    def validate_memory_access(self, collection_name: str) -> bool:
        """Validate if current user has access to specified memory collection"""
        if not self.current_user:
            return False
        
        return self.current_user.has_memory_access(collection_name)
    
    def get_accessible_agents(self) -> List[AgentType]:
        """Get list of agents current user can access"""
        if not self.current_user:
            return []
        
        return self.current_user.get_accessible_agents()
    
    def get_accessible_memory_collections(self) -> List[str]:
        """Get list of memory collections current user can access"""
        if not self.current_user:
            return []
        
        return self.current_user.get_accessible_memory_collections() 