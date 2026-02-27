"""
Birdy Web Views - Frontend Website
"""
import json

from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from species.models import BirdDetection, BirdSpecies, MonthlyStatistics


def home(request):
    """Dashboard Homepage"""
    from django.db.models import Count

    from sensors.models import SensorStatus

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


def statistics(request):
    """Monats- und Jahresstatistiken"""
    MONTH_NAMES = [
        '', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
        'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'
    ]

    current_year = timezone.now().year

    # Verfügbare Jahre (aus DB)
    available_years = list(
        MonthlyStatistics.objects.values_list('year', flat=True)
        .distinct().order_by('-year')
    )
    if not available_years:
        available_years = [current_year]

    # Filter aus GET-Parametern
    try:
        selected_year = int(request.GET.get('year', available_years[0]))
    except (ValueError, IndexError):
        selected_year = current_year

    try:
        selected_month = int(request.GET.get('month', 0)) or None
    except ValueError:
        selected_month = None

    try:
        selected_species_id = int(request.GET.get('species_id', 0)) or None
    except ValueError:
        selected_species_id = None

    # Artenliste für Filter (nur Arten mit Statistiken)
    species_list = BirdSpecies.objects.filter(
        monthlystatistics__isnull=False
    ).distinct().order_by('common_name_de')

    # --- Basisfilter ---
    monthly_qs = MonthlyStatistics.objects.filter(year=selected_year)
    if selected_month:
        monthly_qs = monthly_qs.filter(month=selected_month)
    if selected_species_id:
        monthly_qs = monthly_qs.filter(species_id=selected_species_id)

    # --- Balkendiagramm-Daten ---
    if selected_month:
        # Monatsansicht: Top-Arten als Balken
        bar_items = list(
            monthly_qs.select_related('species')
            .order_by('-visit_count')[:10]
        )
        bar_labels = [item.species.common_name_de for item in bar_items]
        bar_values = [item.visit_count for item in bar_items]
        bar_title = f'Top Arten – {MONTH_NAMES[selected_month]} {selected_year}'
    else:
        # Jahresansicht: Besuche je Monat
        monthly_totals = {
            row['month']: row['total']
            for row in monthly_qs.values('month').annotate(total=Sum('visit_count'))
        }
        bar_labels = MONTH_NAMES[1:]  # Jan–Dez
        bar_values = [monthly_totals.get(m, 0) for m in range(1, 13)]
        bar_title = f'Besuche pro Monat – {selected_year}'

    # --- Donut-Diagramm: Artenverteilung ---
    donut_qs = MonthlyStatistics.objects.filter(year=selected_year)
    if selected_month:
        donut_qs = donut_qs.filter(month=selected_month)
    if selected_species_id:
        donut_qs = donut_qs.filter(species_id=selected_species_id)

    top_species_raw = list(
        donut_qs.values('species__common_name_de')
        .annotate(total=Sum('visit_count'))
        .order_by('-total')[:8]
    )
    donut_labels = [row['species__common_name_de'] for row in top_species_raw]
    donut_values = [row['total'] for row in top_species_raw]
    # Restliche als "Andere"
    all_total = donut_qs.aggregate(t=Sum('visit_count'))['t'] or 0
    top_total = sum(donut_values)
    if all_total - top_total > 0:
        donut_labels.append('Andere')
        donut_values.append(all_total - top_total)

    # --- KPI-Karten ---
    total_visits = all_total
    unique_species_count = donut_qs.values('species').distinct().count()

    if selected_month:
        best_label = None  # kein "bester Monat" bei Monatsansicht
    else:
        best_month_row = (
            monthly_qs.values('month')
            .annotate(total=Sum('visit_count'))
            .order_by('-total')
            .first()
        )
        best_label = MONTH_NAMES[best_month_row['month']] if best_month_row else None

    top_species_row = (
        donut_qs.values('species__common_name_de')
        .annotate(total=Sum('visit_count'))
        .order_by('-total')
        .first()
    )
    top_species_name = top_species_row['species__common_name_de'] if top_species_row else '–'

    # --- Datentabelle ---
    if selected_month:
        # Arten-Tabelle für gewählten Monat
        table_rows = list(
            monthly_qs.select_related('species').order_by('-visit_count')
        )
        table_mode = 'species'
    else:
        # Monats-Tabelle für gewähltes Jahr: aggregiert über Arten
        month_agg = {
            row['month']: row
            for row in monthly_qs.values('month')
            .annotate(
                total_visits=Sum('visit_count'),
                species_count=Count('species', distinct=True),
            )
        }
        # Top-Art je Monat
        top_per_month = {}
        for row in (
            monthly_qs.values('month', 'species__common_name_de')
            .annotate(total=Sum('visit_count'))
            .order_by('month', '-total')
        ):
            if row['month'] not in top_per_month:
                top_per_month[row['month']] = row['species__common_name_de']

        table_rows = []
        for m in range(1, 13):
            agg = month_agg.get(m)
            if agg:
                table_rows.append({
                    'month_name': MONTH_NAMES[m],
                    'total_visits': agg['total_visits'],
                    'species_count': agg['species_count'],
                    'top_species': top_per_month.get(m, '–'),
                })
        table_mode = 'months'

    selected_month_name = MONTH_NAMES[selected_month] if selected_month else None

    context = {
        'available_years': available_years,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'selected_month_name': selected_month_name,
        'selected_species_id': selected_species_id,
        'species_list': species_list,
        # KPI
        'total_visits': total_visits,
        'unique_species_count': unique_species_count,
        'best_label': best_label,
        'top_species_name': top_species_name,
        # Charts (als JSON für Script-Tag)
        'bar_labels_json': json.dumps(bar_labels),
        'bar_values_json': json.dumps(bar_values),
        'bar_title': bar_title,
        'donut_labels_json': json.dumps(donut_labels),
        'donut_values_json': json.dumps(donut_values),
        # Tabelle
        'table_rows': table_rows,
        'table_mode': table_mode,
    }
    return render(request, 'statistics.html', context)
