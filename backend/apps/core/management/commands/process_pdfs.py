from django.core.management.base import BaseCommand
from apps.pdf_processor.tasks import process_pdf_document
from apps.core.models import PDFDocument

class Command(BaseCommand):
    help = 'Process uploaded PDF documents'

    def handle(self, *args, **options):
        pending_docs = PDFDocument.objects.filter(processing_status='pending')
        self.stdout.write(f'Processing {pending_docs.count()} documents...')
        
        for doc in pending_docs:
            success = process_pdf_document(str(doc.id))
            if success:
                self.stdout.write(f'✅ Processed: {doc.name}')
            else:
                self.stdout.write(f'❌ Failed: {doc.name}')