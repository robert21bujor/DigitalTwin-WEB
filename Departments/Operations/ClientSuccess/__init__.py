"""
Client Success Department
========================

Customer success and delivery consulting services including:
- Strategic operations management and oversight
- Customer success management and relationship building
- Delivery consulting and project implementation
- Multi-language support (EN, BG, HU)
- Client onboarding and adoption

Focus: Ensure customer success through expert delivery and ongoing support.
"""

from .manager import ClientSuccessManager
from .Agents import (
    HeadOfOperationsAgent,
    SeniorCSMAgent,
    SeniorDeliveryConsultantAgent,
    DeliveryConsultantBGAgent,
    DeliveryConsultantHUAgent,
    DeliveryConsultantENAgent
)

__all__ = [
    'ClientSuccessManager',
    'HeadOfOperationsAgent',
    'SeniorCSMAgent',
    'SeniorDeliveryConsultantAgent',
    'DeliveryConsultantBGAgent',
    'DeliveryConsultantHUAgent',
    'DeliveryConsultantENAgent'
] 