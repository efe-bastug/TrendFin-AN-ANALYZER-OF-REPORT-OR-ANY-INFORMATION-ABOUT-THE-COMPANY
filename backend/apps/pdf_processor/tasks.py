"""
Background tasks for PDF processing and embedding creation
This module handles asynchronous processing of uploaded PDFs
"""

import logging
from typing import Optional
from django.conf import settings
from apps.core.models import PDFDocument, ProcessingLog
from .utils import process_uploaded_pdf
from apps.vector_store.client import store_document_chunks

logger = logging.getLogger(__name__)


def process_pdf_document(document_id: str) -> bool:
    """
    Complete PDF processing pipeline: extract text, create chunks, and store embeddings
    
    Args:
        document_id: UUID of the PDFDocument to process
        
    Returns:
        True if processing successful, False otherwise
    """
    logger.info(f"Starting PDF processing for document {document_id}")
    
    try:
        document = PDFDocument.objects.get(id=document_id)
        
        ProcessingLog.objects.create(
            document=document,
            operation='pdf_processing',
            level='info',
            message='Started PDF processing pipeline'
        )
        
        logger.info(f"Step 1: Processing PDF file for document {document_id}")
        pdf_success = process_uploaded_pdf(document_id)
        
        if not pdf_success:
            ProcessingLog.objects.create(
                document=document,
                operation='pdf_processing',
                level='error',
                message='Failed to extract text and create chunks from PDF'
            )
            return False
        
        ProcessingLog.objects.create(
            document=document,
            operation='pdf_processing',
            level='info',
            message=f'Successfully created {document.chunks.count()} chunks from PDF'
        )
        
        logger.info(f"Step 2: Creating embeddings for document {document_id}")
        embedding_success = store_document_chunks(document_id)
        
        if not embedding_success:
            ProcessingLog.objects.create(
                document=document,
                operation='embedding_creation',
                level='error',
                message='Failed to create and store embeddings'
            )
            logger.warning(f"Embeddings failed for document {document_id}, but chunks were created")
        else:
            ProcessingLog.objects.create(
                document=document,
                operation='embedding_creation',
                level='info',
                message='Successfully created and stored embeddings'
            )
        
        ProcessingLog.objects.create(
            document=document,
            operation='pdf_processing',
            level='info',
            message='PDF processing pipeline completed successfully',
            details={
                'chunks_created': document.chunks.count(),
                'embeddings_created': embedding_success,
                'total_pages': document.total_pages
            }
        )
        
        logger.info(f"Completed PDF processing for document {document_id}")
        return True
        
    except PDFDocument.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return False
        
    except Exception as e:
        logger.error(f"Error processing PDF document {document_id}: {str(e)}")
        
        try:
            document = PDFDocument.objects.get(id=document_id)
            ProcessingLog.objects.create(
                document=document,
                operation='pdf_processing',
                level='error',
                message=f'PDF processing failed: {str(e)}',
                details={'error_type': type(e).__name__}
            )
            
            # Update document status
            document.processing_status = 'failed'
            document.save()
            
        except Exception as log_error:
            logger.error(f"Failed to log processing error: {str(log_error)}")
        
        return False


def reprocess_document(document_id: str) -> bool:
    """
    Reprocess an existing document (useful for updating chunk size or fixing errors)
    
    Args:
        document_id: UUID of the PDFDocument to reprocess
        
    Returns:
        True if reprocessing successful, False otherwise
    """
    logger.info(f"Starting document reprocessing for {document_id}")
    
    try:
        document = PDFDocument.objects.get(id=document_id)
        
        ProcessingLog.objects.create(
            document=document,
            operation='reprocessing',
            level='info',
            message='Started document reprocessing'
        )
        
        document.processing_status = 'processing'
        document.processed = False
        document.save()
        
        old_chunks_count = document.chunks.count()
        if old_chunks_count > 0:
            from apps.vector_store.client import VectorStoreClient
            vector_client = VectorStoreClient()
            vector_client.delete_document_embeddings(str(document_id))
            
            document.chunks.all().delete()
            
            logger.info(f"Deleted {old_chunks_count} existing chunks for document {document_id}")
        
        success = process_pdf_document(document_id)
        
        if success:
            ProcessingLog.objects.create(
                document=document,
                operation='reprocessing',
                level='info',
                message='Document reprocessing completed successfully',
                details={
                    'old_chunks_count': old_chunks_count,
                    'new_chunks_count': document.chunks.count()
                }
            )
        
        return success
        
    except PDFDocument.DoesNotExist:
        logger.error(f"Document {document_id} not found for reprocessing")
        return False
        
    except Exception as e:
        logger.error(f"Error reprocessing document {document_id}: {str(e)}")
        return False


def cleanup_failed_documents():
    """
    Clean up documents that have been stuck in processing state
    This is a maintenance task that can be run periodically
    """
    from django.utils import timezone
    from datetime import timedelta
    
    logger.info("Starting cleanup of failed documents")
    
    try:
        cutoff_time = timezone.now() - timedelta(hours=1)
        stuck_documents = PDFDocument.objects.filter(
            processing_status='processing',
            uploaded_at__lt=cutoff_time
        )
        
        count = 0
        for document in stuck_documents:
            logger.warning(f"Marking document {document.id} as failed (stuck in processing)")
            
            document.processing_status = 'failed'
            document.save()
            
            ProcessingLog.objects.create(
                document=document,
                operation='cleanup',
                level='warning',
                message='Document marked as failed due to processing timeout'
            )
            
            count += 1
        
        logger.info(f"Cleanup completed: marked {count