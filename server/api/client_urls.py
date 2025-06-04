"""
Дополнительные URL маршруты для клиентов
"""
from django.urls import path
from .client_status_view import check_client_status

urlpatterns = [
    path('clients/<uuid:client_uuid>/status/', check_client_status, name='check_client_status'),
]