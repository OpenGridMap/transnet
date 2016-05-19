from Way import Way

class Line(Way):
    cables = None
    end_point_dict = None

    def __init__(self, id, geom, type, name, ref, voltage, cables, nodes, tags, lat, lon, end_point_dict):
        Way.__init__(self, id, geom, type, name, ref, voltage, nodes, tags, lat, lon)
        self.cables = cables
        self.end_point_dict = end_point_dict

    def __str__(self):
        return 'Line - ' + Way.__str__(self)