"""
Home Assistant MQTT Client Integration
"""
import json
import logging
from django.conf import settings
import paho.mqtt.client as mqtt

logger = logging.getLogger('birdy')


class HomeAssistantMQTT:
    """MQTT Client für Home Assistant Integration"""
    
    def __init__(self):
        self.broker = settings.BIRDY_SETTINGS['MQTT_BROKER']
        self.port = settings.BIRDY_SETTINGS['MQTT_PORT']
        self.username = settings.BIRDY_SETTINGS['MQTT_USERNAME']
        self.password = settings.BIRDY_SETTINGS['MQTT_PASSWORD']
        self.topic_prefix = settings.BIRDY_SETTINGS['MQTT_TOPIC_PREFIX']
        
        self.client = None
        self.is_connected = False
        
    def initialize(self):
        """Initialisiere MQTT Client"""
        try:
            self.client = mqtt.Client(client_id="birdy_feeder")
            
            # Callbacks setzen
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            
            # Authentication wenn konfiguriert
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            # Verbinde zu Broker
            self.client.connect(self.broker, self.port, keepalive=60)
            
            # Starte Loop in separatem Thread
            self.client.loop_start()
            
            logger.info(f"MQTT client connecting to {self.broker}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MQTT client: {e}")
            return False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback bei Verbindung"""
        if rc == 0:
            self.is_connected = True
            logger.info("MQTT connected successfully")
            
            # Publiziere Discovery Messages für Home Assistant
            self._publish_discovery()
        else:
            logger.error(f"MQTT connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback bei Disconnect"""
        self.is_connected = False
        logger.warning(f"MQTT disconnected with code {rc}")
    
    def _publish_discovery(self):
        """Publiziere Home Assistant Discovery Messages"""
        
        # Sensor: Futtermenge
        weight_config = {
            "name": "Birdy Feed Weight",
            "state_topic": f"{self.topic_prefix}/feed/weight",
            "unit_of_measurement": "g",
            "device_class": "weight",
            "unique_id": "birdy_feed_weight",
            "device": {
                "identifiers": ["birdy_feeder"],
                "name": "Birdy Bird Feeder",
                "model": "DIY Smart Feeder",
                "manufacturer": "Birdy Project"
            }
        }
        self.client.publish(
            f"homeassistant/sensor/birdy/feed_weight/config",
            json.dumps(weight_config),
            retain=True
        )
        
        # Binary Sensor: Vogel anwesend
        bird_config = {
            "name": "Birdy Bird Present",
            "state_topic": f"{self.topic_prefix}/bird/detected",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device_class": "motion",
            "unique_id": "birdy_bird_present",
            "device": {
                "identifiers": ["birdy_feeder"],
                "name": "Birdy Bird Feeder"
            }
        }
        self.client.publish(
            f"homeassistant/binary_sensor/birdy/bird_detected/config",
            json.dumps(bird_config),
            retain=True
        )
        
        # Sensor: Letzte Spezies
        species_config = {
            "name": "Birdy Last Species",
            "state_topic": f"{self.topic_prefix}/bird/species",
            "unique_id": "birdy_last_species",
            "icon": "mdi:bird",
            "device": {
                "identifiers": ["birdy_feeder"],
                "name": "Birdy Bird Feeder"
            }
        }
        self.client.publish(
            f"homeassistant/sensor/birdy/species/config",
            json.dumps(species_config),
            retain=True
        )
        
        # Sensor: Besuche heute
        visits_config = {
            "name": "Birdy Visits Today",
            "state_topic": f"{self.topic_prefix}/stats/today",
            "unit_of_measurement": "visits",
            "unique_id": "birdy_visits_today",
            "icon": "mdi:counter",
            "device": {
                "identifiers": ["birdy_feeder"],
                "name": "Birdy Bird Feeder"
            }
        }
        self.client.publish(
            f"homeassistant/sensor/birdy/visits_today/config",
            json.dumps(visits_config),
            retain=True
        )
        
        logger.info("Home Assistant discovery messages published")
    
    def publish_weight(self, weight_grams):
        """
        Publiziere Futtermenge
        
        Args:
            weight_grams: Gewicht in Gramm
        """
        if not self.is_connected:
            return
        
        topic = f"{self.topic_prefix}/feed/weight"
        self.client.publish(topic, f"{weight_grams:.1f}")
    
    def publish_bird_detected(self, detection):
        """
        Publiziere Vogel-Detektion
        
        Args:
            detection: BirdDetection Model Instance
        """
        if not self.is_connected:
            return
        
        # Bird Present
        self.client.publish(f"{self.topic_prefix}/bird/detected", "ON")
        
        # Species Name
        if detection.species:
            species_name = detection.species.common_name_de
            self.client.publish(f"{self.topic_prefix}/bird/species", species_name)
            
            # Zusätzliche Attribute als JSON
            attributes = {
                "species": species_name,
                "scientific_name": detection.species.scientific_name,
                "confidence": f"{detection.confidence:.2%}",
                "timestamp": detection.timestamp.isoformat()
            }
            self.client.publish(
                f"{self.topic_prefix}/bird/attributes",
                json.dumps(attributes)
            )
        
        logger.info("Bird detection published to MQTT")
    
    def publish_bird_left(self):
        """Publiziere dass Vogel weg ist"""
        if not self.is_connected:
            return
        
        self.client.publish(f"{self.topic_prefix}/bird/detected", "OFF")
    
    def publish_daily_stats(self, date):
        """
        Publiziere tägliche Statistiken

        Args:
            date: Datum für Statistik
        """
        if not self.is_connected:
            return

        from species.models import BirdDetection
        from django.db.models import Count, Avg

        # Gesamtbesuche heute (nur gültige Besuche mit Spezies)
        total_visits = BirdDetection.objects.filter(
            timestamp__date=date,
            processed=True,
            species__isnull=False  # Nur gültige Besuche (>=50% confidence, kein background)
        ).count()

        # Publiziere Anzahl Besuche heute
        self.client.publish(f"{self.topic_prefix}/stats/today", str(total_visits))

        # Top 5 Spezies heute
        top_species = BirdDetection.objects.filter(
            timestamp__date=date,
            processed=True,
            species__isnull=False
        ).values('species__common_name_de', 'species__scientific_name').annotate(
            visits=Count('id'),
            avg_conf=Avg('confidence')
        ).order_by('-visits')[:5]

        stats_data = {
            "date": date.isoformat(),
            "total_visits": total_visits,
            "top_species": [
                {
                    "name": stat['species__common_name_de'],
                    "scientific_name": stat['species__scientific_name'],
                    "visits": stat['visits'],
                    "avg_confidence": f"{stat['avg_conf']:.2%}" if stat['avg_conf'] else "0%"
                }
                for stat in top_species
            ]
        }

        self.client.publish(
            f"{self.topic_prefix}/stats/daily",
            json.dumps(stats_data)
        )
    
    def cleanup(self):
        """Cleanup MQTT Client"""
        try:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
                logger.info("MQTT client disconnected")
        except Exception as e:
            logger.error(f"MQTT cleanup failed: {e}")


# Singleton Instance
_mqtt_instance = None

def get_mqtt_client():
    """Hole Singleton Instance des MQTT Clients"""
    global _mqtt_instance
    if _mqtt_instance is None:
        _mqtt_instance = HomeAssistantMQTT()
        _mqtt_instance.initialize()
    return _mqtt_instance