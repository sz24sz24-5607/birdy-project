"""
Celery Configuration mit optionalen Periodic Tasks
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'birdy_config.settings')

app = Celery('birdy')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.broker_connection_retry_on_startup = True

# Task Queue Konfiguration
# Bird Detection Queue: Nur 1 Task parallel wegen einzelner Kamera
app.conf.task_routes = {
    'services.bird_detection.process_bird_detection': {
        'queue': 'bird_detection',
    },
}

# Autodiscover tasks in installed apps
app.autodiscover_tasks()

# Explizit importiere tasks aus services (nicht in INSTALLED_APPS)
app.conf.imports = ('services.bird_detection',)

# OPTIONAL: Periodic Tasks nur aktivieren wenn gewünscht
# Auskommentieren wenn start_birdy läuft!
ENABLE_PERIODIC_TASKS = True

if ENABLE_PERIODIC_TASKS:
    app.conf.beat_schedule = {
        'update-sensor-status': {
            'task': 'sensors.tasks.update_sensor_status_task',
            'schedule': 60.0,
        },
        'update-daily-statistics': {
            'task': 'species.tasks.update_statistics_task',
            'schedule': crontab(hour=0, minute=1),
        },
        'publish-ha-status': {
            'task': 'homeassistant.tasks.publish_status_task',
            'schedule': 300.0,
        },
        'measure-weight-backup': {
            'task': 'sensors.tasks.measure_weight_task',
            'schedule': 300.0,  # 5 Minuten - Backup Task (liest nur aus DB)
        },
    }   


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')