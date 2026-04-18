from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Q

class Service(models.Model):
    CATEGORY_CHOICES = (
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('carpentry', 'Carpentry'),
        ('cleaning', 'Cleaning'),
        ('painting', 'Painting'),
        ('ac_repair', 'AC Repair'),
        ('appliance', 'Appliance Repair'),
        ('other', 'Other'),
    )
    
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    icon = models.CharField(max_length=50, default="fas fa-tools")
    duration = models.CharField(max_length=50, blank=True)
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


class ServicePlan(models.Model):
    PLAN_TYPES = (
        ('one_time', 'One Time Service'),
        ('before_service', 'Before Service Check'),
        ('after_service', 'After Service Support'),
        ('monthly', 'Monthly Plan'),
        ('yearly', 'Yearly Plan'),
        ('quarterly', 'Quarterly Plan'),
    )
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    service = models.ForeignKey('Service', on_delete=models.CASCADE, related_name='plans')
    description = models.TextField()
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Plan details
    duration_months = models.IntegerField(default=1, help_text="For monthly/yearly plans")
    visits_included = models.IntegerField(default=1, help_text="Number of visits included")
    emergency_visits = models.IntegerField(default=0, help_text="Emergency visits included")
    
    # Features
    features = models.JSONField(default=list, help_text="List of features included")
    popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - ₹{self.price}"
    
    def get_final_price(self):
        return self.discount_price if self.discount_price else self.price
    
    def get_savings_percentage(self):
        if self.discount_price and self.price:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0
    


