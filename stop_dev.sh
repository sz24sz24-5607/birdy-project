#!/bin/bash
# Stop Birdy Development Environment

echo "Stopping all Birdy processes..."

pkill -f "manage.py runserver"
pkill -f "celery.*worker"
pkill -f "celery.*beat"
pkill -f "python.*manage.py.*start_birdy"

sleep 2

echo "✓ All processes stopped"
