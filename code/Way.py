class Way:
    id = None
    geom = None
    type = None
    name = None
    ref = None
    voltage = None
    nodes = None
    tags = None
    lat = None
    lon = None


    def __init__(self, id, geom, type, name, ref, voltage, nodes, tags, lat, lon):
        self.id = id
        self.geom = geom
        self.type = type
        self.name = name
        self.ref = ref
        self.voltage = voltage
        self.nodes = nodes
        self.tags = tags
        self.lat = lat
        self.lon = lon

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
