from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Rota para atualizações globais e específicas (aceitando PK opcional)
    re_path(r'ws/repositorio/galerias/(?P<pk>\d+)?/?$', consumers.GaleriaConsumer.as_asgi()),
]