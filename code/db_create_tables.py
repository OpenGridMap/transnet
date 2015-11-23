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


def ct__analysis_rels(cur,conn):
    # Create _analysis_rels table.
    sql = "DROP TABLE IF EXISTS _analysis_rels;"
    cur.execute(sql)
    conn.commit()
    sql =   """
            CREATE TABLE _analysis_rels (
            id                  serial PRIMARY KEY NOT NULL, 
            osm_id              bigint, 
            voltage             integer,
            cables              smallint,
            wires               text,
            wires_nb            smallint,
            frequency	          text,
            num_parts	          smallint,
            num_stations        smallint,
            num_transmissions   smallint,
            num_discardeds      smallint,
            stations            text[],
            transmissions       text[],
            discardeds          text[],
            T_node_ids          bigint[],
            incomplete          text,
            abstracted          smallint);
            """
    cur.execute(sql)
    conn.commit()


def ct__vertices(cur,conn):
    # Create _vertices table.
    sql = "DROP TABLE IF EXISTS _vertices;"
    cur.execute(sql)
    conn.commit()
    sql =   """
            CREATE TABLE _vertices (
            id              serial PRIMARY KEY NOT NULL, 
            osm_id          bigint,
            osm_id_typ      char, 
            geo_center      geometry,
            longitude       float,
            latitude        float,
            role            text,
            voltage         text,
            from_relation   bigint);
            """
    cur.execute(sql)
    conn.commit()


def ct__links(cur,conn):
    # Create _links table.
    sql = "DROP TABLE IF EXISTS _links;"
    cur.execute(sql)
    conn.commit()
    sql = """
        CREATE TABLE _links (
        	id 		      serial PRIMARY KEY NOT NULL, 
        	osm_id_1 	      bigint, 
           osm_id_1_typ     char,
        	osm_id_2 	      bigint,
           osm_id_2_typ     char,
        	length_m		integer,
        	way		      geometry,
        	voltage		integer,
        	cables		integer,
        	wires		      text,
		wires_nb		integer,
        	frequency 	      text,	
        	from_relation	bigint,
        	from_transmissions bigint[]);
         """
    cur.execute(sql)
    conn.commit()


def ct__t_node_problems(cur,conn):
    # Create _t_node_problems table.
    sql = "DROP TABLE IF EXISTS _t_node_problems;"
    cur.execute(sql)
    conn.commit()
    sql =   """
            CREATE TABLE _t_node_problems ( 
            id              serial PRIMARY KEY NOT NULL, 
            rel_id          bigint, 
            T_node_ids      bigint[], 
            stations        text[], 
            transmissions   text[],
            error_msg       text);
            """
    cur.execute(sql)
    conn.commit()


def ct_vertices_ref_id(cur,conn):
    # Create _vertices_ref_id table.
    sql = "DROP TABLE IF EXISTS vertices_ref_id;"
    cur.execute(sql)
    conn.commit()
    sql = """
        CREATE TABLE vertices_ref_id (
        v_id            serial PRIMARY KEY NOT NULL,
        osm_id          bigint,
        osm_id_typ	  char,
        visible         smallint);        
         """
    cur.execute(sql)
    conn.commit()


def ct_vertices(cur,conn):
    # Create vertices table.
    sql = "DROP TABLE IF EXISTS vertices;"
    cur.execute(sql)
    conn.commit()
    sql = """
        CREATE TABLE vertices (
        v_id             bigint PRIMARY KEY NOT NULL,
        lon              float,
        lat              float,
        typ              text,
        voltage          text,
        geom             geometry);
         """
    cur.execute(sql)
    conn.commit()


def ct_links(cur,conn):
    # Create links table.
    sql = "DROP TABLE IF EXISTS links;"
    cur.execute(sql)
    conn.commit()
    sql = """
        CREATE TABLE links (
        l_id             serial PRIMARY KEY NOT NULL,
        v_id_1           bigint,
        v_id_2           bigint,
        voltage          integer,
        cables           integer,
        wires            integer,
        frequency        text,
        length_m         integer,
        r                 float,
        x                 float,
        c                 float,
        i_th_max          float,
        geom             geometry);
         """
    cur.execute(sql)
    conn.commit()

def ct_poles(cur,conn):
    # Create poles table.
    sql = "DROP TABLE IF EXISTS poles;"
    cur.execute(sql)
    conn.commit()
    sql = """
        CREATE TABLE poles (
        p_id             bigint PRIMARY KEY NOT NULL,
        lon              float,
        lat              float,
        typ              text,
        voltage          text,
        geom             geometry);
         """
    cur.execute(sql)
    conn.commit()
 
def create_tables(cur,conn):
    # Create all tables
    ct__analysis_rels(cur,conn)
    ct__vertices(cur,conn)
    ct__links(cur,conn)
    ct__t_node_problems(cur,conn)
    ct_vertices_ref_id(cur,conn)
    ct_vertices(cur,conn)
    ct_links(cur,conn)
    ct_poles(cur,conn)
    
    
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
    dbname = options.dbname if options.dbname else 'de_power_150601'
    dbhost = options.dbhost if options.dbhost else '127.0.0.1'
    dbport = options.dbport if options.dbport else '5333'
    dbuser = options.dbuser if options.dbuser else 'postgres' 
    dbpwrd = options.dbpwrd if options.dbpwrd else '' 
 
    # Connect to DB 
    try:
        conn = psycopg2.connect(database=dbname, user=dbuser, port=dbport, host=dbhost, password=dbpwrd)
        cur = conn.cursor()
    except:
        print "Could not connect to database. Please check the values of host,port,user,password,database name."
        parser.print_help()
        exit() 
    
    try:
        create_tables(cur,conn)
        print 'Tables created.'
    except:
        print 'ERROR: Could not create tables in database.'
        exit()    
