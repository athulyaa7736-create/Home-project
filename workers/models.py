from django.db import models
from django.conf import settings


class WorkerProfile(models.Model):
    AVAILABILITY_STATUS = (
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('on_leave', 'On Leave'),
        ('unavailable', 'Unavailable'),
        ('vacation', 'On Vacation'),
    )
    
    SERVICE_TYPE_CHOICES = (
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('carpentry', 'Carpentry'),
        ('cleaning', 'Cleaning'),
        ('painting', 'Painting'),
        ('ac_repair', 'AC Repair'),
    )
    
    PREFERRED_CONTACT_CHOICES = (
        ('phone', 'Phone Call'),
        ('whatsapp', 'WhatsApp'),
        ('both', 'Both'),
    )
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='worker_profile'
    )
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPE_CHOICES)
    experience = models.IntegerField(default=0)
    
    # Skills and area fields - ADD THESE
    skills = models.TextField(blank=True, help_text="List your skills (comma separated)")
    service_area = models.CharField(max_length=200, blank=True, help_text="Cities where you work")
    pincodes = models.CharField(max_length=500, blank=True, help_text="Comma separated pincodes")
    
    # Document fields - ADD THESE
    photo= models.ImageField(upload_to='worker_docs/photo/', blank=True, null=True)
    id_proof = models.ImageField(upload_to='worker_docs/id_proof/', blank=True, null=True)
    address_proof = models.ImageField(upload_to='worker_docs/address_proof/', blank=True, null=True)
    certificate = models.ImageField(upload_to='worker_docs/certificates/', blank=True, null=True)
    
    # Financial fields
    job_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fixed_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Verification
    verified = models.BooleanField(default=False)
    
    # Availability fields
    available = models.BooleanField(default=True)
    availability_status = models.CharField(
        max_length=20, 
        choices=AVAILABILITY_STATUS, 
        default='available'
    )
    
    # Contact preference - ADD THIS
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=PREFERRED_CONTACT_CHOICES,
        default='both'
    )
    phone_number = models.CharField(max_length=15, blank=True)

    # Workload
    current_jobs_count = models.IntegerField(default=0)
    max_jobs_per_day = models.IntegerField(
        default=3,
        help_text="Maximum jobs per day (set by admin)"
    )
    current_jobs_count = models.IntegerField(default=0)
    completed_jobs_count = models.IntegerField(default=0)
    
    # ✅ Daily job tracking
    jobs_today        = models.IntegerField(default=0)
    last_reset_date   = models.DateField(null=True, blank=True)

    # Ratings
    total_ratings = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    completed_jobs_count = models.IntegerField(default=0)
    
    # Timestamps
    last_active = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


     # Bank Details for Payments
    account_holder_name = models.CharField(max_length=100, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    upi_id = models.CharField(max_length=100, blank=True, help_text="UPI ID for instant payments")
    
    # Payment Preferences
    payment_method = models.CharField(
        max_length=20,
        choices=(
            ('bank', 'Bank Transfer'),
            ('upi', 'UPI'),
            ('cash', 'Cash Collection'),
        ),
        default='bank'
    )
    
    # Payment Tracking
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pending_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_paid_date = models.DateTimeField(null=True, blank=True)
    
     
    # Location tracking
    latitude        = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude       = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_updated_at = models.DateTimeField(null=True, blank=True)
    location_sharing    = models.BooleanField(default=False)  # worker can toggle

    def __str__(self):
        return f"{self.user.username} - {self.get_service_type_display()}"
    
    def get_display_status(self):
        """Return status with emoji for display"""
        if not self.available:
            return "🔴 Unavailable"
        
        status_icons = {
            'available': '🟢 Available',
            'busy': '🟡 Busy',
            'on_leave': '🔴 On Leave',
            'unavailable': '⚪ Unavailable',
            'vacation': '🌴 On Vacation',
        }
        return status_icons.get(self.availability_status, '⚪ Unknown')
    
    def reset_daily_jobs_if_needed(self):
            """Reset daily counter if it's a new day"""
            from datetime import date
            today = date.today()
            if self.last_reset_date != today:
                self.jobs_today     = 0
                self.last_reset_date = today
                self.save(update_fields=['jobs_today', 'last_reset_date'])
        
    @property
    def slots_remaining_today(self):
            """How many slots left today"""
            self.reset_daily_jobs_if_needed()
            return max(0, self.max_jobs_per_day - self.jobs_today)
        
    @property
    def is_available_today(self):
            """Can take more jobs today"""
            return self.slots_remaining_today > 0


class WorkerNotification(models.Model):
    NOTIF_TYPES = (
        ('job_assigned', 'New Job Assigned'),
        ('job_updated',  'Job Updated'),
        ('payment_sent', 'Payment Sent'),
        ('general',      'General'),
    )
    worker = models.ForeignKey(
        'workers.WorkerProfile',   # ✅ correct app
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPES, default='general')
    job        = models.ForeignKey(
        'booking.ServiceRequest',  # ✅ correct app
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return '{} - {}'.format(self.worker.user.username, self.title)