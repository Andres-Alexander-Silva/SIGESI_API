from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================
# SEGURIDAD
# ============================================
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# ============================================
# ENTORNO
# ============================================
RENDER = config('RENDER', default=False, cast=bool)

# ============================================
# APLICACIONES
# ============================================
ASGI_APPS = [
    'daphne',
    'channels',
]

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_yasg',
]

LOCAL_APPS = [
    'apps.sigesi'
]

INSTALLED_APPS = ASGI_APPS + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ============================================
# MIDDLEWARE
# ============================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

ASGI_APPLICATION = 'config.asgi.application'

WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

# ============================================
# BASE DE DATOS
# ============================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='semilleros_db'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600 if not DEBUG else 0,
    }
}

# ============================================
# VALIDACIÓN DE CONTRASEÑAS
# ============================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============================================
# INTERNACIONALIZACIÓN
# ============================================
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# ============================================
# ARCHIVOS ESTÁTICOS Y MEDIA
# ============================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================
# DJANGO REST FRAMEWORK
# ============================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.sigesi.middleware.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
        'apps.sigesi.decorators.permissions.HasRolePermission',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ) if not DEBUG else (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
}

# ============================================
# JWT
# ============================================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ============================================
# SWAGGER
# ============================================
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
        }
    },
    'USE_SESSION_AUTH': False,
}

# ============================================
# CORS
# ============================================
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://localhost:5173',
    cast=Csv()
)

# ============================================
# CHANNELS Y WEBSOCKETS
# ============================================
# URL única de Redis, reutilizada por Channels y Celery para que nunca
# diverjan. En Render se provee REDIS_URL; en local se compone desde
# REDIS_HOST/REDIS_PORT (la base 0 es la convención por defecto).
if RENDER:
    REDIS_URL = config('REDIS_URL', default='redis://127.0.0.1:6379/0')
else:
    REDIS_URL = config(
        'REDIS_URL',
        default=f"redis://{config('REDIS_HOST', default='127.0.0.1')}:{config('REDIS_PORT', default='6379')}/0",
    )

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
        },
    },
}

# ============================================
# MODELO DE USUARIO PERSONALIZADO
# ============================================
AUTH_USER_MODEL = 'sigesi.User'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================
# SEGURIDAD EN PRODUCCIÓN
# ============================================
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# ============================================
# LOGGING (para ver errores en Render)
# ============================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ============================================
# CONFIGURACIÓN DE CORREO (SMTP)
# ============================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='SIGESI <noreply@sigesi.com>')
# Sin timeout, smtplib espera indefinidamente si el host SMTP no responde
# (puerto bloqueado en producción) y la petición HTTP nunca termina.
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=15, cast=int)
# Estrategia de envío del correo (ver apps/sigesi/utils/email_service.py):
#   'celery' -> tarea en el worker Celery (durable, con reintentos)  [producción]
#   'thread' -> hilo en segundo plano, sin infraestructura extra     [local]
#   'sync'   -> en línea dentro de la petición                       [tests]
EMAIL_DELIVERY = config('EMAIL_DELIVERY', default='thread')

# ============================================
# CELERY (cola de tareas asíncronas)
# ============================================
# Reutiliza la misma instancia de Redis que Channels (ver REDIS_URL arriba).
# Solo broker: el correo es "fire-and-forget", no necesitamos backend de
# resultados.
CELERY_BROKER_URL = REDIS_URL
CELERY_TASK_IGNORE_RESULT = True
# Reintenta la conexión al broker al arrancar el worker (evita fallo si Redis
# tarda en estar disponible en el deploy).
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
# No bloquear si el broker está caído al encolar: el dispatcher hace fallback.
CELERY_BROKER_TRANSPORT_OPTIONS = {'socket_connect_timeout': 5}
# En tests, ejecuta las tareas en línea (sin worker ni broker).
CELERY_TASK_ALWAYS_EAGER = config('CELERY_TASK_ALWAYS_EAGER', default=False, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True

# ============================================
# FRONTEND
# ============================================
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')
