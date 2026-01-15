from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Rota atualizada para aceitar o slug da galeria, permitindo conexão com o grupo correto.
    # Opcional para suportar tanto a visualização da galeria quanto o upload geral.
    re_path(r'ws/repositorio/galerias/(?P<slug>[\w-]+)?/?$', consumers.GaleriaConsumer.as_asgi()),
]