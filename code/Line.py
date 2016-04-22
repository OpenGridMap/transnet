from Way import Way

class Line(Way):
    cables = None

    def __init__(self, id, geom, type, name, ref, voltage, cables, nodes, tags, lat, lon):
        Way.__init__(self, id, geom, type, name, ref, voltage, nodes, tags, lat, lon)
        self.cables = cables

    def __str__(self):
        return 'Line - ' + Way.__str__(self)