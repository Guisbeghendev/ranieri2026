from pathlib import Path
import os
import environ

# ==============================================================================
# 1. SETUP BÁSICO E VARIÁVEIS DE AMBIENTE
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    REDIS_URL=(str, 'redis://localhost:6379/1'),
    CELERY_BROKER_URL=(str, 'redis://localhost:6379/0'),
    CELERY_RESULT_BACKEND=(str, 'redis://localhost:6379/0')
)

environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['.escolajoseranieri.com.br', '147.93.88.204'])

# ==============================================================================
# 2. DEFINIÇÃO DE APLICATIVOS
# ==============================================================================

INSTALLED_APPS = [
    'daphne',  # Obrigatório antes do staticfiles para Channels
    'users',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'formtools',
    'core',
    'storages',
    'channels',
    'historia',
    'coral',
    'sim_cozinha',
    'brinc_dialogando',
    'mensagens',
    'suporte',
    'galerias',
    'repositorio.apps.RepositorioConfig',
    'django_celery_beat',
    'django_celery_results',
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
ASGI_APPLICATION = 'config.asgi.application'

# ==============================================================================
# 3. BANCO DE DADOS
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
# 6. ARQUIVOS ESTÁTICOS E MÍDIA (S3 HÍBRIDO)
# ==============================================================================

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Mídia Local (Fallback/Padrão)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- Configurações S3 ---
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default=None)
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default=None)
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default=None)
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='sa-east-1')
AWS_S3_QUERYSTRING_AUTH = True
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_S3_FILE_OVERWRITE = False

# Gestão de Storages (Conforme Guisbeghen)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "repositorio_s3": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
}

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
# 10. CONFIGURAÇÕES DO DJANGO CHANNELS
# ==============================================================================

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [env('REDIS_URL')],
        },
    },
}

# ==============================================================================
# 11. CONFIGURAÇÕES CELERY (REVISADO)
# ==============================================================================

# Otimização: Centralizando no Redis para evitar gargalo de escrita no Postgres
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

CELERY_TIMEZONE = TIME_ZONE
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# IMPORTANTE: Aumentar visibilidade para evitar que tarefas sumam em filas longas
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 7200, # 2 horas
    'socket_timeout': 30,
    'socket_connect_timeout': 30,
}

# Controle de Concorrência
CELERY_WORKER_CONCURRENCY = 4
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = False # Mudado para False para garantir enfileiramento imediato

# Limites de Tempo
CELERY_TASK_SOFT_TIME_LIMIT = 600
CELERY_TASK_TIME_LIMIT = 900

CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ==============================================================================
# 12. CONFIGURAÇÕES DE EMAIL
# ==============================================================================

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ==============================================================================
# 13. CONFIGURAÇÕES DA APLICAÇÃO
# ==============================================================================

HOMEPAGE_ITEMS_LIMIT = 9
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000


# ==============================================================================
# 14. LOGGING
# ==============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'django_debug.log'),
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}