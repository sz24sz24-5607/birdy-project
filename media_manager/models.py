"""
Media Manager Models - Foto und Video Verwaltung
"""
from django.db import models
from django.utils import timezone
from django.conf import settings
import os


def photo_upload_path(instance, filename):
    """Generiere Upload-Pfad für Fotos"""
    date = instance.timestamp
    return f'photos/{date.year}/{date.month:02d}/{date.day:02d}/{filename}'


def video_upload_path(instance, filename):
    """Generiere Upload-Pfad für Videos"""
    date = instance.timestamp
    return f'videos/{date.year}/{date.month:02d}/{date.day:02d}/{filename}'


class Photo(models.Model):
    """Foto eines Vogel-Besuchs"""
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # Dateipfade (entweder Django MEDIA oder USB)
    file = models.ImageField(upload_to=photo_upload_path, null=True, blank=True)
    usb_path = models.CharField(max_length=500, blank=True, help_text="Pfad auf USB Stick")
    
    # Metadaten
    filename = models.CharField(max_length=255)
    filesize_bytes = models.BigIntegerField(default=0)
    width = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    
    # Verarbeitung
    is_thumbnail_generated = models.BooleanField(default=False)
    thumbnail_path = models.CharField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"Photo {self.filename} @ {self.timestamp}"
    
    @property
    def file_path(self):
        """Vollständiger Dateipfad"""
        if self.usb_path:
            return os.path.join(settings.USB_STORAGE_PATH, self.usb_path)
        elif self.file:
            return self.file.path
        return None
    
    @property
    def file_url(self):
        """URL für Web-Zugriff"""
        if self.file:
            return self.file.url
        # Für USB-Dateien müsste ein separater View erstellt werden
        return None
    
    def get_filesize_display(self):
        """Lesbare Dateigröße"""
        size = self.filesize_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class Video(models.Model):
    """Video eines Vogel-Besuchs (3s pre-trigger + 10s)"""
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # Dateipfade
    file = models.FileField(upload_to=video_upload_path, null=True, blank=True)
    usb_path = models.CharField(max_length=500, blank=True, help_text="Pfad auf USB Stick")
    
    # Metadaten
    filename = models.CharField(max_length=255)
    filesize_bytes = models.BigIntegerField(default=0)
    duration_seconds = models.FloatField(default=0)
    width = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    framerate = models.IntegerField(default=30)
    codec = models.CharField(max_length=50, default='h264')
    
    # Thumbnail
    thumbnail_frame = models.ImageField(upload_to='video_thumbnails/', null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"Video {self.filename} @ {self.timestamp}"
    
    @property
    def file_path(self):
        """Vollständiger Dateipfad"""
        if self.usb_path:
            return os.path.join(settings.USB_STORAGE_PATH, self.usb_path)
        elif self.file:
            return self.file.path
        return None
    
    @property
    def file_url(self):
        """URL für Web-Zugriff"""
        if self.file:
            return self.file.url
        return None
    
    def get_filesize_display(self):
        """Lesbare Dateigröße"""
        size = self.filesize_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class MediaStorageStats(models.Model):
    """Statistiken über Speicherplatz-Nutzung"""
    updated_at = models.DateTimeField(auto_now=True)
    
    # USB Storage
    usb_total_bytes = models.BigIntegerField(default=0)
    usb_used_bytes = models.BigIntegerField(default=0)
    usb_available_bytes = models.BigIntegerField(default=0)
    
    # Datei-Counts
    total_photos = models.IntegerField(default=0)
    total_videos = models.IntegerField(default=0)
    photos_size_bytes = models.BigIntegerField(default=0)
    videos_size_bytes = models.BigIntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "Media Storage Stats"
    
    def __str__(self):
        return f"Storage Stats @ {self.updated_at}"
    
    @property
    def usb_usage_percent(self):
        """Prozentuale USB-Nutzung"""
        if self.usb_total_bytes > 0:
            return (self.usb_used_bytes / self.usb_total_bytes) * 100
        return 0