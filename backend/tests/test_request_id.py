"""Unit tests for utils.request_id middleware."""
import re
from unittest.mock import MagicMock

import pytest

from utils.request_id import RequestIDMiddleware

UUID_HEX_RE = re.compile(r'^[0-9a-f]{32}$')


def _make_middleware(response_status=200):
    response = MagicMock()
    response.status_code = response_status
    response.__setitem__ = MagicMock()
    get_response = MagicMock(return_value=response)
    middleware = RequestIDMiddleware(get_response)
    return middleware, response


@pytest.mark.unit
class TestRequestIDMiddleware:
    def test_generates_uuid_when_no_header(self):
        # Arrange
        middleware, response = _make_middleware()
        request = MagicMock()
        request.META = {}
        # Act
        middleware(request)
        # Assert
        assert UUID_HEX_RE.match(request.request_id)
        response.__setitem__.assert_called_with('X-Request-ID', request.request_id)

    def test_honours_upstream_request_id(self):
        # Arrange
        middleware, response = _make_middleware()
        request = MagicMock()
        request.META = {'HTTP_X_REQUEST_ID': 'edge-trace-7'}
        # Act
        middleware(request)
        # Assert
        assert request.request_id == 'edge-trace-7'
        response.__setitem__.assert_called_with('X-Request-ID', 'edge-trace-7')

    def test_caps_oversized_header_at_64_chars(self):
        # Arrange
        middleware, response = _make_middleware()
        long_id = 'X' * 200
        request = MagicMock()
        request.META = {'HTTP_X_REQUEST_ID': long_id}
        # Act
        middleware(request)
        # Assert
        assert len(request.request_id) == 64
        assert request.request_id == 'X' * 64

    def test_blank_header_falls_back_to_uuid(self):
        # Arrange
        middleware, response = _make_middleware()
        request = MagicMock()
        request.META = {'HTTP_X_REQUEST_ID': '   '}
        # Act
        middleware(request)
        # Assert — empty/whitespace header should not be propagated
        assert UUID_HEX_RE.match(request.request_id)
