"""Unit tests for the order/stage state-machine services.

Showcases the five test-double styles:
  * Fake     — full Django ORM via factory_boy
  * Stub     — pre-baked fixture rows that supply method input
  * Mock     — mocker.patch() to replace scheduling allocation
  * Spy      — mocker.spy() to verify _send_notification was invoked
  * Time fake — freeze_time() to make schedule guards deterministic
"""
from datetime import timedelta

import pytest
from freezegun import freeze_time
from rest_framework.exceptions import ValidationError

from orders import services
from orders.models import Order, OrderStage
from tests.factories import (
    EquipmentFactory,
    EquipmentTypeFactory,
    ExperimentFactory,
    OrderFactory,
    OrderStageFactory,
    UserFactory,
)


@pytest.mark.unit
class TestCreateOrder:
    def test_user_without_department_is_rejected(self, db, equipment_type):
        # Arrange — user with no department
        user = UserFactory(department=None)
        # Act / Assert
        with pytest.raises(ValidationError, match='department'):
            services.create_order(user=user, equipment_type=equipment_type)

    def test_rejected_when_no_lab_owns_the_equipment_type(self, db, employee, equipment_type):
        # Arrange — no Equipment registered for this type anywhere
        # Act / Assert — single-lab-per-order needs a deterministic target
        with pytest.raises(ValidationError, match='No lab has any'):
            services.create_order(user=employee, equipment_type=equipment_type)

    def test_creates_order_and_single_stage_in_waiting(self, db, employee, equipment_type):
        # Arrange — at least one unit exists at a lab so target_department can
        # be resolved automatically.
        EquipmentFactory(equipment_type=equipment_type, department=employee.department)
        # Act
        order = services.create_order(
            user=employee, equipment_type=equipment_type, lot_id='L-001',
        )
        # Assert — order itself is WAITING; exactly one stage is created and
        # it sits in WAITING for the lab manager to schedule.
        assert order.status == Order.Status.WAITING
        assert order.lot_id == 'L-001'
        stages = list(order.stages.order_by('step_order'))
        assert len(stages) == 1
        assert stages[0].status == OrderStage.Status.WAITING
        assert stages[0].equipment_type == equipment_type

    def test_target_department_can_be_passed_explicitly(self, db, employee, equipment_type):
        # Arrange — owning lab for the equipment differs from the requester's
        # own department; explicit target_department should win.
        from tests.factories import DepartmentFactory
        target = DepartmentFactory(name='Lab-Target')
        EquipmentFactory(equipment_type=equipment_type, department=target)
        # Act
        order = services.create_order(
            user=employee, equipment_type=equipment_type, target_department=target,
        )
        # Assert
        stage = order.stages.first()
        assert stage.department_id == target.id

    def test_first_manager_is_notified(self, db, employee, equipment_type, mocker):
        # Arrange — Spy on _send_notification; the lab manager belongs to the
        # owning department of the equipment unit.
        notify_spy = mocker.spy(services, '_send_notification')
        EquipmentFactory(equipment_type=equipment_type, department=employee.department)
        UserFactory(department=employee.department, role='lab_manager')
        # Act
        services.create_order(user=employee, equipment_type=equipment_type)
        # Assert — exactly one notification (to the target lab manager)
        assert notify_spy.call_count == 1

    def test_optional_experiment_is_persisted_as_tag(self, db, employee, equipment_type):
        # Arrange — experiment is now a free-form grouping tag, optional
        EquipmentFactory(equipment_type=equipment_type, department=employee.department)
        experiment = ExperimentFactory()
        # Act
        order = services.create_order(
            user=employee, equipment_type=equipment_type, experiment=experiment,
        )
        # Assert
        assert order.experiment_id == experiment.id


@pytest.mark.unit
class TestRejectOrder:
    def test_blank_reason_is_rejected(self, db, order):
        # Act / Assert
        with pytest.raises(ValidationError, match='rejection_reason'):
            services.reject_order(order, rejection_reason='   ')

    def test_valid_rejection_persists_reason_and_status(self, db, order):
        # Arrange
        order.status = Order.Status.WAITING
        order.save()
        # Act
        result = services.reject_order(order, rejection_reason='Out of capacity')
        # Assert
        assert result.status == Order.Status.REJECTED
        assert result.rejection_reason == 'Out of capacity'

    def test_cannot_reject_already_done_order(self, db, order):
        # Arrange
        order.status = Order.Status.DONE
        order.save()
        # Act / Assert
        with pytest.raises(ValidationError, match='Cannot transition'):
            services.reject_order(order, rejection_reason='nope')


@pytest.mark.unit
class TestApproveAndScheduleStage:
    @freeze_time('2026-05-01 10:00:00')
    def test_rejects_schedule_in_the_past(self, db, order, equipment_type):
        # Arrange — stage in WAITING
        stage = OrderStageFactory(
            order=order, equipment_type=equipment_type, status=OrderStage.Status.WAITING,
        )
        # Act / Assert
        with pytest.raises(ValidationError, match='past'):
            services.approve_and_schedule_stage(
                stage,
                schedule_start='2026-04-30T10:00:00Z',
                schedule_end='2026-04-30T11:00:00Z',
            )

    @freeze_time('2026-05-01 10:00:00')
    def test_rejects_end_before_start(self, db, order, equipment_type):
        stage = OrderStageFactory(
            order=order, equipment_type=equipment_type, status=OrderStage.Status.WAITING,
        )
        with pytest.raises(ValidationError, match='after'):
            services.approve_and_schedule_stage(
                stage,
                schedule_start='2026-05-02T11:00:00Z',
                schedule_end='2026-05-02T10:00:00Z',
            )

    def test_cannot_approve_pending_stage(self, db, order, equipment_type):
        # Arrange — stage in PENDING (not yet relayed)
        stage = OrderStageFactory(
            order=order, equipment_type=equipment_type, status=OrderStage.Status.PENDING,
        )
        with pytest.raises(ValidationError, match='Cannot approve'):
            services.approve_and_schedule_stage(
                stage,
                schedule_start='2099-01-01T00:00:00Z',
                schedule_end='2099-01-01T01:00:00Z',
            )

    @freeze_time('2026-05-01 10:00:00')
    def test_happy_path_transitions_to_in_progress(self, db, order, equipment_type, mocker):
        # Arrange
        # Mock external dependency: scheduling.services.allocate_equipments_for_stage
        mocker.patch(
            'scheduling.services.allocate_equipments_for_stage', return_value=[],
        )
        stage = OrderStageFactory(
            order=order, equipment_type=equipment_type, status=OrderStage.Status.WAITING,
        )
        # Act
        result = services.approve_and_schedule_stage(
            stage,
            schedule_start='2026-05-02T10:00:00Z',
            schedule_end='2026-05-02T12:00:00Z',
        )
        # Assert
        assert result.status == OrderStage.Status.IN_PROGRESS
        assert result.schedule_start.isoformat().startswith('2026-05-02')

    @freeze_time('2026-05-01 10:00:00')
    def test_first_approval_promotes_order_from_waiting_to_in_progress(
        self, db, employee, equipment_type, mocker,
    ):
        """Regression: previously create_order set the order straight to
        IN_PROGRESS, skipping the documented WAITING phase. The fix sets
        new orders to WAITING; the only stage approval is what promotes
        them to IN_PROGRESS. This test pins both halves."""
        mocker.patch(
            'scheduling.services.allocate_equipments_for_stage', return_value=[],
        )
        # Arrange — build a real order via the public API so the WAITING
        # invariant on creation is also covered.
        EquipmentFactory(equipment_type=equipment_type, department=employee.department)
        order = services.create_order(user=employee, equipment_type=equipment_type)
        assert order.status == Order.Status.WAITING        # invariant on creation
        first_stage = order.stages.order_by('step_order').first()
        assert first_stage.status == OrderStage.Status.WAITING

        # Act — manager approves the first stage
        services.approve_and_schedule_stage(
            first_stage,
            schedule_start='2026-05-02T10:00:00Z',
            schedule_end='2026-05-02T12:00:00Z',
        )

        # Assert — order now IN_PROGRESS, stage IN_PROGRESS
        order.refresh_from_db()
        first_stage.refresh_from_db()
        assert order.status == Order.Status.IN_PROGRESS
        assert first_stage.status == OrderStage.Status.IN_PROGRESS

    @freeze_time('2026-05-01 10:00:00')
    def test_assignee_as_uuid_string_does_not_break_notification(
        self, db, order, equipment_type, lab_member, mocker,
    ):
        """Regression: PATCH /api/orders/stages/<id>/review/ passes the
        assignee field as a raw UUID string from request.data, not a User
        instance. _send_notification used to call .username on it and crash
        with AttributeError, surfacing as a 500 to the manager UI."""
        # Arrange
        mocker.patch(
            'scheduling.services.allocate_equipments_for_stage', return_value=[],
        )
        stage = OrderStageFactory(
            order=order, equipment_type=equipment_type, status=OrderStage.Status.WAITING,
        )
        # Act — pass assignee as a UUID string, the way the view layer does
        result = services.approve_and_schedule_stage(
            stage,
            schedule_start='2026-05-02T10:00:00Z',
            schedule_end='2026-05-02T12:00:00Z',
            assignee=str(lab_member.id),
        )
        # Assert — no AttributeError + assignee was correctly bound to the user
        assert result.status == OrderStage.Status.IN_PROGRESS
        assert str(result.assignee_id) == str(lab_member.id)


@pytest.mark.unit
class TestCompleteStage:
    def test_cannot_complete_before_schedule_start(self, db, order, equipment_type):
        # Arrange
        with freeze_time('2026-05-01 10:00:00'):
            stage = OrderStageFactory(
                order=order,
                equipment_type=equipment_type,
                status=OrderStage.Status.IN_PROGRESS,
            )
            stage.schedule_start = stage.schedule_end = None
            stage.save()
            # Manually set schedule_start in the future via update to bypass
            # auto_now_add semantics
            from django.utils.dateparse import parse_datetime
            stage.schedule_start = parse_datetime('2026-05-02T10:00:00Z')
            stage.save()
        # Act / Assert
        with freeze_time('2026-05-01 10:00:00'):
            with pytest.raises(ValidationError, match='before its scheduled start'):
                services.complete_stage(stage)

    @freeze_time('2026-05-02 11:00:00')
    def test_marks_done_and_releases_equipment(self, db, order, equipment_type):
        # Arrange
        equipment = EquipmentFactory(equipment_type=equipment_type, status='occupied')
        stage = OrderStageFactory(
            order=order, equipment_type=equipment_type,
            status=OrderStage.Status.IN_PROGRESS,
            equipment=equipment,
        )
        # Act
        services.complete_stage(stage)
        # Assert
        stage.refresh_from_db()
        equipment.refresh_from_db()
        assert stage.status == OrderStage.Status.DONE
        assert stage.completed_at is not None
        assert equipment.status == 'available'

    @freeze_time('2026-05-02 11:00:00')
    def test_completes_order_when_stage_done(self, db, order, equipment_type):
        # Arrange — single-stage order: completing the stage finishes the order.
        order.status = Order.Status.IN_PROGRESS
        order.save()
        stage = OrderStageFactory(
            order=order, equipment_type=equipment_type,
            status=OrderStage.Status.IN_PROGRESS,
        )
        # Act
        services.complete_stage(stage)
        # Assert
        order.refresh_from_db()
        assert order.status == Order.Status.DONE
        assert order.ended_at is not None

    @freeze_time('2026-05-02 11:00:00')
    def test_completion_notifies_requester_to_collect_wafer(
        self, db, order, equipment_type, mocker,
    ):
        # Arrange
        notify_spy = mocker.spy(services, '_send_notification')
        order.status = Order.Status.IN_PROGRESS
        order.save()
        stage = OrderStageFactory(
            order=order, equipment_type=equipment_type,
            status=OrderStage.Status.IN_PROGRESS,
        )
        # Act
        services.complete_stage(stage)
        # Assert — single notification to the requester, no relay handoff
        assert notify_spy.call_count == 1
        notified_user, msg = notify_spy.call_args[0]
        assert notified_user == order.user
        assert 'ready' in msg.lower()
