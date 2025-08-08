from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone


class PDFDocument(models.Model):
    """Model for uploaded PDF documents"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    file_path = models.FileField(upload_to='pdfs/')
    size = models.PositiveIntegerField()  # bayt cinsinden
    uploaded_at = models.DateTimeField(default=timezone.now)
    processed = models.BooleanField(default=False)
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    total_pages = models.PositiveIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'pdf_documents'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.name} ({self.size} bytes)"


class DocumentChunk(models.Model):
    """Model for PDF text chunks with embeddings"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(PDFDocument, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.PositiveIntegerField()  # Order within document
    content = models.TextField()
    page_start = models.PositiveIntegerField()
    page_end = models.PositiveIntegerField()
    token_count = models.PositiveIntegerField()
    vector_id = models.CharField(max_length=255, null=True, blank=True)  # Qdrant vektör ID'si
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'document_chunks'
        unique_together = ['document', 'chunk_index']
        ordering = ['document', 'chunk_index']

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.name}"


class ChatSession(models.Model):
    """Model for chat sessions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-updated_at']

    def __str__(self):
        return self.title or f"Chat {self.id}"

    def save(self, *args, **kwargs):
        if not self.title:
            # Varsa ilk mesajdan başlık üret
            first_message = self.messages.filter(role='user').first()
            if first_message:
                self.title = first_message.content[:50] + "..." if len(first_message.content) > 50 else first_message.content
            else:
                self.title = f"Chat {timezone.now().strftime('%Y-%m-%d %H:%M')}"
        super().save(*args, **kwargs)


class ChatMessage(models.Model):
    """Model for individual chat messages"""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    tokens_used = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class Citation(models.Model):
    """Model for citations linking messages to document chunks"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='citations')
    chunk = models.ForeignKey(DocumentChunk, on_delete=models.CASCADE, related_name='citations')
    relevance_score = models.FloatField(null=True, blank=True)  # Similarity score
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'citations'
        unique_together = ['message', 'chunk']

    def __str__(self):
        return f"Citation: {self.chunk.document.name} (p.{self.chunk.page_start}-{self.chunk.page_end})"


class ProcessingLog(models.Model):
    """Model for tracking processing operations"""
    LOG_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(PDFDocument, on_delete=models.CASCADE, related_name='logs', null=True, blank=True)
    operation = models.CharField(max_length=50)  # e.g., 'pdf_processing', 'embedding_creation'
    level = models.CharField(max_length=10, choices=LOG_LEVELS, default='info')
    message = models.TextField()
    details = models.JSONField(null=True, blank=True)  # Additional structured data
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'processing_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.operation} - {self.level}: {self.message[:50]}..."