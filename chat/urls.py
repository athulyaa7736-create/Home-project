from django.urls import path
from . import views

urlpatterns = [
    path('', views.ai_chat, name='ai_chat'),
    path('escalate/', views.escalate_to_admin, name='escalate_issue'),
    path('mark-resolved-seen/', views.mark_resolved_seen, name='mark_resolved_seen'),
]


