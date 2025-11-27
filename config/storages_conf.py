from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

# Garante que o Django saiba onde salvar Static e Media no S3
class StaticStorage(S3Boto3Storage):
    # A base de upload será /static/ no bucket
    location = 'static'
    default_acl = 'public-read'
    # Evita que o Django apague arquivos que não estão no Manifest
    file_overwrite = False

class MediaStorage(S3Boto3Storage):
    # A base de upload será /media/ no bucket
    location = 'media'
    default_acl = 'public-read'
    # Necessário para o Celery ter acesso ao arquivo original e para link público
    # Assumimos que a variável settings.AWS_QUERYSTRING_AUTH está sendo lida.
    querystring_auth = settings.AWS_QUERYSTRING_AUTH
    custom_domain = settings.AWS_S3_CUSTOM_DOMAIN