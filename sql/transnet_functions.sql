CREATE OR REPLACE FUNCTION create_line(way_id BIGINT)
  RETURNS geometry AS
$BODY$
BEGIN
  RETURN st_makeline((SELECT array_agg(ST_SetSRID(ST_MakePoint(lon / 100.0, lat / 100.0), 3857))
                      FROM planet_osm_nodes n, (SELECT unnest(nodes) AS node
                                                FROM planet_osm_ways
                                                WHERE id = way_id) w
                      WHERE n.id = node));
END
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;

CREATE OR REPLACE FUNCTION create_point(node_id BIGINT)
  RETURNS geometry AS
$BODY$
BEGIN
  RETURN (SELECT ST_SetSRID(ST_MakePoint(lon / 100.0, lat / 100.0), 3857)
          FROM planet_osm_nodes
          WHERE id = node_id);
END
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;

CREATE OR REPLACE FUNCTION create_polygon(way_id BIGINT)
  RETURNS geometry AS
$BODY$
BEGIN
  RETURN st_setsrid(
      st_makepolygon(st_makeline((SELECT array_agg(ST_SetSRID(ST_MakePoint(lon / 100.0, lat / 100.0), 3857))
                                  FROM planet_osm_nodes n, (SELECT unnest(nodes) AS node
                                                            FROM planet_osm_ways
                                                            WHERE id = way_id) w
                                  WHERE n.id = node))), 3857);
END
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;

CREATE OR REPLACE FUNCTION get_stations(parts BIGINT [])
  RETURNS BIGINT [] AS
$BODY$
BEGIN
  RETURN (SELECT array_agg(s.osm_id)
          FROM planet_osm_polygon s
          WHERE ARRAY [s.osm_id] :: BIGINT [] <@ parts AND
                (s.power ~ 'substation|station|sub_station' AND s.voltage ~ '220000|380000' OR
                 s.power ~ 'plant|generator'));
END
$BODY$
LANGUAGE plpgsql VOLATILE
COST 100;
