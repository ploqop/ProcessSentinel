from django.db import models
from django.contrib.auth.models import User
import uuid

class ManagerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='manager_profile')
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Manager {self.user.username} ({self.uuid})"

class ClientAgent(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    manager = models.ForeignKey(ManagerProfile, on_delete=models.SET_NULL, null=True, related_name='clients')
    name = models.CharField(max_length=100, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

class Command(models.Model):
    client = models.ForeignKey(ClientAgent, on_delete=models.CASCADE, related_name='commands')
    text = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    executed = models.BooleanField(default=False)
    result = models.TextField(blank=True)

class Log(models.Model):
    client = models.ForeignKey(ClientAgent, on_delete=models.CASCADE, related_name='logs')
    event = models.CharField(max_length=100)
    data = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)