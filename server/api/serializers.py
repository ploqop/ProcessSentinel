# serializers.py
# Здесь будут сериализаторы для моделей API 
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ManagerProfile, ClientAgent, Policy, Command, Log, Report

class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для стандартной модели пользователя Django."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        read_only_fields = ['id']

class ManagerProfileSerializer(serializers.ModelSerializer):
    """Сериализатор для профиля менеджера."""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    clients_count = serializers.SerializerMethodField()

    class Meta:
        model = ManagerProfile
        fields = ['uuid', 'username', 'email', 'created_at', 'clients_count']
        read_only_fields = ['uuid', 'created_at']

    def get_clients_count(self, obj):
        return obj.clients.count()

class ClientAgentSerializer(serializers.ModelSerializer):
    """Сериализатор для клиентского агента."""
    manager_username = serializers.CharField(source='manager.user.username', read_only=True)
    is_online = serializers.BooleanField(read_only=True)
    last_heartbeat = serializers.DateTimeField(read_only=True, format="%Y-%m-%dT%H:%M:%S.%fZ")
    last_seen = serializers.DateTimeField(read_only=True, format="%Y-%m-%dT%H:%M:%S.%fZ")
    created_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S.%fZ")

    class Meta:
        model = ClientAgent
        fields = ['uuid', 'name', 'manager_username', 'created_at', 
                 'is_online', 'last_heartbeat', 'last_seen']
        read_only_fields = ['uuid', 'created_at']

class PolicySerializer(serializers.ModelSerializer):
    """Сериализатор для политики доступа."""
    manager_username = serializers.CharField(source='manager.user.username', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True, allow_null=True)
    client_uuid = serializers.UUIDField(source='client.uuid', read_only=True, allow_null=True)

    class Meta:
        model = Policy
        fields = ['id', 'process_name', 'action', 'created_at', 'is_active',
                 'manager_username', 'client_name', 'client_uuid']
        read_only_fields = ['id', 'created_at']

class CommandSerializer(serializers.ModelSerializer):
    """Сериализатор для команд."""
    client_name = serializers.CharField(source='client.name', read_only=True)
    client_uuid = serializers.UUIDField(source='client.uuid', read_only=True)

    class Meta:
        model = Command
        fields = ['id', 'client_uuid', 'client_name', 'command_type', 
                 'parameters', 'sent_at', 'executed', 'result']
        read_only_fields = ['id', 'sent_at']

class LogSerializer(serializers.ModelSerializer):
    """Сериализатор для логов."""
    client_name = serializers.CharField(source='client.name', read_only=True)
    client_uuid = serializers.UUIDField(source='client.uuid', read_only=True)

    class Meta:
        model = Log
        fields = ['id', 'client_uuid', 'client_name', 'event', 
                 'data', 'timestamp', 'level']
        read_only_fields = ['id', 'timestamp']

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['id', 'client', 'event_type', 'process_name', 'process_id', 
                 'timestamp', 'system_stats', 'created_at']
        read_only_fields = ['id', 'created_at'] 