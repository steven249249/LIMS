"""backend/urls.py – Root URL configuration."""
from django.contrib import admin
from django.urls import path, include

from . import health

urlpatterns = [
    # Kubernetes probes — unauthenticated, intentionally cheap.
    path('healthz', health.healthz, name='healthz'),
    path('readyz', health.readyz, name='readyz'),
    # Prometheus scrape target. NetworkPolicy keeps it cluster-internal in
    # production; in dev it's harmless to expose.
    path('', include('django_prometheus.urls')),

    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/equipments/', include('equipments.urls')),
    path('api/scheduling/', include('scheduling.urls')),
    path('api/monitoring/', include('monitoring.urls')),
    path('api/admin/', include('admin_api.urls')),
]
