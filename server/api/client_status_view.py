"""
Представление для проверки статуса клиента
"""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import ClientAgent
from .audit_logger import log_event

@api_view(['GET'])
def check_client_status(request, client_uuid):
    """
    Проверяет статус клиента на сервере.
    
    Этот эндпоинт используется клиентским агентом для проверки,
    существует ли он на сервере и привязан ли к менеджеру.
    
    Args:
        request: HTTP запрос
        client_uuid: UUID клиента
        
    Returns:
        Response: Ответ с информацией о статусе клиента
    """
    try:
        # Проверяем существование клиента
        client = ClientAgent.objects.filter(uuid=client_uuid).first()
        
        if client:
            # Проверяем, привязан ли клиент к менеджеру
            is_registered = client.manager is not None
            
            # Логируем проверку статуса
            log_event('client_status_check', client, client.manager if is_registered else None, 
                     {'is_registered': is_registered}, request)
            
            return Response({
                'client_uuid': str(client.uuid),
                'name': client.name,
                'is_registered': is_registered,
                'last_heartbeat': client.last_heartbeat.isoformat() if client.last_heartbeat else None,
                'is_online': client.is_online
            })
        else:
            # Клиент не найден
            return Response({
                'error': 'Client not found',
                'is_registered': False
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({
            'error': f'Error checking client status: {str(e)}',
            'is_registered': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)