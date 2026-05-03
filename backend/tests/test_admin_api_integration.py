"""Integration tests for /api/admin/* via DRF APIClient.

These exercise the full request → router → permission → viewset → serializer
→ response stack. They lean on the per-role authenticated client fixtures
defined in conftest.py.
"""
import pytest

from tests.factories import (
    EquipmentTypeFactory,
    SuperUserFactory,
    UserFactory,
)


@pytest.mark.integration
class TestAdminPermissionGating:
    """Only superusers may reach /api/admin/*."""

    @pytest.mark.parametrize('client_fixture', [
        'api_client',          # anonymous
        'employee_client',
        'manager_client',
        'member_client',
    ])
    def test_non_superuser_is_blocked(self, request, client_fixture):
        # Arrange
        client = request.getfixturevalue(client_fixture)
        # Act
        response = client.get('/api/admin/users/')
        # Assert — anonymous → 401, authenticated non-admin → 403
        assert response.status_code in (401, 403)

    def test_superuser_reaches_admin(self, superuser_client):
        # Act
        response = superuser_client.get('/api/admin/users/')
        # Assert
        assert response.status_code == 200
        assert 'results' in response.data


@pytest.mark.integration
class TestAdminEquipmentTypeCRUD:
    def test_create_then_retrieve(self, superuser_client):
        # Arrange / Act — create
        create = superuser_client.post(
            '/api/admin/equipment-types/',
            {'name': 'TEST-CRUD-EQ'},
            format='json',
        )
        # Assert
        assert create.status_code == 201, create.data
        new_id = create.data['id']

        retrieve = superuser_client.get(f'/api/admin/equipment-types/{new_id}/')
        assert retrieve.status_code == 200
        assert retrieve.data['name'] == 'TEST-CRUD-EQ'

    def test_patch_updates_fields(self, superuser_client):
        # Arrange
        eq_type = EquipmentTypeFactory(name='OLD-NAME')
        # Act
        response = superuser_client.patch(
            f'/api/admin/equipment-types/{eq_type.id}/',
            {'name': 'NEW-NAME'},
            format='json',
        )
        # Assert
        assert response.status_code == 200
        assert response.data['name'] == 'NEW-NAME'

    def test_delete_returns_204_then_404(self, superuser_client):
        # Arrange
        eq_type = EquipmentTypeFactory()
        # Act
        delete = superuser_client.delete(f'/api/admin/equipment-types/{eq_type.id}/')
        retrieve = superuser_client.get(f'/api/admin/equipment-types/{eq_type.id}/')
        # Assert
        assert delete.status_code == 204
        assert retrieve.status_code == 404

    def test_search_filters_results(self, superuser_client):
        # Arrange
        EquipmentTypeFactory(name='SEM-Alpha')
        EquipmentTypeFactory(name='SEM-Beta')
        EquipmentTypeFactory(name='AFM-Gamma')
        # Act
        response = superuser_client.get('/api/admin/equipment-types/?search=SEM')
        # Assert
        names = {row['name'] for row in response.data['results']}
        assert 'SEM-Alpha' in names
        assert 'SEM-Beta' in names
        assert 'AFM-Gamma' not in names


@pytest.mark.integration
class TestAdminUserCRUD:
    def test_password_is_hashed_and_omitted_from_response(self, superuser_client, department):
        # Arrange / Act — create with plaintext password
        response = superuser_client.post(
            '/api/admin/users/',
            {
                'username': 'crud_test_user',
                'email': 'crud@test.com',
                'password': 'P@ssw0rd2026!',
                'role': 'regular_employee',
                'status': 'active',
                'department': str(department.id),
            },
            format='json',
        )
        # Assert
        assert response.status_code == 201, response.data
        # Password is hashed (cannot equal raw)
        from users.models import User
        new_user = User.objects.get(id=response.data['id'])
        assert new_user.password != 'P@ssw0rd2026!'
        assert new_user.check_password('P@ssw0rd2026!')
        # And never echoed back
        assert 'password' not in response.data

    def test_self_delete_is_forbidden(self, superuser_client, superuser):
        # Act
        response = superuser_client.delete(f'/api/admin/users/{superuser.id}/')
        # Assert
        assert response.status_code == 403
        assert 'own account' in response.data['detail'].lower()

    def test_cannot_delete_last_remaining_superuser(self, db):
        # Arrange — exactly one user with role=superuser. The deleter passes
        # IsSystemSuperuser via Django's is_superuser flag instead, so removing
        # `only_superuser` would leave zero role=superuser accounts.
        only_superuser = SuperUserFactory()
        other_admin = UserFactory(
            role='lab_manager', is_staff=True, is_superuser=True,
        )
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken

        client = APIClient()
        token = RefreshToken.for_user(other_admin)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
        # Act
        response = client.delete(f'/api/admin/users/{only_superuser.id}/')
        # Assert
        assert response.status_code == 400
        assert 'last' in str(response.data).lower()

    def test_partial_update_does_not_reset_password(self, superuser_client, department):
        # Arrange
        from users.models import User
        user = UserFactory(department=department)
        original_hash = user.password
        # Act — update name only, no password key in payload
        response = superuser_client.patch(
            f'/api/admin/users/{user.id}/',
            {'first_name': 'Updated'},
            format='json',
        )
        # Assert
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.password == original_hash       # unchanged
        assert user.first_name == 'Updated'


@pytest.mark.integration
class TestAdminCRUDListEndpoints:
    """Smoke test that every admin resource at least serves a paginated list."""

    @pytest.mark.parametrize('endpoint', [
        'fabs', 'departments', 'users', 'experiments',
        'equipment-types', 'equipment', 'experiment-requirements',
        'orders', 'order-stages', 'bookings',
    ])
    def test_list_returns_paginated_envelope(self, superuser_client, endpoint):
        response = superuser_client.get(f'/api/admin/{endpoint}/')
        assert response.status_code == 200, f'{endpoint} failed: {response.data}'
        assert {'count', 'results'} <= response.data.keys()
