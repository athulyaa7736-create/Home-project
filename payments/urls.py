from django.urls import path
from . import views
# from .admin import payment_dashboard,process_payment_view
from django.contrib.admin.views.decorators import staff_member_required

urlpatterns = [
    # Payment URLs
    path('pay/<int:booking_id>/', views.payment_page, name='payment_page'),
    # path('process/', views.process_payment, name='process_payment'),
    path('history/', views.payment_history, name='payment_history'),
    path('payment/<int:booking_id>/', views.payment_page, name='payment_page'),
     # path('test/', views.test_payment, name='test_payment'),
    path('api/payment/<int:booking_id>/', views.process_payment_api, name='process_payment_api'),
    path('process/<int:booking_id>/', views.process_payment, name='process_payment'),
    path('history/', views.payment_history, name='payment_history'),
    path('receipt/<int:payment_id>/', views.payment_receipt, name='payment_receipt'),
    path('process-plan/<int:plan_id>/', views.process_plan_payment, name='process_plan_payment'),
    
    # Subscription URLs
    path('subscriptions/', views.my_subscriptions, name='my_subscriptions'),
    path('subscription/<int:sub_id>/', views.subscription_detail, name='subscription_detail'),
    path('subscription/<int:sub_id>/cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('subscription/<int:sub_id>/renew/', views.renew_subscription, name='renew_subscription'),

    path('refund/<int:payment_id>/', views.request_refund, name='request_refund'),
    path('process-cash/', views.process_cash_payment, name='process_cash_payment'),
    path('worker/confirm-cash/<int:job_id>/', views.worker_confirm_cash, name='worker_confirm_cash'),
    path('confirm-cash/<int:job_id>/', views.confirm_cash_received, name='confirm_cash_received'),
    path('reject-cash/<int:payment_id>/', views.reject_cash_payment, name='reject_cash_payment'),
    path('admin/partial-refund/<int:payment_id>/', views.admin_partial_refund, name='admin_partial_refund'),
   
   path('admin/payments/dashboard/', 
         staff_member_required(views.payment_dashboard), 
         name='payment_dashboard'),
    
    # Process payment URL - this matches the one used in admin
    path('admin/payments/workerpayment/<int:payment_id>/process/', 
         staff_member_required(views.process_payment_view), 
         name='payments_workerpayment_process'),

    # API endpoint for worker payment details
    path('admin/payments/api/worker/<int:worker_id>/', 
         staff_member_required(views.get_worker_payment_details), 
         name='api_worker_payment_details'),

     path('process-payment/', views.process_payment_page, name='process_payment_page'), 
     path('complete-payment/', views.complete_payment, name='complete_payment'),
    
]