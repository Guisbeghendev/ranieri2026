from django.urls import path
from .views import CoralIndexView, HistoriaDigitalView, RepertorioListView

app_name = 'coral'

urlpatterns = [
    # Rota de índice principal do Coral
    path(
        '',
        CoralIndexView.as_view(),
        name='index'
    ),

    # Rota específica para o Livro de História
    path(
        'historia/',
        HistoriaDigitalView.as_view(),
        name='historia_digital'
    ),

    # Rota específica para a Listagem de Repertório
    path(
        'repertorio/',
        RepertorioListView.as_view(),
        name='repertorio_list'
    ),
]