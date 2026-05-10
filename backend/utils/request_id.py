"""Request-correlation middleware.

Assigns a UUID to every incoming request and surfaces it on:

  * ``request.request_id`` — for downstream views, exception handlers, logging
  * ``response['X-Request-ID']`` — so frontend / proxies can echo it back
  * ActivityLog records via ``ActivityLogMiddleware``

If the upstream proxy already supplies ``X-Request-ID``, we honour it (capped
at 64 chars) so traces stitch across the edge.
"""
import uuid

from .logging_filters import request_id_var

REQUEST_ID_HEADER = 'HTTP_X_REQUEST_ID'
RESPONSE_HEADER = 'X-Request-ID'
MAX_LENGTH = 64


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.META.get(REQUEST_ID_HEADER, '').strip()[:MAX_LENGTH]
        request.request_id = incoming or uuid.uuid4().hex
        # Mirror onto a ContextVar so log records outside the view (e.g. in
        # services / signals) still inherit the correlation ID.
        token = request_id_var.set(request.request_id)
        try:
            response = self.get_response(request)
        finally:
            request_id_var.reset(token)
        response[RESPONSE_HEADER] = request.request_id
        return response
