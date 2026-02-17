# Kamera-Architektur - Wichtige Hinweise

## Problem: Kamera-Zugriff über Prozessgrenzen

### Ursprüngliches Design (NICHT FUNKTIONSFÄHIG)
1. `start_birdy` initialisiert Kamera
2. PIR Motion Event triggert → `process_bird_detection.delay()` (Celery Task)
3. Celery Worker führt Task aus → **FEHLER**: Kamera nicht verfügbar!

### Warum das nicht funktioniert
- **Singleton funktioniert nur pro Prozess**: `_camera_worker_instance` ist in jedem Python-Prozess separate Variable
- **start_birdy Prozess**: Hat Camera Worker mit Kamera-Zugriff
- **Celery Worker Prozess**: Erstellt NEUEN Camera Worker ohne Kamera-Zugriff
- **Fehler**: `Camera not initialized (should be initialized by start_birdy)`

## Aktuelle Lösung: Synchrone Verarbeitung

### Architektur
1. `start_birdy` initialisiert Kamera
2. PIR Motion Event triggert → `detection_service.process_detection()` **synchron**
3. Verarbeitung läuft im **gleichen Prozess** wie start_birdy
4. Kamera ist verfügbar ✓

### Code-Änderung
In `services/bird_detection.py`:
```python
def handle_motion_detected(self, pir_event):
    # WICHTIG: Führe Detection synchron aus (in start_birdy Prozess)
    # Grund: Kamera läuft nur in diesem Prozess, Celery Worker hat keinen Zugriff
    # Da nur 1 Kamera existiert, können sowieso keine parallelen Detections laufen
    self.process_detection(pir_event.id)
```

### Vorteile
- ✓ Kamera-Zugriff funktioniert
- ✓ Keine Prozess-Kommunikation nötig
- ✓ Einfacher, weniger Fehlerquellen
- ✓ Passt zur Hardware-Einschränkung (nur 1 Kamera)

### Nachteile
- PIR Detection Loop blockiert während Verarbeitung (ca. 10-15 Sekunden)
- Kein anderer Motion Event während dieser Zeit

**Ist das ein Problem?**
NEIN, weil:
1. Nur 1 Kamera → kann sowieso nicht 2 Videos gleichzeitig aufnehmen
2. Verarbeitung ist relativ schnell (10-15 Sekunden)
3. Vögel bleiben normalerweise länger am Futterhaus

## Celery Task Status

Der Celery Task `process_bird_detection` existiert noch, wird aber **NICHT verwendet**:
```python
@shared_task
def process_bird_detection(pir_event_id):
    """
    HINWEIS: Dieser Task wird aktuell NICHT verwendet!
    Grund: Kamera läuft nur in start_birdy Prozess, Celery Worker hat keinen Zugriff.
    """
    logger.warning("process_bird_detection task called - but detection should run in start_birdy!")
    pass
```

Der Task bleibt für potenzielle zukünftige Verwendung (z.B. Re-Processing von bereits aufgenommenen Videos).

## Celery Worker Konfiguration

Die `bird_detection` Queue-Konfiguration bleibt bestehen:
- `celery.py`: Task-Routing für `services.bird_detection.process_bird_detection`
- `settings.py`: Queue-Definition mit `bird_detection` und `default`

**Diese Konfiguration schadet nicht**, sie ist einfach inaktiv, da der Task nicht aufgerufen wird.

## Alternative Lösungen (NICHT implementiert)

### Option 1: Shared Camera Service via IPC
- Camera Worker als eigenständiger Service (z.B. Socket/Redis)
- Alle Prozesse kommunizieren über IPC
- **Zu komplex** für dieses Projekt

### Option 2: Video-Aufnahme und Processing trennen
- start_birdy: Nur Video aufnehmen, in DB speichern
- Celery Task: Nur Frame-Extraktion + Classification
- **Problem**: Erfordert Umstrukturierung, mehr Arbeit

### Option 3: Multiprocessing Queue/Pipe
- Camera Worker teilt Queue mit Celery Worker
- **Problem**: Celery und start_birdy sind separate Prozess-Bäume

## Was zu tun ist

### Beim Starten des Systems
```bash
# 1. Redis
redis-server &

# 2. Django
python manage.py runserver &

# 3. Celery Worker (für Sensoren, MQTT, Statistiken)
celery -A birdy_config worker -Q default --loglevel=info &

# 4. Celery Beat
celery -A birdy_config beat --loglevel=info &

# 5. start_birdy (PIR + Camera + Detection)
python manage.py start_birdy
```

**WICHTIG**: Du brauchst **KEINEN** separaten Worker für die `bird_detection` Queue, da diese nicht verwendet wird!

### Bei Debugging
Wenn du Fehler wie `Camera not initialized` siehst:
1. Prüfe ob start_birdy läuft
2. Prüfe ob Kamera in start_birdy initialisiert wurde
3. Prüfe ob `handle_motion_detected()` synchron aufruft (nicht `.delay()`)

## Zusammenfassung

**Bird Detection läuft synchron in start_birdy, NICHT als Celery Task.**

Dies ist die richtige Lösung für ein System mit:
- Einer einzelnen Kamera
- Hardware, die nur von einem Prozess gesteuert werden kann
- Sequentielle Verarbeitung (ein Vogel zur Zeit)

Die Celery Queue-Konfiguration bleibt für potenzielle zukünftige Erweiterungen bestehen.
