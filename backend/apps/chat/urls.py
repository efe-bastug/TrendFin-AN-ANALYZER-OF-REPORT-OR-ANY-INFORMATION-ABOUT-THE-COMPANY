from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Sohbet oturumları
    path('api/chat/sessions/', views.ChatSessionListCreateView.as_view(), name='chat-sessions'),
    path('api/chat/sessions/<uuid:pk>/', views.ChatSessionDetailView.as_view(), name='chat-session-detail'),
    path('api/chat/sessions/<uuid:session_id>/messages/', views.ChatSessionMessagesView.as_view(), name='session-messages'),
    
    # Soru-cevap
    path('api/chat/ask/', views.AskQuestionView.as_view(), name='ask-question'),
    path('api/chat/quick-answer/', views.QuickAnswerView.as_view(), name='quick-answer'),
    
    # Sohbet istatistikleri ve yönetimi
    path('api/chat/stats/', views.chat_stats, name='chat-stats'),
    path('api/chat/clear-history/', views.clear_chat_history, name='clear-history'),
]

"""
Sohbet API Uç Nokta Özeti:

Sohbet Oturumları:
- GET /api/chat/sessions/ - Sohbet oturumlarını listele
- POST /api/chat/sessions/ - Yeni sohbet oturumu oluştur
- GET /api/chat/sessions/{id}/ - Oturum detaylarını getir
- PUT /api/chat/sessions/{id}/ - Oturumu güncelle
- DELETE /api/chat/sessions/{id}/ - Oturumu sil
- GET /api/chat/sessions/{id}/messages/ - Oturum mesajlarını getir

Soru & Cevap:
- POST /api/chat/ask/ - Soru sor (oturum yönetimi ve akış desteğiyle)
  Gövde: {
    "question": "Bu belge ne hakkında?",
    "session_id": "uuid" (opsiyonel),
    "document_ids": ["uuid1", "uuid2"] (opsiyonel),
    "stream": true/false (opsiyonel, varsayılan: false)
  }

- POST /api/chat/quick-answer/ - Oturum olmadan hızlı yanıt
  Gövde: {
    "question": "Bu belge ne hakkında?",
    "document_ids": ["uuid1", "uuid2"] (opsiyonel)
  }

İstatistik & Yönetim:
- GET /api/chat/stats/ - Sohbet istatistiklerini getir
- DELETE /api/chat/clear-history/ - Tüm sohbet geçmişini temizle
"""