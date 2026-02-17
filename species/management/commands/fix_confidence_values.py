"""
Management Command - Korrigiere Confidence Werte von 0-100 zu 0-1
"""
from django.core.management.base import BaseCommand
from species.models import BirdDetection, DailyStatistics
from django.db.models import Max


class Command(BaseCommand):
    help = 'Korrigiert Confidence-Werte von 0-100 zu 0-1 Format'

    def handle(self, *args, **options):
        # Prüfe ob Korrektur nötig ist
        max_conf = BirdDetection.objects.aggregate(Max('confidence'))['confidence__max']

        if max_conf is None:
            self.stdout.write('Keine Detections gefunden')
            return

        if max_conf <= 1.0:
            self.stdout.write(self.style.SUCCESS('Confidence-Werte sind bereits korrekt (0-1)'))
            return

        self.stdout.write(f'Maximaler Confidence-Wert: {max_conf} - Korrektur erforderlich!')

        # Korrigiere BirdDetection
        detections = BirdDetection.objects.all()
        count = 0

        for det in detections:
            if det.confidence > 1.0:
                # Konvertiere von 0-100 zu 0-1
                det.confidence = det.confidence / 100.0

                # Korrigiere auch top_predictions
                if det.top_predictions:
                    for pred in det.top_predictions:
                        if 'confidence' in pred and pred['confidence'] > 1.0:
                            pred['confidence'] = pred['confidence'] / 100.0

                det.save()
                count += 1

                if count % 100 == 0:
                    self.stdout.write(f'Korrigiert: {count} Detections...')

        self.stdout.write(self.style.SUCCESS(f'{count} BirdDetections korrigiert'))

        # Statistiken neu berechnen
        self.stdout.write('Berechne Statistiken neu...')

        # Lösche alte Statistiken
        DailyStatistics.objects.all().delete()

        # Berechne neu für alle Detections
        from django.db.models.functions import TruncDate
        dates_species = BirdDetection.objects.filter(
            processed=True,
            species__isnull=False
        ).values('timestamp__date', 'species').distinct()

        stats_count = 0
        for item in dates_species:
            date = item['timestamp__date']
            species_id = item['species']

            from species.models import BirdSpecies
            species = BirdSpecies.objects.get(id=species_id)

            DailyStatistics.update_for_date(date, species)
            stats_count += 1

        self.stdout.write(self.style.SUCCESS(f'{stats_count} DailyStatistics neu berechnet'))
        self.stdout.write(self.style.SUCCESS('Fertig!'))
