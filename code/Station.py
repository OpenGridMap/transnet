from Way import Way

class Station(Way):
    covered_line_ids = None

    def __init__(self, id, geom, type, name, nodes, tags):
        Way.__init__(self, id, geom, type, name, nodes, tags)
        self.covered_line_ids = []

    def __str__(self):
        return 'Station - ' + Way.__str__(self)