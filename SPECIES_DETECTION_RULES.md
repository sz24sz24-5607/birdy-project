# Spezies-Detektion Regeln

## Gültige Besuche

Ein Detection Event wird nur dann als **gültiger Besuch** gezählt, wenn:

1. **Confidence >= 50%** (`MIN_CONFIDENCE_SPECIES` in settings.py)
2. **Spezies ist NICHT "background"** (letzte Zeile in labels.txt)
3. **Spezies ist im Swiss Mittelland Allowlist** (`ml_models/swiss_midland_allowlist.txt`)

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

## Swiss Mittelland Regionaler Filter

Das verwendete ML-Modell (iNaturalist) kennt ~964 Vogelarten weltweit. Ohne Filter wurden
regelmässig unplausible Arten erkannt, z.B. **Rotkardinal** (Nordamerika), **Mönchssittich**
(Südamerika) oder **Rosakakadu** (Australien).

### Funktionsweise

Beim Start lädt der Classifier die Datei `ml_models/swiss_midland_allowlist.txt` mit
wissenschaftlichen Namen der im Schweizer Mittelland vorkommenden Arten. Nur diese Arten
werden bei der Klassifikation berücksichtigt. Der **höchste Score unter den erlaubten Arten**
gewinnt. `background` ist immer erlaubt, damit Nicht-Vogel-Frames korrekt erkannt werden.

```
Log-Meldung beim Start:
  Swiss Mittelland filter active: 152 allowed classes (151 species + background)
```

### Allowlist verwalten

Die Datei `ml_models/swiss_midland_allowlist.txt` enthält wissenschaftliche Namen
(eine Art pro Zeile, `#`-Zeilen werden ignoriert):

```
# Finken / Finches
Fringilla coelebs
Chloris chloris
Carduelis carduelis
...
```

**Arten hinzufügen/entfernen:** Datei editieren, dann `birdy-detection` neu starten.

### Erlaubte Artengruppen (151 Arten)

| Gruppe | Beispiele |
|---|---|
| Singvögel | Rotkehlchen, Amsel, Meisen, Finken, Ammern, Spatzen, Stelzen |
| Schwalben / Segler | Rauchschwalbe, Mehlschwalbe, Mauersegler |
| Spechte | Buntspecht, Grünspecht |
| Tauben | Ringeltaube, Türkentaube, Straßentaube |
| Eulen | Schleiereule, Steinkauz, Waldohreule |
| Greifvögel | Bussard, Turmfalke, Sperber, Rotmilan |
| Rabenvögel | Amsel, Elster, Eichelhäher, Dohle, Saatkrähe |
| Wasservögel | Stockente, Blässhuhn, Graureiher, Kormoran |
| Schwäne & Gänse | Höckerschwan, Graugans, Nilgans |
| Limikolen | Kiebitz, Bekassine, Flussuferläufer |

### Beispiel aus den Logs (27. Feb 2026)

**Ohne Filter: Mönchssittich gespeichert (falsch)**
```
Frame 2: Haussperling    82%   ← wäre korrekt
Frame 7: Mönchssittich  136%   ← gewann, weil global höchster Score
→ Detection saved: Mönchssittich  ✗
```

**Mit Filter: Haussperling gespeichert (korrekt)**
```
Frame 2: Haussperling    82%   ← höchster Score unter Schweizer Arten
Frame 7: Mönchssittich  136%   ← gefiltert (nicht in Allowlist)
→ Detection saved: Haussperling  ✓
```

**Mit Filter: Falsch-Positiv verhindert**
```
Frame 5: Schwarzkopfmeise  61%  ← gefiltert (nordamerikanisch)
Frame 3: Kohlmeise         40%  ← Schweizer Kandidat, aber 40% < 50%
→ Not a valid visit          ✓
```

## Implementierung

### 1. Detection Workflow (`services/bird_detection.py`)

Statt einem einzelnen Frame werden **8 Frames gleichmässig** aus dem 4s-Video extrahiert
und jeder klassifiziert. Der Frame mit der höchsten Konfidenz (kein Background) gewinnt:

```python
# Alle 8 Frames klassifizieren
for frame_path in candidate_frames:
    result = classifier.classify(frame_path, top_k=5)
    if not is_background and confidence > best_confidence:
        best_confidence = confidence
        best_frame = frame_path

# Bestes Frame bewerten
if best_frame is not None and best_confidence >= min_confidence:
    is_valid_visit = True
    species = BirdSpecies.objects.get_or_create(...)
```

**Ergebnis:**
- Kein gültiger Frame → Video und Temp-Frames werden gelöscht, **kein DB-Eintrag**
- Gültiger Frame → bestes Frame wird als Photo gespeichert, DB-Einträge werden erstellt

### 2. Statistiken (`species/models.py`)

```python
# Nur bei gültigen Besuchen (species != None)
if species:
    DailyStatistics.update_for_date(timestamp.date(), species)
```

**Ergebnis:** Nur Besuche mit gültiger Spezies landen in den Statistiken. Ungültige Detections werden gar nicht erst in die DB geschrieben.

### 3. Visit Counts (MQTT, Dashboard)

```python
# homeassistant/tasks.py und homeassistant/mqtt_client.py
total_visits = BirdDetection.objects.filter(
    timestamp__date=today,
    processed=True,
    species__isnull=False  # NUR gültige Besuche
).count()
```

**Ergebnis:** Visit Counter zeigt nur gültige Besuche an. Da ungültige Detections nie in der DB landen, wird hier nur über tatsächliche BirdDetection-Einträge gezählt.

## Beispiele

### Beispiel 1: Hohe Confidence, echte Spezies
- **Bestes Frame:** "Parus major" mit 85% Confidence (Frame 3 von 8)
- **Gültiger Besuch?** ✅ JA
- **Log:** `Best frame: frame_03.jpg → Parus major (85.0%) [512ms total]`
- **Ergebnis:** Bestes Frame gespeichert, Spezies in DB, Statistik aktualisiert

### Beispiel 2: Niedrige Confidence über alle Frames
- **Bestes Frame:** "Parus major" mit 35% Confidence
- **Gültiger Besuch?** ❌ NEIN
- **Grund:** 35% < 50% (kein Frame erreicht Schwellwert)
- **Log:** `Not a valid visit: best confidence too low (35.0% < 50.0%)`
- **Ergebnis:** Video gelöscht, kein DB-Eintrag

### Beispiel 3: Alle Frames = Background
- **Bestes Frame:** alle Frames als "background" klassifiziert
- **Gültiger Besuch?** ❌ NEIN
- **Grund:** "background" wird immer übersprungen
- **Log:** `Not a valid visit: no valid (non-background) frame found`
- **Ergebnis:** Video gelöscht, kein DB-Eintrag

### Beispiel 4: Grenzfall
- **Bestes Frame:** "Parus major" mit 50% Confidence
- **Gültiger Besuch?** ✅ JA
- **Grund:** 50% >= 50% UND nicht "background"
- **Ergebnis:** Bestes Frame gespeichert, Statistik aktualisiert

## Auswirkungen auf Daten

### Was wird gespeichert?

**Nur bei gültigen Besuchen** (confidence >= 50%, kein background):
- Video (MP4) auf USB-Storage
- Bestes Frame (JPG) auf USB-Storage
- `Video`-, `Photo`-, `BirdDetection`-DB-Einträge
- `BirdDetection.species` gesetzt
- Eintrag in `DailyStatistics`
- Zählt in Visit Counters (Dashboard, MQTT)

**Bei ungültigen Detections** (background, zu niedrige Konfidenz):
- Video und Temp-Frames werden sofort gelöscht
- **Kein DB-Eintrag** wird erstellt

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

### Problem: Art in den Logs erkannt aber nicht gespeichert

**Ursache:** Art ist nicht im Swiss Mittelland Allowlist

**Prüfen:**
```bash
grep "Swiss Mittelland" /home/pi/birdy_project/logs/birdy.log | tail -1
# Swiss Mittelland filter active: 152 allowed classes (151 species + background)
```

**Lösung:** Wissenschaftlichen Namen in `ml_models/swiss_midland_allowlist.txt` eintragen,
dann `sudo systemctl restart birdy-detection`.

### Problem: Filter lädt nicht (labels_en.txt fehlt)

**Ursache:** `labels_en.txt` fehlt im `ml_models/`-Ordner

**Lösung:** Ohne `labels_en.txt` kann kein Mapping von wissenschaftlichen Namen zu Model-Indices
aufgebaut werden → Filter wird deaktiviert (alle Arten erlaubt, Warning im Log).

## Zusammenfassung

**Gültige Besuche = bestes Frame aus 8 Kandidaten erfüllt alle drei Bedingungen:**
1. Confidence >= 50%
2. Kein "background"
3. Art ist im Swiss Mittelland Allowlist (`ml_models/swiss_midland_allowlist.txt`)

Ungültige Detections werden **nicht** in die DB gespeichert:
- ❌ Kein DB-Eintrag
- ❌ Kein Video gespeichert
- ❌ Kein Foto gespeichert
- ❌ Keine Statistik
- ❌ Keine MQTT-Benachrichtigung
