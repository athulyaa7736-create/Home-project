from django.core.management.base import BaseCommand
from payments.models import WorkerPayment
from workers.models import WorkerProfile
from booking.models import ServiceRequest

class Command(BaseCommand):
    help = 'Generate pending payments for all completed jobs without payments'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🔍 Checking for completed jobs without payments..."))
        
        # Find all completed jobs without payments
        completed_jobs = ServiceRequest.objects.filter(
            status='completed',
            worker_payment__isnull=True  # Jobs without payments
        ).select_related('assigned_worker', 'service')
        
        job_count = completed_jobs.count()
        
        if job_count == 0:
            self.stdout.write(self.style.WARNING("📭 No pending jobs found. All completed jobs have payments!"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"📋 Found {job_count} completed jobs without payments"))
        
        payments_created = 0
        
        for job in completed_jobs:
            try:
                # Get worker profile
                worker_profile = WorkerProfile.objects.get(user=job.assigned_worker)
                
                # Create payment
                payment = WorkerPayment.objects.create(
                    worker=worker_profile,
                    job=job,
                    fixed_rate=worker_profile.job_rate or 0,
                    amount=worker_profile.job_rate or 0,
                    status='pending'
                )
                
                payments_created += 1
                self.stdout.write(f"   ✅ Created payment #{payment.id} for {worker_profile.user.username} - Job #{job.id}")
                
            except WorkerProfile.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"   ❌ No worker profile for user {job.assigned_worker}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Error: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"\n🎉 Success! Created {payments_created} payments"))