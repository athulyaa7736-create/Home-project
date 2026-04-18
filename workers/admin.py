from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import WorkerProfile
from booking.models import ServiceRequest

class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'user', 
        'service_type', 
        'experience',  
        'phone_number',  # Added phone number
        'max_jobs_per_day', 
        'current_jobs_simple',  # Using simple version first
        'completed_jobs_simple',  # Using simple version first
        'available',
        'job_rate',
        'verified',
    ]
    
    list_editable = ['verified', 'available', 'job_rate', 'max_jobs_per_day']
    list_filter = ['verified', 'available', 'service_type']
    search_fields = ['user__username', 'service_type']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'service_type', 'experience', 'skills')
        }),
        ('Workload Management', {
            'fields': ('max_jobs_per_day', 'current_jobs_count'),
            'classes': ('wide',)
        }),
        ('Service Area', {
            'fields': ('service_area', 'pincodes')
        }),
        ('Contact Preference', {
            'fields': ('preferred_contact_method','phone_number')
        }),
        ('Documents', {
            'fields': ('photo', 'id_proof', 'address_proof', 'certificate'),
        }),
        ('Financials', {
            'fields': ('job_rate', 'fixed_rate')
        }),
        ('Verification', {
            'fields': ('verified', 'available'),
        }),
    )
    
    readonly_fields = ['current_jobs_count']
    
    # SIMPLE VERSION - No format_html first
    def current_jobs_simple(self, obj):
        """Simple version without format_html"""
        from booking.models import ServiceRequest
        
        current_jobs = ServiceRequest.objects.filter(
            assigned_worker=obj.user,
            status__in=['assigned', 'in_progress']
        ).count()
        
        # Update the model field
        if obj.current_jobs_count != current_jobs:
            obj.current_jobs_count = current_jobs
            obj.save(update_fields=['current_jobs_count'])
        
        return f"{current_jobs} / {obj.max_jobs_per_day}"
    current_jobs_simple.short_description = 'Current Jobs'
    
    # SIMPLE VERSION - No format_html
    def completed_jobs_simple(self, obj):
        """Simple version without format_html"""
        from booking.models import ServiceRequest
        
        completed_jobs = ServiceRequest.objects.filter(
            assigned_worker=obj.user,
            status='completed'
        )
        
        completed_count = completed_jobs.count()
        job_rate = obj.job_rate or 0
        total_earnings = completed_count * job_rate
        
        return f"{completed_count} jobs - ₹{total_earnings} (₹{job_rate}/job)"
    completed_jobs_simple.short_description = 'Completed Jobs'
    
    # If the above works, then we can add this enhanced version
    def current_jobs_display(self, obj):
        """Enhanced version with colors (only if simple version works)"""
        from booking.models import ServiceRequest
        
        current_jobs = ServiceRequest.objects.filter(
            assigned_worker=obj.user,
            status__in=['assigned', 'in_progress']
        ).count()
        
        in_progress = ServiceRequest.objects.filter(
            assigned_worker=obj.user,
            status='in_progress'
        ).count()
        
        assigned = ServiceRequest.objects.filter(
            assigned_worker=obj.user,
            status='assigned'
        ).count()
        
        # Update the model field
        if obj.current_jobs_count != current_jobs:
            obj.current_jobs_count = current_jobs
            obj.save(update_fields=['current_jobs_count'])
        
        # Choose color based on load
        if current_jobs >= obj.max_jobs_per_day:
            color = '#e74c3c'  # Red
            indicator = '🔴'
        elif current_jobs > 0:
            color = '#f39c12'  # Orange
            indicator = '🟡'
        else:
            color = '#27ae60'  # Green
            indicator = '🟢'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;" title="In Progress: {} | Assigned: {}">{} {} / {}</span>',
            color,
            str(in_progress),
            str(assigned),
            indicator,
            str(current_jobs),
            str(obj.max_jobs_per_day)
        )
    current_jobs_display.short_description = 'Current Jobs'
    
    def completed_jobs_display(self, obj):
        """Enhanced version with earnings"""
        from booking.models import ServiceRequest
        
        completed_jobs = ServiceRequest.objects.filter(
            assigned_worker=obj.user,
            status='completed'
        )
        
        completed_count = completed_jobs.count()
        job_rate = obj.job_rate or 0
        total_earnings = completed_count * job_rate
        
        paid_count = completed_jobs.filter(payment__isnull=False).count()
        unpaid_count = completed_count - paid_count
        
        if completed_count > 0:
            return format_html(
                '<div style="text-align: center;">'
                '<span style="color: #27ae60; font-weight: bold;">{} completed</span><br>'
                '<span style="color: #2c3e50; font-weight: bold;">₹{}</span><br>'
                '<small>{} jobs × ₹{}/job</small><br>'
                '<small style="color: {};">{} paid | {} pending</small>'
                '</div>',
                str(completed_count),
                str(total_earnings),
                str(completed_count),
                str(job_rate),
                '#27ae60' if unpaid_count == 0 else '#e67e22',
                str(paid_count),
                str(unpaid_count)
            )
        else:
            return format_html(
                '<span style="color: #95a5a6;">No completed jobs</span>'
            )
    completed_jobs_display.short_description = 'Completed Jobs & Earnings'

    def view_photo(self, obj):
        if obj.photo:
            return format_html(
                '<a href="{}" target="_blank" style="background: #3498db; color: white; padding: 3px 10px; border-radius: 3px; text-decoration: none;">📄 View Photo</a>',
                obj.photo.url
            )
        return "Not uploaded"
    view_photo.short_description = 'Photo'
    
    def view_id_proof(self, obj):
        if obj.id_proof:
            return format_html(
                '<a href="{}" target="_blank" style="background: #3498db; color: white; padding: 3px 10px; border-radius: 3px; text-decoration: none;">📄 View ID</a>',
                obj.id_proof.url
            )
        return "Not uploaded"
    view_id_proof.short_description = 'ID Proof'
    
    def view_address_proof(self, obj):
        if obj.address_proof:
            return format_html(
                '<a href="{}" target="_blank" style="background: #3498db; color: white; padding: 3px 10px; border-radius: 3px; text-decoration: none;">📍 View Address</a>',
                obj.address_proof.url
            )
        return "Not uploaded"
    view_address_proof.short_description = 'Address Proof'
    
    def view_certificate(self, obj):
        if obj.certificate:
            return format_html(
                '<a href="{}" target="_blank" style="background: #27ae60; color: white; padding: 3px 10px; border-radius: 3px; text-decoration: none;">📜 View Certificate</a>',
                obj.certificate.url
            )
        return "Not uploaded"
    view_certificate.short_description = 'Certificate'
    
    def quick_actions(self, obj):
        """Quick action buttons"""
        actions = []
        
        # View Jobs Button
        jobs_url = reverse('admin:booking_servicerequest_changelist') + f'?assigned_worker__id__exact={obj.user.id}'
        actions.append(
            f'<a href="{jobs_url}" style="background: #17a2b8; color: white; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-size: 11px; margin-right: 5px;">📋 Jobs</a>'
        )
        
        # Get completed jobs without payments
        from booking.models import ServiceRequest
        completed_jobs = ServiceRequest.objects.filter(
            assigned_worker=obj.user,
            status='completed',
            payment__isnull=True
        ).count()
        
        # Quick Pay Button
        if completed_jobs > 0:
            job_rate = obj.job_rate or 0
            amount = completed_jobs * job_rate
            actions.append(
                f'<a href="#" onclick="alert(\'Pay ₹{amount} for {completed_jobs} jobs\')" style="background: #28a745; color: white; padding: 3px 8px; border-radius: 4px; text-decoration: none; font-size: 11px;">💰 Pay ₹{amount}</a>'
            )
        
        return format_html(''.join(actions))
    quick_actions.short_description = 'Actions'
    
    actions = ['update_job_counts']
    
    def update_job_counts(self, request, queryset):
        """Update job counts for selected workers"""
        from booking.models import ServiceRequest
        
        updated = 0
        for worker in queryset:
            current_jobs = ServiceRequest.objects.filter(
                assigned_worker=worker.user,
                status__in=['assigned', 'in_progress']
            ).count()
            
            if worker.current_jobs_count != current_jobs:
                worker.current_jobs_count = current_jobs
                worker.save(update_fields=['current_jobs_count'])
                updated += 1
        
        self.message_user(request, f'✅ Updated job counts for {updated} workers')
    update_job_counts.short_description = "Update job counts"

# Register the admin class
admin.site.register(WorkerProfile, WorkerProfileAdmin)