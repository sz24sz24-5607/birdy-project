"""
Management Command - Generiere Thumbnails für vorhandene Videos
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from media_manager.models import Video
from hardware.camera import CameraController
from pathlib import Path


class Command(BaseCommand):
    help = 'Generiert Thumbnails für Videos ohne Thumbnail'

    def handle(self, *args, **options):
        videos = Video.objects.filter(thumbnail_frame__isnull=True) | Video.objects.filter(thumbnail_frame='')
        count = 0

        camera = CameraController()

        for video in videos:
            if not video.file:
                self.stdout.write(f"Überspringe {video.filename} - keine Datei")
                continue

            try:
                # Pfad zum Video
                video_path = Path(video.file.path)
                if not video_path.exists():
                    self.stdout.write(f"Datei nicht gefunden: {video_path}")
                    continue

                # Thumbnail generieren
                timestamp = video.timestamp
                date_path = timestamp.strftime('%Y/%m/%d')
                filename_base = timestamp.strftime('%Y%m%d_%H%M%S')
                thumbnail_filename = f"{filename_base}_thumb.jpg"
                thumbnail_path = settings.USB_STORAGE_PATH / 'video_thumbnails' / date_path / thumbnail_filename

                # Frame extrahieren
                frame_path = camera.extract_best_frame(video_path, thumbnail_path)

                if frame_path and frame_path.exists():
                    # Relativer Pfad zu MEDIA_ROOT
                    relative_path = str(Path('video_thumbnails') / date_path / thumbnail_filename)
                    video.thumbnail_frame = relative_path
                    video.save()
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f'Thumbnail erstellt: {video.filename}'))
                else:
                    self.stdout.write(self.style.WARNING(f'Konnte kein Thumbnail erstellen: {video.filename}'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Fehler bei {video.filename}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'{count} Thumbnails erstellt'))
