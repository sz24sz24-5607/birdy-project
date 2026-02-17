"""
Birdy Web Views - Frontend Website
"""
from django.shortcuts import render
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime
from species.models import BirdDetection, BirdSpecies, DailyStatistics
from media_manager.models import Photo


def home(request):
    """Dashboard Homepage"""
    from sensors.models import SensorStatus
    from django.db.models import Count

    today = timezone.now().date()

    # Sensor Status
    sensor_status = SensorStatus.get_current()

    # Statistiken
    stats = {
        'today_detections': BirdDetection.objects.filter(
            timestamp__date=today,
            processed=True,
            species__isnull=False  # Nur gültige Besuche (>=50% confidence, kein background)
        ).count(),
        'weight_grams': sensor_status.current_weight_grams or 0,
        'sensors_online': {
            'weight': sensor_status.weight_sensor_online,
            'pir': sensor_status.pir_sensor_online,
            'camera': sensor_status.camera_online,
        }
    }

    # Anzahl pro Art heute
    today_species = BirdDetection.objects.filter(
        timestamp__date=today,
        processed=True,
        species__isnull=False
    ).values('species__common_name_de').annotate(
        count=Count('id')
    ).order_by('-count')

    # Letzte 12 Detections als Galerie (nur gültige Besuche)
    recent_detections = BirdDetection.objects.filter(
        processed=True,
        species__isnull=False  # Nur gültige Besuche
    ).select_related('species', 'photo', 'video').order_by('-timestamp')[:12]

    context = {
        'stats': stats,
        'today_species': today_species,
        'recent_detections': recent_detections,
    }

    return render(request, 'home.html', context)


def detections(request):
    """Alle Detections mit Filter - zeigt ALLE inkl. Background und niedrige Confidence"""
    # Basis-Query: ALLE processed detections (inkl. Background und niedrige Confidence)
    detections_list = BirdDetection.objects.filter(
        processed=True
    ).select_related('species', 'photo', 'video').order_by('-timestamp')

    # Filter nach Art
    selected_species = request.GET.get('species', '')
    if selected_species:
        if selected_species == 'none':
            # Zeige nur Detections ohne Spezies (Background / niedrige Confidence)
            detections_list = detections_list.filter(species__isnull=True)
        else:
            detections_list = detections_list.filter(species_id=selected_species)

    # Filter nach Confidence
    min_confidence = request.GET.get('min_confidence', '')
    if min_confidence:
        try:
            min_conf_value = float(min_confidence) / 100.0  # Convert percentage to decimal
            detections_list = detections_list.filter(confidence__gte=min_conf_value)
        except ValueError:
            pass  # Ignoriere ungültige Werte

    # Filter Background ein/ausblenden
    show_background = request.GET.get('show_background', 'yes')
    if show_background == 'no':
        # Verstecke Detections ohne Spezies (Background / niedrige Confidence)
        detections_list = detections_list.filter(species__isnull=False)

    # Pagination
    paginator = Paginator(detections_list, 24)  # 24 pro Seite
    page_number = request.GET.get('page', 1)
    detections_page = paginator.get_page(page_number)

    # Alle Arten für Filter (inkl. "Keine Spezies" Option)
    species_list = BirdSpecies.objects.all().order_by('common_name_de')

    context = {
        'detections': detections_page,
        'species_list': species_list,
        'selected_species': selected_species,
        'min_confidence': min_confidence,
        'show_background': show_background,
    }

    return render(request, 'detections.html', context)
