from datetime import datetime
from optparse import OptionParser

import psycopg2
from shapely import wkb

from CimWriter import CimWriter
from Circuit import Circuit
from Line import Line
from Station import Station
from Transnet import Transnet


# noinspection PyShadowingBuiltins,PyShadowingBuiltins,PyShadowingBuiltin
# noinspection PyShadowingBuiltins,PyShadowingBuiltins,PyShadowingBuiltins
# noinspection PyShadowingBuiltins,PyPep8,PyPep8,PyPep8,PyPep8,PyPep8,PyStringFormat
class CimWriterTest:
    def __init__(self, database, user, host, port, password):
        # Initializes the SciGRID class with the database connection parameters.
        # These parameters are: database name, database user, database password, database host and port. 
        # Notice: The password will not be stored.

        self.cur = self.conn.cursor()
        self.conn = psycopg2.connect(password=password, **self.connection)
        self.connection = {'database': database, 'user': user, 'host': host, 'port': port}

    def get_connection_data(self):
        # Obtain the database connection parameters.
        return self.connection

    def retrieve_relations(self):

        circuits = []
        sql = "SELECT parts FROM planet_osm_rels r1 WHERE ARRAY[27124619]::BIGINT[] <@ r1.parts AND hstore(r1.tags)->'voltage' ~ '110000|220000|380000' AND hstore(r1.tags)->'type'='route' AND hstore(r1.tags)->'route'='power'"
        self.cur.execute(sql)
        result = self.cur.fetchall()
        for (parts,) in result:
            relation = []
            for part in parts:
                sql = "SELECT hstore(tags)->'power' FROM planet_osm_ways WHERE id = " + str(part)
                self.cur.execute(sql)
                [(type,)] = self.cur.fetchall()
                if 'station' in type:
                    sql = "SELECT id,create_polygon(id) AS geom, hstore(tags)->'power' AS type, hstore(tags)->'name' AS name, hstore(tags)->'ref' AS ref, hstore(tags)->'voltage' AS voltage, nodes, tags, ST_Y(ST_Transform(ST_Centroid(create_polygon(id)),4326)) AS lat, ST_X(ST_Transform(ST_Centroid(create_polygon(id)),4326)) AS lon FROM planet_osm_ways WHERE id = " + str(
                        part)
                    self.cur.execute(sql)
                    [(id, geom, type, name, ref, voltage, nodes, tags, lat, lon)] = self.cur.fetchall()
                    polygon = wkb.loads(geom, hex=True)
                    relation.append(Station(id, polygon, type, name, ref, voltage, nodes, tags, lat, lon, geom))
                elif 'generator' in type or 'plant' in type:
                    sql = "SELECT id,create_polygon(id) AS geom, hstore(tags)->'power' AS type, hstore(tags)->'name' AS name, hstore(tags)->'ref' AS ref, hstore(tags)->'voltage' AS voltage, hstore(tags)->'plant:output:electricity' AS output1, hstore(tags)->'generator:output:electricity' AS output2, nodes, tags, ST_Y(ST_Transform(ST_Centroid(create_polygon(id)),4326)) AS lat, ST_X(ST_Transform(ST_Centroid(create_polygon(id)),4326)) AS lon FROM planet_osm_ways WHERE id = " + str(
                        part)
                    self.cur.execute(sql)
                    [(
                        id, geom, type, name, ref, voltage, output1, output2, nodes, tags, lat,
                        lon)] = self.cur.fetchall()
                    polygon = wkb.loads(geom, hex=True)
                    generator = Station(id, polygon, type, name, ref, voltage, nodes, tags, lat, lon, geom)
                    generator.nominal_power = Transnet.parse_power(
                        output1) if output1 is not None else Transnet.parse_power(output2)
                    relation.append(generator)
                elif 'line' in type or 'cable' in type:
                    sql = "SELECT id, create_line(id) AS geom, hstore(tags)->'power' AS type, hstore(tags)->'name' AS name, hstore(tags)->'ref' AS ref, hstore(tags)->'voltage' AS voltage, hstore(tags)->'cables' AS cables, nodes, tags, ST_Y(ST_Transform(ST_Centroid(create_line(id)),4326)) AS lat, ST_X(ST_Transform(ST_Centroid(create_line(id)),4326)) AS lon FROM planet_osm_ways WHERE id = " + str(
                        part)
                    self.cur.execute(sql)
                    [(id, geom, type, name, ref, voltage, cables, nodes, tags, lat, lon)] = self.cur.fetchall()
                    line = wkb.loads(geom, hex=True)
                    relation.append(
                        Line(id, line, type, name, ref, voltage, cables, nodes, tags, lat, lon, None, None, None, geom))
                else:
                    print('Unknown power tag ' + type)
            sorted_relation = CimWriterTest.sort_relation(relation)
            reference_line = CimWriterTest.get_reference_line(sorted_relation)
            circuits.append(Circuit(sorted_relation, reference_line.voltage, reference_line.name, reference_line.ref))
            for circuit in circuits:
                circuit.print_circuit()

            for circuit in circuits:
                circuit.print_overpass()

        print('CIM model generation started ...')
        cim_writer = CimWriter(circuits, None, None, None)
        cim_writer.publish('../results/cim')

        return

    @staticmethod
    def get_reference_line(relation):
        suspect1 = relation[1]
        suspect2 = relation[len(relation) - 2]
        if ',' in suspect1.voltage or ';' in suspect1.voltage:
            return suspect2
        return suspect1

    @staticmethod
    def sort_relation( unsorted_relation):
        station1 = None
        station2 = None
        lines = []
        for part in unsorted_relation:
            if isinstance(part, Station):
                if station1:
                    station2 = part
                else:
                    station1 = part
            else:  # part is a line
                lines.append(part)
        sorted_circuit = []
        sorted_circuit.extend(lines)
        sorted_circuit.insert(0, station1)
        sorted_circuit.append(station2)
        return sorted_circuit


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

    (options, args) = parser.parse_args()
    # get connection data via command line or set to default values
    dbname = options.dbname if options.dbname else 'power_de'
    dbhost = options.dbhost if options.dbhost else '127.0.0.1'
    dbport = options.dbport if options.dbport else '5432'
    dbuser = options.dbuser if options.dbuser else 'postgres'
    dbpwrd = options.dbpwrd if options.dbpwrd else 'OpenGridMap'

    # Connect to DB 
    # noinspection PyBroadException
    try:
        CimWriterTest_instance = CimWriterTest(database=dbname, user=dbuser, port=dbport, host=dbhost, password=dbpwrd)
        time = datetime.now()
        CimWriterTest_instance.retrieve_relations()
        print('Took ' + str(datetime.now() - time) + ' millies')
    except Exception as e:
        print "Could not connect to database. Please check the values of host,port,user,password, and database name."
        parser.print_help()
        exit()
