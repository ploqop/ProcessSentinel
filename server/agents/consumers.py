# agents/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ClientAgent, Command

class AgentConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        # клиент передаёт свой UUID как параметр
        self.client_uuid = self.scope['url_route']['kwargs']['client_uuid']
        self.group_name = f"agent_{self.client_uuid}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        # обработка сообщений от клиента (например, результат выполнения команд)
        pass

    # метод для отправки команды из view
    async def send_command(self, event):
        await self.send_json({ 'command': event['text'], 'id': event['cmd_id'] })