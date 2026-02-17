"""
Celery Tasks für Home Assistant
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger('birdy')


@shared_task
def publish_status_task():
    """Publiziere Status zu Home Assistant"""
    try:
        import paho.mqtt.publish as publish
        from sensors.models import SensorStatus
        from species.models import BirdDetection
        from django.db.models import Count, Avg
        from django.conf import settings
        import json

        # Verwende direkt paho publish (single shot) statt persistente Verbindung
        # Dies vermeidet Probleme mit mehreren Worker-Prozessen
        broker = settings.BIRDY_SETTINGS['MQTT_BROKER']
        port = settings.BIRDY_SETTINGS['MQTT_PORT']
        username = settings.BIRDY_SETTINGS['MQTT_USERNAME']
        password = settings.BIRDY_SETTINGS['MQTT_PASSWORD']
        topic_prefix = settings.BIRDY_SETTINGS['MQTT_TOPIC_PREFIX']

        auth = {'username': username, 'password': password} if username and password else None

        status = SensorStatus.get_current()
        today = timezone.now().date()

        # Bereite alle Messages vor
        messages = []

        # 1. Gewicht
        if status.current_weight_grams is not None:
            messages.append({
                'topic': f"{topic_prefix}/feed/weight",
                'payload': f"{status.current_weight_grams:.1f}",
                'retain': False
            })

        # 2. Bird Present
        messages.append({
            'topic': f"{topic_prefix}/bird/detected",
            'payload': "ON" if status.bird_present else "OFF",
            'retain': False
        })

        # 3. Besuche heute (nur mit gültiger Spezies)
        total_visits = BirdDetection.objects.filter(
            timestamp__date=today,
            processed=True,
            species__isnull=False  # Nur gültige Besuche (>=50% confidence, kein background)
        ).count()

        messages.append({
            'topic': f"{topic_prefix}/stats/today",
            'payload': str(total_visits),
            'retain': False
        })

        # 4. Daily stats (JSON)
        top_species = BirdDetection.objects.filter(
            timestamp__date=today,
            processed=True,
            species__isnull=False
        ).values('species__common_name_de', 'species__scientific_name').annotate(
            visits=Count('id'),
            avg_conf=Avg('confidence')
        ).order_by('-visits')[:5]

        stats_data = {
            "date": today.isoformat(),
            "total_visits": total_visits,
            "top_species": [
                {
                    "name": stat['species__common_name_de'],
                    "scientific_name": stat['species__scientific_name'],
                    "visits": stat['visits'],
                    "avg_confidence": f"{stat['avg_conf']:.2%}" if stat['avg_conf'] else "0%"
                }
                for stat in top_species
            ]
        }

        messages.append({
            'topic': f"{topic_prefix}/stats/daily",
            'payload': json.dumps(stats_data),
            'retain': False
        })

        # Publiziere alle Messages in einem Batch
        publish.multiple(messages, hostname=broker, port=port, auth=auth)

        logger.debug(f"Published MQTT status: weight={status.current_weight_grams:.1f}g, visits={total_visits}, bird_present={status.bird_present}")

    except Exception as e:
        logger.error(f"Error publishing to MQTT: {e}")
        import traceback
        logger.error(traceback.format_exc())