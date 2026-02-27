
"""
Sensor Models - Wägezelle und PIR Sensor Daten
"""
from django.db import models
from django.utils import timezone


class WeightMeasurement(models.Model):
    """Futtermenge Messung von der Wägezelle"""
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    weight_grams = models.FloatField(help_text="Gewicht in Gramm")
    tare_offset = models.FloatField(default=0, help_text="Tara-Offset für Kalibrierung")

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        return f"{self.weight_grams}g @ {self.timestamp}"

    @property
    def net_weight(self):
        """Nettogewicht nach Tara-Abzug"""
        return max(0, self.weight_grams - self.tare_offset)


class PIREvent(models.Model):
    """PIR Sensor Event - Bewegungserkennung"""
    EVENT_TYPE_CHOICES = [
        ('triggered', 'Triggered'),
        ('cleared', 'Cleared'),
    ]

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    event_type = models.CharField(max_length=10, choices=EVENT_TYPE_CHOICES)
    duration_seconds = models.FloatField(null=True, blank=True, help_text="Dauer der Bewegung")

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp', 'event_type']),
        ]

    def __str__(self):
        return f"PIR {self.event_type} @ {self.timestamp}"


class SensorStatus(models.Model):
    """Aktueller Status aller Sensoren"""
    updated_at = models.DateTimeField(auto_now=True)

    # Gewichtssensor
    current_weight_grams = models.FloatField(default=0)
    weight_sensor_online = models.BooleanField(default=False)
    last_weight_reading = models.DateTimeField(null=True, blank=True)

    # PIR Sensor
    pir_sensor_online = models.BooleanField(default=False)
    bird_present = models.BooleanField(default=False)
    last_pir_trigger = models.DateTimeField(null=True, blank=True)

    # Kamera
    camera_online = models.BooleanField(default=False)
    last_photo = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Sensor Status"

    def __str__(self):
        return f"Sensor Status @ {self.updated_at}"

    @classmethod
    def get_current(cls):
        """Hole oder erstelle den aktuellen Sensor Status"""
        status, created = cls.objects.get_or_create(pk=1)
        return status
