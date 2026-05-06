from rest_framework.routers import DefaultRouter

from . import views

app_name = 'admin_api'

router = DefaultRouter()
router.register(r'fabs', views.FABViewSet, basename='admin-fab')
router.register(r'departments', views.DepartmentViewSet, basename='admin-department')
router.register(r'wafer-lots', views.WaferLotViewSet, basename='admin-wafer-lot')
router.register(r'users', views.UserViewSet, basename='admin-user')
router.register(r'experiments', views.ExperimentViewSet, basename='admin-experiment')
router.register(r'equipment-types', views.EquipmentTypeViewSet, basename='admin-equipment-type')
router.register(r'equipment', views.EquipmentViewSet, basename='admin-equipment')
router.register(
    r'experiment-requirements',
    views.ExperimentRequiredEquipmentViewSet,
    basename='admin-experiment-requirement',
)
router.register(r'orders', views.OrderViewSet, basename='admin-order')
router.register(r'order-stages', views.OrderStageViewSet, basename='admin-order-stage')
router.register(r'bookings', views.EquipmentBookingViewSet, basename='admin-booking')

urlpatterns = router.urls
