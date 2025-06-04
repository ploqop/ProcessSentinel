from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.models import User
from django.utils import timezone
from .models import ManagerProfile, ClientAgent, Policy, Command, Log, Report
from .serializers import (
    ManagerProfileSerializer, ClientAgentSerializer,
    PolicySerializer, CommandSerializer, LogSerializer,
    ReportSerializer
)
import uuid
import hashlib
from rest_framework.authtoken.models import Token
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken

# Create your views here.

@api_view(['POST'])
@permission_classes([AllowAny])
def register_manager(request):
    """Регистрация нового менеджера."""
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        print(f"Attempting to register manager with username: {username}")
        
        if not username or not password:
            return Response(
                {'error': 'Username and password are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Username already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Создаем пользователя
            print("Creating user...")
            user = User.objects.create_user(username=username, password=password)
            print(f"User created with ID: {user.id}")
            
            # Создаем профиль менеджера
            print("Creating manager profile...")
            manager_profile = ManagerProfile.objects.create(
                user=user,
                department='Default',
                position='Manager'
            )
            print(f"Manager profile created with UUID: {manager_profile.uuid}")
            
            # Генерируем JWT токены
            print("Generating JWT tokens...")
            refresh = RefreshToken.for_user(user)
            print("JWT tokens generated successfully")
            
            return Response({
                'uuid': str(manager_profile.uuid),
                'username': username,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"Error during user/manager creation: {str(e)}")
            # Если что-то пошло не так, удаляем созданного пользователя
            if 'user' in locals():
                print(f"Cleaning up: deleting user {user.id}")
                user.delete()
            raise e
            
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class ManagerTokenObtainPairView(TokenObtainPairView):
    """Получение JWT токена для менеджера."""
    permission_classes = [AllowAny]

@api_view(['POST'])
@permission_classes([AllowAny])  # Разрешаем доступ без аутентификации
def client_heartbeat(request, client_uuid):
    """Обновление статуса клиента от клиентского приложения."""
    try:
        client = ClientAgent.objects.get(uuid=client_uuid)
        data = request.data
        
        # Обновляем статус клиента
        client.is_online = True
        client.last_seen = timezone.now()
        client.save()
        
        return Response({
            'status': 'success',
            'message': 'Heartbeat received'
        }, status=status.HTTP_200_OK)
    except ClientAgent.DoesNotExist:
        return Response(
            {'error': 'Client not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class ClientAgentViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с клиентами."""
    queryset = ClientAgent.objects.all()
    serializer_class = ClientAgentSerializer
    lookup_field = 'uuid'

    def get_permissions(self):
        """Разрешаем регистрацию и получение токена без аутентификации."""
        if self.action in ['create', 'token']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Получаем только клиентов текущего менеджера."""
        if self.action in ['create', 'token']:
            return ClientAgent.objects.all()
        try:
            manager = self.request.user.manager_profile
            return ClientAgent.objects.filter(manager=manager)
        except:
            return ClientAgent.objects.none()

    def retrieve(self, request, *args, **kwargs):
        """Получение деталей клиента."""
        try:
            # Получаем UUID из URL параметров
            client_uuid = kwargs.get('uuid')
            if not client_uuid:
                print("No UUID provided in request")
                return Response(
                    {'error': 'Client UUID is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            print(f"Attempting to retrieve client with UUID: {client_uuid}")
            
            # Получаем клиента по UUID
            client = ClientAgent.objects.get(uuid=client_uuid)
            print(f"Found client: {client.name} (UUID: {client.uuid})")
            
            # Проверяем, что клиент принадлежит менеджеру
            if client.manager != request.user.manager_profile:
                print(f"Access denied: Client belongs to manager {client.manager.uuid}, but request from {request.user.manager_profile.uuid}")
                return Response(
                    {'error': 'You do not have permission to access this client'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Сериализуем данные клиента
            serializer = self.get_serializer(client)
            return Response(serializer.data)
            
        except ClientAgent.DoesNotExist:
            print(f"Client not found with UUID: {client_uuid}")
            return Response(
                {'error': 'Client not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Error retrieving client: {str(e)}")
            return Response(
                {'error': f'Error retrieving client data: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """Удаление клиента."""
        try:
            instance = self.get_object()
            # Проверяем, что клиент принадлежит менеджеру
            if instance.manager != request.user.manager_profile:
                return Response(
                    {'error': 'You do not have permission to delete this client'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_404_NOT_FOUND
            )

    def create(self, request):
        """Регистрация нового клиента."""
        manager_uuid = request.data.get('manager_uuid')
        client_name = request.data.get('name', 'Unknown Client')
        client_uuid = request.data.get('uuid')
        
        if not manager_uuid:
            return Response(
                {'error': 'manager_uuid is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            manager = ManagerProfile.objects.get(uuid=manager_uuid)
            
            # Если передан UUID, проверяем существующего клиента
            if client_uuid:
                try:
                    client = ClientAgent.objects.get(uuid=client_uuid)
                    if client.manager != manager:
                        return Response(
                            {'error': 'Client already registered with different manager'}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    # Обновляем существующего клиента
                    client.name = client_name
                    client.is_online = True
                    client.last_seen = timezone.now()
                    client.last_heartbeat = timezone.now()
                    client.save()
                    
                    # Создаем или обновляем токен
                    if not client.user:
                        username = f"client_{client.uuid}"
                        user = User.objects.create_user(username=username, password=None)
                        client.user = user
                        client.save()
                    
                    # Удаляем старый токен, если он есть
                    Token.objects.filter(user=client.user).delete()
                    # Создаем новый токен
                    token = Token.objects.create(user=client.user)
                    
                    return Response({
                        'uuid': str(client.uuid),
                        'name': client.name,
                        'token': token.key
                    })
                except ClientAgent.DoesNotExist:
                    pass
            
            # Проверяем, существует ли уже клиент с таким именем у этого менеджера
            existing_client = ClientAgent.objects.filter(
                manager=manager,
                name=client_name
            ).first()
            
            if existing_client:
                # Если клиент существует, обновляем его статус и возвращаем данные
                existing_client.is_online = True
                existing_client.last_seen = timezone.now()
                existing_client.last_heartbeat = timezone.now()
                existing_client.save()
                
                # Создаем или обновляем токен
                if not existing_client.user:
                    username = f"client_{existing_client.uuid}"
                    user = User.objects.create_user(username=username, password=None)
                    existing_client.user = user
                    existing_client.save()
                
                # Удаляем старый токен, если он есть
                Token.objects.filter(user=existing_client.user).delete()
                # Создаем новый токен
                token = Token.objects.create(user=existing_client.user)
                
                return Response({
                    'uuid': str(existing_client.uuid),
                    'name': existing_client.name,
                    'token': token.key
                })
            
            # Создаем нового клиента
            client = ClientAgent.objects.create(
                name=client_name,
                manager=manager,
                is_online=True,
                last_seen=timezone.now(),
                last_heartbeat=timezone.now()
            )
            
            # Создаем пользователя для клиента
            username = f"client_{client.uuid}"
            user = User.objects.create_user(username=username, password=None)
            client.user = user
            client.save()
            
            # Генерируем токен
            token = Token.objects.create(user=user)
            
            return Response({
                'uuid': str(client.uuid),
                'name': client.name,
                'token': token.key
            }, status=status.HTTP_201_CREATED)
            
        except ManagerProfile.DoesNotExist:
            return Response(
                {'error': 'Manager not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def token(self, request):
        """Получение токена для существующего клиента."""
        client_uuid = request.data.get('uuid')
        
        if not client_uuid:
            return Response(
                {'error': 'uuid is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            client = ClientAgent.objects.get(uuid=client_uuid)
            
            # Обновляем статус клиента
            client.is_online = True
            client.last_seen = timezone.now()
            client.last_heartbeat = timezone.now()
            client.save()
            
            # Создаем или обновляем токен
            if not client.user:
                username = f"client_{client.uuid}"
                user = User.objects.create_user(username=username, password=None)
                client.user = user
                client.save()
            
            # Удаляем старый токен, если он есть
            Token.objects.filter(user=client.user).delete()
            # Создаем новый токен
            token = Token.objects.create(user=client.user)
            
            serializer = self.get_serializer(client)
            return Response({
                **serializer.data,
                'token': token.key
            })
            
        except ClientAgent.DoesNotExist:
            return Response(
                {'error': 'Client not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['patch'])
    def update_name(self, request, uuid=None):
        """Обновление имени клиента."""
        client = self.get_object()
        new_name = request.data.get('name')
        
        if not new_name:
            return Response(
                {'error': 'name is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        client.name = new_name
        client.save()
        
        serializer = self.get_serializer(client)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send_command(self, request, uuid=None):
        """Отправка команды клиенту."""
        client = self.get_object()
        command_type = request.data.get('command_type')
        parameters = request.data.get('parameters', {})
        
        if not command_type:
            return Response(
                {'error': 'Command type is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        command = Command.objects.create(
            client=client,
            command_type=command_type,
            parameters=parameters
        )
        
        # TODO: Отправка команды через WebSocket
        
        serializer = CommandSerializer(command)
        return Response(serializer.data)

class PolicyViewSet(viewsets.ModelViewSet):
    """ViewSet для управления политиками безопасности."""
    serializer_class = PolicySerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Разрешаем доступ как менеджерам, так и клиентам."""
        return [IsAuthenticated()]

    def get_queryset(self):
        """Получаем политики в зависимости от типа пользователя."""
        try:
            client_uuid = self.request.query_params.get('client_uuid')
            
            # Если это клиент
            if hasattr(self.request.user, 'client_agent'):
                client = self.request.user.client_agent
                return Policy.objects.filter(
                    Q(client=client) | Q(client__isnull=True),
                    is_active=True
                ).distinct()
            
            # Если это менеджер
            elif hasattr(self.request.user, 'manager_profile'):
                manager = self.request.user.manager_profile
                
                if client_uuid:
                    try:
                        client = ClientAgent.objects.get(uuid=client_uuid, manager=manager)
                        return Policy.objects.filter(
                            Q(client=client) | Q(client__isnull=True),
                            is_active=True
                        ).distinct()
                    except ClientAgent.DoesNotExist:
                        return Policy.objects.none()
                else:
                    return Policy.objects.filter(
                        Q(client__isnull=True) | Q(client__manager=manager),
                        is_active=True
                    ).distinct()
            
            return Policy.objects.none()
        except Exception as e:
            print(f"Error in PolicyViewSet.get_queryset: {str(e)}")
            return Policy.objects.none()

    def perform_create(self, serializer):
        """Создание новой политики."""
        try:
            if not hasattr(self.request.user, 'manager_profile'):
                raise ValidationError("Only managers can create policies")
            
            client_uuid = self.request.data.get('client_uuid')
            process_name = self.request.data.get('process_name')
            
            if not process_name:
                raise ValidationError("process_name is required")
            
            if client_uuid:
                try:
                    client = ClientAgent.objects.get(uuid=client_uuid)
                    # Проверяем, что клиент принадлежит менеджеру
                    if client.manager != self.request.user.manager_profile:
                        raise ValidationError("You don't have permission to create policies for this client")
                    serializer.save(
                        client=client,
                        manager=self.request.user.manager_profile,
                        blacklist=[process_name],
                        action='block',
                        is_active=True
                    )
                except ClientAgent.DoesNotExist:
                    raise ValidationError("Client not found")
            else:
                serializer.save(
                    client=None,
                    manager=self.request.user.manager_profile,
                    blacklist=[process_name],
                    action='block',
                    is_active=True
                )
        except Exception as e:
            print(f"Error in PolicyViewSet.perform_create: {str(e)}")
            raise ValidationError(str(e))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_violation_logs(request, client_uuid):
    """Получение логов нарушений для клиента."""
    try:
        # Получаем клиента
        client = get_object_or_404(ClientAgent, uuid=client_uuid)
        
        # Проверяем, что клиент принадлежит менеджеру
        if client.manager != request.user.manager_profile:
            return Response(
                {'error': 'You do not have permission to access this client\'s logs'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем логи нарушений, исключая heartbeats
        logs = Log.objects.filter(
            client=client,
            event__in=['policy_violation', 'process_blocked']  # Only get actual violations
        ).order_by('-timestamp')
        
        serializer = LogSerializer(logs, many=True)
        
        return Response(serializer.data)
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])  # Allow both client and manager access
def get_client_policy(request, client_uuid):
    """Получение политики безопасности для клиента."""
    try:
        # Получаем клиента
        client = get_object_or_404(ClientAgent, uuid=client_uuid)
        
        # Проверяем аутентификацию
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Token '):
            # Это запрос от клиента
            token = auth_header.replace('Token ', '')
            if not client.user or not Token.objects.filter(user=client.user, key=token).exists():
                return Response(
                    {'error': 'Invalid token'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
        elif hasattr(request.user, 'manager_profile'):
            # Это запрос от менеджера
            if client.manager != request.user.manager_profile:
                return Response(
                    {'error': 'You do not have permission to access this client\'s policy'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Получаем активные политики
        policies = Policy.objects.filter(
            Q(client=client) | Q(client__isnull=True),
            is_active=True,
            action='block'
        ).order_by('-created_at')
        
        # Форматируем ответ
        blacklist = set()
        for policy in policies:
            if isinstance(policy.blacklist, list):
                blacklist.update(policy.blacklist)
        
        return Response({
            'blacklist': list(blacklist),
            'last_update': timezone.now().isoformat()
        })
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_blacklist(request):
    """Add a process to the blacklist."""
    try:
        process_name = request.data.get('process_name')
        client_uuid = request.data.get('client_uuid')
        
        if not process_name:
            return Response({'error': 'Process name is required'}, status=400)
            
        # Get manager profile
        manager_profile = ManagerProfile.objects.filter(user=request.user).first()
        if not manager_profile:
            return Response({'error': 'Manager profile not found'}, status=404)
            
        # Get or create policy
        if client_uuid:
            try:
                client = ClientAgent.objects.get(uuid=client_uuid)
                policy, created = Policy.objects.get_or_create(
                    client=client,
                    manager=manager_profile,
                    defaults={'blacklist': []}
                )
            except ClientAgent.DoesNotExist:
                return Response({'error': 'Client not found'}, status=404)
        else:
            policy, created = Policy.objects.get_or_create(
                manager=manager_profile,
                client=None,
                defaults={'blacklist': []}
            )
            
        # Add process to blacklist
        policy.add_to_blacklist(process_name)
        policy.is_active = True
        policy.save()
        
        return Response({
            'message': f'Process {process_name} added to blacklist',
            'blacklist': policy.blacklist
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_from_blacklist(request):
    """Remove a process from the blacklist."""
    try:
        process_name = request.data.get('process_name')
        client_uuid = request.data.get('client_uuid')
        
        if not process_name:
            return Response({'error': 'Process name is required'}, status=400)
            
        # Get manager profile
        manager_profile = ManagerProfile.objects.filter(user=request.user).first()
        if not manager_profile:
            return Response({'error': 'Manager profile not found'}, status=404)
            
        # Find policy
        if client_uuid:
            try:
                client = ClientAgent.objects.get(uuid=client_uuid)
                policy = Policy.objects.filter(
                    client=client,
                    manager=manager_profile
                ).first()
            except ClientAgent.DoesNotExist:
                return Response({'error': 'Client not found'}, status=404)
        else:
            policy = Policy.objects.filter(
                manager=manager_profile,
                client=None
            ).first()
            
        if not policy:
            return Response({'error': 'Policy not found'}, status=404)
            
        # Remove process from blacklist
        if policy.remove_from_blacklist(process_name):
            return Response({
                'message': f'Process {process_name} removed from blacklist',
                'blacklist': policy.blacklist
            })
        else:
            return Response({
                'error': f'Process {process_name} not found in blacklist'
            }, status=404)
            
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def report_violation(request, client_uuid):
    """Отправка отчета о нарушении политики."""
    try:
        client = ClientAgent.objects.get(uuid=client_uuid)
        Log.objects.create(
            client=client,
            event='policy_violation',
            data=request.data,
            level='warning'
        )
        return Response({"status": "success"})
    except ClientAgent.DoesNotExist:
        return Response(
            {"error": "Client not found"},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def process_report(request):
    """Обработка отчетов от клиента (heartbeat и violations)."""
    client_uuid = request.data.get('client_uuid')
    event_type = request.data.get('event_type')
    auth_token = request.headers.get('Authorization', '').replace('Token ', '')
    
    if not client_uuid or not event_type:
        return Response(
            {'error': 'client_uuid and event_type are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        client = ClientAgent.objects.get(uuid=client_uuid)
        
        # Проверяем токен, если он предоставлен
        if auth_token and client.user:
            token = Token.objects.filter(user=client.user, key=auth_token).first()
            if not token:
                return Response(
                    {'error': 'Invalid token'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        if event_type == 'heartbeat':
            # Обновляем статус клиента
            client.is_online = True
            client.last_seen = timezone.now()
            client.last_heartbeat = timezone.now()
            client.save()
            
            # Сохраняем информацию о процессах
            processes = request.data.get('processes', [])
            system_stats = request.data.get('system_stats', {})
            
            Log.objects.create(
                client=client,
                event='heartbeat',
                data={
                    'processes': processes,
                    'system_stats': system_stats
                }
            )
            
            return Response({
                'status': 'success',
                'client_status': {
                    'is_online': client.is_online,
                    'last_seen': client.last_seen,
                    'last_heartbeat': client.last_heartbeat
                }
            })
            
        elif event_type in ['violation', 'policy_violation']:  # Handle both old and new event types
            process_name = request.data.get('process_name')
            pid = request.data.get('process_id')
            
            if not process_name or not pid:
                return Response(
                    {'error': 'process_name and pid are required for violations'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            Log.objects.create(
                client=client,
                event='policy_violation',  # Always use policy_violation for consistency
                data={
                    'process_name': process_name,
                    'pid': pid
                }
            )
            
            return Response({'status': 'success'})
            
        else:
            return Response(
                {'error': 'Invalid event_type'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except ClientAgent.DoesNotExist:
        return Response(
            {'error': 'Client not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_client_blacklist(request, client_uuid):
    """Получение записей черного списка для конкретного клиента."""
    try:
        client = ClientAgent.objects.get(
            uuid=client_uuid, 
            manager=request.user.manager_profile
        )
        
        # Получаем политики клиента
        client_policies = Policy.objects.filter(
            client=client, 
            is_active=True, 
            action='block'
        )
        
        # Получаем общие политики менеджера
        common_policies = Policy.objects.filter(
            manager=request.user.manager_profile,
            client__isnull=True,
            is_active=True,
            action='block'
        )
        
        # Объединяем результаты
        all_policies = client_policies | common_policies
        
        serializer = PolicySerializer(all_policies, many=True)
        return Response(serializer.data)
    except ClientAgent.DoesNotExist:
        return Response(
            {"error": "Client not found or access denied"},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_manager_blacklist(request):
    """Получение всех записей черного списка для менеджера."""
    policies = Policy.objects.filter(
        manager=request.user.manager_profile,
        is_active=True,
        action='block'
    )
    
    serializer = PolicySerializer(policies, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_manager_profile(request):
    """Получение профиля менеджера."""
    manager_profile = request.user.manager_profile
    return Response({
        'uuid': manager_profile.uuid,
        'username': request.user.username,
        'created_at': manager_profile.created_at
    })

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_client(request, client_uuid):
    """Удаление клиента."""
    try:
        client = ClientAgent.objects.get(uuid=client_uuid)
        if client.manager != request.user.manager_profile:
            return Response(
                {"error": "You don't have permission to delete this client"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Удаляем связанные данные
        if client.user:
            Token.objects.filter(user=client.user).delete()
            client.user.delete()
        
        client.delete()
        return Response({"status": "success"})
    except ClientAgent.DoesNotExist:
        return Response(
            {"error": "Client not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [AllowAny]  # Разрешаем отправку отчетов без аутентификации

    def create(self, request):
        """Создание отчета."""
        client_uuid = request.data.get('client_uuid')
        auth_token = request.headers.get('Authorization', '').replace('Token ', '')

        if not client_uuid:
            return Response(
                {"error": "client_uuid is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Проверяем токен, если он предоставлен
            if auth_token:
                client = ClientAgent.objects.get(uuid=client_uuid, auth_token=auth_token)
            else:
                client = ClientAgent.objects.get(uuid=client_uuid)

            # Обновляем время последнего обращения
            client.last_seen = timezone.now()
            client.save()

            # Создаем отчет
            report = Report.objects.create(
                client=client,
                event_type=request.data.get('event_type'),
                process_name=request.data.get('process_name'),
                process_id=request.data.get('process_id'),
                timestamp=request.data.get('timestamp'),
                system_stats=request.data.get('system_stats')
            )

            return Response({
                "id": report.id,
                "event_type": report.event_type,
                "timestamp": report.timestamp
            }, status=status.HTTP_201_CREATED)

        except ClientAgent.DoesNotExist:
            return Response(
                {"error": "Client not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@api_view(['GET'])
@permission_classes([AllowAny])
def get_manager_violations(request, manager_uuid):
    """Получение нарушений для менеджера."""
    try:
        manager = ManagerProfile.objects.get(uuid=manager_uuid)
        clients = ClientAgent.objects.filter(manager=manager)
        
        violations = Log.objects.filter(
            client__in=clients,
            event='policy_violation'
        ).order_by('-timestamp')
        
        return Response(LogSerializer(violations, many=True).data)
    except ManagerProfile.DoesNotExist:
        return Response(
            {"error": "Manager not found"},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_manager_clients(request):
    """Получение списка клиентов для менеджера."""
    try:
        manager = request.user.manager_profile
        clients = ClientAgent.objects.filter(manager=manager)
        
        # Проверяем статус клиентов
        now = timezone.now()
        for client in clients:
            # Если клиент не отправлял heartbeat более 30 секунд, считаем его оффлайн
            if client.last_heartbeat and (now - client.last_heartbeat).total_seconds() > 30:
                client.is_online = False
                client.save()
        
        serializer = ClientAgentSerializer(clients, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# Здесь будут добавлены остальные viewsets
