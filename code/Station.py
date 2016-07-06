from Way import Way

class Station(Way):
    # all starting lines for which a circuit has already been extracted
    covered_line_ids = None
    # remember the connection to a station: map starting line to station
    covered_stations_by_start_line = None
    nominal_power = None # only used by generators

    def __init__(self, id, geom, type, name, ref, voltage, nodes, tags, lat, lon):
        Way.__init__(self, id, geom, type, name, ref, voltage, nodes, tags, lat, lon)
        self.covered_line_ids = []
        self.covered_stations_by_start_line = dict()

    def __str__(self):
        return 'Station - ' + Way.__str__(self)