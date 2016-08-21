from django.views.generic import TemplateView


class MapView(TemplateView):
    template_name = 'power/map.html'
