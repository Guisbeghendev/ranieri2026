from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Rota para galeria específica
    re_path(r'ws/repositorio-admin/galerias/(?P<slug>[\w-]+)/$', consumers.GaleriaConsumer.as_asgi()),

    # Rota para listagem de galerias (resolvendo o erro 500/No route found)
    re_path(r'ws/repositorio/galerias/$', consumers.GaleriaConsumer.as_asgi()),

    # Rota adicional para o prefixo admin sem slug
    re_path(r'ws/repositorio-admin/galerias/$', consumers.GaleriaConsumer.as_asgi()),
]