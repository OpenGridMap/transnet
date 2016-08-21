from django.conf.urls import url
from django.contrib import admin

from djgeojson.views import GeoJSONLayerView

from power import views
from power import models as power_models

urlpatterns = [
    url(r'^lines$', GeoJSONLayerView.as_view(model=power_models.Line, geometry_field='line_string', precision=4,
                                             properties=('name', 'lon', 'lat', 'power_type', 'voltage')), name='lines'),
    url(r'^stations$', GeoJSONLayerView.as_view(model=power_models.Station, geometry_field='poly', precision=4,
                                                properties=('name', 'lon', 'lat', 'power_type', 'voltage')),
        name='stations'),

    url(r'^$', views.MapView.as_view()),

    url(r'^admin/', admin.site.urls),
]
