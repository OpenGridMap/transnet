DO
$$
DECLARE
	curr_pole_id bigint;
	prev_pole_geom geometry;
	curr_pole_geom geometry;
	prev_determined smallint;
	curr_distance float;
	distances float[];
	avg_distance float;
BEGIN
 prev_determined = 0;
 FOR curr_pole_id IN (select unnest(nodes) from planet_osm_ways where id = 35076222) LOOP
	RAISE NOTICE '%', curr_pole_id;

	curr_pole_geom = (select ST_SetSRID(ST_MakePoint(lon/100.0,lat/100.0),900913) from planet_osm_nodes where id = curr_pole_id);
	if prev_determined = 1 then
		curr_distance = st_distance(prev_pole_geom, curr_pole_geom);
		RAISE NOTICE '%', curr_distance;
		distances = array_append(distances, curr_distance);
	end if;	
	prev_pole_geom = curr_pole_geom;
	prev_determined = 1;
 END LOOP;
 avg_distance = array_avg(distances);
 RAISE NOTICE 'Average: %', avg_distance;
END
$$