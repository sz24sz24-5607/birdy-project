"""
Birdy Django Production Settings
"""
import os

# Import base settings
from .settings import *  # noqa: F401, F403, F405

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-CHANGE-THIS-IN-PRODUCTION')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Allowed hosts - WICHTIG für Production!
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'raspberrypi',
    'raspberrypi.local',
    'smartfeeder',
    'smartfeeder.local',
    '192.168.178.132',
]

# CORS - Restriktiver in Production
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    # Füge hier weitere erlaubte Origins hinzu
]

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_SECURE = False  # Setze auf True wenn HTTPS verwendet wird
SESSION_COOKIE_SECURE = False  # Setze auf True wenn HTTPS verwendet wird

# Static Files mit WhiteNoise für Production
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Logging für Production - weniger verbose
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'birdy.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'birdy_error.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'birdy': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Email Configuration (optional - für Error Reports)
# ADMINS = [('Admin Name', 'admin@example.com')]
# SERVER_EMAIL = 'birdy@raspberrypi.local'

# DATABASE - Nutze die gleiche DB wie Development
# Falls du separate Production DB willst, überschreibe hier:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'birdy_production',
#         'USER': 'birdy',
#         'PASSWORD': os.environ.get('DB_PASSWORD', 'birdy_secure_password'),
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }
