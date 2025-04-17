from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    register_manager, ManagerTokenObtainPairView,
    register_client, ManagerViewSet, LogViewSet
)

router = DefaultRouter()
router.register(r'manager', ManagerViewSet, basename='manager')
router.register(r'logs', LogViewSet, basename='logs')

urlpatterns = [
    path('register-manager/', register_manager),
    path('token/', ManagerTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('register-client/', register_client),
    path('', include(router.urls)),
]