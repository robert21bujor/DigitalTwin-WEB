"""
File Indexer for Semantic Search
Handles content extraction, preprocessing, and embedding generation for files
"""

import logging
import os
import io
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
import asyncio
import json

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    import PyPDF2
    from docx import Document
    import html2text
    INDEXER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ File indexer dependencies not available: {e}")
    INDEXER_AVAILABLE = False

logger = logging.getLogger(__name__)

class ContentExtractor:
    """Extract text content from various file types"""
    
    def __init__(self):
        self.html_converter = html2text.HTML2Text() if INDEXER_AVAILABLE else None
        if self.html_converter:
            self.html_converter.ignore_links = True
            self.html_converter.ignore_images = True
    
    def extract_content(self, file_data: Dict, file_content: Optional[bytes] = None) -> str:
        """
        Extract text content from a file
        
        Args:
            file_data: File metadata from Google Drive
            file_content: Optional file content bytes
            
        Returns:
            Extracted text content
        """
        mime_type = file_data.get('mime_type', '').lower()
        file_name = file_data.get('name', '').lower()
        
        try:
            if file_content:
                # Try to extract from file content
                if 'pdf' in mime_type or file_name.endswith('.pdf'):
                    return self._extract_pdf_content(file_content)
                elif 'word' in mime_type or file_name.endswith(('.doc', '.docx')):
                    return self._extract_docx_content(file_content)
                elif 'text' in mime_type or file_name.endswith('.txt'):
                    return self._extract_text_content(file_content)
                elif 'html' in mime_type or file_name.endswith('.html'):
                    return self._extract_html_content(file_content)
            
            # Fallback: extract from metadata and filename
            return self._extract_metadata_content(file_data)
            
        except Exception as e:
            logger.warning(f"Content extraction failed for {file_data.get('name', 'unknown')}: {e}")
            return self._extract_metadata_content(file_data)
    
    def _extract_pdf_content(self, content: bytes) -> str:
        """Extract text from PDF content"""
        if not INDEXER_AVAILABLE:
            return ""
        
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            text_parts = []
            
            # Extract text from first few pages (limit for performance)
            max_pages = min(5, len(pdf_reader.pages))
            for page_num in range(max_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                if text.strip():
                    text_parts.append(text.strip())
            
            return ' '.join(text_parts)[:2000]  # Limit length
            
        except Exception as e:
            logger.debug(f"PDF extraction error: {e}")
            return ""
    
    def _extract_docx_content(self, content: bytes) -> str:
        """Extract text from DOCX content"""
        if not INDEXER_AVAILABLE:
            return ""
        
        try:
            doc = Document(io.BytesIO(content))
            text_parts = []
            
            # Extract paragraphs
            for paragraph in doc.paragraphs[:20]:  # Limit paragraphs
                if paragraph.text.strip():
                    text_parts.append(paragraph.text.strip())
            
            return ' '.join(text_parts)[:2000]  # Limit length
            
        except Exception as e:
            logger.debug(f"DOCX extraction error: {e}")
            return ""
    
    def _extract_text_content(self, content: bytes) -> str:
        """Extract from plain text files"""
        try:
            text = content.decode('utf-8', errors='ignore')
            return text[:2000]  # Limit length
        except Exception as e:
            logger.debug(f"Text extraction error: {e}")
            return ""
    
    def _extract_html_content(self, content: bytes) -> str:
        """Extract text from HTML content"""
        if not INDEXER_AVAILABLE:
            return ""
        
        try:
            html = content.decode('utf-8', errors='ignore')
            text = self.html_converter.handle(html)
            return text[:2000]  # Limit length
        except Exception as e:
            logger.debug(f"HTML extraction error: {e}")
            return ""
    
    def _extract_metadata_content(self, file_data: Dict) -> str:
        """Extract searchable content from file metadata"""
        content_parts = []
        
        # File name (most important)
        name = file_data.get('name', '')
        if name:
            # Clean filename
            clean_name = re.sub(r'[_\-\.]', ' ', name)
            clean_name = re.sub(r'\d{4}-\d{2}-\d{2}', '', clean_name)  # Remove dates
            content_parts.append(clean_name)
        
        # Folder path context
        folder_path = file_data.get('folder_path', '')
        if folder_path:
            # Extract meaningful folder names
            path_parts = folder_path.replace('My Drive/', '').split('/')
            meaningful_parts = [part for part in path_parts if part and len(part) > 2]
            content_parts.extend(meaningful_parts)
        
        # File type
        file_type = file_data.get('file_type', '')
        if file_type:
            content_parts.append(file_type)
        
        return ' '.join(content_parts)

class FileIndexer:
    """Main file indexer for semantic search"""
    
    def __init__(self, model: Optional[Any] = None):
        self.model = model
        self.content_extractor = ContentExtractor()
        self.index_cache = {}
        self.last_update = None
    
    def create_file_index(self, files: List[Dict]) -> Tuple[np.ndarray, List[Dict]]:
        """
        Create semantic index for a list of files
        
        Args:
            files: List of file dictionaries from Google Drive
            
        Returns:
            Tuple of (embeddings_matrix, indexed_file_metadata)
        """
        if not self.model or not INDEXER_AVAILABLE:
            logger.warning("Semantic indexing not available")
            return np.array([]), []
        
        try:
            logger.info(f"🔄 Creating semantic index for {len(files)} files...")
            
            indexed_files = []
            texts_to_embed = []
            
            for file_data in files:
                # Extract and process content
                content = self.content_extractor.extract_content(file_data)
                
                if content.strip():
                    # Create enhanced searchable text
                    searchable_text = self._create_enhanced_searchable_text(file_data, content)
                    texts_to_embed.append(searchable_text)
                    
                    # Store enhanced metadata
                    enhanced_file_data = {
                        **file_data,
                        'extracted_content': content[:500],  # First 500 chars for snippets
                        'searchable_text': searchable_text,
                        'content_length': len(content),
                        'indexed_at': datetime.now().isoformat()
                    }
                    indexed_files.append(enhanced_file_data)
                else:
                    logger.debug(f"No content extracted for {file_data.get('name', 'unknown')}")
            
            if not texts_to_embed:
                logger.warning("No content to index")
                return np.array([]), []
            
            # Generate embeddings in batches for efficiency
            logger.info(f"🧠 Generating embeddings for {len(texts_to_embed)} files...")
            embeddings = self.model.encode(texts_to_embed, batch_size=32, show_progress_bar=False)
            
            logger.info(f"✅ Created semantic index: {embeddings.shape}")
            return embeddings, indexed_files
            
        except Exception as e:
            logger.error(f"Failed to create file index: {e}")
            return np.array([]), []
    
    def _create_enhanced_searchable_text(self, file_data: Dict, content: str) -> str:
        """Create enhanced searchable text combining metadata and content"""
        components = []
        
        # File name (highest weight - add multiple times)
        name = file_data.get('name', '')
        if name:
            clean_name = re.sub(r'[_\-\.]', ' ', name)
            components.append(clean_name)
            components.append(clean_name)  # Add twice for higher weight
        
        # Folder context
        folder_path = file_data.get('folder_path', '')
        if folder_path:
            folder_names = folder_path.replace('My Drive/', '').split('/')
            meaningful_folders = [f for f in folder_names if f and len(f) > 2]
            components.extend(meaningful_folders)
        
        # File type and category
        file_type = file_data.get('file_type', '')
        if file_type:
            components.append(file_type)
        
        # Content summary (first part)
        if content:
            # Take first 200 characters of content
            content_preview = content[:200].strip()
            if content_preview:
                components.append(content_preview)
        
        # Create intent-based content
        intent_keywords = self._generate_intent_keywords(file_data, content)
        components.extend(intent_keywords)
        
        # Join and clean
        searchable_text = ' '.join(components)
        searchable_text = re.sub(r'\s+', ' ', searchable_text).strip()
        
        return searchable_text
    
    def _generate_intent_keywords(self, file_data: Dict, content: str) -> List[str]:
        """Generate intent-based keywords for better matching"""
        keywords = []
        
        name_lower = file_data.get('name', '').lower()
        content_lower = content.lower()
        folder_lower = file_data.get('folder_path', '').lower()
        
        # Contract-related
        if any(term in name_lower + content_lower for term in ['contract', 'agreement', 'deal', 'terms']):
            keywords.extend(['contract', 'agreement', 'legal document'])
        
        # Email-related
        if 'email' in folder_lower or any(term in name_lower for term in ['mail', 'message', 'communication']):
            keywords.extend(['email', 'communication', 'message'])
        
        # Report-related
        if any(term in name_lower + content_lower for term in ['report', 'analysis', 'briefing', 'summary']):
            keywords.extend(['report', 'analysis', 'business document'])
        
        # Financial
        if any(term in name_lower + content_lower for term in ['earnings', 'financial', 'revenue', 'profit']):
            keywords.extend(['financial', 'earnings', 'business metrics'])
        
        # Internal vs external
        if 'internal' in folder_lower or 'team' in name_lower:
            keywords.extend(['internal', 'company', 'team'])
        elif any(term in folder_lower for term in ['client', 'customer', 'external']):
            keywords.extend(['client', 'external', 'customer'])
        
        # Time-based
        current_year = datetime.now().year
        if str(current_year) in name_lower or str(current_year-1) in name_lower:
            keywords.append('recent')
        
        return keywords
    
    def update_file_in_index(self, file_data: Dict, embeddings: np.ndarray, indexed_files: List[Dict]) -> Tuple[np.ndarray, List[Dict]]:
        """
        Update a single file in the existing index
        
        Args:
            file_data: Updated file data
            embeddings: Current embeddings matrix
            indexed_files: Current indexed files list
            
        Returns:
            Updated (embeddings, indexed_files)
        """
        if not self.model or not INDEXER_AVAILABLE:
            return embeddings, indexed_files
        
        try:
            file_id = file_data.get('file_id')
            if not file_id:
                return embeddings, indexed_files
            
            # Find existing file index
            existing_index = None
            for i, existing_file in enumerate(indexed_files):
                if existing_file.get('file_id') == file_id:
                    existing_index = i
                    break
            
            # Extract content and create embedding
            content = self.content_extractor.extract_content(file_data)
            searchable_text = self._create_enhanced_searchable_text(file_data, content)
            new_embedding = self.model.encode([searchable_text])
            
            enhanced_file_data = {
                **file_data,
                'extracted_content': content[:500],
                'searchable_text': searchable_text,
                'content_length': len(content),
                'indexed_at': datetime.now().isoformat()
            }
            
            if existing_index is not None:
                # Update existing
                embeddings[existing_index] = new_embedding[0]
                indexed_files[existing_index] = enhanced_file_data
            else:
                # Add new
                if embeddings.size > 0:
                    embeddings = np.vstack([embeddings, new_embedding])
                else:
                    embeddings = new_embedding
                indexed_files.append(enhanced_file_data)
            
            return embeddings, indexed_files
            
        except Exception as e:
            logger.error(f"Failed to update file in index: {e}")
            return embeddings, indexed_files
    
    def remove_file_from_index(self, file_id: str, embeddings: np.ndarray, indexed_files: List[Dict]) -> Tuple[np.ndarray, List[Dict]]:
        """
        Remove a file from the index
        
        Args:
            file_id: ID of file to remove
            embeddings: Current embeddings matrix
            indexed_files: Current indexed files list
            
        Returns:
            Updated (embeddings, indexed_files)
        """
        try:
            # Find file index
            remove_index = None
            for i, file_data in enumerate(indexed_files):
                if file_data.get('file_id') == file_id:
                    remove_index = i
                    break
            
            if remove_index is not None:
                # Remove from both arrays
                indexed_files.pop(remove_index)
                if embeddings.size > 0:
                    embeddings = np.delete(embeddings, remove_index, axis=0)
            
            return embeddings, indexed_files
            
        except Exception as e:
            logger.error(f"Failed to remove file from index: {e}")
            return embeddings, indexed_files
    
    def save_index(self, embeddings: np.ndarray, indexed_files: List[Dict], file_path: str):
        """Save index to disk"""
        try:
            index_data = {
                'embeddings': embeddings.tolist() if embeddings.size > 0 else [],
                'files': indexed_files,
                'created_at': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Saved semantic index to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def load_index(self, file_path: str) -> Tuple[np.ndarray, List[Dict]]:
        """Load index from disk"""
        try:
            if not os.path.exists(file_path):
                return np.array([]), []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            embeddings_list = index_data.get('embeddings', [])
            embeddings = np.array(embeddings_list) if embeddings_list else np.array([])
            
            indexed_files = index_data.get('files', [])
            
            logger.info(f"✅ Loaded semantic index from {file_path}")
            return embeddings, indexed_files
            
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return np.array([]), []

# Global instance
file_indexer = FileIndexer() if INDEXER_AVAILABLE else None

def get_file_indexer() -> Optional[FileIndexer]:
    """Get the global file indexer instance"""
    return file_indexer