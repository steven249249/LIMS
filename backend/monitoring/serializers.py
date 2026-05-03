from rest_framework import serializers

from .models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default=None)
    user_role = serializers.CharField(source='user.role', read_only=True, default=None)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)

    class Meta:
        model = ActivityLog
        fields = (
            'id',
            'timestamp',
            'username',
            'user_role',
            'action_type',
            'action_type_display',
            'http_method',
            'path',
            'status_code',
            'ip_address',
            'user_agent',
            'request_data',
            'duration_ms',
            'request_id',
        )
        read_only_fields = fields
