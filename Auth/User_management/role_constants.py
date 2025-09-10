"""
Centralized Role and Permission Constants
=========================================

Single source of truth for all user roles and permissions across the platform.
All scripts should import from this file instead of maintaining their own lists.
"""

from typing import List, Dict, Any

# Company Roles - Single source of truth
COMPANY_ROLES = [
    # No specific role
    'none',
    
    # Leadership Roles
    'cmo', 'ceo', 'cto', 'cfo',
    
    # Management Roles
    'product_manager', 'digital_manager', 'content_manager', 
    'business_dev_manager', 'operations_manager',
    
    # Marketing Department Agents
    'positioning_agent', 'persona_agent', 'gtm_agent', 'competitor_agent', 'launch_agent',
    'seo_agent', 'sem_agent', 'landing_agent', 'analytics_agent', 'funnel_agent',
    'content_agent', 'brand_agent', 'social_agent', 'community_agent',
    
    # Business Development Agents
    'ipm_agent', 'bdm_agent', 'presales_engineer_agent', 'advisory_board_manager_agent',
    
    # Operations Department Agents
    'head_of_operations_agent', 'senior_csm_agent', 'senior_delivery_consultant_agent',
    'delivery_consultant_bg_agent', 'delivery_consultant_hu_agent', 'delivery_consultant_en_agent',
    'reporting_manager_agent', 'reporting_specialist_agent',
    
    # Legal & Compliance
    'legal_agent',
    
    # General Employee Roles
    'employee', 'contractor', 'intern'
]

# Admin Rights - Single source of truth
ADMIN_RIGHTS = [
    'none',         # No admin privileges
    'admin',        # Basic admin privileges
    'super_admin',  # Full admin privileges
    'system_admin'  # System-level admin privileges
]

# Role descriptions for UI/CLI display
ROLE_DESCRIPTIONS = {
    'none': 'No Specific Role',
    'cmo': 'Chief Marketing Officer',
    'ceo': 'Chief Executive Officer',
    'cto': 'Chief Technology Officer',
    'cfo': 'Chief Financial Officer',
    'product_manager': 'Product Manager',
    'digital_manager': 'Digital Manager',
    'content_manager': 'Content Manager',
    'business_dev_manager': 'Business Development Manager',
    'operations_manager': 'Operations Manager',
    'positioning_agent': 'Positioning Agent',
    'persona_agent': 'Persona Agent',
    'gtm_agent': 'Go-to-Market Agent',
    'competitor_agent': 'Competitor Agent',
    'launch_agent': 'Launch Agent',
    'seo_agent': 'SEO Agent',
    'sem_agent': 'SEM Agent',
    'landing_agent': 'Landing Page Agent',
    'analytics_agent': 'Analytics Agent',
    'funnel_agent': 'Funnel Agent',
    'content_agent': 'Content Agent',
    'brand_agent': 'Brand Agent',
    'social_agent': 'Social Media Agent',
    'community_agent': 'Community Agent',
    'ipm_agent': 'IPM Agent',
    'bdm_agent': 'BDM Agent',
    'presales_engineer_agent': 'Presales Engineer Agent',
    'advisory_board_manager_agent': 'Advisory Board Manager Agent',
    'head_of_operations_agent': 'Head of Operations Agent',
    'senior_csm_agent': 'Senior CSM Agent',
    'senior_delivery_consultant_agent': 'Senior Delivery Consultant Agent',
    'delivery_consultant_bg_agent': 'Delivery Consultant (BG) Agent',
    'delivery_consultant_hu_agent': 'Delivery Consultant (HU) Agent',
    'delivery_consultant_en_agent': 'Delivery Consultant (EN) Agent',
    'reporting_manager_agent': 'Reporting Manager Agent',
    'reporting_specialist_agent': 'Reporting Specialist Agent',
    'legal_agent': 'Legal Agent',
    'employee': 'Employee',
    'contractor': 'Contractor',
    'intern': 'Intern'
}

# Admin rights descriptions
ADMIN_DESCRIPTIONS = {
    'none': 'No admin privileges',
    'admin': 'Basic admin privileges', 
    'super_admin': 'Full admin privileges',
    'system_admin': 'System-level admin privileges'
}

# Role categories for better organization
ROLE_CATEGORIES = {
    'leadership': ['cmo', 'ceo', 'cto', 'cfo'],
    'management': ['product_manager', 'digital_manager', 'content_manager', 'business_dev_manager', 'operations_manager'],
    'marketing': ['positioning_agent', 'persona_agent', 'gtm_agent', 'competitor_agent', 'launch_agent',
                  'seo_agent', 'sem_agent', 'landing_agent', 'analytics_agent', 'funnel_agent',
                  'content_agent', 'brand_agent', 'social_agent', 'community_agent'],
    'business_dev': ['ipm_agent', 'bdm_agent', 'presales_engineer_agent', 'advisory_board_manager_agent'],
    'operations': ['head_of_operations_agent', 'senior_csm_agent', 'senior_delivery_consultant_agent',
                   'delivery_consultant_bg_agent', 'delivery_consultant_hu_agent', 'delivery_consultant_en_agent',
                   'reporting_manager_agent', 'reporting_specialist_agent'],
    'legal': ['legal_agent'],
    'general': ['employee', 'contractor', 'intern'],
    'none': ['none']
}

def validate_role(role: str) -> bool:
    """Validate if a role is valid"""
    return role in COMPANY_ROLES

def validate_admin_rights(admin_rights: str) -> bool:
    """Validate if admin rights value is valid"""
    return admin_rights in ADMIN_RIGHTS

def get_role_description(role: str) -> str:
    """Get user-friendly description for a role"""
    return ROLE_DESCRIPTIONS.get(role, role.replace('_', ' ').title())

def get_admin_description(admin_rights: str) -> str:
    """Get user-friendly description for admin rights"""
    return ADMIN_DESCRIPTIONS.get(admin_rights, admin_rights)

def get_roles_by_category(category: str) -> List[str]:
    """Get all roles in a specific category"""
    return ROLE_CATEGORIES.get(category, [])

def get_all_roles() -> List[str]:
    """Get all valid company roles"""
    return COMPANY_ROLES.copy()

def get_all_admin_rights() -> List[str]:
    """Get all valid admin rights"""
    return ADMIN_RIGHTS.copy()