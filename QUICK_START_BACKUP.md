# Git + NAS Backup - Quick Start

## Sofort loslegen (3 Schritte)

### Schritt 1: NAS einrichten (einmalig)

**Sie brauchen:**
- NAS IP-Adresse
- NAS Share-Name (z.B. "birdy_backup")
- Ggf. Benutzername + Passwort

**Beispiel für Synology/QNAP NAS:**

```bash
# Mount-Point erstellen
sudo mkdir -p /mnt/nas/birdy_backup

# NAS mounten (wählen Sie NFS ODER SMB)

# Option A: NFS (schneller, empfohlen)
sudo mount -t nfs 192.168.1.100:/volume1/birdy_backup /mnt/nas/birdy_backup

# Option B: SMB/CIFS (Windows-kompatibel)
sudo mount -t cifs //192.168.1.100/birdy_backup /mnt/nas/birdy_backup -o username=admin,password=IhrPasswort

# Testen ob es funktioniert
ls /mnt/nas/birdy_backup

# Permanent machen (Mount bleibt nach Neustart)
# Für NFS:
echo "192.168.1.100:/volume1/birdy_backup /mnt/nas/birdy_backup nfs defaults 0 0" | sudo tee -a /etc/fstab

# Für SMB:
echo "//192.168.1.100/birdy_backup /mnt/nas/birdy_backup cifs username=admin,password=IhrPasswort 0 0" | sudo tee -a /etc/fstab
```

**WICHTIG**: Passen Sie an:
- `192.168.1.100` → Ihre NAS IP-Adresse
- `/volume1/birdy_backup` → Ihr NAS Share-Pfad
- `admin` / `IhrPasswort` → Ihre NAS Zugangsdaten

### Schritt 2: Git initialisieren (einmalig)

```bash
cd ~/birdy_project

# Git starten
git init

# Ihre Identität (für Commit-Nachrichten)
git config user.name "Ihr Name"
git config user.email "ihre@email.de"

# Alles hinzufügen
git add .

# Ersten Commit
git commit -m "Initial commit: Birdy Project mit allen Bugfixes"
```

### Schritt 3: Erstes Backup erstellen

```bash
./backup_to_nas.sh
```

**Fertig!** Ihr Code ist jetzt gesichert.

## Tägliche Verwendung

### Code geändert? → Speichern mit Git

```bash
git add .
git commit -m "Kurze Beschreibung was geändert wurde"
```

**Beispiele:**
```bash
git commit -m "PIR Cooldown auf 90s erhöht"
git commit -m "Neue Vogelart Blaumeise hinzugefügt"
git commit -m "Camera Auflösung auf 1920x1080 geändert"
```

### Backup auf NAS

```bash
# Manuell
./backup_to_nas.sh

# Automatisch jeden Tag um 3 Uhr (einmalig einrichten):
crontab -e
# Folgende Zeile einfügen:
0 3 * * * cd /home/pi/birdy_project && ./backup_to_nas.sh >> logs/backup.log 2>&1
```

## Nützliche Befehle

```bash
# Was wurde geändert seit letztem Commit?
git status

# Änderungshistorie ansehen
git log --oneline

# Letzten Commit rückgängig machen
git reset --soft HEAD~1

# Datei auf letzten Stand zurücksetzen
git checkout -- dateiname.py

# Backup-Status prüfen
ls -lh /mnt/nas/birdy_backup/
```

## Im Notfall: System wiederherstellen

```bash
# Projekt von NAS wiederherstellen
./restore_from_nas.sh

# Dann Virtual Environment neu erstellen
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# System starten
./start_dev.sh
```

## Hilfe

- **Ausführliche Anleitung**: Siehe [GIT_SETUP.md](GIT_SETUP.md)
- **NAS Mount Probleme**: `mount | grep nas` zum Prüfen
- **Git Fragen**: `git status` zeigt immer den aktuellen Zustand

## Was wird gesichert?

✅ Gesamter Code (.py, .sh Dateien)
✅ Konfiguration (settings.py, celery.py, etc.)
✅ Dokumentation (.md Dateien)
✅ Git History (komplette Änderungshistorie)

❌ Logs (zu groß, nicht wichtig)
❌ Videos/Fotos (separat auf USB/NAS)
❌ Virtual Environment (wird neu erstellt)
❌ Datenbank (kann neu migriert werden)

## Häufige Fragen

**Q: Wie oft soll ich committen?**
A: Bei jeder sinnvollen Änderung! Lieber zu oft als zu selten.

**Q: Muss ich vor jedem Backup committen?**
A: Empfohlen, aber nicht zwingend. Backup-Skript warnt wenn uncommitted changes existieren.

**Q: Wie viele Backups werden behalten?**
A: Letzte 30 Tage automatisch. Ältere werden gelöscht.

**Q: Kann ich auch manuell Backups auf USB-Stick machen?**
A: Ja! Einfach `/mnt/nas/birdy_backup/latest` auf USB-Stick kopieren.

**Q: Was wenn NAS offline ist?**
A: Backup schlägt fehl, aber Git funktioniert weiter lokal.
