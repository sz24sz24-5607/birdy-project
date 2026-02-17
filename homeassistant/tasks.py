"""
Celery Tasks für Home Assistant
"""
import json
import logging
import os
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger('birdy')


@shared_task
def publish_status_task():
    """Publiziere Status zu Home Assistant (alle 60s via Celery Beat)"""
    try:
        import paho.mqtt.publish as publish
        from sensors.models import SensorStatus
        from species.models import BirdDetection
        from django.db.models import Count, Avg
        from django.conf import settings

        # Verwende direkt paho publish (single shot) statt persistente Verbindung
        # Dies vermeidet Probleme mit mehreren Worker-Prozessen
        broker = settings.BIRDY_SETTINGS['MQTT_BROKER']
        port = settings.BIRDY_SETTINGS['MQTT_PORT']
        username = settings.BIRDY_SETTINGS['MQTT_USERNAME']
        password = settings.BIRDY_SETTINGS['MQTT_PASSWORD']
        topic_prefix = settings.BIRDY_SETTINGS['MQTT_TOPIC_PREFIX']
        base_url = settings.BIRDY_SETTINGS['BIRDY_BASE_URL']

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
            species__isnull=False
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

        # 5. Letzte Detektion (Species + Attribute + Kamerabild)
        last_detection = BirdDetection.objects.filter(
            processed=True,
            species__isnull=False
        ).select_related('species', 'photo', 'video').first()

        if last_detection and last_detection.species:
            messages.append({
                'topic': f"{topic_prefix}/bird/species",
                'payload': last_detection.species.common_name_de,
                'retain': True
            })

            attributes = {
                "species": last_detection.species.common_name_de,
                "scientific_name": last_detection.species.scientific_name,
                "confidence": f"{last_detection.confidence:.2%}",
                "timestamp": last_detection.timestamp.isoformat(),
            }
            if last_detection.photo and last_detection.photo.file_url:
                attributes["photo_url"] = f"{base_url}{last_detection.photo.file_url}"
            if last_detection.video and last_detection.video.file_url:
                attributes["video_url"] = f"{base_url}{last_detection.video.file_url}"

            messages.append({
                'topic': f"{topic_prefix}/bird/attributes",
                'payload': json.dumps(attributes),
                'retain': True
            })

        # Publiziere alle Text-Messages in einem Batch
        publish.multiple(messages, hostname=broker, port=port, auth=auth)

        # Kamerabild separat (Binary, nicht im Batch möglich)
        if last_detection and last_detection.photo:
            photo_path = last_detection.photo.file_path
            if photo_path and os.path.exists(photo_path):
                try:
                    with open(photo_path, 'rb') as f:
                        image_data = f.read()
                    publish.single(
                        f"{topic_prefix}/camera/last_visitor",
                        payload=image_data,
                        retain=True,
                        hostname=broker, port=port, auth=auth
                    )
                except Exception as e:
                    logger.error(f"Failed to publish camera image: {e}")

        logger.debug(f"Published MQTT status: weight={status.current_weight_grams:.1f}g, visits={total_visits}, bird_present={status.bird_present}")

    except Exception as e:
        logger.error(f"Error publishing to MQTT: {e}")
        import traceback
        logger.error(traceback.format_exc())