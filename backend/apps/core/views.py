from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view, parser_classes, action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.files.storage import default_storage
import os
import logging
from typing import List

from .models import PDFDocument, DocumentChunk, ChatSession, ChatMessage
from .serializers import (
    PDFDocumentSerializer, PDFDocumentListSerializer,
    DocumentChunkSerializer, ChatSessionSerializer, 
    ChatMessageSerializer, PDFUploadSerializer
)

logger = logging.getLogger(__name__)


class PDFDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing PDF documents"""
    queryset = PDFDocument.objects.all()
    parser_classes = [MultiPartParser, FormParser]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PDFDocumentListSerializer
        return PDFDocumentSerializer
    
    def get_queryset(self):
        # Kullanıcı doğrulanmışsa belgelere göre filtrele
        queryset = PDFDocument.objects.all()
        if self.request.user.is_authenticated:
            queryset = queryset.filter(created_by=self.request.user)
        return queryset.order_by('-uploaded_at')

    def perform_create(self, serializer):
        # Belge oluşturulurken kullanıcıyı ayarla
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)

    def create(self, request, *args, **kwargs):
        # Oluşturma metodunu ezerek debug logu ekle ve işlemeyi başlat
        logger.info(f"PDF upload request received: {request.data}")
        try:
            response = super().create(request, *args, **kwargs)
            
            # PDF işlemeyi arka planda başlat
            if response.status_code == 201:
                document_id = response.data['id']
                logger.info(f"Starting PDF processing for document: {document_id}")
                
                # Dairesel importları önlemek için burada import et
                from .services import process_pdf_upload
                import threading
                
                # Arka plan thread'inde işle
                thread = threading.Thread(
                    target=process_pdf_upload,
                    args=(document_id,)
                )
                thread.daemon = True
                thread.start()
            
            return response
        except Exception as e:
            logger.error(f"PDF upload error: {str(e)}")
            raise

    @action(detail=True, methods=['get'])
    def chunks(self, request, pk=None):
        # Belirli bir belgenin parçalarını getir
        document = self.get_object()
        chunks = DocumentChunk.objects.filter(document=document).order_by('chunk_index')
        serializer = DocumentChunkSerializer(chunks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        # Bir belgenin yeniden işlenmesini tetikle
        document = self.get_object()
        
        if document.processing_status == 'processing':
            return Response(
                {'error': 'Document is already being processed'},
                status=status.HTTP_409_CONFLICT
            )
        
        # İşleme durumunu sıfırla
        document.processing_status = 'pending'
        document.processed = False
        document.save()
        
        # Mevcut parçaları sil
        document.chunks.all().delete()
        
        # İşlemeyi tetikle (normalde arka plan görevi yapar)
        # Şimdilik sadece durumu güncelliyoruz
        document.processing_status = 'processing'
        document.save()
        
        return Response({'message': 'Document reprocessing started'})


class MultiPDFUploadView(APIView):
    """Handle multiple PDF file uploads"""
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, *args, **kwargs):
        """Upload multiple PDF files"""
        serializer = PDFUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        files = serializer.validated_data['files']
        uploaded_documents = []
        errors = []
        
        for file_obj in files:
            try:
        # Belge örneği oluştur
                document_data = {
                    'file_path': file_obj,
                    'name': os.path.splitext(file_obj.name)[0],
                    'original_filename': file_obj.name,
                    'size': file_obj.size
                }
                
                doc_serializer = PDFDocumentSerializer(data=document_data)
                if doc_serializer.is_valid():
                    document = doc_serializer.save(
                        created_by=request.user if request.user.is_authenticated else None
                    )
                    uploaded_documents.append(doc_serializer.data)
                    
                    # Başarılı yüklemeyi logla
                    logger.info(f"PDF uploaded successfully: {file_obj.name} (ID: {document.id})")
                    
                else:
                    errors.append({
                        'filename': file_obj.name,
                        'errors': doc_serializer.errors
                    })
                    
            except Exception as e:
                logger.error(f"Error uploading {file_obj.name}: {str(e)}")
                errors.append({
                    'filename': file_obj.name,
                    'errors': {'general': [str(e)]}
                })
        
        response_data = {
            'uploaded': uploaded_documents,
            'uploaded_count': len(uploaded_documents),
            'total_count': len(files),
            'errors': errors
        }
        
        if errors and not uploaded_documents:
            # Tüm yüklemeler başarısız oldu
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        elif errors:
            # Kısmi başarı
            return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
        else:
            # Hepsi başarılı
            return Response(response_data, status=status.HTTP_201_CREATED)


class PDFUploadProgressView(APIView):
    """Check upload and processing progress"""
    
    def get(self, request, document_id):
        """Get processing progress for a document"""
        try:
            document = PDFDocument.objects.get(id=document_id)
        except PDFDocument.DoesNotExist:
            raise Http404("Document not found")
        
        # İlerlemeyi hesapla
        if document.processed:
            progress = {
                'status': 'completed',
                'progress': 100,
                'chunks_created': document.chunks.count(),
                'total_pages': document.total_pages,
                'message': 'Document processing completed successfully'
            }
        elif document.processing_status == 'failed':
            progress = {
                'status': 'failed',
                'progress': 0,
                'message': 'Document processing failed',
                'chunks_created': document.chunks.count()
            }
        elif document.processing_status == 'processing':
            chunks_count = document.chunks.count()
            # Oluşturulan parçalara göre ilerlemeyi tahmin et
            estimated_progress = min(95, chunks_count * 10)  # Kabaca bir tahmin
            progress = {
                'status': 'processing',
                'progress': estimated_progress,
                'chunks_created': chunks_count,
                'message': f'Processing document... Created {chunks_count} chunks'
            }
        else:
            progress = {
                'status': 'pending',
                'progress': 0,
                'message': 'Document is queued for processing'
            }
        
        return Response(progress)


class DocumentStatsView(APIView):
        """Get statistics about uploaded documents"""
    
    def get(self, request):
        """Return document statistics"""
        queryset = PDFDocument.objects.all()
        
        # Kullanıcı doğrulanmışsa kullanıcıya göre filtrele
        if request.user.is_authenticated:
            queryset = queryset.filter(created_by=request.user)
        
        stats = {
            'total_documents': queryset.count(),
            'processed_documents': queryset.filter(processed=True).count(),
            'processing_documents': queryset.filter(processing_status='processing').count(),
            'failed_documents': queryset.filter(processing_status='failed').count(),
            'total_size_bytes': sum(doc.size for doc in queryset),
            'total_chunks': sum(doc.chunks.count() for doc in queryset),
            'total_pages': sum(doc.total_pages or 0 for doc in queryset),
        }
        
        # Okunabilirlik için baytı MB'a çevir
        stats['total_size_mb'] = round(stats['total_size_bytes'] / (1024 * 1024), 2)
        
        return Response(stats)


@api_view(['DELETE'])
def delete_document(request, document_id):
    """Delete a PDF document and its associated data"""
    try:
        document = PDFDocument.objects.get(id=document_id)
        
        # İzinleri kontrol et (kullanıcı doğrulaması etkinse)
        if request.user.is_authenticated and document.created_by != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Dosyayı depolamadan sil
        if document.file_path:
            try:
                default_storage.delete(document.file_path.name)
            except Exception as e:
                logger.warning(f"Could not delete file {document.file_path.name}: {e}")
        
        # Parçaları sil (ilişkili verileri kaskad silme halleder)
        chunks_count = document.chunks.count()
        document.delete()
        
        logger.info(f"Document deleted: {document.name} (ID: {document_id}, Chunks: {chunks_count})")
        
        return Response({
            'message': 'Document deleted successfully',
            'deleted_chunks': chunks_count
        })
        
    except PDFDocument.DoesNotExist:
        raise Http404("Document not found")


@api_view(['GET'])
def health_check(request):
    """Simple health check endpoint"""
    return Response({
        'status': 'healthy',
        'service': 'pdf-qa-api',
        'version': '1.0.0'
    })


class ChatSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing chat sessions"""
    queryset = ChatSession.objects.all()
    serializer_class = ChatSessionSerializer
    
    def get_queryset(self):
        # Oturumları, kullanıcı doğrulanmışsa kullanıcıya göre filtrele
        queryset = ChatSession.objects.all()
        if self.request.user.is_authenticated:
            queryset = queryset.filter(created_by=self.request.user)
        return queryset.order_by('-updated_at')

    def perform_create(self, serializer):
        # Oturum oluştururken kullanıcıyı ayarla
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        # Belirli bir sohbet oturumunun mesajlarını getir
        session = self.get_object()
        messages = ChatMessage.objects.filter(session=session).order_by('created_at')
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)


class ChatMessageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing chat messages"""
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer
    
    def get_queryset(self):
        # Mesajları oturuma ya da kullanıcıya göre filtrele
        queryset = ChatMessage.objects.all()
        
        session_id = self.request.query_params.get('session', None)
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        if self.request.user.is_authenticated:
            queryset = queryset.filter(session__created_by=self.request.user)
        
        return queryset.order_by('created_at')