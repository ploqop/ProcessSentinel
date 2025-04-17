# server/routing.py
from django.urls import re_path
from agents.consumers import AgentConsumer

websocket_urlpatterns = [
    re_path(r'wss/agent/(?P<client_uuid>[0-9a-f-]+)/$', AgentConsumer.as_asgi()),
]