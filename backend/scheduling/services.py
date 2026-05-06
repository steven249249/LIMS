"""
scheduling/services.py
Core scheduling engine – equipment allocation with double-booking prevention.

Key technique:
  1. Read experiment requirements (Experiment_Required_Equipment).
  2. For each equipment type, find available units that have NO
     overlapping bookings in the requested time window.
  3. Lock those rows with `select_for_update()` inside `transaction.atomic()`
     to prevent concurrent allocations.
  4. After locking, perform a second conflict check (double-check pattern).
  5. Create EquipmentBooking rows.
"""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from equipments.models import Equipment, ExperimentRequiredEquipment
from scheduling.models import EquipmentBooking


def _get_conflicting_equipment_ids(start, end):
    """Return a set of equipment IDs that have a booking overlapping [start, end)."""
    return set(
        EquipmentBooking.objects.filter(
            started_at__lt=end,
            ended_at__gt=start,
        ).values_list('equipment_id', flat=True)
    )


def check_availability(experiment_id, start, end):
    """
    Read-only check: returns a dict mapping each required EquipmentType
    to the list of available Equipment objects.
    Raises ValidationError if any type is short on quantity.
    """
    requirements = ExperimentRequiredEquipment.objects.filter(
        experiment_id=experiment_id
    ).select_related('equipment_type')

    if not requirements.exists():
        raise ValidationError('This experiment has no equipment requirements configured.')

    conflicting_ids = _get_conflicting_equipment_ids(start, end)
    allocation_map = {}  # {requirement: [Equipment, ...]}

    for req in requirements:
        available = list(
            Equipment.objects.filter(
                equipment_type_id=req.equipment_type_id,
                status=Equipment.Status.AVAILABLE,
            ).exclude(
                id__in=conflicting_ids,
            )[:req.quantity]
        )
        if len(available) < req.quantity:
            raise ValidationError(
                f'Not enough "{req.equipment_type.name}" available: '
                f'need {req.quantity}, found {len(available)}. '
                f'Please choose a different time window.'
            )
        allocation_map[req] = available

    return allocation_map


def allocate_equipments(order):
    """
    Transactional allocation with pessimistic locking.
    Called by orders.services.approve_and_schedule().
    """
    start = order.schedule_start
    end = order.schedule_end

    # ── 1. Optimistic pre-check (no lock) ──────────────────────────────
    allocation_map = check_availability(order.experiment_id, start, end)

    # Flatten all candidate equipment IDs
    candidate_ids = [eq.id for eqs in allocation_map.values() for eq in eqs]

    # ── 2. Pessimistic lock + double-check ─────────────────────────────
    with transaction.atomic():
        # Lock the candidate rows (row-level exclusive lock)
        locked_eqs = {
            eq.id: eq
            for eq in Equipment.objects.select_for_update().filter(id__in=candidate_ids)
        }

        # Double-check: make sure none of these got booked in the meantime
        newly_conflicting = set(
            EquipmentBooking.objects.filter(
                equipment_id__in=candidate_ids,
                started_at__lt=end,
                ended_at__gt=start,
            ).values_list('equipment_id', flat=True)
        )

        if newly_conflicting:
            raise ValidationError(
                'Schedule conflict detected during allocation. '
                'Another booking was created concurrently. Please retry.'
            )

        # ── 3. Create bookings ─────────────────────────────────────────
        bookings = []
        for req, equipments in allocation_map.items():
            for eq in equipments:
                bookings.append(EquipmentBooking(
                    order=order,
                    equipment=eq,
                    started_at=start,
                    ended_at=end,
                ))
        EquipmentBooking.objects.bulk_create(bookings)

    return bookings

def allocate_equipments_for_stage(stage, equipment_id=None):
    """
    Allocates a single equipment unit to the stage.

    Experiments no longer pre-define equipment requirements, so the stage
    has no fixed ``equipment_type``. The manager either:
      * picks a specific unit (``equipment_id``) — we validate it lives in
        the stage's lab and is free in the chosen window, or
      * leaves it blank — we no-op and the stage runs without a pinned
        machine. (Returns ``None`` in that case.)
    """
    start = stage.schedule_start
    end = stage.schedule_end

    if not equipment_id:
        # No machine pinning requested — that is now a valid path.
        return None

    conflicting_ids = _get_conflicting_equipment_ids(start, end)
    try:
        chosen_eq = Equipment.objects.get(id=equipment_id)
    except Equipment.DoesNotExist:
        raise ValidationError('Selected machine does not exist.')
    if chosen_eq.department_id != stage.department_id:
        raise ValidationError('Selected machine belongs to a different lab.')
    if chosen_eq.status != Equipment.Status.AVAILABLE:
        raise ValidationError('Selected machine is not available.')
    if chosen_eq.id in conflicting_ids:
        raise ValidationError(
            'Selected machine is already booked in this time window.'
        )

    # 2. Pessimistic lock + Double-check
    with transaction.atomic():
        # Re-fetch with lock
        eq = Equipment.objects.select_for_update().get(id=chosen_eq.id)
        
        # Check conflict again
        is_taken = EquipmentBooking.objects.filter(
            equipment_id=eq.id,
            started_at__lt=end,
            ended_at__gt=start,
        ).exists()
        
        if is_taken:
            raise ValidationError('This specific machine was just booked. Please retry.')

        # 3. Cleanup: Delete any existing bookings for this stage to prevent duplicates
        EquipmentBooking.objects.filter(stage=stage).delete()

        # 4. Create booking & Associate with stage
        booking = EquipmentBooking.objects.create(
            order=stage.order,
            stage=stage,
            equipment=eq,
            started_at=start,
            ended_at=end,
        )
        
        # Link equipment to stage and set to Occupied
        stage.equipment = eq
        stage.save(update_fields=['equipment'])
        
        eq.status = Equipment.Status.OCCUPIED
        eq.save(update_fields=['status'])

    return booking
