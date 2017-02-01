import json
import logging
import sys
import urllib
from datetime import datetime
from optparse import OptionParser
from os import makedirs, remove
from os import walk
from os.path import dirname, getsize
from os.path import exists
from os.path import join
from subprocess import call

import psycopg2
from shapely import wkb, wkt
from shapely.geometry import MultiPoint

from CSVWriter import CSVWriter
from CimWriter import CimWriter
from Circuit import Circuit
from InferenceValidator import InferenceValidator
from Line import Line
from LoadEstimator import LoadEstimator
from Plotter import Plotter
from PolyParser import PolyParser
from Station import Station

root = logging.getLogger()
root.setLevel(logging.DEBUG)


class Transnet:
    covered_nodes = None

    def __init__(self, _database, _user, _host, _port, _password, _ssid, _poly, _bpoly, _verbose, _validate,
                 _topology, _voltage_levels, _load_estimation, _destdir, _continent, _whole_planet, _find_missing_data):
        self.length_all = 0
        self.all_lines = dict()
        self.all_stations = dict()
        self.all_power_planet = dict()

        self.db_name = _database
        self.ssid = _ssid
        self.poly = _poly
        self.bpoly = _bpoly
        self.verbose = _verbose
        self.validate = _validate
        self.topology = _topology
        self.voltage_levels = _voltage_levels
        self.load_estimation = _load_estimation
        self.destdir = _destdir
        self.chose_continent = _continent
        self.whole_planet = _whole_planet
        self.find_missing_data = _find_missing_data

        self.connection = {'database': _database, 'user': _user, 'host': _host, 'port': _port}
        self.conn = psycopg2.connect(password=_password, **self.connection)
        self.cur = self.conn.cursor()

    @staticmethod
    def prepare_poly_country(continent_name, country):
        if not exists('../data/{0}/{1}/'.format(continent_name, country)):
            makedirs('../data/{0}/{1}/'.format(continent_name, country))
        root.info('Downloading poly for {0}'.format(country))
        if continent_name == 'usa':
            download_string = 'http://download.geofabrik.de/north-america/us/{0}.poly'.format(country)
            root.info(download_string)
        elif continent_name == 'germany':
            download_string = 'http://download.geofabrik.de/europe/germany/{0}.poly'.format(country)
            root.info(download_string)
        else:
            download_string = 'http://download.geofabrik.de/{0}/{1}.poly'.format(continent_name, country)
        urllib.URLopener().retrieve(download_string, '../data/{0}/{1}/pfile.poly'.format(continent_name, country))

    @staticmethod
    def prepare_poly_continent(continent_name):
        if not exists('../data/planet/{0}/'.format(continent_name)):
            makedirs('../data/planet/{0}/'.format(continent_name))
        root.info('Downloading poly for {0}'.format(continent_name))
        if continent_name == 'usa':
            download_string = 'http://svn.openstreetmap.org/applications/utils/' \
                              'osm-extract/polygons/united_states_inc_ak_and_hi.poly'
        elif continent_name == 'germany':
            download_string = 'http://download.geofabrik.de/europe/germany.poly'
        else:
            download_string = 'http://download.geofabrik.de/{0}.poly'.format(continent_name)
        urllib.URLopener().retrieve(download_string, '../data/planet/{0}/pfile.poly'.format(continent_name))

    @staticmethod
    def reset_params():
        Transnet.covered_nodes = None

    @staticmethod
    def create_relations(stations, lines, _ssid, voltage):
        # root.info('\nStart inference for Substation %s', str(ssid))
        station_id = long(_ssid)

        relations = []
        relations.extend(Transnet.infer_relations(stations, lines, stations[station_id]))

        circuits = []
        for relation in relations:
            if Transnet.num_subs_in_relation(relation) == 2 and len(
                    relation) >= 3:  # at least two end points + one line

                first_line = relation[1]
                station1 = relation[0]
                station2 = relation[-1]
                station1.add_connected_station(station2.id, voltage)
                station2.add_connected_station(station1.id, voltage)

                circuit = Circuit(relation, voltage, first_line.name, first_line.ref)

                circuits.append(circuit)

        return circuits

    # inferences circuits around a given station
    # station - represents the station to infer circuits for
    # stations - dict of all possibly connected stations
    # lines - list of all lines that could connect stations
    @staticmethod
    def infer_relations(stations, lines, station):
        # find lines that cross the station's area - note that
        #  the end point of the line has to be within the substation for valid crossing
        relations = []
        for line in lines.values():
            node_to_continue_id = None
            if Transnet.node_in_any_station(line.end_point_dict[line.first_node()], [station]):
                node_to_continue_id = line.last_node()
            elif Transnet.node_in_any_station(line.end_point_dict[line.last_node()], [station]):
                node_to_continue_id = line.first_node()
            if node_to_continue_id:
                Transnet.covered_nodes = set(line.nodes)
                Transnet.covered_nodes.remove(node_to_continue_id)
                if line.id in station.covered_line_ids:
                    root.debug('Relation with %s at %s already covered', str(line), str(station))
                    continue
                root.debug('%s', str(station))
                root.debug('%s', str(line))
                station.covered_line_ids.append(line.id)
                # init new circuit
                relation = [station, line]
                relations.extend(
                    Transnet.infer_relation(stations, lines, relation, node_to_continue_id, line))
        return relations

    # recursive function that infers electricity circuits
    # circuit - sorted member array
    # line - line of circuit
    # stations - all known stations
    @staticmethod
    def infer_relation(stations, lines, relation, node_to_continue_id, from_line):
        relation = list(relation)  # make a copy
        start_station = relation[0]
        station_id = Transnet.node_in_any_station(from_line.end_point_dict[node_to_continue_id], stations.values())
        if station_id and station_id == start_station.id:  # if node to continue is at the starting station --> LOOP
            root.debug('Encountered loop: %s', Transnet.to_overpass_string(relation))
            return []
        elif station_id and station_id != start_station.id:
            # if a node is within another station --> FOUND THE 2nd ENDPOINT
            station = stations[station_id]
            root.debug('%s', str(station))
            if from_line.id in station.covered_line_ids:
                root.debug('Relation with %s at %s already covered', str(from_line), str(station))
                return []
            station.covered_line_ids.append(from_line.id)
            relation.append(station)
            root.debug('Could obtain relation')
            return [list(relation)]

        # no endpoints encountered - handle line subsection
        # at first find all lines that cover the node to continue
        relations = []
        for line in lines.values():
            if from_line.end_point_dict[node_to_continue_id].intersects(line.geom):
                if line.id == from_line.id:
                    continue
                root.debug('%s', str(line))
                if from_line.end_point_dict[node_to_continue_id].intersects(line.end_point_dict[line.first_node()]):
                    new_node_to_continue_id = line.last_node()
                else:
                    new_node_to_continue_id = line.first_node()
                if new_node_to_continue_id in Transnet.covered_nodes:
                    relation.append(line)
                    root.debug('Encountered loop - stopping inference at line (%s): %s', str(line.id),
                               Transnet.to_overpass_string(relation))
                    relation.remove(line)
                    Transnet.covered_nodes.update(line.nodes)
                    continue
                relation_copy = list(relation)
                relation_copy.append(line)
                Transnet.covered_nodes.update(line.nodes)
                Transnet.covered_nodes.remove(new_node_to_continue_id)
                relations.extend(Transnet.infer_relation(stations, lines, relation_copy, new_node_to_continue_id, line))

        # if not relations:
        #     root.debug('Could not obtain circuit')
        return relations

    @staticmethod
    def to_overpass_string(relation):
        overpass = ''
        for member in relation:
            overpass += 'way(' + str(member.id) + ');'
        return overpass

    # returns if node is in station
    @staticmethod
    def node_in_any_station(node, stations):
        for station in stations:
            if node.intersects(station.geom):
                return station.id
        return None

    @staticmethod
    def num_subs_in_relation(relation):
        num_stations = 0
        for way in relation:
            if isinstance(way, Station):
                num_stations += 1
        return num_stations

    @staticmethod
    def get_close_components(components, center_component):
        close_components = dict()
        for component in components:
            distance = center_component.geom.centroid.distance(component.geom.centroid)
            if distance <= 300000:
                close_components[component.id] = component
        return close_components

    @staticmethod
    def parse_power(power_string):
        if not power_string:
            return None
        power_string = power_string.replace(',', '.').replace('W', '')
        try:
            if 'k' in power_string:
                tokens = power_string.split('k')
                return float(tokens[0].strip()) * 1000
            elif 'K' in power_string:
                tokens = power_string.split('K')
                return float(tokens[0].strip()) * 1000
            elif 'm' in power_string:
                tokens = power_string.split('m')
                return float(tokens[0].strip()) * 1000000
            elif 'M' in power_string:
                tokens = power_string.split('M')
                return float(tokens[0].strip()) * 1000000
            elif 'g' in power_string:
                tokens = power_string.split('g')
                return float(tokens[0].strip()) * 1000000000
            elif 'G' in power_string:
                tokens = power_string.split('G')
                return float(tokens[0].strip()) * 1000000000
            else:
                return float(power_string.strip())
        except ValueError:
            root.debug('Could not extract power from string %s', power_string)
            return None

    @staticmethod
    def create_relations_of_region(substations, generators, lines, voltage):
        stations = substations.copy()
        stations.update(generators)
        circuits = []
        for substation_id in substations.keys():
            close_stations_dict = Transnet.get_close_components(stations.values(), stations[substation_id])
            close_lines_dict = Transnet.get_close_components(lines.values(), stations[substation_id])
            circuits.extend(Transnet.create_relations(close_stations_dict, close_lines_dict, substation_id, voltage))
        return circuits

    @staticmethod
    def remove_duplicates(circuits):
        root.info('Remove duplicates from %s circuits', str(len(circuits)))
        covered_connections = []
        filtered_circuits = []
        total_line_length = 0
        for circuit in circuits:
            station1 = circuit.members[0]
            station2 = circuit.members[-1]
            for line in circuit.members[1:-1]:
                total_line_length += line.length
            if str(station1.id) + str(station2.id) + str(circuit.voltage) in covered_connections \
                    or str(station2.id) + str(station1.id) + str(circuit.voltage) in covered_connections:
                continue
            covered_connections.append(str(station1.id) + str(station2.id) + str(circuit.voltage))
            filtered_circuits.append(circuit)
        root.info('%s circuits remain', str(len(filtered_circuits)))
        root.info('Line length with duplicates is %s meters', str(total_line_length))
        return filtered_circuits

    @staticmethod
    def run_matlab_for_continent(matlab_command, continent_folder, root_log):
        matlab_dir = join(dirname(__file__), '../matlab')
        try:
            log_dir = join(dirname(__file__), '../logs/planet/{0}'.format(continent_folder))
            if not exists(log_dir):
                makedirs(log_dir)

            command = 'cd {0} && {1} -r "transform planet/{2};quit;"| tee ../logs/planet/{2}/transnet_matlab.log' \
                .format(matlab_dir, matlab_command, continent)
            root_log.info('running MATLAB modeling for {0}'.format(continent_folder))
            return_code = call(command, shell=True)
            root_log.info('MATLAB return code {0}'.format(return_code))
        except Exception as ex:
            root_log.error(ex.message)

    @staticmethod
    def run_matlab_for_countries(matlab_command, continent_folder, root_log):
        dirs = [x[0] for x in walk(join(dirname(__file__), '../models/{0}/'.format(continent_folder)))]
        matlab_dir = join(dirname(__file__), '../matlab')
        for DIR in dirs[1:]:
            try:
                country = DIR.split('/')[-1]
                log_dir = join(dirname(__file__), '../logs/{0}/{1}'.format(continent_folder, country))
                if not exists(log_dir):
                    makedirs(log_dir)

                command = 'cd {0} && {1} -r "transform {2}/{3};quit;"| tee ../logs/{2}/{3}/transnet_matlab.log' \
                    .format(matlab_dir, matlab_command, continent, country)
                root_log.info('running MATLAB modeling for {0}'.format(country))
                return_code = call(command, shell=True)
                root_log.info('MATLAB return code {0}'.format(return_code))
            except Exception as ex:
                root_log.error(ex.message)

    @staticmethod
    def try_parse_int(string):
        try:
            return int(string)
        except ValueError:
            return 0

    @staticmethod
    def convert_size_mega_byte(size):
        return size / 1048576.0

    def prepare_continent_json(self, continent_name):
        with open('meta/{0}.json'.format(continent_name), 'r+') as continent_file:
            continent_json = json.load(continent_file)
            for country in continent_json:
                Transnet.prepare_poly_country(continent_name, country)
                boundary = PolyParser.poly_to_polygon('../data/{0}/{1}/pfile.poly'.format(continent_name, country))
                where_clause = "st_intersects(l.way, st_transform(st_geomfromtext('" + boundary.wkt + "',4269),3857))"

                # where_clause = "ST_Intersects(ST_GeographyFromText(s.geom_str),
                #  st_transform(st_geomfromtext('" + boundary.wkt + "',4269),4326))"
                # with open('../data/{0}/{1}/where_clause'.format(continent_name, country), 'w') as wfile:
                #     wfile.write(where_clause)

                query = '''SELECT DISTINCT(voltage) AS voltage, count(*)
                            AS num FROM planet_osm_line  l WHERE %s
                            GROUP BY voltage ORDER BY num DESC''' % where_clause
                continent_json[country]['voltages'] = self.get_voltages_from_query(query=query)
            continent_file.seek(0)
            continent_file.write(json.dumps(continent_json, indent=4))
            continent_file.truncate()

    def prepare_planet_json(self, continent_name):
        with open('meta/planet.json'.format(continent_name), 'r+') as continent_file:
            continent_json = json.load(continent_file)
            Transnet.prepare_poly_continent(continent_name)
            query = '''SELECT DISTINCT(voltage) AS voltage, count(*) AS num
                        FROM planet_osm_line  l
                        GROUP BY voltage ORDER BY num DESC'''
            continent_json[continent_name]['voltages'] = self.get_voltages_from_query(query=query)
            continent_file.seek(0)
            continent_file.write(json.dumps(continent_json, indent=4))
            continent_file.truncate()

    def get_voltages_from_query(self, query):
        voltages = set()
        voltages_string = ''
        first_round = True
        self.cur.execute(query)
        result = self.cur.fetchall()
        for (voltage, num) in result:
            if num > 30 and voltage:
                raw_voltages = [Transnet.try_parse_int(x) for x in str(voltage).strip().split(';')]
                voltages = voltages.union(set(raw_voltages))
        for voltage in sorted(voltages):
            if voltage > 99999:
                if first_round:
                    voltages_string += str(voltage)
                    first_round = False
                else:
                    voltages_string += '|' + str(voltage)
        return voltages_string

    def export_to_json(self, all_circuits):
        try:
            with open('{0}/relations.json'.format(self.destdir), 'w') as outfile:
                json.dump([c.serialize() for c in all_circuits], outfile, indent=4)
            file_size = Transnet.convert_size_mega_byte(getsize('{0}/relations.json'.format(self.destdir)))

            if file_size >= 100:
                command = 'split --bytes=50M {0}/relations.json {0}/_relations'.format(self.destdir)
                return_code = call(command, shell=True)
                root.info('Relation file split return {0}'.format(return_code))
                remove('{0}/relations.json'.format(self.destdir))
        except Exception as ex:
            root.error(ex.message)

    def inference_for_voltage(self, voltage_level, where_clause, length_found_lines, equipment_points, all_substations,
                              all_generators, boundary):
        root.info('Infer net for voltage level %sV', voltage_level)

        substations = dict()
        generators = dict()
        lines = dict()

        # create lines dictionary
        sql = '''SELECT l.osm_id AS id,
                st_transform(create_line(l.osm_id), 4326) AS geom,
                l.way AS srs_geom, l.power AS type,
                l.name, l.ref, l.voltage, l.cables, w.nodes, w.tags,
                st_transform(create_point(w.nodes[1]), 4326) AS first_node_geom,
                st_transform(create_point(w.nodes[array_length(w.nodes, 1)]), 4326) AS last_node_geom,
                ST_Y(ST_Transform(ST_Centroid(l.way),4326)) AS lat,
                ST_X(ST_Transform(ST_Centroid(l.way),4326)) AS lon,
                st_length(st_transform(l.way, 4326), TRUE) AS spheric_length
                FROM planet_osm_line l, planet_osm_ways w
                WHERE l.osm_id >= 0 AND l.power ~ 'line|cable|minor_line'
                AND l.voltage ~ '%s' AND l.osm_id = w.id AND %s''' % (voltage_level, where_clause)

        self.cur.execute(sql)
        result = self.cur.fetchall()
        # noinspection PyShadowingBuiltins,PyShadowingBuiltins
        for (id, geom, srs_geom, type, name, ref, voltage, cables, nodes, tags, first_node_geom, last_node_geom,
             lat, lon, length) in result:
            line = wkb.loads(geom, hex=True)
            raw_geom = geom
            srs_line = wkb.loads(srs_geom, hex=True)
            length_found_lines += length
            first_node = wkb.loads(first_node_geom, hex=True)
            last_node = wkb.loads(last_node_geom, hex=True)
            end_points_geom_dict = dict()
            end_points_geom_dict[nodes[0]] = first_node
            end_points_geom_dict[nodes[-1]] = last_node
            lines[id] = Line(id, line, srs_line, type, name.replace(',', ';') if name else None,
                             ref.replace(',', ';') if ref is not None else None,
                             voltage.replace(',', ';').replace('/', ';') if voltage else None, cables,
                             nodes, tags, lat, lon,
                             end_points_geom_dict, length, raw_geom)
            equipment_points.append((lat, lon))
        root.info('Found %s lines', str(len(result)))

        # create station dictionary by quering only ways
        # (there are almost no node substations for voltage level 110kV and higher)
        sql = '''SELECT DISTINCT(p.osm_id) AS id,
                  st_transform(p.way, 4326) AS geom,
                  p.power AS type, p.name, p.ref, p.voltage, p.tags,
                  ST_Y(ST_Transform(ST_Centroid(p.way),4326)) AS lat,
                  ST_X(ST_Transform(ST_Centroid(p.way),4326)) AS lon
                  FROM planet_osm_line l, planet_osm_polygon p
                  WHERE l.osm_id >= 0 AND p.osm_id >= 0
                  AND p.power ~ 'substation|station|sub_station' AND (p.voltage ~ '%s'
                  OR (p.voltage = '') IS NOT FALSE) AND st_intersects(l.way, p.way)
                  AND l.power ~ 'line|cable|minor_line' AND l.voltage ~ '%s' AND %s''' \
              % (self.voltage_levels, voltage_level, where_clause)

        self.cur.execute(sql)
        result = self.cur.fetchall()
        # noinspection PyShadowingBuiltins,PyShadowingBuiltins
        for (id, geom, type, name, ref, voltage, tags, lat, lon) in result:
            if id not in all_substations:
                polygon = wkb.loads(geom, hex=True)
                raw_geom = geom
                substations[id] = Station(id, polygon, type, name, ref,
                                          voltage.replace(',', ';').replace('/', ';') if voltage else None,
                                          None, tags, lat, lon, raw_geom)
                equipment_points.append((lat, lon))
            else:
                substations[id] = all_substations[id]

        root.info('Found %s stations', str(len(equipment_points)))

        # add power plants with area
        sql = '''SELECT DISTINCT(p.osm_id) AS id,
                st_transform(p.way, 4326) AS geom,
                p.power AS type,
                p.name, p.ref, p.voltage, p.\"plant:output:electricity\" AS output1,
                p.\"generator:output:electricity\" AS output2,
                p.tags, ST_Y(ST_Transform(ST_Centroid(p.way),4326)) AS lat,
                ST_X(ST_Transform(ST_Centroid(p.way),4326)) AS lon
                FROM planet_osm_line l, planet_osm_polygon p
                WHERE l.osm_id >= 0 AND p.osm_id >= 0 AND p.power ~ 'plant|generator'
                AND st_intersects(l.way, p.way) AND l.power ~ 'line|cable|minor_line'
                AND l.voltage ~ '%s' AND %s''' % (voltage_level, where_clause)

        self.cur.execute(sql)
        result = self.cur.fetchall()
        # noinspection PyShadowingBuiltins,PyShadowingBuiltins
        for (id, geom, type, name, ref, voltage, output1, output2, tags, lat, lon) in result:
            if id not in all_generators:
                polygon = wkb.loads(geom, hex=True)
                raw_geom = geom
                generators[id] = Station(id, polygon, type, name, ref,
                                         voltage.replace(',', ';').replace('/', ';') if voltage else None,
                                         None, tags, lat, lon, raw_geom)
                generators[id].nominal_power = Transnet.parse_power(
                    output1) if output1 is not None else Transnet.parse_power(output2)
                equipment_points.append((lat, lon))
            else:
                generators[id] = all_generators[id]
        root.info('Found %s generators', str(len(generators)))

        if boundary is not None:
            circuits = Transnet.create_relations_of_region(substations, generators, lines, voltage_level)
        else:
            stations = substations.copy()
            stations.update(generators)
            circuits = Transnet.create_relations(stations, lines, self.ssid, voltage_level)

        return length_found_lines, equipment_points, generators, substations, circuits

    def find_missing_data_for_country(self, where_clause):
        root.info('Finding missing data')

        voltages_line = set()
        voltages_cable = set()
        voltages_minor_line = set()
        line_voltage_query = '''SELECT DISTINCT(voltage) AS voltage, power as power_type, count(*) AS num
                                          FROM planet_osm_line  l WHERE %s
                                          GROUP BY power, voltage''' % where_clause
        self.cur.execute(line_voltage_query)
        result_voltages = self.cur.fetchall()
        for (voltage, power_type, num) in result_voltages:
            if num > 30 and voltage:
                raw_voltages = [Transnet.try_parse_int(x) for x in str(voltage).strip().split(';')]
                if power_type == 'line':
                    voltages_line = voltages_line.union(set(raw_voltages))
                elif power_type == 'cable':
                    voltages_cable = voltages_cable.union(set(raw_voltages))
                elif power_type == 'minor_line':
                    voltages_minor_line = voltages_minor_line.union(set(raw_voltages))

        cables_line = set()
        cables_cable = set()
        cables_minor_line = set()
        line_cables_query = '''SELECT DISTINCT(cables) AS cables, power as power_type, count(*) AS num
                                                  FROM planet_osm_line  l WHERE %s
                                                  GROUP BY power, cables''' % where_clause
        self.cur.execute(line_cables_query)
        result_cables = self.cur.fetchall()
        for (cables, power_type, num) in result_cables:
            if num > 30 and cables:
                raw_cables = [Transnet.try_parse_int(x) for x in str(cables).strip().split(';')]
                if power_type == 'line':
                    cables_line = cables_line.union(set(raw_cables))
                elif power_type == 'cable':
                    cables_cable = cables_cable.union(set(raw_cables))
                elif power_type == 'minor_line':
                    cables_minor_line = cables_minor_line.union(set(raw_cables))

        voltages_line_str = ';'.join([str(x) for x in voltages_line])
        cables_line_str = ';'.join([str(x) for x in cables_line])
        voltages_cable_str = ';'.join([str(x) for x in voltages_cable])
        cables_cable_str = ';'.join([str(x) for x in cables_cable])
        voltages_minor_line_str = ';'.join([str(x) for x in voltages_minor_line])
        cables_minor_line_str = ';'.join([str(x) for x in cables_minor_line])

        lines = dict()

        # create lines dictionary
        lines_sql = '''SELECT l.osm_id AS osm_id,
                        st_transform(create_line(l.osm_id), 4326) AS geom,
                        l.way AS srs_geom, l.power AS power_type,
                        l.name, l.ref, l.voltage, l.cables, w.nodes, w.tags,
                        st_transform(create_point(w.nodes[1]), 4326) AS first_node_geom,
                        st_transform(create_point(w.nodes[array_length(w.nodes, 1)]), 4326) AS last_node_geom,
                        ST_Y(ST_Transform(ST_Centroid(l.way),4326)) AS lat,
                        ST_X(ST_Transform(ST_Centroid(l.way),4326)) AS lon,
                        st_length(st_transform(l.way, 4326), TRUE) AS spheric_length
                        FROM planet_osm_line l, planet_osm_ways w
                        WHERE l.osm_id >= 0 AND l.power ~ 'line|cable|minor_line'
                        AND l.voltage IS NULL AND l.osm_id = w.id AND %s''' % where_clause

        self.cur.execute(lines_sql)
        lines_result = self.cur.fetchall()
        for (osm_id, geom, srs_geom, power_type, name, ref, voltage, cables, nodes, tags, first_node_geom,
             last_node_geom, lat, lon, length) in lines_result:
            line = wkb.loads(geom, hex=True)
            raw_geom = geom
            srs_line = wkb.loads(srs_geom, hex=True)
            first_node = wkb.loads(first_node_geom, hex=True)
            last_node = wkb.loads(last_node_geom, hex=True)
            end_points_geom_dict = dict()
            end_points_geom_dict[nodes[0]] = first_node
            end_points_geom_dict[nodes[-1]] = last_node
            temp_line = Line(osm_id, line, srs_line, power_type, name.replace(',', ';') if name else None,
                             ref.replace(',', ';') if ref is not None else None,
                             voltage.replace(',', ';').replace('/', ';') if voltage else None, cables,
                             nodes, tags, lat, lon,
                             end_points_geom_dict, length, raw_geom)
            if power_type == 'line':
                temp_line.add_missing_data_estimation(voltage=voltages_line_str, cables=cables_line_str)
            elif power_type == 'cable':
                temp_line.add_missing_data_estimation(voltage=voltages_cable_str, cables=cables_cable_str)
            elif power_type == 'minor_line':
                temp_line.add_missing_data_estimation(voltage=voltages_minor_line_str, cables=cables_minor_line_str)
            lines[osm_id] = temp_line

        with open('{0}/lines_with_missing_data.json'.format(self.destdir), 'w') as outfile:
            json.dump([l.serialize() for osm_id, l in lines.iteritems()], outfile, indent=4)

    def run(self):
        if self.whole_planet and self.chose_continent:
            with open('meta/planet.json'.format(continent)) as continent_file:
                continent_json = json.load(continent_file)
                try:
                    self.voltage_levels = continent_json[self.chose_continent]['voltages']
                    if self.voltage_levels:
                        self.poly = '../data/planet/{0}/pfile.poly'.format(continent)
                        self.destdir = '../models/planet/{0}/'.format(continent)
                        Transnet.reset_params()
                        self.modeling(continent)
                except Exception as ex:
                    root.error(ex.message)
        elif self.chose_continent:
            with open('meta/{0}.json'.format(continent)) as continent_file:
                continent_json = json.load(continent_file)
                for country in continent_json:
                    try:
                        self.voltage_levels = continent_json[country]['voltages']
                        if self.voltage_levels:
                            self.poly = '../data/{0}/{1}/pfile.poly'.format(continent, country)
                            self.destdir = '../models/{0}/{1}/'.format(continent, country)
                            Transnet.reset_params()
                            self.modeling(country)
                    except Exception as ex:
                        root.error(ex.message)
        else:
            self.modeling(self.db_name)

    def modeling(self, country_name):

        # create dest dir
        if not exists(self.destdir):
            makedirs(self.destdir)

        root.info('Infer for %s', country_name)

        time = datetime.now()

        # build location where clause for succeeding queries
        boundary = None
        if self.poly:
            boundary = PolyParser.poly_to_polygon(self.poly)
            where_clause = "st_intersects(l.way, st_transform(st_geomfromtext('" + boundary.wkt + "',4269),3857))"
        elif self.bpoly:
            boundary = wkt.loads(self.bpoly)
            where_clause = "st_intersects(l.way, st_transform(st_geomfromtext('" + boundary.wkt + "',4269),3857))"
        else:
            where_clause = "st_distance(l.way, (select way from planet_osm_polygon where osm_id = " + str(
                self.ssid) + ")) <= 300000"

        # do inference for each voltage level
        all_circuits = []
        all_substations = dict()
        all_generators = dict()
        equipment_points = []
        length_found_lines = 0

        for voltage_level in self.voltage_levels.split('|'):
            (length_found_lines, equipment_points, generators, substations, circuits) = self.inference_for_voltage(
                voltage_level, where_clause, length_found_lines, equipment_points,
                all_substations, all_generators, boundary)
            all_generators.update(generators)
            all_substations.update(substations)
            all_circuits.extend(circuits)

        root.info('Total length of all found lines is %s meters', str(length_found_lines))
        equipments_multipoint = MultiPoint(equipment_points)
        map_centroid = equipments_multipoint.centroid
        logging.debug('Centroid lat:%lf, lon:%lf', map_centroid.x, map_centroid.y)
        all_circuits = Transnet.remove_duplicates(all_circuits)
        root.info('Inference took %s millies', str(datetime.now() - time))

        transnet_instance.export_to_json(all_circuits)

        partition_by_station_dict = None
        population_by_station_dict = None
        cities = None
        if self.load_estimation:
            root.info('Start partitioning into Voronoi-portions')
            load_estimator = LoadEstimator(all_substations, boundary)
            partition_by_station_dict, population_by_station_dict = load_estimator.partition()
            cities = load_estimator.cities

        if self.topology:
            root.info('Plot inferred transmission system topology')
            plotter = Plotter(self.voltage_levels)
            plotter.plot_topology(all_circuits, equipments_multipoint, partition_by_station_dict, cities, self.destdir)

        root.info('CSV generation started ...')
        csv_writer = CSVWriter(all_circuits)
        csv_writer.publish(self.destdir + '/csv')

        root.info('CIM model generation started ...')
        cim_writer = CimWriter(all_circuits, map_centroid, population_by_station_dict, self.voltage_levels)
        cim_writer.publish(self.destdir + '/cim')

        # for circuit in all_circuits:
        #     for line in circuit.members[1:-1]:
        #         if line.id not in self.all_lines:
        #             self.length_all += line.length
        #             self.all_lines[line.id] = line.id
        #
        # root.info('All lines length without duplicates %s', str(self.length_all / 1000))
        #
        # self.length_all = 0
        # for circuit in all_circuits:
        #     for line in circuit.members[1:-1]:
        #         self.length_all += line.length
        #
        # root.info('All lines length with duplicates %s', str(self.length_all / 1000))
        #
        # for circuit in all_circuits:
        #     sts = [circuit.members[0], circuit.members[-1]]
        #     for st in sts:
        #         if st.id not in self.all_stations:
        #             self.all_stations[st.id] = 1
        #         else:
        #             self.all_stations[st.id] += 1
        #
        # root.info('All Stations count %s', str(len(self.all_stations)))
        #
        # # for circuit in all_circuits:
        # #     for gen in [circuit.members[0], circuit.members[-1]]:
        # #         tags_list = [x.replace('"', "").replace('\\', "").strip() for x in
        # #                      str(gen.tags).replace(',', '=>').split('=>')]
        # #         if gen.type in ['plant', 'generator'] and not any([x.startswith('solar') for x in tags_list]):
        # #             if gen.id not in self.all_power_planet:
        # #                 self.all_power_planet[gen.id] = '%s_%s' % (gen.lat, gen.lon)
        #
        # for circuit in all_circuits:
        #     for gen in [circuit.members[0], circuit.members[-1]]:
        #
        #         if gen.type in ['plant', 'generator']:
        #             if gen.id not in self.all_power_planet:
        #                 self.all_power_planet[gen.id] = '%s_%s' % (gen.lat, gen.lon)
        #
        # root.info('All power Planets count %s', str(len(self.all_power_planet)))

        if self.validate:
            validator = InferenceValidator(self.cur)
            if boundary:
                all_stations = all_substations.copy()
                all_stations.update(all_generators)
                validator.validate2(all_circuits, all_stations, boundary, self.voltage_levels)
            else:
                validator.validate(self.ssid, all_circuits, None, self.voltage_levels)

        if self.find_missing_data:
            self.find_missing_data_for_country(where_clause)

        root.info('Took %s in total', str(datetime.now() - time))


if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option("-D", "--dbname", action="store", dest="dbname",
                      help="database name of the topology network")
    parser.add_option("-H", "--dbhost", action="store", dest="dbhost",
                      help="database host address of the topology network")
    parser.add_option("-P", "--dbport", action="store", dest="dbport",
                      help="database port of the topology network")
    parser.add_option("-U", "--dbuser", action="store", dest="dbuser",
                      help="database user name of the topology network")
    parser.add_option("-X", "--dbpwrd", action="store", dest="dbpwrd",
                      help="database user password of the topology network")
    parser.add_option("-s", "--ssid", action="store", dest="ssid",
                      help="substation id to start the inference from")
    parser.add_option("-p", "--poly", action="store", dest="poly",
                      help="poly file that defines the region to perform the inference for")
    parser.add_option("-b", "--bpoly", action="store", dest="bounding_polygon",
                      help="defines the region to perform the inference for within the specified polygon in WKT, e.g."
                           "'POLYGON((128.74 41.68, 142.69 41.68, 142.69 30.84, 128.74 30.84, 128.74 41.68))'")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      help="enable verbose logging")
    parser.add_option("-e", "--evaluate", action="store_true", dest="evaluate",
                      help="enable inference-to-existing-relation evaluation")
    parser.add_option("-t", "--topology", action="store_true", dest="topology",
                      help="enable plotting topology graph")
    parser.add_option("-V", "--voltage", action="store", dest="voltage_levels",
                      help="voltage levels in format 'level 1|...|level n', e.g. '220000|380000'")
    parser.add_option("-l", "--loadestimation", action="store_true", dest="load_estimation",
                      help="enable load estimation based on Voronoi partitions")
    parser.add_option("-d", "--destdir", action="store", dest="destdir",
                      help="destination of the inference results; "
                           "results will be stored in directory transnet/models/<destdir>")
    parser.add_option("-c", "--continent", action="store", dest="continent",
                      help="name of continent, options: 'africa', 'antarctica', 'asia', "
                           "'australia-oceania', 'central-america', 'europe', 'north-america', 'south-america' ")
    parser.add_option("-m", "--matlab", action="store", dest="matlab",
                      help="run matlab for all countries in continent modeling")
    parser.add_option("-j", "--preparejson", action="store_true", dest="prepare_json",
                      help="prepare json files of planet")
    parser.add_option("-g", "--globe", action="store_true", dest="whole_planet",
                      help="run global commmands")
    parser.add_option("-f", "--findmissing", action="store_true", dest="find_missing",
                      help="find missing data from OSM")

    (options, args) = parser.parse_args()
    # get connection data via command line or set to default values
    dbname = options.dbname
    dbhost = options.dbhost if options.dbhost else '127.0.0.1'
    dbport = options.dbport if options.dbport else '5432'
    dbuser = options.dbuser
    dbpwrd = options.dbpwrd
    ssid = options.ssid if options.ssid else '23025610'
    poly = options.poly
    bpoly = options.bounding_polygon
    verbose = options.verbose if options.verbose else False
    validate = options.evaluate if options.evaluate else False
    topology = options.topology if options.topology else False
    voltage_levels = options.voltage_levels
    load_estimation = options.load_estimation if options.load_estimation else False
    destdir = '../models/countries/' + options.destdir if options.destdir else '../results'
    continent = options.continent
    matlab = options.matlab

    # configure logging
    ch = logging.StreamHandler(sys.stdout)
    if verbose:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)
    root.addHandler(ch)

    if matlab and continent:
        if options.whole_planet:
            Transnet.run_matlab_for_continent(matlab, continent, root)
        else:
            Transnet.run_matlab_for_countries(matlab, continent, root)
        exit()

    try:
        transnet_instance = Transnet(_database=dbname, _host=dbhost, _port=dbport,
                                     _user=dbuser, _password=dbpwrd, _ssid=ssid,
                                     _poly=poly, _bpoly=bpoly, _verbose=verbose,
                                     _validate=validate, _topology=topology, _voltage_levels=voltage_levels,
                                     _load_estimation=load_estimation, _destdir=destdir, _continent=continent,
                                     _whole_planet=options.whole_planet, _find_missing_data=options.find_missing)
        if options.prepare_json and continent:
            transnet_instance.prepare_continent_json(continent)
            if options.whole_planet:
                transnet_instance.prepare_planet_json(continent)
        else:
            transnet_instance.run()
    except Exception as e:
        root.error(e.message)
        parser.print_help()
        exit()
