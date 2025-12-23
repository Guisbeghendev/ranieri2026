# galerias/urls.py (CORRIGIDO)
from django.urls import path
from . import views
# REMOVIDO: from .views import PrivateMediaProxyView

app_name = 'galerias'

urlpatterns = [
    # 1. Listagem de todas as galerias acessíveis (Públicas e Exclusivas)
    path('', views.GaleriaListView.as_view(), name='lista_galerias'),

    # 2. Detalhe da Galeria (Exibição das Imagens)
    path('detalhe/<int:pk>/', views.GaleriaDetailView.as_view(), name='detalhe_galeria'),

    # 3. Endpoint de Interação: Curtir/Descurtir (AJAX/POST)
    # Recebe o PK da Imagem para registrar/remover a curtida
    path('interacao/curtir/<int:imagem_pk>/', views.CurtirView.as_view(), name='curtir_imagem'),

    # Rota do Proxy de Mídia Privada S3 (REMOVIDA DAQUI)
]