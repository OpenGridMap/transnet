from Way import Way


class Line(Way):
    cables = None
    end_point_dict = None
    srs_geom = None
    length = None

    def __init__(self, id, geom, srs_geom, type, name, ref, voltage, cables, nodes, tags, lat, lon, end_point_dict,
                 length, raw_geom):
        Way.__init__(self, id, geom, type, name, ref, voltage, nodes, tags, lat, lon, raw_geom)
        self.srs_geom = srs_geom
        self.cables = cables
        self.end_point_dict = end_point_dict
        self.length = length

    def __str__(self):
        return 'Line - ' + Way.__str__(self)

    def serialize(self):
        return {
            'id': self.id,
            'geom': str(self.geom),
            'srs_geom': str(self.srs_geom),
            'type': self.type,
            'name': str(self.name),
            'voltage': str(self.voltage),
            'cables': str(self.cables),
            'nodes': self.nodes,
            'tags': str(self.tags),
            'lat': str(self.lat),
            'lon': str(self.lon),
            'length': str(self.length),
            'raw_geom': str(self.raw_geom)
        }
