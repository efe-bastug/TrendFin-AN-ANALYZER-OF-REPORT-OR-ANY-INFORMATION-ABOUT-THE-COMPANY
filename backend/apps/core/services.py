"""
PDF processing services for extracting text, chunking, and storing embeddings
"""

import fitz  # PyMuPDF
import tiktoken
from typing import List, Dict, Tuple
from django.conf import settings
from .models import PDFDocument, DocumentChunk
from apps.vector_store.client import store_document_chunks
import logging

logger = logging.getLogger(__name__)


class PDFProcessingService:
    """Service for processing PDF documents"""
    
    def __init__(self):
        self.chunk_size = settings.PDF_SETTINGS['CHUNK_SIZE']
        self.chunk_overlap = settings.PDF_SETTINGS['CHUNK_OVERLAP']
        self.encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict]:
        """
        Extract text from PDF with page information
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of dictionaries with page text and metadata
        """
        try:
            doc = fitz.open(pdf_path)
            pages_data = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                
                if text.strip():  # Only include pages with content
                    pages_data.append({
                        'page_number': page_num + 1,
                        'text': text.strip(),
                        'token_count': len(self.encoding.encode(text))
                    })
            
            doc.close()
            logger.info(f"Extracted text from {len(pages_data)} pages")
            return pages_data
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise
    
    def chunk_text(self, pages_data: List[Dict]) -> List[Dict]:
        """
        Split text into overlapping chunks
        
        Args:
            pages_data: List of page data with text
            
        Returns:
            List of chunk data
        """
        chunks = []
        chunk_index = 0
        
        for page_data in pages_data:
            page_text = page_data['text']
            page_number = page_data['page_number']
            
            # Split page text into sentences or paragraphs
            sentences = self._split_into_sentences(page_text)
            
            current_chunk = ""
            current_tokens = 0
            start_page = page_number
            end_page = page_number
            
            for sentence in sentences:
                sentence_tokens = len(self.encoding.encode(sentence))
                
                # If adding this sentence would exceed chunk size
                if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                    # Save current chunk
                    chunks.append({
                        'chunk_index': chunk_index,
                        'content': current_chunk.strip(),
                        'page_start': start_page,
                        'page_end': end_page,
                        'token_count': current_tokens
                    })
                    chunk_index += 1
                    
                    # Start new chunk with overlap
                    overlap_text = self._get_overlap_text(current_chunk, self.chunk_overlap)
                    current_chunk = overlap_text + " " + sentence
                    current_tokens = len(self.encoding.encode(current_chunk))
                    start_page = page_number
                    end_page = page_number
                else:
                    # Add sentence to current chunk
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
                    current_tokens += sentence_tokens
                    end_page = page_number
            
            # Add final chunk from this page
            if current_chunk.strip():
                chunks.append({
                    'chunk_index': chunk_index,
                    'content': current_chunk.strip(),
                    'page_start': start_page,
                    'page_end': end_page,
                    'token_count': current_tokens
                })
                chunk_index += 1
        
        logger.info(f"Created {len(chunks)} chunks from text")
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        import re
        # Simple sentence splitting - can be improved
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_text(self, text: str, overlap_tokens: int) -> str:
        """Get overlap text from the end of a chunk"""
        tokens = self.encoding.encode(text)
        if len(tokens) <= overlap_tokens:
            return text
        
        overlap_tokens_list = tokens[-overlap_tokens:]
        return self.encoding.decode(overlap_tokens_list)
    
    def process_pdf_document(self, document: PDFDocument) -> bool:
        """
        Process a PDF document: extract text, create chunks, store embeddings
        
        Args:
            document: PDFDocument instance
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Processing PDF document: {document.name}")
            
            # Update status
            document.processing_status = 'processing'
            document.save()
            
            # Get full file path
            import os
            file_path = os.path.join(settings.MEDIA_ROOT, str(document.file_path))
            
            # Extract text from PDF
            pages_data = self.extract_text_from_pdf(file_path)
            
            if not pages_data:
                logger.warning(f"No text extracted from PDF: {document.name}")
                document.processing_status = 'failed'
                document.save()
                return False
            
            # Create chunks
            chunks_data = self.chunk_text(pages_data)
            
            if not chunks_data:
                logger.warning(f"No chunks created from PDF: {document.name}")
                document.processing_status = 'failed'
                document.save()
                return False
            
            # Save chunks to database
            for chunk_data in chunks_data:
                DocumentChunk.objects.create(
                    document=document,
                    chunk_index=chunk_data['chunk_index'],
                    content=chunk_data['content'],
                    page_start=chunk_data['page_start'],
                    page_end=chunk_data['page_end'],
                    token_count=chunk_data['token_count']
                )
            
            # Store embeddings in Qdrant
            success = store_document_chunks(str(document.id))
            
            if success:
                document.processed = True
                document.processing_status = 'completed'
                document.total_pages = len(pages_data)
                document.save()
                logger.info(f"Successfully processed PDF: {document.name}")
                return True
            else:
                document.processing_status = 'failed'
                document.save()
                logger.error(f"Failed to store embeddings for: {document.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing PDF {document.name}: {str(e)}")
            document.processing_status = 'failed'
            document.save()
            return False


def process_pdf_upload(document_id: str) -> bool:
    """
    Process a PDF document after upload
    
    Args:
        document_id: UUID of the PDFDocument
        
    Returns:
        True if successful, False otherwise
    """
    try:
        document = PDFDocument.objects.get(id=document_id)
        service = PDFProcessingService()
        return service.process_pdf_document(document)
    except Exception as e:
        logger.error(f"Error in process_pdf_upload: {str(e)}")
        return False 