"""backend/urls.py – Root URL configuration."""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/equipments/', include('equipments.urls')),
    path('api/scheduling/', include('scheduling.urls')),
    path('api/monitoring/', include('monitoring.urls')),
    path('api/admin/', include('admin_api.urls')),
]
