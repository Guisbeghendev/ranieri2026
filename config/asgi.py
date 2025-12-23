import os
from django.core.asgi import get_asgi_application

# 1. Configura as settings do Django para o processo ASGI.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# 2. Inicializa o Django ASGI application primeiro para carregar os apps.
django_asgi_app = get_asgi_application()

# --- IMPORTAÇÕES QUE DEPENDEM DO DJANGO INICIALIZADO ---
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

# Importação das rotas dos apps
import mensagens.routing
import repositorio.routing

application = ProtocolTypeRouter({
    # 1. Requisições HTTP normais
    "http": django_asgi_app,

    # 2. Requisições WebSocket
    "websocket": AuthMiddlewareStack(
        URLRouter(
            # Combina as rotas de mensagens com as de repositório
            mensagens.routing.websocket_urlpatterns +
            repositorio.routing.websocket_urlpatterns
        )
    ),
})