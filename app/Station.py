from Way import Way


class Station(Way):
    # all starting lines for which a circuit has already been extracted
    covered_line_ids = None
    # remember the connection to a station: map starting line to station
    nominal_power = None  # only used by generators
    # for validation purposes
    connected_stations = None

    def __init__(self, _id, geom, _type, name, ref, voltage, nodes, tags, lat, lon, raw_geom):
        Way.__init__(self, _id, geom, _type, name, ref, voltage, nodes, tags, lat, lon, raw_geom)
        self.covered_line_ids = []
        self.connected_stations = dict()
        self.nominal_power = None

        self.missing_voltage_estimatate = None
        self.missing_connection = False

    def __str__(self):
        return 'Station - ' + Way.__str__(self)

    def add_connected_station(self, station_id, voltage):
        if voltage not in self.connected_stations:
            self.connected_stations[voltage] = set()
        self.connected_stations[voltage].add(station_id)

    def add_missing_data_estimation(self, voltage=None):
        self.missing_voltage_estimatate = voltage

    def add_missing_connection(self):
        self.missing_connection = True

    def serialize(self):
        station = {
            'id': self.id,
            'geom': str(self.geom),
            'type': self.type,
            'name': str(self.name),
            'voltage': str(self.voltage),
            'nodes': self.nodes,
            'tags': str(self.tags),
            'lat': str(self.lat),
            'lon': str(self.lon),
            'length': str(self.length()),
            'raw_geom': str(self.raw_geom),
            'nominal_power': str(self.nominal_power)
        }

        if self.missing_voltage_estimatate:
            station['estimated_voltage'] = self.missing_voltage_estimatate

        if self.missing_connection:
            station['missing_connection'] = self.missing_connection

        return station
