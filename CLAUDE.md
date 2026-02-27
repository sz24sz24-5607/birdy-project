# Birdy – Projekt-Onboarding für Claude

Smart Bird Feeder auf Raspberry Pi 5. Erkennt Vögel per PIR + Kamera + TFLite ML,
speichert Fotos/Videos, zeigt Statistiken im Web-Dashboard, meldet an Home Assistant via MQTT.

---

## Umgebung

- Python 3.13, Venv: `venv/` → aktivieren mit `source venv/bin/activate`
- Django 5.0, PostgreSQL (`birdy_db`), Celery + Redis
- Produktions-Settings: `DJANGO_SETTINGS_MODULE=birdy_config.settings_production`
- Secrets in `.env` (gitignored) – niemals hardcoden, immer `os.environ.get()`

---

## Häufige Befehle

```bash
# Service-Verwaltung
sudo systemctl restart birdy-gunicorn
sudo systemctl restart birdy-celery-worker
sudo systemctl restart birdy-celery-beat
sudo systemctl restart birdy-detection
sudo systemctl status birdy-gunicorn   # Fehler prüfen

# Django
source venv/bin/activate
python manage.py check
python manage.py migrate
python manage.py collectstatic --no-input

# Logs
tail -f logs/birdy.log
tail -f logs/start_birdy.log
journalctl -u birdy-gunicorn -f
```

---

## Architektur

```
PIR (GPIO 17) → start_birdy (Thread) → BirdDetectionService
  → picamera2 (4s Video, 720p H.264)
  → 8 Frames extrahieren → TFLite Classifier
  → Bestes Frame (höchste Confidence, Swiss-Mittelland-Allowlist)
  → confidence >= 0.5 → Photo + Video auf USB (/mnt/birdy_storage)
  → DB: BirdDetection, DailyStatistics
  → MQTT → Home Assistant (192.168.178.150)

Celery Beat (täglich 00:05): MonthlyStatistics + YearlyStatistics aktualisieren
Celery Beat (60s): SensorStatus + MQTT publish
```

---

## Django Apps

| App | Zweck |
|-----|-------|
| `species/` | BirdSpecies, BirdDetection, Daily/Monthly/YearlyStatistics |
| `sensors/` | PIREvent, WeightMeasurement, SensorStatus |
| `media_manager/` | Photo, Video (gespeichert auf USB) |
| `homeassistant/` | MQTT-Client, publish_status_task |
| `api/` | DRF REST API – alle Endpoints unter `/api/` |
| `birdy_config/` | Settings, Haupt-Views (home, detections, statistics) |
| `hardware/` | Treiber: camera.py, classifier.py, pir_monitor.py, weight_sensor.py |
| `services/` | bird_detection.py – Orchestrierung des Erkennungs-Workflows |

---

## Wichtige Dateipfade

| Was | Pfad |
|-----|------|
| Haupt-Views | `birdy_config/views.py` |
| URLs | `birdy_config/urls.py` |
| Settings | `birdy_config/settings.py` / `settings_production.py` |
| Templates | `templates/base.html`, `home.html`, `detections.html`, `statistics.html` |
| Detection-Service | `services/bird_detection.py` |
| TFLite-Classifier | `hardware/classifier.py` |
| Species-Allowlist | `ml_models/swiss_midland_allowlist.txt` (151 Arten) |
| Celery-Tasks | `species/tasks.py`, `sensors/tasks.py`, `homeassistant/tasks.py` |
| API-Endpoints | `api/urls.py`, `api/views.py` |
| Logs | `logs/birdy.log`, `logs/start_birdy.log`, `logs/gunicorn_*.log` |
| Secrets | `.env` (gitignored) |
| Fotos/Videos | `/mnt/birdy_storage/photos/`, `/mnt/birdy_storage/videos/` |
| NAS-Backup | `/mnt/nas/birdy_backup/` (Synology CIFS, credentials: `/etc/nas-credentials`) |

---

## Frontend

- Kein Bootstrap/Tailwind – reines Custom CSS, inline in `base.html` `<style>`-Block
- Chart.js 4.x nur auf der Statistik-Seite (`statistics.html`), via CDN
- Routen: `/` (Dashboard), `/detections/`, `/statistics/`, `/admin/`, `/api/`
- Media-Dateien via `re_path + django.views.static.serve` (weil DEBUG=False)

---

## Key Conventions / Do's & Don'ts

- **Niemals** `DEBUG=True` in Produktion setzen
- **Niemals** Secrets hardcoden – immer aus `.env` via `os.environ.get()`
- **Kamera-Zugriff** nur im `start_birdy`-Prozess (Thread, nicht Celery) – picamera2 ist single-process
- **Media-Pfad** ist `/mnt/birdy_storage`, nicht im Projektverzeichnis
- **NAS rsync** braucht `--no-specials --no-devices` (CIFS-Mount)
- **Nach Django-Änderungen**: `sudo systemctl restart birdy-gunicorn`
- **Nach Celery-Task-Änderungen**: auch `birdy-celery-worker` und `birdy-celery-beat` restarten
- **Nach Detection-Service-Änderungen**: `birdy-detection` restarten
- **Kein Auto-Commit** – User committet und pusht selbst (oder explizit anfragen)

---

## Hardware

| Komponente | Details |
|-----------|---------|
| Raspberry Pi 5 | 8 GB RAM |
| Kamera | Pi Camera Module, 1280×720 @ 15fps |
| PIR | HC-SR501, GPIO 17 |
| Wägesensor | HX711, DT=GPIO 5, SCK=GPIO 6 |
| Speicher | USB-Drive `/mnt/birdy_storage` |

---

## Systemd Services

| Service | Funktion |
|---------|---------|
| `birdy-gunicorn` | Web-App auf Port 8000 |
| `birdy-celery-worker` | Task-Queue-Worker |
| `birdy-celery-beat` | Periodische Tasks (Cron) |
| `birdy-detection` | PIR-Loop + ML-Erkennung (`manage.py start_birdy`) |

Alle nutzen `EnvironmentFile=/home/pi/birdy_project/.env`.
