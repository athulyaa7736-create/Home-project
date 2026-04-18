from django.urls import path
from . import views

urlpatterns = [
    path('plans/', views.plan_list, name='plan_list'),
    path('plan/<int:plan_id>/', views.select_plan, name='select_plan'),
    path('plan/<int:plan_id>/pay/', views.plan_payment_page, name='plan_payment_page'),
    path('process-plan-payment/', views.process_plan_payment, name='process_plan_payment'),
    path('subscription-history/', views.subscription_history, name='subscription_history'),
]