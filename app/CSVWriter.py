import ast
import csv


class CSVWriter:
    circuits = None

    # Aluminum R = 36/S(c.s.a)
    # Aluminum S = 2000mmsq
    # R = 36/2000 = 0.018 Ohms per km

    R = 0.018

    def __init__(self, circuits):
        self.circuits = circuits

    @staticmethod
    def try_parse_int(string):
        try:
            return int(string)
        except ValueError:
            return 0

    @staticmethod
    def sanitize_csv(string):
        if string:
            return string.replace("'", '').replace(';', '-')
        return ''

    @staticmethod
    def convert_set_to_string(set_to_convert):
        return CSVWriter.sanitize_csv('-'.join([str(v) for v in set_to_convert]))

    @staticmethod
    def convert_min_set_to_string(set_to_convert):
        if len(set_to_convert):
            return CSVWriter.sanitize_csv(str(sorted(set_to_convert)[0]))
        return ''

    def publish(self, file_name):

        id_by_station_dict = dict()
        line_counter = 1

        with open(file_name + '_nodes.csv', 'wb') as nodes_file, \
                open(file_name + '_lines.csv', 'wb') as lines_file:

            nodes_writer = csv.writer(nodes_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            nodes_writer.writerow(
                ['n_id', 'longitude', 'latitude', 'type', 'voltage', 'frequency', 'name', 'operator', 'not_accurate'])

            lines_writer = csv.writer(lines_file, delimiter=',', quoting=csv.QUOTE_MINIMAL)
            lines_writer.writerow(['l_id', 'n_id_start', 'n_id_end', 'voltage', 'cables', 'type',
                                   'frequency', 'name', 'operator', 'length_m', 'r_ohm_km', 'x_ohm_km', 'c_nf_km',
                                   'i_th_max_km', 'not_accurate'])

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
                not_accurate_line = False

                for line_part in circuit.members[1:-1]:
                    tags_list = ast.literal_eval(str(line_part.tags))
                    line_tags = dict(zip(tags_list[::2], tags_list[1::2]))
                    line_tags_keys = line_tags.keys()
                    voltages.update([CSVWriter.try_parse_int(v) for v in line_part.voltage.split(';')])
                    if 'cables' in line_tags_keys:
                        cables.update([CSVWriter.try_parse_int(line_tags['cables'])])
                    if 'frequency' in line_tags_keys:
                        frequencies.update([CSVWriter.try_parse_int(line_tags['frequency'])])
                    if 'operator' in line_tags_keys:
                        operators.update([CSVWriter.sanitize_csv(line_tags['operator'])])
                    names.update([line_part.name if line_part.name else ''])
                    types.update([line_part.type])

                    line_length += line_part.length

                if len(voltages) > 1 or len(cables) > 1 or len(frequencies) > 1 or len(types) > 1:
                    not_accurate_line = True

                for station in [station1, station2]:
                    if station not in id_by_station_dict:
                        tags_list = [x.replace('"', "").replace('\\', "").strip() for x in
                                     str(station.tags).replace(',', '=>').split('=>')]
                        station_tags = dict(zip(tags_list[::2], tags_list[1::2]))
                        id_by_station_dict[station] = station.id
                        station_tags_keys = station_tags.keys()
                        station_voltages = [CSVWriter.try_parse_int(v) for v in str(station.voltage).split(';')]
                        not_accurate_node = False
                        if len(station_voltages) > 1:
                            not_accurate_node = True

                        nodes_writer.writerow(
                            [str(station.id),
                             str(station.lon),
                             str(station.lat),
                             str(station.type),
                             CSVWriter.convert_min_set_to_string(station_voltages),
                             str(station_tags['frequency'] if 'frequency' in station_tags_keys else ''),
                             str(CSVWriter.sanitize_csv(station.name) if station.name else ''),
                             str(CSVWriter.sanitize_csv(station_tags['operator'])
                                 if 'operator' in station_tags_keys else ''),
                             'Yes' if not_accurate_node else ''])
                lines_writer.writerow([str(line_counter),
                                       str(id_by_station_dict[station1]),
                                       str(id_by_station_dict[station2]),
                                       CSVWriter.convert_min_set_to_string(voltages),
                                       CSVWriter.convert_min_set_to_string(cables),
                                       CSVWriter.convert_min_set_to_string(types),
                                       CSVWriter.convert_min_set_to_string(frequencies),
                                       CSVWriter.convert_set_to_string(names),
                                       CSVWriter.convert_set_to_string(operators),
                                       str(round(line_length)),
                                       CSVWriter.convert_min_set_to_string(r_ohm_kms),
                                       # http://www.electricalengineeringtoolbox.com/2009/11/calculation-of-cable-resistance.html
                                       CSVWriter.convert_min_set_to_string(x_ohm_kms),
                                       CSVWriter.convert_min_set_to_string(c_nf_kms),
                                       CSVWriter.convert_min_set_to_string(i_th_max_kms),
                                       'Yes' if not_accurate_line else ''])
                line_counter += 1
