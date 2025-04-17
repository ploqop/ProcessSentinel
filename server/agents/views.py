from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth.models import User
from .models import ManagerProfile, ClientAgent, Command, Log
from .serializers import (
    ManagerProfileSerializer, ClientAgentSerializer,
    CommandSerializer, LogSerializer, UserSerializer
)

# Регистрация нового управляющего (администратора)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_manager(request):
    # Создать пользователя и вернуть uuid его ManagerProfile
    username = request.data.get('username')
    password = request.data.get('password')
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Пользователь существует'}, status=status.HTTP_400_BAD_REQUEST)
    user = User.objects.create_user(username=username, password=password)
    mp = ManagerProfile.objects.create(user=user)
    return Response({'uuid': mp.uuid}, status=status.HTTP_201_CREATED)

# Получение JWT токенов для менеджера
class ManagerTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]

# Клиент регистрируется у менеджера по его UUID
@api_view(['POST'])
@permission_classes([AllowAny])
def register_client(request):
    manager_uuid = request.data.get('manager_uuid')
    name = request.data.get('name', '')
    try:
        mp = ManagerProfile.objects.get(uuid=manager_uuid)
    except ManagerProfile.DoesNotExist:
        return Response({'error': 'Менеджер не найден'}, status=status.HTTP_404_NOT_FOUND)
    client = ClientAgent.objects.create(manager=mp, name=name)
    return Response({'client_uuid': client.uuid}, status=status.HTTP_201_CREATED)

# ViewSet для управляющего: список клиентов, логов, отправка команд
class ManagerViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def clients(self, request):
        mp = request.user.manager_profile
        clients = mp.clients.all()
        serializer = ClientAgentSerializer(clients, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send_command(self, request, pk=None):
        # pk = UUID клиента
        try:
            client = ClientAgent.objects.get(uuid=pk, manager=request.user.manager_profile)
        except ClientAgent.DoesNotExist:
            return Response({'error': 'Клиент не найден'}, status=status.HTTP_404_NOT_FOUND)
        text = request.data.get('text')
        cmd = Command.objects.create(client=client, text=text)
        # через WebSocket отправим команду (см. consumers.py)
        return Response(CommandSerializer(cmd).data)

# Клиент отправляет логи
class LogViewSet(viewsets.ModelViewSet):
    queryset = Log.objects.all()
    serializer_class = LogSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # здесь аутентифицировать запрос по токену клиента (JWT или APIKey)
        return super().create(request, *args, **kwargs)