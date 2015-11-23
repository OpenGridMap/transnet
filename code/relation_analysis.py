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


def analyze_rels(cur,conn):
    """ The relations analysis analyzes how many relations exists in the OSM database 
        whith a voltage tag having a value of 220kV and higher. 
        It also defines how many relations are incomplete or are in planning/under construction.
        Further, information about the number of substations and line segements is collected.
 
        This relations analysis is structured as follows:
        Three functions are defined which use the filteres power relation IDs as an input value. 
        The first function "get_rel_parts_with_power_vals" return the elements of the relation having a voltage tag, 
        and the second function "get_rel_parts_without_power_vals" returns the elements of the relation without a voltage tag. 
        The third function "analysis_rel" analyzes the relations and stores the results into the table _analysis_rels.
	The table will be used in the abstraction step.
    """
    # function 1: Obtain relation elements (parts) having a power tag 
    sql =   """
            CREATE OR REPLACE FUNCTION get_rel_parts_with_power_vals (rel_id bigint, vals text[]) 
            RETURNS TABLE (osm_id bigint, osm_id_typ char, power_role text)
            AS $$
            BEGIN
            FOR osm_id, osm_id_typ, power_role IN
                	SELECT id as osm_id,'n' as osm_id_typ, hstore(tags)->'power' as power_role  FROM planet_osm_nodes 
                		WHERE id IN  
                		(SELECT trim(leading 'n' from member)::bigint 
                       FROM (SELECT unnest(members) as member 
                             FROM planet_osm_rels 
                             WHERE id = rel_id)t 
                       WHERE member ~  E'^n[0,1,2,3,4,5,6,7,8,9]+$') AND hstore(tags)->'power' = ANY (vals)	
                	UNION
                	SELECT id as osm_id,'w' as osm_id_typ, hstore(tags)->'power' as power_role FROM planet_osm_ways 
                		WHERE id IN  
                		(SELECT trim(leading 'w' from member)::bigint 
                       FROM (SELECT unnest(members) as member 
                             FROM planet_osm_rels 
                             WHERE id = rel_id)t 
                       WHERE member ~  E'^w[0,1,2,3,4,5,6,7,8,9]+$') AND hstore(tags)->'power' = ANY (vals)	
                	UNION
                	SELECT id as osm_id,'r' as osm_id_typ, hstore(tags)->'power' as power_role  FROM planet_osm_rels 
                		WHERE id IN  
                		(SELECT trim(leading 'r' from member)::bigint 
                       FROM (SELECT unnest(members) as member 
                             FROM planet_osm_rels 
                             WHERE id = rel_id)t 
                       WHERE member ~  E'^r[0,1,2,3,4,5,6,7,8,9]+$') AND hstore(tags)->'power' = ANY (vals)	
            LOOP
                	RETURN NEXT;
            END LOOP;
            RETURN;
            END;
            $$ LANGUAGE plpgsql;
            """
    cur.execute(sql)
    conn.commit()

     # function 2 : Obtain relation elements (parts) wihtout a power tag 
    sql =   """
            CREATE OR REPLACE FUNCTION get_rel_parts_without_power_vals (rel_id bigint, vals text[]) 
            RETURNS TABLE (osm_id bigint, osm_id_typ char, power_role text)
            AS $$
            BEGIN
            FOR osm_id, osm_id_typ, power_role IN
                	SELECT id as osm_id,'n' as osm_id_typ, hstore(tags)->'power' as power_role  FROM planet_osm_nodes 
                		WHERE id IN  
                		(SELECT trim(leading 'n' from member)::bigint 
                       FROM (SELECT unnest(members) as member 
                             FROM planet_osm_rels 
                             WHERE id = rel_id)t 
                       WHERE member ~  E'^n[0,1,2,3,4,5,6,7,8,9]+$') AND (not (hstore(tags)->'power' = ANY (vals)) or not exist(hstore(tags),'power'))	
                	UNION
                	SELECT id as osm_id,'w' as osm_id_typ, hstore(tags)->'power' as power_role FROM planet_osm_ways 
                		WHERE id IN  
                		(SELECT trim(leading 'w' from member)::bigint 
                       FROM (SELECT unnest(members) as member 
                             FROM planet_osm_rels 
                             WHERE id = rel_id)t 
                       WHERE member ~  E'^w[0,1,2,3,4,5,6,7,8,9]+$') AND (not (hstore(tags)->'power' = ANY (vals)) or not exist(hstore(tags),'power'))	
                	UNION
                	SELECT id as osm_id,'r' as osm_id_typ, hstore(tags)->'power' as power_role  FROM planet_osm_rels 
                		WHERE id IN  
                		(SELECT trim(leading 'r' from member)::bigint 
                       FROM (SELECT unnest(members) as member 
                             FROM planet_osm_rels 
                             WHERE id = rel_id)t 
                       WHERE member ~  E'^r[0,1,2,3,4,5,6,7,8,9]+$') and (not (hstore(tags)->'power' = ANY (vals)) or not exist(hstore(tags),'power'))	
            LOOP
                	RETURN NEXT;
            END LOOP;
            RETURN;
            END;
            $$ LANGUAGE plpgsql;
            """
    cur.execute(sql)
    conn.commit()

     # function 3 : Analysis of the power relations
    sql =   """
            CREATE OR REPLACE FUNCTION analysis_rel(rel_id bigint) RETURNS text
            AS $$
            DECLARE 
                 rel_volt               integer;
                 rel_cables             smallint;
                 rel_wires              text;
                 rel_nb_wires           smallint;
                 rel_freq               text;
                 rel_stations           text[];
                 rel_transmissions      text[];
                 rel_discardeds         text[];
                 num_parts              smallint;
                 num_stations           smallint;
                 num_transmissions      smallint;
                 num_discardeds         smallint;
                 rel_incomplete         text;
                 abstracted             smallint;
                 rel_T_nodes            bigint[];
            BEGIN
            abstracted = 0;
            	rel_volt = (SELECT (hstore(tags)->'voltage')::integer FROM planet_osm_rels WHERE id = rel_id);
            	rel_cables = (SELECT hstore(tags)->'cables' FROM planet_osm_rels WHERE id = rel_id);
            	rel_wires = (SELECT hstore(tags)->'wires' FROM planet_osm_rels WHERE id = rel_id);
            	rel_freq = (SELECT hstore(tags)->'frequency' FROM planet_osm_rels WHERE id = rel_id);
            	rel_stations = (SELECT array_agg(osm_id_typ || osm_id || power_role) FROM get_rel_parts_with_power_vals(rel_id,'{station,substation,sub_station,plant,generator}'::text[]));
            	rel_transmissions = (SELECT array_agg(osm_id_typ || osm_id || power_role) FROM get_rel_parts_with_power_vals(rel_id,'{line,cable}'::text[]));
            	rel_discardeds = (SELECT array_agg( CASE WHEN power_role <> '' THEN osm_id_typ || osm_id || power_role ELSE 'object ' || osm_id_typ || osm_id || ' has no power tag' END) FROM get_rel_parts_without_power_vals(rel_id,'{station,substation,sub_station,plant,generator,line,cable}'::text[]));
            	num_parts = CASE WHEN array_length(rel_stations, 1) is null THEN 0 ELSE array_length(rel_stations, 1) END  +  
            		    CASE WHEN array_length(rel_transmissions, 1) is null THEN 0 ELSE array_length(rel_transmissions, 1) END +
            		    CASE WHEN array_length(rel_discardeds, 1) is null THEN 0 ELSE array_length(rel_discardeds, 1) END;
            	num_stations = CASE WHEN array_length(rel_stations, 1) is null THEN 0 ELSE array_length(rel_stations, 1) END;
            	num_transmissions = CASE WHEN array_length(rel_transmissions, 1) is null THEN 0 ELSE array_length(rel_transmissions, 1) END;
            num_discardeds = CASE WHEN array_length(rel_discardeds, 1) is null THEN 0 ELSE array_length(rel_discardeds, 1) END;
            rel_incomplete = (SELECT CASE WHEN exist(hstore(tags),'planned') THEN 'planned' ELSE CASE WHEN exist(hstore(tags),'construction') THEN 'construction' ELSE  CASE WHEN exist(hstore(tags),'fixme') THEN 'fixme' ELSE CASE WHEN array_length(rel_discardeds, 1) is not null THEN 'discarded parts' ELSE 'no' END END END END FROM planet_osm_rels WHERE id = rel_id);
            
            --- Find T-junctions in relations with more than 3 stations             
            IF num_stations > 2 
            THEN  rel_T_nodes = (SELECT array_agg(node) 
                                FROM (
                                    SELECT node, COUNT(node) 
                                    FROM ( 
                                        SELECT unnest(nodes) as node 
                                        FROM planet_osm_ways w 
                                        JOIN (
                                            SELECT parts 
                                            FROM planet_osm_line l 
                                            JOIN (
                                                SELECT unnest(parts) as parts 
                                                FROM planet_osm_rels 
                                                WHERE id = rel_id) j 
                                            ON j.parts = l.osm_id) p 
                                        ON w.id = p.parts) pp 
                                    GROUP BY pp.node) ppp 
                                    WHERE count=3);
            END IF;
            
            --- Transform the number of wires from a text tag to an integer
            IF rel_wires = 'single' THEN
        		rel_nb_wires = 1;
        	 ELSE IF rel_wires = 'double' THEN 
        		rel_nb_wires = 2;
        	 ELSE if rel_wires = 'triple' THEN
        		rel_nb_wires = 3;
        	 ELSE if rel_wires = 'quad' THEN
        		rel_nb_wires = 4;
        	 END IF;
        	 END IF;
        	 END IF;
        	 END IF;
            	
             
            INSERT INTO _analysis_rels (osm_id,voltage,cables,wires,wires_nb,frequency,num_parts,num_stations,num_transmissions,num_discardeds,stations,transmissions,discardeds,T_node_ids,incomplete,abstracted) VALUES (rel_id,rel_volt,rel_cables,rel_wires,rel_nb_wires,rel_freq,num_parts,num_stations,num_transmissions,num_discardeds,rel_stations,rel_transmissions,rel_discardeds,rel_T_nodes,rel_incomplete,abstracted);
            
            RETURN 'Done. Analysis of relation: relation(' || rel_id || ');';
            END;
            $$ LANGUAGE plpgsql;
            """
    cur.execute(sql)
    conn.commit()

    # function 4 : Create function that lists the poles of ways
    sql =   """
            CREATE OR REPLACE FUNCTION get_way_nodes_with_power_vals (way_id bigint, vals text[])
            RETURNS TABLE (osm_id bigint)
            AS $$
            BEGIN
            FOR osm_id IN
                	SELECT id as osm_id FROM planet_osm_nodes
                		WHERE id IN
                		(SELECT node::bigint
                       FROM (SELECT unnest(nodes) as node
                             FROM planet_osm_ways
                             WHERE id = way_id)t)
                       AND hstore(tags)->'power' = ANY (vals)
            LOOP
                	RETURN NEXT;
            END LOOP;
            RETURN;
            END;
            $$ LANGUAGE plpgsql;
            """
    cur.execute(sql)
    conn.commit()

    # function 5 : Create function that lists the poles of rels
    sql =   """
            CREATE OR REPLACE FUNCTION get_rel_way_nodes_with_power_vals (rel_id bigint, vals text[])
            RETURNS TABLE (osm_id bigint)
            AS $$
            BEGIN
            FOR osm_id IN
                	SELECT get_way_nodes_with_power_vals(id, vals) FROM planet_osm_ways
                		WHERE id IN
                		(SELECT trim(leading 'w' from member)::bigint
                       FROM (SELECT unnest(members) as member
                             FROM planet_osm_rels
                             WHERE id = rel_id)t
                       WHERE member ~  E'^w[0,1,2,3,4,5,6,7,8,9]+$')
            LOOP
                	RETURN NEXT;
            END LOOP;
            RETURN;
            END;
            $$ LANGUAGE plpgsql;
            """
    cur.execute(sql)
    conn.commit()

    # Relation analysis querry
    sql =   """
            SELECT analysis_rel(id) 
            FROM planet_osm_rels 
            WHERE hstore(tags)->'route'='power' and 
                  hstore(tags)->'voltage' ~ E'^[0,1,2,3,4,5,6,7,8,9]+$' and 
                  (hstore(tags)->'voltage')::integer > 219999;
            """
    cur.execute(sql)
    msg = cur.fetchall()
    conn.commit()
    return msg




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
    dbport = options.dbport if options.dbport else '5432'
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
        msg = analyze_rels(cur,conn)
        print 'Number of analyzed relations: ', len(msg)
    except:
        print 'ERROR: Could not analyze relations in database.'
        exit()
    
