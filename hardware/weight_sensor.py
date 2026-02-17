"""
Weight Sensor Interface - HX711 Wägezelle
Verwendet die HX711 Library von tatobari
"""
import time
import logging
from django.conf import settings

logger = logging.getLogger('birdy')

try:
    from hx711 import HX711
except ImportError:
    logger.error("HX711 library not found. Install with: pip install HX711")
    HX711 = None

NUMBER_HW_MEASUREMENTS = 5

class WeightSensor:
    """Interface für HX711 Wägezelle"""

    def __init__(self):
        self.dt_pin = settings.BIRDY_SETTINGS['WEIGHT_SENSOR_DT_PIN']
        self.sck_pin = settings.BIRDY_SETTINGS['WEIGHT_SENSOR_SCK_PIN']
        self.hx711 = None
        self.calibration_factor = 1.0
        self.tare_offset = 0
        self.is_initialized = False
        # Gleitender Durchschnitt zur Glättung
        self.weight_history = []
        self.history_size = 5  # Letzte 5 Messungen speichern
        # Automatische Drift-Kompensation
        self.zero_readings = []  # Messungen wenn Waage leer ist
        self.stable_readings = []  # Stabile Messungen (unabhängig vom Gewicht)
        self.last_weight_stable = None  # Letztes stabiles Gewicht
        self.last_drift_compensation = time.time()
        self.drift_compensation_interval = 3600  # Alle 60 Minuten prüfen
        
    def initialize(self):
        """Initialisiere HX711 Sensor"""
        if HX711 is None:
            logger.error("HX711 library not available")
            return False
            
        try:
            logger.info(f"Pins used for weight sensor pins DT:{self.dt_pin}, SCK:{self.sck_pin}")
            self.hx711 = HX711(dout_pin=self.dt_pin, pd_sck_pin=self.sck_pin, gain=128, channel='A')
            
            # Reset sensor
            result = self.hx711.reset()
            if result:			# you can check if the reset was successful
                logger.info(f"Reset of weight sensor successfull")
            else:
                logger.error(f"Reset of weight sensor not successfull")
            
            time.sleep(0.5)
            
            self.is_initialized = True
            logger.info(f"Weight sensor initialized on pins DT:{self.dt_pin}, SCK:{self.sck_pin}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize weight sensor: {e}")
            self.is_initialized = False
            return False
    
    def tare(self, samples=10):
        """Tara - Nullstellung des Sensors"""
        if not self.is_initialized:
            logger.warning("Sensor not initialized, attempting to initialize...")
            if not self.initialize():
                return False
        
        try:
            logger.info("Performing tare...")
            
            # Mehrere Messungen für Durchschnitt
            readings = []
            for i in range(samples):
                try:
                    val = self.hx711.get_raw_data(NUMBER_HW_MEASUREMENTS)
                    if val is not False:  # HX711 gibt False bei Fehler zurück
                        for j in range (NUMBER_HW_MEASUREMENTS):
                            readings.append(val[j])
                    time.sleep(0.1)
                except Exception as e:
                    logger.warning(f"Reading {i} failed: {e}")
                    continue
            
            if not readings:
                logger.error("No valid readings during tare")
                return False
            
            self.tare_offset = sum(readings) / len(readings)
            logger.info(f"Tare completed: offset = {self.tare_offset:.2f} (from {len(readings)} readings)")
            return True
                
        except Exception as e:
            logger.error(f"Tare failed: {e}")
            return False
    
    def calibrate(self, known_weight_grams, samples=10):
        """
        Kalibrierung mit bekanntem Gewicht
        
        Args:
            known_weight_grams: Bekanntes Kalibriergewicht in Gramm
            samples: Anzahl Messungen für Durchschnitt
        """
        if not self.is_initialized:
            logger.warning("Sensor not initialized, attempting to initialize...")
            if not self.initialize():
                return False
        
        try:
            # Erst tarieren (ohne Gewicht)
            print("\n=== Wägezellen Kalibrierung ===")
            print("Schritt 1: Tara (Nullstellung)")
            print("Bitte alle Gewichte entfernen und ENTER drücken...")
            input()
            
            if not self.tare(samples):
                print("✗ Tara fehlgeschlagen!")
                return False
            
            print("✓ Tara abgeschlossen\n")
            
            # Dann mit bekanntem Gewicht messen
            print(f"Schritt 2: Kalibrierung mit {known_weight_grams}g")
            print(f"Bitte {known_weight_grams}g auflegen und ENTER drücken...")
            input()
            
            print(f"Messe {samples} Werte...")
            readings = []
            for i in range(samples):
                try:
                    val = self.hx711.get_raw_data(NUMBER_HW_MEASUREMENTS)
                    if val is not False:
                        for j in range (NUMBER_HW_MEASUREMENTS):
                            readings.append(val[j] - self.tare_offset)
                    time.sleep(0.2)
                except Exception as e:
                    logger.warning(f"Reading {i} failed: {e}")
                    continue
            
            if not readings:
                logger.error("No valid readings during calibration")
                print("✗ Keine gültigen Messungen!")
                return False
            
            avg_reading = sum(readings) / len(readings)
            self.calibration_factor = avg_reading / known_weight_grams
            
            logger.info(f"Calibration completed: factor = {self.calibration_factor:.6f}")
            print(f"\n✓ Kalibrierung abgeschlossen!")
            print(f"Kalibrierungsfaktor: {self.calibration_factor:.6f}")
            print(f"Durchschnittswert: {avg_reading:.2f}")
            print(f"Erwartetes Gewicht: {known_weight_grams}g")
            print(f"Berechnetes Gewicht: {avg_reading / self.calibration_factor:.2f}g")
            
            # Speichere Kalibrierung
            self._save_calibration()
            
            return True
                
        except Exception as e:
            logger.error(f"Calibration failed: {e}")
            print(f"✗ Kalibrierung fehlgeschlagen: {e}")
            return False
    
    def read_weight_grams(self, samples=10):
        """
        Lese aktuelles Gewicht in Gramm mit verbesserter Filterung

        Args:
            samples: Anzahl Messungen für Durchschnitt (Standard: 10)

        Returns:
            float: Gewicht in Gramm oder None bei Fehler
        """
        if not self.is_initialized:
            logger.warning("Sensor not initialized")
            return None

        try:
            readings = []
            for _ in range(samples):
                try:
                    val = self.hx711.get_raw_data(NUMBER_HW_MEASUREMENTS)
                    if val is not False:
                        for j in range (NUMBER_HW_MEASUREMENTS):
                            readings.append(val[j])
                    time.sleep(0.1)  # Längere Pause zwischen Messungen
                except:
                    continue

            if not readings:
                return None

            # Entferne Ausreißer (z.B. durch Vibrationen beim Landen/Abheben)
            # Sortiere und entferne obere und untere 10%
            readings_sorted = sorted(readings)
            trim_count = max(1, int(len(readings_sorted) * 0.1))
            trimmed_readings = readings_sorted[trim_count:-trim_count]

            if not trimmed_readings:
                trimmed_readings = readings_sorted

            avg_reading = sum(trimmed_readings) / len(trimmed_readings)
            weight_raw = avg_reading - self.tare_offset
            weight_grams = weight_raw / self.calibration_factor if self.calibration_factor != 0 else 0

            # Debug-Logging mit Min/Max für Schwankungsanalyse
            min_reading = min(readings)
            max_reading = max(readings)
            spread = max_reading - min_reading

            # Negative Werte auf 0 setzen (aber nur kleine negative Werte durch Sensor-Drift)
            # Wenn Wert > -50g ist, setze auf 0, sonst könnte Kalibrierung falsch sein
            if weight_grams < 0 and weight_grams > -50:
                weight_grams = 0.0

            # Gleitender Durchschnitt zur Glättung von Schwankungen
            self.weight_history.append(weight_grams)
            if len(self.weight_history) > self.history_size:
                self.weight_history.pop(0)

            smoothed_weight = sum(self.weight_history) / len(self.weight_history)

            # Automatische Drift-Kompensation
            # 1. Wenn Waage nahezu leer ist (< 5g), sammle Null-Punkt
            if -5 < smoothed_weight < 5:
                self.zero_readings.append(avg_reading)
                if len(self.zero_readings) > 20:
                    self.zero_readings.pop(0)

            # 2. Sammle stabile Messungen (wenn spread klein ist, d.h. wenig Schwankung)
            # Spread < 100 bedeutet stabile Bedingungen (kein Vogel landet/fliegt)
            if spread < 100:
                self.stable_readings.append((avg_reading, smoothed_weight))
                if len(self.stable_readings) > 30:
                    self.stable_readings.pop(0)

            # Alle X Minuten: Prüfe ob Drift-Kompensation nötig ist
            current_time = time.time()
            if current_time - self.last_drift_compensation > self.drift_compensation_interval:
                self._compensate_drift()
                self.last_drift_compensation = current_time

            logger.debug(f"Weight sensor: raw={weight_grams:.1f}g, smoothed={smoothed_weight:.1f}g, spread={spread:.2f}, zero={len(self.zero_readings)}, stable={len(self.stable_readings)}")

            return smoothed_weight
            
        except Exception as e:
            logger.error(f"Failed to read weight: {e}")
            return None
    
    def _compensate_drift(self):
        """
        Kompensiere Temperaturdrift automatisch

        Strategie 1: Wenn Waage leer ist - nutze Null-Messungen
        Strategie 2: Wenn Futter auf Waage - nutze stabile Gewichts-Trend
        """
        try:
            # Strategie 1: Waage ist leer (bevorzugt, da genauer)
            if len(self.zero_readings) >= 10:
                avg_zero = sum(self.zero_readings) / len(self.zero_readings)
                drift = avg_zero - self.tare_offset

                if abs(drift) > 50:
                    old_offset = self.tare_offset
                    self.tare_offset += drift * 0.5

                    logger.info(f"Drift compensation (zero): tare_offset {old_offset:.2f} -> {self.tare_offset:.2f} (drift: {drift:.2f})")
                    self._save_calibration()
                    self.zero_readings = []
                    return
                else:
                    logger.debug(f"Zero-based drift within tolerance: {drift:.2f}")

            # Strategie 2: Futter auf Waage - erkenne Drift trotz langsamer Gewichtsänderung
            # Idee: Wenn raw readings stärker driften als das Gewicht sich ändert,
            # dann ist die Differenz wahrscheinlich Temperaturdrift
            if len(self.stable_readings) >= 20:
                # Teile in zwei Hälften: alt (erste 50%) vs neu (letzte 50%)
                mid = len(self.stable_readings) // 2
                old_readings = self.stable_readings[:mid]
                new_readings = self.stable_readings[mid:]

                # Berechne Durchschnitte
                old_weights = [w for _, w in old_readings]
                new_weights = [w for _, w in new_readings]
                old_raw = [r for r, _ in old_readings]
                new_raw = [r for r, _ in new_readings]

                avg_old_weight = sum(old_weights) / len(old_weights)
                avg_new_weight = sum(new_weights) / len(new_weights)
                avg_old_raw = sum(old_raw) / len(old_raw)
                avg_new_raw = sum(new_raw) / len(new_raw)

                # Gewichtsänderung in Gramm (kann durch Fressen sein)
                weight_change = avg_new_weight - avg_old_weight  # Kann negativ sein (Futter wird gegessen)

                # Raw reading Änderung in Counts
                raw_change = avg_new_raw - avg_old_raw

                # Erwartete raw change basierend auf Gewichtsänderung
                expected_raw_change = weight_change * self.calibration_factor

                # Die Differenz ist wahrscheinlich Drift
                drift_component = raw_change - expected_raw_change

                logger.debug(f"Drift analysis: weight_change={weight_change:.1f}g, raw_change={raw_change:.1f}, expected_raw={expected_raw_change:.1f}, drift_component={drift_component:.1f}")

                # Wenn die Drift-Komponente signifikant ist (> 100 counts ≈ 2-3g)
                if abs(drift_component) > 100:
                    old_offset = self.tare_offset
                    # Sanfte Anpassung (25%) weil wir Gewichtsänderung mit Drift vermischen
                    self.tare_offset += drift_component * 0.25

                    logger.info(f"Drift compensation (stable+change): tare_offset {old_offset:.2f} -> {self.tare_offset:.2f} (drift: {drift_component:.2f}, weight changed {weight_change:.1f}g from {avg_old_weight:.1f}g to {avg_new_weight:.1f}g)")
                    self._save_calibration()
                    # Behalte einige neuere Messungen als Basis für nächste Runde
                    self.stable_readings = self.stable_readings[mid:]
                    return
                else:
                    logger.debug(f"Drift component within tolerance: {drift_component:.2f}")

            logger.debug("Not enough data for drift compensation")

        except Exception as e:
            logger.error(f"Drift compensation failed: {e}")

    def _save_calibration(self):
        """Speichere Kalibrierungsdaten"""
        try:
            import json
            from pathlib import Path
            
            config_file = Path(__file__).parent.parent / 'weight_calibration.json'
            
            data = {
                'calibration_factor': self.calibration_factor,
                'tare_offset': self.tare_offset,
                'timestamp': time.time()
            }
            
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Calibration saved to {config_file}")
            print(f"Kalibrierung gespeichert in: {config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save calibration: {e}")
    
    def _load_calibration(self):
        """Lade gespeicherte Kalibrierungsdaten"""
        try:
            import json
            from pathlib import Path

            config_file = Path(__file__).parent.parent / 'weight_calibration.json'

            if not config_file.exists():
                return False

            with open(config_file, 'r') as f:
                data = json.load(f)

            self.calibration_factor = data.get('calibration_factor', 1.0)
            self.tare_offset = data.get('tare_offset', 0)

            # Initialisiere Drift-Kompensation Timer
            self.last_drift_compensation = time.time()

            logger.info(f"Calibration loaded: factor={self.calibration_factor:.6f}, offset={self.tare_offset:.2f}")
            return True
            
        except Exception as e:
            logger.warning(f"Could not load calibration: {e}")
            return False
    
    def cleanup(self):
        """Cleanup GPIO"""
        try:
            if self.hx711:
                # HX711 Library hat kein explizites cleanup
                logger.info("Weight sensor cleanup")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


# Singleton Instance
_weight_sensor_instance = None

def get_weight_sensor(auto_init=True):
    """
    Hole Singleton Instance des Weight Sensors

    Args:
        auto_init: Wenn True, initialisiere Sensor automatisch (Standard: True)
                  Setze auf False wenn nur Referenz benötigt wird
    """
    global _weight_sensor_instance
    if _weight_sensor_instance is None:
        _weight_sensor_instance = WeightSensor()
        if auto_init:
            if _weight_sensor_instance.initialize():
                # Versuche gespeicherte Kalibrierung zu laden
                _weight_sensor_instance._load_calibration()
    elif auto_init and not _weight_sensor_instance.is_initialized:
        if _weight_sensor_instance.initialize():
            _weight_sensor_instance._load_calibration()
    return _weight_sensor_instance