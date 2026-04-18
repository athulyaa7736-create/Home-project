from django.db import models
from django.conf import settings
from booking.models import ServiceRequest
from workers.models import WorkerProfile
from django.utils import timezone
from users.models import UserSubscription 

User = settings.AUTH_USER_MODEL

class Payment(models.Model):
    """Customer payments for services"""
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('pending_collection', 'Pending Cash Collection'),
        ('partial_refunded', 'Partially Refunded'),
    ]
    
    PAYMENT_METHODS = [
        ('upi', 'UPI'),
        ('card', 'Card'),
        ('netbanking', 'Net Banking'),
        ('cash', 'Cash'),
        ('netbanking', 'Net Banking'),
        ('wallet', 'Wallet'),
    ]

    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    booking = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, related_name='payment')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    
    transaction_id = models.CharField(max_length=100, unique=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    
    # Subscription payment
    subscription = models.ForeignKey(
        'users.UserSubscription',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    
    # UPI specific
    upi_id = models.CharField(max_length=100, blank=True)
    upi_transaction_id = models.CharField(max_length=100, blank=True)
    
    # Card specific
    card_last_four = models.CharField(max_length=4, blank=True)
    card_type = models.CharField(max_length=20, blank=True)
    
    # Cash specific
    cash_received = models.BooleanField(default=False)
    cash_received_date = models.DateTimeField(null=True, blank=True)
    cash_received_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='cash_collected_payments'
    )
    cash_rejection_date = models.DateTimeField(null=True, blank=True)
    cash_rejection_reason = models.CharField(max_length=255, blank=True)
    
    # Refund fields
    refund_requested = models.BooleanField(default=False)
    refund_request_date = models.DateTimeField(null=True, blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    refund_date = models.DateTimeField(null=True, blank=True)
    refund_reason = models.TextField(blank=True)
    refunded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='refunded_payments'
    )
    
    # Notes
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - ₹{self.amount} - {self.status}"
    
    def get_payment_method_display_with_icon(self):
        icons = {
            'upi': '📱',
            'card': '💳',
            'netbanking': '🏦',
            'cash': '💵',
        }
        icon = icons.get(self.payment_method, '💰')
        return f"{icon} {self.get_payment_method_display()}"
    
    class Meta:
        ordering = ['-payment_date', '-created_at']

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50)  # Basic, Gold, Premium
    price = models.DecimalField(max_digits=10, decimal_places=2)
    visits_allowed = models.IntegerField(default=10)
    discount_percentage = models.IntegerField(default=0)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Subscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, default='active')  # active, expired, cancelled
    visits_used = models.IntegerField(default=0)
    auto_renew = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"




class WorkerPayment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    PAYMENT_METHODS = [
        ('bank', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
    ]
    
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='payments')
    # FIXED: Added unique related_name
    job = models.OneToOneField(
        ServiceRequest, 
        on_delete=models.CASCADE, 
        related_name='worker_payment',  # Changed from 'payment' to 'worker_payment'
        null=True, 
        blank=True
    )
    
    # Payment details based on fixed rate
    fixed_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text="Fixed rate at time of payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # For bulk payments (multiple jobs)
    is_bulk_payment = models.BooleanField(default=False)
    job_count = models.IntegerField(default=1, help_text="Number of jobs in this payment")
    job_ids = models.TextField(blank=True, help_text="Comma-separated job IDs")
    
    # Status
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_date = models.DateTimeField(null=True, blank=True)
    
    # Transaction details
    transaction_id = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='bank')
    payment_reference = models.CharField(max_length=200, blank=True)
    admin_notes = models.TextField(blank=True)
    
    # Bank details snapshot (at time of payment)
    account_holder_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=30, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    upi_id = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='processed_payments'
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.worker.user.username} - ₹{self.amount} - {self.status}"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # On creation
            # Store worker's current bank details as snapshot
            self.account_holder_name = self.worker.account_holder_name
            self.account_number = self.worker.account_number
            self.ifsc_code = self.worker.ifsc_code
            self.bank_name = self.worker.bank_name
            self.upi_id = self.worker.upi_id
            
            if not self.fixed_rate:
                self.fixed_rate = self.worker.fixed_rate_per_job
            
            if not self.amount and self.fixed_rate:
                self.amount = self.fixed_rate * self.job_count
        
        super().save(*args, **kwargs)
    
    def get_masked_account(self):
        """Return masked account number for display"""
        if self.account_number and len(self.account_number) > 4:
            return '*' * (len(self.account_number) - 4) + self.account_number[-4:]
        return self.account_number or 'Not provided'


  



 