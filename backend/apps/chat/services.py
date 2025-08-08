"""
Chat services for Retrieval-Augmented Generation (RAG)
Handles question answering using document context and LLM
"""

import openai
from typing import List, Dict, Optional, Generator
from django.conf import settings
from apps.core.models import PDFDocument, DocumentChunk, ChatSession, ChatMessage, Citation
from apps.vector_store.client import search_relevant_chunks
from apps.vector_store.reranker import reranker_service
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class RAGService:
    """Service for Retrieval-Augmented Generation"""
    
    def __init__(self):
        self.mock_mode = getattr(settings, 'MOCK_MODE', False)
        if not self.mock_mode:
            openai.api_key = settings.OPENAI_API_KEY
        self.llm_model = settings.OPENAI_SETTINGS['LLM_MODEL']
        self.max_tokens = settings.OPENAI_SETTINGS['MAX_ANSWER_TOKENS']
        self.temperature = settings.OPENAI_SETTINGS['TEMPERATURE']
        self.top_k_chunks = settings.PDF_SETTINGS['TOP_K_CHUNKS']
    
    def answer_question(
        self, 
        question: str, 
        document_ids: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        stream: bool = True
    ) -> Dict:
        """
        Answer a question using RAG approach
        
        Args:
            question: User's question
            document_ids: Optional list of document IDs to search within
            session_id: Optional chat session ID
            stream: Whether to stream the response
            
        Returns:
            Dictionary containing answer, citations, and metadata
        """
        try:
            logger.info(f"Processing question: {question[:50]}...")
            
            # Mock mode for testing
            if self.mock_mode:
                return self._mock_response(question, stream)
            
            # Step 1: Retrieve relevant chunks
            relevant_chunks = self._retrieve_relevant_chunks(question, document_ids)
            
            if not relevant_chunks:
                return self._handle_no_context(question, session_id)
            
            # Step 2: Generate answer using LLM
            if stream:
                response_generator = self._generate_streaming_answer(question, relevant_chunks)
                return {
                    'answer_stream': response_generator,
                    'relevant_chunks': relevant_chunks,
                    'has_context': True
                }
            else:
                answer = self._generate_answer(question, relevant_chunks)
                return {
                    'answer': answer,
                    'relevant_chunks': relevant_chunks,
                    'has_context': True
                }
        
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            return {
                'answer': "I apologize, but I encountered an error while processing your question. Please try again.",
                'relevant_chunks': [],
                'has_context': False,
                'error': str(e)
            }
    
    def _retrieve_relevant_chunks(self, question: str, document_ids: Optional[List[str]] = None) -> List[Dict]:
        """Retrieve relevant document chunks for the question"""
        try:
            # Search for relevant chunks
            chunks = search_relevant_chunks(
                query=question,
                document_ids=document_ids,
                limit=self.top_k_chunks * 2  # Get more chunks for reranking
            )
            
            # Return all chunks without reranking for now
            logger.info(f"Retrieved {len(chunks)} relevant chunks (from {len(chunks)} total)")
            return chunks[:self.top_k_chunks]  # Return top k chunks
            
        except Exception as e:
            logger.error(f"Error retrieving chunks: {str(e)}")
            return []
    
    def _generate_answer(self, question: str, relevant_chunks: List[Dict]) -> str:
        """Generate answer using OpenAI LLM"""
        try:
            # Build context from relevant chunks
            context = self._build_context(relevant_chunks)
            
            # Create system prompt
            system_prompt = self._create_system_prompt()
            
            # Create user prompt with context
            user_prompt = self._create_user_prompt(question, context)
            
            # Call OpenAI API
            response = openai.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            answer = response.choices[0].message.content.strip()
            logger.info(f"Generated answer of {len(answer)} characters")
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            return "I apologize, but I couldn't generate an answer at this time. Please try again."
    
    def _generate_streaming_answer(self, question: str, relevant_chunks: List[Dict]) -> Generator[str, None, None]:
        """Generate streaming answer using OpenAI LLM"""
        try:
            # Build context from relevant chunks
            context = self._build_context(relevant_chunks)
            
            # Create system prompt
            system_prompt = self._create_system_prompt()
            
            # Create user prompt with context
            user_prompt = self._create_user_prompt(question, context)
            
            # Call OpenAI API with streaming
            response = openai.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
            
        except Exception as e:
            logger.error(f"Error generating streaming answer: {str(e)}")
            yield "I apologize, but I couldn't generate an answer at this time. Please try again."
    
    def _build_context(self, relevant_chunks: List[Dict]) -> str:
        """Build context string from relevant chunks"""
        context_parts = []
        
        for i, chunk in enumerate(relevant_chunks, 1):
            # Get document name for the chunk
            try:
                document = PDFDocument.objects.get(id=chunk['document_id'])
                doc_name = document.name
            except PDFDocument.DoesNotExist:
                doc_name = "Unknown document"
            
            context_part = f"""
[Citation {i}] - {doc_name} (Pages {chunk['page_start']}-{chunk['page_end']}):
{chunk['content']}
"""
            context_parts.append(context_part.strip())
        
        return "\n\n".join(context_parts)
    
    def _create_system_prompt(self) -> str:
        """Create system prompt for the LLM"""
        return f"""You are a helpful AI assistant that answers questions based on provided document excerpts. 

Instructions:
1. Answer questions using ONLY the information provided in the citations below
2. If the question cannot be answered using the provided context, respond with "I do not know"
3. Always cite your sources by referencing the citation numbers [1], [2], etc.
4. Be concise but comprehensive in your answers (maximum {self.max_tokens} tokens)
5. Maintain a professional and helpful tone
6. If multiple citations support the same point, reference all relevant citation numbers
7. If the question is irrelevant to the provided documents, respond with "I do not know"

Format your response in clear, readable markdown."""
    
    def _create_user_prompt(self, question: str, context: str) -> str:
        """Create user prompt with question and context"""
        return f"""Context from documents:
{context}

Question: {question}

Please provide a comprehensive answer based on the context above. Remember to cite your sources using the citation numbers provided."""
    
    def _handle_no_context(self, question: str, session_id: Optional[str] = None) -> Dict:
        """Handle cases where no relevant context is found"""
        logger.info("No relevant context found for question")
        
        return {
            'answer': "I do not know",
            'relevant_chunks': [],
            'has_context': False,
            'message': "I couldn't find relevant information in the uploaded documents to answer your question. Please make sure your question relates to the content of the uploaded PDF documents."
        }
    
    def _mock_response(self, question: str, stream: bool = False) -> Dict:
        """Generate mock response for testing"""
        mock_answer = f"This is a mock response for testing. You asked: '{question}'. In a real scenario, I would analyze your uploaded PDF documents and provide an answer based on their content."
        
        if stream:
            def mock_stream():
                words = mock_answer.split()
                for word in words:
                    yield word + " "
                    import time
                    time.sleep(0.1)
            
            return {
                'answer_stream': mock_stream(),
                'relevant_chunks': [],
                'has_context': True,
                'mock': True
            }
        else:
            return {
                'answer': mock_answer,
                'relevant_chunks': [],
                'has_context': True,
                'mock': True
            }


class ChatService:
    """Service for managing chat sessions and messages"""
    
    def __init__(self):
        self.rag_service = RAGService()
    
    def create_chat_session(self, title: Optional[str] = None, user=None) -> ChatSession:
        """Create a new chat session"""
        session = ChatSession.objects.create(
            title=title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            created_by=user
        )
        logger.info(f"Created new chat session: {session.id}")
        return session
    
    def add_message_to_session(
        self, 
        session: ChatSession, 
        content: str, 
        role: str = 'user',
        tokens_used: Optional[int] = None
    ) -> ChatMessage:
        """Add a message to a chat session"""
        message = ChatMessage.objects.create(
            session=session,
            role=role,
            content=content,
            tokens_used=tokens_used
        )
        
        # Update session timestamp
        session.save()  # This triggers updated_at
        
        return message
    
    def process_user_question(
        self, 
        session: ChatSession, 
        question: str,
        document_ids: Optional[List[str]] = None,
        stream: bool = True
    ) -> Dict:
        """Process a user question and generate response"""
        try:
            # Add user message to session
            user_message = self.add_message_to_session(session, question, 'user')
            
            # Generate answer using RAG
            rag_response = self.rag_service.answer_question(
                question=question,
                document_ids=document_ids,
                session_id=str(session.id),
                stream=stream
            )
            
            # Handle mock mode
            if rag_response.get('mock', False):
                # For mock mode, create assistant message with mock response
                answer = rag_response.get('answer', 'Mock response')
                assistant_message = self.add_message_to_session(session, answer, 'assistant')
                
                return {
                    'user_message': user_message,
                    'assistant_message': assistant_message,
                    'relevant_chunks': rag_response.get('relevant_chunks', []),
                    'has_context': rag_response.get('has_context', False)
                }
            
            if stream and 'answer_stream' in rag_response:
                # Return streaming response
                return {
                    'user_message': user_message,
                    'answer_stream': rag_response['answer_stream'],
                    'relevant_chunks': rag_response['relevant_chunks'],
                    'has_context': rag_response['has_context']
                }
            else:
                # Complete answer - save assistant message
                answer = rag_response.get('answer', 'I do not know')
                assistant_message = self.add_message_to_session(session, answer, 'assistant')
                
                # Create citations
                if rag_response.get('relevant_chunks'):
                    self._create_citations(assistant_message, rag_response['relevant_chunks'])
                
                return {
                    'user_message': user_message,
                    'assistant_message': assistant_message,
                    'relevant_chunks': rag_response['relevant_chunks'],
                    'has_context': rag_response['has_context']
                }
        
        except Exception as e:
            logger.error(f"Error processing user question: {str(e)}")
            # Add error message to session
            error_message = self.add_message_to_session(
                session, 
                "I apologize, but I encountered an error while processing your question.", 
                'assistant'
            )
            return {
                'user_message': user_message,
                'assistant_message': error_message,
                'relevant_chunks': [],
                'has_context': False,
                'error': str(e)
            }
    
    def _create_citations(self, message: ChatMessage, relevant_chunks: List[Dict]):
        """Create citation objects linking message to chunks"""
        citations = []
        
        for chunk_data in relevant_chunks:
            try:
                # Find the DocumentChunk object
                chunk = DocumentChunk.objects.get(
                    document_id=chunk_data['document_id'],
                    chunk_index=chunk_data['chunk_index']
                )
                
                citation = Citation(
                    message=message,
                    chunk=chunk,
                    relevance_score=chunk_data.get('score', 0.0)
                )
                citations.append(citation)
                
            except DocumentChunk.DoesNotExist:
                logger.warning(f"Chunk not found for citation: {chunk_data}")
        
        # Bulk create citations
        if citations:
            Citation.objects.bulk_create(citations)
            logger.info(f"Created {len(citations)} citations for message {message.id}")
    
    def get_session_history(self, session: ChatSession) -> List[ChatMessage]:
        """Get chat history for a session"""
        return ChatMessage.objects.filter(session=session).order_by('created_at')
    
    def delete_session(self, session: ChatSession) -> bool:
        """Delete a chat session and all its messages"""
        try:
            message_count = session.messages.count()
            session.delete()
            logger.info(f"Deleted chat session {session.id} with {message_count} messages")
            return True
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            return False