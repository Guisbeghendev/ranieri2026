import os
import django
from django.core.asgi import get_asgi_application

# 1. Configura as settings do Django para o processo ASGI.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# 2. Inicializa o Django para permitir importações de modelos e rotas.
django.setup()

# 3. Inicializa o Django ASGI application.
django_asgi_app = get_asgi_application()

# --- IMPORTAÇÕES QUE DEPENDEM DO DJANGO INICIALIZADO ---
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

# Importação das rotas dos apps (Incluindo suporte conforme settings)
import mensagens.routing
import suporte.routing
import repositorio.routing

application = ProtocolTypeRouter({
    # 1. Requisições HTTP normais
    "http": django_asgi_app,

    # 2. Requisições WebSocket
    "websocket": AuthMiddlewareStack(
        URLRouter(
            # Combina as rotas de todos os apps que usam tempo real
            mensagens.routing.websocket_urlpatterns +
            suporte.routing.websocket_urlpatterns +
            repositorio.routing.websocket_urlpatterns
        )
    ),
})