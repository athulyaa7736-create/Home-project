from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser, SubscriptionPlan, UserSubscription

# Custom User Admin
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['id', 'username', 'email', 'role', 'phone', 'is_active']
    list_filter = ['role', 'is_active']
    search_fields = ['username', 'email', 'phone']
    list_editable = ['role']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone', 'address', 'profile_pic')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone', 'password1', 'password2', 'role'),
        }),
    )

# Subscription Plan Admin
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'visits_allowed', 'discount_percentage', 'is_active', 'is_popular']
    list_filter = ['is_active', 'plan_type', 'is_popular']
    search_fields = ['name']
    list_editable = ['price', 'is_active', 'is_popular']
    
    fieldsets = (
        ('Plan Information', {
            'fields': ('name', 'plan_type', 'price', 'visits_allowed', 'discount_percentage', 'description')
        }),
        ('Features', {
            'fields': ('priority_support', 'free_inspection', 'emergency_service')
        }),
        ('Status', {
            'fields': ('is_active', 'is_popular')
        }),
    )

# User Subscription Admin
@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'plan', 'status', 'start_date', 'end_date', 'visits_used', 'visits_remaining_display']
    list_filter = ['status', 'plan']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Plan Information', {
            'fields': ('plan',)
        }),
        ('Subscription Period', {
            'fields': ('start_date', 'end_date')
        }),
        ('Usage', {
            'fields': ('visits_used', 'total_visits_allowed')
        }),
        ('Payment', {
            'fields': ('amount_paid', 'transaction_id', 'payment_date')
        }),
        ('Status', {
            'fields': ('status', 'auto_renew')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def visits_remaining_display(self, obj):
        remaining = obj.visits_remaining
        total = obj.total_visits_allowed
        percentage = (obj.visits_used / total * 100) if total > 0 else 0
        
        if remaining <= 0:
            return format_html(
                '<span style="color: #e74c3c; font-weight: bold;">0 / {} (Expired)</span>',
                total
            )
        elif remaining <= 3:
            return format_html(
                '<span style="color: #f39c12; font-weight: bold;">{} / {} (Low)</span>',
                remaining, total
            )
        else:
            return format_html(
                '<span style="color: #27ae60; font-weight: bold;">{} / {}</span>',
                remaining, total
            )
    visits_remaining_display.short_description = 'Visits Left'
    
    actions = ['extend_subscription', 'mark_as_expired']
    
    def extend_subscription(self, request, queryset):
        from datetime import timedelta
        for sub in queryset:
            if sub.status == 'active':
                sub.end_date += timedelta(days=30)
                sub.save()
        self.message_user(request, f"Extended {queryset.count()} subscriptions by 30 days")
    extend_subscription.short_description = "Extend by 30 days"
    
    def mark_as_expired(self, request, queryset):
        queryset.update(status='expired')
        self.message_user(request, f"Marked {queryset.count()} subscriptions as expired")
    mark_as_expired.short_description = "Mark as expired"