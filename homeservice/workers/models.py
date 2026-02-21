from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class WorkerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    service_type = models.CharField(max_length=100)
    experience = models.IntegerField()
    available = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username
