import json
import logging
import time

from .models import ActivityLog

logger = logging.getLogger(__name__)

EXCLUDED_PATH_PREFIXES = ('/static/', '/media/', '/favicon')
SENSITIVE_FIELD_NAMES = {'password', 'old_password', 'new_password', 'token', 'access', 'refresh'}
MAX_REQUEST_DATA_BYTES = 8 * 1024  # Skip oversized bodies (file uploads etc.)

ACTION_BY_METHOD = {
    'POST': ActivityLog.ActionType.CREATE,
    'GET': ActivityLog.ActionType.READ,
    'PUT': ActivityLog.ActionType.UPDATE,
    'PATCH': ActivityLog.ActionType.UPDATE,
    'DELETE': ActivityLog.ActionType.DELETE,
}


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _redact(payload):
    if isinstance(payload, dict):
        return {
            key: ('***REDACTED***' if key.lower() in SENSITIVE_FIELD_NAMES else _redact(value))
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [_redact(item) for item in payload]
    return payload


def _classify(request):
    path = request.path
    if request.method == 'POST' and ('login' in path or 'token' in path):
        return ActivityLog.ActionType.LOGIN
    if 'logout' in path:
        return ActivityLog.ActionType.LOGOUT
    return ACTION_BY_METHOD.get(request.method, ActivityLog.ActionType.OTHER)


class ActivityLogMiddleware:
    """Persists every API request to ``ActivityLog`` for the admin audit trail.

    Failures here are swallowed: logging must never break the request pipeline.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(prefix) for prefix in EXCLUDED_PATH_PREFIXES):
            return self.get_response(request)

        started_at = time.monotonic()
        request_body = self._read_body(request)

        response = self.get_response(request)

        try:
            self._record(request, response, request_body, started_at)
        except Exception:
            logger.exception('ActivityLogMiddleware failed to record request')

        return response

    @staticmethod
    def _read_body(request):
        if request.method not in ('POST', 'PUT', 'PATCH'):
            return None
        body = request.body
        if not body or len(body) > MAX_REQUEST_DATA_BYTES:
            return None
        try:
            return json.loads(body)
        except (ValueError, UnicodeDecodeError):
            return None

    @staticmethod
    def _record(request, response, request_body, started_at):
        ActivityLog.objects.create(
            user=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
            action_type=_classify(request),
            http_method=request.method,
            path=request.path[:255],
            status_code=response.status_code,
            ip_address=_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:512],
            request_data=_redact(request_body) if request_body else None,
            request_id=getattr(request, 'request_id', '')[:64],
            duration_ms=int((time.monotonic() - started_at) * 1000),
        )
