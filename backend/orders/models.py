import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Order(models.Model):
    """A booking / service order submitted by a requester."""

    class Status(models.TextChoices):
        CREATED = 'created', 'Created'
        WAITING = 'waiting', 'Waiting'
        IN_PROGRESS = 'in_progress', 'In Progress'
        DONE = 'done', 'Done'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        'users.Department',
        on_delete=models.CASCADE,
        related_name='orders',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
    )
    order_no = models.CharField(max_length=30, unique=True, editable=False)
    # In the single-lab-per-order model the experiment is no longer the
    # driver of stage generation — each order is one lab visit. Keeping the
    # field as a nullable optional tag so legacy orders still resolve and
    # admins can group historical batches if they want.
    experiment = models.ForeignKey(
        'equipments.Experiment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )
    lot_id = models.CharField(max_length=50, blank=True, default='',
                              help_text='Wafer lot ID for tracking')
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        help_text='Lab member assigned to this order'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.WAITING,
    )
    is_urgent = models.BooleanField(default=False)
    schedule_start = models.DateTimeField(null=True, blank=True)
    schedule_end = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default='')
    requirements = models.TextField(
        blank=True,
        default='',
        help_text="What the requester needs from this experiment — surfaced "
                  "to the lab manager during scheduling.",
    )
    remark = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'order'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_no:
            self.order_no = self._generate_order_no()
        super().save(*args, **kwargs)

    def _generate_order_no(self):
        """Generate FAB-style order number: FAB12A-20260428-0001"""
        fab_name = 'LAB'
        if self.department and self.department.fab:
            fab_name = self.department.fab.fab_name

        today = timezone.localdate()
        date_str = today.strftime('%Y%m%d')
        prefix = f'{fab_name}-{date_str}-'

        # Find the max sequence for today's prefix
        last = (
            Order.objects
            .filter(order_no__startswith=prefix)
            .order_by('-order_no')
            .values_list('order_no', flat=True)
            .first()
        )
        if last:
            seq = int(last.split('-')[-1]) + 1
        else:
            seq = 1

        return f'{prefix}{seq:04d}'

    def __str__(self):
        return f'Order {self.order_no} – {self.get_status_display()}'


class OrderStage(models.Model):
    """Specific step in an order's relay pipeline."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'   # Waiting for prev stage
        WAITING = 'waiting', 'Waiting'   # Waiting for manager to assign
        IN_PROGRESS = 'in_progress', 'In Progress'
        DONE = 'done', 'Done'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='stages')
    step_order = models.PositiveIntegerField()
    department = models.ForeignKey('users.Department', on_delete=models.CASCADE)
    # equipment_type used to be required (one stage per equipment recipe).
    # Now experiments map to a single lab visit and don't pre-define machines,
    # so this is optional metadata — set if the manager wants the wafer on a
    # specific machine type, NULL otherwise.
    equipment_type = models.ForeignKey(
        'equipments.EquipmentType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    
    # Execution data (set by manager/member)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_stages'
    )
    equipment = models.ForeignKey(
        'equipments.Equipment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='stage_bookings'
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    
    schedule_start = models.DateTimeField(null=True, blank=True)
    schedule_end = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'order_stage'
        ordering = ['order', 'step_order']
        unique_together = ('order', 'step_order')

    def __str__(self):
        return f'{self.order.order_no} | Step {self.step_order} | {self.get_status_display()}'

