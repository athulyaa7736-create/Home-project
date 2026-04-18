from django.db.models.signals import post_save
from django.dispatch import receiver
from booking.models import ServiceRequest
from workers.models import WorkerProfile
from .models import WorkerPayment

@receiver(post_save, sender=ServiceRequest)
def create_payment_on_job_completion(sender, instance, created, **kwargs):
    """Automatically create a payment when a job is marked as completed"""
    
    # Check if job status changed to completed
    if not created and instance.status == 'completed':
        
        # Check if payment doesn't already exist
        if not hasattr(instance, 'worker_payment'):
            try:
                # Get the worker profile
                worker_profile = WorkerProfile.objects.get(user=instance.assigned_worker)
                
                # Create payment
                payment = WorkerPayment.objects.create(
                    worker=worker_profile,
                    job=instance,
                    fixed_rate=worker_profile.job_rate or 0,  # Use job_rate from worker profile
                    amount=worker_profile.job_rate or 0,
                    status='pending'
                )
                
                print(f"✅ Auto-created payment #{payment.id} for worker {worker_profile.user.username}")
                
            except WorkerProfile.DoesNotExist:
                print(f"❌ No worker profile found for user {instance.assigned_worker}")
            except Exception as e:
                print(f"❌ Error creating payment: {e}")