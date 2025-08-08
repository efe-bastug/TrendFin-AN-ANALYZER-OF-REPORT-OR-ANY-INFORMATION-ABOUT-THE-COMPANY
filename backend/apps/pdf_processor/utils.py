"""
PDF processing utilities using PyMuPDF for text extraction and chunking
"""

import fitz
import tiktoken
from typing import List, Dict, Tuple
from django.conf import settings
import logging
import re
import os

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Main class for processing PDF documents"""
    
    def __init__(self):
        self.chunk_size = settings.PDF_SETTINGS['CHUNK_SIZE']
        self.chunk_overlap = settings.PDF_SETTINGS['CHUNK_OVERLAP']
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def extract_text_from_pdf(self, pdf_path: str) -> Dict[int, str]:
        """
        Extract text from PDF file page by page
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary mapping page numbers to text content
        """
        try:
            doc = fitz.open(pdf_path)
            pages_text = {}
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                text = self._clean_text(text)
                pages_text[page_num + 1] = text
                
                logger.debug(f"Extracted {len(text)} characters from page {page_num + 1}")
            
            doc.close()
            total_pages = len(pages_text)
            total_chars = sum(len(text) for text in pages_text.values())
            
            logger.info(f"Extracted text from {total_pages} pages, {total_chars} total characters")
            return pages_text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        if not text:
            return ""
        
        text = re.sub(r'\s+', ' ', text)
        
        lines = text.split('\n')
        if len(lines) > 3:
            if len(lines[0]) < 50:
                lines = lines[1:]
            if len(lines) > 0 and len(lines[-1]) < 50:
                lines = lines[:-1]
        
        text = '\n'.join(lines)
        
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        return len(self.encoding.encode(text))
    
    def create_chunks(self, pages_text: Dict[int, str]) -> List[Dict]:
        """
        Create overlapping chunks from extracted text
        
        Args:
            pages_text: Dictionary mapping page numbers to text
            
        Returns:
            List of chunk dictionaries with metadata
        """
        chunks = []
        current_chunk = ""
        current_tokens = 0
        current_pages = []
        chunk_index = 0
        
        for page_num, page_text in pages_text.items():
            if not page_text.strip():
                continue
            
            sentences = self._split_into_sentences(page_text)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                sentence_tokens = self.count_tokens(sentence)
                
                if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                    chunk = self._create_chunk_dict(
                        content=current_chunk,
                        chunk_index=chunk_index,
                        pages=current_pages
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    
                    overlap_text = self._get_overlap_text(current_chunk)
                    current_chunk = overlap_text + " " + sentence if overlap_text else sentence
                    current_tokens = self.count_tokens(current_chunk)
                    current_pages = [page_num]
                else:
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
                    
                    current_tokens = self.count_tokens(current_chunk)
                    
                    if page_num not in current_pages:
                        current_pages.append(page_num)
        
        if current_chunk.strip():
            chunk = self._create_chunk_dict(
                content=current_chunk,
                chunk_index=chunk_index,
                pages=current_pages
            )
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks from {len(pages_text)} pages")
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from the end of current chunk"""
        tokens = self.encoding.encode(text)
        if len(tokens) <= self.chunk_overlap:
            return text
        
        overlap_tokens = tokens[-self.chunk_overlap:]
        overlap_text = self.encoding.decode(overlap_tokens)
        
        words = overlap_text.split()
        if len(words) > 1:
            return ' '.join(words[1:])
        
        return overlap_text
    
    def _create_chunk_dict(self, content: str, chunk_index: int, pages: List[int]) -> Dict:
        """Create chunk dictionary with metadata"""
        return {
            'content': content,
            'chunk_index': chunk_index,
            'page_start': min(pages),
            'page_end': max(pages),
            'token_count': self.count_tokens(content)
        }
    
    def process_pdf_file(self, pdf_path: str) -> Tuple[Dict[int, str], List[Dict], int]:
        """
        Complete PDF processing pipeline
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Tuple of (pages_text, chunks, total_pages)
        """
        logger.info(f"Starting PDF processing for: {pdf_path}")
        
        # Extract text from PDF
        pages_text = self.extract_text_from_pdf(pdf_path)
        total_pages = len(pages_text)
        
        if not pages_text or all(not text.strip() for text in pages_text.values()):
            raise ValueError("No text could be extracted from the PDF")
        
        chunks = self.create_chunks(pages_text)
        
        if not chunks:
            raise ValueError("No chunks could be created from the PDF text")
        
        logger.info(f"PDF processing completed: {total_pages} pages, {len(chunks)} chunks")
        return pages_text, chunks, total_pages


class PDFValidator:
    """Validate PDF files before processing"""
    
    @staticmethod
    def validate_pdf_file(file_path: str) -> Dict[str, any]:
        """
        Validate PDF file and return metadata
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary with validation results and metadata
        """
        try:
            if not os.path.exists(file_path):
                return {'valid': False, 'error': 'File does not exist'}
            
            # Check file size
            file_size = os.path.getsize(file_path)
            max_size = settings.PDF_SETTINGS['MAX_FILE_SIZE']
            
            if file_size > max_size:
                return {
                    'valid': False, 
                    'error': f'File too large: {file_size} bytes (max: {max_size} bytes)'
                }
            
            # Try to open PDF
            doc = fitz.open(file_path)
            page_count = len(doc)
            
            if page_count == 0:
                doc.close()
                return {'valid': False, 'error': 'PDF has no pages'}
            
            # Check if PDF is encrypted
            if doc.needs_pass:
                doc.close()
                return {'valid': False, 'error': 'PDF is password protected'}
            
            # Get basic metadata
            metadata = doc.metadata
            doc.close()
            
            return {
                'valid': True,
                'page_count': page_count,
                'file_size': file_size,
                'metadata': {
                    'title': metadata.get('title', ''),
                    'author': metadata.get('author', ''),
                    'subject': metadata.get('subject', ''),
                    'creator': metadata.get('creator', ''),
                    'producer': metadata.get('producer', ''),
                }
            }
            
        except Exception as e:
            logger.error(f"Error validating PDF {file_path}: {str(e)}")
            return {'valid': False, 'error': f'PDF validation failed: {str(e)}'}


def process_uploaded_pdf(document_id: str) -> bool:
    """
    Process an uploaded PDF document
    
    Args:
        document_id: UUID of the PDFDocument
        
    Returns:
        True if processing succeeded, False otherwise
    """
    from apps.core.models import PDFDocument, DocumentChunk
    
    try:
        document = PDFDocument.objects.get(id=document_id)
        
        # Update status
        document.processing_status = 'processing'
        document.save()
        
        # Validate PDF
        validator = PDFValidator()
        validation_result = validator.validate_pdf_file(document.file_path.path)
        
        if not validation_result['valid']:
            document.processing_status = 'failed'
            document.save()
            logger.error(f"PDF validation failed for {document_id}: {validation_result['error']}")
            return False
        
        # Update total pages
        document.total_pages = validation_result['page_count']
        document.save()
        
        # Process PDF
        processor = PDFProcessor()
        pages_text, chunks, total_pages = processor.process_pdf_file(document.file_path.path)
        
        # Save chunks to database
        chunk_objects = []
        for chunk_data in chunks:
            chunk = DocumentChunk(
                document=document,
                chunk_index=chunk_data['chunk_index'],
                content=chunk_data['content'],
                page_start=chunk_data['page_start'],
                page_end=chunk_data['page_end'],
                token_count=chunk_data['token_count']
            )
            chunk_objects.append(chunk)
        
        DocumentChunk.objects.bulk_create(chunk_objects)
        
        # Update document status
        document.processed = True
        document.processing_status = 'completed'
        document.save()
        
        logger.info(f"Successfully processed PDF {document_id}: {len(chunks)} chunks created")
        return True
        
    except Exception as e:
        logger.error(f"Error processing PDF {document_id}: {str(e)}")
        
        try:
            document = PDFDocument.objects.get(id=document_id)
            document.processing_status = 'failed'
            document.save()
        except:
            pass
        
        return False