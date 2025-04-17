from rest_framework import serializers
from .models import ManagerProfile, ClientAgent, Command, Log
from django.contrib.auth.models import User

class ManagerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerProfile
        fields = ['uuid', 'created_at']

class ClientAgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientAgent
        fields = ['uuid', 'name', 'registered_at']

class CommandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Command
        fields = ['id', 'client', 'text', 'sent_at', 'executed', 'result']

class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = ['id', 'client', 'event', 'data', 'timestamp']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']