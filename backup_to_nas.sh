#!/bin/bash
# Backup Birdy Project to NAS
# Erstellt tägliche Backups + aktuelles "latest" Backup

set -e  # Beende bei Fehler

# Konfiguration
PROJECT_DIR="/home/pi/birdy_project"
NAS_BACKUP_DIR="/mnt/nas/birdy_backup"  # ANPASSEN an Ihr NAS Mount-Point!
BACKUP_DATE=$(date +%Y-%m-%d)
BACKUP_TIME=$(date +%H-%M-%S)

# Farben für Output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Birdy Project Backup ===${NC}"
echo "Date: $BACKUP_DATE $BACKUP_TIME"
echo "Project: $PROJECT_DIR"
echo "NAS: $NAS_BACKUP_DIR"
echo ""

# Prüfe ob NAS gemountet ist
if [ ! -d "$NAS_BACKUP_DIR" ]; then
    echo -e "${RED}ERROR: NAS backup directory not found: $NAS_BACKUP_DIR${NC}"
    echo "Bitte mounten Sie zuerst Ihr NAS oder passen Sie NAS_BACKUP_DIR an!"
    echo ""
    echo "Beispiele:"
    echo "  NFS:  sudo mount -t nfs NAS_IP:/volume1/birdy_backup $NAS_BACKUP_DIR"
    echo "  CIFS: sudo mount -t cifs //NAS_IP/birdy_backup $NAS_BACKUP_DIR -o username=USER"
    exit 1
fi

# Prüfe ob NAS beschreibbar ist
if [ ! -w "$NAS_BACKUP_DIR" ]; then
    echo -e "${RED}ERROR: NAS backup directory not writable: $NAS_BACKUP_DIR${NC}"
    echo "Prüfen Sie Berechtigungen!"
    exit 1
fi

echo -e "${GREEN}✓${NC} NAS mounted and writable"

# Wechsle ins Projekt-Verzeichnis
cd "$PROJECT_DIR"

# Git Status prüfen
if [ -d ".git" ]; then
    echo ""
    echo "Git Status:"

    # Prüfe ob es uncommitted changes gibt
    if ! git diff-index --quiet HEAD --; then
        echo -e "${YELLOW}⚠ Warning: Uncommitted changes detected!${NC}"
        echo "Folgende Dateien haben Änderungen:"
        git status --short
        echo ""
        echo "Empfehlung: Commit vor Backup erstellen:"
        echo "  git add ."
        echo "  git commit -m 'Beschreibung der Änderungen'"
        echo ""
        read -p "Trotzdem Backup erstellen? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Backup abgebrochen."
            exit 1
        fi
    else
        echo -e "${GREEN}✓${NC} Git repository clean (no uncommitted changes)"

        # Zeige letzten Commit
        LAST_COMMIT=$(git log -1 --oneline)
        echo "Last commit: $LAST_COMMIT"
    fi
else
    echo -e "${YELLOW}⚠ Warning: Not a git repository${NC}"
    echo "Git ist nicht initialisiert. Backup läuft trotzdem."
fi

# Erstelle Backup-Verzeichnisse
DAILY_BACKUP="$NAS_BACKUP_DIR/$BACKUP_DATE"
LATEST_BACKUP="$NAS_BACKUP_DIR/latest"

mkdir -p "$DAILY_BACKUP"
mkdir -p "$LATEST_BACKUP"

echo ""
echo -e "${GREEN}Starting backup...${NC}"

# Rsync Optionen:
# -a: archive mode (erhält Berechtigungen, Zeiten, etc.)
# -v: verbose
# -h: human-readable
# --delete: Löscht Dateien im Backup die im Source nicht mehr existieren
# --exclude: Ausschluss von Dateien/Ordnern

rsync -avh --no-specials --no-devices \
    --delete \
    --exclude='venv/' \
    --exclude='venv_old/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='*.log' \
    --exclude='logs/' \
    --exclude='db.sqlite3' \
    --exclude='media/photos/' \
    --exclude='media/videos/' \
    --exclude='usb_storage/' \
    --exclude='tensorflow_src/' \
    --exclude='tflite_build/' \
    --exclude='test_script/' \
    --exclude='.git/objects/' \
    --exclude='*.tmp' \
    --exclude='celerybeat-schedule' \
    --exclude='*.pid' \
    "$PROJECT_DIR/" "$DAILY_BACKUP/"

echo ""
echo -e "${GREEN}✓${NC} Daily backup created: $DAILY_BACKUP"

# Update "latest" backup
rsync -avh --delete "$DAILY_BACKUP/" "$LATEST_BACKUP/"
echo -e "${GREEN}✓${NC} Latest backup updated: $LATEST_BACKUP"

# Git Bundle erstellen (komplette Git History als einzelne Datei)
if [ -d ".git" ]; then
    echo ""
    echo "Creating git bundle (complete history)..."
    git bundle create "$DAILY_BACKUP/birdy_project.bundle" --all
    cp "$DAILY_BACKUP/birdy_project.bundle" "$LATEST_BACKUP/"
    echo -e "${GREEN}✓${NC} Git bundle created (can be used to restore complete git history)"
fi

# Backup-Info Datei erstellen
INFO_FILE="$DAILY_BACKUP/backup_info.txt"
cat > "$INFO_FILE" << EOF
Birdy Project Backup
====================
Date: $BACKUP_DATE $BACKUP_TIME
Host: $(hostname)
User: $(whoami)
Project: $PROJECT_DIR

Git Info:
$(if [ -d ".git" ]; then
    echo "Branch: $(git branch --show-current)"
    echo "Last commit: $(git log -1 --oneline)"
    echo "Total commits: $(git rev-list --count HEAD)"
else
    echo "Not a git repository"
fi)

Backup Size: $(du -sh "$DAILY_BACKUP" | cut -f1)

Files Backed Up:
$(find "$DAILY_BACKUP" -type f | wc -l) files

Restore Instructions:
1. Copy backup to Raspberry Pi:
   rsync -av $DAILY_BACKUP/ ~/birdy_project/

2. Restore git repository:
   cd ~/birdy_project
   git bundle unbundle birdy_project.bundle

3. Recreate virtual environment:
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

4. Start system:
   ./start_dev.sh
EOF

echo -e "${GREEN}✓${NC} Backup info created: $INFO_FILE"

# Alte Backups löschen (behalte letzte 30 Tage)
echo ""
echo "Cleaning old backups (keeping last 30 days)..."
find "$NAS_BACKUP_DIR" -maxdepth 1 -type d -name "20*" -mtime +30 -exec rm -rf {} \;
echo -e "${GREEN}✓${NC} Old backups cleaned"

# Zusammenfassung
echo ""
echo -e "${GREEN}=== Backup Complete ===${NC}"
echo "Daily backup: $DAILY_BACKUP"
echo "Latest backup: $LATEST_BACKUP"
echo "Size: $(du -sh "$DAILY_BACKUP" | cut -f1)"
echo ""
echo "To restore this backup:"
echo "  rsync -av $DAILY_BACKUP/ ~/birdy_project/"
echo ""

# Backup-Log erstellen
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup successful to $DAILY_BACKUP" >> "$LOG_DIR/backup.log"

exit 0
