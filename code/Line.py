from Way import Way

class Line(Way):
    voltage = None
    cables = None
    ref = None

    def __init__(self, id, type, voltage, cables, name, ref, nodes, tags):
        Way.__init__(self, id, type, name, nodes,  tags)
        self.voltage = voltage
        self.cables = cables
        self.ref = ref

    def __str__(self):
        return 'Line - ' + Way.__str__(self)