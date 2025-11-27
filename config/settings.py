from pathlib import Path
import environ

# ==============================================================================
# 1. SETUP BÁSICO E VARIÁVEIS DE AMBIENTE
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False)
)

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
    # Repositório (USANDO APPS.PY PARA CARREGAR OS SIGNALS)
    'repositorio.apps.RepositorioConfig',
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
# 3. BANCO DE DADOS (Configurado MANUALMENTE para PostgreSQL via environ)
# ==============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),        # Lê do .env
        'USER': env('DB_USER'),        # Lê do .env
        'PASSWORD': env('DB_PASSWORD'),# Lê do .env
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

if USE_S3:
    # 2. Configurações do Storage (CORRIGIDO: Aponta para a classe customizada)
    DEFAULT_FILE_STORAGE = 'config.storages_conf.MediaStorage'
    STATICFILES_STORAGE = 'config.storages_conf.StaticStorage'

    # URL Base para acesso aos arquivos (necessário para que o Django gere URLs corretas)
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

    # Configurações de segurança e cache
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_DEFAULT_ACL = 'public-read'
    AWS_QUERYSTRING_AUTH = False

else:
    # Fallback para desenvolvimento local (se o S3 não estiver configurado)
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

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

ASGI_APPLICATION = 'config.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.pubsub.RedisPubSubChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# ==============================================================================
# 11. CONFIGURAÇÕES CELERY (Processamento Assíncrono)
# ==============================================================================

CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

CELERY_TASK_SOFT_TIME_LIMIT = 600
CELERY_TASK_TIME_LIMIT = 900