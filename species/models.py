"""
Species Models - Vogel-Erkennung und Statistiken
"""
from django.db import models
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth, TruncYear


class BirdSpecies(models.Model):
    """Vogel-Spezies Stammdaten"""
    scientific_name = models.CharField(max_length=200, unique=True)
    common_name_de = models.CharField(max_length=200, blank=True)
    common_name_en = models.CharField(max_length=200, blank=True)
    inat_taxon_id = models.IntegerField(null=True, blank=True, help_text="iNaturalist Taxon ID")
    
    # Metadaten
    description = models.TextField(blank=True)
    conservation_status = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Bird Species"
        ordering = ['common_name_de']
    
    def __str__(self):
        return self.common_name_de or self.scientific_name


class BirdDetection(models.Model):
    """Einzelne Vogel-Detektion mit Klassifikation"""
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    species = models.ForeignKey(BirdSpecies, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Klassifikations-Ergebnisse
    confidence = models.FloatField(help_text="Confidence Score 0-1")
    top_predictions = models.JSONField(default=list, help_text="Top 5 Predictions mit Scores")
    
    # Verknüpfung zu Media
    photo = models.ForeignKey('media_manager.Photo', on_delete=models.SET_NULL, null=True, blank=True)
    video = models.ForeignKey('media_manager.Video', on_delete=models.SET_NULL, null=True, blank=True)
    
    # PIR Event Referenz
    pir_event = models.ForeignKey('sensors.PIREvent', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Verarbeitungs-Status
    processed = models.BooleanField(default=False)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['species', '-timestamp']),
            models.Index(fields=['confidence']),
        ]
    
    def __str__(self):
        species_name = self.species.common_name_de if self.species else "Unbekannt"
        return f"{species_name} ({self.confidence:.2f}) @ {self.timestamp}"


class DailyStatistics(models.Model):
    """Tägliche Statistiken pro Spezies"""
    date = models.DateField(db_index=True)
    species = models.ForeignKey(BirdSpecies, on_delete=models.CASCADE)
    visit_count = models.IntegerField(default=0)
    total_confidence = models.FloatField(default=0)
    avg_confidence = models.FloatField(default=0)
    
    class Meta:
        unique_together = ['date', 'species']
        ordering = ['-date', '-visit_count']
        indexes = [
            models.Index(fields=['-date', 'species']),
        ]
    
    def __str__(self):
        return f"{self.species.common_name_de}: {self.visit_count} visits on {self.date}"
    
    @classmethod
    def update_for_date(cls, date, species):
        """Aktualisiere Statistik für Datum und Spezies"""
        stats = BirdDetection.objects.filter(
            timestamp__date=date,
            species=species,
            processed=True
        ).aggregate(
            count=Count('id'),
            avg_conf=models.Avg('confidence')
        )
        
        obj, created = cls.objects.update_or_create(
            date=date,
            species=species,
            defaults={
                'visit_count': stats['count'] or 0,
                'avg_confidence': stats['avg_conf'] or 0,
            }
        )
        return obj


class MonthlyStatistics(models.Model):
    """Monatliche Statistiken pro Spezies"""
    year = models.IntegerField()
    month = models.IntegerField()
    species = models.ForeignKey(BirdSpecies, on_delete=models.CASCADE)
    visit_count = models.IntegerField(default=0)
    unique_days = models.IntegerField(default=0)

    class Meta:
        unique_together = ['year', 'month', 'species']
        ordering = ['-year', '-month', '-visit_count']
        indexes = [
            models.Index(fields=['-year', '-month', 'species']),
        ]

    def __str__(self):
        return f"{self.species.common_name_de}: {self.visit_count} visits in {self.year}-{self.month:02d}"

    @classmethod
    def update_for_month(cls, year, month, species):
        """Aktualisiere Statistik für Monat und Spezies"""
        # Zähle alle Detections im Monat
        stats = BirdDetection.objects.filter(
            timestamp__year=year,
            timestamp__month=month,
            species=species,
            processed=True
        ).aggregate(
            count=Count('id')
        )

        # Zähle unique Tage mit Detections
        unique_days = BirdDetection.objects.filter(
            timestamp__year=year,
            timestamp__month=month,
            species=species,
            processed=True
        ).dates('timestamp', 'day').count()

        obj, created = cls.objects.update_or_create(
            year=year,
            month=month,
            species=species,
            defaults={
                'visit_count': stats['count'] or 0,
                'unique_days': unique_days,
            }
        )
        return obj


class YearlyStatistics(models.Model):
    """Jährliche Statistiken pro Spezies"""
    year = models.IntegerField(db_index=True)
    species = models.ForeignKey(BirdSpecies, on_delete=models.CASCADE)
    visit_count = models.IntegerField(default=0)
    unique_months = models.IntegerField(default=0)

    class Meta:
        unique_together = ['year', 'species']
        ordering = ['-year', '-visit_count']
        indexes = [
            models.Index(fields=['-year', 'species']),
        ]

    def __str__(self):
        return f"{self.species.common_name_de}: {self.visit_count} visits in {self.year}"

    @classmethod
    def update_for_year(cls, year, species):
        """Aktualisiere Statistik für Jahr und Spezies"""
        # Zähle alle Detections im Jahr
        stats = BirdDetection.objects.filter(
            timestamp__year=year,
            species=species,
            processed=True
        ).aggregate(
            count=Count('id')
        )

        # Zähle unique Monate mit Detections
        unique_months = BirdDetection.objects.filter(
            timestamp__year=year,
            species=species,
            processed=True
        ).dates('timestamp', 'month').count()

        obj, created = cls.objects.update_or_create(
            year=year,
            species=species,
            defaults={
                'visit_count': stats['count'] or 0,
                'unique_months': unique_months,
            }
        )
        return obj