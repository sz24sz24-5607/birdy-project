from django.core.management.base import BaseCommand
import logging

logger = logging.getLogger('birdy')


class Command(BaseCommand):
    help = 'Startet das Birdy Bird Detection System'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Starting Birdy System ==='))
        
        # 1. Hardware initialisieren
        self.stdout.write('Initializing hardware...')
        
        from hardware.weight_sensor import get_weight_sensor
        from hardware.pir_sensor import get_pir_sensor
        from hardware.camera import get_camera
        from ml_models.bird_classifier import get_classifier
        from homeassistant.mqtt_client import get_mqtt_client
        
        weight_sensor = get_weight_sensor()
        if weight_sensor.is_initialized:
            self.stdout.write(self.style.SUCCESS('✓ Weight sensor initialized'))
        else:
            self.stdout.write(self.style.ERROR('✗ Weight sensor failed'))
        
        pir_sensor = get_pir_sensor()
        if pir_sensor.is_initialized:
            self.stdout.write(self.style.SUCCESS('✓ PIR sensor initialized'))
        else:
            self.stdout.write(self.style.ERROR('✗ PIR sensor failed'))
        
        camera = get_camera()
        if camera.is_initialized:
            self.stdout.write(self.style.SUCCESS('✓ Camera initialized'))
        else:
            self.stdout.write(self.style.ERROR('✗ Camera failed'))
        
        # 2. ML Model laden
        self.stdout.write('Loading ML model...')
        classifier = get_classifier()
        if classifier.is_initialized:
            self.stdout.write(self.style.SUCCESS('✓ Classifier initialized'))
        else:
            self.stdout.write(self.style.WARNING('⚠ Classifier not initialized'))
        
        # 3. MQTT Client
        self.stdout.write('Connecting to MQTT...')
        mqtt = get_mqtt_client()
        if mqtt.is_connected:
            self.stdout.write(self.style.SUCCESS('✓ MQTT connected'))
        else:
            self.stdout.write(self.style.WARNING('⚠ MQTT not connected'))
        
        # 4. PIR Callbacks registrieren
        self.stdout.write('Registering PIR callbacks...')
        from services.bird_detection import get_detection_service

        # WICHTIG: Übergebe Hardware-Instanzen an Detection Service
        # Damit nutzt der Service die gleichen Instanzen wie start_birdy (gleicher Prozess)
        detection_service = get_detection_service(camera=camera, classifier=classifier)
        pir_sensor.register_motion_callback(detection_service.handle_motion_detected)

        self.stdout.write(self.style.SUCCESS('✓ Detection service registered'))
        
        # System läuft
        self.stdout.write(self.style.SUCCESS('\n=== Birdy System Running ==='))
        self.stdout.write('System is monitoring for birds...')
        self.stdout.write('Weight measurements every 30 seconds')
        self.stdout.write('Press Ctrl+C to stop')

        try:
            # Main Loop mit Weight Messungen
            import time
            from sensors.models import WeightMeasurement, SensorStatus
            from django.utils import timezone

            last_weight_measurement = time.time()
            last_sensor_status_update = time.time()

            while True:
                current_time = time.time()

                # Weight Messung alle 30 Sekunden
                if current_time - last_weight_measurement >= 30:
                    try:
                        weight = weight_sensor.read_weight_grams()
                        if weight is not None:
                            WeightMeasurement.objects.create(weight_grams=weight)

                            status = SensorStatus.get_current()
                            status.current_weight_grams = weight
                            status.weight_sensor_online = True
                            status.last_weight_reading = timezone.now()
                            status.save()

                            logger.info(f"Weight measured: {weight:.1f}g")
                        else:
                            status = SensorStatus.get_current()
                            status.weight_sensor_online = False
                            status.save()
                    except Exception as e:
                        logger.error(f"Error measuring weight: {e}")

                    last_weight_measurement = current_time

                # Sensor Status Update alle 10 Sekunden
                if current_time - last_sensor_status_update >= 10:
                    try:
                        status = SensorStatus.get_current()

                        # PIR Status
                        status.pir_sensor_online = pir_sensor.is_initialized
                        status.bird_present = pir_sensor.is_motion_detected() if pir_sensor.is_initialized else False

                        # Camera Status (prüfe Worker Health)
                        if hasattr(camera, 'is_healthy'):
                            status.camera_online = camera.is_healthy()
                        else:
                            status.camera_online = camera.is_initialized

                        status.save()
                        logger.debug(f"Sensor status: PIR={status.pir_sensor_online}, Camera={status.camera_online}, Weight={status.weight_sensor_online}")
                    except Exception as e:
                        logger.error(f"Error updating sensor status: {e}")

                    last_sensor_status_update = current_time

                time.sleep(1)

        except KeyboardInterrupt:
            self.stdout.write('\n\nShutting down...')

            # Cleanup
            weight_sensor.cleanup()
            pir_sensor.cleanup()
            camera.cleanup()
            mqtt.cleanup()

            self.stdout.write(self.style.SUCCESS('Birdy stopped successfully'))

