"""
Birdy Configuration Package
Lädt Celery App damit sie in allen Prozessen verfügbar ist
"""
from .celery import app as celery_app

__all__ = ('celery_app',)
