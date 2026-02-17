"""
PIR Motion Sensor Interface - Native lgpio Implementation
Raspberry Pi 5 optimiert - verwendet lgpio direkt ohne gpiozero
"""
import time
import logging
import threading
from django.conf import settings
from django.utils import timezone

try:
    import lgpio
except ImportError:
    raise ImportError("lgpio library not found. Install with: pip install lgpio")

logger = logging.getLogger('birdy')


class PIRSensorController:
    """Controller für PIR Bewegungssensor - Native lgpio Implementation"""

    def __init__(self):
        self.pin = settings.BIRDY_SETTINGS['PIR_SENSOR_PIN']
        self.chip_handle = None
        self.is_initialized = False
        self.last_motion_time = None
        self.motion_active = False

        # Cooldown um false triggers zu vermeiden
        # Ignoriere Bewegungen wenn letzte Bewegung < 60 Sekunden her ist
        self.min_motion_interval = 10  # Sekunden

        # Callbacks die bei Events aufgerufen werden
        self.on_motion_callbacks = []
        self.on_no_motion_callbacks = []

        # Polling Thread für GPIO Monitoring
        self._monitor_thread = None
        self._monitor_running = False
        self._last_gpio_state = 0

    def initialize(self):
        """Initialisiere PIR Sensor mit lgpio"""
        try:
            # Öffne GPIO Chip (gpiochip0 auf Raspberry Pi 5)
            self.chip_handle = lgpio.gpiochip_open(0)
            logger.info(f"GPIO chip opened successfully (handle={self.chip_handle})")

            # Konfiguriere GPIO Pin als Input mit Pull-Down
            # Flags: LGPIO_SET_PULL_DOWN = 4
            lgpio.gpio_claim_input(self.chip_handle, self.pin, lgpio.SET_PULL_DOWN)
            logger.info(f"PIR sensor GPIO{self.pin} claimed as input with pull-down")

            # Lese initialen Zustand
            self._last_gpio_state = lgpio.gpio_read(self.chip_handle, self.pin)
            logger.info(f"Initial GPIO state: {self._last_gpio_state}")

            self.is_initialized = True

            # Warte auf Sensor Warmup (ca. 30-60 Sekunden)
            logger.info("PIR sensor warming up (30s)...")
            time.sleep(30)

            # Starte Monitoring Thread
            self._monitor_running = True
            self._monitor_thread = threading.Thread(target=self._monitor_gpio, daemon=True)
            self._monitor_thread.start()

            logger.info("PIR sensor ready (monitoring thread started)")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize PIR sensor: {e}")
            self.is_initialized = False
            if self.chip_handle is not None:
                try:
                    lgpio.gpiochip_close(self.chip_handle)
                except:
                    pass
                self.chip_handle = None
            return False

    def _monitor_gpio(self):
        """
        Background Thread der kontinuierlich GPIO Pin überwacht
        Erkennt Zustandsänderungen (LOW->HIGH, HIGH->LOW)
        """
        logger.debug("PIR GPIO monitoring thread started")

        motion_start_time = None

        while self._monitor_running:
            try:
                # Lese aktuellen GPIO Zustand
                current_state = lgpio.gpio_read(self.chip_handle, self.pin)

                # Zustandsänderung erkannt
                if current_state != self._last_gpio_state:
                    timestamp = timezone.now()

                    if current_state == 1:
                        # LOW -> HIGH (Bewegung erkannt)
                        logger.debug(f"PIR: GPIO {self.pin} went HIGH (motion)")
                        motion_start_time = time.time()
                        self._handle_motion_detected(timestamp, current_state)

                    else:
                        # HIGH -> LOW (Bewegung beendet)
                        logger.debug(f"PIR: GPIO {self.pin} went LOW (no motion)")
                        duration = None
                        if motion_start_time:
                            duration = time.time() - motion_start_time
                        self._handle_no_motion(timestamp, current_state, duration)
                        motion_start_time = None

                    self._last_gpio_state = current_state

                # Poll alle 50ms (20 Hz)
                time.sleep(0.05)

            except Exception as e:
                logger.error(f"Error in PIR monitoring thread: {e}")
                time.sleep(0.5)  # Längere Pause bei Fehler

        logger.debug("PIR GPIO monitoring thread stopped")

    def _handle_motion_detected(self, timestamp, gpio_state):
        """Interner Handler für Bewegungserkennung"""
        logger.debug(f"PIR: _handle_motion_detected called, GPIO state={gpio_state}")

        # Cooldown Check: Ignoriere Trigger wenn zu kurz nach letztem Trigger
        if self.last_motion_time is not None:
            time_since_last = (timestamp - self.last_motion_time).total_seconds()
            if time_since_last < self.min_motion_interval:
                logger.warning(f"PIR: Motion detected but IGNORED (cooldown: {time_since_last:.1f}s < {self.min_motion_interval}s, gpio={gpio_state})")
                return

        self.motion_active = True
        self.last_motion_time = timestamp

        logger.info(f"PIR: Motion detected! (gpio={gpio_state})")

        # Speichere Event in DB
        from sensors.models import PIREvent
        event = PIREvent.objects.create(event_type='triggered')

        # Rufe alle registrierten Callbacks auf
        for callback in self.on_motion_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in motion callback: {e}")

    def _handle_no_motion(self, timestamp, gpio_state, duration):
        """Interner Handler für Ende der Bewegung"""
        logger.debug(f"PIR: _handle_no_motion called, GPIO state={gpio_state}")

        if not self.motion_active:
            return

        self.motion_active = False

        logger.info(f"PIR: No motion (duration: {duration:.2f}s, gpio={gpio_state})")

        # Speichere Event in DB
        from sensors.models import PIREvent
        event = PIREvent.objects.create(
            event_type='cleared',
            duration_seconds=duration
        )

        # Rufe alle registrierten Callbacks auf
        for callback in self.on_no_motion_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in no-motion callback: {e}")

    def register_motion_callback(self, callback):
        """
        Registriere Callback für Bewegungserkennung

        Args:
            callback: Funktion die aufgerufen wird (erhält PIREvent als Parameter)
        """
        if callback not in self.on_motion_callbacks:
            self.on_motion_callbacks.append(callback)
            logger.debug(f"Registered motion callback: {callback.__name__}")

    def register_no_motion_callback(self, callback):
        """
        Registriere Callback für Ende der Bewegung

        Args:
            callback: Funktion die aufgerufen wird (erhält PIREvent als Parameter)
        """
        if callback not in self.on_no_motion_callbacks:
            self.on_no_motion_callbacks.append(callback)
            logger.debug(f"Registered no-motion callback: {callback.__name__}")

    def is_motion_detected(self):
        """Prüfe ob aktuell Bewegung erkannt wird"""
        if not self.is_initialized or self.chip_handle is None:
            return False
        try:
            return lgpio.gpio_read(self.chip_handle, self.pin) == 1
        except:
            return False

    def wait_for_motion(self, timeout=None):
        """
        Warte auf Bewegungserkennung

        Args:
            timeout: Maximale Wartezeit in Sekunden (None = unbegrenzt)

        Returns:
            bool: True wenn Bewegung erkannt wurde, False bei Timeout
        """
        if not self.is_initialized or self.chip_handle is None:
            logger.warning("PIR sensor not initialized")
            return False

        start_time = time.time()
        while True:
            if lgpio.gpio_read(self.chip_handle, self.pin) == 1:
                return True

            if timeout is not None and (time.time() - start_time) >= timeout:
                return False

            time.sleep(0.01)

    def wait_for_no_motion(self, timeout=None):
        """
        Warte bis Bewegung endet

        Args:
            timeout: Maximale Wartezeit in Sekunden (None = unbegrenzt)

        Returns:
            bool: True wenn Bewegung geendet hat, False bei Timeout
        """
        if not self.is_initialized or self.chip_handle is None:
            logger.warning("PIR sensor not initialized")
            return False

        start_time = time.time()
        while True:
            if lgpio.gpio_read(self.chip_handle, self.pin) == 0:
                return True

            if timeout is not None and (time.time() - start_time) >= timeout:
                return False

            time.sleep(0.01)

    def cleanup(self):
        """Cleanup GPIO"""
        try:
            # Stoppe Monitoring Thread
            self._monitor_running = False
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=2)
                logger.debug("Monitoring thread stopped")

            # Freigebe GPIO und schließe Chip
            if self.chip_handle is not None:
                try:
                    lgpio.gpio_free(self.chip_handle, self.pin)
                    logger.debug(f"GPIO{self.pin} freed")
                except:
                    pass

                lgpio.gpiochip_close(self.chip_handle)
                logger.info("PIR sensor closed")
                self.chip_handle = None

        except Exception as e:
            logger.error(f"PIR cleanup failed: {e}")


# Singleton Instance
_pir_sensor_instance = None

def get_pir_sensor(auto_init=True):
    """
    Hole Singleton Instance des PIR Sensors

    Args:
        auto_init: Wenn True, initialisiere Sensor automatisch (Standard: True)
                  Setze auf False wenn nur Referenz benötigt wird
    """
    global _pir_sensor_instance
    if _pir_sensor_instance is None:
        _pir_sensor_instance = PIRSensorController()
        if auto_init:
            _pir_sensor_instance.initialize()
    elif auto_init and not _pir_sensor_instance.is_initialized:
        _pir_sensor_instance.initialize()
    return _pir_sensor_instance
