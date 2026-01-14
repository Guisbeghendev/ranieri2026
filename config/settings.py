from pathlib import Path
import environ

# ==============================================================================
# 1. SETUP BÁSICO E VARIÁVEIS DE AMBIENTE
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    # Adicionando as definições de tipo para Redis/Celery para robustez
    REDIS_URL=(str, 'redis://localhost:6379/1'),
    CELERY_BROKER_URL=(str, 'redis://localhost:6379/0'),
    CELERY_RESULT_BACKEND=(str, 'redis://localhost:6379/0')
)

# Tenta ler o arquivo .env no diretório base
# IMPORTANTE: O .env deve estar na raiz do projeto, um nível acima da pasta config.
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')

DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# ==============================================================================
# 2. DEFINIÇÃO DE APLICATIVOS
# ==============================================================================

INSTALLED_APPS = [
    # meus app
    'users',
    # outros
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # config
    'formtools',
    'core',
    # django-storages para S3
    'storages',
    # Configuração do Channels
    'channels',
    # meus app (continua)
    'historia',
    'coral',
    'sim_cozinha',
    'brinc_dialogando',
    'mensagens',
    'suporte',
    'galerias',
    # Repositório (USANDO APPS.PY PARA CARREGAR OS SIGNALS)
    'repositorio.apps.RepositorioConfig',
    # Celery beat para tarefas agendadas
    'django_celery_beat',
    # Adicionar aqui apps de terceiros como celery-results se necessário
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ==============================================================================
# 3. BANCO DE DADOS (Configuração EXPLICITA para PostgreSQL)
# CORREÇÃO: Lê cada campo DB_* individualmente, resolvendo o KeyError: 'DATABASE_URL'.
# ==============================================================================

DATABASES = {
    'default': {
        'ENGINE': env('DB_ENGINE'),
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}


# ==============================================================================
# 4. VALIDAÇÃO DE SENHA
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

# ==============================================================================
# 5. INTERNACIONALIZAÇÃO (PT-BR)
# ==============================================================================

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True

# ==============================================================================
# 6. ARQUIVOS ESTÁTICOS E MÍDIA (S3)
#
# REGRA: Apenas arquivos de MÍDIA do repositório (usando Storage customizado)
# vão para o S3. Arquivos ESTÁTICOS ficam locais.
# ==============================================================================

STATIC_URL = 'static/'

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Configurações S3 para ARQUIVOS DE MÍDIA (App repositorio/galerias) ---

# 1. Credenciais S3 (Lidas do .env)
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default=None)
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default=None)
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default=None)
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='sa-east-1')

# Variável de controle para simplificar a lógica (True se S3 estiver configurado)
USE_S3 = all([AWS_STORAGE_BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY])

# Configuração do Endpoint S3
if AWS_S3_REGION_NAME:
    AWS_S3_ENDPOINT_URL = f'https://s3.{AWS_S3_REGION_NAME}.amazonaws.com'
else:
    AWS_S3_ENDPOINT_URL = None

if USE_S3:
    # ** CORREÇÃO MANDATÓRIA PARA O ERRO AccessControlListNotSupported **
    # Desabilita o envio de ACLs, o que é rejeitado por buckets com 'Bucket Owner Enforced'.
    AWS_DEFAULT_ACL = None
    AWS_ACL = None

    # 2. Configurações do Storage para MÍDIA (S3)

    # DEFAULT_FILE_STORAGE aponta para o storage privado (para uploads genéricos)
    DEFAULT_FILE_STORAGE = 'config.storages_conf.PrivateMediaStorage'

    # Configurações de segurança e cache
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_VERIFY = True

    # Nova configuração necessária para storages privados:
    # O MEDIA_URL é usado como URL base para o FileField. Se o S3 for privado, este
    # valor é apenas um placeholder.
    MEDIA_URL = '/media-s3-proxy/'

else:
    # Fallback para desenvolvimento local (se o S3 não estiver configurado)
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'
    # Define o DEFAULT_FILE_STORAGE para o sistema de arquivos local
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'


# ==============================================================================
# 7. CHAVE PRIMÁRIA PADRÃO
# ==============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# 8. CONFIGURAÇÕES DE AUTENTICAÇÃO
# ==============================================================================

AUTH_USER_MODEL = 'users.CustomUser'

LOGIN_REDIRECT_URL = 'users:dashboard'

LOGOUT_REDIRECT_URL = 'users:login'

LOGIN_URL = 'users:login'

# ==============================================================================
# 9. CONFIGURAÇÕES DE SESSÃO
# ==============================================================================

SESSION_SAVE_EVERY_REQUEST = True

# ==============================================================================
# 10. CONFIGURAÇÕES DO DJANGO CHANNELS (Tempo Real)
# ==============================================================================

# Define o protocolo de entrada como ASGI
ASGI_APPLICATION = 'config.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        # Alterado para o backend estável
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [env('REDIS_URL')],
        },
    },
}

# ==============================================================================
# 11. CONFIGURAÇÕES CELERY (Processamento Assíncrono)
# ==============================================================================

# BROKER e BACKEND (Usando as variáveis definidas no environ.Env)
CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')

# Fuso horário para Celery
CELERY_TIMEZONE = TIME_ZONE

# Configurações de conteúdo para evitar problemas de serialização
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Tarefas agendadas (Celery Beat)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
# Desabilita o agendamento de tarefas padrão (usa o django_celery_beat)
CELERY_BEAT_FOR_RAVEN = False

# Configurações de tempo limite para tarefas do Celery (adicionado para robustez)
CELERY_TASK_SOFT_TIME_LIMIT = 600
CELERY_TASK_TIME_LIMIT = 900


# ==============================================================================
# 12. CONFIGURAÇÕES DE EMAIL (Fallback Simples)
# ==============================================================================

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Se precisar de configuração SMTP real:
# EMAIL_HOST = env('EMAIL_HOST', default='smtp.seudominio.com')
# EMAIL_PORT = env.int('EMAIL_PORT', default=587)
# EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
# EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
# EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
# DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='webmaster@localhost')

# ==============================================================================
# 13. CONFIGURAÇÕES DA APLICAÇÃO (Específicas do Projeto)
# ==============================================================================

# Variável usada no app 'repositorio' para limitar o número de uploads por usuário
MAX_UPLOADS_PER_USER = 1000
# Variável usada no app 'coral' para definir o número de itens na homepage
HOMEPAGE_ITEMS_LIMIT = 9

# Aumenta o limite de memória para 50MB (ajuste conforme necessário)
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800

# Aumenta o limite de campos para 2000
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000