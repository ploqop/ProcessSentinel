from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.utils import timezone
import uuid
from django.conf import settings

class ManagerProfile(models.Model):
    """Профиль менеджера, расширяет стандартного пользователя Django."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='manager_profile'
    )
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    department = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.position}"

    class Meta:
        verbose_name = 'Manager Profile'
        verbose_name_plural = 'Manager Profiles'

class ClientAgent(models.Model):
    """Модель клиентского агента."""
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    manager = models.ForeignKey(ManagerProfile, on_delete=models.CASCADE, related_name='clients')
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.uuid})"

class Policy(models.Model):
    client = models.ForeignKey(ClientAgent, on_delete=models.CASCADE, related_name='policies', null=True, blank=True)
    manager = models.ForeignKey(ManagerProfile, on_delete=models.CASCADE, related_name='policies', null=True, blank=True)
    blacklist = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    action = models.CharField(max_length=20, choices=[
        ('block', 'Block'),
        ('allow', 'Allow')
    ], default='block')

    def __str__(self):
        return f"Policy for {self.client.name if self.client else 'Global'}"

    def add_to_blacklist(self, process_name):
        """Add a process to the blacklist."""
        if not isinstance(self.blacklist, list):
            self.blacklist = []
        if process_name not in self.blacklist:
            self.blacklist.append(process_name)
            self.save()

    def remove_from_blacklist(self, process_name):
        """Remove a process from the blacklist."""
        if isinstance(self.blacklist, list) and process_name in self.blacklist:
            self.blacklist.remove(process_name)
            if not self.blacklist:
                self.is_active = False
            self.save()
            return True
        return False

class Report(models.Model):
    client = models.ForeignKey(ClientAgent, on_delete=models.CASCADE, related_name='reports')
    event_type = models.CharField(max_length=50)  # 'violation' или 'heartbeat'
    process_name = models.CharField(max_length=255, null=True, blank=True)
    process_id = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField()
    system_stats = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} from {self.client.name} at {self.timestamp}"

class Command(models.Model):
    """Команда для клиента (например, завершить процесс)."""
    client = models.ForeignKey(ClientAgent, on_delete=models.CASCADE, related_name='commands')
    command_type = models.CharField(max_length=50, choices=[
        ('terminate_process', 'Terminate Process'),
        ('update_policy', 'Update Policy'),
        ('get_process_list', 'Get Process List')
    ])
    parameters = models.JSONField(default=dict)
    sent_at = models.DateTimeField(auto_now_add=True)
    executed = models.BooleanField(default=False)
    result = models.TextField(blank=True)

    def __str__(self):
        return f"Command {self.command_type} for {self.client}"

class Log(models.Model):
    """Лог событий клиента."""
    client = models.ForeignKey(ClientAgent, on_delete=models.CASCADE, related_name='logs')
    event = models.CharField(max_length=100)
    data = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=20, choices=[
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error')
    ], default='info')

    def __str__(self):
        return f"{self.event} from {self.client} at {self.timestamp}"
