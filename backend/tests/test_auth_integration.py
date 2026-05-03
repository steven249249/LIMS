"""Integration tests for the auth surface (JWT login / refresh / profile)."""
import pytest


@pytest.mark.integration
class TestAuthLogin:
    def test_valid_credentials_return_jwt_pair(self, api_client, employee):
        # Act
        response = api_client.post(
            '/api/users/login/',
            {'username': employee.username, 'password': 'TestPass2026!'},
            format='json',
        )
        # Assert
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_wrong_password_uses_uniform_error_envelope(self, api_client, employee):
        # Act
        response = api_client.post(
            '/api/users/login/',
            {'username': employee.username, 'password': 'wrong'},
            format='json',
        )
        # Assert — uniform envelope shape from custom_exception_handler
        assert response.status_code == 401
        assert 'detail' in response.data
        assert 'code' in response.data

    def test_missing_fields_return_validation_envelope(self, api_client):
        # Act
        response = api_client.post('/api/users/login/', {}, format='json')
        # Assert
        assert response.status_code == 400
        assert response.data['code'] == 'validation_error'
        assert 'fields' in response.data


@pytest.mark.integration
class TestAuthProfile:
    def test_anonymous_blocked(self, api_client):
        response = api_client.get('/api/users/profile/')
        assert response.status_code == 401
        assert response.data['code'] == 'not_authenticated'

    def test_authenticated_returns_user_payload(self, employee_client, employee):
        response = employee_client.get('/api/users/profile/')
        assert response.status_code == 200
        assert response.data['username'] == employee.username
        assert response.data['role'] == 'regular_employee'


@pytest.mark.integration
class TestAuthRefresh:
    def test_refresh_token_grants_new_access(self, api_client, employee):
        # Arrange — login to grab refresh
        login = api_client.post(
            '/api/users/login/',
            {'username': employee.username, 'password': 'TestPass2026!'},
            format='json',
        )
        refresh_token = login.data['refresh']
        # Act
        response = api_client.post(
            '/api/users/token/refresh/',
            {'refresh': refresh_token},
            format='json',
        )
        # Assert
        assert response.status_code == 200
        assert 'access' in response.data
