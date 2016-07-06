CREATE OR REPLACE FUNCTION create_line(way_id bigint)
  RETURNS geometry AS
$BODY$
BEGIN
 return st_makeline((select array_agg(ST_SetSRID(ST_MakePoint(lon/100.0,lat/100.0),3857)) from planet_osm_nodes n, (select unnest(nodes) as node from planet_osm_ways where id = way_id) w where n.id = node));
END
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

CREATE OR REPLACE FUNCTION create_point(node_id bigint)
  RETURNS geometry AS
$BODY$
BEGIN
 return (select ST_SetSRID(ST_MakePoint(lon/100.0,lat/100.0),3857) from planet_osm_nodes where id = node_id);
END
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

CREATE OR REPLACE FUNCTION create_polygon(way_id bigint)
  RETURNS geometry AS
$BODY$
BEGIN
 return st_setsrid(st_makepolygon(st_makeline((select array_agg(ST_SetSRID(ST_MakePoint(lon/100.0,lat/100.0),3857)) from planet_osm_nodes n, (select unnest(nodes) as node from planet_osm_ways where id = way_id) w where n.id = node))),3857);
END
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

CREATE OR REPLACE FUNCTION get_stations(parts bigint[])
  RETURNS bigint[] AS
$BODY$
BEGIN
 return (select array_agg(s.osm_id) from planet_osm_polygon s where ARRAY[s.osm_id]::bigint[] <@ parts and (s.power ~ 'substation|station|sub_station' and s.voltage ~ '220000|380000' or s.power ~ 'plant|generator'));
END
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;
