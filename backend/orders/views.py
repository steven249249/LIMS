"""
orders/views.py
"""
from rest_framework import generics, permissions, status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from equipments.models import Experiment
from .models import Order, OrderStage
from .serializers import (
    OrderListSerializer,
    OrderDetailSerializer,
    OrderCreateSerializer,
    OrderReviewSerializer,
    OrderStageSerializer,
)

from . import services


# ── Permission helpers ─────────────────────────────────────────────────────

class IsLabManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ('lab_manager', 'superuser')


class IsLabMember(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ('lab_member', 'lab_manager', 'superuser')


class IsRegularEmployee(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ('regular_employee', 'superuser')



# ── Views ──────────────────────────────────────────────────────────────────

class OrderListView(generics.ListAPIView):
    """
    GET /api/orders/
    Requester sees own orders, Manager sees department orders, Superuser sees all.
    """
    serializer_class = OrderListSerializer

    def get_queryset(self):
        """Visibility scoping per role:

        * superuser          — every order
        * lab_manager        — orders whose department is the manager's lab
        * lab_member         — orders that have at least one stage assigned to them
        * regular_employee   — only orders they themselves submitted
        """
        user = self.request.user
        qs = Order.objects.select_related('user', 'experiment', 'department', 'assignee')

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        if user.role == 'superuser':
            return qs
        if user.role == 'lab_manager':
            return qs.filter(department=user.department)
        if user.role == 'lab_member':
            return qs.filter(stages__assignee=user).distinct()
        # regular_employee
        return qs.filter(user=user)


class OrderCreateView(APIView):
    """POST /api/orders/create/ – Requester submits a new order (no schedule)."""
    permission_classes = [IsRegularEmployee]

    def post(self, request):
        ser = OrderCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        experiment = get_object_or_404(Experiment, id=ser.validated_data['experiment'])
        order = services.create_order(
            user=request.user,
            experiment=experiment,
            is_urgent=ser.validated_data.get('is_urgent', False),
            lot_id=ser.validated_data.get('lot_id', ''),
            remark=ser.validated_data.get('remark', ''),
        )
        return Response(
            OrderDetailSerializer(order).data,
            status=http_status.HTTP_201_CREATED,
        )


class OrderDetailView(generics.RetrieveAPIView):
    """GET /api/orders/<uuid:pk>/

    Returns 404 instead of 403 when the requester lacks visibility — mirrors
    the row-level filtering of the list endpoint and avoids leaking the
    existence of orders outside the caller's scope.
    """
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = (
            Order.objects
            .select_related('user', 'experiment', 'department', 'department__fab', 'assignee')
            .prefetch_related(
                'stages__department',
                'stages__equipment_type',
                'stages__equipment',
                'stages__assignee',
            )
        )
        if user.role == 'superuser':
            return qs
        if user.role == 'lab_manager':
            return qs.filter(department=user.department)
        if user.role == 'lab_member':
            return qs.filter(stages__assignee=user).distinct()
        return qs.filter(user=user)


class OrderReviewView(generics.UpdateAPIView):
    """
    PATCH /api/v1/orders/stages/<uuid:pk>/review/
    { "action": "approve", "schedule_start": "...", "schedule_end": "...", "assignee": "..." }
    """
    queryset = OrderStage.objects.all()
    serializer_class = OrderStageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        stage = self.get_object()
        action = request.data.get('action')

        if action == 'approve':
            from .services import approve_and_schedule_stage
            approve_and_schedule_stage(
                stage,
                schedule_start=request.data.get('schedule_start'),
                schedule_end=request.data.get('schedule_end'),
                assignee=request.data.get('assignee'),
            )
            return Response({'detail': f'Stage {stage.step_order} approved.'})

        if action == 'reject':
            from .services import reject_order
            reject_order(stage.order, rejection_reason=request.data.get('rejection_reason'))
            return Response({'detail': 'Order rejected.'})

        if action == 'reassign':
            return self._reassign(stage, request)

        return Response({'detail': 'Invalid action.'}, status=400)

    @staticmethod
    def _reassign(stage, request):
        from django.utils import timezone
        from django.utils.dateparse import parse_datetime
        from django.utils.timezone import is_aware, make_aware

        from scheduling.models import EquipmentBooking

        assignee_id = request.data.get('assignee', stage.assignee_id)
        new_start = request.data.get('schedule_start') or stage.schedule_start
        new_end = request.data.get('schedule_end') or stage.schedule_end

        d_start = parse_datetime(new_start) if isinstance(new_start, str) else new_start
        d_end = parse_datetime(new_end) if isinstance(new_end, str) else new_end

        if d_start and d_end:
            if not is_aware(d_start):
                d_start = make_aware(d_start)
            if not is_aware(d_end):
                d_end = make_aware(d_end)
            if d_start >= d_end:
                return Response({'detail': 'End time must be after start time.'}, status=400)
            if d_start < timezone.now():
                return Response({'detail': 'Start time cannot be in the past.'}, status=400)

        stage.assignee_id = assignee_id
        stage.schedule_start = new_start
        stage.schedule_end = new_end
        stage.save()

        EquipmentBooking.objects.filter(stage=stage).update(
            started_at=new_start, ended_at=new_end,
        )
        return Response({'detail': 'Task reassigned/rescheduled.'})


class OrderStageListView(generics.ListAPIView):
    """GET /api/v1/orders/stages/?status=waiting"""
    serializer_class = OrderStageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Visibility scoping for stages:

        * superuser        — every stage
        * lab_manager      — stages whose department is the manager's lab
                             (so they see who is assigned to what in their lab)
        * lab_member       — only stages assigned to them
        * regular_employee — only stages on their own orders
        """
        user = self.request.user
        qs = (
            OrderStage.objects
            .select_related(
                'order',
                'order__user',
                'order__experiment',
                'department',
                'equipment_type',
                'equipment',
                'assignee',
            )
            .all()
        )

        status = self.request.query_params.get('status')
        if status:
            qs = qs.filter(status=status)

        if user.role == 'superuser':
            return qs
        if user.role == 'lab_manager' and user.department:
            return qs.filter(department=user.department)
        if user.role == 'lab_member':
            return qs.filter(assignee=user)
        return qs.filter(order__user=user)



class OrderCompleteView(generics.UpdateAPIView):
    """Member completes a stage."""
    queryset = OrderStage.objects.all()
    serializer_class = OrderStageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        stage = self.get_object()
        # Only the assignee or any manager in the dept can complete
        if stage.assignee != request.user and request.user.role != 'lab_manager':
            return Response({'detail': 'You are not assigned to this stage.'}, status=403)

        from .services import complete_stage
        complete_stage(stage)
        return Response({'detail': f'Stage {stage.step_order} completed.'})
