from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from apps.core.models import PDFDocument, DocumentChunk, ChatSession, ChatMessage, Citation
import uuid


class PDFDocumentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_pdf_document_creation(self):
        """Test PDF document creation"""
        document = PDFDocument.objects.create(
            name='Test Document',
            original_filename='test.pdf',
            size=1024000,
            uploaded_at=timezone.now(),
            created_by=self.user
        )
        
        self.assertEqual(document.name, 'Test Document')
        self.assertEqual(document.size, 1024000)
        self.assertEqual(document.processing_status, 'pending')
        self.assertFalse(document.processed)
        
    def test_pdf_document_str(self):
        """Test PDF document string representation"""
        document = PDFDocument.objects.create(
            name='Test Document',
            original_filename='test.pdf',
            size=1024000,
            created_by=self.user
        )
        
        expected_str = f"Test Document (1024000 bytes)"
        self.assertEqual(str(document), expected_str)


class DocumentChunkModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.document = PDFDocument.objects.create(
            name='Test Document',
            original_filename='test.pdf',
            size=1024000,
            created_by=self.user
        )
        
    def test_document_chunk_creation(self):
        """Test document chunk creation"""
        chunk = DocumentChunk.objects.create(
            document=self.document,
            chunk_index=1,
            content='This is test content for the chunk.',
            page_start=1,
            page_end=2,
            token_count=10,
            vector_id='test_vector_id'
        )
        
        self.assertEqual(chunk.document, self.document)
        self.assertEqual(chunk.chunk_index, 1)
        self.assertEqual(chunk.content, 'This is test content for the chunk.')
        self.assertEqual(chunk.page_start, 1)
        self.assertEqual(chunk.page_end, 2)
        self.assertEqual(chunk.token_count, 10)
        self.assertEqual(chunk.vector_id, 'test_vector_id')
        
    def test_document_chunk_str(self):
        """Test document chunk string representation"""
        chunk = DocumentChunk.objects.create(
            document=self.document,
            chunk_index=1,
            content='Test content',
            page_start=1,
            page_end=2,
            token_count=10
        )
        
        expected_str = f"Chunk 1 of Test Document"
        self.assertEqual(str(chunk), expected_str)


class ChatSessionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_chat_session_creation(self):
        """Test chat session creation"""
        session = ChatSession.objects.create(
            title='Test Chat Session',
            created_by=self.user
        )
        
        self.assertEqual(session.title, 'Test Chat Session')
        self.assertEqual(session.created_by, self.user)
        self.assertIsNotNone(session.created_at)
        self.assertIsNotNone(session.updated_at)
        
    def test_chat_session_str(self):
        """Test chat session string representation"""
        session = ChatSession.objects.create(
            title='Test Chat Session',
            created_by=self.user
        )
        
        self.assertEqual(str(session), 'Test Chat Session')
        
    def test_chat_session_auto_title(self):
        """Test automatic title generation"""
        session = ChatSession.objects.create(created_by=self.user)
        
        # Should have a default title
        self.assertIsNotNone(session.title)
        self.assertIn('Chat', session.title)


class ChatMessageModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.session = ChatSession.objects.create(
            title='Test Chat Session',
            created_by=self.user
        )
        
    def test_chat_message_creation(self):
        """Test chat message creation"""
        message = ChatMessage.objects.create(
            session=self.session,
            role='user',
            content='Hello, how are you?',
            tokens_used=10
        )
        
        self.assertEqual(message.session, self.session)
        self.assertEqual(message.role, 'user')
        self.assertEqual(message.content, 'Hello, how are you?')
        self.assertEqual(message.tokens_used, 10)
        self.assertIsNotNone(message.created_at)
        
    def test_chat_message_str(self):
        """Test chat message string representation"""
        message = ChatMessage.objects.create(
            session=self.session,
            role='user',
            content='Hello, how are you?'
        )
        
        expected_str = f"user: Hello, how are you?"
        self.assertEqual(str(message), expected_str)


class CitationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.document = PDFDocument.objects.create(
            name='Test Document',
            original_filename='test.pdf',
            size=1024000,
            created_by=self.user
        )
        self.chunk = DocumentChunk.objects.create(
            document=self.document,
            chunk_index=1,
            content='Test content',
            page_start=1,
            page_end=2,
            token_count=10
        )
        self.session = ChatSession.objects.create(
            title='Test Chat Session',
            created_by=self.user
        )
        self.message = ChatMessage.objects.create(
            session=self.session,
            role='assistant',
            content='This is an answer with citations.'
        )
        
    def test_citation_creation(self):
        """Test citation creation"""
        citation = Citation.objects.create(
            message=self.message,
            chunk=self.chunk,
            relevance_score=0.95
        )
        
        self.assertEqual(citation.message, self.message)
        self.assertEqual(citation.chunk, self.chunk)
        self.assertEqual(citation.relevance_score, 0.95)
        self.assertIsNotNone(citation.created_at)
        
    def test_citation_str(self):
        """Test citation string representation"""
        citation = Citation.objects.create(
            message=self.message,
            chunk=self.chunk,
            relevance_score=0.95
        )
        
        expected_str = f"Citation for message {self.message.id} -> chunk {self.chunk.id}"
        self.assertEqual(str(citation), expected_str) 