from django.db import models
from django.conf import settings

class EscalatedIssue(models.Model):
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='escalated_issues'
    )
    reason = models.TextField()
    message = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    seen_by_user  = models.BooleanField(default=False)  # ✅ add this
    resolved_message = models.TextField(blank=True, null=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_issues'
    )
    notes = models.TextField(blank=True)

    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Issue #{self.id} - {self.user.username} - {self.get_status_display()}"


class ChatMessage(models.Model):
    """Store chat messages between user and AI/admin"""
    MESSAGE_TYPE = (
        ('user', 'User Message'),
        ('ai', 'AI Response'),
        ('admin', 'Admin Response'),
        ('system', 'System Message'),
    )
    
    STATUS = (
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
        ('escalated', 'Escalated to Admin'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='chat_messages'
    )
    message = models.TextField()
    response = models.TextField(blank=True)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE, default='user')
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    escalated = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, help_text="Admin notes for this conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.created_at}"
    
class Notification(models.Model):
    """Notifications for users about resolved issues"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    issue = models.ForeignKey(
        EscalatedIssue,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"