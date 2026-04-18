from django.contrib import admin
from .models import Service

class ServiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'is_active']
    list_filter = ['is_active']

admin.site.register(Service, ServiceAdmin)
