from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Rota para as atualizações de status das galerias
    re_path(r'ws/repositorio/galerias/$', consumers.GaleriaConsumer.as_asgi()),
]