from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BirdDetectionViewSet,
    BirdSpeciesViewSet,
    PhotoViewSet,
    SensorStatusViewSet,
    StatisticsViewSet,
    VideoViewSet,
    WeightViewSet,
)

router = DefaultRouter()
router.register(r'species', BirdSpeciesViewSet, basename='species')
router.register(r'detections', BirdDetectionViewSet, basename='detections')
router.register(r'photos', PhotoViewSet, basename='photos')
router.register(r'videos', VideoViewSet, basename='videos')
router.register(r'weight', WeightViewSet, basename='weight')
router.register(r'sensor-status', SensorStatusViewSet, basename='sensor-status')
router.register(r'statistics', StatisticsViewSet, basename='statistics')

urlpatterns = [
    path('', include(router.urls)),
]

"""
API Endpoints:

GET /api/species/ - Liste aller Vogel-Spezies
GET /api/species/{id}/ - Details einer Spezies

GET /api/detections/ - Liste aller Detektionen
GET /api/detections/{id}/ - Details einer Detektion
GET /api/detections/recent/ - Letzte 10 Detektionen
GET /api/detections/today/ - Heutige Detektionen

GET /api/photos/ - Liste aller Fotos
GET /api/photos/{id}/ - Details eines Fotos

GET /api/videos/ - Liste aller Videos
GET /api/videos/{id}/ - Details eines Videos

GET /api/weight/ - Liste aller Gewichtsmessungen
GET /api/weight/current/ - Aktuelle Gewichtsmessung
GET /api/weight/history/ - Verlauf letzte 24h

GET /api/sensor-status/current/ - Aktueller Sensor-Status

GET /api/statistics/daily/?date=2024-01-15 - Tagesstatistik
GET /api/statistics/top-species/?days=30 - Top Spezies
GET /api/statistics/summary/ - Gesamtübersicht
"""
