"""
Django settings for backend project.
Lab Equipment Booking & Order Management System

Environment-aware: defaults are dev-friendly; production must override
``DJANGO_SECRET_KEY``, set ``DJANGO_DEBUG=False``, narrow ``ALLOWED_HOSTS`` and
``CORS_ALLOWED_ORIGINS``, and set ``DJANGO_PRODUCTION=True`` to opt into the
strict security headers below.
"""

import logging
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Core flags
# ---------------------------------------------------------------------------
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')
PRODUCTION = os.environ.get('DJANGO_PRODUCTION', 'False').lower() in ('true', '1', 'yes')

DEV_FALLBACK_SECRET = 'django-insecure-tpoy8ifpj9v@sh1qi3vo#nf!p87-@_rn(5#ff)myn&_pw%1++o'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', DEV_FALLBACK_SECRET)

if PRODUCTION and SECRET_KEY == DEV_FALLBACK_SECRET:
    raise RuntimeError(
        'DJANGO_SECRET_KEY must be set when DJANGO_PRODUCTION=True. '
        'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(50))"'
    )
if not DEBUG and SECRET_KEY == DEV_FALLBACK_SECRET:
    logging.getLogger(__name__).warning(
        'Running with DEBUG=False but the development SECRET_KEY is still in use. '
        'Set DJANGO_SECRET_KEY before deploying.',
    )

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',') if h.strip()]

if PRODUCTION and ALLOWED_HOSTS == ['*']:
    raise RuntimeError(
        'DJANGO_ALLOWED_HOSTS must be set to a comma-separated host list when '
        'DJANGO_PRODUCTION=True (wildcard "*" is rejected).'
    )

# CSRF_TRUSTED_ORIGINS is required by Django 4+ when the SPA is on a different
# scheme/host from the backend (typical: SPA on https://lims.example.com, API
# on the same host but behind a load balancer that terminates TLS).
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if o.strip()
]

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'corsheaders',
    'django_prometheus',
    # Local apps
    'users',
    'orders',
    'equipments',
    'scheduling',
    'monitoring',
    'admin_api',
]

MIDDLEWARE = [
    # Prometheus middleware MUST sandwich every other one to time the full
    # request — "Before" first, "After" last.
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise serves static files in K8s where there is no separate static
    # web server. Must come immediately after SecurityMiddleware.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'utils.request_id.RequestIDMiddleware',          # Trace correlation – first thing
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',          # CORS – before CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'monitoring.middleware.ActivityLogMiddleware',   # Last – capture authenticated user
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'

# ---------------------------------------------------------------------------
# Database – MySQL (fallback to SQLite for quick local dev)
# ---------------------------------------------------------------------------
if os.environ.get('DB_ENGINE') == 'mysql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'lab_booking'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ---------------------------------------------------------------------------
# Custom User Model
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'users.User'

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'utils.exception_handler.custom_exception_handler',
}

# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173',
    ).split(',')
    if o.strip()
]
# CORS_ALLOW_ALL_ORIGINS is intentionally never enabled.

# ---------------------------------------------------------------------------
# Redis & Celery
# ---------------------------------------------------------------------------
REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    }
}

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8 if DEBUG else 12},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'zh-hant'
TIME_ZONE = 'Asia/Taipei'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files — served by WhiteNoise in production (K8s has no static web
# server). ``collectstatic`` runs at image-build time so STATIC_ROOT is
# populated before the pod starts.
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Compressed + cache-busted filenames in production. Falls back to plain
# WhiteNoise in dev/tests so reloads stay snappy.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': (
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
            if PRODUCTION
            else 'whitenoise.storage.CompressedStaticFilesStorage'
        ),
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Security headers (active when PRODUCTION=True)
# ---------------------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

if PRODUCTION:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30        # 30 days; raise after stable
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ---------------------------------------------------------------------------
# Structured logging — JSON in production (so Loki/Cloud Logging can parse
# fields without regex). Plain text in dev for human readability.
# ---------------------------------------------------------------------------
_LOG_FORMAT_JSON = (
    '%(asctime)s %(levelname)s %(name)s %(message)s '
    '%(request_id)s %(trace_id)s %(span_id)s'
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.json.JsonFormatter',
            'format': _LOG_FORMAT_JSON,
        },
    },
    'filters': {
        'correlation': {'()': 'utils.logging_filters.CorrelationFilter'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json' if PRODUCTION else 'simple',
            'filters': ['correlation'],
        },
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO')},
        'monitoring': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'utils': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}

# ---------------------------------------------------------------------------
# Sentry – optional. Set ``SENTRY_DSN`` to enable.
# ---------------------------------------------------------------------------
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
            send_default_pii=False,
            environment=os.environ.get('SENTRY_ENVIRONMENT', 'development'),
        )
    except ImportError:
        pass
