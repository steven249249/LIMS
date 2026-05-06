"""factory_boy factories for every domain model.

Factories produce *minimal valid* objects so each test can override only the
fields under inspection. Sub-factories are used (rather than ``RelatedFactory``)
to keep object graphs explicit.
"""
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model

from equipments.models import (
    Equipment,
    EquipmentType,
    Experiment,
    ExperimentRequiredEquipment,
)
from orders.models import Order, OrderStage
from scheduling.models import EquipmentBooking
from users.models import FAB, Department, WaferLot

User = get_user_model()


# ── Users ──────────────────────────────────────────────────────────────────

class FABFactory(DjangoModelFactory):
    class Meta:
        model = FAB
        django_get_or_create = ('fab_name',)

    fab_name = factory.Sequence(lambda n: f'FAB-{n:03d}')


class DepartmentFactory(DjangoModelFactory):
    class Meta:
        model = Department
        django_get_or_create = ('fab', 'name')

    fab = factory.SubFactory(FABFactory)
    name = factory.Sequence(lambda n: f'Department-{n:03d}')


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: f'user-{n:04d}')
    email = factory.LazyAttribute(lambda o: f'{o.username}@lims.test')
    first_name = 'Test'
    last_name = 'User'
    role = User.Role.REGULAR_EMPLOYEE
    status = User.Status.ACTIVE
    department = factory.SubFactory(DepartmentFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop('password', 'TestPass2026!')
        instance = model_class(*args, **kwargs)
        instance.set_password(password)
        instance.save()
        return instance


class SuperUserFactory(UserFactory):
    role = User.Role.SUPERUSER
    is_staff = True
    is_superuser = True
    username = factory.Sequence(lambda n: f'superuser-{n:04d}')


class LabManagerFactory(UserFactory):
    role = User.Role.LAB_MANAGER
    username = factory.Sequence(lambda n: f'manager-{n:04d}')


class LabMemberFactory(UserFactory):
    role = User.Role.LAB_MEMBER
    username = factory.Sequence(lambda n: f'member-{n:04d}')


# ── Equipment ──────────────────────────────────────────────────────────────

class EquipmentTypeFactory(DjangoModelFactory):
    class Meta:
        model = EquipmentType
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'EquipType-{n:03d}')


class EquipmentFactory(DjangoModelFactory):
    class Meta:
        model = Equipment
        django_get_or_create = ('code',)

    equipment_type = factory.SubFactory(EquipmentTypeFactory)
    department = factory.SubFactory(DepartmentFactory)
    code = factory.Sequence(lambda n: f'EQ-{n:05d}')
    status = Equipment.Status.AVAILABLE


class ExperimentFactory(DjangoModelFactory):
    class Meta:
        model = Experiment
        django_get_or_create = ('name',)

    name = factory.Sequence(lambda n: f'Experiment-{n:03d}')
    remark = ''

    @classmethod
    def with_requirement(cls, equipment_type=None, quantity=1, step_order=1, **kwargs):
        """Build an Experiment plus a single ExperimentRequiredEquipment.

        Common in tests because a bare Experiment with no requirement cannot
        drive the relay flow.
        """
        exp = cls(**kwargs)
        eq_type = equipment_type or EquipmentTypeFactory()
        ExperimentRequiredEquipmentFactory(
            experiment=exp,
            equipment_type=eq_type,
            quantity=quantity,
            step_order=step_order,
        )
        return exp


class ExperimentRequiredEquipmentFactory(DjangoModelFactory):
    class Meta:
        model = ExperimentRequiredEquipment

    experiment = factory.SubFactory(ExperimentFactory)
    equipment_type = factory.SubFactory(EquipmentTypeFactory)
    quantity = 1
    step_order = 1


# ── Orders ─────────────────────────────────────────────────────────────────

class WaferLotFactory(DjangoModelFactory):
    class Meta:
        model = WaferLot
        django_get_or_create = ('code',)

    code = factory.Sequence(lambda n: f'LOT-{n:05d}')
    fab = factory.SubFactory(FABFactory)
    notes = ''


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    department = factory.SubFactory(DepartmentFactory)
    experiment = factory.SubFactory(ExperimentFactory)
    lot = factory.SubFactory(WaferLotFactory)
    is_urgent = False
    status = Order.Status.WAITING


class OrderStageFactory(DjangoModelFactory):
    class Meta:
        model = OrderStage

    order = factory.SubFactory(OrderFactory)
    step_order = 1
    department = factory.SubFactory(DepartmentFactory)
    equipment_type = factory.SubFactory(EquipmentTypeFactory)
    status = OrderStage.Status.PENDING


# ── Scheduling ─────────────────────────────────────────────────────────────

class EquipmentBookingFactory(DjangoModelFactory):
    class Meta:
        model = EquipmentBooking

    order = factory.SubFactory(OrderFactory)
    equipment = factory.SubFactory(EquipmentFactory)
    started_at = factory.Faker('future_datetime', tzinfo=None)
    ended_at = factory.LazyAttribute(
        lambda o: o.started_at + __import__('datetime').timedelta(hours=2),
    )
