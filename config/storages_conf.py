from storages.backends.s3boto3 import S3Boto3Storage


# NOTA: O S3Boto3Storage irá carregar as configurações AWS_* automaticamente
# do módulo django.conf.settings no momento da inicialização do Django.


# --- Storage para Arquivos de Média PÚBLICOS (Watermarks) ---
class PublicMediaStorage(S3Boto3Storage):
    location = 'media'
    default_acl = 'public-read'
    querystring_auth = False


# --- Storage para Arquivos de Média PRIVADOS (Imagens Originais/Processadas) ---
class PrivateMediaStorage(S3Boto3Storage):
    location = ''
    default_acl = None

    # CORREÇÃO: Deve ser True para que o S3 aceite o acesso via URLs assinadas
    # geradas internamente ou pelo Celery, mas mantido False se o objetivo
    # for EXCLUSIVAMENTE o uso do proxy local para servir as imagens.
    # No seu caso, para o proxy funcionar sem expor links do S3:
    querystring_auth = False

    # GARANTIA DE PRIVACIDADE:
    custom_domain = False