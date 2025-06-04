# urls.py
# Здесь будут маршруты (endpoints) для API
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    register_manager,
    ManagerTokenObtainPairView,
    PolicyViewSet,
    ReportViewSet,
    get_manager_profile,
    get_manager_blacklist,
    ClientAgentViewSet,
    client_heartbeat,
    get_client_policy,
    add_to_blacklist,
    remove_from_blacklist,
    get_manager_violations,
    get_manager_clients,
    get_client_blacklist,
    get_violation_logs,
    report_violation,
    delete_client,
    process_report,
)

router = DefaultRouter()
router.register(r'manager/clients', ClientAgentViewSet, basename='client')
router.register(r'policy', PolicyViewSet, basename='policy')

urlpatterns = [
    path('', include(router.urls)),
    path('manager/register/', register_manager, name='register_manager'),
    path('manager/token/', ManagerTokenObtainPairView.as_view(), name='manager_token'),
    path('manager/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('manager/profile/', get_manager_profile, name='manager_profile'),
    path('manager/clients/', get_manager_clients, name='manager_clients'),
    path('manager/clients/<uuid:client_uuid>/delete/', delete_client, name='delete_client'),
    path('manager/clients/<uuid:client_uuid>/policy/', get_client_policy, name='client_policy'),
    path('manager/clients/<uuid:client_uuid>/logs/', get_violation_logs, name='client_logs'),
    path('manager/violations/<uuid:manager_uuid>/', get_manager_violations, name='manager_violations'),
    path('manager/blacklist/add/', add_to_blacklist, name='add_to_blacklist'),
    path('manager/blacklist/remove/', remove_from_blacklist, name='remove_from_blacklist'),
    path('clients/', ClientAgentViewSet.as_view({'post': 'create'}), name='client-register'),
    path('clients/token/', ClientAgentViewSet.as_view({'post': 'token'}), name='client-token'),
    path('clients/<uuid:client_uuid>/policy/', get_client_policy, name='client-policy'),
    path('clients/<uuid:client_uuid>/heartbeat/', client_heartbeat, name='client-heartbeat'),
    path('report/', process_report, name='process_report'),
]