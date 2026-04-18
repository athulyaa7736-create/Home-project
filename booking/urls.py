from django.urls import path
from . import views

urlpatterns = [
    # User URLs
    path('request/', views.request_service, name='request_service'),
    path('my-requests/', views.my_requests, name='my_requests'),
    path('request/<int:request_id>/', views.request_detail, name='request_detail'),
    path('request/<int:request_id>/cancel/', views.cancel_request, name='cancel_request'),
    path('<int:request_id>/complete/', views.complete_service, name='complete_service'),
    path('booking/rate/<int:job_id>/', views.rate_job, name='rate_job'),
    # path('rate/<int:job_id>/', views.rate_job, name='rate_job'),

    # Admin URLs
    path('assign-worker/<int:request_id>/', views.assign_worker, name='assign_worker'),
    
    path('assign-worker-ajax/<int:request_id>/', views.ajax_assign_worker, name='ajax_assign_worker'),
    # Worker URLs
    path('update-status/<int:job_id>/', views.update_job_status, name='update_job_status'),
    path('reject-job/', views.reject_job, name='reject_job'),
     
    # Worker location endpoint
    path('worker-location/<int:job_id>/', 
     views.get_worker_location, name='get_worker_location'),  
]