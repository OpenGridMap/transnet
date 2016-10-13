class Way:
    def __init__(self, _id, geom, _type, name, ref, voltage, nodes, tags, lat, lon, raw_geom):
        self.id = _id
        self.geom = geom
        self.type = _type
        self.name = name
        self.ref = ref
        self.voltage = voltage
        self.nodes = nodes
        self.tags = tags
        self.lat = lat
        self.lon = lon
        self.raw_geom = raw_geom

    def __str__(self):
        s = list('ID: ' + str(self.id) + ' Type: ' + self.type)
        if self.name:
            s.append(' Name: ' + self.name)
        if self.ref:
            s.append(' Ref: ' + self.ref)
        if self.voltage:
            s.append(' Voltage: ' + self.voltage)
        return ''.join(s)

    def first_node(self):
        if self.nodes and len(self.nodes) > 0:
            return self.nodes[0]
        return None

    def last_node(self):
        if self.nodes and len(self.nodes) > 0:
            return self.nodes[len(self.nodes) - 1]
        return None

    def length(self):
        return self.geom.length
