# PWA Setup - Birdy auf Android Homescreen

## ✅ Was wurde erstellt?

### 1. PWA Manifest (`static/manifest.json`)
- Definiert App-Name, Icons, Farben
- Ermöglicht "Add to Homescreen" auf Android/iOS

### 2. App Icons (10 Stück in `static/icons/`)
- **Roter Vogel** auf lila-blauem Hintergrund (#667eea)
- Verschiedene Größen für alle Devices:
  - 72x72, 96x96, 128x128, 144x144, 152x152
  - 192x192, 384x384, 512x512 (Android)
  - 180x180 (apple-touch-icon für iOS)
  - 32x32 (favicon)

### 3. Aktualisiertes Template (`templates/base.html`)
- PWA Manifest Link
- Favicon Links
- Apple Touch Icon
- Theme Color Meta-Tags
- SEO Description

## 🚀 Nächste Schritte

### Development (sofort testen):

```bash
# Static Files sammeln
python manage.py collectstatic --noinput

# Django Server neu starten
./stop_dev.sh
./start_dev.sh
```

### Production:

```bash
# Static Files sammeln
python manage.py collectstatic --noinput --settings=birdy_config.settings_production

# Gunicorn neu starten
sudo systemctl restart birdy-gunicorn
```

## 📱 Auf Android installieren

### Chrome/Edge (Android):

1. Öffne Birdy-Website auf dem Handy
2. Tippe auf **⋮ (Menü)** → **"Zum Startbildschirm hinzufügen"**
3. Bestätige den App-Namen "Birdy"
4. ✅ Rotes Vogel-Icon erscheint auf dem Homescreen!

### Safari (iOS):

1. Öffne Birdy-Website auf dem iPhone
2. Tippe auf **Teilen-Symbol** (Pfeil nach oben)
3. Scroll zu **"Zum Home-Bildschirm"**
4. Bestätige
5. ✅ Icon erscheint auf dem Homescreen!

## 🎨 Icons anpassen

Falls du das Icon-Design ändern möchtest:

```bash
# Icons neu generieren:
python generate_icons.py

# Static Files neu sammeln:
python manage.py collectstatic --noinput
```

Das `generate_icons.py` Script erstellt einen **roten Vogel** auf lila-blauem Hintergrund.

### Farben ändern:

Editiere `generate_icons.py`:
```python
BACKGROUND_COLOR = "#667eea"  # Header-Farbe (lila-blau)
BIRD_COLOR = "#ff4444"        # Vogel-Farbe (rot)
```

## 🔍 Testen

### PWA Manifest testen:

1. Chrome DevTools öffnen (F12)
2. **Application** Tab
3. **Manifest** → Prüfe ob alle Icons geladen werden
4. **Service Workers** → (optional für Offline-Support)

### Icons testen:

Besuche im Browser:
- http://raspberrypi.local:8000/static/manifest.json
- http://raspberrypi.local:8000/static/favicon.ico
- http://raspberrypi.local:8000/static/icons/icon-192x192.png

## 📝 Technische Details

### PWA Eigenschaften:

- **Display:** Standalone (Fullscreen ohne Browser-UI)
- **Orientation:** Portrait (Hochformat)
- **Theme Color:** #667eea (Lila-Blau)
- **Background Color:** #667eea
- **Icons:** Purpose "any maskable" (funktioniert überall)

### Unterstützte Plattformen:

✅ **Android** (Chrome, Edge, Samsung Internet, Firefox)
✅ **iOS** (Safari 11.3+)
✅ **Desktop** (Chrome, Edge)

## 🐛 Troubleshooting

### Icon wird nicht angezeigt auf Android:

1. Prüfe ob `collectstatic` ausgeführt wurde
2. Leere Browser-Cache
3. Prüfe ob manifest.json korrekt geladen wird (DevTools)
4. Prüfe ALLOWED_HOSTS in Production Settings

### Icon hat falsche Farbe:

1. Regeneriere Icons: `python generate_icons.py`
2. Sammle Static Files: `python manage.py collectstatic --noinput`
3. Hard-Refresh im Browser (Ctrl+Shift+R)

### "Add to Homescreen" Option fehlt:

- Chrome/Android: Manifest muss korrekt geladen werden
- iOS/Safari: Nur über Teilen-Menü möglich (kein automatischer Banner)
- HTTPS erforderlich (außer localhost/192.168.x.x)

## ✨ Weitere PWA Features (optional)

Falls du später Offline-Support willst:

1. Service Worker erstellen (`static/sw.js`)
2. In base.html registrieren:
   ```javascript
   <script>
   if ('serviceWorker' in navigator) {
     navigator.serviceWorker.register('/static/sw.js');
   }
   </script>
   ```

3. Cache-Strategie implementieren (Offline-Zugriff auf Bilder/API)

## 🎯 Ergebnis

Nach dem Setup hast du:

✅ Birdy App-Icon mit rotem Vogel auf Android/iOS Homescreen
✅ Fullscreen-Modus beim Start vom Homescreen
✅ Native App-ähnliches Feeling
✅ Theme-Farbe passt zum Design (#667eea)

Viel Spaß mit der Birdy PWA! 🐦
