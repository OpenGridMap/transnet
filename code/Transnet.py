"""							         
Copyright "2015" "NEXT ENERGY"						  
										  
Licensed under the Apache License, Version 2.0 (the "License");		  
you may not use this file except in compliance with the License.	  
You may obtain a copy of the License at					  
										  
http://www.apache.org/licenses/LICENSE-2.0				  

Unless required by applicable law or agreed to in writing, software	  
distributed under the License is distributed on an "AS IS" BASIS,	  
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  
See the License for the specific language governing permissions and	  
limitations under the License.
"""

import psycopg2
from optparse import OptionParser
from Circuit import Circuit
from Line import Line
from Station import Station
from shapely import wkb
from datetime import datetime

class Transnet:
    stations = dict()
    lines = dict()

    def __init__(self, database, user, host, port, password):
        # Initializes the SciGRID class with the database connection parameters.
        # These parameters are: database name, database user, database password, database host and port. 
        # Notice: The password will not be stored.

        self.connection = {'database':database, 'user':user, 'host':host, 'port':port}
        self.connect_to_DB(password)

    def get_connection_data(self):
	# Obtain the database connection parameters. 
        return self.connection
    
    def connect_to_DB(self, password):
	# Establish the database connection. 
        self.conn = psycopg2.connect(password=password, **self.connection)
        self.cur = self.conn.cursor()

    def reconnect_to_DB(self):
	# Reconnect to the database if connection got lost. 
        msg = "Please enter the database password for \n\t database=%s, user=%s, host=%s, port=%port \nto reconnect to the database: " \
            %(str(self.connection['database']), str(self.connection['user']), str(self.connection['host']), str(self.connection['port'])) 
        password = raw_input(msg)
        self.connect_to_DB(self, password)

    def create_relations(self):
        # create station dictionary
        sql = "select id,create_polygon(id) as geom, hstore(tags)->'power' as type, hstore(tags)->'name' as name, hstore(tags)->'ref' as ref, hstore(tags)->'voltage' as voltage, nodes,tags from planet_osm_ways where hstore(tags)->'power'~'station|substation|sub_station|plant|generator' and array_length(nodes, 1) >= 4 and st_isclosed(create_line(id)) and hstore(tags)->'voltage' ~ '110000|220000|380000'"
        self.cur.execute(sql)
        result = self.cur.fetchall()
        for (id, geom, type, name, ref, voltage, nodes, tags) in result:
            polygon = wkb.loads(geom, hex=True)
            self.stations[id] = Station(id, polygon, type, name, ref, voltage, nodes, tags)
        print('Found ' + str(len(self.stations)) + ' stations')

        # create lines dictionary
        sql =   """
                select id, create_line(id) as geom, hstore(tags)->'power' as type, hstore(tags)->'name' as name, hstore(tags)->'ref' as ref, hstore(tags)->'voltage' as voltage, hstore(tags)->'cables' as cables, nodes, tags
                from planet_osm_ways where hstore(tags)->'power'~'line|cable|minor_line' and exist(hstore(tags),'voltage') and hstore(tags)->'voltage' ~ '110000|220000|380000';
                """
        self.cur.execute(sql)
        result = self.cur.fetchall()
        for (id, geom, type, name, ref, voltage, cables, nodes,tags) in result:
            line = wkb.loads(geom, hex=True)
            self.lines[id] = Line(id, line, type, name, ref, voltage, cables, nodes, tags)
        print('Found ' + str(len(self.lines)) + ' lines')
        print('')

        #for id in stations:
        relations = []
        relations.extend(self.infer_relations(self.stations[137197826]))

        # post-process circuits and identify corrupt circuits
        corrupt_relations = []
        i = 1
        for relation in relations:
            if self.num_subs_in_relation(relation) == 2 and len(relation) >= 3: # at least two end points + one line

                # extend valid relations with busbars
                first_station = relation[0]
                first_line = relation[1]
                second_station = relation[len(relation) - 1]
                second_line = relation[len(relation) - 2]
                
                if self.node_in_any_station(first_line.first_node(), [first_station], first_line.voltage):
                    node_to_continue_id = first_line.first_node()
                else:
                    node_to_continue_id = first_line.last_node()

                busbars = self.extend_relation_endpoint(node_to_continue_id, first_line, 0)
                if busbars:
                    relation.insert(0, busbars)

                if self.node_in_any_station(second_line.first_node(), [second_station], second_line.voltage):
                    node_to_continue_id = second_line.first_node()
                else:
                    node_to_continue_id = second_line.last_node()

                busbars = self.extend_relation_endpoint(node_to_continue_id, second_line, 1)
                if busbars:
                    relation.append(busbars)

                circuit = Circuit(relation, first_line.voltage, first_line.name, first_line.ref)
                print('Circuit ' + str(i))
                circuit.print_circuit()
                print('')
                i+=1
            else:
                corrupt_relations.append(relation)

        print('##### Corrupt circuits #####')
        i = 1
        for relation in corrupt_relations:
            print('Circuit ' + str(i))
            Circuit.print_relation(relation)
            print('')
            i+=1
        return

    # inferences circuits around a given station
    # station - represents the station to infer circuits for
    # stations - dict of all possibly connected stations
    # lines - list of all lines that could connect stations
    def infer_relations(self, station):
        close_stations = self.get_close_stations(station.id)

        # find lines that cross the station's area - note that the end point of the line has to be within the substation for valid crossing
        relations = []
        for line in self.lines.values():
            line_crosses_station = station.geom.crosses(line.geom)
            first_node_in_station = self.node_in_any_station(line.first_node(), [station], line.voltage)
            last_node_in_station = self.node_in_any_station(line.last_node(), [station], line.voltage)
            if line_crosses_station and (first_node_in_station or last_node_in_station):
                if line.id not in station.covered_line_ids:
                    print(str(station))
                    print(str(line))
                    station.covered_line_ids.append(line.id)
                    # init new circuit
                    relation = [station, line]
                    if first_node_in_station:
                        node_to_continue = line.last_node()
                        covered_nodes = [line.first_node()]
                    else:
                        node_to_continue = line.first_node()
                        covered_nodes = [line.last_node()]
                    relation = self.infer_relation(relation, node_to_continue, line, line, close_stations, covered_nodes)
                    if relation is not None:
                        relations.append(relation)
        return relations

    # recursive function that infers electricity circuits
    # circuit - sorted member array
    # line - line of circuit
    # stations - all known stations
    def infer_relation(self, relation, node_to_continue_id, starting_line, from_line, close_stations, covered_nodes):
        station_id = self.node_in_any_station(node_to_continue_id, close_stations, starting_line.voltage)
        if station_id and station_id == relation[0].id: # if node to continue is at the starting station --> LOOP
            print('Encountered loop')
            print('')
            return relation
        elif station_id and station_id != relation[0].id: # if a node is within another station --> FOUND THE 2nd ENDPOINT
            station = self.stations[station_id]
            print(str(station))
            if from_line.id in station.covered_line_ids:
                print('Relation with ' + str(from_line) + ' at ' + str(station) + ' already covered')
                print('')
                return None
            station.covered_line_ids.append(from_line.id)
            relation.append(station)
            print('Could obtain relation')
            print('')
            return relation

        # no endpoints encountered - handle line subsection
        # at first find all lines that cover the node to continue
        node_covering_lines = []
        for line in self.lines.values():
            if node_to_continue_id in line.nodes:
                node_covering_lines.append(line)

        for line in node_covering_lines:
            if line.id == from_line.id:
                continue
            if not Transnet.have_common_voltage(starting_line.voltage, line.voltage):
                continue
            if not self.ref_matches(starting_line, line):
                continue
            if node_to_continue_id in covered_nodes:
                print('Encountered loop - stopping inference for this line')
                print('')
                return relation
            print(str(line))
            relation.append(line)
            if line.first_node() == node_to_continue_id:
                node_to_continue = line.last_node()
            else:
                node_to_continue = line.first_node()
            covered_nodes.append(node_to_continue_id)
            return self.infer_relation(relation, node_to_continue, starting_line, line, close_stations, covered_nodes)

        print('Error - could not obtain circuit')
        print('')
        return relation

    # returns if node is in station
    def node_in_any_station(self, node_id, stations, voltage):
        sql = " select create_point(id) as point from planet_osm_nodes where id = " + str(node_id) + ";"
        self.cur.execute(sql)

        result = self.cur.fetchall()
        for(point,) in result:
            node = wkb.loads(point, hex=True)
        for station in stations:
            if node.within(station.geom) and Transnet.have_common_voltage(voltage, station.voltage):
                return station.id
        return None

    def num_subs_in_relation(self, relation):
        num_stations = 0
        for way in relation:
            if isinstance(way, Station):
                num_stations+=1
        return num_stations

    # compares the ref/name tokens like 303;304 in the power line tags
    def ref_matches(self, starting_line, current_line):
        result = [self.compare_refs(starting_line.ref, current_line.ref),
                      self.compare_refs(starting_line.ref, current_line.name),
                      self.compare_refs(starting_line.name, current_line.ref),
                      self.compare_refs(starting_line.name, current_line.name)]
        lists = map(list, zip(*result))
        both_had_numeric_tokens = reduce(lambda x,y: x or y, lists[0], False)
        refs_matched = reduce(lambda x,y: x or y, lists[1], False)
        if not both_had_numeric_tokens:
            return True
        return refs_matched

    @staticmethod
    def compare_refs(ref1, ref2):
        ref1_has_digit_token = False
        ref2_has_digit_token = False
        tokens_match = False
        if ref1 is None or ref2 is None:
            return False, False
        split_char_1 = ';'
        if ',' in ref1:
            split_char_1 = ','
        split_char_2 = ';'
        if ',' in ref2:
            split_char_2 = ','
        for token1 in ref1.split(split_char_1):
            if token1.isdigit():
                ref1_has_digit_token = True
            for token2 in ref2.split(split_char_2):
                if token2.isdigit():
                    ref2_has_digit_token = True
                if token1.isdigit() and token2.isdigit() and token1.strip() == token2.strip():
                    tokens_match = True
                    break
        return ref1_has_digit_token and ref2_has_digit_token, tokens_match

    @staticmethod
    def have_common_voltage(vstring1, vstring2):
        for v1 in vstring1.split(';'):
            for v2 in vstring2.split(';'):
                if v1.strip() == v2.strip():
                    return True
        return False

    def get_close_stations(self, station_id):
        close_stations = []
        for station in self.stations.values():
            distance = station.geom.centroid.distance(station.geom.centroid)
            if distance <= 300000:
                close_stations.append(station)
        return close_stations

    # extend relations with busbars
    def extend_relation_endpoint(self, node_to_continue_id, from_line, append=1):
        node_covering_lines = []
        for line in self.lines.values():
            if node_to_continue_id in line.nodes:
                node_covering_lines.append(line)

        for line in node_covering_lines:
            if line.id == from_line.id:
                continue
            if node_to_continue_id == line.first_node():
                node_to_continue_id = line.last_node()
            else:
                node_to_continue_id = line.first_node()
            if append:
                return [line].append(self.extend_relation_endpoint(node_to_continue_id, line, append))
            else:
                return [line].insert(0, self.extend_relation_endpoint(node_to_continue_id, line, append))
        return []
        
if __name__ == '__main__':
    
    parser=OptionParser()
    parser.add_option("-D","--dbname", action="store", dest="dbname", \
    help="database name of the topology network")
    parser.add_option("-H","--dbhost", action="store", dest="dbhost", \
    help="database host address of the topology network")
    parser.add_option("-P","--dbport", action="store", dest="dbport", \
    help="database port of the topology network")
    parser.add_option("-U","--dbuser", action="store", dest="dbuser", \
    help="database user name of the topology network")
    parser.add_option("-X","--dbpwrd", action="store", dest="dbpwrd", \
    help="database user password of the topology network")
    
    (options, args) = parser.parse_args()
    # get connection data via command line or set to default values
    dbname = options.dbname if options.dbname else 'de_power_151125_de2'
    dbhost = options.dbhost if options.dbhost else '127.0.0.1'
    dbport = options.dbport if options.dbport else '5432'
    dbuser = options.dbuser if options.dbuser else 'postgres' 
    dbpwrd = options.dbpwrd if options.dbpwrd else 'open50arms'
 
    # Connect to DB 
    try:
        transnet_instance = Transnet(database=dbname, user=dbuser, port=dbport, host=dbhost, password=dbpwrd)
    except:
        print "Could not connect to database. Please check the values of host,port,user,password, and database name."
        parser.print_help()
        exit()

    time = datetime.now()
    transnet_instance.create_relations()
    print('Took ' + str(datetime.now() - time) + ' millies')

    
    
