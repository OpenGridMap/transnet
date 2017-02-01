from Way import Way


class Line(Way):
    def __init__(self, _id, geom, srs_geom, _type, name, ref, voltage, cables, nodes, tags, lat, lon, end_point_dict,
                 length, raw_geom):
        Way.__init__(self, _id, geom, _type, name, ref, voltage, nodes, tags, lat, lon, raw_geom)
        self.srs_geom = srs_geom
        self.cables = cables
        self.end_point_dict = end_point_dict
        self.length = length

        self.missing_voltage_estimatate = None
        self.missing_cables_estimatate = None

    def __str__(self):
        return 'Line - ' + Way.__str__(self)

    def add_missing_data_estimation(self, voltage=None, cables=None):
        self.missing_voltage_estimatate = voltage
        self.missing_cables_estimatate = cables

    def serialize(self):
        line = {
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

        if self.missing_cables_estimatate or self.missing_voltage_estimatate:
            line['estmiated_cables'] = self.missing_cables_estimatate
            line['estmiated_voltage'] = self.missing_voltage_estimatate

        return line
