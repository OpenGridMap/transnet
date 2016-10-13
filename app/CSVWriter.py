import ast
import csv
import json


class CSVWriter:
    circuits = None

    def __init__(self, circuits):
        self.circuits = circuits

    @staticmethod
    def try_parse_int(string):
        try:
            return int(string)
        except ValueError:
            return 0

    def publish(self, file_name):

        id_by_station_dict = dict()
        station_counter = 1
        line_counter = 1

        with open(file_name + '_nodes.csv', 'wb') as nodes_file, \
                open(file_name + '_lines.csv', 'wb') as lines_file:

            nodes_writer = csv.writer(nodes_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            nodes_writer.writerow(['n_id', 'longitude', 'latitude', 'type', 'voltage', 'frequency', 'name', 'operator'])

            lines_writer = csv.writer(lines_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            lines_writer.writerow(['l_id', 'n_id_start', 'n_id_end', 'voltage', 'cables', 'type',
                                   'frequency', 'name', 'operator', 'length_m', 'r_ohm_km', 'x_ohm_km', 'c_nf_km',
                                   'i_th_max_km'])

            for circuit in self.circuits:
                station1 = circuit.members[0]
                station2 = circuit.members[-1]
                line_length = 0
                voltages = set()
                cables = set()
                frequencies = set()
                names = set()
                operators = set()
                r_ohm_kms = set()
                x_ohm_kms = set()
                c_nf_kms = set()
                i_th_max_kms = set()
                types = set()

                for line_part in circuit.members[1:-1]:
                    tags_list = ast.literal_eval(str(line_part.tags))
                    line_tags = dict(zip(tags_list[::2], tags_list[1::2]))
                    line_tags_keys = line_tags.keys()
                    voltages.update([CSVWriter.try_parse_int(v) for v in line_part.voltage.split(';')])
                    if 'cables' in line_tags_keys:
                        cables.update([line_tags['cables']])
                    if 'frequency' in line_tags_keys:
                        frequencies.update([CSVWriter.try_parse_int(line_tags['frequency'])])
                    if 'operator' in line_tags_keys:
                        operators.update([line_tags['operator'].replace("'", '').replace(';', '-')])
                    names.update([line_part.name.replace("'", '').replace(';', '-') if line_part.name else ''])
                    types.update([line_part.type])

                    line_length += line_part.length
                for station in [station1, station2]:
                    if station not in id_by_station_dict:
                        tags_list = [x.replace('"', "").replace('\\', "").strip() for x in
                                     str(station.tags).replace(',', '=>').split('=>')]
                        station_tags = dict(zip(tags_list[::2], tags_list[1::2]))
                        id_by_station_dict[station] = station_counter
                        station_tags_keys = station_tags.keys()
                        nodes_writer.writerow(
                            [str(station_counter),
                             str(station.lon),
                             str(station.lat),
                             str(station.type),
                             str(station.voltage).replace(';', '-'),
                             str(station_tags['frequency'] if 'frequency' in station_tags_keys else ''),
                             str(station.name.replace("'", '').replace(';', '-') if station.name else ''),
                             str(station_tags['operator']
                                 .replace("'", '').replace(';', '-') if 'operator' in station_tags_keys else '')])
                        station_counter += 1
                lines_writer.writerow([str(line_counter),
                                       str(id_by_station_dict[station1]),
                                       str(id_by_station_dict[station2]),
                                       '-'.join([str(v) for v in voltages]),
                                       '-'.join([str(v) for v in cables]),
                                       '-'.join([str(v) for v in types]),
                                       '-'.join([str(v) for v in frequencies]),
                                       '-'.join([str(v) for v in names]),
                                       '-'.join([str(v) for v in operators]),
                                       str(line_length),
                                       str(r_ohm_kms).replace(';', '-'),
                                       str(x_ohm_kms).replace(';', '-'),
                                       str(c_nf_kms).replace(';', '-'),
                                       str(i_th_max_kms).replace(';', '-')])
                line_counter += 1
