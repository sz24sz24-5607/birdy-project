"""
Camera Worker Process - Isolierter Kamera-Prozess
Läuft unabhängig vom Hauptprozess und kann bei Fehlern neu gestartet werden
"""
import logging
import subprocess
import time
from multiprocessing import Process, Queue
from pathlib import Path

from django.conf import settings

logger = logging.getLogger('birdy')


class CameraWorkerProcess:
    """Isolierter Kamera-Prozess mit automatischem Restart"""

    def __init__(self):
        self.process = None
        self.command_queue = Queue()
        self.result_queue = Queue()
        self.is_running = False
        self.is_initialized = False  # Kompatibilität mit CameraController

        self.resolution = settings.BIRDY_SETTINGS['CAMERA_RESOLUTION']
        self.framerate = settings.BIRDY_SETTINGS['CAMERA_FRAMERATE']
        self.recording_duration = settings.BIRDY_SETTINGS['RECORDING_DURATION_SECONDS']

    def start(self):
        """Starte Camera Worker Prozess"""
        if self.process and self.process.is_alive():
            logger.warning("Camera worker already running")
            self.is_initialized = True
            return True

        try:
            self.process = Process(target=self._worker_loop, daemon=True)
            self.process.start()
            self.is_running = True
            self.is_initialized = True
            logger.info("Camera worker process started")
            return True
        except Exception as e:
            logger.error(f"Failed to start camera worker: {e}")
            self.is_running = False
            self.is_initialized = False
            return False

    def stop(self):
        """Stoppe Camera Worker Prozess"""
        if self.process and self.process.is_alive():
            self.command_queue.put(('STOP', None))
            self.process.join(timeout=5)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=2)
            self.is_running = False
            self.is_initialized = False
            logger.info("Camera worker process stopped")

    def restart(self):
        """Restart Camera Worker Prozess"""
        logger.info("Restarting camera worker...")
        self.stop()
        time.sleep(2)
        return self.start()

    def record_video_with_pretrigger(self, output_path):
        """
        Nimmt Video auf - Blockierend, wartet auf Ergebnis
        Kompatibel mit CameraController API

        Returns:
            Path zum Video oder None bei Fehler
        """
        if not self.is_running or not self.process or not self.process.is_alive():
            logger.error("Camera worker not running, attempting restart...")
            if not self.restart():
                return None

        try:
            # Leere alte Results
            while not self.result_queue.empty():
                self.result_queue.get_nowait()

            # Sende Kommando
            self.command_queue.put(('RECORD', str(output_path)))

            # Warte auf Ergebnis (mit Timeout)
            timeout = self.recording_duration + 30  # Recording + 30s Buffer
            result = self.result_queue.get(timeout=timeout)

            if result['success']:
                return Path(result['video_path'])
            else:
                logger.error(f"Recording failed: {result['error']}")
                # Bei Fehler: Restart Worker
                self.restart()
                return None

        except Exception as e:
            logger.error(f"Error in record_video: {e}")
            self.restart()
            return None

    def capture_photo(self, output_path):
        """
        Fotografiert ein Einzelbild - Blockierend

        Returns:
            Path zum Foto oder None bei Fehler
        """
        if not self.is_running or not self.process or not self.process.is_alive():
            logger.error("Camera worker not running, attempting restart...")
            if not self.restart():
                return None

        try:
            # Leere alte Results
            while not self.result_queue.empty():
                self.result_queue.get_nowait()

            # Sende Kommando
            self.command_queue.put(('PHOTO', str(output_path)))

            # Warte auf Ergebnis
            result = self.result_queue.get(timeout=10)

            if result['success']:
                return Path(result['photo_path'])
            else:
                logger.error(f"Photo capture failed: {result['error']}")
                return None

        except Exception as e:
            logger.error(f"Error in capture_photo: {e}")
            return None

    def _worker_loop(self):
        """Worker Loop - läuft in separatem Prozess"""
        # Imports müssen im Worker-Prozess sein
        from picamera2 import Picamera2

        camera = None

        try:
            # Initialisiere Kamera
            logger.info("[Worker] Initializing camera...")
            camera = Picamera2()
            video_config = camera.create_video_configuration(
                main={"size": self.resolution, "format": "RGB888"},
                controls={"FrameRate": self.framerate}
            )
            camera.configure(video_config)
            camera.start()
            time.sleep(2)
            logger.info("[Worker] Camera initialized successfully")

            # Hauptloop
            while True:
                try:
                    # Warte auf Kommando (mit Timeout für Health Check)
                    if not self.command_queue.empty():
                        cmd, data = self.command_queue.get(timeout=1)

                        if cmd == 'STOP':
                            logger.info("[Worker] Received STOP command")
                            break

                        elif cmd == 'RECORD':
                            self._record_video_worker(camera, data)

                        elif cmd == 'PHOTO':
                            self._capture_photo_worker(camera, data)

                    time.sleep(0.1)

                except Exception as e:
                    logger.error(f"[Worker] Error in main loop: {e}")
                    time.sleep(1)

        except Exception as e:
            logger.error(f"[Worker] Fatal error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            if camera:
                try:
                    camera.stop()
                    camera.close()
                    logger.info("[Worker] Camera cleaned up")
                except Exception:
                    pass

    def _record_video_worker(self, camera, output_path):
        """Nimmt Video auf - läuft im Worker-Prozess"""
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mp4_path = output_path.with_suffix('.mp4')

            logger.info(f"[Worker] Recording {self.recording_duration}s video...")

            # Schließe picamera2 für rpicam-vid
            camera.stop()
            camera.close()
            time.sleep(1)

            # Nutze rpicam-vid für Hardware-Encoding
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

            # Reinitialize camera
            camera.__init__()
            video_config = camera.create_video_configuration(
                main={"size": self.resolution, "format": "RGB888"},
                controls={"FrameRate": self.framerate}
            )
            camera.configure(video_config)
            camera.start()
            time.sleep(2)

            if result.returncode == 0 and mp4_path.exists():
                logger.info(f"[Worker] Video recorded successfully: {mp4_path}")

                self.result_queue.put({
                    'success': True,
                    'video_path': str(mp4_path),
                })
            else:
                logger.error(f"[Worker] rpicam-vid failed: {result.stderr}")
                self.result_queue.put({
                    'success': False,
                    'error': result.stderr
                })

        except Exception as e:
            logger.error(f"[Worker] Recording error: {e}")
            import traceback
            traceback.print_exc()
            self.result_queue.put({
                'success': False,
                'error': str(e)
            })

    def _capture_photo_worker(self, camera, output_path):
        """Fotografiert - läuft im Worker-Prozess"""
        try:
            from PIL import Image

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            array = camera.capture_array()
            image = Image.fromarray(array)
            image.save(str(output_path), quality=95)

            logger.info(f"[Worker] Photo captured: {output_path}")

            self.result_queue.put({
                'success': True,
                'photo_path': str(output_path)
            })

        except Exception as e:
            logger.error(f"[Worker] Photo error: {e}")
            self.result_queue.put({
                'success': False,
                'error': str(e)
            })

    def extract_best_frame(self, video_path, output_path):
        """
        Extrahiert Frame aus Video - Öffentliche API für Kompatibilität

        Args:
            video_path: Pfad zum Video
            output_path: Pfad für extrahierten Frame

        Returns:
            Path zum Frame oder None
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self._extract_frame(video_path, output_path)

            if output_path.exists():
                return output_path
            else:
                return None

        except Exception as e:
            logger.error(f"Extract frame failed: {e}")
            return None

    def extract_candidate_frames(self, video_path, n_frames=8):
        """
        Extrahiere N gleichmässig verteilte Frames für Best-Frame-Selektion.
        ffmpeg läuft als Subprocess im Hauptprozess – kein Worker-Queue nötig.

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
                logger.info(f"[Worker] Extracted {len(frames)} candidate frames from {video_path.name}")
                return frames
            else:
                logger.error(f"[Worker] ffmpeg multi-frame extraction failed: {result.stderr}")
                temp_dir.rmdir()
                return []

        except Exception as e:
            logger.error(f"[Worker] Failed to extract candidate frames: {e}")
            return []

    def get_stream_frame(self):
        """
        Live-Stream Frame - Nicht unterstützt im Worker-Modus

        Returns:
            None (Worker-Modus unterstützt kein Streaming)
        """
        logger.warning("Stream frames not supported in worker mode")
        return None

    def cleanup(self):
        """Cleanup - Kompatibilität mit CameraController"""
        self.stop()

    def is_healthy(self):
        """
        Prüfe ob Worker-Prozess gesund ist

        Returns:
            bool: True wenn Worker läuft und gesund ist
        """
        if not self.is_initialized:
            return False

        if not self.process:
            return False

        if not self.process.is_alive():
            logger.warning("Camera worker process is not alive")
            return False

        return True

    def _extract_frame(self, video_path, output_path):
        """Extrahiert Frame aus Video - Interne Funktion"""
        try:
            middle_time = self.recording_duration / 2.0

            result = subprocess.run([
                'ffmpeg', '-y',
                '-ss', str(middle_time),
                '-i', str(video_path),
                '-frames:v', '1',
                '-q:v', '2',
                str(output_path)
            ], capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"[Worker] Frame extracted: {output_path}")
            else:
                logger.error(f"[Worker] Frame extraction failed: {result.stderr}")

        except Exception as e:
            logger.error(f"[Worker] Frame extraction error: {e}")


# Singleton Instance
_camera_worker_instance = None

def get_camera_worker():
    """Hole Singleton Instance des Camera Workers"""
    global _camera_worker_instance
    if _camera_worker_instance is None:
        _camera_worker_instance = CameraWorkerProcess()
        _camera_worker_instance.start()
    return _camera_worker_instance
