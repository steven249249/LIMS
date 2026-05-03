"""Project-wide DRF exception handler.

Produces a uniform JSON envelope so frontend code can rely on a single shape:

    {
        "detail": "Human-readable summary",
        "code": "machine_code",
        "fields": {<field>: [<error>, ...]},   # only on validation errors
        "request_id": "<uuid>",                # if available
    }

Unhandled exceptions never leak stack traces to clients — they are logged,
optionally forwarded to Sentry, and a generic 500 is returned.
"""
import logging

from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Wrap DRF responses in a uniform envelope; mask 5xx tracebacks."""
    request = context.get('request')
    request_id = getattr(request, 'request_id', None) if request else None

    response = drf_exception_handler(exc, context)

    if response is not None:
        return _shape_drf_response(exc, response, request_id)

    # Anything DRF doesn't know about is a server error: log, never leak.
    logger.exception(
        'Unhandled exception in view',
        extra={'request_id': request_id, 'path': getattr(request, 'path', None)},
    )
    return Response(
        {
            'detail': 'An internal error occurred. Please contact support if this persists.',
            'code': 'server_error',
            'request_id': request_id,
        },
        status=500,
    )


def _shape_drf_response(exc, response, request_id):
    data = response.data

    if isinstance(exc, ValidationError):
        envelope = {
            'detail': 'Validation failed.',
            'code': 'validation_error',
            'fields': data if isinstance(data, dict) else {'non_field_errors': data},
        }
    elif isinstance(exc, APIException):
        envelope = {
            'detail': str(exc.detail) if not isinstance(exc.detail, dict) else 'Request failed.',
            'code': getattr(exc, 'default_code', 'error'),
        }
        if isinstance(exc.detail, dict):
            envelope['fields'] = exc.detail
    else:
        envelope = {
            'detail': data.get('detail', 'Request failed.') if isinstance(data, dict) else str(data),
            'code': 'error',
        }

    if request_id:
        envelope['request_id'] = request_id

    response.data = envelope
    return response
