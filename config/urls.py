# config/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
# Importa a View do app 'galerias' para uso na configuração global
from galerias.views import PrivateMediaProxyView

urlpatterns = [
    # URLs da administração padrão do Django
    path('admin/', admin.site.urls),

    # URLs do App 'core' (Home e Erros) - Acessível na raiz
    path('', include('core.urls')),

    # URLs dos Apps de Conteúdo Público
    path('historia/', include(('historia.urls', 'historia'), namespace='historia')),
    path('coral/', include(('coral.urls', 'coral'), namespace='coral')),
    path('brincando-e-dialogando/',
         include(('brinc_dialogando.urls', 'brinc_dialogando'), namespace='brinc_dialogando')),

    # URLs do App de Identidade e Acesso
    path('users/', include('users.urls', namespace='users')),

    # URLs dos Apps de Conteúdo Restrito
    path('simoninha-na-cozinha/', include(('sim_cozinha.urls', 'sim_cozinha'), namespace='sim_cozinha')),
    path('mensagens/', include('mensagens.urls', namespace='mensagens')),

    # 🎯 NOVO: URLs do App de Suporte (Help Desk)
    path('suporte/', include(('suporte.urls', 'suporte'), namespace='suporte')),

    # 🎯 NOVO: URLs do App Administrativo (Interface Customizada para Fotógrafo)
    path('repositorio-admin/', include(('repositorio.urls', 'repositorio'), namespace='repositorio')),

    # 1. Rota de Proxy de Mídia (ROOT /medias3/) - CORREÇÃO DO ERRO 3
    # Captura qualquer path (caminho de arquivo S3) após 'medias3/'
    re_path(r'^medias3/(?P<path>.*)$', PrivateMediaProxyView.as_view(), name='private_media_proxy'),

    # 2. URLs de Conteúdo (Prefixadas /galerias/)
    # Inclui TODAS as rotas do app 'galerias'
    path('galerias/', include(('galerias.urls', 'galerias'), namespace='galerias')),
]

# Configuração para servir STATIC e MEDIA em ambiente de desenvolvimento
if settings.DEBUG:
    # Apenas para garantir que o Django sirva os arquivos estáticos (CORRETO)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # REMOVIDO: A linha urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)