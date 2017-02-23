import ast
import csv


class CSVWriter:
    circuits = None

    coeffs_of_voltage = {
        220000: dict(wires_typical=2.0, r=0.08, x=0.32, c=11.5, i=1.3),
        380000: dict(wires_typical=4.0, r=0.025, x=0.25, c=13.7, i=2.6)
    }

    def __init__(self, circuits):
        self.circuits = circuits

    @staticmethod
    def convert_wire_names_to_numbers(string):
        wires_names = {'single': 1, 'double': 2, 'triple': 3, 'quad': 4}
        if string:
            wire_tokens = string.split('-')
            return [wires_names[x] if x in wires_names.keys() else 0 for x in wire_tokens]
        return []

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

    @staticmethod
    def convert_max_set_to_string(set_to_convert):
        if len(set_to_convert):
            return CSVWriter.sanitize_csv(str(sorted(set_to_convert)[-1]))
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
                wires = set()
                r_ohm_kms = None
                x_ohm_kms = None
                c_nf_kms = None
                i_th_max_kms = None
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
                    if 'wires' in line_tags_keys:
                        wires.update(
                            CSVWriter.convert_wire_names_to_numbers(CSVWriter.sanitize_csv(line_tags['wires'])))
                    names.update([line_part.name if line_part.name else ''])
                    types.update([line_part.type])

                    line_length += line_part.length

                if len(voltages) > 1 or len(cables) > 1 or len(frequencies) > 1 or len(types) > 1 or len(wires) > 1:
                    not_accurate_line = True

                for station in [station1, station2]:
                    if station not in id_by_station_dict:
                        tags_list = [x.replace('"', "").replace('\\', "").strip() for x in
                                     str(station.tags).replace(',', '=>').split('=>')]
                        station_tags = dict(zip(tags_list[::2], tags_list[1::2]))
                        id_by_station_dict[station] = station.id
                        station_tags_keys = station_tags.keys()
                        station_voltages = [str(CSVWriter.try_parse_int(v)) for v in str(station.voltage).split(';')]
                        not_accurate_node = False
                        # if len(station_voltages) > 1:
                        #     not_accurate_node = True

                        nodes_writer.writerow(
                            [str(station.id),
                             str(station.lon),
                             str(station.lat),
                             str(station.type),
                             ";".join(station_voltages),
                             str(station_tags['frequency'] if 'frequency' in station_tags_keys else ''),
                             str(CSVWriter.sanitize_csv(station.name) if station.name else ''),
                             str(CSVWriter.sanitize_csv(station_tags['operator'])
                                 if 'operator' in station_tags_keys else ''),
                             'Yes' if not_accurate_node else ''])

                length_selected = round(line_length)
                cables_selected = CSVWriter.convert_max_set_to_string(cables)
                voltage_selected = CSVWriter.convert_max_set_to_string(voltages)
                wires_selected = CSVWriter.convert_max_set_to_string(wires)

                voltage_selected_round = 0
                if 360000 <= int(voltage_selected) <= 400000:
                    voltage_selected_round = 380000
                elif 180000 <= int(voltage_selected) <= 260000:
                    voltage_selected_round = 220000
                if length_selected and cables_selected and int(
                        voltage_selected_round) in self.coeffs_of_voltage and wires_selected:
                    coeffs = self.coeffs_of_voltage[int(voltage_selected_round)]
                    # Specific resistance of the transmission lines.
                    if coeffs['wires_typical']:
                        r_ohm_kms = coeffs['r'] / (int(wires_selected) / coeffs['wires_typical']) / (
                        int(cables_selected) / 3.0)
                        # Specific reactance of the transmission lines.
                        x_ohm_kms = coeffs['x'] / (int(wires_selected) / coeffs['wires_typical']) / (
                            int(cables_selected) / 3.0)
                        # Specific capacitance of the transmission lines.
                        c_nf_kms = coeffs['c'] * (int(wires_selected) / coeffs['wires_typical']) * (
                            int(cables_selected) / 3.0)
                        # Specific maximum current of the transmission lines.
                        i_th_max_kms = coeffs['i'] * (int(wires_selected) / coeffs['wires_typical']) * (
                            int(cables_selected) / 3.0)

                lines_writer.writerow([str(line_counter),
                                       str(id_by_station_dict[station1]),
                                       str(id_by_station_dict[station2]),
                                       voltage_selected,
                                       cables_selected,
                                       CSVWriter.convert_max_set_to_string(types),
                                       CSVWriter.convert_max_set_to_string(frequencies),
                                       CSVWriter.convert_set_to_string(names),
                                       CSVWriter.convert_set_to_string(operators),
                                       str(length_selected),
                                       str(r_ohm_kms) if r_ohm_kms else '',
                                       str(x_ohm_kms) if x_ohm_kms else '',
                                       str(c_nf_kms) if c_nf_kms else '',
                                       str(i_th_max_kms) if i_th_max_kms else '',
                                       'Yes' if not_accurate_line else ''])
                line_counter += 1
