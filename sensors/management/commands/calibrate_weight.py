from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Kalibriert die Wägezelle'

    def add_arguments(self, parser):
        parser.add_argument(
            '--weight',
            type=float,
            default=500.0,
            help='Bekanntes Kalibriergewicht in Gramm (default: 500g)'
        )

    def handle(self, *args, **options):
        from hardware.weight_sensor import get_weight_sensor
        
        weight = options['weight']
        
        self.stdout.write(self.style.SUCCESS('=== Wägezellen Kalibrierung ==='))
        self.stdout.write(f'Verwende Kalibriergewicht: {weight}g\n')
        
        sensor = get_weight_sensor()
        
        if not sensor.is_initialized:
            self.stdout.write(self.style.ERROR('Sensor konnte nicht initialisiert werden'))
            return
        
        # Kalibrierung durchführen
        success = sensor.calibrate(weight)
        
        if success:
            self.stdout.write(self.style.SUCCESS('\n✓ Kalibrierung erfolgreich!'))
            self.stdout.write(f'Kalibrierungsfaktor: {sensor.calibration_factor}')
            
            # Kalibrierung wird automatisch in weight_calibration.json gespeichert
            self.stdout.write('\n✓ Kalibrierung gespeichert in weight_calibration.json')

        else:
            self.stdout.write(self.style.ERROR('\n✗ Kalibrierung fehlgeschlagen'))
        
        sensor.cleanup()