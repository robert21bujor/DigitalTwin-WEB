"""
Email Whitelist Management
=========================

Manages whitelisted domains, senders, and business patterns for email filtering.
Supports English and Romanian business email patterns.
"""

import json
import logging
import re
from typing import Dict, List, Set, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class WhitelistManager:
    """Manages email whitelist with multi-language business pattern support"""
    
    def __init__(self, whitelist_file: str = "Gmail/email_filtering/whitelist.json"):
        self.whitelist_file = whitelist_file
        self.whitelist_data = {
            'trusted_domains': set(),
            'trusted_senders': set(),
            'business_indicators': []
        }
        
        # Romanian business indicators
        self.romanian_business_indicators = [
            # Company types
            r'\b(srl|sa|pfa|ii|ong|asociatia|fundatia)\b',
            # Business domains
            r'@.*\.(ro|com\.ro)$',
            # Professional titles in Romanian
            r'\b(director|manager|sef|administrator|consultant|inginer|avocat)\b',
            # Business keywords
            r'\b(companie|firma|business|contract|factura|comanda|livrare)\b'
        ]
        
        # Initialize with default trusted domains including Romanian
        self.default_trusted_domains = {
            # Major tech companies
            'google.com', 'microsoft.com', 'apple.com', 'amazon.com',
            'github.com', 'gitlab.com', 'atlassian.com', 'slack.com',
            'zoom.us', 'teams.microsoft.com', 'dropbox.com',
            
            # Romanian business domains and institutions
            'gov.ro', 'edu.ro', 'org.ro',  # Government, education, organizations
            'bcr.ro', 'brd.ro', 'raiffeisen.ro',  # Major Romanian banks
            'enel.ro', 'digi.ro', 'orange.ro', 'vodafone.ro',  # Utilities and telecom
            'anaf.ro', 'insse.ro',  # Tax authority, statistics office
            
            # International domains commonly used in Romanian business
            'gmail.com', 'outlook.com', 'yahoo.com'  # But with additional validation
        }
        
        self.load_whitelist()
    
    def load_whitelist(self):
        """Load whitelist from file or create default"""
        try:
            if Path(self.whitelist_file).exists():
                with open(self.whitelist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.whitelist_data['trusted_domains'] = set(data.get('trusted_domains', []))
                    self.whitelist_data['trusted_senders'] = set(data.get('trusted_senders', []))
                    self.whitelist_data['business_indicators'] = data.get('business_indicators', [])
                    logger.info(f"Loaded whitelist with {len(self.whitelist_data['trusted_domains'])} domains")
            else:
                # Initialize with defaults
                self.whitelist_data['trusted_domains'] = self.default_trusted_domains.copy()
                self.save_whitelist()
                logger.info("Created default whitelist with Romanian business domain support")
                
        except Exception as e:
            logger.error(f"Error loading whitelist: {e}")
            self.whitelist_data['trusted_domains'] = self.default_trusted_domains.copy()
    
    def save_whitelist(self):
        """Save current whitelist to file"""
        try:
            # Ensure directory exists
            Path(self.whitelist_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Convert sets to lists for JSON serialization
            save_data = {
                'trusted_domains': list(self.whitelist_data['trusted_domains']),
                'trusted_senders': list(self.whitelist_data['trusted_senders']),
                'business_indicators': self.whitelist_data['business_indicators']
            }
            
            with open(self.whitelist_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved whitelist to {self.whitelist_file}")
            
        except Exception as e:
            logger.error(f"Error saving whitelist: {e}")
    
    def is_whitelisted(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if email should be whitelisted with Romanian business pattern support
        
        Args:
            email_data: Dictionary containing email information
            
        Returns:
            Dictionary with whitelisting decision and reasoning
        """
        sender_email = email_data.get('sender_email', '').lower()
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        
        # Extract domain from sender email
        domain = ''
        if '@' in sender_email:
            domain = sender_email.split('@')[1]
        
        # Check 1: Trusted domains
        if domain in self.whitelist_data['trusted_domains']:
            return {
                'whitelisted': True,
                'reason': 'trusted_domain',
                'details': f"Domain {domain} is in trusted domains list"
            }
        
        # Check 2: Trusted senders
        if sender_email in self.whitelist_data['trusted_senders']:
            return {
                'whitelisted': True,
                'reason': 'trusted_sender',
                'details': f"Sender {sender_email} is explicitly whitelisted"
            }
        
        # Check 3: Romanian business patterns
        combined_text = f"{sender_email} {subject} {body[:200]}".lower()
        for pattern in self.romanian_business_indicators:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return {
                    'whitelisted': True,
                    'reason': 'romanian_business_pattern',
                    'details': f"Matches Romanian business pattern: {pattern}"
                }
        
        # Check 4: General business indicators
        for pattern in self.whitelist_data['business_indicators']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return {
                    'whitelisted': True,
                    'reason': 'business_pattern',
                    'details': f"Matches business pattern: {pattern}"
                }
        
        # Check 5: High-value Romanian domains (even if not in default list)
        romanian_business_patterns = [
            r'@.*\.(ro|com\.ro)$',  # Romanian domains
            r'\b(guvern|minister|primarie|consiliu)\b.*\.ro$',  # Government entities
            r'\b(universitat|coleg|scoala)\b.*\.ro$'  # Educational institutions
        ]
        
        for pattern in romanian_business_patterns:
            if re.search(pattern, sender_email, re.IGNORECASE):
                return {
                    'whitelisted': True,
                    'reason': 'romanian_institutional',
                    'details': f"Romanian institutional domain pattern: {pattern}"
                }
        
        # Not whitelisted
        return {
            'whitelisted': False,
            'reason': 'not_whitelisted',
            'details': 'Email does not match any whitelist criteria'
        }
    
    def add_trusted_domain(self, domain: str, reason: str = None) -> bool:
        """Add a domain to the trusted domains list"""
        try:
            domain = domain.lower().strip()
            self.whitelist_data['trusted_domains'].add(domain)
            self.save_whitelist()
            logger.info(f"Added trusted domain: {domain} (reason: {reason})")
            return True
        except Exception as e:
            logger.error(f"Error adding trusted domain {domain}: {e}")
            return False
    
    def add_trusted_sender(self, sender_email: str, reason: str = None) -> bool:
        """Add a sender to the trusted senders list"""
        try:
            sender_email = sender_email.lower().strip()
            self.whitelist_data['trusted_senders'].add(sender_email)
            self.save_whitelist()
            logger.info(f"Added trusted sender: {sender_email} (reason: {reason})")
            return True
        except Exception as e:
            logger.error(f"Error adding trusted sender {sender_email}: {e}")
            return False
    
    def remove_trusted_domain(self, domain: str) -> bool:
        """Remove a domain from the trusted domains list"""
        try:
            domain = domain.lower().strip()
            if domain in self.whitelist_data['trusted_domains']:
                self.whitelist_data['trusted_domains'].remove(domain)
                self.save_whitelist()
                logger.info(f"Removed trusted domain: {domain}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing trusted domain {domain}: {e}")
            return False
    
    def get_whitelist_stats(self) -> Dict[str, Any]:
        """Get statistics about the current whitelist"""
        return {
            'trusted_domains_count': len(self.whitelist_data['trusted_domains']),
            'trusted_senders_count': len(self.whitelist_data['trusted_senders']),
            'business_indicators_count': len(self.whitelist_data['business_indicators']),
            'romanian_business_indicators_count': len(self.romanian_business_indicators),
            'has_romanian_support': True
        }
    
    def export_whitelist(self) -> Dict[str, Any]:
        """Export current whitelist for backup or analysis"""
        return {
            'trusted_domains': list(self.whitelist_data['trusted_domains']),
            'trusted_senders': list(self.whitelist_data['trusted_senders']),
            'business_indicators': self.whitelist_data['business_indicators'],
            'romanian_business_indicators': self.romanian_business_indicators
        } 