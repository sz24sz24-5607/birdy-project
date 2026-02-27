"""
Management Command - Migriere usb_path zu file Field
"""
from django.core.management.base import BaseCommand

from media_manager.models import Photo, Video


class Command(BaseCommand):
    help = 'Migriert vorhandene Photos und Videos von usb_path zu file Field'

    def handle(self, *args, **options):
        # Videos migrieren
        videos = Video.objects.filter(usb_path__isnull=False).exclude(usb_path='')
        video_count = 0

        for video in videos:
            if not video.file:
                # Kopiere usb_path zu file
                video.file = video.usb_path
                video.save()
                video_count += 1
                self.stdout.write(f"Migriert: {video.filename}")

        self.stdout.write(self.style.SUCCESS(f'{video_count} Videos migriert'))

        # Photos migrieren
        photos = Photo.objects.filter(usb_path__isnull=False).exclude(usb_path='')
        photo_count = 0

        for photo in photos:
            if not photo.file:
                # Kopiere usb_path zu file
                photo.file = photo.usb_path
                photo.save()
                photo_count += 1
                self.stdout.write(f"Migriert: {photo.filename}")

        self.stdout.write(self.style.SUCCESS(f'{photo_count} Photos migriert'))
        self.stdout.write(self.style.SUCCESS('Migration abgeschlossen!'))
