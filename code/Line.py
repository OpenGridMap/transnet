from Way import Way

class Line(Way):
    cables = None
    end_point_dict = None
    srs_geom = None
    length = None

    def __init__(self, id, geom, srs_geom, type, name, ref, voltage, cables, nodes, tags, lat, lon, end_point_dict, length):
        Way.__init__(self, id, geom, type, name, ref, voltage, nodes, tags, lat, lon)
        self.srs_geom = srs_geom
        self.cables = cables
        self.end_point_dict = end_point_dict
        self.length = length

    def __str__(self):
        return 'Line - ' + Way.__str__(self)