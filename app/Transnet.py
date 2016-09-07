import json
import logging
import sys
import urllib
from datetime import datetime
from optparse import OptionParser
from os import makedirs
from os.path import exists
from os.path import isfile
from os.path import dirname
from os.path import join
from os import walk
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
    conn = None
    cur = None
    conn_export = None
    cur_export = None
    ssid = None
    poly = None
    bpoly = None
    verbose = None
    validate = None
    topology = None
    voltage_levels = None
    load_estimation = None
    destdir = None
    continent = None
    root = None
    db_name = None

    def __init__(self, database, export_database, user, host, port, password, ssid, poly, bpoly, verbose, validate,
                 topology, voltage_levels, load_estimation, destdir, continent, root):
        self.db_name = database
        self.connection = {'database': database, 'user': user, 'host': host, 'port': port}
        # self.export_connection = {'database': export_database, 'user': user, 'host': host, 'port': port}
        self.connect_to_DB(password)
        self.ssid = ssid
        self.poly = poly
        self.bpoly = bpoly
        self.verbose = verbose
        self.validate = validate
        self.topology = topology
        self.voltage_levels = voltage_levels
        self.load_estimation = load_estimation
        self.destdir = destdir
        self.continent = continent
        self.root = root

    def get_connection_data(self):
        return self.connection

    def connect_to_DB(self, password):
        self.conn = psycopg2.connect(password=password, **self.connection)
        self.cur = self.conn.cursor()
        # self.conn_export = psycopg2.connect(password=password, **self.export_connection)
        # self.cur_export = self.conn_export.cursor()

    def reconnect_to_DB(self):
        msg = "Please enter the database password for \n\t database=%s, user=%s, host=%s, port=%port \nto reconnect to the database: " \
              % (str(self.connection['database']), str(self.connection['user']), str(self.connection['host']),
                 str(self.connection['port']))
        password = raw_input(msg)
        self.connect_to_DB(self, password)

    def run(self):
        if self.continent:
            with open('meta/{0}.json'.format(continent)) as continent_file:
                continent_json = json.load(continent_file)
                for country in continent_json:
                    try:
                        self.voltage_levels = continent_json[country]['voltages']
                        if self.voltage_levels:
                            self.prepare_poly(continent, country)
                            self.poly = '../data/{0}/{1}/pfile.poly'.format(continent, country)
                            self.destdir = '../models/{0}/{1}/'.format(continent, country)
                            Transnet.reset_params()
                            self.modeling(country)
                    except Exception as e:
                        root.error(e)
        else:
            self.modeling(self.db_name)

    def prepare_poly(self, continent, country):
        if not exists('../data/{0}/{1}/'.format(continent, country)):
            makedirs('../data/{0}/{1}/'.format(continent, country))
        self.root.info('Downloading poly for {0}'.format(country))
        urllib.URLopener().retrieve('http://download.geofabrik.de/{0}/{1}.poly'.format(continent, country),
                                    '../data/{0}/{1}/pfile.poly'.format(continent, country))

    @staticmethod
    def reset_params():
        Transnet.covered_nodes = None

    def modeling(self, country_name):
        # create dest dir
        if not exists(self.destdir):
            makedirs(self.destdir)

        root.info('Infer for %s', country_name)

        time = datetime.now()

        # build location where clause for succeeding queries
        boundary = None
        if self.poly:
            poly_parser = PolyParser()
            boundary = poly_parser.poly_to_polygon(self.poly)
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
            root.info('Infer net for voltage level %sV', voltage_level)

            substations = dict()
            generators = dict()
            lines = dict()

            # create lines dictionary
            sql = "SELECT l.osm_id AS id, st_transform(create_line(l.osm_id), 4326) AS geom, l.way AS srs_geom, l.power AS type, l.name, l.ref, l.voltage, l.cables, w.nodes, w.tags, st_transform(create_point(w.nodes[1]), 4326) AS first_node_geom, st_transform(create_point(w.nodes[array_length(w.nodes, 1)]), 4326) AS last_node_geom, ST_Y(ST_Transform(ST_Centroid(l.way),4326)) AS lat, ST_X(ST_Transform(ST_Centroid(l.way),4326)) AS lon, st_length(st_transform(l.way, 4326), TRUE) AS spheric_length FROM planet_osm_line l, planet_osm_ways w WHERE l.osm_id >= 0 AND l.power ~ 'line|cable|minor_line' AND l.voltage ~ '" + voltage_level + "' AND l.osm_id = w.id AND " + where_clause

            self.cur.execute(sql)
            result = self.cur.fetchall()
            for (
                    id, geom, srs_geom, type, name, ref, voltage, cables, nodes, tags, first_node_geom, last_node_geom,
                    lat,
                    lon,
                    length) in result:
                line = wkb.loads(geom, hex=True)
                raw_geom = geom
                srs_line = wkb.loads(srs_geom, hex=True)
                length_found_lines += length
                first_node = wkb.loads(first_node_geom, hex=True)
                last_node = wkb.loads(last_node_geom, hex=True)
                end_points_geom_dict = dict()
                end_points_geom_dict[nodes[0]] = first_node
                end_points_geom_dict[nodes[-1]] = last_node
                lines[id] = Line(id, line, srs_line, type, name.replace(',', ';') if name is not None else None,
                                 ref.replace(',', ';') if ref is not None else None,
                                 voltage.replace(',', ';').replace('/', ';') if voltage is not None else None, cables,
                                 nodes, tags, lat, lon,
                                 end_points_geom_dict, length, raw_geom)
                equipment_points.append((lat, lon))
            root.info('Found %s lines', str(len(result)))

            # create station dictionary by quering only ways (there are almost no node substations for voltage level 110kV and higher)
            sql = "SELECT DISTINCT(p.osm_id) AS id, st_transform(p.way, 4326) AS geom, p.power AS type, p.name, p.ref, p.voltage, p.tags, ST_Y(ST_Transform(ST_Centroid(p.way),4326)) AS lat, ST_X(ST_Transform(ST_Centroid(p.way),4326)) AS lon FROM planet_osm_line l, planet_osm_polygon p WHERE l.osm_id >= 0 AND p.osm_id >= 0 AND p.power ~ 'substation|station|sub_station' AND (p.voltage ~ '" + self.voltage_levels + "' OR (p.voltage = '') IS NOT FALSE) AND st_intersects(l.way, p.way) AND l.power ~ 'line|cable|minor_line' AND l.voltage ~ '" + voltage_level + "' AND " + where_clause

            self.cur.execute(sql)
            result = self.cur.fetchall()
            for (id, geom, type, name, ref, voltage, tags, lat, lon) in result:
                if id not in all_substations:
                    polygon = wkb.loads(geom, hex=True)
                    raw_geom = geom
                    substations[id] = Station(id, polygon, type, name, ref,
                                              voltage.replace(',', ';').replace('/',
                                                                                ';') if voltage is not None else None,
                                              None, tags, lat,
                                              lon, raw_geom)
                    equipment_points.append((lat, lon))
                else:
                    substations[id] = all_substations[id]

            root.info('Found %s stations', str(len(equipment_points)))

            # add power plants with area
            sql = "SELECT DISTINCT(p.osm_id) AS id, st_transform(p.way, 4326) AS geom, p.power AS type, p.name, p.ref, p.voltage, p.\"plant:output:electricity\" AS output1, p.\"generator:output:electricity\" AS output2, p.tags, ST_Y(ST_Transform(ST_Centroid(p.way),4326)) AS lat, ST_X(ST_Transform(ST_Centroid(p.way),4326)) AS lon FROM planet_osm_line l, planet_osm_polygon p WHERE l.osm_id >= 0 AND p.osm_id >= 0 AND p.power ~ 'plant|generator' AND st_intersects(l.way, p.way) AND l.power ~ 'line|cable|minor_line' AND l.voltage ~ '" + voltage_level + "' AND " + where_clause

            self.cur.execute(sql)
            result = self.cur.fetchall()
            for (id, geom, type, name, ref, voltage, output1, output2, tags, lat, lon) in result:
                if id not in all_generators:
                    polygon = wkb.loads(geom, hex=True)
                    raw_geom = geom
                    generators[id] = Station(id, polygon, type, name, ref,
                                             voltage.replace(',', ';').replace('/',
                                                                               ';') if voltage is not None else None,
                                             None, tags, lat,
                                             lon, raw_geom)
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
            all_generators.update(generators)
            all_substations.update(substations)
            all_circuits.extend(circuits)

        root.info('Total length of all found lines is %s meters', str(length_found_lines))
        equipments_multipoint = MultiPoint(equipment_points)
        map_centroid = equipments_multipoint.centroid
        logging.debug('Centroid lat:%lf, lon:%lf', map_centroid.x, map_centroid.y)
        all_circuits = Transnet.remove_duplicates(all_circuits)
        root.info('Inference took %s millies', str(datetime.now() - time))

        # transnet_instance.export_to_db(all_circuits, dbname)

        partition_by_station_dict = None
        population_by_station_dict = None
        cities = None
        if self.load_estimation:
            root.info('Start partitioning into Voronoi-partions')
            load_estimator = LoadEstimator(all_substations, boundary)
            partition_by_station_dict, population_by_station_dict = load_estimator.partition()
            cities = load_estimator.cities

        if self.topology:
            root.info('Plot inferred transmission system topology')
            plotter = Plotter(self.voltage_levels)
            plotter.plot_topology(all_circuits, equipments_multipoint, partition_by_station_dict, cities, self.destdir)

        root.info('CIM model generation started ...')
        cim_writer = CimWriter(all_circuits, map_centroid, population_by_station_dict, self.voltage_levels)
        cim_writer.publish(self.destdir + '/cim')

        root.info('CSV generation started ...')
        csv_writer = CSVWriter(all_circuits)
        csv_writer.publish(self.destdir + '/csv')

        if validate:
            validator = InferenceValidator(self.cur)
            if boundary is not None:
                all_stations = all_substations.copy()
                all_stations.update(all_generators)
                validator.validate2(all_circuits, all_stations, boundary, self.voltage_levels)
            else:
                validator.validate(self.ssid, all_circuits, self.voltage_levels)

        root.info('Took %s in total', str(datetime.now() - time))

    @staticmethod
    def determine_circuit_voltage(relation):
        if ';' not in relation[1].voltage and relation[1].voltage is not None:
            return relation[1].voltage
        if ';' not in relation[-2].voltage and relation[2].voltage is not None:
            return relation[-2].voltage
        for line in relation[1:len(relation) - 1]:
            if ';' not in line.voltage and line.voltage is not None:
                return line.voltage;
        first_voltage = relation[1].voltage.split(';')[0]
        root.warning('Could not determine exact voltage: Using voltage %s of %s', first_voltage, relation[1].voltage)
        return first_voltage

    @staticmethod
    def create_relations(stations, lines, ssid, voltage):
        # root.info('\nStart inference for Substation %s', str(ssid))
        station_id = long(ssid)

        relations = []
        relations.extend(Transnet.infer_relations(stations, lines, stations[station_id]))

        circuits = []
        i = 1
        for relation in relations:
            if Transnet.num_subs_in_relation(relation) == 2 and len(
                    relation) >= 3:  # at least two end points + one line

                first_line = relation[1]
                station1 = relation[0]
                station2 = relation[-1]
                station1.add_connected_station(station2.id, voltage)
                station2.add_connected_station(station1.id, voltage)

                circuit = Circuit(relation, voltage, first_line.name, first_line.ref)
                # print('Circuit ' + str(i))
                # circuit.print_circuit()
                circuits.append(circuit)
                i += 1
        num_valid_circuits = len(circuits)
        # if num_valid_circuits > 0:
        #     None
        # else:
        #     root.info('Could not obtain any circuit')

        # for circuit in circuits:
        #    circuit.print_overpass()

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
            if node_to_continue_id is not None:
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
        elif station_id and station_id != start_station.id:  # if a node is within another station --> FOUND THE 2nd ENDPOINT
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

    # returns list of existing relation ids for substation
    def existing_relations(self, station_id):
        sql = "SELECT array_agg(id) FROM planet_osm_rels WHERE ARRAY[" + str(
            station_id) + "]::BIGINT[] <@ parts AND hstore(tags)->'voltage' ~ '220000|380000'"
        self.cur.execute(sql)

        result = self.cur.fetchall()
        for (ids,) in result:
            return ids

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

    # sometimes refs are modeled with 12A or A12, which is the same
    @staticmethod
    def have_equal_characters(str1, str2):
        for c1 in str1:
            if c1 not in str2:
                return False
        return True

    @staticmethod
    def parse_power(power_string):
        if power_string is None:
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
            station2 = circuit.members[- 1]
            for line in circuit.members[1:-1]:
                total_line_length += line.length
            if str(station1.id) + str(station2.id) + str(circuit.voltage) in covered_connections or str(
                    station2.id) + str(
                station1.id) + str(circuit.voltage) in covered_connections:
                continue
            covered_connections.append(str(station1.id) + str(station2.id) + str(circuit.voltage))
            filtered_circuits.append(circuit)
        root.info('%s circuits remain', str(len(filtered_circuits)))
        root.info('Line length with duplicates is %s meters', str(total_line_length))
        return filtered_circuits

    def export_to_db(self, circuits, country):
        root.info('Exporting circuits to DB')
        self.cur_export.execute("DELETE FROM power_line WHERE country='{0}';".format(country))
        self.cur_export.execute("DELETE FROM power_station WHERE country='{0}';".format(country))
        self.conn_export.commit()

        for circuit in circuits:
            self.insert_station(circuit.members[0], country)
            self.insert_station(circuit.members[- 1], country)
            for line in circuit.members[1:-1]:
                self.insert_line(line, country)

    def insert_station(self, station, country):
        insert_sql = "INSERT INTO power_station ( name, voltage, lon, lat, power_type, country, poly) VALUES ('{0}','{1}',{2}, {3}, '{4}', '{5}', '{6}')".format(
            station.name.replace("'", '') if station.name else None,
            station.voltage,
            station.lon,
            station.lat,
            station.type,
            country,
            station.raw_geom,
        )
        self.cur_export.execute(insert_sql)
        self.conn_export.commit()

    def insert_line(self, line, country):
        insert_sql = "INSERT INTO power_line (name, voltage, lon, lat, power_type, country, line_string) VALUES ('{0}', '{1}' , {2}, {3}, '{4}', '{5}', '{6}')".format(
            line.name.replace("'", '') if line.name  else None,
            line.voltage,
            line.lon,
            line.lat,
            line.type,
            country,
            line.raw_geom,
        )

        self.cur_export.execute(insert_sql)
        self.conn_export.commit()

    @staticmethod
    def run_matlab_for_continent(matlab, continent_folder, root_log):
        dirs = [x[0] for x in walk(join(dirname(__file__), '../models/{0}/'.format(continent_folder)))]
        matlab_dir = join(dirname(__file__), '../matlab')
        for dir in dirs[1:]:
            try:
                country = dir.split('/')[-1]
                log_dir = join(dirname(__file__), '../logs/{0}/{1}'.format(continent_folder, country))
                if not exists(log_dir):
                    makedirs(log_dir)

                command = 'cd {0} && {1} -r "transform {2}/{3};quit;"| tee ../logs/{2}/{3}/transnet_matlab.log' \
                    .format(matlab_dir, matlab, continent, country)
                root_log.info('running MATLAB modeling for {0}'.format(country))
                return_code = call(command, shell=True)
                root_log.info('MATLAB return code {0}'.format(return_code))
            except Exception as e:
                root_log.error(e)

    @staticmethod
    def try_parse_int(string):
        try:
            return int(string)
        except ValueError:
            return 0

    def prepare_planet_json(self, continent):

        with open('meta/{0}.json'.format(continent), 'r+') as continent_file:
            continent_json = json.load(continent_file)
            for country in continent_json:
                self.prepare_poly(continent, country)
                poly_parser = PolyParser()
                boundary = poly_parser.poly_to_polygon('../data/{0}/{1}/pfile.poly'.format(continent, country))
                where_clause = "st_intersects(l.way, st_transform(st_geomfromtext('" + boundary.wkt + "',4269),3857))"
                voltages = set()
                voltages_string = ''
                first_round = True
                sql = "SELECT DISTINCT(voltage) AS voltage, count(*) AS num FROM planet_osm_line  l WHERE " + where_clause + " GROUP BY voltage ORDER BY num DESC"
                self.cur.execute(sql)
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
                continent_json[country]['voltages'] = voltages_string
            continent_file.seek(0)
            continent_file.write(json.dumps(continent_json, indent=4))
            continent_file.truncate()


if __name__ == '__main__':

    parser = OptionParser()
    parser.add_option("-D", "--dbname", action="store", dest="dbname", \
                      help="database name of the topology network")
    parser.add_option("-E", "--export", action="store", dest="export_dbname", \
                      help="database name of export data")
    parser.add_option("-H", "--dbhost", action="store", dest="dbhost", \
                      help="database host address of the topology network")
    parser.add_option("-P", "--dbport", action="store", dest="dbport", \
                      help="database port of the topology network")
    parser.add_option("-U", "--dbuser", action="store", dest="dbuser", \
                      help="database user name of the topology network")
    parser.add_option("-X", "--dbpwrd", action="store", dest="dbpwrd", \
                      help="database user password of the topology network")
    parser.add_option("-s", "--ssid", action="store", dest="ssid", \
                      help="substation id to start the inference from")
    parser.add_option("-p", "--poly", action="store", dest="poly", \
                      help="poly file that defines the region to perform the inference for")
    parser.add_option("-b", "--bpoly", action="store", dest="bounding_polygon", \
                      help="defines the region to perform the inference for within the specified polygon in WKT, e.g. "
                           "'POLYGON((128.74 41.68, 142.69 41.68, 142.69 30.84, 128.74 30.84, 128.74 41.68))'")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", \
                      help="enable verbose logging")
    parser.add_option("-e", "--evaluate", action="store_true", dest="evaluate", \
                      help="enable inference-to-existing-relation evaluation")
    parser.add_option("-t", "--topology", action="store_true", dest="topology", \
                      help="enable plotting topology graph")
    parser.add_option("-V", "--voltage", action="store", dest="voltage_levels", \
                      help="voltage levels in format 'level 1|...|level n', e.g. '220000|380000'")
    parser.add_option("-l", "--loadestimation", action="store_true", dest="load_estimation", \
                      help="enable load estimation based on Voronoi partitions")
    parser.add_option("-d", "--destdir", action="store", dest="destdir", \
                      help="destination of the inference results; results will be stored in directory transnet/models/<destdir>")
    parser.add_option("-c", "--continent", action="store", dest="continent", \
                      help="name of continent, options: 'africa', 'antarctica', 'asia', "
                           "'australia-oceania', 'central-america', 'europe', 'north-america', 'south-america' ")
    parser.add_option("-m", "--matlab", action="store", dest="matlab", \
                      help="run matlab for all countries in continent modeling")
    parser.add_option("-j", "--preparejson", action="store_true", dest="prepare_json", \
                      help="prepare json files of planet")

    (options, args) = parser.parse_args()
    # get connection data via command line or set to default values
    dbname = options.dbname if options.dbname else 'germany'
    export_dbname = options.export_dbname if options.export_dbname else 'transnetdjango'
    dbhost = options.dbhost if options.dbhost else '127.0.0.1'
    dbport = options.dbport if options.dbport else '5432'
    dbuser = options.dbuser if options.dbuser else 'lej'
    dbpwrd = options.dbpwrd if options.dbpwrd else 'OpenGridMap'
    ssid = options.ssid if options.ssid else '23025610'
    poly = options.poly
    bpoly = options.bounding_polygon
    verbose = options.verbose if options.verbose else False
    validate = options.evaluate if options.evaluate else False
    topology = options.topology if options.topology else False
    voltage_levels = options.voltage_levels if options.voltage_levels else '220000|380000'
    load_estimation = options.load_estimation if options.load_estimation else False
    destdir = '../models/' + options.destdir if options.destdir else '../results'
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
        Transnet.run_matlab_for_continent(matlab, continent, root)
        exit()

    # Connect to DB
    try:
        transnet_instance = Transnet(database=dbname, export_database=export_dbname, host=dbhost, port=dbport,
                                     user=dbuser, password=dbpwrd, ssid=ssid, poly=poly, bpoly=bpoly, verbose=verbose,
                                     validate=validate, topology=topology, voltage_levels=voltage_levels,
                                     load_estimation=load_estimation, destdir=destdir, continent=continent, root=root)
        if options.prepare_json and continent:
            transnet_instance.prepare_planet_json(continent)
        else:
            transnet_instance.run()
    except Exception as e:
        root.error(e)
        parser.print_help()
        exit()
