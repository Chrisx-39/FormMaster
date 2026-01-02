"""
Formwork & Scaffolding Management System - Settings
This module loads the appropriate settings based on the environment.
"""

import os
from pathlib import Path
from decouple import config, Csv
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
import dj_database_url
import logging

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables
ENVIRONMENT = config('ENVIRONMENT', default='development')
DEBUG = True


SECRET_KEY = config('SECRET_KEY', default='django-insecure-development-key-change-in-production')

# Security Settings
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Third party apps
    'crispy_forms',
    'crispy_tailwind',
    'django_extensions',
    'django_filters',
    'import_export',
    'widget_tweaks',
    'django_celery_beat',
    'django_celery_results',
    'rest_framework',
    'corsheaders',
    'django_cleanup.apps.CleanupConfig',
    
    # Local apps
    'apps.accounts',
    'apps.core',
    'apps.inventory',
    'apps.hiring',
    'apps.delivery',
    'apps.finance',
    'apps.documents',
    'apps.reporting',
    'apps.api',
    'apps.clients',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Add debug toolbar in development
if DEBUG and ENVIRONMENT == 'development':
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

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
                'apps.core.context_processors.user_role_processor',
                'apps.core.context_processors.system_stats_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database Configuration
# Use DATABASE_URL environment variable or fallback to SQLite for development
DATABASE_URL = config('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')

if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = config('LANGUAGE_CODE', default='en-us')
TIME_ZONE = config('TIME_ZONE', default='UTC')
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# WhiteNoise configuration for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Login/Logout URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Crispy Forms Configuration
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

"""
# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', 
    default='django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@formwork-system.com')
SERVER_EMAIL = config('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Sentry Configuration (Production only)
SENTRY_DSN = config('SENTRY_DSN', default='')
if SENTRY_DSN and not DEBUG:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=config('SENTRY_TRACES_SAMPLE_RATE', default=0.1, cast=float),
        send_default_pii=True,
        environment=ENVIRONMENT,
    )

# Security Settings (Production)
if ENVIRONMENT == 'production':
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
else:
    # Development security settings
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
"""
# Debug Toolbar Configuration (Development only)
if DEBUG and ENVIRONMENT == 'development':
    INTERNAL_IPS = ['127.0.0.1']
    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': lambda request: True,
    }

# CORS Configuration (for API if needed)
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='', cast=Csv())
CORS_ALLOW_CREDENTIALS = True

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}
"""
# Business Configuration
DOCUMENT_RETENTION_DAYS = config('DOCUMENT_RETENTION_DAYS', default=730, cast=int)  # 2 years
MINIMUM_STOCK_ALERT_PERCENTAGE = config('MINIMUM_STOCK_ALERT_PERCENTAGE', default=10, cast=int)
LATE_RETURN_PENALTY_RATE = config('LATE_RETURN_PENALTY_RATE', default=50.00, cast=float)
ADVANCE_PAYMENT_PERCENTAGE = config('ADVANCE_PAYMENT_PERCENTAGE', default=100, cast=int)
PARTIAL_PAYMENT_THRESHOLD = config('PARTIAL_PAYMENT_THRESHOLD', default=10000.00, cast=float)
TAX_RATE = config('TAX_RATE', default=0.15, cast=float)  # 15%

# File Upload Settings
MAX_UPLOAD_SIZE = config('MAX_UPLOAD_SIZE', default=5242880, cast=int)  # 5MB
ALLOWED_IMAGE_EXTENSIONS = config('ALLOWED_IMAGE_EXTENSIONS', 
    default='jpg,jpeg,png,gif', cast=Csv())
ALLOWED_DOCUMENT_EXTENSIONS = config('ALLOWED_DOCUMENT_EXTENSIONS',
    default='pdf,doc,docx,xls,xlsx', cast=Csv())

# Session Configuration
SESSION_COOKIE_AGE = config('SESSION_COOKIE_AGE', default=3600, cast=int)  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_CACHE_LOCATION', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Logging Configuration
LOG_LEVEL = config('LOG_LEVEL', default='INFO' if DEBUG else 'WARNING')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': LOG_LEVEL,
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'mail_admins'],
            'level': LOG_LEVEL,
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': True,
        },
        'celery': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': True,
        },
    },
}
"""
# Ensure logs directory exists
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Custom Settings
FORMWORK_SYSTEM = {
    'VERSION': '1.0.0',
    'NAME': 'Formwork & Scaffolding Management System',
    'SUPPORT_EMAIL': config('SUPPORT_EMAIL', default='support@formwork-system.com'),
    'SUPPORT_PHONE': config('SUPPORT_PHONE', default='+263 123 456 789'),
    'COMPANY_NAME': config('COMPANY_NAME', default='Fossil Contracting'),
    'COMPANY_ADDRESS': config('COMPANY_ADDRESS', default='123 Business Street, Harare, Zimbabwe'),
    'COMPANY_TAX_ID': config('COMPANY_TAX_ID', default='TAX-123456789'),
}
"""
# AWS S3 Configuration (Optional - for production file storage)
USE_S3 = config('USE_S3', default=False, cast=bool)

if USE_S3 and ENVIRONMENT == 'production':
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_LOCATION = 'media'
    AWS_DEFAULT_ACL = 'private'
    
    # Media files
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# PDF Generation Settings
PDF_GENERATION = {
    'TEMPLATE_DIR': BASE_DIR / 'templates' / 'pdf',
    'OUTPUT_DIR': MEDIA_ROOT / 'generated_pdfs',
    'KEEP_GENERATED': config('KEEP_GENERATED_PDFS', default=False, cast=bool),
}

# Ensure PDF output directory exists
PDF_GENERATION['OUTPUT_DIR'].mkdir(parents=True, exist_ok=True)

# Backup Configuration
BACKUP_CONFIG = {
    'ENABLED': config('BACKUP_ENABLED', default=True, cast=bool),
    'SCHEDULE': config('BACKUP_SCHEDULE', default='0 2 * * *'),  # Daily at 2 AM
    'RETENTION_DAYS': config('BACKUP_RETENTION_DAYS', default=30, cast=int),
    'LOCATION': config('BACKUP_LOCATION', default=str(BASE_DIR / 'backups')),
    'S3_BUCKET': config('BACKUP_S3_BUCKET', default=''),
}

# Alert Configuration
ALERT_CONFIG = {
    'LOW_STOCK_DAYS': config('LOW_STOCK_ALERT_DAYS', default=3, cast=int),
    'RETURN_REMINDER_DAYS': config('RETURN_REMINDER_DAYS', default=5, cast=int),
    'INVOICE_REMINDER_DAYS': config('INVOICE_REMINDER_DAYS', default=7, cast=int),
    'INSPECTION_REMINDER_DAYS': config('INSPECTION_REMINDER_DAYS', default=30, cast=int),
}

# Testing Configuration
TEST_RUNNER = 'django.test.runner.DiscoverRunner'
TEST_OUTPUT_DIR = BASE_DIR / 'test-reports'

# Performance Optimization
if ENVIRONMENT == 'production':
    # Database connection persistence
    DATABASES['default']['CONN_MAX_AGE'] = 600
    
    # Template caching
    TEMPLATES[0]['OPTIONS']['loaders'] = [
        ('django.template.loaders.cached.Loader', [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]),
    ]
"""
# Custom Middleware for request/response logging (development only)
if DEBUG and ENVIRONMENT == 'development':
    MIDDLEWARE.append('apps.core.middleware.RequestResponseLoggingMiddleware')

# Final validation
if ENVIRONMENT == 'production' and DEBUG:
    import warnings
    warnings.warn(
        "DEBUG mode is enabled in production! This is a security risk.",
        RuntimeWarning
    )

if ENVIRONMENT == 'production' and SECRET_KEY.startswith('django-insecure'):
    import warnings
    warnings.warn(
        "Default secret key is being used in production! Change it immediately.",
        RuntimeWarning
    )