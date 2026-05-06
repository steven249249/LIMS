import uuid
from django.db import models


class Experiment(models.Model):
    """A type of experiment that can be performed.

    One experiment is performed at exactly one lab (Department). The
    requester picks the experiment and the order is automatically routed to
    that lab — they never pick a lab or a machine themselves.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    remark = models.TextField(blank=True, default='')
    department = models.ForeignKey(
        'users.Department',
        on_delete=models.PROTECT,
        related_name='experiments',
        null=True,
        blank=True,
        help_text='The lab that performs this experiment.',
    )

    class Meta:
        db_table = 'experiment'

    def __str__(self):
        return self.name


class EquipmentType(models.Model):
    """Category / type of equipment (e.g. SEM, AFM)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'equipment_type'

    def __str__(self):
        return self.name


class Equipment(models.Model):
    """A specific physical equipment unit."""

    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        OCCUPIED = 'occupied', 'Occupied'
        PENDING = 'pending', 'Pending'
        MAINTENANCE = 'maintenance', 'Maintenance'
        INACTIVE = 'inactive', 'Inactive'


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipment_type = models.ForeignKey(
        EquipmentType,
        on_delete=models.CASCADE,
        related_name='equipments',
    )
    department = models.ForeignKey(
        'users.Department',
        on_delete=models.CASCADE,
        related_name='equipments',
        null=True, blank=True
    )
    code = models.CharField(max_length=50, unique=True, help_text='Unique asset code')

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.AVAILABLE)

    class Meta:
        db_table = 'equipment'

    def __str__(self):
        return f'{self.equipment_type.name} – {self.code}'


class ExperimentRequiredEquipment(models.Model):
    """M:N bridge – how many units of each equipment type an experiment needs."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name='required_equipments',
    )
    equipment_type = models.ForeignKey(
        EquipmentType,
        on_delete=models.CASCADE,
        related_name='experiment_requirements',
    )
    quantity = models.PositiveIntegerField(default=1)
    step_order = models.PositiveIntegerField(default=1, help_text='Order of this step in the experiment relay')


    class Meta:
        db_table = 'experiment_required_equipment'
        unique_together = ('experiment', 'equipment_type')

    def __str__(self):
        return f'{self.experiment.name} needs {self.quantity}x {self.equipment_type.name}'
