from django.urls import re_path

# Importa o Consumer que gerencia as conexões WebSocket
from . import consumers

# Lista de padrões de URL para conexões WebSocket
websocket_urlpatterns = [
    # Mapeia a URL /ws/chat/ID_DO_CANAL/ para o ChatConsumer.
    # O <canal_id> é capturado e passado como argumento no escopo do Consumer.
    re_path(r'ws/chat/(?P<canal_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]