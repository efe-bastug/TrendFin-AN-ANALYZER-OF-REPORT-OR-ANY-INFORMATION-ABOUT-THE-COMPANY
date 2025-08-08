"""
Chat API views for handling Q&A interactions
"""

from rest_framework import status, generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from apps.core.models import ChatSession, ChatMessage, PDFDocument
from apps.core.serializers import ChatSessionSerializer, ChatMessageSerializer
from .services import ChatService, RAGService
from .serializers import QuestionSerializer, ChatResponseSerializer, ChatMessageDetailSerializer
import json
import logging

logger = logging.getLogger(__name__)


class ChatSessionListCreateView(generics.ListCreateAPIView):
    """List and create chat sessions"""
    serializer_class = ChatSessionSerializer
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return ChatSession.objects.filter(created_by=self.request.user).order_by('-updated_at')
        return ChatSession.objects.all().order_by('-updated_at')
    
    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)


class ChatSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a chat session"""
    serializer_class = ChatSessionSerializer
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return ChatSession.objects.filter(created_by=self.request.user)
        return ChatSession.objects.all()


class ChatSessionMessagesView(generics.ListAPIView):
    """Get messages for a specific chat session"""
    serializer_class = ChatMessageSerializer
    
    def get_queryset(self):
        session_id = self.kwargs['session_id']
        session = get_object_or_404(ChatSession, id=session_id)
        return ChatMessage.objects.filter(session=session).order_by('created_at')


class AskQuestionView(APIView):
    """Handle question asking with RAG"""
    
    def post(self, request):
        """Process a question and return an answer"""
        serializer = QuestionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            question = serializer.validated_data['question']
            session_id = serializer.validated_data.get('session_id')
            document_ids = serializer.validated_data.get('document_ids')
            stream = serializer.validated_data.get('stream', False)
            
            chat_service = ChatService()
            
            # Oturumu getir ya da gerekirse oluştur
            if session_id:
                try:
                    session = ChatSession.objects.get(id=session_id)
                except ChatSession.DoesNotExist:
                    return Response(
                        {'error': 'Session not found'}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Yeni bir oturum oluştur
                session = chat_service.create_chat_session(
                    title=question[:50] + "..." if len(question) > 50 else question,
                    user=request.user if request.user.is_authenticated else None
                )
            
            # Soruyu işle
            if stream:
                return self._handle_streaming_response(chat_service, session, question, document_ids)
            else:
                return self._handle_regular_response(chat_service, session, question, document_ids)
        
        except Exception as e:
            logger.error(f"Error in AskQuestionView: {str(e)}")
            return Response(
                {'error': 'An error occurred while processing your question'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _handle_regular_response(self, chat_service, session, question, document_ids):
        """Handle non-streaming response"""
        response_data = chat_service.process_user_question(
            session=session,
            question=question,
            document_ids=document_ids,
            stream=False
        )
        
        # Cevabı hazırlayalım
        response_serializer = ChatResponseSerializer(data={
            'session_id': str(session.id),
            'user_message': ChatMessageDetailSerializer(response_data['user_message']).data,
            'assistant_message': ChatMessageDetailSerializer(response_data['assistant_message']).data,
            'citations': [
                {
                    'document_id': str(chunk['document_id']),
                    'document_name': self._get_document_name(chunk['document_id']),
                    'page_start': chunk['page_start'],
                    'page_end': chunk['page_end'],
                    'content_preview': chunk['content'][:200] + '...' if len(chunk['content']) > 200 else chunk['content'],
                    'relevance_score': chunk.get('score', 0.0)
                }
                for chunk in response_data.get('relevant_chunks', [])
            ],
            'has_context': response_data.get('has_context', False)
        })
        
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(response_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _handle_streaming_response(self, chat_service, session, question, document_ids):
        """Handle streaming response"""
        def generate_stream():
            try:
                response_data = chat_service.process_user_question(
                    session=session,
                    question=question,
                    document_ids=document_ids,
                    stream=True
                )
                
                # Önce başlangıç metadatasını gönder
                initial_data = {
                    'type': 'metadata',
                    'session_id': str(session.id),
                    'user_message_id': str(response_data['user_message'].id),
                    'has_context': response_data.get('has_context', False),
                    'citations': [
                        {
                            'document_id': str(chunk['document_id']),
                            'document_name': self._get_document_name(chunk['document_id']),
                            'page_start': chunk['page_start'],
                            'page_end': chunk['page_end'],
                            'content_preview': chunk['content'][:200] + '...' if len(chunk['content']) > 200 else chunk['content'],
                            'relevance_score': chunk.get('score', 0.0)
                        }
                        for chunk in response_data.get('relevant_chunks', [])
                    ]
                }
                yield f"data: {json.dumps(initial_data)}\n\n"
                
                # Cevap içeriğini parça parça akışla gönder
                full_answer = ""
                for chunk in response_data.get('answer_stream', []):
                    full_answer += chunk
                    chunk_data = {
                        'type': 'content',
                        'content': chunk
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                
                # Tam oluşan asistan mesajını kaydet
                assistant_message = chat_service.add_message_to_session(
                    session, full_answer, 'assistant'
                )
                
                # Kaynakları oluştur
                if response_data.get('relevant_chunks'):
                    chat_service._create_citations(assistant_message, response_data['relevant_chunks'])
                
                # Tamamlandığını bildiren mesajı gönder
                completion_data = {
                    'type': 'completion',
                    'assistant_message_id': str(assistant_message.id)
                }
                yield f"data: {json.dumps(completion_data)}\n\n"
                
            except Exception as e:
                logger.error(f"Error in streaming response: {str(e)}")
                error_data = {
                    'type': 'error',
                    'error': 'An error occurred while generating the response'
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        response = StreamingHttpResponse(
            generate_stream(),
            content_type='text/plain'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
    
    def _get_document_name(self, document_id):
        """Get document name by ID"""
        try:
            document = PDFDocument.objects.get(id=document_id)
            return document.name
        except PDFDocument.DoesNotExist:
            return "Unknown document"


class QuickAnswerView(APIView):
    """Quick answer endpoint without session management"""
    
    def post(self, request):
        """Get a quick answer to a question"""
        question = request.data.get('question')
        document_ids = request.data.get('document_ids')
        
        if not question:
            return Response(
                {'error': 'Question is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            rag_service = RAGService()
            response_data = rag_service.answer_question(
                question=question,
                document_ids=document_ids,
                stream=False
            )
            
            return Response({
                'question': question,
                'answer': response_data.get('answer', 'I do not know'),
                'has_context': response_data.get('has_context', False),
                'citations': [
                    {
                        'document_id': str(chunk['document_id']),
                        'document_name': self._get_document_name(chunk['document_id']),
                        'page_start': chunk['page_start'],
                        'page_end': chunk['page_end'],
                        'content_preview': chunk['content'][:200] + '...' if len(chunk['content']) > 200 else chunk['content'],
                        'relevance_score': chunk.get('score', 0.0)
                    }
                    for chunk in response_data.get('relevant_chunks', [])
                ]
            })
        
        except Exception as e:
            logger.error(f"Error in QuickAnswerView: {str(e)}")
            return Response(
                {'error': 'An error occurred while processing your question'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_document_name(self, document_id):
        """Get document name by ID"""
        try:
            document = PDFDocument.objects.get(id=document_id)
            return document.name
        except PDFDocument.DoesNotExist:
            return "Unknown document"


@api_view(['GET'])
def chat_stats(request):
    """Get chat statistics"""
    try:
        queryset = ChatSession.objects.all()
        
        if request.user.is_authenticated:
            queryset = queryset.filter(created_by=request.user)
        
        stats = {
            'total_sessions': queryset.count(),
            'total_messages': ChatMessage.objects.filter(session__in=queryset).count(),
            'active_sessions': queryset.filter(messages__isnull=False).distinct().count(),
        }
        
        return Response(stats)
    
    except Exception as e:
        logger.error(f"Error getting chat stats: {str(e)}")
        return Response(
            {'error': 'Could not retrieve chat statistics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
def clear_chat_history(request):
    """Clear all chat history for the user"""
    try:
        queryset = ChatSession.objects.all()
        
        if request.user.is_authenticated:
            queryset = queryset.filter(created_by=request.user)
        
        session_count = queryset.count()
        message_count = ChatMessage.objects.filter(session__in=queryset).count()
        
        queryset.delete()
        
        return Response({
            'message': 'Chat history cleared successfully',
            'deleted_sessions': session_count,
            'deleted_messages': message_count
        })
    
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}")
        return Response(
            {'error': 'Could not clear chat history'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )