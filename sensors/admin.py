from django.contrib import admin
from .models import WeightMeasurement, PIREvent, SensorStatus


@admin.register(WeightMeasurement)
class WeightMeasurementAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'weight_grams', 'net_weight']
    list_filter = ['timestamp']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp', 'net_weight']
    
    def has_add_permission(self, request):
        return False


@admin.register(PIREvent)
class PIREventAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'event_type', 'duration_seconds']
    list_filter = ['event_type', 'timestamp']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']
    
    def has_add_permission(self, request):
        return False


@admin.register(SensorStatus)
class SensorStatusAdmin(admin.ModelAdmin):
    list_display = ['updated_at', 'current_weight_grams', 'bird_present', 
                    'weight_sensor_online', 'pir_sensor_online', 'camera_online']
    readonly_fields = ['updated_at', 'current_weight_grams', 'bird_present',
                       'last_weight_reading', 'last_pir_trigger', 'last_photo']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
