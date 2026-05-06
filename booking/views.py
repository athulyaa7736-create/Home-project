from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import ServiceRequest
from .forms import ServiceRequestForm
from services.models import Service
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
import json
from django.db import models 
from users.models import UserSubscription, CustomUser
from workers.models import WorkerProfile
from datetime import date

@login_required
def request_service(request):
    """Create a new service request"""
    if request.user.role != "user":
        return redirect("login")
    
    # Check user's active subscription
    active_sub = UserSubscription.objects.filter(
        user=request.user,
        status='active',
        end_date__gte=date.today()
    ).first()
    
    if request.method == 'POST':
        form = ServiceRequestForm(request.POST, request.FILES)
        if form.is_valid():
            service_request = form.save(commit=False)
            service_request.user = request.user
            
            # If user has active subscription with remaining visits
            if active_sub and active_sub.visits_remaining > 0:
                service_request.subscription = active_sub
                messages.success(request, f'Service booked using subscription! ({active_sub.visits_remaining} visits left)')
            else:
                messages.success(request, 'Service request submitted successfully!')
            
            try:
                service_request.save()
                print(f"ServiceRequest saved with ID: {service_request.id}, issue_image: {service_request.issue_image}")
                return redirect('user_dashboard')
            except Exception as e:
                messages.error(request, 'Error saving service request.')
                print("Error saving service request:", e)
        else:
            messages.error(request, 'Form is invalid. Please check your input.')
            print("Form errors:", form.errors)
            print("Non-field errors:", form.non_field_errors())
    else:
        form = ServiceRequestForm()
    
    # Get available services
    services = Service.objects.filter(is_active=True).values('id', 'name', 'price', 'category')
    services_json = json.dumps([
    {
        'id':    s['id'],
        'name':  s['name'],
        'price': float(s['price']),  # ✅ convert Decimal to float
    }
    for s in services
])
    
    context = {
        'form': form,
        'services': services,
        'services_json': services_json,
        'active_subscription': active_sub,
        'remaining_visits': active_sub.visits_remaining if active_sub else 0,
    }
    return render(request, 'booking/request_service.html', context)

@login_required
def complete_service(request, request_id):
    """Mark a service as completed (for workers/admin)"""
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    
    # Check permission (worker assigned or admin)
    if request.user.role == 'worker' and service_request.assigned_worker != request.user:
        messages.error(request, "You are not assigned to this service")
        return redirect('worker_dashboard')
    
    if request.method == 'POST':
        # Mark service as completed
        service_request.status = 'completed'
        service_request.save()
        
        # If this service used a subscription, update the subscription
        if service_request.subscription:
            subscription = service_request.subscription
            if subscription.visits_used < subscription.total_visits_allowed:
                subscription.visits_used += 1
                subscription.save()
                
                # Check if subscription should expire
                if subscription.visits_used >= subscription.total_visits_allowed:
                    subscription.status = 'expired'
                    subscription.save()
                    messages.success(request, f"Service completed! Subscription expired - all visits used.")
                else:
                    remaining = subscription.total_visits_allowed - subscription.visits_used
                    messages.success(request, f"Service completed! {remaining} visits remaining in subscription.")
            else:
                messages.warning(request, "Service completed but subscription has no visits left.")
        else:
            messages.success(request, "Service completed successfully!")
        
        if request.user.role == 'worker':
            return redirect('worker_dashboard')
        return redirect('admin:booking_servicerequest_changelist')
    
    context = {
        'request': service_request,
    }
    return render(request, 'booking/confirm_complete.html', context)

def my_requests(request):
    """View for users to see their service requests"""
    if request.user.role != "user":
        return redirect("login")
    
    service_requests = ServiceRequest.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "booking/my_requests.html", {"service_requests": service_requests})

@login_required
def request_detail(request, request_id):
    """View for users to see details of a specific request"""
    service_request = get_object_or_404(ServiceRequest, id=request_id, user=request.user)
    return render(request, "booking/request_detail.html", {"service_request": service_request})

@login_required
def cancel_request(request, request_id):
    """View for users to cancel a pending request"""
    service_request = get_object_or_404(ServiceRequest, id=request_id, user=request.user)
    
    if service_request.status == 'pending':
        service_request.status = 'cancelled'
        service_request.save()
        messages.success(request, "Your service request has been cancelled.")
    else:
        messages.error(request, "Only pending requests can be cancelled.")
    
    return redirect('my_requests')

# Admin/Worker views
@login_required
def assign_worker(request, request_id):
    """Admin view to assign worker to a request"""
    if request.user.role != 'admin':
        messages.error(request, "Access denied. Admins only.")
        return redirect('login')
    
    service_request = get_object_or_404(ServiceRequest, id=request_id)
    
    if request.method == 'POST':
        worker_id = request.POST.get('worker_id')
        if worker_id:
            from users.models import CustomUser
            from workers.models import WorkerProfile
            
            try:
                worker = CustomUser.objects.get(id=worker_id, role='worker')
                worker_profile = WorkerProfile.objects.get(user=worker)
                
                # VALIDATE: Check if worker type matches service category
                if worker_profile.service_type != service_request.service.category:
                    messages.error(
                        request, 
                        f"Cannot assign {worker_profile.get_service_type_display()} "
                        f"to {service_request.service.category} service. "
                        f"Please select a {service_request.service.category} worker."
                    )
                    return redirect('admin_dashboard')
                
                # Check if worker is available
                if not worker_profile.can_accept_job():
                    messages.error(
                        request, 
                        f"Worker {worker.username} is not available or has reached maximum jobs."
                    )
                    return redirect('admin_dashboard')
                
                # Assign the worker
                service_request.assigned_worker = worker
                service_request.status = 'assigned'
                service_request.save()
                
                # Update worker's job count
                worker_profile.assign_job()
                
                messages.success(
                    request, 
                    f"✅ {worker_profile.get_service_type_display()} {worker.username} "
                    f"assigned successfully!"
                )
                
            except CustomUser.DoesNotExist:
                messages.error(request, 'Worker not found.')
            except WorkerProfile.DoesNotExist:
                messages.error(request, 'Worker profile not found.')
        else:
            messages.error(request, 'Please select a worker.')
    
    return redirect('admin_dashboard')


@login_required
def update_job_status(request, job_id):
    """Worker updates job status (accept/start/complete)"""
    if request.user.role != 'worker':
        messages.error(request, "Access denied. Workers only.")
        return redirect('login')
    
    service_request = get_object_or_404(ServiceRequest, id=job_id, assigned_worker=request.user)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        if new_status == 'in_progress':
            service_request.status = 'in_progress'
            
            # Mark worker as busy
            worker_profile = request.user.worker_profile
            worker_profile.available = False
            worker_profile.availability_status = 'busy'
            worker_profile.current_jobs_count += 1
            worker_profile.save()
            
            messages.success(request, "Job accepted! You are now working on this job.")
            
        elif new_status == 'completed':
            service_request.status = 'completed'
            
            # 🔴 FIXED: Check for subscription and update visits
            try:
                # Check if user has active subscription
                subscription = UserSubscription.objects.filter(
                    user=service_request.user,
                    status='active',
                    end_date__gte=timezone.now().date()
                ).first()
                
                if subscription:
                    print(f"Found subscription for user {service_request.user.username}")  # Debug
                    print(f"Current visits used: {subscription.visits_used}")
                    
                    # Check if they have visits left
                    if subscription.visits_used < subscription.total_visits_allowed:
                        # Increment visit count
                        subscription.visits_used += 1
                        subscription.save()
                        
                        # Link this service to the subscription
                        service_request.subscription = subscription
                        service_request.save()
                        
                        print(f"New visits used: {subscription.visits_used}")  # Debug
                        
                        messages.success(
                            request, 
                            f"Job completed! Used 1 visit from {subscription.plan.name}. "
                            f"{subscription.visits_remaining()} visits remaining."
                        )
                    else:
                        messages.warning(
                            request, 
                            "Job completed but you've used all your subscription visits. Payment may be required."
                        )
                else:
                    print(f"No active subscription found for user {service_request.user.username}")  # Debug
                    messages.info(request, "Job completed. No active subscription found.")
                    
            except Exception as e:
                print(f"Error updating subscription: {e}")
                messages.info(request, "Job completed.")
            
            # Mark worker as available again
            worker_profile = request.user.worker_profile
            worker_profile.available = True
            worker_profile.availability_status = 'available'
            worker_profile.current_jobs_count = max(0, worker_profile.current_jobs_count - 1)
            worker_profile.completed_jobs_count += 1
            worker_profile.save()
            
        else:
            messages.error(request, 'Invalid status.')
            return redirect('worker_dashboard')
        
        service_request.save()
    
    return redirect('worker_dashboard')

@login_required
def worker_dashboard(request):
    if request.user.role != "worker":
        return redirect("login")
    
    # Get worker's assigned jobs
    jobs = ServiceRequest.objects.filter(assigned_worker=request.user).order_by('-created_at')
    
    # Get worker profile
    try:
        profile = WorkerProfile.objects.get(user=request.user)
        # Debug print
        print(f"====== WORKER DASHBOARD ======")
        print(f"Worker: {request.user.username}")
        print(f"Completed jobs from DB: {profile.completed_jobs_count}")
        print(f"Current jobs: {profile.current_jobs_count}")
        print(f"=============================")
    except WorkerProfile.DoesNotExist:
        profile = None
    

@staff_member_required
@csrf_exempt
def ajax_assign_worker(request, request_id):
    """AJAX view to assign worker to request"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            worker_id = data.get('worker_id')
            
            service_request = ServiceRequest.objects.get(id=request_id)
            worker = CustomUser.objects.get(id=worker_id, role='worker')
            worker_profile = WorkerProfile.objects.get(user=worker)
            
            # Check if worker type matches service category
            if worker_profile.service_type != service_request.service.category:
                return JsonResponse({
                    'success': False, 
                    'message': f'Cannot assign {worker_profile.get_service_type_display()} to {service_request.service.category} service.'
                })
            
            # Assign worker and update status
            service_request.assigned_worker = worker
            service_request.status = 'assigned'
            service_request.save()
            
            # Update worker's job count if available
            if hasattr(worker_profile, 'current_jobs_count'):
                worker_profile.current_jobs_count += 1
                worker_profile.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Worker {worker.username} assigned successfully'
            })
            
        except ServiceRequest.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Request not found'})
        except CustomUser.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Worker not found'})
        except WorkerProfile.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Worker profile not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def reject_job(request):
    if request.method == 'POST':
        from booking.models import ServiceRequest
        from workers.models import WorkerProfile, WorkerNotification
        
        job_id = request.POST.get('job_id')
        reason = request.POST.get('reason', 'other')
        comments = request.POST.get('comments', '')
        
        job = get_object_or_404(ServiceRequest, id=job_id)
        
        # ✅ Mark job as cancelled when worker rejects
        job.status = 'cancelled'
        job.assigned_worker = None  # ✅ unassign worker so admin can reassign
        job.save()
        
        # Save rejection record
        from booking.models import JobRejection
        JobRejection.objects.create(
            job      = job,
            worker   = request.user,
            reason   = reason,
            comments = comments
        )

        # ✅ Notify admin via LogEntry
        try:
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            LogEntry.objects.create(
                user_id         = request.user.pk,
                content_type_id = ContentType.objects.get_for_model(job).pk,
                object_id       = str(job.pk),
                object_repr     = 'JOB REJECTED - Job #{} - Worker: {} - Reason: {}'.format(
                    job.id, request.user.username, reason
                ),
                action_flag    = CHANGE,
                change_message = 'Worker rejected job. Reason: {} {}'.format(reason, comments)
            )
        except Exception as e:
            print('LogEntry error:', e)

        messages.warning(request, 'Job #{} rejected and marked as cancelled.'.format(job.id))
        return redirect('worker_dashboard')
    
    return redirect('worker_dashboard')

@login_required
def complete_job(request, job_id):
    """Worker completes a job"""
    job = get_object_or_404(ServiceRequest, id=job_id, assigned_worker=request.user)
    
    if request.method == 'POST':
        job.status = 'completed'
        
        # Check if user has active subscription
        try:
            subscription = UserSubscription.objects.get(
                user=job.user,
                status='active'
            )
            
            # Link job to subscription
            job.subscription = subscription
            
            # Increment usage count
            subscription.visits_used += 1
            subscription.save()
            
        except UserSubscription.DoesNotExist:
            # No subscription, payment will be required
            pass
            
        job.save()
        messages.success(request, "Job completed successfully!")
        
        return redirect('worker_dashboard')
 

@login_required
def rate_job(request, job_id):
    from booking.models import ServiceRequest, ServiceRating
    import json
    if request.method == 'POST':
        job = get_object_or_404(ServiceRequest, id=job_id, user=request.user)
        
        try:
            data   = json.loads(request.body)
            stars  = int(data.get('stars', 0))
            review = data.get('review', '')
        except Exception:
            stars  = int(request.POST.get('stars', 0))
            review = request.POST.get('review', '')

        if job.status != 'completed':
            return JsonResponse({'success': False, 'message': 'Job not completed yet'})
        if stars < 1 or stars > 5:
            return JsonResponse({'success': False, 'message': 'Select 1-5 stars'})
        if ServiceRating.objects.filter(job=job).exists():
            return JsonResponse({'success': False, 'message': 'Already rated this job'})

        ServiceRating.objects.create(
            job=job, user=request.user,
            worker=job.assigned_worker,
            stars=stars, review=review,
        )

        # Update worker average rating
        if job.assigned_worker:
            try:
                from workers.models import WorkerProfile
                profile   = WorkerProfile.objects.get(user=job.assigned_worker)
                ratings   = ServiceRating.objects.filter(worker=job.assigned_worker)
                total     = ratings.count()
                avg       = sum(r.stars for r in ratings) / total
                profile.total_ratings  = total
                profile.average_rating = round(avg, 2)
                profile.save(update_fields=['total_ratings', 'average_rating'])
            except Exception as e:
                print('Rating error:', e)

        return JsonResponse({'success': True, 'message': 'Rating submitted!'})

    return JsonResponse({'success': False, 'message': 'Invalid method'}) 

    # In booking/views.py — add this view:

@login_required
def get_worker_location(request, job_id):
    from datetime import timedelta

    try:
        job = ServiceRequest.objects.get(
            id=job_id,
            user=request.user,
            status__in=['assigned', 'in_progress']
        )

        if not job.assigned_worker:
            return JsonResponse({'success': False, 'message': 'No worker assigned'})

        profile = WorkerProfile.objects.get(user=job.assigned_worker)

        if not profile.location_sharing or not profile.latitude:
            return JsonResponse({'success': False, 'message': 'Worker is not sharing location yet'})

        # Check if location is fresh (within 5 minutes)
        if profile.location_updated_at:
            age = timezone.now() - profile.location_updated_at
            if age > timedelta(minutes=5):
                return JsonResponse({'success': False, 'message': 'Location data is outdated'})

        return JsonResponse({
            'success':    True,
            'latitude':   float(profile.latitude),
            'longitude':  float(profile.longitude),
            'updated_at': profile.location_updated_at.strftime('%H:%M:%S'),
            'worker':     job.assigned_worker.username,
        })

    except ServiceRequest.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Booking not found'})
    except WorkerProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Worker profile not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})