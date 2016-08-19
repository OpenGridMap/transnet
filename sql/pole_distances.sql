SELECT
  id,
  voltage,
  distance
FROM (SELECT
        id,
        hstore(tags) -> 'voltage'      AS voltage,
        avg_distance_between_poles(id) AS distance
      FROM planet_osm_ways
      WHERE hstore(tags) -> 'power' ~ 'line' AND hstore(tags) -> 'voltage' ~ E'^[0,1,2,3,4,5,6,7,8,9]+$' AND
            ((hstore(tags) -> 'voltage') :: INTEGER = 110000 OR (hstore(tags) -> 'voltage') :: INTEGER = 220000 OR
             (hstore(tags) -> 'voltage') :: INTEGER = 380000 OR (hstore(tags) -> 'voltage') :: INTEGER = 400000)) m
WHERE distance IS NOT NULL AND distance <= 1000