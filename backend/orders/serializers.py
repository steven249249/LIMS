"""
orders/serializers.py
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Order, OrderStage

User = get_user_model()


class OrderStageSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    equipment_type_name = serializers.CharField(source='equipment_type.name', read_only=True)
    assignee_name = serializers.CharField(source='assignee.username', read_only=True)
    equipment_code = serializers.CharField(source='equipment.code', read_only=True)
    
    # Metadata from parent order
    order_no = serializers.CharField(source='order.order_no', read_only=True)
    user_name = serializers.CharField(source='order.user.username', read_only=True)
    lot_id = serializers.CharField(source='order.lot_id', read_only=True)

    class Meta:
        model = OrderStage
        fields = [
            'id', 'step_order', 'department_name', 'equipment_type_name',
            'status', 'assignee', 'assignee_name', 'equipment', 'equipment_code',
            'order_no', 'user_name', 'lot_id',
            'schedule_start', 'schedule_end', 'completed_at'
        ]


class OrderListSerializer(serializers.ModelSerializer):
    """Compact representation for list views."""
    user_name = serializers.CharField(source='user.username', read_only=True)
    experiment_name = serializers.CharField(source='experiment.name', read_only=True)
    stages = OrderStageSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_no', 'user_name', 'experiment_name', 
            'lot_id', 'status', 'is_urgent', 'created_at', 'stages'
        ]
        read_only_fields = ['id', 'order_no', 'status', 'created_at']


class OrderDetailSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    experiment_name = serializers.CharField(source='experiment.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    assignee_name = serializers.CharField(source='assignee.username', read_only=True)
    experiment_details = serializers.SerializerMethodField()
    # The detail drawer in the requester UI renders a relay-progress
    # ant-design Steps component off this list; without it the tracker
    # silently disappears.
    stages = OrderStageSerializer(many=True, read_only=True)

    def get_experiment_details(self, obj):
        if obj.experiment is None:
            return None
        from equipments.serializers import ExperimentSerializer
        return ExperimentSerializer(obj.experiment).data


    class Meta:
        model = Order
        fields = [
            'id', 'order_no', 'user', 'user_name',
            'department', 'department_name',
            'experiment', 'experiment_name', 'experiment_details',
            'status', 'is_urgent', 'lot_id', 'assignee', 'assignee_name',
            'schedule_start', 'schedule_end',
            'rejection_reason', 'remark',
            'created_at', 'updated_at', 'ended_at',
            'stages',
        ]
        read_only_fields = [
            'id', 'order_no', 'status', 'rejection_reason', 'assignee_name',
            'created_at', 'updated_at', 'ended_at',
        ]


class OrderCreateSerializer(serializers.Serializer):
    """Requester creates a single-lab-visit order.

    The wafer journey is now driven step by step by the requester: each Order
    represents exactly one lab visit, so the payload describes WHICH equipment
    type the wafer needs and (optionally) WHICH lab to send it to. The legacy
    ``experiment`` field is still accepted as an optional grouping tag.
    """
    equipment_type = serializers.UUIDField()
    target_department = serializers.UUIDField(required=False, allow_null=True)
    experiment = serializers.UUIDField(required=False, allow_null=True)
    is_urgent = serializers.BooleanField(default=False)
    lot_id = serializers.CharField(required=False, default='', allow_blank=True)
    remark = serializers.CharField(required=False, default='', allow_blank=True)


class OrderReviewSerializer(serializers.Serializer):
    """Lab Manager approves (with schedule) or rejects (with reason)."""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    rejection_reason = serializers.CharField(required=False, default='', allow_blank=True)
    schedule_start = serializers.DateTimeField(required=False)
    schedule_end = serializers.DateTimeField(required=False)
    assignee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role__in=['lab_member', 'lab_manager']),
        required=False, allow_null=True
    )


    def validate(self, data):
        if data['action'] == 'approve':
            if not data.get('schedule_start') or not data.get('schedule_end'):
                raise serializers.ValidationError(
                    'schedule_start and schedule_end are required when approving.'
                )
        if data['action'] == 'reject':
            if not data.get('rejection_reason', '').strip():
                raise serializers.ValidationError(
                    'rejection_reason is required when rejecting.'
                )
        return data
