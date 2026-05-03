"""Unit tests for utils.exception_handler.

Verifies the uniform envelope shape and the 5xx traceback masking.
"""
from unittest.mock import MagicMock

import pytest
from rest_framework.exceptions import (
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)

from utils.exception_handler import custom_exception_handler


@pytest.fixture
def context():
    request = MagicMock()
    request.path = '/api/orders/'
    request.request_id = 'req-abc'
    return {'request': request, 'view': MagicMock()}


@pytest.mark.unit
class TestCustomExceptionHandler:
    def test_validation_error_returns_uniform_envelope(self, context):
        # Arrange
        exc = ValidationError({'username': ['This field is required.']})
        # Act
        response = custom_exception_handler(exc, context)
        # Assert
        assert response.status_code == 400
        assert response.data['code'] == 'validation_error'
        assert response.data['detail'] == 'Validation failed.'
        assert response.data['fields'] == {'username': ['This field is required.']}
        assert response.data['request_id'] == 'req-abc'

    def test_not_authenticated_envelope(self, context):
        # Arrange
        exc = NotAuthenticated()
        # Act
        response = custom_exception_handler(exc, context)
        # Assert
        assert response.status_code == 401
        assert response.data['code'] == 'not_authenticated'
        assert response.data['request_id'] == 'req-abc'

    def test_permission_denied_envelope(self, context):
        # Arrange
        exc = PermissionDenied('Superuser role required.')
        # Act
        response = custom_exception_handler(exc, context)
        # Assert
        assert response.status_code == 403
        assert response.data['code'] == 'permission_denied'
        assert 'Superuser' in response.data['detail']

    def test_unhandled_exception_masks_traceback(self, context, mocker):
        # Arrange — raise a non-DRF error. We mock the module-level logger so
        # we can assert the exception was logged regardless of the project's
        # propagate=False logging config.
        mock_logger = mocker.patch('utils.exception_handler.logger')
        exc = RuntimeError('database is on fire')
        # Act
        response = custom_exception_handler(exc, context)
        # Assert — never leak internal message
        assert response.status_code == 500
        assert response.data['code'] == 'server_error'
        assert 'database is on fire' not in response.data['detail']
        assert 'internal error' in response.data['detail'].lower()
        # And the original error must have been logged
        mock_logger.exception.assert_called_once()
        assert 'Unhandled exception' in mock_logger.exception.call_args[0][0]

    def test_request_id_omitted_when_request_lacks_one(self, context):
        # Arrange
        delattr(context['request'], 'request_id')
        exc = NotAuthenticated()
        # Act
        response = custom_exception_handler(exc, context)
        # Assert
        assert 'request_id' not in response.data
