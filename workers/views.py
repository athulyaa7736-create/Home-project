from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from booking.models import ServiceRequest
from .models import WorkerProfile, WorkerNotification
from payments.models import WorkerPayment
from .forms import WorkerProfileForm
import json
from django.db.models import Sum
from django.utils import timezone

@login_required
def edit_worker_profile(request):
    """Allow workers to edit their profile"""
    if request.user.role != 'worker':
        messages.error(request, "Access denied. Workers only.")
        return redirect('login')
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        profile = None
    
    if request.method == 'POST':
        if profile:
            form = WorkerProfileForm(request.POST, request.FILES, instance=profile)
        else:
            form = WorkerProfileForm(request.POST, request.FILES)
        
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()

            phone = request.POST.get('phone_number', '').strip()
            if phone:
                request.user.phone = phone
                request.user.save(update_fields=['phone'])
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('worker_dashboard')
        else:
            # Print errors to console for debugging
            print("Form errors:", form.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        if profile:
            form = WorkerProfileForm(instance=profile)
        else:
            form = WorkerProfileForm()
    
    return render(request, 'workers/edit_profile.html', {'form': form, 'profile': profile})

@login_required
def toggle_availability(request):
    """Worker can toggle their availability"""
    if request.user.role != 'worker':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        try:
            profile = WorkerProfile.objects.get(user=request.user)
            profile.available = not profile.available
            profile.save()
            return JsonResponse({
                'success': True,
                'available': profile.available,
                'message': f"You are now {'available' if profile.available else 'unavailable'}"
            })
        except WorkerProfile.DoesNotExist:
            return JsonResponse({'error': 'Profile not found'}, status=404)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def update_worker_status(request):
    """Worker can update their status"""
    if request.user.role != 'worker':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_status = data.get('status')
            
            if new_status in ['available', 'busy', 'on_leave', 'vacation']:
                profile = WorkerProfile.objects.get(user=request.user)
                profile.availability_status = new_status
                profile.save()
                return JsonResponse({
                    'success': True,
                    'status': new_status,
                    'message': f"Status updated to {new_status}"
                })
            else:
                return JsonResponse({'error': 'Invalid status'}, status=400)
                
        except WorkerProfile.DoesNotExist:
            return JsonResponse({'error': 'Profile not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def update_bank_details(request):
    """Worker updates their bank details for payment"""
    if request.user.role != 'worker':
        messages.error(request, "Access denied.")
        return redirect('login')
    
    try:
        profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        profile = None
    
    if request.method == 'POST':
        if not profile:
            messages.error(request, "Worker profile not found.")
            return redirect('worker_dashboard')
        
        # Update bank details
        profile.account_holder_name = request.POST.get('account_holder_name')
        profile.bank_name = request.POST.get('bank_name')
        profile.account_number = request.POST.get('account_number')
        profile.ifsc_code = request.POST.get('ifsc_code')
        profile.upi_id = request.POST.get('upi_id')
        profile.payment_method = request.POST.get('payment_method')
        profile.save()
        
        messages.success(request, "Bank details updated successfully!")
        return redirect('worker_dashboard')
    
    return redirect('worker_dashboard')

@login_required
def worker_dashboard(request):
    if request.user.role != "worker":
        return redirect("login")
    
    # Get worker's assigned jobs
    # jobs = ServiceRequest.objects.filter(assigned_worker=request.user).order_by('-created_at')
    
    # Get worker profile
    try:
        profile = WorkerProfile.objects.get(user=request.user)
    except WorkerProfile.DoesNotExist:
        profile = None
    
    # Get all jobs assigned to this worker
    all_jobs = ServiceRequest.objects.filter(assigned_worker=request.user).order_by('-created_at')
    
    # Get unread payment notifications
    payments_notifications = WorkerPayment.objects.filter(
        worker=profile, 
        status='completed',
        seen_by_worker=False
    ).order_by('-payment_date')
    
    # Calculate stats
    total_jobs = all_jobs.count()
    pending_jobs = all_jobs.filter(status='assigned').count()
    in_progress_jobs = all_jobs.filter(status='in_progress').count()
    completed_jobs = all_jobs.filter(status='completed').count()
    
    # Calculate earnings
    job_rate = profile.job_rate if profile else 0
    total_earnings = completed_jobs * job_rate
    pending_earnings = (pending_jobs + in_progress_jobs) * job_rate
    
    # Get recent jobs
    recent_jobs = all_jobs[:5]

    context = {
        'all_jobs': all_jobs,
        'profile': profile,
        'payments_notifications': payments_notifications,
        'total_jobs': total_jobs,
        'pending_jobs': pending_jobs,
        'in_progress_jobs': in_progress_jobs,
        'completed_jobs': completed_jobs,
        'total_earnings': total_earnings,
        'pending_earnings': pending_earnings,
        'recent_jobs': recent_jobs,
    }
    
    return render(request, "dashboard/worker_dashboard.html", context)

@login_required
def worker_my_jobs(request):
    """Show all assigned jobs for worker"""
    if request.user.role != "worker":
        return redirect("login")
    
    # Get all jobs for this worker
    jobs = ServiceRequest.objects.filter(
        assigned_worker=request.user
    ).select_related('service', 'user').order_by('-created_at')
    
    # Separate by status
    active_jobs = jobs.filter(status__in=['assigned', 'in_progress'])
    completed_jobs = jobs.filter(status='completed')
    
    context = {
        'active_jobs': active_jobs,
        'completed_jobs': completed_jobs,
        'all_jobs': jobs,
        'active_count': active_jobs.count(),
        'completed_count': completed_jobs.count(),
    }
    
    return render(request, "workers/worker_my_jobs.html", context)

@login_required
def worker_job_history(request):
    """Show job history for worker"""
    if request.user.role != "worker":
        return redirect("login")
    
    # Get completed jobs
    completed_jobs = ServiceRequest.objects.filter(
        assigned_worker=request.user,
        status='completed'
    ).select_related('service', 'user').order_by('-created_at')
    
    # Calculate total earnings
    total_earnings = 0
    for job in completed_jobs:
        if job.service and job.service.price:
            total_earnings += job.service.price
    
    context = {
        'completed_jobs': completed_jobs,
        'total_jobs': completed_jobs.count(),
        'total_earnings': total_earnings,
    }
    
    return render(request, "workers/worker_job_history.html", context)


@login_required
def job_details(request, job_id):
    """View detailed job information"""
    if request.user.role != 'worker':
        return redirect('login')
    
    job = get_object_or_404(ServiceRequest, id=job_id, assigned_worker=request.user)
    
    context = {
        'job': job,
    }
    
    return render(request, 'workers/job_details.html', context)

@login_required
def update_job_status(request, job_id):
    if request.method == 'POST':
        from users.models import UserSubscription
        from workers.models import WorkerProfile

        job = get_object_or_404(ServiceRequest, id=job_id)
        old_status = job.status
        new_status = request.POST.get('status')

        job.status = new_status
        job.save()

        # ✅ When job starts — increment daily counter
        if new_status == 'in_progress' and old_status != 'in_progress':
            try:
                profile = WorkerProfile.objects.get(user=request.user)
                profile.reset_daily_jobs_if_needed()
                profile.jobs_today += 1
                profile.current_jobs_count += 1
                profile.save(update_fields=['jobs_today', 'current_jobs_count'])
            except Exception as e:
                print('Counter error:', e)

        # ✅ When job completes — decrement current, increment completed
        if new_status == 'completed' and old_status != 'completed':
            try:
                profile = WorkerProfile.objects.get(user=request.user)
                profile.current_jobs_count  = max(0, profile.current_jobs_count - 1)
                profile.completed_jobs_count += 1
                profile.save(update_fields=['current_jobs_count', 'completed_jobs_count'])
            except Exception as e:
                print('Counter error:', e)

            # Subscription visit decrement
            active_sub = UserSubscription.objects.filter(
                user=job.user, status='active'
            ).first()
            if active_sub and active_sub.visits_used < active_sub.total_visits_allowed:
                active_sub.visits_used += 1
                if active_sub.visits_used >= active_sub.total_visits_allowed:
                    active_sub.status = 'expired'
                active_sub.save()

        messages.success(request, 'Job status updated to {}'.format(new_status))
        return redirect('worker_dashboard')



@login_required
def mark_notifications_read(request):
    if request.method == 'POST':
        from workers.models import WorkerProfile, WorkerNotification
        try:
            profile = WorkerProfile.objects.get(user=request.user)
            
            try:
                data    = json.loads(request.body)
                notif_id = data.get('notif_id')
            except Exception:
                notif_id = None

            if notif_id:
                # ✅ Mark single notification as read
                WorkerNotification.objects.filter(
                    id=notif_id, worker=profile
                ).update(is_read=True)
            else:
                # ✅ Mark ALL as read
                WorkerNotification.objects.filter(
                    worker=profile, is_read=False
                ).update(is_read=True)

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False})

# In workers/views.py
from django.http import JsonResponse
from django.utils import timezone
import json

@login_required
def update_worker_location(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lat  = data.get('latitude')
            lng  = data.get('longitude')

            from workers.models import WorkerProfile
            profile = WorkerProfile.objects.get(user=request.user)
            profile.latitude         = lat
            profile.longitude        = lng
            profile.location_updated_at = timezone.now()
            profile.location_sharing = True
            profile.save(update_fields=[
                'latitude', 'longitude',
                'location_updated_at', 'location_sharing'
            ])
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False})


@login_required
def stop_location_sharing(request):
    if request.method == 'POST':
        try:
            from workers.models import WorkerProfile
            profile = WorkerProfile.objects.get(user=request.user)
            profile.location_sharing = False
            profile.save(update_fields=['location_sharing'])
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False})


@login_required
def get_worker_location(request, job_id):
    """User calls this to get worker's current location"""
    from booking.models import ServiceRequest
    from workers.models import WorkerProfile

    try:
        job = ServiceRequest.objects.get(
            id=job_id,
            user=request.user,  # security — only the job owner
            status__in=['assigned', 'in_progress']
        )
        if not job.assigned_worker:
            return JsonResponse({'success': False, 'message': 'No worker assigned'})

        profile = WorkerProfile.objects.get(user=job.assigned_worker)

        if not profile.location_sharing or not profile.latitude:
            return JsonResponse({'success': False, 'message': 'Worker not sharing location'})

        # Check if location is fresh (within 5 minutes)
        from datetime import timedelta
        if profile.location_updated_at:
            age = timezone.now() - profile.location_updated_at
            if age > timedelta(minutes=5):
                return JsonResponse({'success': False, 'message': 'Location data is stale'})

        return JsonResponse({
            'success':    True,
            'latitude':   float(profile.latitude),
            'longitude':  float(profile.longitude),
            'updated_at': profile.location_updated_at.strftime('%H:%M:%S'),
            'worker':     job.assigned_worker.username,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})