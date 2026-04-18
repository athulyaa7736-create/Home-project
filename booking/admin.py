from django.contrib import admin
from django.urls import reverse
from users.models import CustomUser
from .models import ServiceRequest, JobRejection
from django.db import models
from booking.models import ServiceRating
from payments.models import Payment

class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'service',
        'status',
        'payment_status',
        'worker_info',
        'created_at'
    ]
    
    list_filter = ['status', 'service__category', 'created_at']
    search_fields = ['user__username', 'service__name']
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'service', 'assigned_worker', 'subscription', 'subscription__plan'
        )
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('user',)
        }),
        ('Service Details', {
            'fields': ('service', 'address', 'issue_image', 'notes')
        }),
        ('Worker Assignment', {
            'fields': ('assigned_worker', 'status'),
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        if obj and obj.pk:
            service_category = obj.service.category
            
            # ✅ Filter out None values from busy_ids
            busy_ids = list(ServiceRequest.objects.filter(
                status__in=['assigned', 'in_progress', 'pending'],
                assigned_worker__isnull=False  # ← exclude unassigned jobs
            ).values_list('assigned_worker_id', flat=True))
    
            workers = CustomUser.objects.filter(
                role='worker',
                worker_profile__service_type=service_category,
                worker_profile__verified=True,
                worker_profile__available=True,
            ).select_related('worker_profile')
    
            # ✅ Only exclude if busy_ids has actual values
            if busy_ids:
                workers = workers.exclude(id__in=busy_ids)
    
            form.base_fields['assigned_worker'].queryset = workers
            form.base_fields['assigned_worker'].required = False
    
            def worker_label(worker):
                if not hasattr(worker, 'worker_profile'):
                    return worker.username
                profile = worker.worker_profile
    
                total_assigned  = ServiceRequest.objects.filter(
                    assigned_worker=worker).count()
                total_completed = ServiceRequest.objects.filter(
                    assigned_worker=worker, status='completed').count()
                active          = ServiceRequest.objects.filter(
                    assigned_worker=worker,
                    status__in=['assigned', 'in_progress']
                ).count()
    
                try:
                    profile.reset_daily_jobs_if_needed()
                    today_info = '{}/{} today'.format(
                        profile.jobs_today, profile.max_jobs_per_day)
                except Exception:
                    today_info = 'Cap: {}/day'.format(profile.max_jobs_per_day)
    
                status = '🟢 Free' if active == 0 else '🟡 {} active job(s)'.format(active)
    
                return '{} | {}yrs | {} | {} | Total: {} assigned, {} completed'.format(
                    worker.username,
                    profile.experience,
                    status,
                    today_info,
                    total_assigned,
                    total_completed,
                )
    
            form.base_fields['assigned_worker'].label_from_instance = worker_label
    
        return form
    
    def worker_info(self, obj):
        if not obj.assigned_worker:
            if obj.status == 'pending':
                return 'Pending assignment'
            elif obj.status == 'cancelled':
                return 'Cancelled'
            return '-'
    
        # ✅ Get total stats for this worker
        total     = ServiceRequest.objects.filter(
            assigned_worker=obj.assigned_worker
        ).count()
        completed = ServiceRequest.objects.filter(
            assigned_worker=obj.assigned_worker,
            status='completed'
        ).count()
        active    = ServiceRequest.objects.filter(
            assigned_worker=obj.assigned_worker,
            status__in=['assigned', 'pending', 'in_progress']
        ).count()
    
        name = obj.assigned_worker.username
    
        if obj.status == 'completed':
            return 'Done by: {} | Total: {} | Completed: {} | Active: {}'.format(
                name, total, completed, active)
        elif obj.status == 'in_progress':
            return 'In Progress: {} | Total: {} | Completed: {} | Active: {}'.format(
                name, total, completed, active)
        elif obj.status == 'assigned':
            return 'Assigned: {} | Total: {} | Completed: {} | Active: {}'.format(
                name, total, completed, active)
        elif obj.status == 'cancelled':
            return 'Cancelled | Was: {}'.format(name)
        return '{} | Total: {} | Completed: {}'.format(name, total, completed)
    
    worker_info.short_description = 'Worker / Stats'

    def payment_status(self, obj):
        # Check if service request is covered by subscription
        if obj.subscription:
            return "📅 Covered by Subscription"
        
        try:
            payment = obj.payment
            status_colors = {
                'pending': '🟡',
                'completed': '🟢',
                'failed': '🔴',
                'refunded': '🔵',
                'pending_collection': '🟠',
                'partial_refunded': '🟣'
            }
            color = status_colors.get(payment.status, '⚪')
            return f"{color} {payment.get_status_display()}"
        except:
            return "⚪ No Payment"
    
    payment_status.short_description = 'Payment Status'

    # ✅ ADD THIS — creates notification when worker is assigned
    def save_model(self, request, obj, form, change):
        # Save old worker before update
        old_worker = None
        if change:
            try:
                old_obj = ServiceRequest.objects.get(pk=obj.pk)
                old_worker = old_obj.assigned_worker
            except Exception:
                pass

        super().save_model(request, obj, form, change)

        # ✅ Only notify if worker was just assigned (new or changed)
        if obj.assigned_worker and obj.assigned_worker != old_worker:
            try:
                from workers.models import WorkerProfile, WorkerNotification
                profile = WorkerProfile.objects.get(user=obj.assigned_worker)
                WorkerNotification.objects.create(
                    worker     = profile,
                    title      = 'New Job Assigned!',
                    message    = 'You have been assigned a {} job for customer {}. Amount: Rs.{}.'.format(
                        obj.service.name  if obj.service  else 'Service',
                        obj.user.username if obj.user     else 'Customer',
                        obj.service.price if obj.service  else '0',
                    ),
                    notif_type = 'job_assigned',
                    job        = obj,
                )
            except Exception as e:
                print('Notification error:', e)

    
    def worker_label(worker):
        if not hasattr(worker, 'worker_profile'):
            return worker.username
        
        profile = worker.worker_profile
          # reset if new day
        try:
              profile.reset_daily_jobs_if_needed()
        except Exception:
                pass
        
        remaining = profile.slots_remaining_today
        completed_today = profile.jobs_today
        
        # ✅ Total jobs ever assigned to this worker
        total_assigned = ServiceRequest.objects.filter(
            assigned_worker=worker
        ).count()
        
        # ✅ Total completed lifetime
        total_completed = ServiceRequest.objects.filter(
            assigned_worker=worker,
            status='completed'
        ).count()
        
        # ✅ Currently active jobs
        active_jobs = ServiceRequest.objects.filter(
            assigned_worker=worker,
            status__in=['assigned', 'pending', 'in_progress']
        ).count()
    
        # Today's availability
        if remaining > 0:
            today_status = '🟢 {} slot{} left today ({}/{} used)'.format(
                remaining,
                's' if remaining != 1 else '',
                completed_today,
                profile.max_jobs_per_day
            )
        else:
            today_status = '🔴 FULL today ({}/{} jobs done)'.format(
                completed_today, profile.max_jobs_per_day
            )
    
        return '{} | {}yrs exp | {} | 📊 Total: {} assigned, {} completed, {} active now'.format(
            worker.username,
            profile.experience,
            today_status,
            total_assigned,
            total_completed,
            active_jobs,
        )

class JobRejectionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'job_id',
        'worker_name',
        'reason',
        'short_comments',
        'rejected_at'
    ]
    
    list_filter = ['reason', 'rejected_at']
    search_fields = ['worker__username', 'job__id', 'comments']
    
    def job_id(self, obj):
        return f"Job #{obj.job.id}"
    job_id.short_description = 'Job'
    
    def worker_name(self, obj):
        return obj.worker.username
    worker_name.short_description = 'Worker'
    
    def short_comments(self, obj):
        return obj.comments[:30] + '...' if len(obj.comments) > 30 else obj.comments
    short_comments.short_description = 'Comments'



@admin.register(ServiceRating)
class ServiceRatingAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_job', 'get_customer', 'get_worker', 
                    'star_display', 'review_short', 'created_at']
    list_filter  = ['stars', 'created_at']
    search_fields = ['user__username', 'worker__username', 'review']
    ordering = ['-created_at']

    def get_job(self, obj):
        return 'Job #{}'.format(obj.job.id)
    get_job.short_description = 'Job'

    def get_customer(self, obj):
        return obj.user.username
    get_customer.short_description = 'Customer'

    def get_worker(self, obj):
        return obj.worker.username if obj.worker else '-'
    get_worker.short_description = 'Worker'

    def star_display(self, obj):
        return '★' * obj.stars + '☆' * (5 - obj.stars)
    star_display.short_description = 'Rating'

    def review_short(self, obj):
        return obj.review[:50] if obj.review else '-'
    review_short.short_description = 'Review'

admin.site.register(ServiceRequest, ServiceRequestAdmin)
admin.site.register(JobRejection, JobRejectionAdmin)