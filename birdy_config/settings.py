"""
Birdy Django Settings
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-dev-only-key')
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'rest_framework',
    'corsheaders',
    'django_filters',
    
    'sensors.apps.SensorsConfig',
    'media_manager.apps.MediaManagerConfig',
    'species.apps.SpeciesConfig',
    'api.apps.ApiConfig',
    'homeassistant.apps.HomeassistantConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'birdy_config.urls'

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

WSGI_APPLICATION = 'birdy_config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'birdy_db',
        'USER': 'birdy',
        'PASSWORD': os.environ.get('DB_PASSWORD', 'birdy_secure_password'),
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'de-ch'
TIME_ZONE = 'Europe/Zurich'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = Path('/mnt/birdy_storage')

# USB Storage - Photos und Videos auf USB Stick
USB_STORAGE_PATH = Path('/mnt/birdy_storage')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ]
}

CORS_ALLOW_ALL_ORIGINS = DEBUG

# Celery - REDIS (WICHTIG!)
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Queue Konfiguration für Kamera-Limitierung
# bird_detection Queue: Nur 1 parallele Task (1 Kamera)
# default Queue: Für alle anderen Tasks (Sensoren, MQTT, etc.)
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_QUEUES = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'bird_detection': {
        'exchange': 'bird_detection',
        'routing_key': 'bird_detection',
    },
}

# Celery Beat Schedule - Periodische Tasks
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Weight Messungen werden direkt in start_birdy gemacht (GPIO Zugriff nur in einem Prozess)
    'update-sensor-status-every-60-seconds': {
        'task': 'sensors.tasks.update_sensor_status_task',
        'schedule': 60.0,  # Alle 60 Sekunden
    },
    'publish-mqtt-status-every-60-seconds': {
        'task': 'homeassistant.tasks.publish_status_task',
        'schedule': 60.0,  # Alle 60 Sekunden
    },
    'update-statistics-at-midnight': {
        'task': 'species.tasks.update_statistics_task',
        'schedule': crontab(hour=0, minute=5),  # Täglich um 00:05 Uhr
    },
}

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
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'birdy.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'birdy': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

BIRDY_SETTINGS = {
    'WEIGHT_SENSOR_DT_PIN': 5,
    'WEIGHT_SENSOR_SCK_PIN': 6,
    'PIR_SENSOR_PIN': 17,
    'CAMERA_RESOLUTION': (1280, 720),
    'CAMERA_FRAMERATE': 15,
    'PRE_TRIGGER_SECONDS': 3,
    'RECORDING_DURATION_SECONDS': 4,  # Gekürzt von 10s auf 4s
    'MIN_CONFIDENCE_THRESHOLD': 0.7,
    'MIN_CONFIDENCE_SPECIES': 0.5,  # Minimale Confidence für gültigen Besuch (50%)
    'ML_MODEL_PATH': BASE_DIR / 'ml_models' / 'bird_classifier.tflite',

    # MQTT Home Assistant Integration
    'MQTT_BROKER': os.environ.get('MQTT_BROKER', '192.168.178.150'),
    'MQTT_PORT': int(os.environ.get('MQTT_PORT', '1883')),
    'MQTT_USERNAME': os.environ.get('MQTT_USERNAME', 'mqtt-user'),
    'MQTT_PASSWORD': os.environ.get('MQTT_PASSWORD', ''),
    'MQTT_TOPIC_PREFIX': 'birdy',

    # Base URL für Media-Links (z.B. in Home Assistant)
    'BIRDY_BASE_URL': os.environ.get('BIRDY_BASE_URL', 'http://192.168.178.132:8000'),
}