SELECT *
FROM (SELECT
        osm_id,
        distance_between_stations(osm_id)      AS distance,
        line_distance_between_stations(osm_id) AS line_distance,
        voltage
      FROM _analysis_rels
      WHERE num_stations = 2 AND incomplete = 'no') m
WHERE distance IS NOT NULL AND line_distance IS NOT NULL AND distance > 0 AND line_distance > 0 AND
      (voltage = 110000 OR voltage = 220000 OR voltage = 380000 OR voltage = 400000)