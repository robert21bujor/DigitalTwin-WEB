"""
User models for Supabase authentication with role-based access control
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid

# Import centralized role constants
from .role_constants import COMPANY_ROLES


class UserRole(Enum):
    """User roles in the system - centralized enum definition"""
    # No specific role
    NONE = "none"
    
    # Leadership Roles
    CMO = "cmo"
    CEO = "ceo"
    CTO = "cto"
    CFO = "cfo"
    
    # Management Roles
    PRODUCT_MANAGER = "product_manager"
    DIGITAL_MANAGER = "digital_manager"
    CONTENT_MANAGER = "content_manager"
    BUSINESS_DEV_MANAGER = "business_dev_manager"
    OPERATIONS_MANAGER = "operations_manager"
    
    # Marketing Department Agents
    POSITIONING_AGENT = "positioning_agent"
    PERSONA_AGENT = "persona_agent"
    GTM_AGENT = "gtm_agent"
    COMPETITOR_AGENT = "competitor_agent"
    LAUNCH_AGENT = "launch_agent"
    SEO_AGENT = "seo_agent"
    SEM_AGENT = "sem_agent"
    LANDING_AGENT = "landing_agent"
    ANALYTICS_AGENT = "analytics_agent"
    FUNNEL_AGENT = "funnel_agent"
    CONTENT_AGENT = "content_agent"
    BRAND_AGENT = "brand_agent"
    SOCIAL_AGENT = "social_agent"
    COMMUNITY_AGENT = "community_agent"
    
    # Business Development Agents
    IPM_AGENT = "ipm_agent"
    BDM_AGENT = "bdm_agent"
    PRESALES_ENGINEER_AGENT = "presales_engineer_agent"
    ADVISORY_BOARD_MANAGER_AGENT = "advisory_board_manager_agent"
    
    # Operations Department Agents
    HEAD_OF_OPERATIONS_AGENT = "head_of_operations_agent"
    SENIOR_CSM_AGENT = "senior_csm_agent"
    SENIOR_DELIVERY_CONSULTANT_AGENT = "senior_delivery_consultant_agent"
    DELIVERY_CONSULTANT_BG_AGENT = "delivery_consultant_bg_agent"
    DELIVERY_CONSULTANT_HU_AGENT = "delivery_consultant_hu_agent"
    DELIVERY_CONSULTANT_EN_AGENT = "delivery_consultant_en_agent"
    REPORTING_MANAGER_AGENT = "reporting_manager_agent"
    REPORTING_SPECIALIST_AGENT = "reporting_specialist_agent"
    
    # Legal & Compliance
    LEGAL_AGENT = "legal_agent"
    
    # General Employee Roles
    EMPLOYEE = "employee"
    CONTRACTOR = "contractor"
    INTERN = "intern"


class AgentType(Enum):
    """Agent types in the system"""
    CMO = "cmo"
    POSITIONING = "positioning"
    PERSONA = "persona"
    GTM = "gtm"
    COMPETITOR = "competitor"
    LAUNCH = "launch"
    SEO = "seo"
    SEM = "sem"
    LANDING = "landing"
    ANALYTICS = "analytics"
    FUNNEL = "funnel"
    CONTENT = "content"
    BRAND = "brand"
    SOCIAL = "social"
    COMMUNITY = "community"
    
    # BusinessDev Agent Types
    IPM = "ipm"
    BDM = "bdm"
    PRESALES_ENGINEER = "presales_engineer"
    
    # Operations Agent Types
    HEAD_OF_OPERATIONS = "head_of_operations"
    SENIOR_CSM = "senior_csm"
    SENIOR_DELIVERY_CONSULTANT = "senior_delivery_consultant"
    DELIVERY_CONSULTANT_BG = "delivery_consultant_bg"
    DELIVERY_CONSULTANT_HU = "delivery_consultant_hu"
    DELIVERY_CONSULTANT_EN = "delivery_consultant_en"
    REPORTING_MANAGER = "reporting_manager"
    REPORTING_SPECIALIST = "reporting_specialist"
    LEGAL = "legal"


@dataclass
class AgentAssignment:
    """Represents a user's assignment to an agent"""
    agent_type: AgentType
    access_level: str  # 'full', 'read', 'limited'
    memory_access: List[str] = field(default_factory=list)  # memory collections accessible (deprecated)
    memory_read_access: List[str] = field(default_factory=list)  # memory collections with read access
    memory_write_access: List[str] = field(default_factory=list)  # memory collections with write access
    assigned_at: datetime = field(default_factory=datetime.now)
    assigned_by: Optional[str] = None  # user_id who assigned
    
    def has_memory_access(self, collection_name: str) -> bool:
        """Check if user has any access to specific memory collection"""
        return collection_name in self.memory_read_access or collection_name in self.memory_write_access
    
    def has_memory_read_access(self, collection_name: str) -> bool:
        """Check if user has read access to specific memory collection"""
        return collection_name in self.memory_read_access
    
    def has_memory_write_access(self, collection_name: str) -> bool:
        """Check if user has write access to specific memory collection"""
        return collection_name in self.memory_write_access
    
    def is_full_access(self) -> bool:
        """Check if user has full access to the agent"""
        return self.access_level == 'full'


@dataclass
class User:
    """User model with role-based access control"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: str = ""
    username: str = ""
    role: UserRole = UserRole.POSITIONING_AGENT
    agent_assignments: List[AgentAssignment] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization setup"""
        if not self.agent_assignments:
            self.agent_assignments = self._get_default_assignments()
    
    def _get_default_assignments(self) -> List[AgentAssignment]:
        """Get default agent assignments based on user role"""
        
        # All public memories that everyone can READ
        all_public_memories = [
            'executive-shared-memory',
            'digital-shared-memory',
            'product-shared-memory',
            'content-shared-memory'
        ]
        
        # Base agent assignments - everyone gets READ access to all public memories
        base_assignments = [
            AgentAssignment(
                agent_type=AgentType.CMO,
                access_level='full',
                memory_read_access=all_public_memories.copy(),
                memory_write_access=[],  # Will be populated based on role
                assigned_by='system'
            ),
            AgentAssignment(
                agent_type=AgentType.POSITIONING,
                access_level='full',
                memory_read_access=all_public_memories.copy(),
                memory_write_access=[],
                assigned_by='system'
            ),
            AgentAssignment(
                agent_type=AgentType.PERSONA,
                access_level='full',
                memory_read_access=all_public_memories.copy(),
                memory_write_access=[],
                assigned_by='system'
            ),
            AgentAssignment(
                agent_type=AgentType.GTM,
                access_level='full',
                memory_read_access=all_public_memories.copy(),
                memory_write_access=[],
                assigned_by='system'
            ),
            AgentAssignment(
                agent_type=AgentType.COMPETITOR,
                access_level='full',
                memory_read_access=all_public_memories.copy(),
                memory_write_access=[],
                assigned_by='system'
            ),
            AgentAssignment(
                agent_type=AgentType.LAUNCH,
                access_level='full',
                memory_read_access=all_public_memories.copy(),
                memory_write_access=[],
                assigned_by='system'
            ),
            AgentAssignment(
                agent_type=AgentType.SEO,
                access_level='full',
                memory_read_access=all_public_memories.copy(),
                memory_write_access=[],
                assigned_by='system'
            ),
            AgentAssignment(
                agent_type=AgentType.SEM,
                access_level='full',
                memory_read_access=all_public_memories.copy(),
                memory_write_access=[],
                assigned_by='system'
            ),
            AgentAssignment(
                agent_type=AgentType.LANDING,
                access_level='full',
                memory_read_access=all_public_memories.copy(),
                memory_write_access=[],
                assigned_by='system'
            ),
            AgentAssignment(
                agent_type=AgentType.ANALYTICS,
                access_level='full',
                memory_read_access=all_public_memories.copy(),
                memory_write_access=[],
                assigned_by='system'
            ),
            AgentAssignment(
                agent_type=AgentType.FUNNEL,
                access_level='full',
                memory_read_access=all_public_memories.copy(),
                memory_write_access=[],
                assigned_by='system'
            ),
            AgentAssignment(
                agent_type=AgentType.CONTENT,
                access_level='full',
                memory_read_access=all_public_memories.copy(),
                memory_write_access=[],
                assigned_by='system'
            ),
            AgentAssignment(
                agent_type=AgentType.BRAND,
                access_level='full',
                memory_read_access=all_public_memories.copy(),
                memory_write_access=[],
                assigned_by='system'
            ),
            AgentAssignment(
                agent_type=AgentType.SOCIAL,
                access_level='full',
                memory_read_access=all_public_memories.copy(),
                memory_write_access=[],
                assigned_by='system'
            ),
            AgentAssignment(
                agent_type=AgentType.COMMUNITY,
                access_level='full',
                memory_read_access=all_public_memories.copy(),
                memory_write_access=[],
                assigned_by='system'
            )
        ]
        
        # Role-specific write permissions based on new department structure
        if self.role == UserRole.CMO:
            # CMO gets WRITE access to executive shared memory
            for assignment in base_assignments:
                if assignment.agent_type == AgentType.CMO:
                    assignment.memory_write_access.append('executive-shared-memory')
                    break
        
        elif self.role == UserRole.PRODUCT_MANAGER:
            # Product Manager gets WRITE access to product shared memory
            for assignment in base_assignments:
                if assignment.agent_type in [AgentType.POSITIONING, AgentType.PERSONA, AgentType.GTM, AgentType.COMPETITOR, AgentType.LAUNCH]:
                    assignment.memory_write_access.append('product-shared-memory')
                    break
        
        elif self.role == UserRole.DIGITAL_MANAGER:
            # Digital Manager gets WRITE access to digital shared memory
            for assignment in base_assignments:
                if assignment.agent_type in [AgentType.SEO, AgentType.SEM, AgentType.LANDING, AgentType.ANALYTICS, AgentType.FUNNEL]:
                    assignment.memory_write_access.append('digital-shared-memory')
                    break
        
        elif self.role == UserRole.CONTENT_MANAGER:
            # Content Manager gets WRITE access to content shared memory
            for assignment in base_assignments:
                if assignment.agent_type in [AgentType.CONTENT, AgentType.BRAND, AgentType.SOCIAL, AgentType.COMMUNITY]:
                    assignment.memory_write_access.append('content-shared-memory')
                    break
        
        # Individual agent roles get WRITE access to their department's shared memory
        from .role_constants import get_roles_by_category
        
        # Define role categories
        product_marketing_roles = ['positioning_agent', 'persona_agent', 'gtm_agent', 'competitor_agent', 'launch_agent']
        digital_marketing_roles = ['seo_agent', 'sem_agent', 'landing_agent', 'analytics_agent', 'funnel_agent']
        content_marketing_roles = ['content_agent', 'brand_agent', 'social_agent', 'community_agent']
        
        # Product Marketing agents
        if self.role.value in product_marketing_roles:
            for assignment in base_assignments:
                if assignment.agent_type in [AgentType.POSITIONING, AgentType.PERSONA, AgentType.GTM, AgentType.COMPETITOR, AgentType.LAUNCH]:
                    assignment.memory_write_access.append('product-shared-memory')
                    break
        
        # Digital Marketing agents
        elif self.role.value in digital_marketing_roles:
            for assignment in base_assignments:
                if assignment.agent_type in [AgentType.SEO, AgentType.SEM, AgentType.LANDING, AgentType.ANALYTICS, AgentType.FUNNEL]:
                    assignment.memory_write_access.append('digital-shared-memory')
                    break
        
        # Content Marketing agents  
        elif self.role.value in content_marketing_roles:
            for assignment in base_assignments:
                if assignment.agent_type in [AgentType.CONTENT, AgentType.BRAND, AgentType.SOCIAL, AgentType.COMMUNITY]:
                    assignment.memory_write_access.append('content-shared-memory')
                    break
        
        # Maintain backward compatibility with old memory_access field
        for assignment in base_assignments:
            assignment.memory_access = list(set(assignment.memory_read_access + assignment.memory_write_access))
        
        return base_assignments
    
    def _role_to_agent_type(self) -> AgentType:
        """Convert user role to agent type"""
        role_mapping = {
            UserRole.CMO: AgentType.CMO,
            UserRole.POSITIONING_AGENT: AgentType.POSITIONING,
            UserRole.PERSONA_AGENT: AgentType.PERSONA,
            UserRole.GTM_AGENT: AgentType.GTM,
            UserRole.COMPETITOR_AGENT: AgentType.COMPETITOR,
            UserRole.LAUNCH_AGENT: AgentType.LAUNCH,
            UserRole.SEO_AGENT: AgentType.SEO,
            UserRole.SEM_AGENT: AgentType.SEM,
            UserRole.LANDING_AGENT: AgentType.LANDING,
            UserRole.ANALYTICS_AGENT: AgentType.ANALYTICS,
            UserRole.FUNNEL_AGENT: AgentType.FUNNEL,
            UserRole.CONTENT_AGENT: AgentType.CONTENT,
            UserRole.BRAND_AGENT: AgentType.BRAND,
            UserRole.SOCIAL_AGENT: AgentType.SOCIAL,
            UserRole.COMMUNITY_AGENT: AgentType.COMMUNITY,
            
            # BusinessDev roles
            UserRole.IPM_AGENT: AgentType.IPM,
            UserRole.BDM_AGENT: AgentType.BDM,
            UserRole.PRESALES_ENGINEER_AGENT: AgentType.PRESALES_ENGINEER,
            
            # Operations roles
            UserRole.HEAD_OF_OPERATIONS_AGENT: AgentType.HEAD_OF_OPERATIONS,
            UserRole.SENIOR_CSM_AGENT: AgentType.SENIOR_CSM,
            UserRole.SENIOR_DELIVERY_CONSULTANT_AGENT: AgentType.SENIOR_DELIVERY_CONSULTANT,
            UserRole.DELIVERY_CONSULTANT_BG_AGENT: AgentType.DELIVERY_CONSULTANT_BG,
            UserRole.DELIVERY_CONSULTANT_HU_AGENT: AgentType.DELIVERY_CONSULTANT_HU,
            UserRole.DELIVERY_CONSULTANT_EN_AGENT: AgentType.DELIVERY_CONSULTANT_EN,
            UserRole.REPORTING_MANAGER_AGENT: AgentType.REPORTING_MANAGER,
            UserRole.REPORTING_SPECIALIST_AGENT: AgentType.REPORTING_SPECIALIST,
            UserRole.LEGAL_AGENT: AgentType.LEGAL,
        }
        return role_mapping.get(self.role, AgentType.POSITIONING)
    
    def get_accessible_agents(self) -> List[AgentType]:
        """Get all agents this user can access"""
        return [assignment.agent_type for assignment in self.agent_assignments]
    
    def get_accessible_memory_collections(self) -> List[str]:
        """Get all memory collections this user can access (read or write)"""
        collections = []
        for assignment in self.agent_assignments:
            collections.extend(assignment.memory_read_access)
            collections.extend(assignment.memory_write_access)
        return list(set(collections))  # Remove duplicates
    
    def get_readable_memory_collections(self) -> List[str]:
        """Get all memory collections this user can read"""
        collections = []
        for assignment in self.agent_assignments:
            collections.extend(assignment.memory_read_access)
        return list(set(collections))  # Remove duplicates
    
    def get_writable_memory_collections(self) -> List[str]:
        """Get all memory collections this user can write to"""
        collections = []
        for assignment in self.agent_assignments:
            collections.extend(assignment.memory_write_access)
        return list(set(collections))  # Remove duplicates
    
    def has_agent_access(self, agent_type: AgentType) -> bool:
        """Check if user has access to specific agent"""
        return agent_type in self.get_accessible_agents()
    
    def has_memory_access(self, collection_name: str) -> bool:
        """Check if user has any access (read or write) to specific memory collection"""
        return collection_name in self.get_accessible_memory_collections()
    
    def has_memory_read_access(self, collection_name: str) -> bool:
        """Check if user has read access to specific memory collection"""
        return collection_name in self.get_readable_memory_collections()
    
    def has_memory_write_access(self, collection_name: str) -> bool:
        """Check if user has write access to specific memory collection"""
        return collection_name in self.get_writable_memory_collections()
    
    def get_agent_assignment(self, agent_type: AgentType) -> Optional[AgentAssignment]:
        """Get assignment details for specific agent"""
        for assignment in self.agent_assignments:
            if assignment.agent_type == agent_type:
                return assignment
        return None
    
    def add_agent_assignment(self, assignment: AgentAssignment):
        """Add new agent assignment"""
        # Remove existing assignment for the same agent if exists
        self.agent_assignments = [
            a for a in self.agent_assignments 
            if a.agent_type != assignment.agent_type
        ]
        self.agent_assignments.append(assignment)
        self.updated_at = datetime.now()
    
    def remove_agent_assignment(self, agent_type: AgentType):
        """Remove agent assignment"""
        self.agent_assignments = [
            a for a in self.agent_assignments 
            if a.agent_type != agent_type
        ]
        self.updated_at = datetime.now()
    
    def is_cmo(self) -> bool:
        """Check if user is CMO"""
        return self.role == UserRole.CMO
    
    def is_manager(self) -> bool:
        """Check if user is a manager"""
        return self.role in [
            UserRole.PRODUCT_MANAGER,
            UserRole.DIGITAL_MANAGER,
            UserRole.CONTENT_MANAGER
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for storage"""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'role': self.role.value,
            'agent_assignments': [
                {
                    'agent_type': a.agent_type.value,
                    'access_level': a.access_level,
                    'memory_access': a.memory_access,  # Keep for backward compatibility
                    'memory_read_access': a.memory_read_access,
                    'memory_write_access': a.memory_write_access,
                    'assigned_at': a.assigned_at.isoformat(),
                    'assigned_by': a.assigned_by
                }
                for a in self.agent_assignments
            ],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active,
            'metadata': self.metadata
        }
    
    def _migrate_old_memory_collections(self):
        """Migrate old collection names to new shared memory collection names"""
        # Mapping of old collection names to new shared memory collections
        old_to_new_mapping = {
            # Old executive/CMO collections
            'cmo-private-memory': 'executive-shared-memory',
            'cmo-public-memory': 'executive-shared-memory',
            'global-shared-memory': 'executive-shared-memory',
            
            # Old product marketing collections
            'positioning-public-memory': 'product-shared-memory',
            'positioning-private-memory': 'product-shared-memory',
            'persona-public-memory': 'product-shared-memory',
            'persona-private-memory': 'product-shared-memory',
            'gtm-public-memory': 'product-shared-memory',
            'gtm-private-memory': 'product-shared-memory',
            'competitor-public-memory': 'product-shared-memory',
            'competitor-private-memory': 'product-shared-memory',
            'launch-public-memory': 'product-shared-memory',
            'launch-private-memory': 'product-shared-memory',
            
            # Old digital marketing collections
            'seo-public-memory': 'digital-shared-memory',
            'seo-private-memory': 'digital-shared-memory',
            'sem-public-memory': 'digital-shared-memory',
            'sem-private-memory': 'digital-shared-memory',
            'landing-public-memory': 'digital-shared-memory',
            'landing-private-memory': 'digital-shared-memory',
            'analytics-public-memory': 'digital-shared-memory',
            'analytics-private-memory': 'digital-shared-memory',
            'funnel-public-memory': 'digital-shared-memory',
            'funnel-private-memory': 'digital-shared-memory',
            
            # Old content marketing collections
            'content-public-memory': 'content-shared-memory',
            'content-private-memory': 'content-shared-memory',
            'brand-public-memory': 'content-shared-memory',
            'brand-private-memory': 'content-shared-memory',
            'social-public-memory': 'content-shared-memory',
            'social-private-memory': 'content-shared-memory',
            'community-public-memory': 'content-shared-memory',
            'community-private-memory': 'content-shared-memory',
        }
        
        # Update all agent assignments
        for assignment in self.agent_assignments:
            # Update read access collections
            updated_read_access = []
            for collection in assignment.memory_read_access:
                new_collection = old_to_new_mapping.get(collection, collection)
                if new_collection not in updated_read_access:
                    updated_read_access.append(new_collection)
            assignment.memory_read_access = updated_read_access
            
            # Update write access collections  
            updated_write_access = []
            for collection in assignment.memory_write_access:
                new_collection = old_to_new_mapping.get(collection, collection)
                if new_collection not in updated_write_access:
                    updated_write_access.append(new_collection)
            assignment.memory_write_access = updated_write_access
            
            # Update legacy memory_access field if it exists
            if hasattr(assignment, 'memory_access') and assignment.memory_access:
                updated_memory_access = []
                for collection in assignment.memory_access:
                    new_collection = old_to_new_mapping.get(collection, collection)
                    if new_collection not in updated_memory_access:
                        updated_memory_access.append(new_collection)
                assignment.memory_access = updated_memory_access
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user from dictionary"""
        user = cls(
            id=data['id'],
            email=data['email'],
            username=data['username'],
            role=UserRole(data['role']),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            is_active=data['is_active'],
            metadata=data['metadata']
        )
        
        # Parse agent assignments
        user.agent_assignments = []
        for a in data['agent_assignments']:
            assignment = AgentAssignment(
                agent_type=AgentType(a['agent_type']),
                access_level=a['access_level'],
                memory_access=a.get('memory_access', []),  # Backward compatibility
                memory_read_access=a.get('memory_read_access', []),
                memory_write_access=a.get('memory_write_access', []),
                assigned_at=datetime.fromisoformat(a['assigned_at']),
                assigned_by=a['assigned_by']
            )
            
            # If new fields are empty but old field exists, migrate data
            if not assignment.memory_read_access and not assignment.memory_write_access and assignment.memory_access:
                # For backward compatibility, assume old memory_access means both read and write
                assignment.memory_read_access = assignment.memory_access.copy()
                assignment.memory_write_access = assignment.memory_access.copy()
            
            user.agent_assignments.append(assignment)
        
        # Migrate old collection names to new shared memory collections
        user._migrate_old_memory_collections()
        
        return user 