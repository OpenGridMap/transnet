import logging

class InferenceValidator:
    cur = None

    root = logging.getLogger()

    def __init__(self, cur):
        self.cur = cur

    def validate(self, ssid, circuits, boundary):
        num_stations = self.num_stations(circuits)
        logging.info('In total %d stations covered with the inference', num_stations)
        sql = "select distinct(unnest(get_stations(r.parts))) from planet_osm_rels r, planet_osm_polygon s1"
        sql += ", planet_osm_polygon s2" if boundary is not None else ""
        sql += " where s1.osm_id = " + str(ssid) + " and s1.power ~ 'substation|station|sub_station' and s1.voltage ~ '220000|380000' and ARRAY[s1.osm_id]::bigint[] <@ r.parts"
        if boundary is not None:
            sql += " and (s2.power ~ 'substation|station|sub_station' and s2.voltage ~ '220000|380000' or s2.power ~ 'generator|plant') and ARRAY[s2.osm_id]::bigint[] <@ r.parts and st_within(s2.way, st_transform(st_geomfromtext('" + boundary.wkt + "',4269),900913))"
        self.cur.execute(sql)
        result = self.cur.fetchall()
        if not result:
            logging.info('No existing relation found for station %s', str(ssid))
            return None
        not_hit_stations = []
        hit_count = 0
        for (station,) in result:
            station_hit = False
            for circuit in circuits:
                if station == circuit.members[0].id or station == circuit.members[-1].id:
                    hit_count += 1
                    station_hit = True
                    break
            if not station_hit:
                not_hit_stations.append(station)
        logging.info('Found %d of %d connected stations to %s', hit_count, len(result), str(ssid))
        logging.info('Not hit stations: %s', str(not_hit_stations))
        return hit_count * 1.0 / len(result)

    def num_stations(self, circuits):
        stations = set()
        stations.clear()
        for circuit in circuits:
            stations.add(circuit.members[0])
            stations.add(circuit.members[-1])
        return len(stations)