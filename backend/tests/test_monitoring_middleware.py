"""Unit tests for the monitoring middleware.

Each test follows the AAA pattern (Arrange / Act / Assert) and exercises a
single behaviour. Pure functions (`_redact`, `_classify`) are tested directly;
the middleware itself is exercised via the test client where DB persistence
matters.
"""
from unittest.mock import MagicMock

import pytest

from monitoring.middleware import (
    ActivityLogMiddleware,
    _classify,
    _client_ip,
    _redact,
)
from monitoring.models import ActivityLog


# ── Pure helpers (pure unit, no DB) ────────────────────────────────────────

@pytest.mark.unit
class TestRedact:
    def test_redacts_password_field(self):
        # Arrange
        payload = {'username': 'alice', 'password': 's3cret'}
        # Act
        result = _redact(payload)
        # Assert
        assert result['username'] == 'alice'
        assert result['password'] == '***REDACTED***'

    def test_redacts_token_and_refresh_keys(self):
        # Arrange
        payload = {'access': 'abc', 'refresh': 'xyz', 'name': 'ok'}
        # Act
        result = _redact(payload)
        # Assert
        assert result == {'access': '***REDACTED***', 'refresh': '***REDACTED***', 'name': 'ok'}

    def test_redacts_nested_dicts(self):
        # Arrange
        payload = {'user': {'username': 'bob', 'password': 'leak'}}
        # Act
        result = _redact(payload)
        # Assert
        assert result['user']['password'] == '***REDACTED***'
        assert result['user']['username'] == 'bob'

    def test_redacts_inside_lists(self):
        # Arrange
        payload = {'creds': [{'password': 'one'}, {'password': 'two'}]}
        # Act
        result = _redact(payload)
        # Assert
        assert all(item['password'] == '***REDACTED***' for item in result['creds'])

    def test_passes_non_dict_unchanged(self):
        assert _redact('plain string') == 'plain string'
        assert _redact(123) == 123


@pytest.mark.unit
class TestClassify:
    @pytest.fixture
    def request_factory(self):
        def _make(method, path):
            request = MagicMock()
            request.method = method
            request.path = path
            return request
        return _make

    def test_login_for_post_with_login_in_path(self, request_factory):
        request = request_factory('POST', '/api/users/login/')
        assert _classify(request) == ActivityLog.ActionType.LOGIN

    def test_login_for_token_endpoint(self, request_factory):
        request = request_factory('POST', '/api/users/token/refresh/')
        assert _classify(request) == ActivityLog.ActionType.LOGIN

    def test_logout_path_overrides_method(self, request_factory):
        request = request_factory('POST', '/api/users/logout/')
        assert _classify(request) == ActivityLog.ActionType.LOGOUT

    @pytest.mark.parametrize('method,expected', [
        ('GET', ActivityLog.ActionType.READ),
        ('POST', ActivityLog.ActionType.CREATE),
        ('PUT', ActivityLog.ActionType.UPDATE),
        ('PATCH', ActivityLog.ActionType.UPDATE),
        ('DELETE', ActivityLog.ActionType.DELETE),
    ])
    def test_method_to_action_mapping(self, request_factory, method, expected):
        request = request_factory(method, '/api/orders/')
        assert _classify(request) == expected

    def test_unknown_method_falls_back_to_other(self, request_factory):
        request = request_factory('OPTIONS', '/api/orders/')
        assert _classify(request) == ActivityLog.ActionType.OTHER


@pytest.mark.unit
class TestClientIP:
    def test_uses_x_forwarded_for_when_present(self):
        request = MagicMock()
        request.META = {'HTTP_X_FORWARDED_FOR': '203.0.113.5, 10.0.0.1', 'REMOTE_ADDR': '127.0.0.1'}
        assert _client_ip(request) == '203.0.113.5'

    def test_falls_back_to_remote_addr(self):
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '192.168.1.10'}
        assert _client_ip(request) == '192.168.1.10'


# ── Middleware behaviour (integration with DB) ─────────────────────────────

@pytest.mark.unit
class TestActivityLogMiddleware:
    def test_skips_static_paths(self, db):
        # Arrange — fake response
        get_response = MagicMock(return_value=MagicMock(status_code=200))
        middleware = ActivityLogMiddleware(get_response)
        request = MagicMock()
        request.path = '/static/main.css'
        # Act
        middleware(request)
        # Assert — short-circuit means the response is fetched but no log row written
        get_response.assert_called_once_with(request)
        assert ActivityLog.objects.count() == 0

    def test_failure_to_log_does_not_break_request(self, db, mocker):
        # Arrange — make ActivityLog.objects.create blow up
        mocker.patch.object(ActivityLog.objects, 'create', side_effect=RuntimeError('db down'))
        get_response = MagicMock(return_value=MagicMock(status_code=200))
        middleware = ActivityLogMiddleware(get_response)
        request = MagicMock()
        request.path = '/api/orders/'
        request.method = 'GET'
        request.META = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_USER_AGENT': 'pytest'}
        request.body = b''
        request.user = MagicMock(is_authenticated=False)
        request.request_id = 'r-1'
        # Act
        response = middleware(request)
        # Assert — request must still succeed even though logging raised
        assert response.status_code == 200
