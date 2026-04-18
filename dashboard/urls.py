from django.urls import path
from . import views

urlpatterns = [
    path('user/', views.user_dashboard, name='user_dashboard'),
    path('worker/', views.worker_dashboard, name='worker_dashboard'),
]

