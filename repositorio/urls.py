from django.urls import path
from .views import (
    UploadImagemView,
    CriarGaleriaView,
    GerenciarGaleriasView,
    GerenciarImagensGaleriaView,
    ExcluirGaleriaView,
    AssinarUploadView,
    ConfirmarUploadView,
    PublicarGaleriaView,
    ArquivarGaleriaView,
    DefinirCapaGaleriaView,  # ADICIONADO: Importa a nova view de configuração de capa
)

app_name = 'repositorio'

urlpatterns = [
    # 1. Rota de Upload (Página de Upload)
    path('upload/', UploadImagemView.as_view(), name='upload_imagem'),

    # 1b. Rota para Assinar o Upload S3 (API de Upload)
    path('upload/assinar/', AssinarUploadView.as_view(), name='assinar_upload'),

    # 1c. Rota para Confirmação do Upload S3
    path('upload/confirmar/', ConfirmarUploadView.as_view(), name='confirmar_upload'),

    # ROTAS RELACIONADAS A GALERIAS
    path('galeria/criar/', CriarGaleriaView.as_view(), name='criar_galeria'),
    path('galeria/editar/<int:pk>/', CriarGaleriaView.as_view(), name='editar_galeria'),
    path('galeria/excluir/<int:pk>/', ExcluirGaleriaView.as_view(), name='excluir_galeria'),

    # 2. Rota de Publicação de Galeria
    path('galeria/publicar/<int:pk>/', PublicarGaleriaView.as_view(), name='publicar_galeria'),

    # Rota de Arquivamento de Galeria
    path('galeria/arquivar/<int:pk>/', ArquivarGaleriaView.as_view(), name='arquivar_galeria'),

    path('galerias/', GerenciarGaleriasView.as_view(), name='gerenciar_galerias'),
    path('galeria/imagens/<int:pk>/', GerenciarImagensGaleriaView.as_view(), name='gerenciar_imagens_galeria'),

    # NOVO: Rota para Definir a Capa da Galeria (Endpoint AJAX)
    # Recebe o PK da Galeria e o PK da Imagem a ser definida como capa
    path('galeria/<int:galeria_pk>/capa/<int:imagem_pk>/definir/',
         DefinirCapaGaleriaView.as_view(),
         name='definir_capa_galeria'),
]