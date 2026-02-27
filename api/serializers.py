"""
REST API Serializers
"""
from rest_framework import serializers

from media_manager.models import Photo, Video
from sensors.models import SensorStatus, WeightMeasurement
from species.models import BirdDetection, BirdSpecies, DailyStatistics


class BirdSpeciesSerializer(serializers.ModelSerializer):
    """Serializer für Vogel-Spezies"""

    class Meta:
        model = BirdSpecies
        fields = ['id', 'scientific_name', 'common_name_de', 'common_name_en',
                  'description', 'conservation_status']


class PhotoSerializer(serializers.ModelSerializer):
    """Serializer für Fotos"""
    filesize_display = serializers.CharField(source='get_filesize_display', read_only=True)

    class Meta:
        model = Photo
        fields = ['id', 'timestamp', 'filename', 'filesize_bytes', 'filesize_display',
                  'width', 'height', 'file_url']


class VideoSerializer(serializers.ModelSerializer):
    """Serializer für Videos"""
    filesize_display = serializers.CharField(source='get_filesize_display', read_only=True)

    class Meta:
        model = Video
        fields = ['id', 'timestamp', 'filename', 'filesize_bytes', 'filesize_display',
                  'duration_seconds', 'width', 'height', 'file_url']


class BirdDetectionSerializer(serializers.ModelSerializer):
    """Serializer für Vogel-Detektionen"""
    species = BirdSpeciesSerializer(read_only=True)
    photo = PhotoSerializer(read_only=True)
    video = VideoSerializer(read_only=True)
    confidence_percent = serializers.SerializerMethodField()

    class Meta:
        model = BirdDetection
        fields = ['id', 'timestamp', 'species', 'confidence', 'confidence_percent',
                  'top_predictions', 'photo', 'video', 'processed', 'processing_time_ms']

    def get_confidence_percent(self, obj):
        return f"{obj.confidence * 100:.1f}%"


class BirdDetectionListSerializer(serializers.ModelSerializer):
    """Leichtgewichtiger Serializer für Listen"""
    species_name = serializers.CharField(source='species.common_name_de', read_only=True)
    confidence_percent = serializers.SerializerMethodField()

    class Meta:
        model = BirdDetection
        fields = ['id', 'timestamp', 'species_name', 'confidence', 'confidence_percent']

    def get_confidence_percent(self, obj):
        return f"{obj.confidence * 100:.1f}%"


class WeightMeasurementSerializer(serializers.ModelSerializer):
    """Serializer für Gewichtsmessungen"""
    net_weight = serializers.FloatField(read_only=True)

    class Meta:
        model = WeightMeasurement
        fields = ['id', 'timestamp', 'weight_grams', 'net_weight']


class SensorStatusSerializer(serializers.ModelSerializer):
    """Serializer für aktuellen Sensor-Status"""

    class Meta:
        model = SensorStatus
        fields = ['updated_at', 'current_weight_grams', 'weight_sensor_online',
                  'last_weight_reading', 'pir_sensor_online', 'bird_present',
                  'last_pir_trigger', 'camera_online', 'last_photo']


class DailyStatisticsSerializer(serializers.ModelSerializer):
    """Serializer für tägliche Statistiken"""
    species = BirdSpeciesSerializer(read_only=True)
    avg_confidence_percent = serializers.SerializerMethodField()

    class Meta:
        model = DailyStatistics
        fields = ['date', 'species', 'visit_count', 'avg_confidence', 'avg_confidence_percent']

    def get_avg_confidence_percent(self, obj):
        return f"{obj.avg_confidence * 100:.1f}%"
