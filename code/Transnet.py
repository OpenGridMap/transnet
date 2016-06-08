import psycopg2
from optparse import OptionParser
from shapely import wkb, wkt
from shapely.geometry import MultiPoint
from datetime import datetime
import logging
import sys
from Circuit import Circuit
from Line import Line
from Station import Station
from CimWriter import CimWriter
from PolyParser import PolyParser
from Plotter import Plotter
from InferenceValidator import InferenceValidator
from Util import Util
from LoadEstimator import LoadEstimator

root = logging.getLogger()
root.setLevel(logging.DEBUG)

validate = False
validator = None


class Transnet:

    def __init__(self, database, user, host, port, password):
        self.connection = {'database':database, 'user':user, 'host':host, 'port':port}
        self.connect_to_DB(password)

    def get_connection_data(self):
        return self.connection
    
    def connect_to_DB(self, password):
        self.conn = psycopg2.connect(password=password, **self.connection)
        self.cur = self.conn.cursor()

    def reconnect_to_DB(self):
        msg = "Please enter the database password for \n\t database=%s, user=%s, host=%s, port=%port \nto reconnect to the database: " \
            %(str(self.connection['database']), str(self.connection['user']), str(self.connection['host']), str(self.connection['port'])) 
        password = raw_input(msg)
        self.connect_to_DB(self, password)

    @staticmethod
    def determine_circuit_voltage(relation):
        if ';' not in relation[1].voltage:
            return relation[1].voltage
        if ';' not in relation[len(relation) - 2].voltage:
            return relation[len(relation) - 2].voltage
        for line in relation[1:len(relation) - 1]:
            if ';' not in line.voltage:
                return voltage;
        first_voltage = relation[1].voltage.split(';')[0]
        root.warning('Could not determine exact voltage: Using voltage %s of %s', first_voltage, relation[1].voltage)
        return first_voltage

    @staticmethod
    def create_relations(stations, lines, ssid):
        root.info('\nStart inference for Substation %s', str(ssid))
        station_id = long(ssid)

        relations = []
        relations.extend(Transnet.infer_relations(stations, lines, stations[station_id]))

        circuits = []
        i = 1
        for relation in relations:
            if Transnet.num_subs_in_relation(relation) == 2 and len(
                    relation) >= 3:  # at least two end points + one line
                first_line = relation[1]
                circuit = Circuit(relation, Transnet.determine_circuit_voltage(relation), first_line.name, first_line.ref)
                print('Circuit ' + str(i))
                circuit.print_circuit()
                circuits.append(circuit)
                i += 1
        num_valid_circuits = len(circuits)
        if num_valid_circuits > 0:
            None
        else:
            root.info('Could not obtain any circuit')

        #for circuit in circuits:
        #    circuit.print_overpass()

        return circuits

    # inferences circuits around a given station
    # station - represents the station to infer circuits for
    # stations - dict of all possibly connected stations
    # lines - list of all lines that could connect stations
    @staticmethod
    def infer_relations(stations, lines, station):
        # find lines that cross the station's area - note that the end point of the line has to be within the substation for valid crossing
        relations = []
        for line in lines.values():
            node_to_continue = None
            if Transnet.node_in_any_station(line.end_point_dict[line.first_node()], [station], line.voltage):
                node_to_continue = line.last_node()
                covered_nodes = [line.first_node()]
            elif Transnet.node_in_any_station(line.end_point_dict[line.last_node()], [station], line.voltage):
                node_to_continue = line.first_node()
                covered_nodes = [line.last_node()]
            if node_to_continue is not None:
                line.ref = '' if line.ref is None else line.ref
                if line.id in station.covered_line_ids and not validate:
                    continue
                root.debug('%s', str(station))
                root.debug('%s', str(line))
                station.covered_line_ids.append(line.id)
                # init new circuit
                for r in line.ref.split(';'):
                    relation = [station, line]
                    relations.extend(
                        Transnet.infer_relation(stations, lines, relation, node_to_continue, line.voltage, r,
                                                line.name, line, covered_nodes))
        return relations

    # recursive function that infers electricity circuits
    # circuit - sorted member array
    # line - line of circuit
    # stations - all known stations
    @staticmethod
    def infer_relation(stations, lines, relation, node_to_continue_id, voltage, ref, name, from_line, covered_nodes):
        relation = list(relation) # make a copy
        station_id = Transnet.node_in_any_station(from_line.end_point_dict[node_to_continue_id], stations.values(), voltage)
        if station_id and station_id == relation[0].id: # if node to continue is at the starting station --> LOOP
            root.debug('Encountered loop')
            return []
        elif station_id and station_id != relation[0].id: # if a node is within another station --> FOUND THE 2nd ENDPOINT
            station = stations[station_id]
            root.debug('%s', str(station))
            if from_line.id in station.covered_line_ids and not validate:
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
            if node_to_continue_id in line.nodes:
                relation_copy = list(relation)
                if line.id == from_line.id:
                    continue
                if not Util.have_common_voltage(voltage, line.voltage):
                    continue
                if not ref:
                    ref = line.ref
                    if ref:
                        for r in ref.split(';'):
                            relations.extend(Transnet.infer_relation(stations, lines, relation_copy, node_to_continue_id, line.voltage, r,
                                                    line.name, from_line, covered_nodes))
                        return relations
                if not Transnet.ref_matches(ref, line.ref):
                    continue
                if node_to_continue_id in covered_nodes:
                    root.debug('Encountered loop - stopping inference for this line')
                    continue
                root.debug('%s', str(line))
                relation_copy.append(line)
                if line.first_node() == node_to_continue_id:
                    node_to_continue = line.last_node()
                else:
                    node_to_continue = line.first_node()
                covered_nodes_new = list(covered_nodes)
                covered_nodes_new.append(node_to_continue_id)
                relations.extend(Transnet.infer_relation(stations, lines, relation_copy, node_to_continue, voltage, ref, name, line, covered_nodes_new))

        if not relations:
            root.debug('Could not obtain circuit')
        return relations

    # returns if node is in station
    @staticmethod
    def node_in_any_station(node, stations, voltage):
        for station in stations:
            if node.intersects(station.geom) and Util.have_common_voltage(voltage, station.voltage):
                return station.id
        return None

    # returns list of existing relation ids for substation
    def existing_relations(self, station_id):
        sql = "select array_agg(id) from planet_osm_rels where ARRAY[" + str(station_id) + "]::bigint[] <@ parts and hstore(tags)->'voltage' ~ '220000|380000'"
        self.cur.execute(sql)

        result = self.cur.fetchall()
        for(ids,) in result:
            return ids

    @staticmethod
    def num_subs_in_relation(relation):
        num_stations = 0
        for way in relation:
            if isinstance(way, Station):
                num_stations+=1
        return num_stations

    @staticmethod
    def get_close_components(components, center_component):
        close_components = dict()
        for component in components:
            distance = center_component.geom.centroid.distance(component.geom.centroid)
            if distance <= 300000:
                close_components[component.id] = component
        return close_components

    # compares the ref/name tokens like 303;304 in the power line tags
    @staticmethod
    def ref_matches(circuit_ref, line_ref):
        if line_ref is None:
            return True
        for r in line_ref.split(';'):
            if Transnet.have_equal_characters(r.strip(), circuit_ref):
                return True
        return False

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
        power_string = power_string.replace(',', '.')
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
                return float(power_string)
        except ValueError:
            root.debug('Could not extract power from string %s', power_string)
            return None

    @staticmethod
    def create_relations_of_region(substations, generators, lines):
        stations = substations.copy()
        stations.update(generators)
        circuits = []
        for substation_id in substations.keys():
            close_stations_dict = Transnet.get_close_components(stations.values(), stations[substation_id])
            close_lines_dict = Transnet.get_close_components(lines.values(), stations[substation_id])
            circuits.extend(Transnet.create_relations(close_stations_dict, close_lines_dict, substation_id))
        return circuits




if __name__ == '__main__':
    
    parser = OptionParser()
    parser.add_option("-D","--dbname", action="store", dest="dbname", \
    help = "database name of the topology network")
    parser.add_option("-H","--dbhost", action="store", dest="dbhost", \
    help = "database host address of the topology network")
    parser.add_option("-P","--dbport", action="store", dest="dbport", \
    help = "database port of the topology network")
    parser.add_option("-U","--dbuser", action="store", dest="dbuser", \
    help = "database user name of the topology network")
    parser.add_option("-X","--dbpwrd", action="store", dest="dbpwrd", \
    help = "database user password of the topology network")
    parser.add_option("-s", "--ssid", action="store", dest="ssid", \
    help = "substation id to start the inference from")
    parser.add_option("-p", "--poly", action="store", dest="poly",\
    help = "poly file that defines the region to perform the inference for")
    parser.add_option("-b", "--bpoly", action="store", dest="bounding_polygon",\
    help = "defines the region to perform the inference for within the specified polygon in WKT, e.g. 'POLYGON((128.74 41.68, 142.69 41.68, 142.69 30.84, 128.74 30.84, 128.74 41.68))'")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",\
    help = "enable verbose logging")
    parser.add_option("-e", "--evaluate", action="store_true", dest="evaluate",\
    help = "enable inference-to-existing-relation evaluation")
    parser.add_option("-t", "--topology", action="store_true", dest="topology", \
    help="enable plotting topology graph")
    parser.add_option("-V", "--voltage", action="store", dest="voltage_levels", \
    help="voltage levels in format 'level 1|...|level n', e.g. '220000|380000'")
    parser.add_option("-l", "--loadestimation", action="store_true", dest="load_estimation", \
    help="enable load estimation based on Voronoi partitions")

    
    (options, args) = parser.parse_args()
    # get connection data via command line or set to default values
    dbname = options.dbname if options.dbname else 'power_de'
    dbhost = options.dbhost if options.dbhost else '127.0.0.1'
    dbport = options.dbport if options.dbport else '5432'
    dbuser = options.dbuser if options.dbuser else 'lej'
    dbpwrd = options.dbpwrd if options.dbpwrd else 'OpenGridMap'
    ssid = options.ssid if options.ssid else '23025610'
    poly = options.poly if options.poly else None
    bpoly = options.bounding_polygon if options.bounding_polygon else None
    verbose = options.verbose if options.verbose else False
    validate = options.evaluate if options.evaluate else False
    topology = options.topology if options.topology else False
    voltage_levels = options.voltage_levels if options.voltage_levels else '220000|380000'
    load_estimation = options.load_estimation if options.load_estimation else False

    ch = logging.StreamHandler(sys.stdout)
    if verbose:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)
    root.addHandler(ch)

    # Connect to DB 
    try:
        transnet_instance = Transnet(database=dbname, user=dbuser, port=dbport, host=dbhost, password=dbpwrd)
    except:
        root.error("Could not connect to database. Please check the values of host,port,user,password, and database name.")
        parser.print_help()
        exit()

    time = datetime.now()

    boundary = None
    if poly is not None:
        poly_parser = PolyParser()
        boundary = poly_parser.poly_to_polygon(poly)
        where_clause = "st_within(way, st_transform(st_geomfromtext('" + boundary.wkt + "',4269),900913))"
    elif bpoly is not None:
        boundary = wkt.loads(bpoly)
        where_clause = "st_within(way, st_transform(st_geomfromtext('" + boundary.wkt + "',4269),900913))"
    else:
        where_clause = "st_distance(way, (select way from planet_osm_polygon where osm_id = " + str(ssid) + ")) <= 300000"

    substations = dict()
    generators = dict()
    lines = dict()
    substation_points = []

    # create station dictionary by quering only ways (there are almost no node substations for voltage level 110kV and higher)
    sql = "select osm_id as id, st_transform(way, 4326) as geom, power as type, name, ref, voltage, tags, ST_Y(ST_Transform(ST_Centroid(way),4326)) as lat, ST_X(ST_Transform(ST_Centroid(way),4326)) as lon from planet_osm_polygon where power ~ 'substation|station|sub_station' and voltage ~ '" + voltage_levels + "' and " + where_clause
    transnet_instance.cur.execute(sql)
    result = transnet_instance.cur.fetchall()
    for (id, geom, type, name, ref, voltage, tags, lat, lon) in result:
        polygon = wkb.loads(geom, hex=True)
        substations[id] = Station(id, polygon, type, name, ref,
                                    voltage.replace(',', ';') if voltage is not None else None, None, tags, lat, lon)
        substation_points.append((lat, lon))
    root.info('Found %s stations', str(len(result)))
    map_centroid = MultiPoint(substation_points).centroid
    logging.debug('Centroid lat:%lf, lon:%lf', map_centroid.x, map_centroid.y)

    # add power plants with area
    sql = "select osm_id as id, st_transform(way, 4326) as geom, power as type, name, ref, voltage, \"plant:output:electricity\" as output1, \"generator:output:electricity\" as output2, tags, ST_Y(ST_Transform(ST_Centroid(way),4326)) as lat, ST_X(ST_Transform(ST_Centroid(way),4326)) as lon from planet_osm_polygon where power ~ 'plant|generator' and " + where_clause
    transnet_instance.cur.execute(sql)
    result = transnet_instance.cur.fetchall()
    for (id, geom, type, name, ref, voltage, output1, output2, tags, lat, lon) in result:
        polygon = wkb.loads(geom, hex=True)
        generators[id] = Station(id, polygon, type, name, ref,
                                    voltage.replace(',', ';') if voltage is not None else None, None, tags, lat, lon)
        generators[id].nominal_power = Transnet.parse_power(
            output1) if output1 is not None else Transnet.parse_power(output2)
    root.info('Found %s generators', str(len(result)))

    # create lines dictionary
    sql = "select l.osm_id as id, st_transform(create_line(osm_id), 4326) as geom, way as srs_geom, l.power as type, l.name, l.ref, l.voltage, l.cables, w.nodes, w.tags, st_transform(create_point(w.nodes[1]), 4326) as first_node_geom, st_transform(create_point(w.nodes[array_length(w.nodes, 1)]), 4326) as last_node_geom, ST_Y(ST_Transform(ST_Centroid(way),4326)) as lat, ST_X(ST_Transform(ST_Centroid(way),4326)) as lon from planet_osm_line l, planet_osm_ways w where l.power ~ 'line|cable|minor_line' and voltage ~ '" + voltage_levels + "' and l.osm_id = w.id and " + where_clause
    transnet_instance.cur.execute(sql)
    result = transnet_instance.cur.fetchall()
    for (id, geom, srs_geom, type, name, ref, voltage, cables, nodes, tags, first_node_geom, last_node_geom, lat, lon) in result:
        line = wkb.loads(geom, hex=True)
        srs_line = wkb.loads(srs_geom, hex=True)
        first_node = wkb.loads(first_node_geom, hex=True)
        last_node = wkb.loads(last_node_geom, hex=True)
        end_points_geom_dict = dict()
        end_points_geom_dict[nodes[0]] = first_node
        end_points_geom_dict[nodes[-1]] = last_node
        lines[id] = Line(id, line, srs_line, type, name.replace(',', ';') if name is not None else None,
                              ref.replace(',', ';') if ref is not None else None,
                              voltage.replace(',', ';') if voltage is not None else None, cables, nodes, tags, lat, lon,
                              end_points_geom_dict)
    root.info('Found %s lines', str(len(result)))

    if boundary is not None:
        circuits = Transnet.create_relations_of_region(substations, generators, lines)
    else:
        stations = substations.copy()
        stations.update(generators)
        circuits = Transnet.create_relations(stations, lines, ssid)

    if validate:
        validator = InferenceValidator(transnet_instance.cur)
        if boundary is not None:
            validator.validate2(circuits, boundary)
        else:
            validator.validate(ssid, circuits, None)

    root.info('Infernece took %s millies', str(datetime.now() - time))

    root.info('CIM model generation started ...')
    cim_writer = CimWriter(circuits, map_centroid)
    cim_writer.publish('../results/cim')

    voronoi_partitions = None
    if load_estimation:
        root.info('Start partitioning into Voronoi-partions')
        load_estimator = LoadEstimator()
        voronoi_partitions = load_estimator.partition(substations)

    if topology:
        root.info('Plot inferred transmission system topology')
        plotter = Plotter(voltage_levels)
        plotter.plot_topology(circuits, boundary, voronoi_partitions)

    root.info('Took %s millies in total', str(datetime.now() - time))
