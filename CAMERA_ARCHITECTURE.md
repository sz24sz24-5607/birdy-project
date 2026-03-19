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

## Aktuelle Lösung: Thread-basierte Verarbeitung mit Recording Lock

### Architektur
1. `start_birdy` initialisiert Kamera, PIR-Sensor und Detection Service
2. PIR Motion Event triggert → `detection_service.handle_motion_detected(pir_event)`
3. `handle_motion_detected()` prüft `_recording_lock`: falls gesperrt → PIR-Trigger ignorieren
4. Falls frei → **Detection-Thread starten** (daemon=False, läuft bis zum Ende)
5. Verarbeitung läuft im **gleichen Prozess** wie start_birdy → Kamera verfügbar ✓
6. Thread belegt `_recording_lock` für gesamte Aufnahme + Klassifikation

### Code
In `services/bird_detection.py`:
```python
def handle_motion_detected(self, pir_event):
    # Wenn gerade eine Aufnahme läuft: PIR-Trigger ignorieren
    if self._recording_lock.locked():
        logger.debug("Recording already in progress – PIR trigger ignored")
        return

    # Detection in separatem Thread (PIR-Monitoring blockiert nicht)
    detection_thread = threading.Thread(
        target=self.process_detection,
        args=(pir_event.id,),
        daemon=False,
        name=f"BirdDetection-{pir_event.id}"
    )
    detection_thread.start()
```

### Vorteile
- ✓ Kamera-Zugriff funktioniert
- ✓ PIR-Monitoring wird während der Aufnahme **nicht blockiert**
- ✓ `_recording_lock` verhindert parallele Aufnahmen sauber
- ✓ Neue PIR-Trigger während laufender Aufnahme werden ignoriert
- ✓ Passt zur Hardware-Einschränkung (nur 1 Kamera)

### Dynamische Aufnahmedauer

Statt fixer 4s nutzt `record_video_dynamic()` den PIR-Status:
- Startet rpicam-vid als Hintergrundprozess (`subprocess.Popen`)
- Überwacht PIR alle 200ms: PIR LOW für ≥ `PIR_ABSENCE_THRESHOLD_SECONDS` (3s) → Aufnahme stoppen
- Sicherheitsnetz: max. `MAX_RECORDING_DURATION_SECONDS` (30s)
- Gibt `(mp4_path, actual_duration_seconds)` zurück

### Recording Lock Flow

```
PIR HIGH → handle_motion_detected()
  → _recording_lock.locked()? → TRUE  → Trigger ignoriert (Aufnahme läuft bereits)
                               → FALSE → Detection-Thread starten

Detection-Thread:
  with _recording_lock:          ← Lock belegen
    record_video_dynamic()       ← PIR überwachen, dynamisch stoppen (bis 30s)
    extract_candidate_frames()   ← Proportional (2fps, min 8 Frames)
    BirdSizeDetector filter      ← Frames ohne vollständigen Vogel verwerfen
    Alle Frames klassifizieren   ← Bestes Frame wählen
    BirdDetection speichern      ← is_new_visit Deduplication
                                 ← Lock freigeben → bereit für nächsten Besuch
```

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
3. Prüfe ob `handle_motion_detected()` den Detection-Thread startet (nicht `.delay()`)

## Zusammenfassung

**Bird Detection läuft in einem Thread im start_birdy-Prozess, NICHT als Celery Task.**

- `_recording_lock` verhindert parallele Aufnahmen
- `record_video_dynamic()` nimmt auf solange der Vogel da ist (PIR-basiert, max. 30s)
- PIR-Monitoring wird während der Aufnahme nicht blockiert
- Sequentielle Verarbeitung (ein Vogel zur Zeit) ist korrekt für eine einzelne Kamera

Die Celery Queue-Konfiguration bleibt für potenzielle zukünftige Erweiterungen bestehen.
