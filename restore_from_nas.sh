#!/bin/bash
# Restore Birdy Project from NAS Backup

set -e

# Konfiguration
NAS_BACKUP_DIR="/mnt/nas/birdy_backup"  # ANPASSEN an Ihr NAS Mount-Point!
TARGET_DIR="/home/pi/birdy_project"

# Farben
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Birdy Project Restore ===${NC}"
echo ""

# Prüfe ob NAS gemountet ist
if [ ! -d "$NAS_BACKUP_DIR" ]; then
    echo -e "${RED}ERROR: NAS backup directory not found: $NAS_BACKUP_DIR${NC}"
    exit 1
fi

# Liste verfügbare Backups
echo "Available backups:"
echo ""
ls -lh "$NAS_BACKUP_DIR" | grep "^d" | awk '{print $9, "(" $5 ")"}'
echo ""

# Frage welches Backup restored werden soll
echo "Available options:"
echo "  1) latest    - Most recent backup"
echo "  2) YYYY-MM-DD - Specific date"
echo ""
read -p "Which backup to restore? (latest/YYYY-MM-DD): " BACKUP_CHOICE

if [ "$BACKUP_CHOICE" = "latest" ]; then
    BACKUP_PATH="$NAS_BACKUP_DIR/latest"
elif [ -d "$NAS_BACKUP_DIR/$BACKUP_CHOICE" ]; then
    BACKUP_PATH="$NAS_BACKUP_DIR/$BACKUP_CHOICE"
else
    echo -e "${RED}ERROR: Backup not found: $BACKUP_CHOICE${NC}"
    exit 1
fi

echo ""
echo "Restoring from: $BACKUP_PATH"
echo "To: $TARGET_DIR"
echo ""

# Warnung wenn Ziel existiert
if [ -d "$TARGET_DIR" ]; then
    echo -e "${YELLOW}⚠ WARNING: Target directory exists!${NC}"
    echo "This will overwrite existing files in $TARGET_DIR"
    echo ""
    read -p "Continue? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Restore cancelled."
        exit 0
    fi

    # Backup des aktuellen Zustands
    echo ""
    echo "Creating backup of current state..."
    BACKUP_CURRENT="/tmp/birdy_backup_before_restore_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_CURRENT"
    rsync -a "$TARGET_DIR/" "$BACKUP_CURRENT/" 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Current state backed up to: $BACKUP_CURRENT"
fi

# Restore durchführen
echo ""
echo -e "${GREEN}Starting restore...${NC}"
mkdir -p "$TARGET_DIR"
rsync -avh --delete "$BACKUP_PATH/" "$TARGET_DIR/"

echo ""
echo -e "${GREEN}✓${NC} Files restored"

# Git Bundle restore (falls vorhanden)
if [ -f "$BACKUP_PATH/birdy_project.bundle" ]; then
    echo ""
    echo "Restoring git repository from bundle..."
    cd "$TARGET_DIR"

    if [ -d ".git" ]; then
        echo "Git repository already exists, skipping bundle restore"
    else
        git init
        git bundle unbundle birdy_project.bundle
        git checkout main 2>/dev/null || git checkout master 2>/dev/null || true
        echo -e "${GREEN}✓${NC} Git repository restored"
    fi
fi

# Post-Restore Schritte
echo ""
echo -e "${YELLOW}Post-Restore Steps:${NC}"
echo ""
echo "1. Recreate virtual environment:"
echo "   cd $TARGET_DIR"
echo "   python3 -m venv venv"
echo "   source venv/bin/activate"
echo "   pip install -r requirements.txt"
echo ""
echo "2. Check configuration:"
echo "   Review birdy_config/settings.py"
echo "   Review database settings"
echo ""
echo "3. Initialize database (if needed):"
echo "   python manage.py migrate"
echo ""
echo "4. Start system:"
echo "   ./start_dev.sh"
echo ""
echo -e "${GREEN}=== Restore Complete ===${NC}"
echo "Restored from: $BACKUP_PATH"
echo "Restored to: $TARGET_DIR"
echo ""

if [ -d "$BACKUP_CURRENT" ]; then
    echo "Previous state backed up to: $BACKUP_CURRENT"
    echo "(Delete when no longer needed)"
fi

exit 0
