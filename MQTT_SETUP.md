# Home Assistant MQTT Integration - Setup Anleitung

## Übersicht

Birdy publiziert alle 60 Sekunden Sensor-Daten via MQTT zu Home Assistant:
- **Futtermenge** (Gewicht in Gramm)
- **Vogel anwesend** (Binary Sensor)
- **Letzte Spezies** (Name des Vogels)
- **Besuche heute** (Anzahl Detections)

## 1. MQTT Broker in Home Assistant einrichten

### Mosquitto Broker installieren
1. **Home Assistant** öffnen
2. **Einstellungen** → **Add-ons** → **Add-on Store**
3. Suche nach **"Mosquitto broker"**
4. **Installieren** klicken
5. **Start** klicken
6. **Start on boot** aktivieren

### MQTT User anlegen
1. Öffne das **Mosquitto broker Add-on**
2. Gehe zum Tab **"Konfiguration"**
3. Füge einen User hinzu (oder nutze die Home Assistant User-Verwaltung):

```yaml
logins:
  - username: birdy
    password: birdy123
```

4. **Speichern** und **Neustart** des Add-ons

## 2. MQTT Integration in Home Assistant aktivieren

1. **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
2. Suche nach **"MQTT"**
3. Konfiguriere:
   - **Broker**: `localhost` (wenn auf demselben System) oder IP-Adresse
   - **Port**: `1883`
   - **Username**: `birdy`
   - **Password**: `birdy123`
4. **Absenden** klicken

## 3. Birdy MQTT Konfiguration

Bearbeite `/home/pi/birdy_project/birdy_config/settings.py`:

```python
BIRDY_SETTINGS = {
    ...
    # MQTT Home Assistant Integration
    'MQTT_BROKER': 'localhost',     # IP von Home Assistant (z.B. '192.168.1.100')
    'MQTT_PORT': 1883,
    'MQTT_USERNAME': 'birdy',       # Mosquitto User
    'MQTT_PASSWORD': 'birdy123',    # Mosquitto Passwort
    'MQTT_TOPIC_PREFIX': 'birdy',
}
```

**Wichtig:**
- Wenn Home Assistant auf **demselben Raspberry Pi** läuft: `'MQTT_BROKER': 'localhost'`
- Wenn Home Assistant auf **anderem System** läuft: `'MQTT_BROKER': '192.168.1.100'` (IP-Adresse)

## 4. System neu starten

```bash
cd /home/pi/birdy_project
./restart_birdy.sh
```

## 5. Testen der Verbindung

### In Home Assistant
Nach dem Neustart sollten automatisch **neue Geräte und Sensoren** erscheinen:

1. **Einstellungen** → **Geräte & Dienste** → **MQTT**
2. Du solltest das Gerät **"Birdy Bird Feeder"** sehen mit folgenden Entities:
   - `sensor.birdy_feed_weight` (Futtermenge in g)
   - `binary_sensor.birdy_bird_present` (Vogel anwesend)
   - `sensor.birdy_last_species` (Letzte Vogelart)
   - `sensor.birdy_visits_today` (Besuche heute)

### MQTT Logs prüfen

**In Birdy Logs:**
```bash
tail -f /home/pi/birdy_project/logs/birdy.log | grep MQTT
```

Du solltest sehen:
```
INFO MQTT client connecting to localhost:1883
INFO MQTT connected successfully
INFO Home Assistant discovery messages published
```

**In Celery Worker Logs:**
```bash
tail -f /home/pi/birdy_project/logs/celery_worker.log | grep mqtt
```

Alle 60 Sekunden sollte Status publiziert werden.

## 6. Troubleshooting

### MQTT verbindet nicht
```bash
# Prüfe ob Mosquitto läuft
mosquitto -h

# Teste Verbindung manuell
mosquitto_sub -h localhost -p 1883 -u birdy -P birdy123 -t 'birdy/#' -v
```

### Birdy publiziert nicht
```bash
# Prüfe Celery Worker Logs
tail -f logs/celery_worker.log

# Prüfe ob publish_status_task läuft
grep "publish_status_task" logs/celery_worker.log
```

### Home Assistant erkennt Gerät nicht
1. Gehe zu **MQTT Integration** in Home Assistant
2. Klicke auf **"Geräte neu erkennen"** oder **"MQTT neu laden"**
3. Prüfe MQTT Explorer (optional):
   - Topic: `homeassistant/sensor/birdy/#`
   - Topic: `birdy/#`

## 7. Was wird publiziert?

### Discovery Messages (einmalig bei Verbindung)
```
homeassistant/sensor/birdy/feed_weight/config
homeassistant/binary_sensor/birdy/bird_detected/config
homeassistant/sensor/birdy/species/config
homeassistant/sensor/birdy/visits_today/config
```

### Status Updates (alle 60 Sekunden)
```
birdy/feed/weight → "125.5"
birdy/stats/today → "7"
birdy/stats/daily → {"date": "2026-01-20", "total_visits": 7, "top_species": [...]}
```

### Bei Vogel-Detektion (Event-basiert)
```
birdy/bird/detected → "ON"
birdy/bird/species → "Blaumeise"
birdy/bird/attributes → {"species": "Blaumeise", "confidence": "85%", ...}
```

## 8. Home Assistant Dashboard Beispiel

```yaml
type: entities
title: Birdy Vogelfutterhaus
entities:
  - entity: sensor.birdy_feed_weight
    name: Futtermenge
  - entity: binary_sensor.birdy_bird_present
    name: Vogel anwesend
  - entity: sensor.birdy_last_species
    name: Letzte Art
  - entity: sensor.birdy_visits_today
    name: Besuche heute
```

## Architektur

```
┌─────────────────────┐
│   start_birdy       │
│   (Main Process)    │
│   - Updates DB      │
└─────────────────────┘
           │
           ▼
    ┌──────────────┐
    │  DATABASE    │
    │ SensorStatus │
    └──────────────┘
           │
           ▼
┌─────────────────────┐
│  Celery Worker      │ (alle 60s)
│  publish_status     │──────┐
└─────────────────────┘      │
                             │
                             ▼
                     ┌──────────────┐
                     │ MQTT Broker  │
                     │  Mosquitto   │
                     └──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Home Assistant  │
                    │   Integration   │
                    └─────────────────┘
```

## Fertig!

Nach dem Setup solltest du alle Birdy-Sensoren in Home Assistant sehen und verwenden können.
