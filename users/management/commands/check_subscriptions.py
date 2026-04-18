from django.core.management.base import BaseCommand
from django.db import models  # Required for F() expressions
from datetime import date
from users.models import UserSubscription

class Command(BaseCommand):
    help = 'Check and expire subscriptions'

    def handle(self, *args, **options):
        today = date.today()
        
        # Expire by date (end date passed)
        expired_by_date = UserSubscription.objects.filter(
            status='active',
            end_date__lt=today
        ).update(status='expired')
        
        # Expire by visits (all visits used)
        expired_by_visits = UserSubscription.objects.filter(
            status='active',
            visits_used__gte=models.F('total_visits_allowed')
        ).update(status='expired')
        
        # Also check for subscriptions that should be active but have no visits left
        # This is a safety check
        auto_expired = UserSubscription.objects.filter(
            status='active',
            visits_used__gte=models.F('total_visits_allowed')
        ).update(status='expired')
        
        total_expired = expired_by_date + expired_by_visits + auto_expired
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Subscription check complete!\n'
                f'   • Expired by date: {expired_by_date}\n'
                f'   • Expired by visits: {expired_by_visits}\n'
                f'   • Total expired: {total_expired}'
            )
        )