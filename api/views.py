"""
REST API Views
"""
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from sensors.models import WeightMeasurement, SensorStatus
from media_manager.models import Photo, Video
from species.models import BirdSpecies, BirdDetection, DailyStatistics

from .serializers import (
    BirdSpeciesSerializer, BirdDetectionSerializer, BirdDetectionListSerializer,
    PhotoSerializer, VideoSerializer, WeightMeasurementSerializer,
    SensorStatusSerializer, DailyStatisticsSerializer
)


class BirdSpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet für Vogel-Spezies"""
    queryset = BirdSpecies.objects.all()
    serializer_class = BirdSpeciesSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['scientific_name', 'common_name_de', 'common_name_en']
    ordering_fields = ['common_name_de']


class BirdDetectionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet für Vogel-Detektionen (nur gültige Besuche)"""
    queryset = BirdDetection.objects.select_related('species', 'photo', 'video').filter(
        processed=True,
        species__isnull=False  # Nur gültige Besuche (>=50% confidence, kein background)
    )
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['species', 'timestamp']
    ordering_fields = ['timestamp', 'confidence']
    ordering = ['-timestamp']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BirdDetectionListSerializer
        return BirdDetectionSerializer
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Letzte 10 Detektionen"""
        detections = self.get_queryset()[:10]
        serializer = self.get_serializer(detections, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Heutige Detektionen"""
        today = timezone.now().date()
        detections = self.get_queryset().filter(timestamp__date=today)
        serializer = self.get_serializer(detections, many=True)
        return Response(serializer.data)


class PhotoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet für Fotos"""
    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['timestamp']
    ordering = ['-timestamp']


class VideoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet für Videos"""
    queryset = Video.objects.all()
    serializer_class = VideoSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['timestamp']
    ordering = ['-timestamp']


class WeightViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet für Gewichtsmessungen"""
    queryset = WeightMeasurement.objects.all()
    serializer_class = WeightMeasurementSerializer
    ordering = ['-timestamp']
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Aktuelle Gewichtsmessung"""
        latest = self.get_queryset().first()
        if latest:
            serializer = self.get_serializer(latest)
            return Response(serializer.data)
        return Response({'weight_grams': 0}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Gewichtsverlauf letzte 24 Stunden"""
        since = timezone.now() - timedelta(hours=24)
        measurements = self.get_queryset().filter(timestamp__gte=since)
        serializer = self.get_serializer(measurements, many=True)
        return Response(serializer.data)


class SensorStatusViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet für Sensor-Status"""
    queryset = SensorStatus.objects.all()
    serializer_class = SensorStatusSerializer
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Aktueller Sensor-Status"""
        status = SensorStatus.get_current()
        serializer = self.get_serializer(status)
        return Response(serializer.data)


class StatisticsViewSet(viewsets.ViewSet):
    """ViewSet für Statistiken"""
    
    @action(detail=False, methods=['get'])
    def daily(self, request):
        """Tägliche Statistiken"""
        date_str = request.query_params.get('date')
        
        if date_str:
            from datetime import datetime
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = timezone.now().date()
        
        stats = DailyStatistics.objects.filter(date=date).select_related('species')
        serializer = DailyStatisticsSerializer(stats, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def top_species(self, request):
        """Top Spezies nach Zeitraum"""
        days = int(request.query_params.get('days', 30))
        since = timezone.now().date() - timedelta(days=days)
        
        from django.db.models import Sum
        stats = DailyStatistics.objects.filter(date__gte=since).values(
            'species__id',
            'species__common_name_de'
        ).annotate(
            total_visits=Sum('visit_count')
        ).order_by('-total_visits')[:10]
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Zusammenfassung aller Statistiken"""
        from django.db.models import Count, Sum
        
        # Gesamtzahlen (nur gültige Besuche)
        total_detections = BirdDetection.objects.filter(
            processed=True,
            species__isnull=False
        ).count()
        unique_species = BirdSpecies.objects.filter(birddetection__isnull=False).distinct().count()

        # Heute
        today = timezone.now().date()
        today_detections = BirdDetection.objects.filter(
            timestamp__date=today,
            processed=True,
            species__isnull=False
        ).count()

        # Diese Woche
        week_ago = today - timedelta(days=7)
        week_detections = BirdDetection.objects.filter(
            timestamp__date__gte=week_ago,
            processed=True,
            species__isnull=False
        ).count()
        
        return Response({
            'total_detections': total_detections,
            'unique_species': unique_species,
            'today_detections': today_detections,
            'week_detections': week_detections,
        })