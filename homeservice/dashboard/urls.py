from django.urls import path
from .views import *

urlpatterns = [
    path('', home, name='home'),
    path("user/", user_dashboard, name="user_dashboard"),
    path("worker/", worker_dashboard, name="worker_dashboard"),
    path("admin-dashboard/", admin_dashboard, name="admin_dashboard"),
]
