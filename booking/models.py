from django.db import models
from django.conf import settings
from services.models import Service


User = settings.AUTH_USER_MODEL


class ServiceRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='service_requests')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    address = models.TextField()
    issue_image = models.ImageField(upload_to="issues/", null=True, blank=True)
    
    # Add these fields if you want them
    notes = models.TextField(blank=True, help_text="Any special instructions")
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time = models.TimeField(null=True, blank=True)
    
    assigned_worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_jobs"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Link to subscription if used
    subscription = models.ForeignKey(
        'users.UserSubscription',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_requests'
    )
    
    def __str__(self):
        return f"{self.user.username} - {self.service.name}"
    
    def complete_service(self):
        """Mark service as completed and update subscription if needed"""
        self.status = 'completed'
        self.save()
        
        # If this service used a subscription, update the subscription
        if self.subscription:
            success, message = self.subscription.use_visit()
            return success, message
        return False, "No subscription linked"
    
    class Meta:
        ordering = ['-created_at']


class ServiceRating(models.Model):
    job      = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, related_name='rating')
    user     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    worker   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_ratings')
    stars    = models.IntegerField(choices=[(i,i) for i in range(1,6)])
    review   = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return 'Job #{} - {} stars by {}'.format(self.job.id, self.stars, self.user.username)
            

class JobRejection(models.Model):
    REASON_CHOICES = (
        ('too_busy', 'Too busy with other jobs'),
        ('out_of_area', 'Outside my service area'),
        ('not_qualified', 'Not qualified for this service'),
        ('personal', 'Personal reason'),
        ('other', 'Other'),
    )
    
    job = models.OneToOneField(
        ServiceRequest, 
        on_delete=models.CASCADE,
        related_name='rejection'
    )
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rejected_jobs'
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    comments = models.TextField(blank=True)
    rejected_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.worker.username} rejected job #{self.job.id} - {self.get_reason_display()}"



