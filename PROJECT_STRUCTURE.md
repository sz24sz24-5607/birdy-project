# Birdy Project Structure

Aufgeräumt am: $(date +%Y-%m-%d)

## Aktive Verzeichnisse

### Core Application
```
birdy_project/
├── birdy_config/         # Django settings, Celery config, URLs
├── hardware/             # Hardware interfaces (PIR, Camera, Weight)
├── sensors/              # Sensor models, management commands
├── services/             # Bird detection service
├── species/              # Species detection, classification
├── media_manager/        # Photo/Video management
├── homeassistant/        # Home Assistant MQTT integration
├── api/                  # REST API (optional)
└── manage.py            # Django management
```

### Configuration & Deployment
```
├── systemd/              # Systemd service files for production
├── logs/                 # Application logs
├── media/                # Django media files
├── static/               # Static files
├── staticfiles/          # Collected static files
└── venv/                 # Python virtual environment
```

### ML & Models
```
└── ml_models/            # TensorFlow Lite models for bird classification
```

## Aktive Scripts

### Development & Operations
- **start_dev.sh** - Start development environment (Redis, Celery, Django, Birdy)
- **stop_dev.sh** - Stop all services
- **restart_birdy.sh** - Restart Birdy detection system

### Backup & Recovery
- **backup_to_nas.sh** - Backup project to NAS
- **restore_from_nas.sh** - Restore project from NAS backup

### Analysis
- **analyze_pir_pattern.py** - Analyze PIR trigger patterns from logs

### Maintenance
- **move_to_archive.sh** - Move unused files to archive (already executed)

## Aktive Dokumentation

### Setup & Configuration
- **GIT_SETUP.md** - Git und NAS Backup Setup Anleitung
- **QUICK_START_BACKUP.md** - Schnelleinstieg Backup
- **PRODUCTION_SETUP.md** - Production Deployment Guide
- **MQTT_SETUP.md** - Home Assistant MQTT Integration

### Architecture & Development
- **CAMERA_ARCHITECTURE.md** - Camera System Architektur
- **SPECIES_DETECTION_RULES.md** - Species Classification Regeln
- **LGPIO_MIGRATION.md** - Migration zu native lgpio (Raspberry Pi 5)

### Troubleshooting & Bugfixes
- **PIR_TROUBLESHOOTING.md** - PIR Debugging Guide
- **BUGFIX_PIR_8S_DELAY.md** - Dokumentation des 8-Sekunden Delay Bugfix

## Archivierte Dateien

Verschoben nach `birdy_archive/`:

### Dokumentation (veraltet/redundant)
- CELERY_WORKER_SETUP.md → Ersetzt durch PRODUCTION_SETUP.md
- PIR_DEBUGGING_PI5.md → Info jetzt in PIR_TROUBLESHOOTING.md
- GPIO_MONITORING.md → Nicht mehr relevant mit native lgpio
- RASPBERRY_PI5_GPIO.md → Covered in LGPIO_MIGRATION.md

### Scripts (nicht mehr benötigt)
- monitor_pir_gpio.py → Funktioniert nicht auf Pi 5 mit claimed pins
- monitor_pir_sysfs.py → sysfs nicht verfügbar auf Pi 5
- monitor_pir_direct.py → Pin Konflikt mit Hauptapp
- monitor_pir.sh → Wrapper für obige Scripts

### Duplikate
- settings.py → Duplikat (echte Datei: birdy_config/settings.py)
- check_status.sh → Funktionalität in start_dev.sh

### Build Artifacts (können gelöscht werden)
- tensorflow_src/ (1.8 GB)
- tflite_build/ (2.0 GB)
- venv_old/ (1.8 GB)

**Speicherplatz freigeben:**
```bash
rm -rf birdy_archive/tensorflow_src
rm -rf birdy_archive/tflite_build
rm -rf birdy_archive/venv_old
# → Spart ~5.6 GB!
```

## Wichtige Dateien

### Configuration
- `birdy_config/settings.py` - Django Settings
- `birdy_config/celery.py` - Celery Configuration
- `.gitignore` - Git ignore patterns
- `requirements.txt` - Python dependencies

### Hardware Layer
- `hardware/pir_sensor.py` - PIR Motion Sensor (native lgpio)
- `hardware/camera.py` - Picamera2 + rpicam-vid
- `hardware/weight_sensor.py` - HX711 Weight Sensor

### Detection Workflow
- `sensors/management/commands/start_birdy.py` - Main detection loop
- `services/bird_detection.py` - Detection workflow orchestration
- `species/classifier.py` - TensorFlow Lite classification

## Git Ignore

Folgende Dateien/Ordner werden NICHT gesichert:
- `venv/` - Virtual Environment (wird neu erstellt)
- `logs/` - Log Dateien (zu groß)
- `db.sqlite3` - SQLite Datenbank (wird migriert)
- `media/photos/`, `media/videos/` - Media Files (separat gesichert)
- `__pycache__/`, `*.pyc` - Python Cache
- `birdy_archive/` - Archiv (muss nicht gesichert werden)

Siehe `.gitignore` für vollständige Liste.

## Quick Commands

```bash
# Development
./start_dev.sh          # Start all services
./stop_dev.sh           # Stop all services
./restart_birdy.sh      # Restart detection only

# Backup
./backup_to_nas.sh      # Manual backup to NAS

# Analysis
python3 analyze_pir_pattern.py  # Analyze PIR patterns

# Logs
tail -f logs/birdy.log | grep "PIR:"     # Watch PIR events
tail -f logs/celery_worker.log           # Watch Celery tasks
tail -f logs/django.log                  # Watch Django
```

## Projektgröße

```
Aktiver Code:         ~50 MB
Virtual Environment:  ~500 MB
Logs (variabel):      ~10-100 MB
Media (extern):       Auf USB/NAS
Archive:              ~5.5 GB (kann gelöscht werden)
```

## Nächste Schritte

1. ✅ **Code aufgeräumt** - Archiv erstellt
2. ⏳ **Git initialisieren** - `git init && git add . && git commit -m "Initial commit"`
3. ⏳ **NAS Backup einrichten** - NAS mounten und `./backup_to_nas.sh` testen
4. ⏳ **System testen** - Nach PIR False Triggers überwachen
5. ⏳ **Archive löschen** - `rm -rf birdy_archive/` um 5.6 GB freizugeben (optional)
