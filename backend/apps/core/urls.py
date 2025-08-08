from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# ViewSet'ler için router oluştur
router = DefaultRouter()
router.register(r'documents', views.PDFDocumentViewSet, basename='pdfdocument')
router.register(r'chat-sessions', views.ChatSessionViewSet, basename='chatsession')
router.register(r'chat-messages', views.ChatMessageViewSet, basename='chatmessage')

app_name = 'core'

urlpatterns = [
    # Router URL'lerini dahil et
    path('api/', include(router.urls)),
    
    # PDF yükleme uç noktaları
    path('api/upload/', views.MultiPDFUploadView.as_view(), name='multi-pdf-upload'),
    path('api/upload/progress/<uuid:document_id>/', views.PDFUploadProgressView.as_view(), name='upload-progress'),
    
    # Belge yönetimi
    path('api/documents/<uuid:document_id>/delete/', views.delete_document, name='delete-document'),
    path('api/documents/stats/', views.DocumentStatsView.as_view(), name='document-stats'),
    
    # Sağlık kontrolü
    path('api/health/', views.health_check, name='health-check'),
]

"""
API Uç Nokta Özeti:

Belgeler:
- GET /api/documents/ - Tüm PDF belgelerini listele
- POST /api/documents/ - Tek PDF belgesi yükle
- GET /api/documents/{id}/ - Belge detaylarını getir
- PUT /api/documents/{id}/ - Belge meta verilerini güncelle
- DELETE /api/documents/{id}/ - Belgeyi sil
- GET /api/documents/{id}/chunks/ - Belge parçalarını getir
- POST /api/documents/{id}/reprocess/ - Belgeyi yeniden işle

Çoklu yükleme:
- POST /api/upload/ - Birden fazla PDF dosyası yükle

İlerleme takibi:
- GET /api/upload/progress/{document_id}/ - İşleme ilerlemesini kontrol et

İstatistikler:
- GET /api/documents/stats/ - Belge istatistiklerini getir

Sohbet Oturumları:
- GET /api/chat-sessions/ - Sohbet oturumlarını listele
- POST /api/chat-sessions/ - Yeni sohbet oturumu oluştur
- GET /api/chat-sessions/{id}/ - Oturum detaylarını getir
- PUT /api/chat-sessions/{id}/ - Oturumu güncelle
- DELETE /api/chat-sessions/{id}/ - Oturumu sil
- GET /api/chat-sessions/{id}/messages/ - Oturum mesajlarını getir

Sohbet Mesajları:
- GET /api/chat-messages/ - Mesajları listele (oturum filtresi ile)
- POST /api/chat-messages/ - Yeni mesaj oluştur
- GET /api/chat-messages/{id}/ - Mesaj detaylarını getir
- PUT /api/chat-messages/{id}/ - Mesajı güncelle
- DELETE /api/chat-messages/{id}/ - Mesajı sil

Sağlık:
- GET /api/health/ - Servis sağlık kontrolü
"""