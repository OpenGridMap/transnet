from Way import Way

class Station(Way):
    # all starting lines for which a circuit has already been extracted
    covered_line_ids = None
    nominal_power = None # only used by generators

    def __init__(self, id, geom, type, name, ref, voltage, nodes, tags):
        Way.__init__(self, id, geom, type, name, ref, voltage, nodes, tags)
        self.covered_line_ids = []

    def __str__(self):
        return 'Station - ' + Way.__str__(self)