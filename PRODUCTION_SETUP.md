# Birdy Production Setup Guide

Vollständige Anleitung für die Produktiv-Installation von Birdy auf Raspberry Pi.

## Übersicht

Für den Produktiv-Betrieb werden folgende Komponenten als Systemd-Services eingerichtet:

1. **Redis** - Message Broker (bereits als System-Service)
2. **Celery Worker** - Background Tasks (Sensor Updates, MQTT, Statistiken)
3. **Celery Beat** - Periodische Tasks (MQTT Publishing, Backup)
4. **Gunicorn** - Django WSGI Server (Production Web Server)
5. **Birdy Detection** - Bird Detection System (PIR + Kamera + ML)
6. **Nginx** - Reverse Proxy & Static Files (optional, empfohlen)

---

## 1. Voraussetzungen

```bash
# System-Pakete installieren
sudo apt-get update
sudo apt-get install -y nginx redis-server postgresql postgresql-contrib

# Gunicorn installieren (im venv)
source ~/birdy_project/venv/bin/activate
pip install gunicorn
```

---

## 2. Datenbank (Production)

### Option A: SQLite (aktuell, einfach)
- Funktioniert für kleine bis mittlere Installationen
- Aktuell in Verwendung: `db.sqlite3`
- **Kein Setup nötig**

### Option B: PostgreSQL (empfohlen für Production)

```bash
# PostgreSQL Datenbank erstellen
sudo -u postgres psql

CREATE DATABASE birdy_db;
CREATE USER birdy_user WITH PASSWORD 'dein_sicheres_passwort';
ALTER ROLE birdy_user SET client_encoding TO 'utf8';
ALTER ROLE birdy_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE birdy_user SET timezone TO 'Europe/Berlin';
GRANT ALL PRIVILEGES ON DATABASE birdy_db TO birdy_user;
\q
```

**Django Settings anpassen** (`birdy_config/settings.py`):

```python
# PostgreSQL installieren
pip install psycopg2-binary

# In settings.py ändern:
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'birdy_db',
        'USER': 'birdy_user',
        'PASSWORD': 'dein_sicheres_passwort',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

**Migration durchführen:**

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

---

## 3. Django Production Settings

**Datei erstellen:** `birdy_config/settings_production.py`

```python
from .settings import *

DEBUG = False

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'your-raspberry-pi-ip',  # z.B. 192.168.1.100
    'your-domain.com',       # Falls du eine Domain hast
]

# Static Files
STATIC_ROOT = '/home/pi/birdy_project/staticfiles/'

# Security Settings
CSRF_COOKIE_SECURE = False  # True wenn HTTPS
SESSION_COOKIE_SECURE = False  # True wenn HTTPS
SECURE_SSL_REDIRECT = False  # True wenn HTTPS

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/home/pi/birdy_project/logs/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

**Static Files sammeln:**

```bash
python manage.py collectstatic --noinput
```

---

## 4. Systemd Service Files

### 4.1 Celery Worker Service

**Datei:** `/etc/systemd/system/birdy-celery-worker.service`

```ini
[Unit]
Description=Birdy Celery Worker (Background Tasks)
After=network.target redis.service

[Service]
Type=forking
User=pi
Group=pi
WorkingDirectory=/home/pi/birdy_project
Environment="PATH=/home/pi/birdy_project/venv/bin"
ExecStart=/home/pi/birdy_project/venv/bin/celery -A birdy_config worker -Q default -l info --logfile=/home/pi/birdy_project/logs/celery_worker.log --detach --pidfile=/tmp/celery_worker.pid
ExecStop=/bin/kill -TERM $MAINPID
PIDFile=/tmp/celery_worker.pid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4.2 Celery Beat Service

**Datei:** `/etc/systemd/system/birdy-celery-beat.service`

```ini
[Unit]
Description=Birdy Celery Beat (Periodic Tasks)
After=network.target redis.service

[Service]
Type=forking
User=pi
Group=pi
WorkingDirectory=/home/pi/birdy_project
Environment="PATH=/home/pi/birdy_project/venv/bin"
ExecStart=/home/pi/birdy_project/venv/bin/celery -A birdy_config beat -l info --logfile=/home/pi/birdy_project/logs/celery_beat.log --detach --pidfile=/tmp/celery_beat.pid
ExecStop=/bin/kill -TERM $MAINPID
PIDFile=/tmp/celery_beat.pid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4.3 Gunicorn Service (Django)

**Datei:** `/etc/systemd/system/birdy-gunicorn.service`

```ini
[Unit]
Description=Birdy Gunicorn (Django WSGI)
After=network.target

[Service]
Type=notify
User=pi
Group=pi
WorkingDirectory=/home/pi/birdy_project
Environment="PATH=/home/pi/birdy_project/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=birdy_config.settings_production"
ExecStart=/home/pi/birdy_project/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --access-logfile /home/pi/birdy_project/logs/gunicorn_access.log \
    --error-logfile /home/pi/birdy_project/logs/gunicorn_error.log \
    birdy_config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4.4 Birdy Detection Service

**Datei:** `/etc/systemd/system/birdy-detection.service`

```ini
[Unit]
Description=Birdy Detection System (PIR + Camera + ML)
After=network.target redis.service birdy-celery-worker.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/birdy_project
Environment="PATH=/home/pi/birdy_project/venv/bin"
ExecStart=/home/pi/birdy_project/venv/bin/python manage.py start_birdy
Restart=always
RestartSec=10
StandardOutput=append:/home/pi/birdy_project/logs/start_birdy.log
StandardError=append:/home/pi/birdy_project/logs/start_birdy.log

[Install]
WantedBy=multi-user.target
```

---

## 5. Nginx Configuration (optional, empfohlen)

**Datei:** `/etc/nginx/sites-available/birdy`

```nginx
upstream birdy_gunicorn {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-raspberry-pi-ip your-domain.com;

    client_max_body_size 100M;

    # Static files
    location /static/ {
        alias /home/pi/birdy_project/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files (Videos, Photos)
    location /media/ {
        alias /home/pi/birdy_project/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Proxy to Gunicorn
    location / {
        proxy_pass http://birdy_gunicorn;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

**Nginx aktivieren:**

```bash
# Symlink erstellen
sudo ln -s /etc/nginx/sites-available/birdy /etc/nginx/sites-enabled/

# Default Site deaktivieren (optional)
sudo rm /etc/nginx/sites-enabled/default

# Nginx testen und neu laden
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl enable nginx
```

---

## 6. Installation & Aktivierung

### Service Files installieren

```bash
# Service Files kopieren
sudo cp ~/birdy_project/systemd/*.service /etc/systemd/system/

# Systemd neu laden
sudo systemctl daemon-reload

# Services aktivieren (Auto-Start beim Boot)
sudo systemctl enable redis-server
sudo systemctl enable birdy-celery-worker
sudo systemctl enable birdy-celery-beat
sudo systemctl enable birdy-gunicorn
sudo systemctl enable birdy-detection
sudo systemctl enable nginx

# Services starten
sudo systemctl start redis-server
sudo systemctl start birdy-celery-worker
sudo systemctl start birdy-celery-beat
sudo systemctl start birdy-gunicorn
sudo systemctl start birdy-detection
sudo systemctl start nginx
```

### Status überprüfen

```bash
# Alle Services prüfen
sudo systemctl status birdy-celery-worker
sudo systemctl status birdy-celery-beat
sudo systemctl status birdy-gunicorn
sudo systemctl status birdy-detection
sudo systemctl status nginx

# Logs anzeigen
sudo journalctl -u birdy-detection -f
sudo journalctl -u birdy-gunicorn -f
tail -f ~/birdy_project/logs/birdy.log
```

---

## 7. Hardware testen

Vor dem Produktiv-Start sollten alle Sensoren getestet werden.

### Vorbereitung

```bash
cd ~/birdy_project
source venv/bin/activate
```

### PIR Bewegungssensor

```bash
# Standard-Test (60 Sekunden, Ctrl+C zum Beenden)
python manage.py test_pir

# Längerer Test
python manage.py test_pir --duration 120
```

Zeigt jede Zustandsänderung (Bewegung erkannt / keine Bewegung) mit Zeitstempel an.

### Kamera

```bash
# Foto + 5s Video aufnehmen
python manage.py test_camera
```

Testdateien werden in `/tmp/birdy_test/` gespeichert.

### Gewichtssensor

```bash
# 10 Messungen mit Kalibrierung
python manage.py test_weight

# Kontinuierliche Messung (Ctrl+C zum Beenden)
python manage.py test_weight --continuous

# Mehr Messungen, schnellerer Intervall
python manage.py test_weight --count 20 --interval 0.5
```

### Gewichtssensor Rohdaten (ohne Filter)

```bash
# 20 Rohdaten-Messungen direkt vom HX711
python manage.py test_weight_raw

# Kontinuierlich
python manage.py test_weight_raw --continuous

# Viele Messungen, schnell
python manage.py test_weight_raw --count 50 --interval 0.2
```

### Waage kalibrieren

```bash
# Interaktive Kalibrierung (Gewicht in Gramm angeben)
python manage.py calibrate_weight --weight 100
```

Ablauf:
1. Waage leer → ENTER → Tare wird gesetzt
2. Bekanntes Gewicht auflegen → ENTER → Kalibrierungsfaktor wird berechnet
3. Kalibrierung wird in `weight_calibration.json` gespeichert

---

## 8. Management Commands

### Services neu starten

```bash
# Einzelne Services
sudo systemctl restart birdy-celery-worker
sudo systemctl restart birdy-celery-beat
sudo systemctl restart birdy-gunicorn
sudo systemctl restart birdy-detection

# Alle Birdy Services
sudo systemctl restart birdy-*
```

### Services stoppen

```bash
# Alle Birdy Services stoppen
sudo systemctl stop birdy-*

# Einzelne Services
sudo systemctl stop birdy-detection
```

### Logs überwachen

```bash
# Live Logs
sudo journalctl -u birdy-detection -f
sudo journalctl -u birdy-gunicorn -f

# Letzte 100 Zeilen
sudo journalctl -u birdy-detection -n 100

# Alle Birdy Services
sudo journalctl -u birdy-* -f
```

---

## 9. Firewall (optional)

```bash
# UFW installieren und konfigurieren
sudo apt-get install -y ufw

# SSH erlauben (WICHTIG!)
sudo ufw allow 22/tcp

# HTTP erlauben
sudo ufw allow 80/tcp

# HTTPS erlauben (falls SSL)
sudo ufw allow 443/tcp

# Firewall aktivieren
sudo ufw enable
sudo ufw status
```

---

## 10. Backup & Wartung

### Datenbank Backup (SQLite)

```bash
# Backup erstellen
cp ~/birdy_project/db.sqlite3 ~/birdy_project/backups/db_$(date +%Y%m%d_%H%M%S).sqlite3

# Automatisches Backup via Cron
crontab -e

# Täglich um 3 Uhr
0 3 * * * cp /home/pi/birdy_project/db.sqlite3 /home/pi/birdy_project/backups/db_$(date +\%Y\%m\%d).sqlite3
```

### Datenbank Backup (PostgreSQL)

```bash
# Backup erstellen
pg_dump -U birdy_user birdy_db > ~/birdy_project/backups/db_$(date +%Y%m%d_%H%M%S).sql

# Automatisches Backup via Cron
0 3 * * * pg_dump -U birdy_user birdy_db > /home/pi/birdy_project/backups/db_$(date +\%Y\%m\%d).sql
```

### Log Rotation

**Datei:** `/etc/logrotate.d/birdy`

```
/home/pi/birdy_project/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 pi pi
    sharedscripts
    postrotate
        systemctl reload birdy-gunicorn > /dev/null 2>&1 || true
    endscript
}
```

---

## 11. Monitoring & Health Checks

### System Status Script

**Datei:** `~/birdy_project/check_status.sh`

```bash
#!/bin/bash
echo "=== Birdy System Status ==="
echo ""

services=("redis-server" "birdy-celery-worker" "birdy-celery-beat" "birdy-gunicorn" "birdy-detection" "nginx")

for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        echo "✓ $service is running"
    else
        echo "✗ $service is NOT running"
    fi
done

echo ""
echo "=== Disk Usage ==="
df -h /home/pi/birdy_project/media

echo ""
echo "=== Memory Usage ==="
free -h

echo ""
echo "=== CPU Temperature ==="
vcgencmd measure_temp
```

```bash
chmod +x ~/birdy_project/check_status.sh
```

---

## 12. Troubleshooting

### Services starten nicht

```bash
# Detaillierte Logs anzeigen
sudo journalctl -xe -u birdy-detection

# Permissions prüfen
ls -la /home/pi/birdy_project/logs/

# Manuell testen
cd ~/birdy_project
source venv/bin/activate
python manage.py start_birdy
```

### Nginx zeigt 502 Bad Gateway

```bash
# Gunicorn läuft?
sudo systemctl status birdy-gunicorn

# Gunicorn Logs prüfen
tail -f ~/birdy_project/logs/gunicorn_error.log

# Nginx Error Log
sudo tail -f /var/log/nginx/error.log
```

### Celery Tasks werden nicht ausgeführt

```bash
# Redis läuft?
redis-cli ping

# Celery Worker Status
sudo systemctl status birdy-celery-worker

# Registrierte Tasks anzeigen
cd ~/birdy_project
source venv/bin/activate
celery -A birdy_config inspect registered
```

---

## 13. Updates & Deployment

```bash
# Code aktualisieren (Git)
cd ~/birdy_project
git pull

# Dependencies aktualisieren
source venv/bin/activate
pip install -r requirements.txt

# Datenbank migrieren
python manage.py migrate

# Static Files aktualisieren
python manage.py collectstatic --noinput

# Services neu starten
sudo systemctl restart birdy-*
```

---

## Zusammenfassung

**Produktiv-Setup Checklist:**

- [ ] PostgreSQL installiert und konfiguriert (optional)
- [ ] Gunicorn installiert
- [ ] Production Settings erstellt (`settings_production.py`)
- [ ] Static Files gesammelt (`collectstatic`)
- [ ] Systemd Service Files erstellt
- [ ] Services aktiviert und gestartet
- [ ] Nginx konfiguriert (optional)
- [ ] Firewall konfiguriert
- [ ] Backup-Strategie eingerichtet
- [ ] Log Rotation konfiguriert
- [ ] Monitoring eingerichtet

**URL nach Installation:**

- Mit Nginx: `http://your-raspberry-pi-ip/`
- Ohne Nginx: `http://your-raspberry-pi-ip:8000/`

**Wichtige Befehle:**

```bash
# Status prüfen
~/birdy_project/check_status.sh

# Services neu starten
sudo systemctl restart birdy-*

# Logs anzeigen
sudo journalctl -u birdy-detection -f
```
