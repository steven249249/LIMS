"""Integration tests for /api/monitoring/* endpoints."""
import pytest

from monitoring.models import ActivityLog


@pytest.mark.integration
class TestDashboardEndpoint:
    def test_anonymous_blocked(self, api_client):
        response = api_client.get('/api/monitoring/dashboard/')
        assert response.status_code == 401

    def test_non_superuser_forbidden(self, employee_client):
        response = employee_client.get('/api/monitoring/dashboard/')
        assert response.status_code == 403

    def test_superuser_receives_full_payload(self, superuser_client):
        # Act
        response = superuser_client.get('/api/monitoring/dashboard/')
        # Assert
        assert response.status_code == 200
        for key in ('orders', 'order_stages', 'equipment', 'users', 'activity'):
            assert key in response.data, f'missing top-level key: {key}'
        assert 'by_status' in response.data['orders']


@pytest.mark.integration
class TestActivityLogsEndpoint:
    def test_middleware_records_each_request(self, db, employee_client, employee):
        # Arrange — clear the slate so the next request is the only entry
        ActivityLog.objects.all().delete()
        # Act
        employee_client.get('/api/users/profile/')
        # Assert
        log = ActivityLog.objects.order_by('-timestamp').first()
        assert log is not None
        assert log.path == '/api/users/profile/'
        assert log.user == employee
        assert log.http_method == 'GET'
        assert log.status_code == 200

    def test_filter_by_action_type(self, db, superuser_client):
        # Arrange — emit a known login + a read
        superuser_client.post(
            '/api/users/login/',
            {'username': 'noone', 'password': 'noone'},
            format='json',
        )
        superuser_client.get('/api/monitoring/dashboard/')
        # Act
        response = superuser_client.get('/api/monitoring/logs/?action_type=login')
        # Assert
        assert response.status_code == 200
        for row in response.data['results']:
            assert row['action_type'] == 'login'

    def test_request_id_round_trips_to_log(self, db, superuser_client):
        # Arrange
        ActivityLog.objects.all().delete()
        # Act — supply a custom trace id
        superuser_client.credentials(
            HTTP_AUTHORIZATION=superuser_client._credentials['HTTP_AUTHORIZATION'],
            HTTP_X_REQUEST_ID='trace-pytest-9',
        )
        superuser_client.get('/api/users/profile/')
        # Assert
        log = ActivityLog.objects.filter(path='/api/users/profile/').first()
        assert log is not None
        assert log.request_id == 'trace-pytest-9'

    def test_password_is_redacted_in_log(self, db, api_client):
        # Arrange — anonymous login attempt with bad creds (still goes through middleware)
        ActivityLog.objects.all().delete()
        # Act
        api_client.post(
            '/api/users/login/',
            {'username': 'unknown', 'password': 'ShouldNotAppear!'},
            format='json',
        )
        # Assert — log captured the body but with the password redacted
        log = ActivityLog.objects.filter(path='/api/users/login/').first()
        assert log is not None
        assert log.request_data is not None
        assert log.request_data.get('password') == '***REDACTED***'
        assert log.request_data.get('username') == 'unknown'
