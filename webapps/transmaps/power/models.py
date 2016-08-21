from django.contrib.gis.db import models


class PowerBaseModel(models.Model):
    country = models.CharField(max_length=100, )
    name = models.CharField(max_length=500, blank=True, null=True)
    lon = models.FloatField(blank=True, null=True)
    lat = models.FloatField(blank=True, null=True)
    power_type = models.CharField(max_length=500, blank=True, null=True)
    voltage = models.CharField(max_length=500, blank=True, null=True)

    objects = models.GeoManager()

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


class Station(PowerBaseModel):
    poly = models.PolygonField(blank=True, null=True)

    class Meta:
        db_table = 'power_station'


class Line(PowerBaseModel):
    line_string = models.LineStringField(blank=True, null=True)

    class Meta:
        db_table = 'power_line'

