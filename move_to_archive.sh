#!/bin/bash
# Move unused/outdated files to archive
# Preserves directory structure

ARCHIVE_DIR="birdy_archive"
DATE=$(date +%Y%m%d_%H%M%S)

echo "=== Moving unused files to archive ==="
echo "Archive directory: $ARCHIVE_DIR"
echo ""

# Create archive base directory
mkdir -p "$ARCHIVE_DIR"

# Function to move file preserving directory structure
move_to_archive() {
    local file="$1"
    local reason="$2"

    if [ ! -f "$file" ] && [ ! -d "$file" ]; then
        echo "SKIP: $file (not found)"
        return
    fi

    # Get directory path
    local dir=$(dirname "$file")
    local basename=$(basename "$file")

    # Create archive subdirectory
    mkdir -p "$ARCHIVE_DIR/$dir"

    # Move file
    mv "$file" "$ARCHIVE_DIR/$dir/"
    echo "✓ Archived: $file ($reason)"
}

echo "1. Outdated Documentation"
echo "-------------------------"
move_to_archive "CELERY_WORKER_SETUP.md" "Outdated - replaced by PRODUCTION_SETUP.md"

echo ""
echo "2. Duplicate/Redundant Documentation"
echo "------------------------------------"
move_to_archive "PIR_DEBUGGING_PI5.md" "Redundant - info now in PIR_TROUBLESHOOTING.md"
move_to_archive "GPIO_MONITORING.md" "Redundant - lgpio is now native"
move_to_archive "RASPBERRY_PI5_GPIO.md" "Redundant - covered in LGPIO_MIGRATION.md"

echo ""
echo "3. Monitoring Scripts (no longer needed with native lgpio)"
echo "----------------------------------------------------------"
move_to_archive "monitor_pir_gpio.py" "Not needed - lgpio can't monitor claimed pins anyway"
move_to_archive "monitor_pir_sysfs.py" "Not needed - sysfs not available on Pi 5"
move_to_archive "monitor_pir_direct.py" "Not needed - can't share pin with main app"
move_to_archive "monitor_pir.sh" "Not needed - use logs instead"

echo ""
echo "4. Old/Duplicate Files"
echo "----------------------"
move_to_archive "settings.py" "Duplicate - real one is in birdy_config/settings.py"
move_to_archive "check_status.sh" "Not used - functionality in start_dev.sh"

echo ""
echo "5. Test/Development Scripts"
echo "---------------------------"
if [ -d "test_script" ]; then
    move_to_archive "test_script" "Old test directory"
fi

echo ""
echo "6. Build Artifacts (can be deleted later)"
echo "-----------------------------------------"
if [ -d "tensorflow_src" ]; then
    move_to_archive "tensorflow_src" "Build directory - can be deleted"
fi
if [ -d "tflite_build" ]; then
    move_to_archive "tflite_build" "Build directory - can be deleted"
fi
if [ -d "venv_old" ]; then
    move_to_archive "venv_old" "Old virtual environment - can be deleted"
fi

# Create archive info file
cat > "$ARCHIVE_DIR/ARCHIVE_INFO.md" << 'EOF'
# Birdy Archive

This directory contains files that are no longer actively used but kept for reference.

## Categories

### 1. Outdated Documentation
- **CELERY_WORKER_SETUP.md**: Old Celery setup guide, replaced by PRODUCTION_SETUP.md

### 2. Redundant Documentation
- **PIR_DEBUGGING_PI5.md**: Information now consolidated in PIR_TROUBLESHOOTING.md
- **GPIO_MONITORING.md**: No longer relevant with native lgpio implementation
- **RASPBERRY_PI5_GPIO.md**: Covered in LGPIO_MIGRATION.md

### 3. Obsolete Monitoring Scripts
These scripts were attempts to monitor GPIO while PIR was running, but:
- On Raspberry Pi 5, sysfs GPIO is not available
- lgpio cannot read pins claimed by another process
- Native lgpio implementation makes external monitoring unnecessary

- **monitor_pir_gpio.py**: Attempted lgpio monitoring (fails with "GPIO not allocated")
- **monitor_pir_sysfs.py**: Attempted sysfs monitoring (sysfs not available on Pi 5)
- **monitor_pir_direct.py**: Attempted second gpiozero instance (pin conflict)
- **monitor_pir.sh**: Shell wrapper for monitoring attempts

**Alternative**: Use application logs instead: `tail -f logs/birdy.log | grep "PIR:"`

### 4. Duplicate Files
- **settings.py**: Duplicate of birdy_config/settings.py (wrong location)
- **check_status.sh**: Functionality integrated into start_dev.sh

### 5. Test/Development
- **test_script/**: Old test directory from development

### 6. Build Artifacts (Safe to Delete)
These directories take up ~5.6 GB and can be safely deleted:
- **tensorflow_src/**: TensorFlow source code from build
- **tflite_build/**: TensorFlow Lite build artifacts
- **venv_old/**: Old virtual environment

**To reclaim space:**
```bash
rm -rf birdy_archive/tensorflow_src
rm -rf birdy_archive/tflite_build
rm -rf birdy_archive/venv_old
```

## Current Active Files

### Core Application
- `manage.py` - Django management
- `birdy_config/` - Django settings, Celery config, URLs
- `hardware/` - Hardware interfaces (PIR, Camera, Weight sensor)
- `sensors/` - Sensor models, management commands
- `services/` - Bird detection service
- `species/` - Species detection and classification
- `media_manager/` - Photo/Video management
- `homeassistant/` - Home Assistant integration

### Scripts
- `start_dev.sh` - Start development environment
- `stop_dev.sh` - Stop all services
- `restart_birdy.sh` - Restart Birdy detection system
- `backup_to_nas.sh` - Backup to NAS
- `restore_from_nas.sh` - Restore from NAS

### Analysis Tools
- `analyze_pir_pattern.py` - Analyze PIR trigger patterns

### Documentation
- `GIT_SETUP.md` - Git and NAS backup setup
- `QUICK_START_BACKUP.md` - Quick start for backups
- `LGPIO_MIGRATION.md` - Migration to native lgpio
- `BUGFIX_PIR_8S_DELAY.md` - Documentation of 8s delay bugfix
- `PIR_TROUBLESHOOTING.md` - PIR debugging guide
- `PRODUCTION_SETUP.md` - Production deployment guide
- `SPECIES_DETECTION_RULES.md` - Species classification rules
- `CAMERA_ARCHITECTURE.md` - Camera system architecture
- `MQTT_SETUP.md` - MQTT integration setup

## Restoring Files

If you need any archived file:

```bash
# Copy file back from archive
cp birdy_archive/path/to/file ./path/to/file

# Or move it back
mv birdy_archive/path/to/file ./path/to/file
```

## Archive Date
Created: $(date)
EOF

echo ""
echo "=== Archive Complete ==="
echo ""
echo "Summary:"
echo "--------"
find "$ARCHIVE_DIR" -type f | wc -l | xargs echo "Files archived:"
du -sh "$ARCHIVE_DIR" | awk '{print "Archive size: " $1}'
echo ""
echo "Large directories that can be deleted:"
if [ -d "$ARCHIVE_DIR/tensorflow_src" ]; then
    du -sh "$ARCHIVE_DIR/tensorflow_src" 2>/dev/null || echo "  tensorflow_src/ (not found)"
fi
if [ -d "$ARCHIVE_DIR/tflite_build" ]; then
    du -sh "$ARCHIVE_DIR/tflite_build" 2>/dev/null || echo "  tflite_build/ (not found)"
fi
if [ -d "$ARCHIVE_DIR/venv_old" ]; then
    du -sh "$ARCHIVE_DIR/venv_old" 2>/dev/null || echo "  venv_old/ (not found)"
fi
echo ""
echo "To delete build artifacts and reclaim space:"
echo "  rm -rf birdy_archive/tensorflow_src"
echo "  rm -rf birdy_archive/tflite_build"
echo "  rm -rf birdy_archive/venv_old"
echo ""
echo "Archive info: birdy_archive/ARCHIVE_INFO.md"

exit 0
