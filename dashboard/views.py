from urllib import request
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from booking.models import ServiceRequest
from services.models import Service
from users.models import CustomUser
from workers.models import WorkerProfile
from payments.models import Payment
from django.db.models import Count, Prefetch, Sum, Avg, Q
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Prefetch
from payments.models import WorkerPayment, Payment
from users.models import UserSubscription,SubscriptionPlan 
from payments.models import Payment
from workers.models import WorkerNotification
from users.models import UserSubscription
from payments.models import Payment
from django.db.models import Sum, Q
from datetime import date
from chat.models import EscalatedIssue

@login_required
def user_dashboard(request):
    if request.user.role != "user":
        return redirect("login")


    # Service requests
    service_requests = ServiceRequest.objects.filter(
        user=request.user
    ).select_related(
        'service', 'assigned_worker', 'subscription', 'subscription__plan'
    ).order_by('-created_at')

    # Attach payment safely
    for booking in service_requests:
        try:
            booking.safe_payment = booking.payment
        except Exception:
            booking.safe_payment = None
        # ✅ Attach rating
        try:
            booking.rating = booking.rating  # uses related_name
        except Exception:
            booking.rating = None

    # Active subscription
    active_subscription = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        end_date__gte=date.today()
    ).select_related('plan').first()

    # Stats
    total_requests   = service_requests.count()
    pending_requests = service_requests.filter(status='pending').count()
    in_progress      = service_requests.filter(status='in_progress').count()
    completed        = service_requests.filter(status='completed').count()

    # Total spent
    total_spent = Payment.objects.filter(
        user=request.user,
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0

    # ✅ Refund payments — simple direct filter
    refund_payments = Payment.objects.filter(
        user=request.user,
        refund_requested=True
    ).order_by('-refund_request_date', '-created_at')

    # ✅ Unseen resolved chat issues for notification badge
    unseen_chat_notifications = EscalatedIssue.objects.filter(
        user=request.user,
        status='resolved',
        seen_by_user=False
    ).count()

    context = {
        'service_requests':  service_requests,
        'active_subscription': active_subscription,
        'remaining_visits':  active_subscription.visits_remaining if active_subscription else 0,
        'total_requests':    total_requests,
        'pending_requests':  pending_requests,
        'in_progress':       in_progress,
        'completed':         completed,
        'total_spent':       total_spent,
        'refund_payments':   refund_payments,  # ✅ correct
        'unseen_chat_notifications': unseen_chat_notifications,
    }

    return render(request, 'dashboard/user_dashboard.html', context)



@login_required
def worker_dashboard(request):
    if request.user.role != "worker":
        return redirect("login")

    # Get worker profile
    try:
        profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        profile = None

    # ✅ Define all_jobs first
    all_jobs = ServiceRequest.objects.filter(
        assigned_worker=request.user
    ).order_by('-created_at')

    # Jobs for dashboard
    jobs = all_jobs.filter(
        status__in=['pending', 'assigned', 'in_progress', 'completed']
    ).order_by('-created_at')

    # ✅ Attach safe_payment to each job
    for job in jobs:
        try:
            job.safe_payment = job.payment
        except Exception:
            job.safe_payment = None

    # Stats
    total_jobs       = all_jobs.count()
    pending_jobs     = all_jobs.filter(status__in=['pending', 'assigned']).count()
    in_progress_jobs = all_jobs.filter(status='in_progress').count()
    completed_jobs   = all_jobs.filter(status='completed').count()

    # Earnings
    job_rate       = profile.job_rate if profile else 0
    total_earnings = completed_jobs * job_rate

    
    # Get unread notifications
    notifications = WorkerNotification.objects.filter(
        worker=profile,
        is_read=False
    ) if profile else WorkerNotification.objects.none()
    

    # Payment notifications
    try:
        from payments.models import WorkerPayment
        payments_notifications = WorkerPayment.objects.filter(
            worker=profile,
            status='completed',
            seen_by_worker=False
        ).order_by('-payment_date')
    except Exception:
        payments_notifications = []

    context = {
        'profile':                profile,
        'jobs':                   jobs,
        'total_jobs':             total_jobs,
        'pending_jobs':           pending_jobs,
        'in_progress_jobs':       in_progress_jobs,
        'completed_jobs':         completed_jobs,
        'total_earnings':         total_earnings,
        'payments_notifications': payments_notifications,
        'notifications': notifications,
        'notif_count':   notifications.count(),
    }

    return render(request, 'dashboard/worker_dashboard.html', context)