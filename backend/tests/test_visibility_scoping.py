"""Integration tests for role-based row-level visibility.

Locks in the contract:
  * superuser          — sees everything
  * lab_manager        — only their lab's orders/stages
  * lab_member         — only stages assigned to themselves (and the orders
                          those stages belong to)
  * regular_employee   — only orders they themselves submitted
  * Equipment must be assigned to a lab (department required by admin_api)
"""
import pytest

from tests.factories import (
    DepartmentFactory,
    EquipmentTypeFactory,
    ExperimentFactory,
    LabMemberFactory,
    LabManagerFactory,
    OrderFactory,
    OrderStageFactory,
    UserFactory,
)


@pytest.mark.integration
class TestOrderListVisibility:
    def test_regular_employee_sees_only_own_orders(self, db, employee_client, employee, department):
        # Arrange — employee owns one order, someone else owns another
        mine = OrderFactory(user=employee, department=department)
        other = UserFactory(department=department)
        OrderFactory(user=other, department=department)
        # Act
        response = employee_client.get('/api/orders/')
        # Assert
        assert response.status_code == 200
        ids = {row['id'] for row in response.data['results']}
        assert str(mine.id) in ids
        assert len(ids) == 1

    def test_lab_manager_sees_only_their_department(self, db, manager_client, lab_manager):
        # Arrange — order in manager's dept + order in foreign dept
        own = OrderFactory(department=lab_manager.department)
        foreign_dept = DepartmentFactory()
        foreign = OrderFactory(department=foreign_dept)
        # Act
        response = manager_client.get('/api/orders/')
        # Assert
        ids = {row['id'] for row in response.data['results']}
        assert str(own.id) in ids
        assert str(foreign.id) not in ids

    def test_lab_member_sees_only_orders_with_assigned_stages(
        self, db, member_client, lab_member, equipment_type,
    ):
        # Arrange — order A has a stage assigned to me, order B has a stage assigned to someone else
        order_assigned = OrderFactory(department=lab_member.department)
        OrderStageFactory(
            order=order_assigned, equipment_type=equipment_type,
            department=lab_member.department, assignee=lab_member,
        )

        order_unassigned = OrderFactory(department=lab_member.department)
        other = LabMemberFactory(department=lab_member.department)
        OrderStageFactory(
            order=order_unassigned, equipment_type=equipment_type,
            department=lab_member.department, assignee=other,
        )
        # Act
        response = member_client.get('/api/orders/')
        # Assert
        ids = {row['id'] for row in response.data['results']}
        assert str(order_assigned.id) in ids
        assert str(order_unassigned.id) not in ids

    def test_superuser_sees_everything(self, db, superuser_client):
        # Arrange
        for _ in range(3):
            OrderFactory()
        # Act
        response = superuser_client.get('/api/orders/')
        # Assert — at minimum the three we just made
        assert response.data['count'] >= 3


@pytest.mark.integration
class TestOrderDetailVisibility:
    def test_regular_employee_cannot_read_someone_elses_order(
        self, db, employee_client, employee, department,
    ):
        # Arrange — order owned by another user
        other = UserFactory(department=department)
        their_order = OrderFactory(user=other, department=department)
        # Act
        response = employee_client.get(f'/api/orders/{their_order.id}/')
        # Assert — 404 (not 403) so existence isn't leaked
        assert response.status_code == 404

    def test_lab_member_cannot_read_orders_without_their_stage(
        self, db, member_client, lab_member, equipment_type,
    ):
        # Arrange — order in same department but no stage assigned to me
        other = LabMemberFactory(department=lab_member.department)
        order = OrderFactory(department=lab_member.department)
        OrderStageFactory(
            order=order, equipment_type=equipment_type,
            department=lab_member.department, assignee=other,
        )
        # Act
        response = member_client.get(f'/api/orders/{order.id}/')
        # Assert
        assert response.status_code == 404

    def test_lab_manager_cannot_read_foreign_lab_orders(
        self, db, manager_client, lab_manager,
    ):
        # Arrange
        foreign_order = OrderFactory(department=DepartmentFactory())
        # Act
        response = manager_client.get(f'/api/orders/{foreign_order.id}/')
        # Assert
        assert response.status_code == 404


@pytest.mark.integration
class TestOrderStageListVisibility:
    def test_lab_member_only_sees_assigned_stages(
        self, db, member_client, lab_member, equipment_type,
    ):
        # Arrange — one stage assigned to me, one to someone else, one unassigned
        order = OrderFactory(department=lab_member.department)
        mine = OrderStageFactory(
            order=order, step_order=1,
            equipment_type=equipment_type, department=lab_member.department,
            assignee=lab_member, status='in_progress',
        )
        other = LabMemberFactory(department=lab_member.department)
        OrderStageFactory(
            order=order, step_order=2,
            equipment_type=equipment_type, department=lab_member.department,
            assignee=other, status='in_progress',
        )
        OrderStageFactory(
            order=order, step_order=3,
            equipment_type=equipment_type, department=lab_member.department,
            assignee=None, status='in_progress',
        )
        # Act
        response = member_client.get('/api/orders/stages/')
        # Assert — exactly the one assigned to me
        ids = {row['id'] for row in response.data['results']}
        assert ids == {str(mine.id)}

    def test_lab_manager_sees_all_dept_stages_with_assignees(
        self, db, manager_client, lab_manager, equipment_type,
    ):
        # Arrange — three stages in manager's lab assigned to different members
        order = OrderFactory(department=lab_manager.department)
        members = [LabMemberFactory(department=lab_manager.department) for _ in range(3)]
        for i, m in enumerate(members, start=1):
            OrderStageFactory(
                order=order, step_order=i,
                equipment_type=equipment_type, department=lab_manager.department,
                assignee=m, status='in_progress',
            )
        # And one stage in a foreign lab
        foreign_dept = DepartmentFactory()
        foreign_stage = OrderStageFactory(
            order=OrderFactory(department=foreign_dept),
            step_order=1, equipment_type=equipment_type,
            department=foreign_dept, status='waiting',
        )
        # Act
        response = manager_client.get('/api/orders/stages/')
        # Assert — exactly the 3 dept stages, foreign one filtered out
        ids = {row['id'] for row in response.data['results']}
        assert str(foreign_stage.id) not in ids
        assert response.data['count'] == 3

    def test_regular_employee_sees_only_own_order_stages(
        self, db, employee_client, employee, equipment_type,
    ):
        # Arrange
        my_order = OrderFactory(user=employee, department=employee.department)
        my_stage = OrderStageFactory(
            order=my_order, equipment_type=equipment_type,
            department=employee.department, status='waiting',
        )
        someone_else_order = OrderFactory(department=employee.department)
        OrderStageFactory(
            order=someone_else_order, equipment_type=equipment_type,
            department=employee.department, status='waiting',
        )
        # Act
        response = employee_client.get('/api/orders/stages/')
        # Assert
        ids = {row['id'] for row in response.data['results']}
        assert ids == {str(my_stage.id)}


@pytest.mark.integration
class TestAdminEquipmentRequiresDepartment:
    def test_create_without_department_is_rejected(self, superuser_client, equipment_type):
        # Act — missing department field
        response = superuser_client.post(
            '/api/admin/equipment/',
            {
                'code': 'NEEDS-DEPT-001',
                'equipment_type': str(equipment_type.id),
                'status': 'available',
            },
            format='json',
        )
        # Assert — admin_api validates this even though the model column is nullable
        assert response.status_code == 400
        assert 'department' in str(response.data).lower()

    def test_create_with_explicit_null_department_is_rejected(
        self, superuser_client, equipment_type,
    ):
        # Act
        response = superuser_client.post(
            '/api/admin/equipment/',
            {
                'code': 'NEEDS-DEPT-002',
                'equipment_type': str(equipment_type.id),
                'department': None,
                'status': 'available',
            },
            format='json',
        )
        # Assert
        assert response.status_code == 400

    def test_create_with_department_succeeds(
        self, superuser_client, equipment_type, department,
    ):
        # Act
        response = superuser_client.post(
            '/api/admin/equipment/',
            {
                'code': 'WITH-DEPT-001',
                'equipment_type': str(equipment_type.id),
                'department': str(department.id),
                'status': 'available',
            },
            format='json',
        )
        # Assert
        assert response.status_code == 201, response.data
        assert str(response.data['department']) == str(department.id)
