from django.db import models
import uuid
from .models import ClientAgent, ManagerProfile

class AuditLog(models.Model):
    """Модель для хранения всех событий системы для аудита."""
    LOG_TYPES = [
        ('client_registration', 'Регистрация клиента'),
        ('client_connection', 'Подключение клиента'),
        ('client_disconnection', 'Отключение клиента'),
        ('policy_update', 'Обновление политики'),
        ('policy_violation', 'Нарушение политики'),
        ('command_sent', 'Отправка команды'),
        ('command_executed', 'Выполнение команды'),
        ('login_attempt', 'Попытка входа'),
        ('manager_registration', 'Регистрация менеджера'),
        ('client_deletion', 'Удаление клиента'),
        ('heartbeat', 'Сигнал активности'),
        ('error', 'Ошибка')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(ClientAgent, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs')
    manager = models.ForeignKey(ManagerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs')
    log_type = models.CharField(max_length=50, choices=LOG_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['log_type']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['client']),
            models.Index(fields=['manager']),
        ]
    
    def __str__(self):
        client_str = f"Client: {self.client.name}" if self.client else "No client"
        manager_str = f"Manager: {self.manager.user.username}" if self.manager else "No manager"
        return f"{self.log_type} - {self.timestamp} - {client_str} - {manager_str}"

class Report(models.Model):
    """Модель для хранения сгенерированных отчетов."""
    REPORT_TYPES = [
        ('client_activity', 'Активность клиентов'),
        ('policy_violations', 'Нарушения политик'),
        ('commands_execution', 'Выполнение команд'),
        ('system_health', 'Состояние системы')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manager = models.ForeignKey(ManagerProfile, on_delete=models.CASCADE, related_name='reports')
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    parameters = models.JSONField(default=dict)  # Параметры для генерации отчета
    result = models.JSONField(default=dict)  # Результаты отчета
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.report_type} - {self.created_at} - Manager: {self.manager.user.username}"