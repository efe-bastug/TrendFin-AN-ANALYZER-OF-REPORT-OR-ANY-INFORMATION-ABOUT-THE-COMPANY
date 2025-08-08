from rest_framework import serializers
from django.conf import settings
from django.core.files.storage import default_storage
from .models import PDFDocument, DocumentChunk, ChatSession, ChatMessage, Citation
import os


class PDFDocumentSerializer(serializers.ModelSerializer):
    """Serializer for PDF document upload and display"""
    file_url = serializers.SerializerMethodField()
    processing_progress = serializers.SerializerMethodField()
    
    class Meta:
        model = PDFDocument
        fields = [
            'id', 'name', 'original_filename', 'size', 
            'uploaded_at', 'processed', 'processing_status', 
            'total_pages', 'file_url', 'processing_progress', 'file_path'
        ]
        read_only_fields = [
            'id', 'uploaded_at', 'processed', 'processing_status', 
            'total_pages', 'processing_progress'
        ]

    def get_file_url(self, obj):
        # PDF dosyasına erişmek için URL üret
        if obj.file_path:
            return f"/media/{obj.file_path}"
        return None

    def get_processing_progress(self, obj):
        # Oluşturulan parçalara göre işleme ilerlemesini hesapla
        if not obj.processed and obj.processing_status == 'processing':
            total_chunks = obj.chunks.count()
            return {
                'chunks_created': total_chunks,
                'estimated_total': None,  # İşleme sırasında hesaplanacak
                'percentage': None
            }
        elif obj.processed:
            return {
                'chunks_created': obj.chunks.count(),
                'estimated_total': obj.chunks.count(),
                'percentage': 100
            }
        return None

    def validate_file_path(self, value):
        # Yüklenen PDF dosyasını doğrula
        if not value:
            raise serializers.ValidationError("No file provided.")
        
        # Dosya uzantısını kontrol et
        file_ext = os.path.splitext(value.name)[1].lower()
        if file_ext not in settings.PDF_SETTINGS['ALLOWED_EXTENSIONS']:
            raise serializers.ValidationError(
                f"Invalid file type. Only {', '.join(settings.PDF_SETTINGS['ALLOWED_EXTENSIONS'])} files are allowed."
            )
        
        # Dosya boyutunu kontrol et
        if value.size > settings.PDF_SETTINGS['MAX_FILE_SIZE']:
            max_size_mb = settings.PDF_SETTINGS['MAX_FILE_SIZE'] / (1024 * 1024)
            raise serializers.ValidationError(f"File size must be less than {max_size_mb}MB.")
        
        return value

    def create(self, validated_data):
        # Meta verilerle PDF belgesi oluştur
        file_obj = validated_data['file_path']
        validated_data['original_filename'] = file_obj.name
        validated_data['size'] = file_obj.size
        
        # İsim verilmemişse ayarla
        if not validated_data.get('name'):
            validated_data['name'] = os.path.splitext(file_obj.name)[0]
        
        # Dosyayı media dizinine kaydet
        file_path = default_storage.save(f'pdfs/{file_obj.name}', file_obj)
        validated_data['file_path'] = file_path
        
        return super().create(validated_data)


class PDFDocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing PDF documents"""
    file_url = serializers.SerializerMethodField()
    chunks_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PDFDocument
        fields = [
            'id', 'name', 'original_filename', 'size',
            'uploaded_at', 'processed', 'processing_status',
            'total_pages', 'file_url', 'chunks_count'
        ]

    def get_file_url(self, obj):
        if obj.file_path:
            return f"/media/{obj.file_path}"
        return None

    def get_chunks_count(self, obj):
        return obj.chunks.count()


class DocumentChunkSerializer(serializers.ModelSerializer):
    """Serializer for document chunks"""
    document_name = serializers.CharField(source='document.name', read_only=True)
    
    class Meta:
        model = DocumentChunk
        fields = [
            'id', 'document', 'document_name', 'chunk_index',
            'content', 'page_start', 'page_end', 'token_count',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'document_name']


class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for chat sessions"""
    messages_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'title', 'created_at', 'updated_at',
            'messages_count', 'last_message'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_messages_count(self, obj):
        return obj.messages.count()

    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'content': last_msg.content[:100] + '...' if len(last_msg.content) > 100 else last_msg.content,
                'role': last_msg.role,
                'created_at': last_msg.created_at
            }
        return None


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages"""
    citations = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'session', 'role', 'content', 
            'tokens_used', 'created_at', 'citations'
        ]
        read_only_fields = ['id', 'created_at', 'citations']

    def get_citations(self, obj):
        # Bu mesaj için kaynakları getir
        citations = obj.citations.select_related('chunk__document').all()
        return [
            {
                'id': citation.id,
                'document_name': citation.chunk.document.name,
                'document_id': citation.chunk.document.id,
                'page_start': citation.chunk.page_start,
                'page_end': citation.chunk.page_end,
                'relevance_score': citation.relevance_score,
                'content_preview': citation.chunk.content[:200] + '...' if len(citation.chunk.content) > 200 else citation.chunk.content
            }
            for citation in citations
        ]


class CitationSerializer(serializers.ModelSerializer):
    """Serializer for citations"""
    document_name = serializers.CharField(source='chunk.document.name', read_only=True)
    document_id = serializers.UUIDField(source='chunk.document.id', read_only=True)
    chunk_content = serializers.CharField(source='chunk.content', read_only=True)
    
    class Meta:
        model = Citation
        fields = [
            'id', 'message', 'chunk', 'relevance_score',
            'document_name', 'document_id', 'chunk_content',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PDFUploadSerializer(serializers.Serializer):
    """Serializer specifically for handling multiple PDF uploads"""
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False,
        max_length=10  # Maximum 10 files at once
    )
    
    def validate_files(self, files):
        """Validate multiple PDF files"""
        validated_files = []
        
        for file_obj in files:
            # Check file extension
            file_ext = os.path.splitext(file_obj.name)[1].lower()
            if file_ext not in settings.PDF_SETTINGS['ALLOWED_EXTENSIONS']:
                raise serializers.ValidationError(
                    f"Invalid file type for '{file_obj.name}'. Only PDF files are allowed."
                )
            
            # Check file size
            if file_obj.size > settings.PDF_SETTINGS['MAX_FILE_SIZE']:
                max_size_mb = settings.PDF_SETTINGS['MAX_FILE_SIZE'] / (1024 * 1024)
                raise serializers.ValidationError(
                    f"File '{file_obj.name}' is too large. Maximum size is {max_size_mb}MB."
                )
            
            validated_files.append(file_obj)
        
        return validated_files