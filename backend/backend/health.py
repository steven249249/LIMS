"""Liveness + readiness probes for Kubernetes.

Two endpoints, intentionally cheap and unauthenticated:

* ``/healthz`` — liveness. Returns 200 as long as the process is up. No
  external calls. Kubernetes uses this to decide if a pod should be
  killed and rescheduled.
* ``/readyz`` — readiness. Pings the DB and Redis. Returns 503 if either
  is unreachable, so Kubernetes pulls the pod out of the load-balancer
  rotation without killing it.

These are mounted at the root of the URL tree (not under ``/api``) so an
ingress / probe doesn't need to know about app prefixes.
"""
from django.db import connection
from django.http import JsonResponse


def healthz(_request):
    """Liveness — process is responsive. No backing-service checks."""
    return JsonResponse({'status': 'ok'})


def readyz(_request):
    """Readiness — DB + Redis reachable. Returns 503 if any check fails."""
    checks = {}
    overall_ok = True

    try:
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
        checks['database'] = 'ok'
    except Exception as exc:
        checks['database'] = f'fail: {exc.__class__.__name__}'
        overall_ok = False

    try:
        from django.core.cache import cache
        cache.set('readyz-probe', '1', timeout=5)
        if cache.get('readyz-probe') != '1':
            raise RuntimeError('redis round-trip mismatch')
        checks['redis'] = 'ok'
    except Exception as exc:
        checks['redis'] = f'fail: {exc.__class__.__name__}'
        overall_ok = False

    return JsonResponse(
        {'status': 'ready' if overall_ok else 'fail', 'checks': checks},
        status=200 if overall_ok else 503,
    )
