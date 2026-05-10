"""Logging filter that injects correlation IDs onto every record.

Adds three fields:

* ``request_id`` — set by :class:`~utils.request_id.RequestIDMiddleware`
  on the active request. Empty string outside a request context.
* ``trace_id`` / ``span_id`` — pulled from the active OpenTelemetry span
  if the ``opentelemetry`` SDK is initialised, empty string otherwise.

Pure-stdlib fallback so it works even when OTel isn't installed (e.g. in
tests).
"""
import logging
import contextvars

# RequestIDMiddleware sets ``request.request_id``; we mirror it into a
# ContextVar so log statements outside the request handler still see it.
request_id_var = contextvars.ContextVar('request_id', default='')


class CorrelationFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(record, 'request_id', '') or request_id_var.get()
        trace_id = ''
        span_id = ''
        try:
            from opentelemetry import trace
            ctx = trace.get_current_span().get_span_context()
            if ctx.is_valid:
                trace_id = format(ctx.trace_id, '032x')
                span_id = format(ctx.span_id, '016x')
        except Exception:  # pragma: no cover — OTel not installed or not init'd
            pass
        record.trace_id = trace_id
        record.span_id = span_id
        return True
