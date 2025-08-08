from django.contrib import admin
from .models import PDFDocument, DocumentChunk, ChatSession, ChatMessage, Citation

@admin.register(PDFDocument)
class PDFDocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'size', 'uploaded_at', 'processed', 'processing_status']
    list_filter = ['processed', 'processing_status', 'uploaded_at']
    search_fields = ['name', 'original_filename']

admin.site.register(DocumentChunk)
admin.site.register(ChatSession)  
admin.site.register(ChatMessage)
admin.site.register(Citation)