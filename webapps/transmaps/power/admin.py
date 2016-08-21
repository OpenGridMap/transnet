from django.contrib.gis import admin
from .models import Line
from .models import Station


@admin.register(Line)
class LineAdmin(admin.GeoModelAdmin):
    search_fields = ['name']
    list_display = ['name']


@admin.register(Station)
class StationAdmin(admin.GeoModelAdmin):
    search_fields = ['name']
    list_display = ['name']
