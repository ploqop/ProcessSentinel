from rest_framework import serializers
from .models_extension import AuditLog, Report

class AuditLogSerializer(serializers.ModelSerializer):
    """Сериализатор для логов аудита."""
    client_name = serializers.CharField(source='client.name', read_only=True, allow_null=True)
    client_uuid = serializers.UUIDField(source='client.uuid', read_only=True, allow_null=True)
    manager_username = serializers.CharField(source='manager.user.username', read_only=True, allow_null=True)
    log_type_display = serializers.CharField(source='get_log_type_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = ['id', 'log_type', 'log_type_display', 'timestamp', 'details', 'ip_address',
                 'client_name', 'client_uuid', 'manager_username']
        read_only_fields = ['id', 'timestamp']

class ReportSerializer(serializers.ModelSerializer):
    """Сериализатор для отчетов."""
    manager_username = serializers.CharField(source='manager.user.username', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    
    class Meta:
        model = Report
        fields = ['id', 'report_type', 'report_type_display', 'parameters', 'result',
                 'created_at', 'start_date', 'end_date', 'manager_username']
        read_only_fields = ['id', 'created_at']