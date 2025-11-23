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
    path('historia/', include(('historia.urls', 'historia'), namespace='historia')),
    path('coral/', include(('coral.urls', 'coral'), namespace='coral')),
    path('brincando-e-dialogando/',
         include(('brinc_dialogando.urls', 'brinc_dialogando'), namespace='brinc_dialogando')),

    # URLs do App de Identidade e Acesso
    path('users/', include('users.urls', namespace='users')),

    # URLs dos Apps de Conteúdo Restrito
    path('simoninha-na-cozinha/', include(('sim_cozinha.urls', 'sim_cozinha'), namespace='sim_cozinha')),
    # path('galerias/', include('galerias.urls')),
    path('mensagens/', include('mensagens.urls', namespace='mensagens')),

    # 🎯 NOVO: URLs do App de Suporte (Help Desk)
    path('suporte/', include(('suporte.urls', 'suporte'), namespace='suporte')),

    # URLs do App Administrativo (Interface Customizada para Fotógrafo)
    # path('repositorio-admin/', include('repositorio.urls')),
]

# Configuração para servir STATIC e MEDIA em ambiente de desenvolvimento
# Em produção, o Apache/Nginx (Proxy Reverso) cuidará disso
if settings.DEBUG:
    # Apenas para garantir que o Django sirva os arquivos estáticos e de mídia em DEV
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)  # Descomentar quando MEDIA_ROOT for definido