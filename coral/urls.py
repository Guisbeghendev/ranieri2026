from django.urls import path
from .views import LivroDigitalCoralView, CoralIndexView
from .models import CapituloCoral

# Define o nome do aplicativo para uso no namespace
app_name = 'coral'

urlpatterns = [
    # Rota de índice principal do Coral (Ex: /coral/)
    path(
        '',
        CoralIndexView.as_view(),
        name='index'
    ),

    # Rota unificada que pega o tipo de livro da URL (Ex: /coral/historia/ ou /coral/repertorio/)
    # Esta é a rota base para todo o livro digital.
    path(
        '<str:tipo_livro_url>/',
        LivroDigitalCoralView.as_view(),
        name='livro_digital_coral_base'
    ),
]