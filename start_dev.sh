#!/bin/bash
# Birdy Development Startup Script - Aktualisiert für neue Architektur
#
# ARCHITEKTUR:
# - Bird Detection läuft SYNCHRON in start_birdy (kein Celery Worker nötig)
# - Celery Worker: Nur für Background Tasks (Sensor Updates, MQTT, Statistiken)
# - Celery Beat: Für periodische Tasks (MQTT Publishing, Backup Sensor Status)

cd ~/birdy_project
source venv/bin/activate

echo "=== Starting Birdy Development Environment ==="
echo ""

# Prüfe Redis
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Starting Redis..."
    sudo systemctl start redis-server
    sleep 2
    echo "✓ Redis started"
else
    echo "✓ Redis already running"
fi

# Starte Celery Worker im Hintergrund (für Background Tasks)
# HINWEIS: Bird Detection läuft NICHT über Celery, nur Sensor/MQTT/Stats Tasks
echo ""
echo "Starting Celery Worker (Background Tasks only)..."
celery -A birdy_config worker \
    -Q default \
    -l info \
    --logfile=logs/celery_worker.log \
    --detach

sleep 2

# Starte Celery Beat im Hintergrund (für periodische Tasks)
echo "Starting Celery Beat (Periodic Tasks)..."
celery -A birdy_config beat \
    -l info \
    --logfile=logs/celery_beat.log \
    --detach

sleep 2

echo ""
echo "=== Background Services Started ==="
echo "✓ Redis"
echo "✓ Celery Worker (Background Tasks)"
echo "✓ Celery Beat (Periodic Tasks)"
echo ""

# Starte Django Development Server im Hintergrund
echo "Starting Django Development Server..."
python manage.py runserver 0.0.0.0:8000 >> logs/django.log 2>&1 &
DJANGO_PID=$!
sleep 2
echo "✓ Django running on http://0.0.0.0:8000 (PID: $DJANGO_PID)"

echo ""
echo "=== Starting Birdy Detection System ==="
echo "(Bird Detection runs synchronously in this process)"
echo ""

# Starte Birdy Detection System
# WICHTIG: Dies blockiert - Detection läuft in diesem Prozess
python manage.py start_birdy

# Cleanup beim Beenden (wird ausgeführt wenn start_birdy mit Ctrl+C beendet wird)
echo ""
echo "=== Shutting down ==="
echo "Stopping Django..."
pkill -f "manage.py runserver"
echo "Stopping Celery processes..."
pkill -f "celery.*worker"
pkill -f "celery.*beat"
echo "✓ Django stopped"
echo "✓ Celery stopped"
echo "✓ Birdy stopped"
