"""
Test-Command für den PIR Bewegungssensor
"""
import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Testet den PIR Bewegungssensor'

    def add_arguments(self, parser):
        parser.add_argument(
            '--duration',
            type=int,
            default=60,
            help='Testdauer in Sekunden (default: 60)'
        )

    def handle(self, *args, **options):
        from django.conf import settings

        from hardware.pir_sensor import PIRSensorController

        duration = options['duration']
        pin = settings.BIRDY_SETTINGS['PIR_SENSOR_PIN']

        self.stdout.write(self.style.SUCCESS('=== PIR Bewegungssensor Test ===\n'))
        self.stdout.write(f'GPIO Pin: {pin}')
        self.stdout.write(f'Testdauer: {duration}s')
        self.stdout.write('')

        # Sensor initialisieren (ohne auto_init, manuell ohne Warmup)
        self.stdout.write('Initialisiere Sensor...')

        sensor = PIRSensorController()

        try:
            import lgpio
            sensor.chip_handle = lgpio.gpiochip_open(0)
            lgpio.gpio_claim_input(sensor.chip_handle, pin, lgpio.SET_PULL_DOWN)
            sensor.is_initialized = True
            self.stdout.write(self.style.SUCCESS('✓ Sensor initialisiert (ohne Warmup)'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Fehler: {e}'))
            self.stdout.write(self.style.WARNING('\nPrüfe:'))
            self.stdout.write(f'  - PIR Signal an GPIO {pin}')
            self.stdout.write('  - PIR mit 5V versorgt?')
            self.stdout.write('  - Verkabelung korrekt?')
            return

        self.stdout.write('')
        self.stdout.write(self.style.WARNING(f'Überwache Bewegung für {duration}s (Ctrl+C zum Beenden)\n'))
        self.stdout.write(f'{"Zeit":<12} {"GPIO":>6} {"Status":<20}')
        self.stdout.write('-' * 45)

        # Zähler
        motion_count = 0
        last_state = None
        start_time = time.time()
        motion_start = None

        try:
            import lgpio
            while (time.time() - start_time) < duration:
                state = lgpio.gpio_read(sensor.chip_handle, pin)
                timestamp = time.strftime('%H:%M:%S')

                # Nur bei Zustandsänderung ausgeben
                if state != last_state:
                    if state == 1:
                        motion_count += 1
                        motion_start = time.time()
                        self.stdout.write(
                            f'{timestamp:<12} {state:>6} {self.style.SUCCESS("▶ BEWEGUNG ERKANNT")}'
                        )
                    else:
                        if motion_start:
                            duration_s = time.time() - motion_start
                            self.stdout.write(
                                f'{timestamp:<12} {state:>6} {self.style.HTTP_INFO(f"◼ Keine Bewegung ({duration_s:.1f}s)")}'
                            )
                        else:
                            self.stdout.write(
                                f'{timestamp:<12} {state:>6} {self.style.HTTP_INFO("◼ Keine Bewegung")}'
                            )
                    last_state = state

                time.sleep(0.05)  # 50ms polling

        except KeyboardInterrupt:
            self.stdout.write('\n')

        # Statistik
        elapsed = time.time() - start_time
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== Statistik ==='))
        self.stdout.write(f'  Testdauer:    {elapsed:.0f}s')
        self.stdout.write(f'  Bewegungen:   {motion_count}')

        if motion_count > 0:
            self.stdout.write(self.style.SUCCESS('\n✓ PIR Sensor funktioniert!'))
        else:
            self.stdout.write(self.style.WARNING('\n⚠ Keine Bewegung erkannt'))
            self.stdout.write('  Tipps:')
            self.stdout.write('  - Vor dem Sensor bewegen')
            self.stdout.write('  - PIR Empfindlichkeit prüfen (Poti)')
            self.stdout.write('  - PIR Verzögerung prüfen (Poti)')

        # Aufräumen
        try:
            import lgpio
            lgpio.gpio_free(sensor.chip_handle, pin)
            lgpio.gpiochip_close(sensor.chip_handle)
            self.stdout.write(self.style.SUCCESS('\n✓ Sensor geschlossen'))
        except Exception:
            pass
