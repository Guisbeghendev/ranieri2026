from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # A URL deve conter 'repositorio-admin' para coincidir com a chamada do front-end
    re_path(r'ws/repositorio-admin/galerias/(?P<slug>[\w-]+)/?$', consumers.GaleriaConsumer.as_asgi()),
]