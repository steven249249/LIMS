"""
orders/serializers.py
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Order, OrderStage

User = get_user_model()


class OrderStageSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    assignee_name = serializers.CharField(source='assignee.username', read_only=True)
    equipment_code = serializers.CharField(source='equipment.code', read_only=True)

    # Metadata from parent order — the manager uses experiment_name as the
    # recipe context when scheduling. equipment_type_name is kept for legacy
    # rows but is normally NULL on new stages.
    order_no = serializers.CharField(source='order.order_no', read_only=True)
    user_name = serializers.CharField(source='order.user.username', read_only=True)
    lot_id = serializers.CharField(source='order.lot_id', read_only=True, default='')
    experiment_name = serializers.CharField(source='order.experiment.name', read_only=True)
    is_urgent = serializers.BooleanField(source='order.is_urgent', read_only=True)
    requirements = serializers.CharField(source='order.requirements', read_only=True)
    remark = serializers.CharField(source='order.remark', read_only=True)
    equipment_type_name = serializers.CharField(source='equipment_type.name', read_only=True)

    class Meta:
        model = OrderStage
        fields = [
            'id', 'step_order', 'department_name',
            'status', 'assignee', 'assignee_name', 'equipment', 'equipment_code',
            'order_no', 'user_name', 'lot_id',
            'experiment_name', 'is_urgent', 'requirements', 'remark', 'equipment_type_name',
            'schedule_start', 'schedule_end', 'completed_at',
        ]


class OrderListSerializer(serializers.ModelSerializer):
    """Compact representation for list views."""
    user_name = serializers.CharField(source='user.username', read_only=True)
    experiment_name = serializers.CharField(source='experiment.name', read_only=True)
    # ``Order.lot`` is now an FK to WaferLot (whose PK is the code), so
    # ``order.lot_id`` returns the underlying code string. Expose it under
    # the historical "lot_id" field name to keep frontend reads stable.
    lot_id = serializers.CharField(read_only=True, default='')
    stages = OrderStageSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_no', 'user_name', 'experiment_name',
            'lot_id', 'status', 'is_urgent', 'requirements', 'remark',
            'created_at', 'stages',
        ]
        read_only_fields = ['id', 'order_no', 'status', 'created_at']


class OrderDetailSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    experiment_name = serializers.CharField(source='experiment.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    assignee_name = serializers.CharField(source='assignee.username', read_only=True)
    lot_id = serializers.CharField(read_only=True, default='')
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
            'rejection_reason', 'requirements', 'remark',
            'created_at', 'updated_at', 'ended_at',
            'stages',
        ]
        read_only_fields = [
            'id', 'order_no', 'status', 'rejection_reason', 'assignee_name',
            'created_at', 'updated_at', 'ended_at',
        ]


class OrderCreateSerializer(serializers.Serializer):
    """Requester creates a single-lab-visit order.

    Experiments are pinned to a lab, so the requester only picks the
    experiment plus optional metadata; the order routes to the experiment's
    lab automatically and the requester never sees machines.

    ``lot_id`` MUST resolve to an existing WaferLot row (it's the PK of
    that table) — the form uses a dropdown sourced from the registered
    lots so a typo cannot reach the API.
    """
    experiment = serializers.UUIDField()
    is_urgent = serializers.BooleanField(default=False)
    lot_id = serializers.CharField(max_length=50)
    requirements = serializers.CharField(required=False, default='', allow_blank=True)
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
