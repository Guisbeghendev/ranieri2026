import os

from django.core.asgi import get_asgi_application

# 1. Configura as settings do Django para o processo ASGI.
# ESTE PASSO DEVE SER O PRIMEIRO antes de importar qualquer código Django que use Models.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# 2. A aplicação Django padrão para requisições HTTP.
# A chamada a get_asgi_application() inicializa o registro de Apps do Django.
django_asgi_app = get_asgi_application()

# --- IMPORTAÇÕES QUE DEPENDEM DO DJANGO INICIALIZADO ---

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

# Importamos o módulo de roteamento após a inicialização do Django.
import mensagens.routing


# ProtocolTypeRouter: Roteia a conexão para o handler apropriado
application = ProtocolTypeRouter({
    # 1. Requisições HTTP normais (gerenciadas pelo Django)
    "http": django_asgi_app,

    # 2. Requisições WebSocket (gerenciadas pelo Channels)
    # AuthMiddlewareStack: Essencial para autenticar o usuário na conexão WebSocket.
    "websocket": AuthMiddlewareStack(
        URLRouter(
            # O URLRouter direciona as conexões WebSocket com base na URL
            mensagens.routing.websocket_urlpatterns
        )
    ),
})