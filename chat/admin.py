
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import EscalatedIssue

class EscalatedIssueAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'priority_colored',
        'status_colored',
        'reason_short',
        'created_at',
        'action_buttons'
    ]
    
    list_filter = ['priority', 'status', 'created_at']
    search_fields = ['user__username', 'reason', 'message']
    list_per_page = 20
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Issue Details', {
            'fields': ('reason', 'message', 'priority', 'status')
        }),
        ('Resolution', {
            'fields': ('resolved_at', 'resolved_by', 'notes'),
            'classes': ('wide',)
        }),
    )
    
    def priority_colored(self, obj):
        colors = {
            'low': '#27ae60', 'medium': '#f39c12',
            'high': '#e67e22', 'urgent': '#e74c3c',
        }
        color = colors.get(obj.priority, '#95a5a6')
        return format_html(
            '<span style="background:{0};color:white;padding:3px 10px;border-radius:12px;">{1}</span>',
            color,
            str(obj.get_priority_display() or obj.priority),
        )
    priority_colored.short_description = 'Priority'
    
    def status_colored(self, obj):
        colors = {
            'pending': '#f39c12', 'in_progress': '#3498db',
            'resolved': '#27ae60', 'closed': '#95a5a6',
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background:{0};color:white;padding:3px 10px;border-radius:12px;">{1}</span>',
            color,
            str(obj.get_status_display() or obj.status),
        )
    
    def reason_short(self, obj):
        return obj.reason[:50] + '...' if len(obj.reason) > 50 else obj.reason
    reason_short.short_description = 'Reason'
    
    # ✅ FIXED: Proper format_html usage with arguments
    def action_buttons(self, obj):
        if obj.status == 'pending':
            take_url = reverse('admin:chat_escalatedissue_change', args=[obj.id])
            return format_html(
                '<a class="button" href="{}" style="background: #3498db; color: white; padding: 3px 8px; text-decoration: none; border-radius: 3px; margin-right: 5px;">✓ Take</a>',
                take_url
            )
        elif obj.status == 'in_progress':
            resolve_url = reverse('admin:chat_escalatedissue_change', args=[obj.id])
            return format_html(
                '<a class="button" href="{}" style="background: #27ae60; color: white; padding: 3px 8px; text-decoration: none; border-radius: 3px;">✓ Resolve</a>',
                resolve_url
            )
        return '-'
    action_buttons.short_description = 'Actions'
    
    actions = ['mark_in_progress', 'mark_resolved']
    
    def mark_in_progress(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='in_progress')
        self.message_user(request, f"{updated} issues marked as in progress.")
    mark_in_progress.short_description = "Mark as In Progress"
    
    def mark_resolved(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            status='resolved',
            resolved_at=timezone.now(),
            resolved_by=request.user
        )
        self.message_user(request, f"{updated} issues marked as resolved.")
    mark_resolved.short_description = "Mark as Resolved"

admin.site.register(EscalatedIssue, EscalatedIssueAdmin)


