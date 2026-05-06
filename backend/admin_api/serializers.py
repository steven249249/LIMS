"""Admin-only serializers exposing every editable field of each domain model.

These are intentionally separate from each app's user-facing serializers so the
superuser console can see and modify fields normally hidden from regular users
(``status``, ``role``, raw status transitions, etc.).
"""
from rest_framework import serializers

from equipments.models import (
    Equipment,
    EquipmentType,
    Experiment,
    ExperimentRequiredEquipment,
)
from orders.models import Order, OrderStage
from scheduling.models import EquipmentBooking
from users.models import FAB, Department, User, WaferLot


class FABSerializer(serializers.ModelSerializer):
    department_count = serializers.IntegerField(source='departments.count', read_only=True)

    class Meta:
        model = FAB
        fields = ('id', 'fab_name', 'department_count')


class DepartmentSerializer(serializers.ModelSerializer):
    fab_name = serializers.CharField(source='fab.fab_name', read_only=True)
    member_count = serializers.IntegerField(source='members.count', read_only=True)

    class Meta:
        model = Department
        fields = ('id', 'fab', 'fab_name', 'name', 'member_count')


class WaferLotSerializer(serializers.ModelSerializer):
    fab_name = serializers.CharField(source='fab.fab_name', read_only=True)

    class Meta:
        model = WaferLot
        # ``code`` is the primary key — there is no separate id column.
        fields = ('code', 'fab', 'fab_name', 'notes', 'created_at')
        read_only_fields = ('created_at',)


class UserSerializer(serializers.ModelSerializer):
    """User serializer that hashes ``password`` on create/update.

    Password is write-only and never returned in responses; clients must not
    expect a password field on read.
    """

    password = serializers.CharField(write_only=True, required=False, allow_blank=False, min_length=8)
    department_name = serializers.CharField(source='department.name', read_only=True)
    fab_name = serializers.CharField(source='department.fab.fab_name', read_only=True, default=None)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
            'status',
            'department',
            'department_name',
            'fab_name',
            'is_active',
            'is_staff',
            'is_superuser',
            'joined_at',
            'last_login',
            'password',
        )
        read_only_fields = ('id', 'joined_at', 'last_login')

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class ExperimentSerializer(serializers.ModelSerializer):
    requirement_count = serializers.IntegerField(source='required_equipments.count', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Experiment
        fields = (
            'id', 'name', 'remark',
            'department', 'department_name',
            'requirement_count',
        )


class EquipmentTypeSerializer(serializers.ModelSerializer):
    equipment_count = serializers.IntegerField(source='equipments.count', read_only=True)

    class Meta:
        model = EquipmentType
        fields = ('id', 'name', 'equipment_count')


class EquipmentSerializer(serializers.ModelSerializer):
    """Admin equipment serializer.

    ``department`` is required at the API layer even though the underlying
    model column is nullable: the superuser console exists primarily to
    *allocate equipment to a lab*, so an unassigned record would defeat the
    purpose. Existing legacy rows with ``department=None`` keep working on
    read; they just need a department before the next save round-trips.
    """

    equipment_type_name = serializers.CharField(source='equipment_type.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        required=True,
        allow_null=False,
        error_messages={'null': 'Equipment must be assigned to a lab.',
                        'required': 'Equipment must be assigned to a lab.'},
    )

    class Meta:
        model = Equipment
        fields = (
            'id', 'code', 'status',
            'equipment_type', 'equipment_type_name',
            'department', 'department_name',
        )


class ExperimentRequiredEquipmentSerializer(serializers.ModelSerializer):
    experiment_name = serializers.CharField(source='experiment.name', read_only=True)
    equipment_type_name = serializers.CharField(source='equipment_type.name', read_only=True)

    class Meta:
        model = ExperimentRequiredEquipment
        fields = (
            'id', 'experiment', 'experiment_name',
            'equipment_type', 'equipment_type_name',
            'quantity', 'step_order',
        )


class OrderSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    experiment_name = serializers.CharField(source='experiment.name', read_only=True)
    requester_username = serializers.CharField(source='user.username', read_only=True)
    assignee_username = serializers.CharField(source='assignee.username', read_only=True, default=None)
    stage_count = serializers.IntegerField(source='stages.count', read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'order_no',
            'department', 'department_name',
            'user', 'requester_username',
            'experiment', 'experiment_name',
            'lot_id',
            'assignee', 'assignee_username',
            'status', 'is_urgent',
            'schedule_start', 'schedule_end',
            'rejection_reason', 'remark',
            'created_at', 'updated_at', 'ended_at',
            'stage_count',
        )
        read_only_fields = ('id', 'order_no', 'created_at', 'updated_at')


class OrderStageSerializer(serializers.ModelSerializer):
    order_no = serializers.CharField(source='order.order_no', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    equipment_type_name = serializers.CharField(source='equipment_type.name', read_only=True)
    equipment_code = serializers.CharField(source='equipment.code', read_only=True, default=None)
    assignee_username = serializers.CharField(source='assignee.username', read_only=True, default=None)

    class Meta:
        model = OrderStage
        fields = (
            'id', 'order', 'order_no', 'step_order',
            'department', 'department_name',
            'equipment_type', 'equipment_type_name',
            'assignee', 'assignee_username',
            'equipment', 'equipment_code',
            'status',
            'schedule_start', 'schedule_end', 'completed_at',
        )
        read_only_fields = ('id',)


class EquipmentBookingSerializer(serializers.ModelSerializer):
    order_no = serializers.CharField(source='order.order_no', read_only=True)
    equipment_code = serializers.CharField(source='equipment.code', read_only=True)

    class Meta:
        model = EquipmentBooking
        fields = (
            'id',
            'order', 'order_no',
            'equipment', 'equipment_code',
            'stage',
            'started_at', 'ended_at',
        )

    def validate(self, attrs):
        start = attrs.get('started_at') or getattr(self.instance, 'started_at', None)
        end = attrs.get('ended_at') or getattr(self.instance, 'ended_at', None)
        if start and end and start >= end:
            raise serializers.ValidationError({'ended_at': 'ended_at must be after started_at.'})
        return attrs
