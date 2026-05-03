"""Superuser-only ModelViewSets exposing CRUD over every domain table.

Each viewset reuses an admin-specific serializer (see :mod:`admin_api.serializers`)
and is gated by :class:`monitoring.permissions.IsSystemSuperuser`.
"""
from rest_framework import filters, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from equipments.models import (
    Equipment,
    EquipmentType,
    Experiment,
    ExperimentRequiredEquipment,
)
from monitoring.permissions import IsSystemSuperuser
from orders.models import Order, OrderStage
from scheduling.models import EquipmentBooking
from users.models import FAB, Department, User

from . import serializers as admin_serializers


class AdminBaseViewSet(viewsets.ModelViewSet):
    """Shared defaults for every admin viewset: superuser auth + search/order."""

    permission_classes = (IsSystemSuperuser,)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)


class FABViewSet(AdminBaseViewSet):
    queryset = FAB.objects.all().order_by('fab_name')
    serializer_class = admin_serializers.FABSerializer
    search_fields = ('fab_name',)
    ordering_fields = ('fab_name',)


class DepartmentViewSet(AdminBaseViewSet):
    queryset = Department.objects.select_related('fab').order_by('fab__fab_name', 'name')
    serializer_class = admin_serializers.DepartmentSerializer
    search_fields = ('name', 'fab__fab_name')
    ordering_fields = ('name', 'fab__fab_name')


class UserViewSet(AdminBaseViewSet):
    """Manages user accounts. Includes safety rails on destructive operations."""

    queryset = User.objects.select_related('department', 'department__fab').order_by('username')
    serializer_class = admin_serializers.UserSerializer
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering_fields = ('username', 'role', 'status', 'joined_at')

    def perform_destroy(self, instance):
        if instance == self.request.user:
            raise PermissionDenied('You cannot delete your own account.')
        if instance.role == User.Role.SUPERUSER:
            remaining = User.objects.filter(role=User.Role.SUPERUSER).exclude(pk=instance.pk).count()
            if remaining == 0:
                raise ValidationError('Cannot delete the last remaining superuser.')
        instance.delete()


class ExperimentViewSet(AdminBaseViewSet):
    queryset = Experiment.objects.all().order_by('name')
    serializer_class = admin_serializers.ExperimentSerializer
    search_fields = ('name', 'remark')
    ordering_fields = ('name',)


class EquipmentTypeViewSet(AdminBaseViewSet):
    queryset = EquipmentType.objects.all().order_by('name')
    serializer_class = admin_serializers.EquipmentTypeSerializer
    search_fields = ('name',)
    ordering_fields = ('name',)


class EquipmentViewSet(AdminBaseViewSet):
    queryset = Equipment.objects.select_related('equipment_type', 'department').order_by('code')
    serializer_class = admin_serializers.EquipmentSerializer
    search_fields = ('code', 'equipment_type__name')
    ordering_fields = ('code', 'status')


class ExperimentRequiredEquipmentViewSet(AdminBaseViewSet):
    queryset = (
        ExperimentRequiredEquipment.objects
        .select_related('experiment', 'equipment_type')
        .order_by('experiment__name', 'step_order')
    )
    serializer_class = admin_serializers.ExperimentRequiredEquipmentSerializer
    search_fields = ('experiment__name', 'equipment_type__name')
    ordering_fields = ('step_order',)


class OrderViewSet(AdminBaseViewSet):
    queryset = (
        Order.objects
        .select_related('department', 'experiment', 'user', 'assignee')
        .order_by('-created_at')
    )
    serializer_class = admin_serializers.OrderSerializer
    search_fields = ('order_no', 'lot_id', 'user__username', 'experiment__name')
    ordering_fields = ('created_at', 'status', 'is_urgent')


class OrderStageViewSet(AdminBaseViewSet):
    queryset = (
        OrderStage.objects
        .select_related('order', 'department', 'equipment_type', 'equipment', 'assignee')
        .order_by('order__order_no', 'step_order')
    )
    serializer_class = admin_serializers.OrderStageSerializer
    search_fields = ('order__order_no',)
    ordering_fields = ('step_order', 'status')


class EquipmentBookingViewSet(AdminBaseViewSet):
    queryset = (
        EquipmentBooking.objects
        .select_related('order', 'equipment', 'stage')
        .order_by('-started_at')
    )
    serializer_class = admin_serializers.EquipmentBookingSerializer
    search_fields = ('order__order_no', 'equipment__code')
    ordering_fields = ('started_at', 'ended_at')
