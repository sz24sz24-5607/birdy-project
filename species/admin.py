from django.contrib import admin
from .models import BirdSpecies, BirdDetection, DailyStatistics, MonthlyStatistics, YearlyStatistics


@admin.register(BirdSpecies)
class BirdSpeciesAdmin(admin.ModelAdmin):
    list_display = ['common_name_de', 'scientific_name', 'conservation_status']
    list_filter = ['conservation_status']
    search_fields = ['common_name_de', 'scientific_name', 'common_name_en']
    ordering = ['common_name_de']


@admin.register(BirdDetection)
class BirdDetectionAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'species', 'confidence_display', 'processed', 'processing_time_ms']
    list_filter = ['processed', 'timestamp', 'species']
    date_hierarchy = 'timestamp'
    search_fields = ['species__common_name_de', 'species__scientific_name']
    readonly_fields = ['timestamp', 'confidence_display', 'top_predictions', 'processing_time_ms']
    
    def confidence_display(self, obj):
        return f"{obj.confidence:.2%}"
    confidence_display.short_description = 'Confidence'
    
    def has_add_permission(self, request):
        return False


@admin.register(DailyStatistics)
class DailyStatisticsAdmin(admin.ModelAdmin):
    list_display = ['date', 'species', 'visit_count', 'avg_confidence_display']
    list_filter = ['date', 'species']
    date_hierarchy = 'date'
    readonly_fields = ['date', 'species', 'visit_count', 'avg_confidence']
    
    def avg_confidence_display(self, obj):
        return f"{obj.avg_confidence:.2%}"
    avg_confidence_display.short_description = 'Avg Confidence'
    
    def has_add_permission(self, request):
        return False


@admin.register(MonthlyStatistics)
class MonthlyStatisticsAdmin(admin.ModelAdmin):
    list_display = ['year', 'month', 'species', 'visit_count', 'unique_days']
    list_filter = ['year', 'month', 'species']
    readonly_fields = ['year', 'month', 'species', 'visit_count', 'unique_days']
    
    def has_add_permission(self, request):
        return False


@admin.register(YearlyStatistics)
class YearlyStatisticsAdmin(admin.ModelAdmin):
    list_display = ['year', 'species', 'visit_count', 'unique_months']
    list_filter = ['year', 'species']
    readonly_fields = ['year', 'species', 'visit_count', 'unique_months']
    
    def has_add_permission(self, request):
        return False