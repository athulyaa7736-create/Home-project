from django.urls import path
from . import views

urlpatterns = [
    path('edit-profile/', views.edit_worker_profile, name='edit_worker_profile'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('my-jobs/', views.worker_my_jobs, name='worker_my_jobs'),
    path('job-history/', views.worker_job_history, name='worker_job_history'),
    # path('status/', views.worker_status_dashboard, name='worker_status'),
    path('toggle-availability/', views.toggle_availability, name='toggle_availability'),
    path('update-bank-details/', views.update_bank_details, name='update_bank_details'),
    path('update-status/', views.update_worker_status, name='update_worker_status'),
    # path('profile/<int:worker_id>/', views.worker_profile_detail, name='worker_profile'),
    path('job/<int:job_id>/', views.job_details, name='job_details'),
    path('job/<int:job_id>/update-status/', views.update_job_status, name='update_job_status'),
    # In workers/urls.py
    path('update-location/',   views.update_worker_location, name='update_worker_location'),
    path('stop-location/',     views.stop_location_sharing,  name='stop_location_sharing'),
]