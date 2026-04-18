from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('register/worker/', views.worker_register_view, name='worker_register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),  

    path('subscription/plans/', views.subscription_plans, name='subscription_plans'),
    path('subscription/subscribe/<int:plan_id>/', views.subscribe_plan, name='subscribe_plan'),
    path('subscription/history/', views.subscription_history, name='subscription_history'),
    path('subscription/cancel/<int:sub_id>/', views.cancel_subscription, name='cancel_subscription'),
    path('subscription/renew/<int:sub_id>/', views.renew_subscription, name='renew_subscription'),
]
   

