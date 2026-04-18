from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import date, timedelta

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('worker', 'Worker'),
        ('admin', 'Admin'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    def __str__(self):
        return self.username


class SubscriptionPlan(models.Model):
    """Available subscription plans"""
    PLAN_TYPES = (
        ('basic', 'Basic'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    )
    
    name = models.CharField(max_length=50)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, default='basic')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    visits_allowed = models.IntegerField(default=10, help_text="Number of service visits allowed per month")
    discount_percentage = models.IntegerField(default=0, help_text="Discount on services")
    description = models.TextField(blank=True)
    features = models.TextField(blank=True, help_text="Comma-separated list of features")
    
    # Flags
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    free_inspection = models.BooleanField(default=False)
    emergency_service = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - ₹{self.price}/month"
    
    def get_features_list(self):
        if self.features:
            return [f.strip() for f in self.features.split(',')]
        return []
    
    class Meta:
        ordering = ['price']


from django.db import models
from django.conf import settings
from datetime import date

class UserSubscription(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey('SubscriptionPlan', on_delete=models.CASCADE)
    
    # Subscription period
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Usage tracking - IMPORTANT
    visits_used = models.IntegerField(default=0)
    total_visits_allowed = models.IntegerField()
    
    # Payment
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    auto_renew = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.visits_used}/{self.total_visits_allowed})"
    
    @property
    def visits_remaining(self):
        """Get remaining visits"""
        return max(0, self.total_visits_allowed - self.visits_used)
    
    @property
    def is_valid(self):
        """Check if subscription is valid and has remaining visits"""
        today = date.today()
        return (self.status == 'active' and 
                self.end_date >= today and 
                self.visits_used < self.total_visits_allowed)
    
    def use_visit(self):
        """Use one visit from subscription"""
        if self.visits_used < self.total_visits_allowed:
            self.visits_used += 1
            self.save()
            
            # Auto-expire if no visits left
            if self.visits_used >= self.total_visits_allowed:
                self.status = 'expired'
                self.save()
                return False, "Subscription expired - no visits remaining"
            return True, f"Visit used. {self.visits_remaining} visits remaining"
        return False, "No visits remaining"
    
    def check_and_expire(self):
        """Check if subscription should expire"""
        today = date.today()
        
        # Expire if end date passed
        if self.end_date < today:
            self.status = 'expired'
            self.save()
            return True, "Expired by date"
        
        # Expire if no visits left
        if self.visits_used >= self.total_visits_allowed:
            self.status = 'expired'
            self.save()
            return True, "Expired - all visits used"
        
        return False, "Still active"
    
    class Meta:
        ordering = ['-created_at']