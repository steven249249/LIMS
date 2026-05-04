"""Integration tests for bulk-create / bulk-delete on /api/admin/users/.

Covers:
  * username serial generation per (role, department)
  * password hashing on bulk create
  * department validation per role
  * count clamp + role validation
  * bulk delete safety rails (self, last superuser)
  * /api/users/register/ removed (404)
"""
import pytest

from tests.factories import (
    DepartmentFactory,
    LabManagerFactory,
    LabMemberFactory,
    SuperUserFactory,
    UserFactory,
)
from users.models import User


@pytest.mark.integration
class TestBulkCreate:
    def test_creates_n_regular_employees(self, db, superuser_client):
        # Act
        response = superuser_client.post(
            '/api/admin/users/bulk-create/',
            {'role': 'regular_employee', 'count': 4},
            format='json',
        )
        # Assert
        assert response.status_code == 201, response.data
        assert response.data['count'] == 4
        usernames = {u['username'] for u in response.data['created']}
        assert usernames == {'Emp_001', 'Emp_002', 'Emp_003', 'Emp_004'}

    def test_lab_member_uses_department_in_username(self, db, superuser_client, department):
        # Act
        response = superuser_client.post(
            '/api/admin/users/bulk-create/',
            {
                'role': 'lab_member',
                'count': 2,
                'department': str(department.id),
            },
            format='json',
        )
        # Assert
        assert response.status_code == 201
        usernames = sorted(u['username'] for u in response.data['created'])
        prefix = f'LabMem_{department.name}'.replace(' ', '')
        assert usernames == [f'{prefix}_001', f'{prefix}_002']

    def test_lab_manager_naming_independent_from_member(self, db, superuser_client, department):
        # Arrange — already have a member with serial 001 in the same dept
        superuser_client.post(
            '/api/admin/users/bulk-create/',
            {'role': 'lab_member', 'count': 1, 'department': str(department.id)},
            format='json',
        )
        # Act — manager should still start at 001 because prefix differs
        response = superuser_client.post(
            '/api/admin/users/bulk-create/',
            {'role': 'lab_manager', 'count': 1, 'department': str(department.id)},
            format='json',
        )
        # Assert
        prefix = f'LabMgr_{department.name}'.replace(' ', '')
        assert response.data['created'][0]['username'] == f'{prefix}_001'

    def test_serial_continues_after_existing_users(self, db, superuser_client, department):
        # Arrange — first batch
        superuser_client.post(
            '/api/admin/users/bulk-create/',
            {'role': 'lab_member', 'count': 3, 'department': str(department.id)},
            format='json',
        )
        # Act — second batch
        response = superuser_client.post(
            '/api/admin/users/bulk-create/',
            {'role': 'lab_member', 'count': 2, 'department': str(department.id)},
            format='json',
        )
        # Assert — picks up from 004
        usernames = sorted(u['username'] for u in response.data['created'])
        prefix = f'LabMem_{department.name}'.replace(' ', '')
        assert usernames == [f'{prefix}_004', f'{prefix}_005']

    def test_password_is_hashed_and_login_succeeds(self, db, superuser_client, api_client):
        # Arrange / Act
        response = superuser_client.post(
            '/api/admin/users/bulk-create/',
            {'role': 'regular_employee', 'count': 1, 'password': 'MyTestPass2026!'},
            format='json',
        )
        username = response.data['created'][0]['username']
        # Assert — created user can actually log in with the bulk password
        login = api_client.post(
            '/api/users/login/',
            {'username': username, 'password': 'MyTestPass2026!'},
            format='json',
        )
        assert login.status_code == 200
        assert 'access' in login.data
        # And the stored hash isn't the raw password
        stored = User.objects.get(username=username)
        assert stored.password != 'MyTestPass2026!'

    def test_lab_member_requires_department(self, db, superuser_client):
        # Act — missing department for a lab role
        response = superuser_client.post(
            '/api/admin/users/bulk-create/',
            {'role': 'lab_member', 'count': 2},
            format='json',
        )
        # Assert
        assert response.status_code == 400
        assert 'department' in str(response.data).lower()

    def test_count_must_be_positive(self, db, superuser_client):
        response = superuser_client.post(
            '/api/admin/users/bulk-create/',
            {'role': 'regular_employee', 'count': 0},
            format='json',
        )
        assert response.status_code == 400

    def test_count_capped_at_100(self, db, superuser_client):
        response = superuser_client.post(
            '/api/admin/users/bulk-create/',
            {'role': 'regular_employee', 'count': 200},
            format='json',
        )
        assert response.status_code == 400

    def test_invalid_role_rejected(self, db, superuser_client):
        response = superuser_client.post(
            '/api/admin/users/bulk-create/',
            {'role': 'superuser', 'count': 1},
            format='json',
        )
        # Bulk endpoint refuses to mint superusers — too sensitive
        assert response.status_code == 400

    def test_non_admin_forbidden(self, db, employee_client):
        response = employee_client.post(
            '/api/admin/users/bulk-create/',
            {'role': 'regular_employee', 'count': 1},
            format='json',
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestBulkDelete:
    def test_deletes_listed_ids(self, db, superuser_client):
        # Arrange — three deletable users
        a, b, c = UserFactory(), UserFactory(), UserFactory()
        # Act
        response = superuser_client.post(
            '/api/admin/users/bulk-delete/',
            {'ids': [str(a.id), str(b.id), str(c.id)]},
            format='json',
        )
        # Assert
        assert response.status_code == 200
        assert response.data['deleted'] == 3
        assert response.data['skipped'] == []
        assert not User.objects.filter(pk__in=[a.id, b.id, c.id]).exists()

    def test_skips_self(self, db, superuser_client, superuser):
        # Act
        response = superuser_client.post(
            '/api/admin/users/bulk-delete/',
            {'ids': [str(superuser.id)]},
            format='json',
        )
        # Assert
        assert response.status_code == 200
        assert response.data['deleted'] == 0
        assert response.data['skipped'][0]['reason'] == 'cannot delete self'
        assert User.objects.filter(pk=superuser.id).exists()

    def test_skips_when_would_remove_last_superuser(self, db):
        # Arrange — clear out the auto-provisioned admin so we can simulate
        # the "exactly one superuser left" condition.
        User.objects.filter(role='superuser').delete()
        only_superuser = SuperUserFactory()
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        actor = UserFactory(role='lab_manager', is_staff=True, is_superuser=True)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(actor).access_token}')
        # Act
        response = client.post(
            '/api/admin/users/bulk-delete/',
            {'ids': [str(only_superuser.id)]},
            format='json',
        )
        # Assert
        assert response.status_code == 200
        assert response.data['deleted'] == 0
        assert 'superuser' in response.data['skipped'][0]['reason']

    def test_partial_skip_still_deletes_others(self, db, superuser_client, superuser):
        # Arrange — mix of self + a deletable employee
        target = UserFactory()
        # Act
        response = superuser_client.post(
            '/api/admin/users/bulk-delete/',
            {'ids': [str(superuser.id), str(target.id)]},
            format='json',
        )
        # Assert
        assert response.status_code == 200
        assert response.data['deleted'] == 1
        assert len(response.data['skipped']) == 1
        assert User.objects.filter(pk=superuser.id).exists()
        assert not User.objects.filter(pk=target.id).exists()

    def test_empty_ids_rejected(self, db, superuser_client):
        response = superuser_client.post(
            '/api/admin/users/bulk-delete/',
            {'ids': []},
            format='json',
        )
        assert response.status_code == 400

    def test_non_admin_forbidden(self, db, employee_client):
        response = employee_client.post(
            '/api/admin/users/bulk-delete/',
            {'ids': []},
            format='json',
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestRegistrationRemoved:
    def test_register_endpoint_returns_404(self, api_client):
        # Public registration is intentionally not exposed any more.
        response = api_client.post(
            '/api/users/register/',
            {'username': 'someone', 'password': 'whatever123'},
            format='json',
        )
        assert response.status_code == 404
