# galerias/urls.py
from django.urls import path
from . import views

app_name = 'galerias'

urlpatterns = [
    # 1. Vitrine Pública (Apenas conteúdo público - Acessível por todos)
    path('', views.GaleriaPublicaListView.as_view(), name='lista_publicas'),

    # 2. Listagem Restrita (Apenas conteúdo exclusivo - Acessível apenas por logados)
    path('exclusivas/', views.GaleriaListView.as_view(), name='lista_galerias'),

    # 3. Detalhe da Galeria (Exibição das Imagens - Mixin valida se é pública ou restrita)
    path('detalhe/<int:pk>/', views.GaleriaDetailView.as_view(), name='detalhe_galeria'),

    # 4. Endpoint de Interação: Curtir/Descurtir (AJAX/POST)
    path('interacao/curtir/<int:imagem_pk>/', views.CurtirView.as_view(), name='curtir_imagem'),

    # 5. Proxy de Média Privada S3
    path('media-proxy/<path:path>', views.PrivateMediaProxyView.as_view(), name='private_media_proxy'),
]