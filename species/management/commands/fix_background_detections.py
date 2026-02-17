"""
Management Command: Korrigiere Background-Detections

Setzt species=None für alle Detections mit:
- species.scientific_name = "background"
- confidence < MIN_CONFIDENCE_SPECIES

Damit werden diese nicht mehr als gültige Besuche gezählt.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from species.models import BirdDetection, BirdSpecies


class Command(BaseCommand):
    help = 'Korrigiere Background-Detections und Low-Confidence Detections'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Zeige nur was geändert würde, ohne zu speichern',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        min_confidence = settings.BIRDY_SETTINGS['MIN_CONFIDENCE_SPECIES']

        self.stdout.write(self.style.SUCCESS('=== Background Detection Fixer ==='))
        self.stdout.write(f'Min Confidence: {min_confidence:.1%}')
        self.stdout.write('')

        # 1. Background Species finden
        background_species = BirdSpecies.objects.filter(scientific_name__iexact='background')

        if background_species.exists():
            bg = background_species.first()
            self.stdout.write(f'Background Species gefunden: ID={bg.id}, Name={bg.scientific_name}')

            # Detections mit background species
            bg_detections = BirdDetection.objects.filter(
                species=bg,
                processed=True
            )
            bg_count = bg_detections.count()

            self.stdout.write(f'Detections mit background species: {bg_count}')

            if bg_count > 0:
                if not dry_run:
                    updated = bg_detections.update(species=None)
                    self.stdout.write(self.style.SUCCESS(f'✓ {updated} Background-Detections korrigiert (species=None)'))
                else:
                    self.stdout.write(self.style.WARNING(f'[DRY-RUN] Würde {bg_count} Background-Detections korrigieren'))
        else:
            self.stdout.write('Keine Background Species gefunden')

        self.stdout.write('')

        # 2. Low Confidence Detections
        low_conf_detections = BirdDetection.objects.filter(
            processed=True,
            species__isnull=False,
            confidence__lt=min_confidence
        )
        low_conf_count = low_conf_detections.count()

        self.stdout.write(f'Detections mit confidence < {min_confidence:.1%}: {low_conf_count}')

        if low_conf_count > 0:
            # Zeige Beispiele
            examples = low_conf_detections[:5]
            for det in examples:
                self.stdout.write(f'  - {det.species.scientific_name}: {det.confidence:.1%} (ID={det.id})')

            if low_conf_count > 5:
                self.stdout.write(f'  ... und {low_conf_count - 5} weitere')

            if not dry_run:
                updated = low_conf_detections.update(species=None)
                self.stdout.write(self.style.SUCCESS(f'✓ {updated} Low-Confidence Detections korrigiert (species=None)'))
            else:
                self.stdout.write(self.style.WARNING(f'[DRY-RUN] Würde {low_conf_count} Low-Confidence Detections korrigieren'))

        self.stdout.write('')

        # 3. Statistik nach Korrektur
        valid_visits = BirdDetection.objects.filter(
            processed=True,
            species__isnull=False
        ).count()

        invalid_visits = BirdDetection.objects.filter(
            processed=True,
            species__isnull=True
        ).count()

        self.stdout.write(self.style.SUCCESS('=== Zusammenfassung ==='))
        self.stdout.write(f'Gültige Besuche (species != None): {valid_visits}')
        self.stdout.write(f'Ungültige Detections (species = None): {invalid_visits}')

        if dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('DRY-RUN Modus - Keine Änderungen gespeichert'))
            self.stdout.write('Führe ohne --dry-run aus um Änderungen zu speichern')
