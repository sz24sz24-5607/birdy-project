"""
Test-Command für den Gewichtssensor (HX711)
"""
import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Testet den Gewichtssensor (HX711)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Anzahl Messungen (default: 10)'
        )
        parser.add_argument(
            '--interval',
            type=float,
            default=1.0,
            help='Intervall zwischen Messungen in Sekunden (default: 1.0)'
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Kontinuierliche Messung (Ctrl+C zum Beenden)'
        )

    def handle(self, *args, **options):
        from hardware.weight_sensor import get_weight_sensor

        count = options['count']
        interval = options['interval']
        continuous = options['continuous']

        self.stdout.write(self.style.SUCCESS('=== Gewichtssensor Test ===\n'))

        # Sensor initialisieren
        self.stdout.write('Initialisiere Sensor...')
        sensor = get_weight_sensor()

        if not sensor.is_initialized:
            self.stdout.write(self.style.ERROR('✗ Sensor konnte nicht initialisiert werden'))
            self.stdout.write(self.style.WARNING('\nPrüfe:'))
            self.stdout.write('  - DT Pin: GPIO 5')
            self.stdout.write('  - SCK Pin: GPIO 6')
            self.stdout.write('  - Verkabelung korrekt?')
            self.stdout.write('  - HX711 mit Strom versorgt?')
            return

        self.stdout.write(self.style.SUCCESS('✓ Sensor initialisiert'))
        self.stdout.write(f'  Kalibrierungsfaktor: {sensor.calibration_factor}')
        self.stdout.write(f'  Tare Offset: {sensor.tare_offset}')
        self.stdout.write('')

        # Messungen durchführen
        measurements = []

        if continuous:
            self.stdout.write(self.style.WARNING('Kontinuierliche Messung (Ctrl+C zum Beenden)\n'))
            self.stdout.write(f'{"Zeit":<12} {"Gewicht":>10} {"Status":<20}')
            self.stdout.write('-' * 45)

            try:
                while True:
                    weight = sensor.read_weight_grams()
                    timestamp = time.strftime('%H:%M:%S')

                    # Status bestimmen
                    if weight < 5:
                        status = 'Leer'
                        style = self.style.HTTP_INFO
                    elif weight < 50:
                        status = 'Leicht (Insekt?)'
                        style = self.style.WARNING
                    elif weight < 200:
                        status = 'Vogel möglich'
                        style = self.style.SUCCESS
                    else:
                        status = 'Schwer'
                        style = self.style.ERROR

                    self.stdout.write(f'{timestamp:<12} {weight:>8.1f}g  {style(status)}')
                    time.sleep(interval)

            except KeyboardInterrupt:
                self.stdout.write('\n\nMessung beendet.')

        else:
            self.stdout.write(f'Führe {count} Messungen durch (Intervall: {interval}s)\n')
            self.stdout.write(f'{"Nr.":<5} {"Gewicht":>10} {"Delta":>10}')
            self.stdout.write('-' * 30)

            last_weight = None
            for i in range(count):
                weight = sensor.read_weight_grams()
                measurements.append(weight)

                # Delta berechnen
                if last_weight is not None:
                    delta = weight - last_weight
                    delta_str = f'{delta:+.1f}g'
                else:
                    delta_str = '-'

                self.stdout.write(f'{i+1:<5} {weight:>8.1f}g  {delta_str:>10}')
                last_weight = weight

                if i < count - 1:
                    time.sleep(interval)

            # Statistik
            if measurements:
                avg = sum(measurements) / len(measurements)
                min_val = min(measurements)
                max_val = max(measurements)
                spread = max_val - min_val

                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('=== Statistik ==='))
                self.stdout.write(f'  Durchschnitt: {avg:.1f}g')
                self.stdout.write(f'  Minimum:      {min_val:.1f}g')
                self.stdout.write(f'  Maximum:      {max_val:.1f}g')
                self.stdout.write(f'  Streuung:     {spread:.1f}g')

                # Bewertung
                self.stdout.write('')
                if spread < 2:
                    self.stdout.write(self.style.SUCCESS('✓ Sehr stabil - Sensor funktioniert einwandfrei'))
                elif spread < 5:
                    self.stdout.write(self.style.SUCCESS('✓ Stabil - Sensor funktioniert gut'))
                elif spread < 10:
                    self.stdout.write(self.style.WARNING('⚠ Leichte Schwankungen - evtl. Vibrationen?'))
                else:
                    self.stdout.write(self.style.ERROR('✗ Starke Schwankungen - Verkabelung prüfen!'))

        # Aufräumen
        self.stdout.write('')
        sensor.cleanup()
        self.stdout.write(self.style.SUCCESS('✓ Sensor geschlossen'))
