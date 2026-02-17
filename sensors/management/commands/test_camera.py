# --- sensors/management/commands/test_camera.py ---
from django.core.management.base import BaseCommand
from pathlib import Path


class Command(BaseCommand):
    help = 'Testet die Raspberry Pi Kamera'

    def handle(self, *args, **options):
        from hardware.camera import get_camera
        
        self.stdout.write(self.style.SUCCESS('=== Kamera Test ==='))
        
        camera = get_camera()
        
        if not camera.is_initialized:
            self.stdout.write(self.style.ERROR('Kamera konnte nicht initialisiert werden'))
            return
        
        # Test-Verzeichnis
        test_dir = Path('/tmp/birdy_test')
        test_dir.mkdir(exist_ok=True)
        
        # 1. Foto Test
        self.stdout.write('\n1. Fotografiere Testbild...')
        photo_path = test_dir / 'test_photo.jpg'
        result = camera.capture_photo(photo_path)
        
        if result:
            self.stdout.write(self.style.SUCCESS(f'✓ Foto gespeichert: {photo_path}'))
        else:
            self.stdout.write(self.style.ERROR('✗ Foto fehlgeschlagen'))
        
        # 2. Video Test
        self.stdout.write('\n2. Nehme 5s Testvideo auf...')
        video_path = test_dir / 'test_video.h264'
        
        # Temporär Recording Duration ändern
        original_duration = camera.recording_duration
        camera.recording_duration = 5
        
        result = camera.record_video_with_pretrigger(video_path)
        camera.recording_duration = original_duration
        
        if result:
            self.stdout.write(self.style.SUCCESS(f'✓ Video gespeichert: {video_path}'))
            
            # Frame extrahieren
            self.stdout.write('\n3. Extrahiere Frame aus Video...')
            frame_path = test_dir / 'test_frame.jpg'
            frame = camera.extract_best_frame(video_path, frame_path)
            
            if frame:
                self.stdout.write(self.style.SUCCESS(f'✓ Frame gespeichert: {frame_path}'))
        else:
            self.stdout.write(self.style.ERROR('✗ Video fehlgeschlagen'))
        
        self.stdout.write(self.style.SUCCESS('\n=== Test abgeschlossen ==='))
        self.stdout.write(f'Testdateien in: {test_dir}')
        
        camera.cleanup()