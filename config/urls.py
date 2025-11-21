# config/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # URLs da administração padrão do Django
    path('admin/', admin.site.urls),

    # URLs do App 'core' (Home e Erros) - Acessível na raiz
    path('', include('core.urls')),

    # URLs dos Apps de Conteúdo Público
    # IMPORTANTE: URLs destes Apps serão adicionadas assim que os Apps forem criados.
    # 🚨 CORREÇÃO: Necessário passar (urls_module, app_name) ao usar namespace no include
    path('historia/', include(('historia.urls', 'historia'), namespace='historia')),
    # path('coral/', include('coral.urls')),
    # path('brincando-e-dialogando/', include('brinc_dialogando.urls')),

    # URLs do App de Identidade e Acesso
    # CORRIGIDO: Apenas uma inclusão do namespace 'users' para evitar o aviso urls.W005
    path('users/', include('users.urls', namespace='users')),

    # URLs dos Apps de Conteúdo Restrito
    # path('simoninha-na-cozinha/', include('sim_cozinha.urls')),
    # path('galerias/', include('galerias.urls')),
    # path('mensagens/', include('mensagens.urls')),

    # URLs do App Administrativo (Interface Customizada para Fotógrafo)
    # path('repositorio-admin/', include('repositorio.urls')),
]

# Configuração para servir STATIC e MEDIA em ambiente de desenvolvimento
# Em produção, o Apache/Nginx (Proxy Reverso) cuidará disso
if settings.DEBUG:
    # Apenas para garantir que o Django sirva os arquivos estáticos e de mídia em DEV
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT) # Descomentar quando MEDIA_ROOT for definido