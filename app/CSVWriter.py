import csv

class CSVWriter:

    circuits = None

    def __init__(self, circuits):
        self.circuits = circuits

    def publish(self, file_name):

        id_by_station_dict = dict()
        station_counter = 1
        line_counter = 1

        with open(file_name + '_nodes.csv', 'wb') as nodes_file, open(file_name + '_lines.csv', 'wb') as lines_file:
            nodes_writer = csv.writer(nodes_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            nodes_writer.writerow(['id', 'lon', 'lat', 'name', 'osm_id', 'voltage'])
            lines_writer = csv.writer(lines_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            lines_writer.writerow(['id', 'n1_id', 'n2_id', 'length', 'voltage'])

            for circuit in self.circuits:
                station1 = circuit.members[0]
                station2 = circuit.members[-1]
                line_length = 0
                for line_part in circuit.members[1:-1]:
                    line_length += line_part.length
                for station in [station1, station2]:
                    if station not in id_by_station_dict:
                        station_id = station_counter
                        id_by_station_dict[station] = station_id
                        nodes_writer.writerow([str(station_id), str(station.lon), str(station.lat), str(station.name), str(station.id), str(station.voltage)])
                        station_counter += 1
                lines_writer.writerow([str(line_counter), str(id_by_station_dict[station1]), str(id_by_station_dict[station2]), str(line_length), str(circuit.voltage)])
                line_counter += 1