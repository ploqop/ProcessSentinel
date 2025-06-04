"""
Обновленные URL маршруты с добавлением отчетов и аудита
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    register_manager,
    ManagerTokenObtainPairView,
    ClientViewSet,
    PolicyViewSet,
    ReportViewSet,
    get_manager_profile,
    get_manager_blacklist,
    ClientAgentViewSet
)
from .report_views import (
    generate_report,
    get_reports,
    get_report,
    export_report,
    get_audit_logs
)
from .modified_views import (
    register_client,
    add_to_blacklist,
    client_heartbeat,
    report_violation,
    delete_client
)

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'policy', PolicyViewSet, basename='policy')
router.register(r'report', ReportViewSet, basename='report')
router.register(r'manager/clients', ClientAgentViewSet, basename='manager-clients')

urlpatterns = [
    path('', include(router.urls)),
    
    # Существующие маршруты
    path('manager/register/', register_manager, name='register_manager'),
    path('manager/token/', ManagerTokenObtainPairView.as_view(), name='manager_token'),
    path('manager/profile/', get_manager_profile, name='get_manager_profile'),
    path('manager/blacklist/', get_manager_blacklist, name='get_manager_blacklist'),
    
    # Обновленные маршруты с логированием
    path('register-client/', register_client, name='register_client'),
    path('blacklist/add/', add_to_blacklist, name='add_to_blacklist'),
    path('client/heartbeat/', client_heartbeat, name='client_heartbeat'),
    path('client/violation/', report_violation, name='report_violation'),
    path('client/<uuid:client_uuid>/delete/', delete_client, name='delete_client'),
    
    # Новые маршруты для отчетов и аудита
    path('reports/generate/', generate_report, name='generate_report'),
    path('reports/', get_reports, name='get_reports'),
    path('reports/<uuid:report_id>/', get_report, name='get_report'),
    path('reports/<uuid:report_id>/export/<str:format>/', export_report, name='export_report'),
    path('audit/logs/', get_audit_logs, name='get_audit_logs'),
]