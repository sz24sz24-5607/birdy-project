from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Photo, Video, MediaStorageStats


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['filename', 'timestamp', 'filesize_display', 'width', 'height']
    list_filter = ['timestamp']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp', 'filename', 'filesize_bytes', 'filesize_display',
                       'width', 'height', 'photo_preview', 'file_info']
    fields = ['timestamp', 'filename', 'photo_preview', 'file_info', 'filesize_display',
              'width', 'height']

    def filesize_display(self, obj):
        return obj.get_filesize_display()
    filesize_display.short_description = 'File Size'

    def photo_preview(self, obj):
        """Zeige Photo-Preview im Admin"""
        if obj.file:
            html = f'<img src="{obj.file.url}" style="max-width: 800px; height: auto; border: 1px solid #ccc;">'
            return mark_safe(html)
        return 'Kein Foto'
    photo_preview.short_description = 'Foto Vorschau'

    def file_info(self, obj):
        """Zeige Dateipfad und Link"""
        if obj.file:
            html = f'''
                <p><strong>Dateipfad:</strong> {obj.file.path}</p>
                <p><a href="{obj.file.url}" target="_blank" class="button" style="padding: 8px 16px; background: #417690; color: white; text-decoration: none; border-radius: 4px;">Foto im neuen Tab öffnen</a></p>
            '''
            return mark_safe(html)
        return 'Keine Datei'
    file_info.short_description = 'Datei Information'

    def has_add_permission(self, request):
        return False


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ['filename', 'timestamp', 'duration_seconds', 'filesize_display',
                    'width', 'height', 'framerate', 'codec']
    list_filter = ['timestamp', 'codec']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp', 'filename', 'filesize_bytes', 'filesize_display',
                       'duration_seconds', 'width', 'height', 'framerate', 'codec',
                       'video_preview', 'file_info']
    fields = ['timestamp', 'filename', 'video_preview', 'file_info', 'codec',
              'duration_seconds', 'width', 'height', 'framerate', 'filesize_display']

    def filesize_display(self, obj):
        return obj.get_filesize_display()
    filesize_display.short_description = 'File Size'

    def file_info(self, obj):
        """Zeige Dateipfad und Link"""
        if obj.file:
            html = f'''
                <p><strong>Dateipfad:</strong> {obj.file.path}</p>
            '''
            return mark_safe(html)
        return 'Keine Datei'
    file_info.short_description = 'Datei Information'

    def video_preview(self, obj):
        """Zeige Video-Preview im Admin"""
        if obj.file:
            html = '<div style="max-width: 800px;">'

            # Zeige Thumbnail wenn vorhanden
            if obj.thumbnail_frame:
                html += f'<img src="{obj.thumbnail_frame.url}" style="max-width: 100%; height: auto; border: 1px solid #ccc;"><br><br>'

            # Video-Info und Download-Link
            html += f'''
                <p><strong>Video:</strong> {obj.filename} ({obj.codec.upper()}, {obj.width}x{obj.height}, {obj.framerate} fps)</p>
                <p><a href="{obj.file.url}" target="_blank" class="button" style="padding: 8px 16px; background: #417690; color: white; text-decoration: none; border-radius: 4px;">Video im neuen Tab öffnen</a></p>
            '''
            html += '</div>'
            return mark_safe(html)
        return 'Keine Video-Datei'
    video_preview.short_description = 'Video Vorschau'

    def has_add_permission(self, request):
        return False


@admin.register(MediaStorageStats)
class MediaStorageStatsAdmin(admin.ModelAdmin):
    list_display = ['updated_at', 'total_photos', 'total_videos', 
                    'usb_usage_display', 'usb_available_display']
    readonly_fields = ['updated_at', 'total_photos', 'total_videos', 
                       'photos_size_bytes', 'videos_size_bytes',
                       'usb_total_bytes', 'usb_used_bytes', 'usb_available_bytes',
                       'usb_usage_display']
    
    def usb_usage_display(self, obj):
        return f"{obj.usb_usage_percent:.1f}%"
    usb_usage_display.short_description = 'USB Usage'
    
    def usb_available_display(self, obj):
        size = obj.usb_available_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    usb_available_display.short_description = 'Available Space'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False