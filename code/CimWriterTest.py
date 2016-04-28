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
from CimWriter import CimWriter


class CimWriterTest:

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

    def retrieve_relations(self):

        circuits = []
        sql = "select parts from planet_osm_rels r1, _analysis_rels r2 where ARRAY[23025610]::bigint[] <@ r1.parts and hstore(r1.tags)->'voltage' ~ '110000|220000|380000' and hstore(r1.tags)->'type'='route' and hstore(r1.tags)->'route'='power' and r2.osm_id = r1.id and r2.num_stations = 2 and r2.incomplete = 'no'"
        self.cur.execute(sql)
        result = self.cur.fetchall()
        for (parts,) in result:
            relation = []
            for part in parts:
                sql = "select hstore(tags)->'power' from planet_osm_ways where id = " + str(part)
                self.cur.execute(sql)
                [(type,)]  = self.cur.fetchall()
                if 'station' in type:
                    sql = "select id,create_polygon(id) as geom, hstore(tags)->'power' as type, hstore(tags)->'name' as name, hstore(tags)->'ref' as ref, hstore(tags)->'voltage' as voltage, nodes, tags, ST_Y(ST_Transform(ST_Centroid(create_polygon(id)),4326)) as lat, ST_X(ST_Transform(ST_Centroid(create_polygon(id)),4326)) as lon from planet_osm_ways where id = " + str(part)
                    self.cur.execute(sql)
                    [(id, geom, type, name, ref, voltage, nodes, tags, lat, lon)] = self.cur.fetchall()
                    polygon = wkb.loads(geom, hex=True)
                    relation.append(Station(id, polygon, type, name, ref, voltage, nodes, tags, lat, lon))
                elif 'generator' in type or 'plant' in type:
                    sql = "select id,create_polygon(id) as geom, hstore(tags)->'power' as type, hstore(tags)->'name' as name, hstore(tags)->'ref' as ref, hstore(tags)->'voltage' as voltage, hstore(tags)->'generator:output' as output, nodes, tags, ST_Y(ST_Transform(ST_Centroid(create_polygon(id)),4326)) as lat, ST_X(ST_Transform(ST_Centroid(create_polygon(id)),4326)) as lon from planet_osm_ways where id = " + str(part)
                    self.cur.execute(sql)
                    [(id, geom, type, name, ref, voltage, output, nodes, tags, lat, lon)] = self.cur.fetchall()
                    polygon = wkb.loads(geom, hex=True)
                    generator = Station(id, polygon, type, name, ref, voltage, nodes, tags, lat, lon)
                    generator.nominal_power = output
                    relation.append(generator)
                elif 'line' in type or 'cable' in type:
                    sql =   "select id, create_line(id) as geom, hstore(tags)->'power' as type, hstore(tags)->'name' as name, hstore(tags)->'ref' as ref, hstore(tags)->'voltage' as voltage, hstore(tags)->'cables' as cables, nodes, tags, ST_Y(ST_Transform(ST_Centroid(create_line(id)),4326)) as lat, ST_X(ST_Transform(ST_Centroid(create_line(id)),4326)) as lon from planet_osm_ways where id = " + str(part)
                    self.cur.execute(sql)
                    [(id, geom, type, name, ref, voltage, cables, nodes, tags, lat, lon)] = self.cur.fetchall()
                    line = wkb.loads(geom, hex=True)
                    relation.append(Line(id, line, type, name, ref, voltage, cables, nodes, tags, lat, lon))
                else:
                    print('Unknown power tag ' + type)
            sorted_relation = self.sort_relation(relation)
            reference_line = self.get_reference_line(sorted_relation)
            circuits.append(Circuit(sorted_relation, reference_line.voltage, reference_line.name, reference_line.ref))
            for circuit in circuits:
                circuit.print_circuit()

        print('CIM model generation started ...')
        cim_writer = CimWriter(circuits)
        cim_writer.publish('/home/lej/PycharmProjects/transnet/results/cim')

        return

    def get_reference_line(self, relation):
        suspect1 = relation[1]
        suspect2 = relation[len(relation) - 2]
        if ',' in suspect1.voltage or ';' in suspect1.voltage:
            return suspect2
        return suspect1

    def sort_relation(self, unsorted_relation):
        station1 = None
        station2 = None
        lines = []
        for part in unsorted_relation:
            if isinstance(part, Station):
                if station1 is not None:
                    station2 = part
                else:
                    station1 = part
            else: # part is a line
                lines.append(part)
        sorted_circuit = []
        sorted_circuit.extend(lines)
        sorted_circuit.insert(0, station1)
        sorted_circuit.append(station2)
        return sorted_circuit

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
        CimWriterTest_instance = CimWriterTest(database=dbname, user=dbuser, port=dbport, host=dbhost, password=dbpwrd)
    except:
        print "Could not connect to database. Please check the values of host,port,user,password, and database name."
        parser.print_help()
        exit()

    time = datetime.now()
    CimWriterTest_instance.retrieve_relations()
    print('Took ' + str(datetime.now() - time) + ' millies')

    
    
