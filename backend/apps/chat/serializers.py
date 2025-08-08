"""
Serializers for chat functionality
"""

from rest_framework import serializers
from apps.core.models import ChatSession, ChatMessage
from typing import List, Optional


class QuestionSerializer(serializers.Serializer):
    """Serializer for asking questions"""
    question = serializers.CharField(max_length=2000, help_text="The question to ask")
    session_id = serializers.UUIDField(required=False, help_text="Chat session ID (optional)")
    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        help_text="List of document IDs to search within (optional)"
    )
    stream = serializers.BooleanField(default=False, help_text="Whether to stream the response")
    
    def validate_question(self, value):
        # Soru içeriğini doğrula
        if not value or not value.strip():
            raise serializers.ValidationError("Question cannot be empty")
        
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Question is too short")
        
        return value.strip()
    
    def validate_document_ids(self, value):
        # Belge kimliklerinin varlığını doğrula
        if value:
            from apps.core.models import PDFDocument
            existing_ids = set(
                PDFDocument.objects.filter(id__in=value).values_list('id', flat=True)
            )
            
            invalid_ids = set(value) - existing_ids
            if invalid_ids:
                raise serializers.ValidationError(
                    f"Documents not found: {list(invalid_ids)}"
                )
        
        return value


class CitationSerializer(serializers.Serializer):
    """Serializer for citation information"""
    document_id = serializers.UUIDField()
    document_name = serializers.CharField()
    page_start = serializers.IntegerField()
    page_end = serializers.IntegerField()
    content_preview = serializers.CharField()
    relevance_score = serializers.FloatField()


class ChatMessageDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for chat messages with citations"""
    citations = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'role', 'content', 'tokens_used', 
            'created_at', 'citations'
        ]
    
    def get_citations(self, obj):
        # Asistan mesajları için kaynakları getir
        if hasattr(obj, 'role') and obj.role == 'assistant':
            citations = obj.citations.select_related('chunk__document').all()
            return [
                {
                    'id': citation.id,
                    'document_id': str(citation.chunk.document.id),
                    'document_name': citation.chunk.document.name,
                    'page_start': citation.chunk.page_start,
                    'page_end': citation.chunk.page_end,
                    'content_preview': citation.chunk.content[:200] + '...' if len(citation.chunk.content) > 200 else citation.chunk.content,
                    'relevance_score': citation.relevance_score
                }
                for citation in citations
            ]
        return []


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for chat response"""
    session_id = serializers.UUIDField()
    user_message = ChatMessageDetailSerializer()
    assistant_message = ChatMessageDetailSerializer()
    citations = CitationSerializer(many=True)
    has_context = serializers.BooleanField()


class StreamingChatResponseSerializer(serializers.Serializer):
    """Serializer for streaming chat response metadata"""
    session_id = serializers.UUIDField()
    user_message_id = serializers.UUIDField()
    has_context = serializers.BooleanField()
    citations = CitationSerializer(many=True)


class QuickAnswerSerializer(serializers.Serializer):
    """Serializer for quick answer responses"""
    question = serializers.CharField()
    answer = serializers.CharField()
    has_context = serializers.BooleanField()
    citations = CitationSerializer(many=True)


class ChatStatsSerializer(serializers.Serializer):
    """Serializer for chat statistics"""
    total_sessions = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    active_sessions = serializers.IntegerField()


class BulkQuestionSerializer(serializers.Serializer):
    """Serializer for asking multiple questions at once"""
    questions = serializers.ListField(
        child=serializers.CharField(max_length=2000),
        min_length=1,
        max_length=10,
        help_text="List of questions to ask (max 10)"
    )