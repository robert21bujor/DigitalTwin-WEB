"""
Bilingual Query Interpreter for Romanian/English Search
Transforms natural language queries into typed specifications for Gmail/Drive
"""

import re
import logging
import unicodedata
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SearchSource(Enum):
    """Search source types"""
    GMAIL = "gmail"
    DRIVE = "drive"
    AUTO = "auto"


@dataclass
class SearchSpec:
    """Typed search specification from natural language query"""
    source: SearchSource
    query_text: str
    operators: Dict[str, Any]
    free_text_terms: List[str]
    original_query: str
    language: str = "auto"


class QueryInterpreter:
    """
    Bilingual query interpreter that transforms natural language into structured search specs
    Supports Romanian and English with operator aliasing and date parsing
    """
    
    def __init__(self):
        # Romanian → English operator mappings
        self.ro_operator_map = {
            # Basic operators
            "de la:": "from:",
            "dela:": "from:",
            "de la ": "from:",
            "către:": "to:",
            "catre:": "to:",
            "subiect:": "subject:",
            "titlu:": "subject:",
            "înainte de:": "before:",
            "inainte de:": "before:",
            "după:": "after:",
            "dupa:": "after:",
            "etichetă:": "label:",
            "eticheta:": "label:",
            "are:atașament": "has:attachment",
            "are:atasament": "has:attachment",
            "are:attachment": "has:attachment",
            "tip:": "",  # Will be handled specially for mimeType
            "nume:": "",  # Will be handled specially for name contains
            "conținut:": "",  # Will be handled specially for fullText
            "continut:": "",  # Will be handled specially for fullText
            
            # File type mappings
            "tip:pdf": "mimeType:'application/pdf'",
            "tip:docx": "mimeType:'application/vnd.openxmlformats-officedocument.wordprocessingml.document'",
            "tip:xlsx": "mimeType:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'",
            "tip:pptx": "mimeType:'application/vnd.openxmlformats-officedocument.presentationml.presentation'",
            "tip:doc": "mimeType:'application/msword'",
            "tip:xls": "mimeType:'application/vnd.ms-excel'",
            "tip:ppt": "mimeType:'application/vnd.ms-powerpoint'",
        }
        
        # Romanian month names
        self.ro_months = {
            "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4,
            "mai": 5, "iunie": 6, "iulie": 7, "august": 8,
            "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12
        }
        
        # Romanian relative date terms
        self.ro_relative_dates = {
            "azi": lambda: datetime.now().date(),
            "astăzi": lambda: datetime.now().date(),
            "astazi": lambda: datetime.now().date(),
            "ieri": lambda: (datetime.now() - timedelta(days=1)).date(),
            "săptămâna trecută": lambda: (datetime.now() - timedelta(weeks=1)).date(),
            "saptamana trecuta": lambda: (datetime.now() - timedelta(weeks=1)).date(),
            "luna trecută": lambda: (datetime.now() - timedelta(days=30)).date(),
            "luna trecuta": lambda: (datetime.now() - timedelta(days=30)).date(),
        }
        
        # Email detection keywords
        self.email_keywords = {
            "en": ["email", "emails", "message", "messages", "mail", "correspondence", 
                   "communication", "communications", "from", "to", "sent", "received"],
            "ro": ["email", "emails", "mesaj", "mesaje", "corespondenta", "corespondență", 
                   "comunicare", "de la", "către", "trimis", "primit"]
        }
        
        # File detection keywords  
        self.file_keywords = {
            "en": ["file", "files", "document", "documents", "folder", "folders"],
            "ro": ["fișier", "fisier", "fișiere", "fisiere", "document", "documente", 
                   "folder", "dosare"]
        }

    def interpret_query(self, query: str) -> SearchSpec:
        """
        Main entry point: interpret natural language query into structured specification
        
        Args:
            query: Natural language search query in Romanian or English
            
        Returns:
            SearchSpec with typed operators and search parameters
        """
        logger.debug(f"🔍 Interpreting query: '{query}'")
        
        # Normalize query
        normalized_query = self._normalize_text(query)
        
        # Detect language and source
        language = self._detect_language(normalized_query)
        source = self._detect_source(normalized_query, language)
        
        # Apply Romanian → English operator aliasing
        processed_query = self._apply_ro_aliasing(normalized_query)
        
        # Parse date expressions
        processed_query = self._parse_dates(processed_query, language)
        
        # Extract operators and free text
        operators, free_text_terms = self._extract_operators(processed_query)
        
        # Post-process based on source type
        if source == SearchSource.GMAIL:
            operators = self._optimize_gmail_operators(operators)
        elif source == SearchSource.DRIVE:
            operators = self._optimize_drive_operators(operators)
        
        spec = SearchSpec(
            source=source,
            query_text=processed_query,
            operators=operators,
            free_text_terms=free_text_terms,
            original_query=query,
            language=language
        )
        
        logger.debug(f"✅ Interpreted spec: source={spec.source.value}, operators={spec.operators}")
        return spec

    def _normalize_text(self, text: str) -> str:
        """Normalize text with NFC normalization and basic cleaning"""
        # NFC normalization for consistent diacritic handling
        normalized = unicodedata.normalize('NFC', text)
        
        # Basic cleaning
        normalized = re.sub(r'\s+', ' ', normalized.strip())
        
        return normalized

    def _strip_diacritics(self, text: str) -> str:
        """Strip Romanian diacritics for matching"""
        # Romanian diacritic mappings
        diacritic_map = {
            'ș': 's', 'ş': 's', 'Ș': 'S', 'Ş': 'S',
            'ț': 't', 'ţ': 't', 'Ț': 'T', 'Ţ': 'T',
            'ă': 'a', 'Ă': 'A',
            'â': 'a', 'Â': 'A', 
            'î': 'i', 'Î': 'I'
        }
        
        result = text
        for diacritic, replacement in diacritic_map.items():
            result = result.replace(diacritic, replacement)
        
        return result

    def _detect_language(self, query: str) -> str:
        """Detect if query is primarily Romanian or English"""
        query_lower = query.lower()
        
        # Count Romanian-specific indicators
        ro_indicators = [
            'de la', 'către', 'catre', 'subiect', 'înainte', 'inainte', 
            'după', 'dupa', 'etichetă', 'eticheta', 'atașament', 'atasament',
            'conținut', 'continut', 'fișier', 'fisier', 'găsește', 'gaseste'
        ]
        
        ro_count = sum(1 for indicator in ro_indicators if indicator in query_lower)
        
        # Check for Romanian months
        ro_month_count = sum(1 for month in self.ro_months.keys() if month in query_lower)
        
        return "ro" if (ro_count > 0 or ro_month_count > 0) else "en"

    def _detect_source(self, query: str, language: str) -> SearchSource:
        """Detect if query is for Gmail, Drive, or auto-detect"""
        query_lower = query.lower()
        
        # Check for email keywords
        email_kw = self.email_keywords[language] + self.email_keywords["en"]
        has_email_keywords = any(kw in query_lower for kw in email_kw)
        
        # Check for file keywords
        file_kw = self.file_keywords[language] + self.file_keywords["en"] 
        has_file_keywords = any(kw in query_lower for kw in file_kw)
        
        # Check for specific operators
        has_email_operators = any(op in query_lower for op in [
            "from:", "to:", "subject:", "de la:", "către:", "subiect:"
        ])
        
        has_file_operators = any(op in query_lower for op in [
            "tip:", "nume:", "conținut:", "continut:", "mimeType:", "name:"
        ])
        
        if has_email_keywords or has_email_operators:
            return SearchSource.GMAIL
        elif has_file_keywords or has_file_operators:
            return SearchSource.DRIVE
        else:
            return SearchSource.AUTO

    def _apply_ro_aliasing(self, query: str) -> str:
        """Apply Romanian → English operator aliasing"""
        result = query
        
        # Sort by length (descending) to handle longer phrases first
        sorted_mappings = sorted(self.ro_operator_map.items(), 
                                key=lambda x: len(x[0]), reverse=True)
        
        for ro_op, en_op in sorted_mappings:
            if ro_op in result:
                result = result.replace(ro_op, en_op)
                logger.debug(f"🔄 Aliased '{ro_op}' → '{en_op}'")
        
        return result

    def _parse_dates(self, query: str, language: str) -> str:
        """Parse Romanian date expressions and convert to ISO format"""
        result = query
        
        if language == "ro":
            # Handle relative dates
            for ro_term, date_func in self.ro_relative_dates.items():
                if ro_term in result:
                    iso_date = date_func().isoformat()
                    result = result.replace(ro_term, iso_date)
                    logger.debug(f"📅 Parsed relative date '{ro_term}' → '{iso_date}'")
            
            # Handle absolute dates with Romanian months
            # Pattern: "12 iulie 2025"
            ro_date_pattern = r'(\d{1,2})\s+(' + '|'.join(self.ro_months.keys()) + r')\s+(\d{4})'
            
            def replace_ro_date(match):
                day, month_name, year = match.groups()
                month_num = self.ro_months[month_name]
                try:
                    date_obj = datetime(int(year), month_num, int(day))
                    iso_date = date_obj.date().isoformat()
                    logger.debug(f"📅 Parsed RO date '{match.group()}' → '{iso_date}'")
                    return iso_date
                except ValueError:
                    return match.group()  # Invalid date, keep original
            
            result = re.sub(ro_date_pattern, replace_ro_date, result, flags=re.IGNORECASE)
        
        return result

    def _extract_operators(self, query: str) -> Tuple[Dict[str, Any], List[str]]:
        """Extract search operators and remaining free text"""
        operators = {}
        remaining_text = query
        
        # Common operators for both Gmail and Drive
        operator_patterns = {
            'from': r'from:([^\s]+)',
            'to': r'to:([^\s]+)', 
            'subject': r'subject:"([^"]+)"',
            'before': r'before:([^\s]+)',
            'after': r'after:([^\s]+)',
            'has': r'has:([^\s]+)',
            'label': r'label:([^\s]+)',
            'mimeType': r'mimeType:\'([^\']+)\'',
            'name': r'name:"([^"]+)"',
            'fullText': r'fullText:"([^"]+)"'
        }
        
        for op_name, pattern in operator_patterns.items():
            matches = re.findall(pattern, remaining_text, re.IGNORECASE)
            if matches:
                operators[op_name] = matches[0] if len(matches) == 1 else matches
                # Remove matched operators from remaining text
                remaining_text = re.sub(pattern, '', remaining_text, flags=re.IGNORECASE)
        
        # Extract free text terms (clean up remaining text)
        free_text = re.sub(r'\s+', ' ', remaining_text.strip())
        free_text_terms = [term.strip() for term in free_text.split() if term.strip()]
        
        return operators, free_text_terms

    def _optimize_gmail_operators(self, operators: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize operators specifically for Gmail search"""
        optimized = operators.copy()
        
        # Convert name/fullText to generic search terms for Gmail
        if 'name' in optimized:
            del optimized['name']  # Gmail doesn't support name: operator
            
        if 'fullText' in optimized:
            del optimized['fullText']  # Will be handled in free text
        
        # Ensure dates are in Gmail format (YYYY/MM/DD)
        for date_op in ['before', 'after']:
            if date_op in optimized:
                date_val = optimized[date_op]
                if isinstance(date_val, str) and '-' in date_val:
                    # Convert ISO format to Gmail format
                    optimized[date_op] = date_val.replace('-', '/')
        
        return optimized

    def _optimize_drive_operators(self, operators: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize operators specifically for Drive search"""
        optimized = operators.copy()
        
        # Remove Gmail-specific operators
        gmail_only = ['from', 'to', 'has', 'label']
        for op in gmail_only:
            if op in optimized:
                del optimized[op]
        
        # Drive uses different date format and field names
        if 'before' in optimized:
            # Convert to modifiedTime for Drive
            optimized['modifiedTime'] = f"<{optimized['before']}"
            del optimized['before']
            
        if 'after' in optimized:
            if 'modifiedTime' in optimized:
                # Combine into range
                optimized['modifiedTime'] = f">{optimized['after']} and {optimized['modifiedTime']}"
            else:
                optimized['modifiedTime'] = f">{optimized['after']}"
            del optimized['after']
        
        return optimized

    def build_gmail_query(self, spec: SearchSpec) -> str:
        """Build Gmail API query string from SearchSpec"""
        query_parts = []
        
        # Add operators
        for op_name, op_value in spec.operators.items():
            if op_name == 'subject' and isinstance(op_value, str):
                query_parts.append(f'subject:"{op_value}"')
            elif op_name in ['from', 'to', 'has', 'label']:
                query_parts.append(f'{op_name}:{op_value}')
            elif op_name in ['before', 'after']:
                query_parts.append(f'{op_name}:{op_value}')
        
        # Add free text with diacritic expansion for Romanian
        if spec.free_text_terms:
            if spec.language == "ro":
                # Add both original and diacritic-stripped versions
                expanded_terms = []
                for term in spec.free_text_terms:
                    expanded_terms.append(term)
                    stripped = self._strip_diacritics(term)
                    if stripped != term:
                        expanded_terms.append(stripped)
                query_parts.append(f"({' OR '.join(expanded_terms)})")
            else:
                query_parts.append(' '.join(spec.free_text_terms))
        
        query_string = ' '.join(query_parts)
        logger.debug(f"📧 Built Gmail query: '{query_string}'")
        return query_string

    def build_drive_query(self, spec: SearchSpec) -> str:
        """Build Google Drive API query string from SearchSpec"""
        query_parts = []
        
        # Add operators
        for op_name, op_value in spec.operators.items():
            if op_name == 'mimeType':
                query_parts.append(f"mimeType='{op_value}'")
            elif op_name == 'name':
                query_parts.append(f"name contains '{op_value}'")
            elif op_name == 'fullText':
                query_parts.append(f"fullText contains '{op_value}'")
            elif op_name == 'modifiedTime':
                query_parts.append(f"modifiedTime {op_value}")
        
        # Add free text search (both name and fullText)
        if spec.free_text_terms:
            text_query = ' '.join(spec.free_text_terms)
            
            if spec.language == "ro":
                # Diacritic expansion for Romanian
                stripped_query = self._strip_diacritics(text_query)
                if stripped_query != text_query:
                    # Search both original and stripped versions
                    name_search = f"(name contains '{text_query}' or name contains '{stripped_query}')"
                    content_search = f"(fullText contains '{text_query}' or fullText contains '{stripped_query}')"
                else:
                    name_search = f"name contains '{text_query}'"
                    content_search = f"fullText contains '{text_query}'"
            else:
                name_search = f"name contains '{text_query}'"
                content_search = f"fullText contains '{text_query}'"
            
            query_parts.append(f"({name_search} or {content_search})")
        
        query_string = ' and '.join(query_parts) if query_parts else ''
        logger.debug(f"📁 Built Drive query: '{query_string}'")
        return query_string

    def expand_free_text_for_reranking(self, text: str, language: str) -> List[str]:
        """Expand free text terms for diacritic-insensitive reranking"""
        terms = text.split()
        expanded = []
        
        for term in terms:
            expanded.append(term)
            if language == "ro":
                stripped = self._strip_diacritics(term)
                if stripped != term:
                    expanded.append(stripped)
        
        return expanded
