from django.urls import path
from .views import request_service

urlpatterns = [
    path("request-service/", request_service, name="request_service"),
]
