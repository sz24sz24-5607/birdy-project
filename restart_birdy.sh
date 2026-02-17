#!/bin/bash
# Birdy System Neustart Script - Aktualisiert für neue Architektur
#
# ARCHITEKTUR:
# - Bird Detection läuft SYNCHRON in start_birdy (kein Celery Worker nötig)
# - Celery Worker: Nur für Background Tasks (Sensor Updates, MQTT, Statistiken)
# - Celery Beat: Für periodische Tasks (MQTT Publishing, Backup Sensor Status)

echo "=== Stopping Birdy System ==="

# Stoppe start_birdy Prozess
echo "Stopping start_birdy..."
pkill -f "manage.py start_birdy"
sleep 2

# Stoppe Celery Worker
echo "Stopping Celery Worker..."
pkill -f "celery.*worker"
sleep 1

# Stoppe Celery Beat
echo "Stopping Celery Beat..."
pkill -f "celery.*beat"
sleep 1

echo "All processes stopped."
echo ""
echo "=== Starting Birdy System ==="

# Wechsle ins Projektverzeichnis
cd /home/pi/birdy_project

# Aktiviere Virtual Environment
source venv/bin/activate

# Prüfe Redis
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Starting Redis..."
    sudo systemctl start redis-server
    sleep 2
    echo "✓ Redis started"
else
    echo "✓ Redis already running"
fi

# Starte Celery Beat im Hintergrund
echo "Starting Celery Beat (Periodic Tasks)..."
celery -A birdy_config beat -l info --logfile=logs/celery_beat.log --detach
sleep 2

# Starte Celery Worker im Hintergrund (nur für Background Tasks)
# HINWEIS: Bird Detection läuft NICHT über Celery, nur Sensor/MQTT/Stats Tasks
echo "Starting Celery Worker (Background Tasks only)..."
celery -A birdy_config worker -Q default -l info --logfile=logs/celery_worker.log --detach
sleep 2

# Starte Django Development Server im Hintergrund
echo "Starting Django Development Server..."
python manage.py runserver 0.0.0.0:8000 >> logs/django.log 2>&1 &
sleep 2

# Starte start_birdy im Hintergrund
echo "Starting Birdy Detection System..."
echo "(Bird Detection runs synchronously in this process)"
python manage.py start_birdy >> logs/start_birdy.log 2>&1 &
sleep 2

echo ""
echo "=== Birdy System Started ==="
echo "✓ Redis"
echo "✓ Celery Worker (Background Tasks)"
echo "✓ Celery Beat (Periodic Tasks)"
echo "✓ Django Development Server (http://0.0.0.0:8000)"
echo "✓ Birdy Detection System"
echo ""
echo "Check logs:"
echo "  tail -f logs/birdy.log"
echo "  tail -f logs/start_birdy.log"
echo "  tail -f logs/celery_worker.log"
echo "  tail -f logs/celery_beat.log"
echo "  tail -f logs/django.log"
echo ""
echo "To stop the system, run: ./stop_dev.sh"
