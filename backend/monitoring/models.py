import uuid

from django.conf import settings
from django.db import models


class ActivityLog(models.Model):
    """Records every authenticated API interaction for audit and admin review."""

    class ActionType(models.TextChoices):
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        CREATE = 'create', 'Create'
        READ = 'read', 'Read'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
    )
    action_type = models.CharField(
        max_length=16,
        choices=ActionType.choices,
        default=ActionType.OTHER,
        db_index=True,
    )
    http_method = models.CharField(max_length=8)
    path = models.CharField(max_length=255)
    status_code = models.PositiveSmallIntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True, default='')
    request_data = models.JSONField(null=True, blank=True)
    request_id = models.CharField(max_length=64, blank=True, default='', db_index=True)
    duration_ms = models.PositiveIntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'activity_log'
        ordering = ('-timestamp',)
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action_type', '-timestamp']),
        ]

    def __str__(self):
        actor = self.user.username if self.user else 'anonymous'
        return f'[{self.timestamp:%Y-%m-%d %H:%M}] {actor} {self.http_method} {self.path}'
