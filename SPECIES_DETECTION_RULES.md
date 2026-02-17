# Spezies-Detektion Regeln

## Gültige Besuche

Ein Detection Event wird nur dann als **gültiger Besuch** gezählt, wenn:

1. **Confidence >= 50%** (`MIN_CONFIDENCE_SPECIES` in settings.py)
2. **Spezies ist NICHT "background"** (letzte Zeile in labels.txt)

## Konfiguration

In `birdy_config/settings.py`:

```python
BIRDY_SETTINGS = {
    ...
    'MIN_CONFIDENCE_THRESHOLD': 0.7,      # Schwellwert für Classifier (70%)
    'MIN_CONFIDENCE_SPECIES': 0.5,        # Minimum für gültigen Besuch (50%)
    ...
}
```

### Parameter-Erklärung:

- **`MIN_CONFIDENCE_THRESHOLD`** (70%): Interner Classifier-Schwellwert, wird von `is_confident_detection()` genutzt
- **`MIN_CONFIDENCE_SPECIES`** (50%): Schwellwert für gültige Besuche - bestimmt ob eine Detection als Besuch zählt

## Implementierung

### 1. Detection Workflow (`services/bird_detection.py`)

```python
if confidence >= min_confidence and not is_background:
    is_valid_visit = True
    # Spezies wird erstellt und gespeichert
    species = BirdSpecies.objects.get_or_create(...)
else:
    # Kein gültiger Besuch
    species = None
```

**Ergebnis:**
- `BirdDetection.species = None` → kein gültiger Besuch
- `BirdDetection.species = <Spezies>` → gültiger Besuch

### 2. Statistiken (`species/models.py`)

```python
# Nur bei gültigen Besuchen (species != None)
if species:
    DailyStatistics.update_for_date(timestamp.date(), species)
```

**Ergebnis:** Nur Besuche mit gültiger Spezies landen in den Statistiken

### 3. Visit Counts (MQTT, Dashboard)

```python
# homeassistant/tasks.py und homeassistant/mqtt_client.py
total_visits = BirdDetection.objects.filter(
    timestamp__date=today,
    processed=True,
    species__isnull=False  # NUR gültige Besuche
).count()
```

**Ergebnis:** Visit Counter zeigt nur gültige Besuche an

## Beispiele

### Beispiel 1: Hohe Confidence, echte Spezies
- **Klassifizierung:** "Parus major" mit 85% Confidence
- **Gültiger Besuch?** ✅ JA
- **Grund:** 85% >= 50% UND nicht "background"
- **Ergebnis:** Spezies gespeichert, Statistik aktualisiert

### Beispiel 2: Niedrige Confidence
- **Klassifizierung:** "Parus major" mit 35% Confidence
- **Gültiger Besuch?** ❌ NEIN
- **Grund:** 35% < 50%
- **Ergebnis:** `species = None`, keine Statistik
- **Log:** `Not a valid visit: confidence too low (35.0% < 50.0%)`

### Beispiel 3: Background erkannt
- **Klassifizierung:** "background" mit 92% Confidence
- **Gültiger Besuch?** ❌ NEIN
- **Grund:** "background" ist keine echte Spezies
- **Ergebnis:** `species = None`, keine Statistik
- **Log:** `Not a valid visit: background detected`

### Beispiel 4: Grenzfall
- **Klassifizierung:** "Parus major" mit 50% Confidence
- **Gültiger Besuch?** ✅ JA
- **Grund:** 50% >= 50% UND nicht "background"
- **Ergebnis:** Spezies gespeichert, Statistik aktualisiert

## Auswirkungen auf Daten

### Was wird gespeichert?

**Immer gespeichert (in `BirdDetection`):**
- Alle Motion Events mit Video und Foto
- Klassifizierungs-Ergebnisse (confidence, top_k_predictions)
- Timestamp, PIR Event, etc.

**Nur bei gültigen Besuchen:**
- `BirdDetection.species` ist gesetzt (nicht None)
- Eintrag in `DailyStatistics`
- Zählt in Visit Counters (Dashboard, MQTT)

### Datenbank Queries für Analyse

```python
# Alle Detections (auch ungültige)
all_detections = BirdDetection.objects.filter(processed=True)

# Nur gültige Besuche
valid_visits = BirdDetection.objects.filter(
    processed=True,
    species__isnull=False
)

# Ungültige Detections (background oder low confidence)
invalid_detections = BirdDetection.objects.filter(
    processed=True,
    species__isnull=True
)

# Confidence-Verteilung analysieren
from django.db.models import Avg, Count
BirdDetection.objects.values('species__isnull').annotate(
    avg_conf=Avg('confidence'),
    count=Count('id')
)
```

## Anpassung der Schwellwerte

Um den Schwellwert zu ändern, editiere `birdy_config/settings.py`:

```python
'MIN_CONFIDENCE_SPECIES': 0.6,  # Erhöhe auf 60%
```

**Nach Änderung:**
1. Starte `start_birdy` neu
2. Neue Detections nutzen den neuen Schwellwert
3. Alte Detections bleiben unverändert (bereits in DB)

## Troubleshooting

### Problem: Zu viele ungültige Detections

**Ursache:** Background wird häufig erkannt (z.B. bei schlechtem Licht)

**Lösung:**
- Verbessere Beleuchtung am Futterhaus
- Positioniere Kamera besser
- Oder: Erhöhe `MIN_CONFIDENCE_SPECIES` auf 60-70%

### Problem: Zu wenige Besuche

**Ursache:** Schwellwert zu hoch, echte Vögel werden nicht gezählt

**Lösung:**
- Senke `MIN_CONFIDENCE_SPECIES` auf 40%
- Prüfe ungültige Detections:
  ```python
  BirdDetection.objects.filter(
      species__isnull=True,
      confidence__gte=0.4
  ).order_by('-confidence')
  ```

### Problem: Background wird als Spezies gezählt

**Ursache:** Code-Bug oder labels.txt hat "background" nicht als letzte Zeile

**Lösung:**
- Prüfe `ml_models/labels.txt` - letzte Zeile muss "background" sein
- Prüfe Code in `services/bird_detection.py` Zeile 158:
  ```python
  is_background = species_label.lower() == 'background'
  ```

## Zusammenfassung

**Gültige Besuche = Confidence >= 50% UND Spezies != "background"**

Alle anderen Detections werden zwar gespeichert (für Debugging), aber:
- ❌ Nicht in Statistiken
- ❌ Nicht in Visit Counters
- ❌ Nicht in Top Species Listen
