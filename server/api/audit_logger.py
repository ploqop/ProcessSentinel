"""
Утилита для централизованного логирования событий
"""
import logging
from .models_extension import AuditLog

logger = logging.getLogger(__name__)

def log_event(log_type, client=None, manager=None, details=None, request=None):
    """
    Записывает событие в систему аудита.
    
    Args:
        log_type (str): Тип события из AuditLog.LOG_TYPES
        client (ClientAgent): Объект клиента или None
        manager (ManagerProfile): Объект менеджера или None
        details (dict): Дополнительные данные о событии
        request (HttpRequest): Объект запроса для получения IP
    
    Returns:
        AuditLog: Созданный объект лога
    """
    try:
        if details is None:
            details = {}
        
        ip_address = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
        
        # Создаем запись лога
        log_entry = AuditLog.objects.create(
            client=client,
            manager=manager,
            log_type=log_type,
            details=details,
            ip_address=ip_address
        )
        
        logger.info(f"Audit log created: {log_type} - Client: {client} - Manager: {manager}")
        return log_entry
    
    except Exception as e:
        logger.error(f"Failed to create audit log: {str(e)}")
        # В случае ошибки логирования не должно прерывать основной процесс
        return None

def log_error(error_message, client=None, manager=None, details=None, request=None):
    """
    Записывает ошибку в систему аудита.
    
    Args:
        error_message (str): Сообщение об ошибке
        client (ClientAgent): Объект клиента или None
        manager (ManagerProfile): Объект менеджера или None
        details (dict): Дополнительные данные об ошибке
        request (HttpRequest): Объект запроса для получения IP
    """
    if details is None:
        details = {}
    
    details['error_message'] = error_message
    return log_event('error', client, manager, details, request)