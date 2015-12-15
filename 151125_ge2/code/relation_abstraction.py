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
import re
    

def abstract_2subs(cur,conn):
    """
    Abstracting relations which have exactly 2 stations to vertices and links.
    Vertices: Substations are in general polygons (which applies to the tags "substation", "generator", "station", "switch", 
    etc. The substations are abstracted as a vertex, which is the geometric center of their constituing polygon. 
    If a substation is a node in OpenStreetmap, then the vertex is this node.
    If a station is of type "relation" in OpenStreetMap, the rectangle which includes all nodes of the relation is 
    defined and its center is used as a vertex. 
    To define which relations in OpenStreetMap have exacly two substations, relations analysis is performed in
    relation_analysis.py and the results are to be found in the table _analysis_rels.
    
    Links: Relation are made of one or more links (transmission lines). These transmission lines are abstracted as the
    links between the two vertices obtained when abstracting the substations. The actual length of the transmission lines
    is calculated as sum of the line (and cables) segments length, which are also listed as constituing the relation.    
    """    
    
    # Create the abstraction function for power relations with two substations
    sql =   """
            CREATE OR REPLACE FUNCTION abstract_rel_with_2subs(rel_id bigint) 
            RETURNS text
            AS $$
            DECLARE 
                sub1_id                 bigint;
                sub2_id                 bigint;
                sub1_id_typ             char;
                sub2_id_typ             char;
                sub1_center             geometry;
                sub2_center             geometry;
                sub1_role               text;
                sub2_role               text;
                sub1_volt               text;
                sub2_volt               text;
                link_length             integer;
                link_way                geometry;
                rel_volt                integer;
                rel_cables              smallint; 
                rel_wires               text; 
                rel_frequency           text; 
                rel_transmissions       bigint[];
                id_1                    bigint;
                id_2                    bigint;
                rel_wires_nb            integer;
                pole_id                 bigint;
                pole_lon                float;
                pole_lat                float;
                pole_center             geometry;
            BEGIN	
            	sub1_id = (SELECT osm_id FROM get_rel_parts_with_power_vals(rel_id,'{station,substation,sub_station,plant,generator}'::text[]) ORDER BY osm_id ASC LIMIT 1);
            	sub2_id = (SELECT osm_id FROM get_rel_parts_with_power_vals(rel_id,'{station,substation,sub_station,plant,generator}'::text[]) ORDER BY osm_id ASC LIMIT 1 OFFSET 1);
            	sub1_id_typ = (SELECT osm_id_typ FROM get_rel_parts_with_power_vals(rel_id,'{station,substation,sub_station,plant,generator}'::text[]) ORDER BY osm_id ASC LIMIT 1);
            	sub2_id_typ = (SELECT osm_id_typ FROM get_rel_parts_with_power_vals(rel_id,'{station,substation,sub_station,plant,generator}'::text[]) ORDER BY osm_id ASC LIMIT 1 OFFSET 1);
            	IF sub1_id_typ = 'n' THEN 
            		sub1_center = (SELECT ST_SetSRID(ST_MakePoint(lon/100.0,lat/100.0),900913) FROM planet_osm_nodes WHERE id = sub1_id);
            	ELSE IF sub1_id_typ = 'w' THEN
            			sub1_center = (SELECT ST_centroid(way) FROM planet_osm_polygon WHERE osm_id = sub1_id);
            		ELSE IF sub1_id_typ = 'r' THEN
            			sub1_center = (SELECT ST_SetSRID(ST_MakePoint((max(lon) + min(lon))/200.0,(max(lat) + min(lat))/200.0),900913) 
                                           FROM planet_osm_nodes WHERE id IN (
                                           SELECT trim(leading 'n' from member)::bigint as node_parts 
                                           FROM (
                                               SELECT unnest(members) as member,* 
                                               FROM planet_osm_rels WHERE id = sub1_id) t 
                                               WHERE member~E'[n]\\\\d+'
                                               UNION
                                               SELECT unnest(nodes) as node_parts 
                                               FROM planet_osm_ways 
                                               WHERE id IN (
                                                   SELECT trim(leading 'w' from member)::bigint as way_parts 
                                                   FROM (
                                                       SELECT unnest(members) as member 
                                                       FROM planet_osm_rels 
                                                       WHERE id = sub1_id) t 
                                                   WHERE member~E'[w]\\\\d+')));
            			ELSE RETURN 'ERROR: Cannot get sub1_center'; 
            			END IF;
            		END IF;
            	END IF;
            	IF sub2_id_typ = 'n' THEN 
            		sub2_center = (SELECT ST_SetSRID(ST_MakePoint(lon/100.0,lat/100.0),900913) FROM planet_osm_nodes WHERE id = sub2_id);
            	ELSE IF sub2_id_typ = 'w' THEN
            			sub2_center = (SELECT ST_centroid(way) FROM planet_osm_polygon WHERE osm_id = sub2_id);
            		ELSE IF sub2_id_typ = 'r' THEN
            			sub2_center = (SELECT ST_SetSRID(ST_MakePoint((max(lon) + min(lon))/200.0,(max(lat) + min(lat))/200.0),900913) FROM planet_osm_nodes WHERE id IN (
            					SELECT trim(leading 'n' from member)::bigint as node_parts FROM (SELECT unnest(members) as member,* FROM planet_osm_rels WHERE id = sub2_id) t WHERE member~E'[n]\\\\d+'
            					UNION
            					SELECT unnest(nodes) as node_parts FROM planet_osm_ways WHERE id IN (SELECT trim(leading 'w' from member)::bigint as way_parts FROM (SELECT unnest(members) as member	FROM planet_osm_rels WHERE id = sub2_id) t WHERE member~E'[w]\\\\d+')));
            			ELSE RETURN 'ERROR: Cannot get sub2_center'; 
            			END IF;
            		END IF;
            	END IF;
            	sub1_role = (SELECT power_role FROM get_rel_parts_with_power_vals(rel_id,'{station,substation,sub_station,plant,generator}'::text[]) ORDER BY osm_id ASC LIMIT 1);
            	sub2_role = (SELECT power_role FROM get_rel_parts_with_power_vals(rel_id,'{station,substation,sub_station,plant,generator}'::text[]) ORDER BY osm_id ASC LIMIT 1 OFFSET 1);
            	sub1_volt = (SELECT voltage FROM planet_osm_polygon WHERE osm_id = sub1_id);
            	sub2_volt = (SELECT voltage FROM planet_osm_polygon WHERE osm_id = sub2_id);
            	link_length = (SELECT round(SUM(l)) FROM (SELECT ST_Length(ST_Transform(way,25832)) as l FROM planet_osm_line WHERE osm_id in (SELECT unnest(parts) FROM planet_osm_rels WHERE id = rel_id) and power in ('line','cable')) t2);
            	link_way = ST_MakeLine(sub1_center,sub2_center);
            	rel_volt = (SELECT (hstore(tags)->'voltage')::integer FROM planet_osm_rels WHERE id = rel_id);
            	rel_cables = (SELECT (hstore(tags)->'cables')::smallint FROM planet_osm_rels WHERE id = rel_id);
            	rel_wires = (SELECT hstore(tags)->'wires' FROM planet_osm_rels WHERE id = rel_id);
                 rel_wires_nb = (SELECT wires_nb FROM _analysis_rels WHERE osm_id = rel_id);
            	rel_frequency = (SELECT (hstore(tags)->'frequency')::text FROM planet_osm_rels WHERE id = rel_id);
            	rel_transmissions = (SELECT array_agg(osm_id) FROM planet_osm_line WHERE osm_id in (SELECT unnest(parts) FROM planet_osm_rels WHERE id = rel_id) and power in ('line','cable'));

            	INSERT INTO _vertices (osm_id,osm_id_typ,geo_center,longitude,latitude,role,voltage,from_relation) VALUES (sub1_id, sub1_id_typ, sub1_center, ST_X(ST_Transform(sub1_center,4326)), ST_Y(ST_Transform(sub1_center,4326)), sub1_role, sub1_volt, rel_id);
            	INSERT INTO _vertices (osm_id,osm_id_typ,geo_center,longitude,latitude,role,voltage,from_relation) VALUES (sub2_id, sub2_id_typ, sub2_center, ST_X(ST_Transform(sub2_center,4326)), ST_Y(ST_Transform(sub2_center,4326)), sub2_role, sub2_volt, rel_id);
            
            -- Only insert as new vertice if it not exists in the final TABLE vertices
            	IF not (SELECT exists(SELECT 1 FROM vertices_ref_id WHERE osm_id=sub1_id and osm_id_typ=sub1_id_typ)) THEN
            		INSERT INTO vertices_ref_id (osm_id,osm_id_typ,visible) VALUES(sub1_id,sub1_id_typ,'1'); 
            		id_1 = (SELECT v_id FROM vertices_ref_id WHERE osm_id=sub1_id and osm_id_typ=sub1_id_typ);
            		INSERT INTO vertices (v_id,lon,lat,typ,voltage,geom) VALUES(id_1,ST_X(ST_Transform(sub1_center,4326)),ST_Y(ST_Transform(sub1_center,4326)),sub1_role,sub1_volt,sub1_center);
            	ELSE
            		id_1 = (SELECT v_id FROM vertices_ref_id WHERE osm_id=sub1_id and osm_id_typ=sub1_id_typ);	
            	END IF;
            	IF not (SELECT exists(SELECT 1 FROM vertices_ref_id WHERE osm_id=sub2_id and osm_id_typ=sub2_id_typ)) THEN
            		INSERT INTO vertices_ref_id (osm_id,osm_id_typ,visible) VALUES(sub2_id,sub2_id_typ,'1');
            		id_2 = (SELECT v_id FROM vertices_ref_id WHERE osm_id=sub2_id and osm_id_typ=sub2_id_typ);
            		INSERT INTO vertices (v_id,lon,lat,typ,voltage,geom) VALUES(id_2,ST_X(ST_Transform(sub2_center,4326)),ST_Y(ST_Transform(sub2_center,4326)),sub2_role,sub2_volt,sub2_center);
            	ELSE 
            		id_2 = (SELECT v_id FROM vertices_ref_id WHERE osm_id=sub2_id and osm_id_typ=sub2_id_typ);	
            	END IF;
             
            	INSERT INTO _links (osm_id_1,osm_id_1_typ,osm_id_2,osm_id_2_typ,length_m,way,voltage,cables,wires,wires_nb,frequency,from_relation,from_transmissions) VALUES (sub1_id,sub1_id_typ, sub2_id,sub2_id_typ, link_length, link_way, rel_volt, rel_cables, rel_wires, rel_wires_nb, rel_frequency, rel_id, rel_transmissions);
            	INSERT INTO links (v_id_1,v_id_2,voltage,cables,wires,frequency,length_m,geom) VALUES(id_1,id_2,rel_volt, rel_cables, rel_wires_nb, rel_frequency,link_length,link_way);
            	
            UPDATE _analysis_rels SET abstracted = 1 WHERE osm_id = rel_id;

            FOR pole_id in select get_rel_way_nodes_with_power_vals(rel_id, '{pole,tower}'::text[]) LOOP
                IF not (SELECT exists(SELECT 1 FROM poles WHERE p_id=pole_id)) THEN
                    pole_center = (SELECT ST_SetSRID(ST_MakePoint(lon/100.0,lat/100.0),900913) FROM planet_osm_nodes WHERE id = pole_id);
                    pole_lon = (SELECT lon FROM planet_osm_nodes WHERE id = pole_id);
                    pole_lat = (SELECT lat FROM planet_osm_nodes WHERE id = pole_id);
                    INSERT INTO poles (p_id,lon,lat,typ,voltage,geom) VALUES(pole_id,ST_X(ST_Transform(pole_center,4326)), ST_Y(ST_Transform(pole_center,4326)),'tower',sub2_volt,pole_center);
                END IF;
            END LOOP;

            RETURN 'Done. Abstraction of relation with 2 substations: relation(' || rel_id || ');';
            END;
            $$ LANGUAGE plpgsql;
            """
    cur.execute(sql)
    conn.commit()
    
    # Abstraction querry for relations with only 2 substations 
    sql =   """
            SELECT abstract_rel_with_2subs(rel_id) 
            FROM (
                SELECT osm_id as rel_id 
                FROM _analysis_rels 
                WHERE num_stations = 2 and incomplete = 'no') t;    
            """            
    cur.execute(sql)
    msg = cur.fetchall()
    conn.commit()
    return msg
    

def get_w_nodes(way_id,cur,conn):
    # Obtain nodes from the extracted OSM "power" ways list.
    sql = "SELECT nodes FROM planet_osm_ways WHERE id = '" + str(way_id) + "';"
    cur.execute(sql)
    data = cur.fetchone()
    return data[0]

def ww_intersect(way1,way2,cur,conn):
    # Get intersection ways
    sql = "SELECT ST_Intersects((SELECT way FROM planet_osm_line WHERE osm_id = " + str(way1) + "),(SELECT way FROM planet_osm_line WHERE osm_id = " + str(way2) + "));"
    cur.execute(sql)
    data = cur.fetchone()
    return data[0]

def wsub_intersect(way,substation,cur,conn):
    # Returns true if way and substation intersect otherwise false.
    sql = "SELECT ST_Intersects((SELECT way FROM planet_osm_line WHERE osm_id = " + str(way) + "),(SELECT way FROM planet_osm_polygon WHERE osm_id = " + str(substation) + "));"
    cur.execute(sql)
    data = cur.fetchone()
    return data[0]

def separate_parts(station_ids, transmission_ids, T_node_id,cur,conn):
    """ Extend each section, beginning at T-junction and going to substations"""
    l1,l2,l3,rest = [],[],[],[]
    # Separate three ways that start at T-junction from transmission sections
    for t_id in transmission_ids:
        if T_node_id in get_w_nodes(t_id,cur,conn):
            if len(l1) == 0:
                l1.append(t_id)
            elif len(l2) == 0:
                l2.append(t_id)
            else:
                l3.append(t_id)
        else:
            rest.append(t_id)  
    
    if len(l1) + len(l2) + len(l3) != 3:
        return "ERROR: Did not find three transmission lines starting at T-junction."
    
    iteration = 0
    while len(rest) > 0 and iteration < 100:
        if ww_intersect(rest[-1],l1[-1],cur,conn):
            l1.append(rest.pop())
        elif ww_intersect(rest[-1],l2[-1],cur,conn):
            l2.append(rest.pop())
        elif ww_intersect(rest[-1],l3[-1],cur,conn):
            l3.append(rest.pop())
        else:
            # move last entry of rest to first entry
            last = rest.pop()
            rest = [last] + rest
        iteration += 1
        
    if len(rest) > 0:
        return "ERROR: Could not connect transmission segments: %s" %(str(rest).translate(None,"'[]L "))
    else:
        TBA_station = False
        ordered_stations = [0,0,0]
        for station in station_ids:
            if wsub_intersect(l1[-1],station,cur,conn) and ordered_stations[0] == 0:
                ordered_stations[0] = station
            elif wsub_intersect(l2[-1],station,cur,conn) and ordered_stations[1] == 0:
                ordered_stations[1] = station
            elif wsub_intersect(l3[-1],station,cur,conn) and ordered_stations[2] == 0:
                ordered_stations[2] = station
            elif not TBA_station:
                TBA_station = station
            else:
                return "ERROR: Could not abstract this relation, too many unconnected segments to a substation."
        if TBA_station != False:
            ordered_stations[ordered_stations.index(0)] = TBA_station
    T_node_id
    return (l1,l2,l3,ordered_stations)

def insert_segments(rel_id,T_node_id,stations,result,cur,conn):
    l1_ids = str(result[0]).translate(None,"'[]L ")
    l2_ids = str(result[1]).translate(None,"'[]L ")  
    l3_ids = str(result[2]).translate(None,"'[]L ")
    ordered_station_ids = result[3]
    ordered_station_types = []
    ordered_station_roles = []
    for o_stat in ordered_station_ids:
        for sta in stations:
            if str(o_stat) in str(sta):
                ordered_station_types.append(sta[0])
                ordered_station_roles.append(re.sub(r"\d", "", sta[1:]))
    sql =   """
            SELECT * FROM abstract_rel_with_T_node(
            '%s', '%s', '{%s}'::bigint[], '{%s}'::bigint[], '{%s}'::bigint[],
            '{%s}'::bigint[], '{%s}'::text[], '{%s}'::text[]);
            """ %(str(rel_id),str(T_node_id),l1_ids,l2_ids,l3_ids, \
                  str(ordered_station_ids).translate(None,"'[]L "), \
                  str(ordered_station_types).translate(None,"'[]L "), \
                  str(ordered_station_roles).translate(None,"'[]L "))
    cur.execute(sql)
    msg = cur.fetchone()
    conn.commit()
    return msg[0]

# Query to abstract T-junctions    
def abstract_3subs_T_node(cur,conn):   
    sql =   """
            CREATE OR REPLACE FUNCTION abstract_rel_with_T_node(
            rel_id 			bigint, 
            T_node_id 		bigint,  
            link1_transmissions  	bigint[],
            link2_transmissions  	bigint[],
            link3_transmissions  	bigint[],
            ordered_station_ids    	bigint[],
            ordered_station_types	text[],
            ordered_station_roles	text[])
            RETURNS text
                            AS $$
                        DECLARE  T_node_loc         geometry;
                                 sub1_id            bigint;
                                 sub2_id            bigint;
                                 sub3_id            bigint;
                                 sub1_id_typ        char;
                                 sub2_id_typ        char;	
                                 sub3_id_typ        char;
                                 sub1_center        geometry;
                                 sub2_center        geometry;
                                 sub3_center        geometry;
                                 sub1_role          text;
                                 sub2_role          text;
                                 sub3_role          text;
                                 sub1_volt          text;
                                 sub2_volt          text;
                                 sub3_volt          text;
                                 link1_len          integer;
                                 link2_len          integer;
                                 link3_len          integer;
                                 link1_way          geometry;
                                 link2_way          geometry;
                                 link3_way          geometry;
                                 rel_volt           integer;
                                 rel_cables         smallint; 
                                 rel_wires          text; 
                                 rel_wires_nb       smallint;
                                 rel_frequency      text; 
                                 id_1               bigint;
                                 id_2               bigint; 
                                 id_3               bigint;
                                 id_4               bigint;
                                 pole_id                 bigint;
                                 pole_lon                float;
                                 pole_lat                float;
                                 pole_center             geometry;
            BEGIN                	             
            T_node_loc = (SELECT ST_SetSRID(ST_MakePoint(lon/100.0,lat/100.0),900913) FROM planet_osm_nodes WHERE id = T_node_id);
            sub1_id = ordered_station_ids[1]; 
            sub2_id = ordered_station_ids[2];
            sub3_id = ordered_station_ids[3];
            sub1_id_typ = ordered_station_types[1];
            sub2_id_typ = ordered_station_types[2];
            sub3_id_typ = ordered_station_types[3];
            sub1_role = ordered_station_roles[1];
            sub2_role = ordered_station_roles[2];
            sub3_role = ordered_station_roles[3];
            
            IF sub1_id_typ = 'n' THEN 
            sub1_volt = (SELECT hstore(tags)->'voltage' FROM planet_osm_nodes WHERE id = sub1_id);
            sub1_center = (SELECT ST_SetSRID(ST_MakePoint(lon/100.0,lat/100.0),900913) FROM planet_osm_nodes WHERE id = sub1_id);
            ELSE IF sub1_id_typ = 'w' THEN
            sub1_volt = (SELECT hstore(tags)->'voltage' FROM planet_osm_ways WHERE id = sub1_id);
            sub1_center = (SELECT ST_centroid(way) FROM planet_osm_polygon WHERE osm_id = sub1_id);
            ELSE IF sub1_id_typ = 'r' THEN
            sub1_volt = (SELECT hstore(tags)->'voltage' FROM planet_osm_rels WHERE id = sub1_id);
            sub1_center = (SELECT ST_SetSRID(ST_MakePoint((max(lon) + min(lon))/200.0,(max(lat) + min(lat))/200.0),900913) 
            FROM planet_osm_nodes
            WHERE id IN (
            	SELECT trim(leading 'n' from member)::bigint as node_parts FROM (SELECT unnest(members) as member,* FROM planet_osm_rels WHERE id = rel_id) t WHERE member~E'[n]\\d+'
                    UNION
                    SELECT unnest(nodes) as node_parts FROM planet_osm_ways WHERE id IN (SELECT trim(leading 'w' from member)::bigint as way_parts 
                    FROM (SELECT unnest(members) as member,* FROM planet_osm_rels WHERE id = rel_id) t WHERE member~E'[w]\\d+')));
                    ELSE RETURN 'ERROR: Cannot get sub1_center'; 
                    END IF;
                    END IF;
                    END IF;
            IF sub2_id_typ = 'n' THEN 
            sub2_volt = (SELECT hstore(tags)->'voltage' FROM planet_osm_nodes WHERE id = sub2_id);
            sub2_center = (SELECT ST_SetSRID(ST_MakePoint(lon/100.0,lat/100.0),900913) FROM planet_osm_nodes WHERE id = sub2_id);
            ELSE IF sub2_id_typ = 'w' THEN
            sub2_volt = (SELECT hstore(tags)->'voltage' FROM planet_osm_ways WHERE id = sub2_id);
            sub2_center = (SELECT ST_centroid(way) FROM planet_osm_polygon WHERE osm_id = sub2_id);
            ELSE IF sub2_id_typ = 'r' THEN
            sub2_volt = (SELECT hstore(tags)->'voltage' FROM planet_osm_rels WHERE id = sub2_id);
            sub2_center = (SELECT ST_SetSRID(ST_MakePoint((max(lon) + min(lon))/200.0,(max(lat) + min(lat))/200.0),900913) FROM planet_osm_nodes WHERE id IN (
            		SELECT trim(leading 'n' from member)::bigint as node_parts FROM (SELECT unnest(members) as member,* FROM planet_osm_rels WHERE id = rel_id) t WHERE member~E'[n]\\d+'
            		UNION
            		SELECT unnest(nodes) as node_parts FROM planet_osm_ways WHERE id IN (SELECT trim(leading 'w' from member)::bigint as way_parts FROM (SELECT unnest(members) as member,* 					FROM planet_osm_rels WHERE id = rel_id) t WHERE member~E'[w]\\d+')));
            ELSE RETURN 'ERROR: Cannot get sub2_center'; 
            END IF;
            END IF;
            END IF;
            IF sub3_id_typ = 'n' THEN 
            sub3_volt = (SELECT hstore(tags)->'voltage' FROM planet_osm_nodes WHERE id = sub3_id);
            sub3_center = (SELECT ST_SetSRID(ST_MakePoint(lon/100.0,lat/100.0),900913) FROM planet_osm_nodes WHERE id = sub3_id);
            ELSE IF sub3_id_typ = 'w' THEN
            sub3_volt = (SELECT hstore(tags)->'voltage' FROM planet_osm_ways WHERE id = sub3_id);
            sub3_center = (SELECT ST_centroid(way) FROM planet_osm_polygon WHERE osm_id = sub3_id);
            ELSE IF sub3_id_typ = 'r' THEN
            sub3_volt = (SELECT hstore(tags)->'voltage' FROM planet_osm_rels WHERE id = sub3_id);
            sub3_center = (SELECT ST_SetSRID(ST_MakePoint((max(lon) + min(lon))/200.0,(max(lat) + min(lat))/200.0),900913) FROM planet_osm_nodes WHERE id IN (
            		SELECT trim(leading 'n' from member)::bigint as node_parts FROM (SELECT unnest(members) as member,* FROM planet_osm_rels WHERE id = sub3_id) t WHERE member~E'[n]\\d+'
            		UNION
            		SELECT unnest(nodes) as node_parts FROM planet_osm_ways WHERE id IN (SELECT trim(leading 'w' from member)::bigint as way_parts FROM (SELECT unnest(members) as member,* 					FROM planet_osm_rels WHERE id = sub3_id) t WHERE member~E'[w]\\d+')));
            ELSE RETURN 'ERROR: Cannot get sub3_center'; 
            END IF;
            END IF;
            END IF;
            
                            		
            link1_way = ST_MakeLine(sub1_center, T_node_loc);
            link2_way = ST_MakeLine(sub2_center, T_node_loc);
            link3_way = ST_MakeLine(sub3_center, T_node_loc);    
            link1_len = (SELECT round(SUM(l)) FROM (SELECT ST_Length(ST_Transform(way,25832)) as l FROM planet_osm_line WHERE osm_id = ANY (link1_transmissions) AND power in ('line','cable'))t); 
            link2_len = (SELECT round(SUM(l)) FROM (SELECT ST_Length(ST_Transform(way,25832)) as l FROM planet_osm_line WHERE osm_id = ANY (link2_transmissions) AND power in ('line','cable'))t); 
            link3_len = (SELECT round(SUM(l)) FROM (SELECT ST_Length(ST_Transform(way,25832)) as l FROM planet_osm_line WHERE osm_id = ANY (link3_transmissions) AND power in ('line','cable'))t); 
            rel_volt = (SELECT voltage FROM _analysis_rels WHERE osm_id = rel_id);
            rel_cables = (SELECT cables FROM _analysis_rels WHERE osm_id = rel_id);
            rel_wires = (SELECT wires FROM _analysis_rels WHERE osm_id = rel_id);
            rel_wires_nb = (SELECT wires_nb FROM _analysis_rels WHERE osm_id = rel_id);
            rel_frequency = (SELECT frequency FROM _analysis_rels WHERE osm_id = rel_id);
                            		
                            
            INSERT INTO _vertices (osm_id,osm_id_typ,geo_center,longitude,latitude,role,voltage,from_relation)  VALUES(sub1_id, sub1_id_typ, sub1_center, ST_X(ST_Transform(sub1_center,4326)), ST_Y(ST_Transform(sub1_center,4326)), sub1_role, rel_volt, rel_id);
            INSERT INTO _vertices (osm_id,osm_id_typ,geo_center,longitude,latitude,role,voltage,from_relation)  VALUES(sub2_id, sub2_id_typ, sub2_center, ST_X(ST_Transform(sub2_center,4326)), ST_Y(ST_Transform(sub2_center,4326)), sub2_role, rel_volt, rel_id);
            INSERT INTO _vertices (osm_id,osm_id_typ,geo_center,longitude,latitude,role,voltage,from_relation)  VALUES(sub3_id, sub3_id_typ, sub3_center, ST_X(ST_Transform(sub3_center,4326)), ST_Y(ST_Transform(sub3_center,4326)), sub3_role, rel_volt, rel_id);
            INSERT INTO _vertices (osm_id,osm_id_typ,geo_center,longitude,latitude,role,voltage,from_relation)  VALUES(T_node_id, 'a', T_node_loc, ST_X(ST_Transform(T_node_loc,4326)), ST_Y(ST_Transform(T_node_loc,4326)), 'auxillary_T_node', rel_volt, rel_id);
            
            
            -- Only insert as new vertice if it not exists in the final TABLE vertices
            IF not (SELECT exists(SELECT 1 FROM vertices_ref_id WHERE osm_id=sub1_id and osm_id_typ=sub1_id_typ)) THEN
                        		INSERT INTO vertices_ref_id (osm_id,osm_id_typ,visible) VALUES(sub1_id,sub1_id_typ,'1'); 
                        		id_1 = (SELECT v_id FROM vertices_ref_id WHERE osm_id=sub1_id and osm_id_typ=sub1_id_typ);
                        		INSERT INTO vertices (v_id,lon,lat,typ,voltage,geom) VALUES(id_1,ST_X(ST_Transform(sub1_center,4326)),ST_Y(ST_Transform(sub1_center,4326)),sub1_role,sub1_volt,sub1_center);
                        	ELSE
                        		id_1 = (SELECT v_id FROM vertices_ref_id WHERE osm_id=sub1_id and osm_id_typ=sub1_id_typ);	
                        	END IF;
            IF not (SELECT exists(SELECT 1 FROM vertices_ref_id WHERE osm_id=sub2_id and osm_id_typ=sub2_id_typ)) THEN
                        		INSERT INTO vertices_ref_id (osm_id,osm_id_typ,visible) VALUES(sub2_id,sub2_id_typ,'1');
                        		id_2 = (SELECT v_id FROM vertices_ref_id WHERE osm_id=sub2_id and osm_id_typ=sub2_id_typ);
                        		INSERT INTO vertices (v_id,lon,lat,typ,voltage,geom) VALUES(id_2,ST_X(ST_Transform(sub2_center,4326)),ST_Y(ST_Transform(sub2_center,4326)),sub2_role,sub2_volt,sub2_center);
                        	ELSE 
                        		id_2 = (SELECT v_id FROM vertices_ref_id WHERE osm_id=sub2_id and osm_id_typ=sub2_id_typ);	
                        	END IF;
            IF not (SELECT exists(SELECT 1 FROM vertices_ref_id WHERE osm_id=sub3_id and osm_id_typ=sub3_id_typ)) THEN
                        		INSERT INTO vertices_ref_id (osm_id,osm_id_typ,visible) VALUES(sub3_id,sub3_id_typ,'1');
                        		id_3 = (SELECT v_id FROM vertices_ref_id WHERE osm_id=sub3_id and osm_id_typ=sub3_id_typ);
                        		INSERT INTO vertices (v_id,lon,lat,typ,voltage,geom) VALUES(id_3,ST_X(ST_Transform(sub3_center,4326)),ST_Y(ST_Transform(sub3_center,4326)),sub3_role,sub3_volt,sub3_center);
                        	ELSE 
                        		id_3 = (SELECT v_id FROM vertices_ref_id WHERE osm_id=sub3_id and osm_id_typ=sub3_id_typ);	
                        	END IF;
            IF not (SELECT exists(SELECT 1 FROM vertices_ref_id WHERE osm_id=T_node_id and osm_id_typ='a')) THEN
                        		INSERT INTO vertices_ref_id (osm_id,osm_id_typ,visible) VALUES(T_node_id,'a','1');
                        		id_4 = (SELECT v_id FROM vertices_ref_id WHERE osm_id=T_node_id and osm_id_typ='a');
                        		INSERT INTO vertices (v_id,lon,lat,typ,voltage,geom) VALUES(id_4,ST_X(ST_Transform(T_node_loc,4326)),ST_Y(ST_Transform(T_node_loc,4326)),'auxillary_T_node',rel_volt,T_node_loc);
                        	ELSE 
                        		id_4 = (SELECT v_id FROM vertices_ref_id WHERE osm_id=T_node_id and osm_id_typ='a');	
                        	END IF;
            
            INSERT INTO _links (osm_id_1,osm_id_1_typ,osm_id_2,osm_id_2_typ,length_m,way,voltage,cables,wires,wires_nb,frequency,from_relation,from_transmissions) VALUES (sub1_id,sub1_id_typ, T_node_id,'a', link1_len, link1_way, rel_volt, rel_cables, rel_wires, rel_wires_nb, rel_frequency, rel_id, link1_transmissions);
            INSERT INTO _links (osm_id_1,osm_id_1_typ,osm_id_2,osm_id_2_typ,length_m,way,voltage,cables,wires,wires_nb,frequency,from_relation,from_transmissions) VALUES (sub2_id,sub2_id_typ, T_node_id,'a', link2_len, link2_way, rel_volt, rel_cables, rel_wires, rel_wires_nb, rel_frequency, rel_id, link2_transmissions);
            INSERT INTO _links (osm_id_1,osm_id_1_typ,osm_id_2,osm_id_2_typ,length_m,way,voltage,cables,wires,wires_nb,frequency,from_relation,from_transmissions) VALUES (sub3_id,sub3_id_typ, T_node_id,'a', link3_len, link3_way, rel_volt, rel_cables, rel_wires, rel_wires_nb, rel_frequency, rel_id, link3_transmissions);
            INSERT INTO links (v_id_1,v_id_2,voltage,cables,wires,frequency,length_m,geom) VALUES(id_1,id_4,rel_volt, rel_cables, rel_wires_nb, rel_frequency,link1_len,link1_way);
            INSERT INTO links (v_id_1,v_id_2,voltage,cables,wires,frequency,length_m,geom) VALUES(id_2,id_4,rel_volt, rel_cables, rel_wires_nb, rel_frequency,link2_len,link2_way);
            INSERT INTO links (v_id_1,v_id_2,voltage,cables,wires,frequency,length_m,geom) VALUES(id_3,id_4,rel_volt, rel_cables, rel_wires_nb, rel_frequency,link3_len,link3_way);

            FOR pole_id in select get_rel_way_nodes_with_power_vals(rel_id, '{pole,tower}'::text[]) LOOP
                IF not (SELECT exists(SELECT 1 FROM poles WHERE p_id=pole_id)) THEN
                    pole_center = (SELECT ST_SetSRID(ST_MakePoint(lon/100.0,lat/100.0),900913) FROM planet_osm_nodes WHERE id = pole_id);
                    pole_lon = (SELECT lon FROM planet_osm_nodes WHERE id = pole_id);
                    pole_lat = (SELECT lat FROM planet_osm_nodes WHERE id = pole_id);
                    INSERT INTO poles (p_id,lon,lat,typ,voltage,geom) VALUES(pole_id,ST_X(ST_Transform(pole_center,4326)), ST_Y(ST_Transform(pole_center,4326)),'tower',sub2_volt,pole_center);
                END IF;
            END LOOP;
                        	
                        UPDATE _analysis_rels SET abstracted = 1, t_node_ids = array[T_node_id]::bigint[] WHERE osm_id = rel_id;
                        
                        RETURN 'Done. Abstraction of relation with 3 stations and T-node: relation(' || rel_id || ');';
                            END;
                            $$ LANGUAGE plpgsql;
            """    
    cur.execute(sql)
    conn.commit()
    
    # Get all T-junction relations with 3 stations
    sql =   """
            SELECT osm_id,t_node_ids,stations,transmissions
            FROM _analysis_rels 
            WHERE t_node_ids <> '{}' AND incomplete = 'no' AND num_stations = 3 ORDER BY osm_id;
            """
    cur.execute(sql)
    result = cur.fetchall()
    success = 0
    for (rel_id,T_node_ids,stations,transmissions) in result:
        #print rel_id
        station_ids = [re.sub(r"\D", "", s) for s in stations] 
        station_ids_typ = [s[0] for s in stations]
        transmission_ids = [re.sub(r"\D", "", t) for t in transmissions] 
        
        # FIXME: stations from relation type have no geometry, 
        # How to find a intersection of a line segment with the relation if the relation is a power plant?
        if 'r' in station_ids_typ:
            continue

        for T_node_id in T_node_ids:
            res = separate_parts(station_ids, transmission_ids, T_node_id,cur,conn)                 
            if type(res) is tuple:              
                break

        if type(res) is str:
            #print res
            sql =   """
                    INSERT INTO _t_node_problems (rel_id,t_node_ids,stations,transmissions,error_msg) 
                    VALUES('%s','{%s}'::bigint[],'{%s}'::text[],'{%s}'::text[],'%s');
                    """  % (str(rel_id),str(T_node_ids).translate(None,"'[]L "),str(stations).translate(None,"'[]L "),str(transmissions).translate(None,"'[]L "),res)
            cur.execute(sql)
            conn.commit()
            continue
        else:
            msg = insert_segments(rel_id,T_node_id,stations,res,cur,conn)
            #print msg
            success += 1

    return success

# TODO:
def abstract_3subs_in_row(cur,conn):
    pass

def rel_abstraction(cur,conn):
    msg = abstract_2subs(cur,conn)
    success = abstract_3subs_T_node(cur,conn)
    #abstract_3subs_in_row(cur,conn)
    return len(msg) + success
    
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
        nr_success = rel_abstraction(cur,conn)
        print 'Number of abstracted relations: ', nr_success
    except:
        print 'ERROR: Could not abstract relations in database.'
        exit()
    
