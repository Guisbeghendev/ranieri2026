from storages.backends.s3boto3 import S3Boto3Storage


# NOTA: O S3Boto3Storage irá carregar as configurações AWS_* automaticamente
# do módulo django.conf.settings no momento da inicialização do Django.


# --- Storage para Arquivos de Média PÚBLICOS (Watermarks, Imagens Processadas) ---
# Usado explicitamente em repositorio/models.py
class PublicMediaStorage(S3Boto3Storage):
    location = 'media'

    # Recomendado para Public Media: Permissão de leitura pública padrão.
    default_acl = 'public-read'

    # Para URLs públicas (diretas do S3, sem proxy), não deve usar querystring_auth
    querystring_auth = False


# --- Storage para Arquivos de Média PRIVADOS (Imagens Originais/Processadas por Proxy) ---
# Usado explicitamente em repositorio/models.py ou como DEFAULT_FILE_STORAGE
class PrivateMediaStorage(S3Boto3Storage):
    location = ''

    # Manter default_acl como None para garantir a privacidade.
    default_acl = None

    # CORREÇÃO CRÍTICA DO ERRO 5: Define querystring_auth como False.
    # Isso impede a geração de URLs pré-assinadas e força o FileField a retornar
    # um caminho relativo (ex: /medias3/repo/...), que será interceptado pelo
    # private_media_proxy para checagem de permissão.
    querystring_auth = False

    # O Celery pode acessar o arquivo privado usando as credenciais AWS,
    # sem depender de URLs assinadas.