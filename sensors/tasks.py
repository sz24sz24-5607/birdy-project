"""
Celery Tasks für Sensoren
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger('birdy')


@shared_task
def measure_weight_task():
    """
    Periodische Gewichtsmessung - Backup Task

    HINWEIS: Dieser Task liest nur aus der DB und macht KEINE Hardware-Zugriffe.
    Die eigentliche Gewichtsmessung erfolgt in start_birdy Loop alle 5min.
    Dieser Task dient nur als Backup um den Sensor-Status zu aktualisieren
    falls start_birdy nicht läuft.
    """
    try:
        from sensors.models import SensorStatus, WeightMeasurement

        # Lese letzte Gewichtsmessung aus DB (von start_birdy geschrieben)
        latest_measurement = WeightMeasurement.objects.order_by('-timestamp').first()

        if latest_measurement:
            # Prüfe ob Messung aktuell ist (max 10 Minuten alt)
            age_seconds = (timezone.now() - latest_measurement.timestamp).total_seconds()

            status = SensorStatus.get_current()

            if age_seconds < 600:  # 10 Minuten
                # Messung ist aktuell - Sensor läuft
                status.current_weight_grams = latest_measurement.weight_grams
                status.weight_sensor_online = True
                status.last_weight_reading = latest_measurement.timestamp
                logger.debug(f"Weight from DB: {latest_measurement.weight_grams:.1f}g (age: {age_seconds:.0f}s)")
            else:
                # Messung zu alt - start_birdy läuft vermutlich nicht
                status.weight_sensor_online = False
                logger.warning(f"Latest weight measurement is {age_seconds:.0f}s old - sensor may be offline")

            status.save()
        else:
            # Keine Messungen in DB - Sensor wurde noch nie initialisiert
            logger.debug("No weight measurements in database yet")

    except Exception as e:
        logger.error(f"Error in weight measurement backup task: {e}")


@shared_task
def update_sensor_status_task():
    """
    Update allgemeiner Sensor Status - BACKUP Task

    HINWEIS: Sensor Status wird primär von start_birdy alle 10s aktualisiert.
    Dieser Task läuft nur als Backup alle 60s und ist hauptsächlich für
    Debugging und als Fallback wenn start_birdy nicht läuft.
    """
    try:
        from sensors.models import SensorStatus

        # Dieser Task macht jetzt nichts mehr - Status wird von start_birdy aktualisiert
        # Wir loggen nur dass wir laufen, als Health-Check für Celery
        status = SensorStatus.get_current()
        logger.debug(f"Sensor status backup check (updated by start_birdy): PIR={status.pir_sensor_online}, Camera={status.camera_online}, Weight={status.weight_sensor_online}")

    except Exception as e:
        logger.error(f"Error in sensor status backup task: {e}")
