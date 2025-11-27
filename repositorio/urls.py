from django.urls import path
from .views import (
    UploadImagemView,
    CriarGaleriaView,
    GerenciarGaleriasView,
    GerenciarImagensGaleriaView,
    ExcluirGaleriaView,  # Importação da View de Exclusão
)

app_name = 'repositorio'

urlpatterns = [
    # 1. Rota de Upload
    path('upload/', UploadImagemView.as_view(), name='upload_imagem'),

    # 2. Rota de Criação e Edição da Galeria
    path('galeria/criar/', CriarGaleriaView.as_view(), name='criar_galeria'),
    path('galeria/editar/<int:pk>/', CriarGaleriaView.as_view(), name='editar_galeria'),

    # 3. Rota de Exclusão (usada pelo JS)
    path('galeria/excluir/<int:pk>/', ExcluirGaleriaView.as_view(), name='excluir_galeria'),

    # 4. Listagem e Gestão das Galerias do Fotógrafo
    path('galerias/', GerenciarGaleriasView.as_view(), name='gerenciar_galerias'),

    # 5. Gerenciamento de Imagens vinculadas a uma Galeria específica
    path('galeria/imagens/<int:pk>/', GerenciarImagensGaleriaView.as_view(), name='gerenciar_imagens_galeria'),
]