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
from Line import Line
from Station import Station
from shapely import wkb
from datetime import datetime

class Transnet:

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
        stations = dict()
        sql = "select id,create_polygon(id) as geom,hstore(tags)->'name' as name, hstore(tags)->'power' as type, nodes,tags from planet_osm_ways where hstore(tags)->'power'~'station|substation|sub_station|plant|generator' and array_length(nodes, 1) >= 4 and st_isclosed(create_line(id))"
        self.cur.execute(sql)
        result = self.cur.fetchall()
        for (id,geom,name,type,nodes,tags) in result:
            polygon = wkb.loads(geom, hex=True)
            stations[id] = Station(id,polygon,type,name,nodes,tags)
        print('Found ' + str(len(stations)) + ' stations')

        lines = dict()
        sql =   """
                select id, create_line(id) as geom, hstore(tags)->'voltage' as voltage, hstore(tags)->'power' as type, hstore(tags)->'cables' as cables, hstore(tags)->'name' as name, hstore(tags)->'ref' as ref, nodes, tags
                from planet_osm_ways where hstore(tags)->'power'~'line|cable|minor_line' and exist(hstore(tags),'voltage');
                """
        self.cur.execute(sql)
        result = self.cur.fetchall()
        for (id,geom,voltage,type,cables,name,ref,nodes,tags) in result:
            line = wkb.loads(geom, hex=True)
            lines[id] = Line(id,line,type,voltage,cables,name,ref,nodes,tags)
        print('Found ' + str(len(lines)) + ' lines')
        print('')

        #for id in stations:
        circuits = []
        circuits.extend(self.infer_circuits(stations[137197826],stations,lines))

        corrupt_circuits = []
        i = 1
        for circuit in circuits:
            if self.num_subs_in_circuit(circuit) < 2:
                corrupt_circuits.append(circuit)
            else:
                print('Circuit ' + str(i))
                self.print_circuit(circuit)
                i+=1

        print('##### Corrupt circuits #####')
        i = 1
        for circuit in corrupt_circuits:
            print('Circuit ' + str(i))
            self.print_circuit(circuit)
            i+=1
        return

    def infer_circuits(self, station, stations, lines):
        close_stations = self.get_close_stations(station.id, stations)

        circuits = []
        crossing_not_covered_lines = []
        for line_id in lines:
            if lines[line_id].geom.crosses(station.geom):
                if line_id not in station.covered_line_ids:
                    crossing_not_covered_lines.append(lines[line_id])

        for line in crossing_not_covered_lines:
            print(str(station))
            print(str(line))
            station.covered_line_ids.append(line.id)
            circuit = [station, line]
            temp_stations = dict()
            temp_stations[station.id] = station
            if self.node_in_station(line.first_node(), temp_stations):
                node_to_continue = line.last_node()
                covered_nodes = [line.first_node()]
            else:
                node_to_continue = line.first_node()
                covered_nodes = [line.last_node()]
            circuit = self.infer_circuit(circuit,node_to_continue,line,line,stations,close_stations,lines,covered_nodes)
            if circuit is not None:
                circuits.append(circuit)
        return circuits

    # recursive function that infers electricity circuits
    # circuit - sorted member array
    # line - line of circuit
    # stations - all known stations
    def infer_circuit(self, circuit, node_id, starting_line, from_line, stations, close_stations, lines, covered_nodes):
        station_id = self.node_in_station(node_id, close_stations)
        if station_id and station_id == circuit[0].id:
            print('Encountered loop')
            self.print_circuit(circuit)
            return circuit
        elif station_id and station_id != circuit[0].id:
            station = stations[station_id]
            print(str(station))
            if from_line.id in station.covered_line_ids:
                print('Circuit with ' + str(from_line) + ' at ' + str(station) + ' already covered')
                print('')
                return None
            station.covered_line_ids.append(from_line.id)
            circuit.append(station)
            print('Could obtain circuit')
            self.print_circuit(circuit)
            return circuit

        node_covering_lines = []
        for line_id in lines:
            if node_id in lines[line_id].nodes:
                node_covering_lines.append(lines[line_id])

        for line in node_covering_lines:
            if line.id == from_line.id:
                continue
            if starting_line.voltage not in line.voltage:
                continue
            if not self.ref_matches(starting_line, line):
                continue
            if node_id in covered_nodes:
                print('Encountered loop - stopping inference for this line')
                self.print_circuit(circuit)
                return circuit
            print(str(line))
            circuit.append(line)
            if line.first_node() == node_id:
                node_to_continue = line.last_node()
            else:
                node_to_continue = line.first_node()
            covered_nodes.append(node_id)
            return self.infer_circuit(circuit, node_to_continue, starting_line, line, stations, close_stations, lines, covered_nodes)

        print('Error - could not obtain circuit')
        self.print_circuit(circuit)
        return circuit

    # returns if node is in station
    def node_in_station(self, node_id, stations):
        for station_id in stations:
            if node_id in stations[station_id].nodes:
                # node is a part of a substation
                return station_id
        sql = " select create_point(id) as point from planet_osm_nodes where id = " + str(node_id) + ";"
        self.cur.execute(sql)

        result = self.cur.fetchall()
        for(point,) in result:
            node = wkb.loads(point, hex=True)
        for station_id in stations:
            if node.within(stations[station_id].geom):
                return station_id
        return None

    def num_subs_in_circuit(self, circuit):
        num_stations = 0
        for way in circuit:
            if isinstance(way, Station):
                num_stations+=1
        return num_stations

    def print_circuit(self, circuit):
        string = ''
        overpass = ''
        for way in circuit:
            string += str(way) + ','
            overpass += 'way(' + str(way.id) + ');'
        print(string)
        print(overpass)
        print('')

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

    def compare_refs(self, ref1, ref2):
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

    def get_close_stations(self, station_id, stations):
        close_stations = dict()
        for id in stations:
            distance = stations[station_id].geom.centroid.distance(stations[id].geom.centroid)
            if distance <= 300000:
                close_stations[id] = stations[id]
        return close_stations
    
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

    
    
