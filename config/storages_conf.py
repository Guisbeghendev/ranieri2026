from storages.backends.s3boto3 import S3Boto3Storage


# NOTA: O S3Boto3Storage irá carregar as configurações AWS_* automaticamente
# do módulo django.conf.settings no momento da inicialização do Django.


# --- Storage para Arquivos de Média PÚBLICOS (Watermarks, Imagens Processadas) ---
# Usado explicitamente em repositorio/models.py
class PublicMediaStorage(S3Boto3Storage):
    location = 'media'

    # CORREÇÃO CRÍTICA: Manter default_acl como None para obedecer ao Bucket Owner Enforced
    default_acl = None

    # CORREÇÃO: Necessário gerar URL assinada (querystring_auth = True) para
    # que o navegador possa acessar o arquivo, pois o S3 bloqueou o acesso
    # público por padrão (AccessControlListNotSupported).
    querystring_auth = True

    # custom_domain e endpoint_url são lidos automaticamente de settings.py


# --- Storage para Arquivos de Média PRIVADOS (Imagens Originais) ---
# Usado explicitamente em repositorio/models.py ou como DEFAULT_FILE_STORAGE
class PrivateMediaStorage(S3Boto3Storage):
    location = ''

    # Manter default_acl como None para garantir a privacidade.
    default_acl = None

    # Geração de URL assinada (temporária) NECESSÁRIA para o Celery e acesso privado
    querystring_auth = True

    # endpoint_url é lido automaticamente de settings.py