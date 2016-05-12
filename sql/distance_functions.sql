-- Function: avg_distance_between_stations(bigint)

-- DROP FUNCTION avg_distance_between_stations(bigint);

CREATE OR REPLACE FUNCTION avg_distance_between_stations(rel_id bigint)
  RETURNS double precision AS
$BODY$
DECLARE
	curr_way_id bigint;
	curr_sub_geom geometry;
	prev_sub_geom geometry;
	curr_distance float;
	is_substation smallint;
BEGIN
 FOR curr_way_id IN (select unnest(parts) from planet_osm_rels where osm_id = rel_id) LOOP
	/* RAISE NOTICE '%', curr_pole_id;*/
	is_substation = (select 1 from planet_osm_ways where id = curr_way_id and hstore(tags)->'power'~'substation|station|sub_station|plant|generator');
	if is_substation = 1 then	
		curr_sub_geom = (select create_polygon(id) from planet_osm_ways where id = curr_way_id);
		if not prev_sub_geom is null then
			curr_distance = st_distance(st_centroid(prev_sub_geom), st_centroid(curr_sub_geom));
			/*RAISE NOTICE '%', curr_distance;*/
			return curr_distance;
		end if;	
		prev_sub_geom = curr_sub_geom;
	else 
		prev_sub_geom = null;
	end if;
 END LOOP;
 return null;
END
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
ALTER FUNCTION avg_distance_between_stations(bigint)
  OWNER TO postgres;


-- Function: distance_between_stations(bigint)

-- DROP FUNCTION distance_between_stations(bigint);

CREATE OR REPLACE FUNCTION distance_between_stations(rel_id bigint)
  RETURNS double precision AS
$BODY$
DECLARE
	curr_way_id bigint;
	curr_sub_geom geometry;
	prev_sub_geom geometry;
	distance float;
	is_station smallint;
	num_stations smallint;
BEGIN
 FOR curr_way_id IN (select unnest(parts) from planet_osm_rels where id = rel_id) LOOP
	/* RAISE NOTICE '%', curr_pole_id;*/
	is_station = (select 1 from planet_osm_ways where id = curr_way_id and hstore(tags)->'power'~'substation|station|sub_station|plant|generator' and array_length(nodes, 1) >= 4 and st_isclosed(create_line(id)));
	if is_station = 1 then
		num_stations = (num_stations + 1);
		if num_stations > 2 then
			return null;
		end if;
		curr_sub_geom = (select create_polygon(id) from planet_osm_ways where id = curr_way_id);
		if not prev_sub_geom is null then
			distance = st_distance(st_centroid(prev_sub_geom), st_centroid(curr_sub_geom));
		end if;	
		prev_sub_geom = curr_sub_geom;
	end if;
 END LOOP;
 return distance;
END
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
ALTER FUNCTION distance_between_stations(bigint)
  OWNER TO postgres;


-- Function: line_distance_between_stations(bigint)

-- DROP FUNCTION line_distance_between_stations(bigint);

CREATE OR REPLACE FUNCTION line_distance_between_stations(rel_id bigint)
  RETURNS double precision AS
$BODY$
DECLARE
	curr_way_id bigint;
	line geometry;
	distance float;
	is_station smallint;
	is_line smallint;
	is_first_line smallint;
	num_stations smallint;
BEGIN            
 distance = 0;
 is_first_line = 1;
 is_station = 0;
 num_stations = 0;
 FOR curr_way_id IN (select unnest(parts) from planet_osm_rels where id = rel_id) LOOP
	/* RAISE NOTICE '%', curr_pole_id;*/
	is_station = (select 1 from planet_osm_ways where id = curr_way_id and hstore(tags)->'power'~'substation|station|sub_station|plant|generator' and array_length(nodes, 1) >= 4 and st_isclosed(create_line(id)));
	if is_station = 1 then
		num_stations = (num_stations + 1);
		if num_stations > 2 then
			return null;
		end if;
		/* RAISE NOTICE '% is substation', curr_way_id;*/
	else
		is_line = (select 1 from planet_osm_ways where id = curr_way_id and hstore(tags)->'power'~'line|cable|minor_line');
		if is_line = 1 then
			/* RAISE NOTICE '% is line', curr_way_id;*/
			distance = distance + st_length(create_line(curr_way_id));
		end if;
	end if;
 END LOOP;
 return distance;
END
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
ALTER FUNCTION line_distance_between_stations(bigint)
  OWNER TO postgres;
