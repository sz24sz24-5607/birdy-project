"""
Bird Detection Service - Orchestriert gesamten Detection-Workflow
"""
import logging
from pathlib import Path
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from celery import shared_task

logger = logging.getLogger('birdy')


class BirdDetectionService:
    """Service für kompletten Vogel-Detektion Workflow"""

    def __init__(self, camera=None, classifier=None):
        self.storage_path = settings.USB_STORAGE_PATH
        self.camera = camera
        self.classifier = classifier
        
    def handle_motion_detected(self, pir_event):
        """
        Handler für PIR Motion Event - startet Detection Workflow

        Args:
            pir_event: PIREvent Model Instance
        """
        logger.info("Motion detected - starting bird detection workflow...")

        # WICHTIG: Führe Detection synchron aus (in start_birdy Prozess)
        # Grund: Kamera läuft nur in diesem Prozess, Celery Worker hat keinen Zugriff
        # Da nur 1 Kamera existiert, können sowieso keine parallelen Detections laufen
        self.process_detection(pir_event.id)
    
    def process_detection(self, pir_event_id):
        """
        Vollständiger Detection-Workflow
        
        1. Nehme Video auf (mit Pre-Trigger)
        2. Extrahiere Best Frame
        3. Klassifiziere Vogel
        4. Speichere Ergebnisse
        5. Update Statistiken
        6. Benachrichtige Home Assistant
        """
        from sensors.models import PIREvent
        from media_manager.models import Photo, Video
        from species.models import BirdDetection, BirdSpecies, DailyStatistics
        
        try:
            pir_event = PIREvent.objects.get(id=pir_event_id)

            # Hardware Instanzen nutzen (wurden an __init__ übergeben)
            camera = self.camera
            classifier = self.classifier

            if not camera:
                logger.error("Camera instance not set - must be passed to BirdDetectionService()")
                return

            logger.debug(f"Camera initialized: {camera.is_initialized}")
            logger.debug(f"Classifier initialized: {classifier.is_initialized if classifier else 'None'}")

            if not camera.is_initialized:
                logger.error("Camera not initialized (should be initialized by start_birdy)")
                return

            logger.info("Starting video recording workflow...")

            timestamp = timezone.now()
            date_path = timestamp.strftime('%Y/%m/%d')
            filename_base = timestamp.strftime('%Y%m%d_%H%M%S')

            # Video aufnehmen
            video_filename = f"{filename_base}.h264"
            video_path = self.storage_path / 'videos' / date_path / video_filename
            
            logger.info(f"Recording video: {video_path}")
            recorded_video = camera.record_video_with_pretrigger(video_path)
            
            if not recorded_video:
                logger.error("Video recording failed")
                return
            
            # Video DB Entry
            video_obj = Video.objects.create(
                timestamp=timestamp,
                usb_path=str(Path('videos') / date_path / video_filename),
                filename=video_filename,
                filesize_bytes=recorded_video.stat().st_size if recorded_video.exists() else 0,
                duration_seconds=settings.BIRDY_SETTINGS['PRE_TRIGGER_SECONDS'] + 
                               settings.BIRDY_SETTINGS['RECORDING_DURATION_SECONDS']
            )
            
            # Frame extrahieren
            photo_filename = f"{filename_base}.jpg"
            photo_path = self.storage_path / 'photos' / date_path / photo_filename
            
            logger.info(f"Extracting frame: {photo_path}")
            frame_path = camera.extract_best_frame(recorded_video, photo_path)
            
            if not frame_path:
                logger.error("Frame extraction failed")
                return
            
            # Photo DB Entry
            from PIL import Image
            try:
                with Image.open(frame_path) as img:
                    width, height = img.size
            except:
                width, height = 0, 0
            
            photo_obj = Photo.objects.create(
                timestamp=timestamp,
                usb_path=str(Path('photos') / date_path / photo_filename),
                filename=photo_filename,
                filesize_bytes=frame_path.stat().st_size if frame_path.exists() else 0,
                width=width,
                height=height
            )
            
            # Klassifizierung
            logger.info("Classifying bird species...")
            classification = None
            species = None
            
            if classifier.is_initialized:
                classification = classifier.classify(frame_path, top_k=5)
                
                if classification:
                    top_pred = classification['top_prediction']
                    species_label = top_pred['label']
                    
                    # BirdSpecies erstellen/holen
                    species, created = BirdSpecies.objects.get_or_create(
                        scientific_name=species_label,
                        defaults={
                            'common_name_de': species_label,
                            'inat_taxon_id': top_pred['class_id']
                        }
                    )
                    
                    if created:
                        logger.info(f"New species discovered: {species_label}")
            
            # BirdDetection Entry
            detection = BirdDetection.objects.create(
                timestamp=timestamp,
                species=species if classification and classifier.is_confident_detection(classification) else None,
                confidence=classification['top_prediction']['confidence'] if classification else 0,
                top_predictions=classification['top_k_predictions'] if classification else [],
                photo=photo_obj,
                video=video_obj,
                pir_event=pir_event,
                processed=True,
                processing_time_ms=classification['processing_time_ms'] if classification else 0
            )
            
            logger.info(f"Detection saved: {species.common_name_de if species else 'Unknown'}")
            
            # Statistiken aktualisieren
            if species:
                DailyStatistics.update_for_date(timestamp.date(), species)
                logger.info("Statistics updated")
            
            # Home Assistant benachrichtigen
            try:
                from homeassistant.mqtt_client import get_mqtt_client
                mqtt = get_mqtt_client()
                
                if mqtt.is_connected:
                    mqtt.publish_bird_detected(detection)
                    logger.info("Home Assistant notified")
            except Exception as e:
                logger.error(f"Failed to notify Home Assistant: {e}")
            
            logger.info("Bird detection workflow completed successfully")
            
        except Exception as e:
            logger.error(f"Error in detection workflow: {e}", exc_info=True)


@shared_task
def process_bird_detection(pir_event_id):
    """
    Celery Task für asynchrone Verarbeitung

    HINWEIS: Dieser Task wird aktuell NICHT verwendet!
    Grund: Kamera läuft nur in start_birdy Prozess, Celery Worker hat keinen Zugriff.
    Detection läuft synchron in start_birdy.

    Dieser Task bleibt für zukünftige Verwendung (z.B. Re-Processing von Videos)

    Args:
        pir_event_id: ID des PIREvent
    """
    logger.warning("process_bird_detection task called - but detection should run in start_birdy!")
    # Nicht implementiert - würde fehlschlagen wegen Kamera-Zugriff
    pass


# Service Instance
def get_detection_service(camera=None, classifier=None):
    """
    Hole Detection Service Instance

    Args:
        camera: Camera-Instanz (von start_birdy übergeben)
        classifier: Classifier-Instanz (von start_birdy übergeben)

    Returns:
        BirdDetectionService mit Hardware-Referenzen
    """
    return BirdDetectionService(camera=camera, classifier=classifier)