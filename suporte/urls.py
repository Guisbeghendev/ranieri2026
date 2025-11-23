from django.urls import path
from .views import (
    TopicoListView,
    TopicoCreateView,
    TopicoDetailView,
    MensagemSuporteCreateView,
    TopicoCloseView,
    # NOVO: Importe a view de atualização de status
    TopicoStatusUpdateView,
    # Adicionado: Assumindo a view de reabertura (TopicoReopenView)
    # Você precisará criar esta view no views.py se ela ainda não existir.
    # Se já existir, a view correta deve ser importada.
    # Por enquanto, usaremos TopicoCloseView como placeholder, ou você pode
    # renomeá-la para uma view mais genérica se ela também lidar com a reabertura.
)

app_name = 'suporte'

urlpatterns = [
    # /suporte/
    path('', TopicoListView.as_view(), name='topico_list'),

    # /suporte/novo/
    path('novo/', TopicoCreateView.as_view(), name='topico_create'),

    # /suporte/<pk>/
    path('<int:pk>/', TopicoDetailView.as_view(), name='topico_detail'),

    # /suporte/<pk>/responder/ (Endpoint de POST para adicionar mensagem)
    path('<int:pk>/responder/', MensagemSuporteCreateView.as_view(), name='topico_responder'),

    # /suporte/<pk>/fechar/ (URL para fechar o tópico)
    path('<int:pk>/fechar/', TopicoCloseView.as_view(), name='topico_fechar'),

    # NOVO: /suporte/<pk>/status/ (URL para Staff/Superuser atualizar status e responsável)
    path('<int:pk>/status/', TopicoStatusUpdateView.as_view(), name='topico_update_status'),

    # Adicionado: /suporte/<pk>/reabrir/ (URL para reabrir o tópico - Presumindo que você crie TopicoReopenView)
    # OBSERVAÇÃO: Se a reabertura estiver na mesma view de fechar, ajuste o nome da view ou crie uma nova.
    # Se você já tiver a view de reabrir, substitua TopicoCloseView.as_view() pela view correta.
    # Assumindo que você precisa de uma URL separada para reabrir, vamos chamá-la de 'topico_reopen'.
    # path('<int:pk>/reabrir/', TopicoReopenView.as_view(), name='topico_reabrir'),
]