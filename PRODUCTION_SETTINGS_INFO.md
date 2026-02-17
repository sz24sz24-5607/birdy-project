# Production Settings - Wichtige Hinweise

## Erstellte Datei

**birdy_config/settings_production.py** wurde erstellt für Production-Deployment.

## Wichtige Unterschiede zu Development Settings

### Development (settings.py)
- `DEBUG = True` - Zeigt detaillierte Fehler
- `ALLOWED_HOSTS = ['*']` - Akzeptiert alle Hosts
- Console Logging auf DEBUG-Level
- CORS erlaubt alle Origins

### Production (settings_production.py)
- `DEBUG = False` - Keine Fehlerdetails an User
- `ALLOWED_HOSTS` restriktiv - nur definierte Hosts
- Logging auf INFO-Level, separate Error-Logs
- CORS restriktiv - nur erlaubte Origins
- WhiteNoise für Static Files
- Security Headers aktiviert

## ⚠️ VOR Production-Deployment ÄNDERN:

### 1. SECRET_KEY setzen

**WICHTIG:** Generiere einen sicheren SECRET_KEY!

```bash
# SECRET_KEY generieren:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Dann als Umgebungsvariable setzen:
export DJANGO_SECRET_KEY='your-generated-key-here'

# Oder in /etc/environment eintragen für Persistence:
echo 'DJANGO_SECRET_KEY="your-generated-key-here"' | sudo tee -a /etc/environment
```

### 2. ALLOWED_HOSTS anpassen

Editiere `birdy_config/settings_production.py` Zeile 16-23:

```python
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'raspberrypi',
    'raspberrypi.local',
    '192.168.178.XX',  # Deine Raspberry Pi IP-Adresse
    # 'birdy.example.com',  # Optional: Deine Domain
]
```

### 3. HTTPS aktivieren (optional)

Wenn du HTTPS nutzt, ändere in `settings_production.py`:

```python
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
```

### 4. CORS Origins anpassen

Falls du API von externen Clients nutzt, passe CORS_ALLOWED_ORIGINS an.

## Verwendung

### Development (lokal testen)
```bash
./start_dev.sh
# Nutzt automatisch settings.py (DEBUG=True)
```

### Production (systemd Services)
```bash
# Services nutzen automatisch settings_production.py
sudo systemctl start birdy-gunicorn
sudo systemctl start birdy-celery-worker
sudo systemctl start birdy-celery-beat
sudo systemctl start birdy-detection
```

## Systemd Services Status

Alle Service-Dateien sind jetzt korrekt konfiguriert:

✅ **birdy-gunicorn.service** - Nutzt settings_production.py
✅ **birdy-celery-worker.service** - Korrekte Queue Konfiguration
✅ **birdy-celery-beat.service** - Periodische Tasks
✅ **birdy-detection.service** - Bird Detection System

## Static Files für Production

```bash
# Sammle Static Files vor Production-Start:
python manage.py collectstatic --noinput --settings=birdy_config.settings_production
```

WhiteNoise serviert dann die Static Files effizient über Gunicorn.

## Logging

Production Logs werden geschrieben nach:
- `logs/birdy.log` - Alle INFO+ Messages
- `logs/birdy_error.log` - Nur ERROR+ Messages
- `logs/gunicorn_access.log` - HTTP Requests
- `logs/gunicorn_error.log` - Gunicorn Errors

## Test Production Settings lokal

```bash
# Mit Production Settings testen:
source venv/bin/activate
DJANGO_SETTINGS_MODULE=birdy_config.settings_production python manage.py check --deploy

# Gunicorn lokal testen:
DJANGO_SETTINGS_MODULE=birdy_config.settings_production gunicorn birdy_config.wsgi:application
```

## Nächste Schritte für Production

1. ✅ SECRET_KEY generieren und setzen
2. ✅ ALLOWED_HOSTS anpassen
3. ⏳ Static Files sammeln (`collectstatic`)
4. ⏳ Systemd Services installieren (siehe PRODUCTION_SETUP.md)
5. ⏳ Services starten und testen
