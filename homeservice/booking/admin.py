from django.contrib import admin
from .models import ServiceRequest

class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "service", "status", "assigned_worker")
    list_editable = ("status", "assigned_worker")

admin.site.register(ServiceRequest, ServiceRequestAdmin)

