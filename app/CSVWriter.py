import csv


class CSVWriter:
    circuits = None

    def __init__(self, circuits):
        self.circuits = circuits

    def publish(self, file_name):

        id_by_station_dict = dict()
        station_counter = 1
        line_counter = 1
        line_segment_counter = 1

        with open(file_name + '_nodes.csv', 'wb') as nodes_file, \
                open(file_name + '_lines.csv', 'wb') as lines_file, \
                open(file_name + '_lines_segment.csv', 'wb') as lines_segment_file:

            nodes_writer = csv.writer(nodes_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            nodes_writer.writerow(['id', 'lon', 'lat', 'name', 'osm_id', 'voltage', 'type', 'poly'])

            lines_writer = csv.writer(lines_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            lines_writer.writerow(['id', 'n1_id', 'n2_id', 'length', 'voltage'])

            lines_segment_writer = csv.writer(lines_segment_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            lines_segment_writer.writerow(['id', 'lon', 'lat', 'name', 'osm_id', 'voltage', 'type', 'line_string'])

            for circuit in self.circuits:
                station1 = circuit.members[0]
                station2 = circuit.members[-1]
                line_length = 0
                for line_part in circuit.members[1:-1]:
                    line_length += line_part.length
                    lines_segment_writer.writerow([str(line_segment_counter), str(line_part.lon), str(line_part.lat),
                                                   str(line_part.name.replace("'", '') if line_part.name else None),
                                                   str(line_part.id),
                                                   str(line_part.voltage), str(line_part.type),
                                                   str(line_part.raw_geom)])
                    line_segment_counter += 1
                for station in [station1, station2]:
                    if station not in id_by_station_dict:
                        station_id = station_counter
                        id_by_station_dict[station] = station_id
                        nodes_writer.writerow(
                            [str(station_id), str(station.lon), str(station.lat),
                             str(station.name.replace("'", '') if station.name else None),
                             str(station.id),
                             str(station.voltage), str(station.type), str(station.raw_geom)])
                        station_counter += 1
                lines_writer.writerow(
                    [str(line_counter), str(id_by_station_dict[station1]), str(id_by_station_dict[station2]),
                     str(line_length), str(circuit.voltage)])
                line_counter += 1
