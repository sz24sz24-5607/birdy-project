"""
Test-Command für den Gewichtssensor - Rohdaten ohne Filter
Gibt direkt die HX711 Raw-Werte aus
"""
import time

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Gibt Rohdaten des Gewichtssensors (HX711) aus - ohne Filter oder Kalibrierung'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Anzahl Messungen (default: 20)'
        )
        parser.add_argument(
            '--interval',
            type=float,
            default=0.5,
            help='Intervall zwischen Messungen in Sekunden (default: 0.5)'
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Kontinuierliche Messung (Ctrl+C zum Beenden)'
        )
        parser.add_argument(
            '--samples',
            type=int,
            default=5,
            help='Anzahl HW-Samples pro Messung (default: 5)'
        )

    def handle(self, *args, **options):
        from hx711 import HX711

        count = options['count']
        interval = options['interval']
        continuous = options['continuous']
        hw_samples = options['samples']

        dt_pin = settings.BIRDY_SETTINGS['WEIGHT_SENSOR_DT_PIN']
        sck_pin = settings.BIRDY_SETTINGS['WEIGHT_SENSOR_SCK_PIN']

        self.stdout.write(self.style.SUCCESS('=== HX711 Rohdaten Test ===\n'))
        self.stdout.write(f'DT Pin:  GPIO {dt_pin}')
        self.stdout.write(f'SCK Pin: GPIO {sck_pin}')
        self.stdout.write(f'HW Samples pro Messung: {hw_samples}')
        self.stdout.write('')

        # HX711 direkt initialisieren (ohne WeightSensor Wrapper)
        self.stdout.write('Initialisiere HX711 direkt...')

        try:
            hx = HX711(dout_pin=dt_pin, pd_sck_pin=sck_pin, gain=128, channel='A')
            result = hx.reset()
            if result:
                self.stdout.write(self.style.SUCCESS('✓ HX711 Reset erfolgreich'))
            else:
                self.stdout.write(self.style.ERROR('✗ HX711 Reset fehlgeschlagen'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Fehler: {e}'))
            return

        time.sleep(0.5)
        self.stdout.write('')

        # Header
        self.stdout.write(f'{"Nr.":<5} {"Zeit":<12} {"Raw-Werte":<60} {"Mittel":>12} {"Delta":>10}')
        self.stdout.write('-' * 105)

        all_means = []
        last_mean = None
        i = 0

        try:
            while continuous or i < count:
                i += 1
                timestamp = time.strftime('%H:%M:%S')

                try:
                    raw_data = hx.get_raw_data(hw_samples)

                    if raw_data is False:
                        self.stdout.write(f'{i:<5} {timestamp:<12} {self.style.ERROR("FEHLER - keine Daten")}')
                    else:
                        values = [raw_data[j] for j in range(hw_samples)]
                        mean = sum(values) / len(values)
                        all_means.append(mean)

                        # Delta
                        if last_mean is not None:
                            delta = mean - last_mean
                            delta_str = f'{delta:+.0f}'
                        else:
                            delta_str = '-'

                        # Raw-Werte formatieren
                        raw_str = ', '.join(f'{v:.0f}' for v in values)
                        if len(raw_str) > 58:
                            raw_str = raw_str[:55] + '...'

                        self.stdout.write(
                            f'{i:<5} {timestamp:<12} {raw_str:<60} {mean:>12.0f} {delta_str:>10}'
                        )
                        last_mean = mean

                except Exception as e:
                    self.stdout.write(f'{i:<5} {timestamp:<12} {self.style.ERROR(f"Exception: {e}")}')

                if continuous or i < count:
                    time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write('\n')

        # Statistik
        if all_means:
            avg = sum(all_means) / len(all_means)
            min_val = min(all_means)
            max_val = max(all_means)
            spread = max_val - min_val

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=== Rohdaten Statistik ==='))
            self.stdout.write(f'  Messungen:    {len(all_means)}')
            self.stdout.write(f'  Durchschnitt: {avg:.0f}')
            self.stdout.write(f'  Minimum:      {min_val:.0f}')
            self.stdout.write(f'  Maximum:      {max_val:.0f}')
            self.stdout.write(f'  Streuung:     {spread:.0f}')
            self.stdout.write(f'  Streuung %:   {(spread / abs(avg) * 100) if avg != 0 else 0:.2f}%')

        # Cleanup
        try:
            hx.reset()
        except Exception:
            pass

        self.stdout.write(self.style.SUCCESS('\n✓ Test beendet'))
