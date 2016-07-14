from Way import Way

class Station(Way):
    # all starting lines for which a circuit has already been extracted
    covered_line_ids = None
    # remember the connection to a station: map starting line to station
    nominal_power = None # only used by generators
    # for validation purposes
    connected_stations = None

    def __init__(self, id, geom, type, name, ref, voltage, nodes, tags, lat, lon):
        Way.__init__(self, id, geom, type, name, ref, voltage, nodes, tags, lat, lon)
        self.covered_line_ids = []
        self.connected_stations = dict()

    def __str__(self):
        return 'Station - ' + Way.__str__(self)

    def add_connected_station(self, station_id, voltage):
        if voltage not in self.connected_stations:
            self.connected_stations[voltage] = set()
        self.connected_stations[voltage].add(station_id)