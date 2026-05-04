"""
orders/services.py
Business logic for order creation and state transitions.

State machine (SOP-aligned):
  Created → Waiting       (auto, after field validation)
  Waiting → In Progress   (manager approve + schedule)
  Waiting → Rejected      (manager reject)
  In Progress → Done      (lab member completes)
"""
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from orders.models import Order, OrderStage
from equipments.models import Equipment, ExperimentRequiredEquipment


User = get_user_model()


def _send_notification(user, message):
    """Simulates sending a notification (Email/Socket/Push).

    Accepts either a ``User`` instance or a primary-key string/UUID — callers
    in the relay flow sometimes pass the raw ``request.data['assignee']`` value
    that originated as a UUID string, so this helper resolves it into a User
    rather than relying on every caller to do so.
    """
    if not user:
        print(f"[SYSTEM] Notification skipped: No user provided. Message: {message}")
        return
    if not hasattr(user, 'username'):
        # PK string/UUID — try to resolve once. Bail silently if not found.
        try:
            user = User.objects.filter(pk=user).first()
        except (ValueError, TypeError):
            user = None
        if user is None:
            print(f"[SYSTEM] Notification skipped: user not found. Message: {message}")
            return
    print(f"[NOTIFICATION] User {user.username}: {message}")



# ── Allowed state transitions ──────────────────────────────────────────────
_TRANSITIONS = {
    Order.Status.CREATED:     [Order.Status.WAITING],
    Order.Status.WAITING:     [Order.Status.IN_PROGRESS, Order.Status.REJECTED],
    Order.Status.IN_PROGRESS: [Order.Status.DONE],
    Order.Status.DONE:        [],
    Order.Status.REJECTED:    [],
}


def _assert_transition(order: Order, target: str):
    allowed = _TRANSITIONS.get(order.status, [])
    if target not in allowed:
        raise ValidationError(
            f'Cannot transition from "{order.get_status_display()}" '
            f'to "{target}".'
        )


# ── Public API ─────────────────────────────────────────────────────────────

def create_order(*, user, experiment, is_urgent=False, lot_id='', remark='') -> Order:
    """
    Phase 1 – Requester creates order.
    System generates OrderStage records for each experiment step.
    Step 1 is set to WAITING, others to PENDING.
    """
    if not user.department:
        raise ValidationError("User must belong to a department to create orders.")

    order = Order.objects.create(
        user=user,
        department=user.department,
        experiment=experiment,
        is_urgent=is_urgent,
        lot_id=lot_id,
        remark=remark,
        status=Order.Status.IN_PROGRESS,
    )

    # Generate Stages based on Experiment Steps
    steps = ExperimentRequiredEquipment.objects.filter(experiment=experiment).order_by('step_order')
    
    stage_objs = []
    for step in steps:
        stage = OrderStage(
            order=order,
            step_order=step.step_order,
            department=step.equipment_type.equipments.first().department, # Auto-assign based on machine ownership
            equipment_type=step.equipment_type,
            status=OrderStage.Status.PENDING
        )
        stage_objs.append(stage)

    if stage_objs:
        stage_objs[0].status = OrderStage.Status.WAITING
        OrderStage.objects.bulk_create(stage_objs)
        # Notify first lab manager
        _send_notification(stage_objs[0].department.members.filter(role='lab_manager').first(), 
                           f"New task waiting in your lab for Order {order.order_no}")

    return order


def approve_and_schedule_stage(stage: OrderStage, *, schedule_start, schedule_end, assignee=None) -> OrderStage:
    """Manager approves a specific stage."""
    if stage.status != OrderStage.Status.WAITING:
        raise ValidationError(f"Cannot approve stage in {stage.status} status.")

    from django.utils.dateparse import parse_datetime
    from django.utils.timezone import is_aware, make_aware
    
    # Parse into datetime objects if they are strings
    if isinstance(schedule_start, str):
        schedule_start = parse_datetime(schedule_start)
    if isinstance(schedule_end, str):
        schedule_end = parse_datetime(schedule_end)

    if not schedule_start or not schedule_end:
        raise ValidationError('Invalid date format.')

    if not is_aware(schedule_start):
        schedule_start = make_aware(schedule_start)
    if not is_aware(schedule_end):
        schedule_end = make_aware(schedule_end)

    if schedule_start >= schedule_end:
        raise ValidationError('schedule_end must be after schedule_start.')

    now = timezone.now()
    if schedule_start < now:
        raise ValidationError('schedule_start cannot be in the past.')

    stage.schedule_start = schedule_start
    stage.schedule_end = schedule_end
    if assignee:
        stage.assignee_id = assignee  # Handle ID string or object
    stage.status = OrderStage.Status.IN_PROGRESS
    stage.save()

    # Allocate equipment for THIS stage
    from scheduling.services import allocate_equipments_for_stage
    allocate_equipments_for_stage(stage)

    # Notify assignee
    if assignee:
        _send_notification(assignee, f"You have been assigned to {stage.order.order_no} Step {stage.step_order}")

    return stage


def complete_stage(stage: OrderStage) -> OrderStage:
    """Member completes a specific stage. Triggers next stage relay."""
    if stage.status != OrderStage.Status.IN_PROGRESS:
        raise ValidationError("Only in-progress stages can be completed.")
    
    if stage.schedule_start and timezone.now() < stage.schedule_start:
        raise ValidationError("Cannot complete a task before its scheduled start time.")

    now = timezone.now()
    stage.status = OrderStage.Status.DONE
    stage.completed_at = now
    stage.schedule_end = now  # Release early in stage data
    stage.save()

    # Release equipment booking early
    from scheduling.models import EquipmentBooking
    booking = EquipmentBooking.objects.filter(stage=stage).first()
    if booking:
        booking.ended_at = now
        booking.save()

    # Release equipment status
    if stage.equipment:
        stage.equipment.status = Equipment.Status.AVAILABLE
        stage.equipment.save()

    # Relay Logic: Find next stage
    next_stage = OrderStage.objects.filter(
        order=stage.order, 
        step_order__gt=stage.step_order
    ).order_by('step_order').first()

    if next_stage:
        next_stage.status = OrderStage.Status.WAITING
        next_stage.save()
        # NOTIFICATION: Notify next manager
        mgr = next_stage.department.members.filter(role='lab_manager').first()
        if mgr:
            _send_notification(mgr, f"Sample relay: Order {stage.order.order_no} is now waiting in your lab.")
    else:
        # Last stage done -> Overall Order is Done
        order = stage.order
        order.status = Order.Status.DONE
        order.ended_at = timezone.now()
        order.save()
        _send_notification(order.user, f"Your multi-stage experiment {order.order_no} is fully COMPLETED.")

    return stage



def reject_order(order: Order, *, rejection_reason: str) -> Order:
    """Phase 2 – Lab Manager rejects."""
    _assert_transition(order, Order.Status.REJECTED)
    if not rejection_reason.strip():
        raise ValidationError('rejection_reason is required when rejecting.')
    order.status = Order.Status.REJECTED
    order.rejection_reason = rejection_reason
    order.save(update_fields=['status', 'rejection_reason', 'updated_at'])
    return order


def approve_and_schedule(order: Order, *, schedule_start, schedule_end, assignee=None) -> Order:
    """
    Phase 2-3: Lab Manager approves → picks schedule time →
    system checks conflicts & allocates equipment → status = In Progress.
    Also sets booked equipment status to Occupied and notifies Lab Members.
    """
    _assert_transition(order, Order.Status.IN_PROGRESS)

    if schedule_start >= schedule_end:
        raise ValidationError('schedule_start must be before schedule_end.')

    order.schedule_start = schedule_start
    order.schedule_end = schedule_end
    order.assignee = assignee
    order.save(update_fields=['schedule_start', 'schedule_end', 'assignee', 'updated_at'])

    # Allocate equipment (conflict check + booking creation)
    from scheduling.services import allocate_equipments
    bookings = allocate_equipments(order)

    # Set booked equipment status to Occupied
    booked_eq_ids = [b.equipment_id for b in bookings]
    Equipment.objects.filter(id__in=booked_eq_ids).update(status=Equipment.Status.OCCUPIED)

    order.status = Order.Status.IN_PROGRESS
    order.save(update_fields=['status', 'updated_at'])

    # NOTIFICATION: Notify lab members in the same department
    members_to_notify = User.objects.filter(
        department=order.department,
        role__in=[User.Role.LAB_MEMBER, User.Role.LAB_MANAGER]
    )
    if assignee:
        _send_notification(assignee, f"You have been assigned to Order {order.order_no}.")
    
    msg = f"Experiment for Order {order.order_no} ({order.experiment.name}) is starting."
    for m in members_to_notify:
        if m != assignee:  # Don't notify twice
            _send_notification(m, msg)

    return order


def complete_order(order: Order) -> Order:
    """Phase 4 – Lab Member marks experiment as done.
    Resets booked equipment to Available.
    """
    _assert_transition(order, Order.Status.DONE)
    order.status = Order.Status.DONE
    order.ended_at = timezone.now()
    order.save(update_fields=['status', 'ended_at', 'updated_at'])

    # Reset equipment status to Available
    from scheduling.models import EquipmentBooking
    booked_eq_ids = list(
        EquipmentBooking.objects.filter(order=order).values_list('equipment_id', flat=True)
    )
    if booked_eq_ids:
        Equipment.objects.filter(id__in=booked_eq_ids).update(status=Equipment.Status.AVAILABLE)

    # NOTIFICATION: Notify requester
    _send_notification(order.user, f"Your experiment for Order {order.order_no} is completed.")

    return order
