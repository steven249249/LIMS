from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    # Auth — public registration is intentionally not exposed. New accounts
    # are provisioned by superusers via /api/admin/users/ (single create) or
    # /api/admin/users/bulk-create/ (batched provisioning).
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    # Lookup
    path('fabs/', views.FABListView.as_view(), name='fab-list'),
    path('departments/', views.DepartmentListView.as_view(), name='department-list'),
    path('wafer-lots/', views.WaferLotListView.as_view(), name='wafer-lot-list'),
    path('', views.UserListView.as_view(), name='user-list'),
]
