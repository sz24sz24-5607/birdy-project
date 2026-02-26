"""
Bird Detection Service - Orchestriert gesamten Detection-Workflow
"""
import logging
import shutil
import threading
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

        # WICHTIG: Starte Detection in separatem Thread um PIR Monitoring nicht zu blockieren!
        # Grund: Video-Aufzeichnung dauert ~8 Sekunden und würde PIR "No Motion" Events verzögern
        # Kamera läuft nur in diesem Prozess, Celery Worker hat keinen Zugriff
        # Da nur 1 Kamera existiert, können sowieso keine parallelen Detections laufen
        detection_thread = threading.Thread(
            target=self.process_detection,
            args=(pir_event.id,),
            daemon=False,  # Nicht daemon, damit Thread zu Ende läuft
            name=f"BirdDetection-{pir_event.id}"
        )
        detection_thread.start()
        logger.debug(f"Detection thread started: {detection_thread.name}")
    
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
            video_filename = f"{filename_base}.mp4"
            video_path = self.storage_path / 'videos' / date_path / video_filename

            logger.info(f"Recording video: {video_path}")
            recorded_video = camera.record_video_with_pretrigger(video_path)

            if not recorded_video:
                logger.error("Video recording failed")
                return

            # Extrahiere Kandidaten-Frames für Best-Frame-Selektion
            logger.info("Extracting candidate frames...")
            candidate_frames = camera.extract_candidate_frames(recorded_video, n_frames=8)

            if not candidate_frames:
                logger.error("Candidate frame extraction failed")
                recorded_video.unlink(missing_ok=True)
                return

            temp_dir = candidate_frames[0].parent

            # Klassifiziere alle Frames, wähle den mit höchster Konfidenz
            logger.info(f"Classifying {len(candidate_frames)} candidate frames...")
            classification = None
            species = None
            is_valid_visit = False
            best_frame = None
            best_confidence = -1.0
            total_processing_ms = 0
            min_confidence = settings.BIRDY_SETTINGS['MIN_CONFIDENCE_SPECIES']

            if classifier.is_initialized:
                for i, frame_path in enumerate(candidate_frames):
                    result = classifier.classify(frame_path, top_k=5)
                    if not result:
                        continue

                    total_processing_ms += result['processing_time_ms']
                    top_pred = result['top_prediction']
                    confidence = top_pred['confidence']
                    is_background = top_pred['label'].lower() == 'background'

                    logger.debug(
                        f"Frame {i+1}/{len(candidate_frames)}: "
                        f"{top_pred['label']} ({confidence:.1%})"
                        + (" [background]" if is_background else "")
                    )

                    if not is_background and confidence > best_confidence:
                        best_confidence = confidence
                        best_frame = frame_path
                        classification = result

                if best_frame is not None and best_confidence >= min_confidence:
                    is_valid_visit = True
                    classification['processing_time_ms'] = total_processing_ms
                    species_label = classification['top_prediction']['label']

                    species, created = BirdSpecies.objects.get_or_create(
                        scientific_name=species_label,
                        defaults={
                            'common_name_de': species_label,
                            'inat_taxon_id': classification['top_prediction']['class_id']
                        }
                    )
                    if created:
                        logger.info(f"New species discovered: {species_label}")

                    logger.info(
                        f"Best frame: {best_frame.name} → "
                        f"{species_label} ({best_confidence:.1%}) "
                        f"[{total_processing_ms}ms total]"
                    )
                else:
                    reason = (
                        f"best confidence too low ({best_confidence:.1%} < {min_confidence:.1%})"
                        if best_frame else "no valid (non-background) frame found"
                    )
                    logger.info(f"Not a valid visit: {reason}")

            # Kein gültiger Besuch → Temp-Frames + Video löschen, kein DB-Eintrag
            if not is_valid_visit:
                shutil.rmtree(temp_dir, ignore_errors=True)
                recorded_video.unlink(missing_ok=True)
                logger.info("No valid detection – files deleted, no DB entries created")
                return

            # Bestes Frame an finalen Pfad kopieren
            photo_filename = f"{filename_base}.jpg"
            photo_path = self.storage_path / 'photos' / date_path / photo_filename
            photo_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(best_frame, photo_path)

            # Temp-Frames aufräumen
            shutil.rmtree(temp_dir, ignore_errors=True)

            # Ab hier: gültiger Besuch → DB-Einträge erstellen

            # latest.mp4 aktualisieren (für HA Media Browser via NFS)
            # Kopie statt Symlink, da vfat keine Symlinks unterstützt
            latest_path = self.storage_path / 'videos' / 'latest.mp4'
            try:
                shutil.copy2(recorded_video, latest_path)
                logger.debug(f"Updated latest.mp4 → {recorded_video.name}")
            except Exception as e:
                logger.warning(f"Could not update latest.mp4: {e}")

            # Video DB Entry
            # Nutze tatsächlichen Dateinamen (könnte .mp4 oder .h264 sein, falls ffmpeg fehlschlägt)
            actual_filename = recorded_video.name
            relative_video_path = str(Path('videos') / date_path / actual_filename)

            video_obj = Video.objects.create(
                timestamp=timestamp,
                file=relative_video_path,
                filename=actual_filename,
                filesize_bytes=recorded_video.stat().st_size if recorded_video.exists() else 0,
                duration_seconds=settings.BIRDY_SETTINGS['RECORDING_DURATION_SECONDS'],
                width=settings.BIRDY_SETTINGS['CAMERA_RESOLUTION'][0],
                height=settings.BIRDY_SETTINGS['CAMERA_RESOLUTION'][1],
                framerate=settings.BIRDY_SETTINGS['CAMERA_FRAMERATE'],
                codec='h264'
            )

            # Photo DB Entry
            from PIL import Image
            try:
                with Image.open(photo_path) as img:
                    width, height = img.size
            except:
                width, height = 0, 0

            relative_photo_path = str(Path('photos') / date_path / photo_filename)

            photo_obj = Photo.objects.create(
                timestamp=timestamp,
                file=relative_photo_path,
                filename=photo_filename,
                filesize_bytes=photo_path.stat().st_size if photo_path.exists() else 0,
                width=width,
                height=height
            )

            # Video-Thumbnail setzen
            video_obj.thumbnail_frame = relative_photo_path
            video_obj.save()

            # BirdDetection Entry
            detection = BirdDetection.objects.create(
                timestamp=timestamp,
                species=species,
                confidence=classification['top_prediction']['confidence'],
                top_predictions=classification['top_k_predictions'],
                photo=photo_obj,
                video=video_obj,
                pir_event=pir_event,
                processed=True,
                processing_time_ms=classification['processing_time_ms']
            )

            logger.info(f"Detection saved: {species.common_name_de}")

            # Statistiken aktualisieren
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