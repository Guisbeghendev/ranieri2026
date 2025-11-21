from django.urls import path
from .views import ProjSimCozinhaView, IndexSimCozinhaView # 🚨 Importando a nova view

app_name = 'sim_cozinha'

urlpatterns = [
    # 🚨 NOVO: URL da página inicial do módulo
    path(
        '',
        IndexSimCozinhaView.as_view(),
        name='index'
    ),
    # URL principal do catálogo. A navegação sequencial é controlada via query parameter '?page=X'
    path(
        'catalogo/', # 🚨 Alterado para 'catalogo/' para liberar a URL base
        ProjSimCozinhaView.as_view(),
        name='catalogo'
    ),
]