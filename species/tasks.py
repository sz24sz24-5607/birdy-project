"""
Celery Tasks für Statistiken
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger('birdy')


@shared_task
def update_statistics_task():
    """
    Aktualisiere Monthly und Yearly Statistiken.
    Läuft täglich um Mitternacht.
    """
    try:
        from species.models import BirdSpecies, MonthlyStatistics, YearlyStatistics

        now = timezone.now()
        yesterday = now - timedelta(days=1)

        # Alle Spezies mit Detections
        species_list = BirdSpecies.objects.filter(
            birddetection__processed=True
        ).distinct()

        logger.info(f"Updating statistics for {species_list.count()} species")

        for species in species_list:
            # Update Monthly für aktuellen Monat
            MonthlyStatistics.update_for_month(
                year=now.year,
                month=now.month,
                species=species
            )

            # Wenn gestern ein anderer Monat war, update auch den
            if yesterday.month != now.month:
                MonthlyStatistics.update_for_month(
                    year=yesterday.year,
                    month=yesterday.month,
                    species=species
                )

            # Update Yearly für aktuelles Jahr
            YearlyStatistics.update_for_year(
                year=now.year,
                species=species
            )

            # Wenn gestern ein anderes Jahr war, update auch das
            if yesterday.year != now.year:
                YearlyStatistics.update_for_year(
                    year=yesterday.year,
                    species=species
                )

        logger.info("Statistics update completed")

    except Exception as e:
        logger.error(f"Error updating statistics: {e}")
