"""
Модифицированные представления с добавленным логированием
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from datetime import datetime

from .models import ClientAgent, Policy
from .audit_logger import log_event, log_error

@api_view(['POST'])
@permission_classes([AllowAny])
def register_client(request):
    """Регистрация нового клиента с логированием."""
    manager_uuid = request.data.get('manager_uuid')
    name = request.data.get('name', '')
    
    if not manager_uuid:
        log_error('Manager UUID is required for client registration', 
                 None, None, {'request_data': request.data}, request)
        return Response(
            {'error': 'Manager UUID is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        from .models import ManagerProfile
        manager = ManagerProfile.objects.get(uuid=manager_uuid)
    except ManagerProfile.DoesNotExist:
        log_error('Manager not found during client registration', 
                 None, None, {'manager_uuid': manager_uuid}, request)
        return Response(
            {'error': 'Manager not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if a client with this name already exists for this manager
    existing_client = ClientAgent.objects.filter(manager=manager, name=name).first()
    if existing_client:
        # Логируем повторную попытку регистрации
        log_event('client_registration_attempt', existing_client, manager, 
                 {'status': 'already_exists'}, request)
        
        return Response({
            'client_uuid': existing_client.uuid,
            'name': existing_client.name,
            'message': 'Client already registered'
        }, status=status.HTTP_200_OK)
    
    # Create a new client
    client = ClientAgent.objects.create(manager=manager, name=name)
    
    # Логируем успешную регистрацию
    log_event('client_registration', client, manager, 
             {'status': 'success'}, request)
    
    return Response({
        'client_uuid': client.uuid,
        'name': client.name
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_blacklist(request):
    """Добавление процесса в черный список с логированием."""
    process_name = request.data.get('process_name')
    client_uuid = request.data.get('client_uuid')  # UUID клиента или None для общего правила
    
    if not process_name:
        log_error('Process name is required for blacklist', 
                 None, request.user.manager_profile, {'request_data': request.data}, request)
        return Response(
            {"error": "process_name is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    client = None
    if client_uuid:
        try:
            client = ClientAgent.objects.get(
                uuid=client_uuid, 
                manager=request.user.manager_profile
            )
        except ClientAgent.DoesNotExist:
            log_error('Client not found for blacklist addition', 
                     None, request.user.manager_profile, 
                     {'client_uuid': client_uuid, 'process_name': process_name}, request)
            return Response(
                {"error": "Client not found or access denied"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Создаем или активируем существующую политику
    policy, created = Policy.objects.get_or_create(
        manager=request.user.manager_profile,
        client=client,
        process_name=process_name,
        defaults={'action': 'block', 'is_active': True}
    )
    
    if not created:
        policy.is_active = True
        policy.save()
    
    # Логируем добавление в черный список
    log_event('policy_update', client, request.user.manager_profile, 
             {'action': 'add_to_blacklist', 'process_name': process_name, 'policy_id': policy.id}, 
             request)
    
    from .serializers import PolicySerializer
    return Response(PolicySerializer(policy).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def client_heartbeat(request):
    """Обработка сигнала активности клиента с логированием."""
    client_uuid = request.data.get('client_uuid')
    processes = request.data.get('processes', [])
    system_stats = request.data.get('system_stats', {})
    
    if not client_uuid:
        log_error('Client UUID is required for heartbeat', 
                 None, None, {'request_data': request.data}, request)
        return Response(
            {"error": "client_uuid is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        client = ClientAgent.objects.get(uuid=client_uuid)
    except ClientAgent.DoesNotExist:
        log_error('Client not found for heartbeat', 
                 None, None, {'client_uuid': client_uuid}, request)
        return Response(
            {"error": "Client not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Обновляем статус клиента
    client.last_heartbeat = datetime.now()
    client.is_online = True
    client.save()
    
    # Логируем heartbeat
    log_event('heartbeat', client, client.manager, 
             {'processes_count': len(processes), 'system_stats': system_stats}, 
             request)
    
    return Response({"status": "success"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_violation(request):
    """Отчет о нарушении политики с логированием."""
    client_uuid = request.data.get('client_uuid')
    process_name = request.data.get('process_name')
    process_id = request.data.get('process_id')
    
    if not client_uuid or not process_name:
        log_error('Client UUID and process name are required for violation report', 
                 None, None, {'request_data': request.data}, request)
        return Response(
            {"error": "client_uuid and process_name are required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        client = ClientAgent.objects.get(uuid=client_uuid)
    except ClientAgent.DoesNotExist:
        log_error('Client not found for violation report', 
                 None, None, {'client_uuid': client_uuid}, request)
        return Response(
            {"error": "Client not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Логируем нарушение
    log_event('policy_violation', client, client.manager, 
             {'process_name': process_name, 'process_id': process_id}, 
             request)
    
    return Response({"status": "success"})

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_client(request, client_uuid):
    """Удаление клиента с логированием."""
    try:
        # Get the client that belongs to the current manager
        client = ClientAgent.objects.get(uuid=client_uuid, manager=request.user.manager_profile)
        
        # Store client name for response
        client_name = client.name or str(client.uuid)
        
        # Логируем удаление клиента
        log_event('client_deletion', client, request.user.manager_profile, 
                 {'client_name': client_name}, request)
        
        # Delete the client (this will also delete related policies through CASCADE)
        client.delete()
        
        return Response({
            'success': True,
            'message': f'Client {client_name} deleted successfully'
        }, status=status.HTTP_200_OK)
    except ClientAgent.DoesNotExist:
        log_error('Client not found for deletion', 
                 None, request.user.manager_profile, {'client_uuid': client_uuid}, request)
        return Response({
            'error': 'Client not found or you do not have permission to delete it'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        log_error(f'Error deleting client: {str(e)}', 
                 None, request.user.manager_profile, {'client_uuid': client_uuid}, request)
        return Response({
            'error': f'Error deleting client: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)