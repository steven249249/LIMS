import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class FAB(models.Model):
    """Factory / Fab site."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fab_name = models.CharField(max_length=20, unique=True)

    class Meta:
        db_table = 'fab'
        verbose_name = 'FAB'
        verbose_name_plural = 'FABs'

    def __str__(self):
        return self.fab_name


class Department(models.Model):
    """Department within a FAB."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fab = models.ForeignKey(FAB, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'department'
        unique_together = ('fab', 'name')

    def __str__(self):
        return f'{self.fab.fab_name} - {self.name}'


class WaferLot(models.Model):
    """A registered wafer lot. The lot code is its primary key (globally
    unique) — every Order references it via FK rather than holding a
    free-text lot_id, so traceability is enforced at the database level.

    Admins maintain the master list via the Admin Console; the submission
    UI populates the dropdown from this table so requesters can never
    mistype a code.
    """
    code = models.CharField(max_length=50, primary_key=True)
    fab = models.ForeignKey(FAB, on_delete=models.CASCADE, related_name='wafer_lots')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wafer_lot'
        ordering = ['code']

    def __str__(self):
        return self.code


class User(AbstractUser):
    """Custom user model with UUID, department FK, role, and status."""

    class Role(models.TextChoices):
        LAB_MEMBER = 'lab_member', 'Lab Member'
        LAB_MANAGER = 'lab_manager', 'Lab Manager'
        REGULAR_EMPLOYEE = 'regular_employee', 'Regular Employee'
        SUPERUSER = 'superuser', 'Superuser'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        SUSPENDED = 'suspended', 'Suspended'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.REGULAR_EMPLOYEE)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user'

    @property
    def name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username

    @property
    def department_name(self):
        return self.department.name if self.department else None

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'
