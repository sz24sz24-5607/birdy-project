"""
Raspberry Pi Camera - H.264/MP4 Video Recording
"""
import io
import logging
import subprocess
import time
from pathlib import Path

from django.conf import settings
from picamera2 import Picamera2
from PIL import Image

logger = logging.getLogger('birdy')

# Camera Worker Modus - Nutzt isolierten Prozess für bessere Stabilität
USE_CAMERA_WORKER = True


class CameraController:
    """Controller für Raspberry Pi Camera"""

    def __init__(self):
        self.camera = None
        self.is_initialized = False
        self.is_recording = False

        self.resolution = settings.BIRDY_SETTINGS['CAMERA_RESOLUTION']
        self.framerate = settings.BIRDY_SETTINGS['CAMERA_FRAMERATE']
        self.recording_duration = settings.BIRDY_SETTINGS['RECORDING_DURATION_SECONDS']

    def initialize(self):
        """Initialisiere Kamera"""
        try:
            self.camera = Picamera2()

            # Video-Config für kontinuierliche Aufnahme
            video_config = self.camera.create_video_configuration(
                main={"size": self.resolution, "format": "RGB888"},
                controls={"FrameRate": self.framerate}
            )
            self.camera.configure(video_config)
            self.camera.start()
            time.sleep(2)

            self.is_initialized = True
            logger.info(f"Camera initialized: {self.resolution} @ {self.framerate}fps")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            return False

    def capture_photo(self, output_path):
        """Fotografiere ein Einzelbild"""
        if not self.is_initialized:
            return None

        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            array = self.camera.capture_array()
            image = Image.fromarray(array)
            image.save(str(output_path), quality=95)

            logger.info(f"Photo captured: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to capture photo: {e}")
            return None

    def record_video_with_pretrigger(self, output_path):
        """
        Nehme Video auf - mit rpicam-vid, korrekte Camera-Freigabe
        """
        if not self.is_initialized:
            logger.warning("Camera not initialized")
            return None

        if self.is_recording:
            logger.warning("Already recording")
            return None

        try:
            self.is_recording = True
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mp4_path = output_path.with_suffix('.mp4')

            logger.info(f"Recording {self.recording_duration}s at {self.framerate}fps with rpicam-vid...")

            # Schließe picamera2 komplett und gebe Hardware frei
            self.camera.stop()
            self.camera.close()
            del self.camera
            time.sleep(1)  # Warte auf vollständige Freigabe
            logger.debug("Camera closed for rpicam-vid")

            # Nutze rpicam-vid direkt für Hardware-Encoding
            duration_ms = int(self.recording_duration * 1000)
            result = subprocess.run([
                'rpicam-vid',
                '--width', str(self.resolution[0]),
                '--height', str(self.resolution[1]),
                '--framerate', str(self.framerate),
                '--timeout', str(duration_ms),
                '--codec', 'h264',
                '--output', str(mp4_path),
                '--nopreview'
            ], capture_output=True, text=True)

            # Reinitialize picamera2
            self._reinitialize_camera()

            self.is_recording = False

            if result.returncode == 0 and mp4_path.exists():
                logger.info(f"Video recorded: {mp4_path} ({self.recording_duration}s)")
                return mp4_path
            else:
                logger.error(f"rpicam-vid failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Failed to record video: {e}")
            import traceback
            traceback.print_exc()
            self.is_recording = False
            # Versuche Camera wieder zu initialisieren
            try:
                self._reinitialize_camera()
            except Exception as reinit_error:
                logger.error(f"Failed to reinitialize camera: {reinit_error}")
            return None

    def _reinitialize_camera(self):
        """Reinitialize camera after rpicam-vid usage"""
        # Nach rpicam-vid braucht die Camera Hardware Zeit um freizugeben
        # Mehrere Versuche mit steigenden Wartezeiten
        max_attempts = 5
        wait_times = [2.0, 3.0, 5.0, 8.0, 15.0]

        for attempt in range(max_attempts):
            try:
                logger.debug(f"Camera reinitialization attempt {attempt + 1}/{max_attempts}")

                # Warte bevor wir versuchen die Camera zu öffnen
                time.sleep(wait_times[attempt])

                # Explizit libcamera-Prozesse killen falls hängen geblieben
                if attempt > 0:
                    try:
                        subprocess.run(['pkill', '-9', 'libcamera'], capture_output=True, timeout=1)
                        time.sleep(0.5)
                    except Exception:
                        pass

                # Create fresh camera instance
                self.camera = Picamera2()

                # Configure for video
                video_config = self.camera.create_video_configuration(
                    main={"size": self.resolution, "format": "RGB888"},
                    controls={"FrameRate": self.framerate}
                )
                self.camera.configure(video_config)
                self.camera.start()
                time.sleep(1.0)  # Längere Wartezeit für Stabilität

                logger.info(f"Camera reinitialized successfully after attempt {attempt + 1}")
                return  # Erfolg!

            except Exception as e:
                logger.warning(f"Camera reinitialization attempt {attempt + 1} failed: {e}")

                # Versuche Picamera2 Instanz zu cleanen
                try:
                    if hasattr(self, 'camera') and self.camera:
                        self.camera.close()
                except Exception:
                    pass
                self.camera = None

                if attempt < max_attempts - 1:
                    continue  # Versuche es nochmal
                else:
                    # Letzter Versuch fehlgeschlagen
                    logger.error(f"Camera reinitialization failed after {max_attempts} attempts")
                    self.is_initialized = False
                    raise

    def extract_best_frame(self, video_path, output_path):
        """Extrahiere mittleres Frame aus MP4 Video mit ffmpeg"""
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Extrahiere Frame in der Mitte der Aufnahme
            middle_time = self.recording_duration / 2.0

            result = subprocess.run([
                'ffmpeg', '-y',
                '-ss', str(middle_time),
                '-i', str(video_path),
                '-frames:v', '1',
                '-q:v', '2',
                str(output_path)
            ], capture_output=True, text=True)

            if result.returncode == 0 and output_path.exists():
                logger.info(f"Frame extracted: {output_path} (at {middle_time:.1f}s)")
                return output_path
            else:
                logger.error(f"ffmpeg extraction failed: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Failed to extract frame: {e}")
            import traceback
            traceback.print_exc()
            return None

    def extract_candidate_frames(self, video_path, n_frames=8):
        """
        Extrahiere N gleichmässig verteilte Frames für Best-Frame-Selektion.

        Args:
            video_path: Pfad zum MP4-Video
            n_frames: Anzahl Frames (default: 8 → alle 0.5s bei 4s-Video)

        Returns:
            list[Path]: Temp-Frame-Pfade (müssen vom Aufrufer gelöscht werden),
                        oder [] bei Fehler
        """
        import tempfile
        try:
            video_path = Path(video_path)
            temp_dir = Path(tempfile.mkdtemp(prefix='birdy_frames_'))

            fps = n_frames / self.recording_duration  # z.B. 8/4 = 2.0 fps

            result = subprocess.run([
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-vf', f'fps={fps}',
                '-q:v', '2',
                str(temp_dir / 'frame_%02d.jpg')
            ], capture_output=True, text=True)

            if result.returncode == 0:
                frames = sorted(temp_dir.glob('frame_*.jpg'))
                logger.info(f"Extracted {len(frames)} candidate frames from {video_path.name}")
                return frames
            else:
                logger.error(f"ffmpeg multi-frame extraction failed: {result.stderr}")
                temp_dir.rmdir()
                return []

        except Exception as e:
            logger.error(f"Failed to extract candidate frames: {e}")
            return []

    def get_stream_frame(self):
        """Live-Stream Frame"""
        if not self.is_initialized:
            return None

        try:
            array = self.camera.capture_array()
            image = Image.fromarray(array)

            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Failed to get stream frame: {e}")
            return None

    def cleanup(self):
        """Cleanup"""
        try:
            if self.camera:
                if self.is_recording:
                    self.is_recording = False
                self.camera.stop()
                self.camera.close()
                logger.info("Camera closed")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


_camera_instance = None

def get_camera(auto_init=True):
    """
    Hole Singleton Instance der Kamera

    Args:
        auto_init: Wenn True, initialisiere Kamera automatisch (Standard: True)
                  Setze auf False wenn nur Referenz benötigt wird

    Returns:
        CameraController oder CameraWorkerProcess je nach Konfiguration
    """
    global _camera_instance

    # Nutze Worker-Prozess wenn aktiviert
    if USE_CAMERA_WORKER:
        from hardware.camera_worker import get_camera_worker
        return get_camera_worker()

    # Fallback auf alte Implementierung
    if _camera_instance is None:
        _camera_instance = CameraController()
        if auto_init:
            _camera_instance.initialize()
    elif auto_init and not _camera_instance.is_initialized:
        _camera_instance.initialize()
    return _camera_instance
