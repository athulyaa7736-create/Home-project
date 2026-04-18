from django.core.management.base import BaseCommand
from workers.models import WorkerProfile
from datetime import date

class Command(BaseCommand):
    help = 'Reset daily job counters for all workers'

    def handle(self, *args, **kwargs):
        today = date.today()
        updated = 0
        for profile in WorkerProfile.objects.all():
            if profile.last_reset_date != today:
                profile.jobs_today      = 0
                profile.last_reset_date = today
                profile.save(update_fields=['jobs_today', 'last_reset_date'])
                updated += 1
        self.stdout.write(
            self.style.SUCCESS('Reset {} worker counters for {}'.format(updated, today))
        )