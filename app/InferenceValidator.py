import logging

from Util import Util


class InferenceValidator:
    cur = None

    def __init__(self, cur):
        self.cur = cur

    def validate(self, ssid, circuits, boundary, voltage_levels):
        num_stations = self.num_stations(circuits)
        logging.info('In total %d stations covered with the inference', num_stations)
        sql = "select distinct(unnest(get_stations(r.parts))) from planet_osm_rels r, planet_osm_polygon s1"
        sql += ", planet_osm_polygon s2" if boundary is not None else ""
        sql += " where s1.osm_id = " + str(
            ssid) + " and s1.power ~ 'substation|station|sub_station' and s1.voltage ~ '" + voltage_levels + "' and ARRAY[s1.osm_id]::bigint[] <@ r.parts"
        if boundary is not None:
            sql += " and (s2.power ~ 'substation|station|sub_station' and s2.voltage ~ '220000|380000' or s2.power ~ 'generator|plant') and ARRAY[s2.osm_id]::bigint[] <@ r.parts and st_within(s2.way, st_transform(st_geomfromtext('" + boundary.wkt + "',4269),3857))"
        self.cur.execute(sql)
        result = self.cur.fetchall()
        if not result:
            logging.info('No existing relation found for station %s', str(ssid))
            return None
        not_hit_stations = []
        hits = 0
        for (station,) in result:
            station_hit = False
            for circuit in circuits:
                if station == circuit.members[0].id or station == circuit.members[-1].id:
                    hits += 1
                    station_hit = True
                    break
            if not station_hit:
                not_hit_stations.append(station)
        logging.info('Found %d of %d connected stations to %s', hits, len(result), str(ssid))
        logging.info('Not hit stations: %s', str(not_hit_stations))
        return hits * 1.0 / len(result)

    def validate2(self, circuits, stations_dict, boundary, voltage_levels):

        logging.info("Starting inference validation")
        sql = "select distinct(id), get_stations(r.parts), hstore(r.tags)->'voltage' from planet_osm_rels r, planet_osm_polygon s1, planet_osm_polygon s2"
        sql += " where (s1.power ~ 'substation|station|sub_station' and s1.voltage ~ '" + voltage_levels + "' or s1.power ~ 'generator|plant') and ARRAY[s1.osm_id]::bigint[] <@ r.parts and st_within(s1.way, st_transform(st_geomfromtext('" + boundary.wkt + "',4269),3857))"
        sql += " and (s2.power ~ 'substation|station|sub_station' and s2.voltage ~ '" + voltage_levels + "' or s2.power ~ 'generator|plant') and ARRAY[s2.osm_id]::bigint[] <@ r.parts and st_within(s2.way, st_transform(st_geomfromtext('" + boundary.wkt + "',4269),3857))"
        sql += " and s1.osm_id <> s2.osm_id and hstore(r.tags)->'route'='power'"
        self.cur.execute(sql)
        result = self.cur.fetchall()
        num_eligible_relations = len(result)
        hits = 0
        not_hit_connections = []
        for (id, station_ids, voltage) in result:
            if voltage is None or int(voltage) < 220000:
                sql = "select parts from planet_osm_rels where id = " + str(id)
                self.cur.execute(sql)
                result2 = self.cur.fetchall()
                for (parts,) in result2:
                    for part in parts:
                        sql = "select hstore(tags)->'voltage' from planet_osm_ways where id = " + str(part)
                        self.cur.execute(sql)
                        result3 = self.cur.fetchall()
                        if not result3:
                            voltage = None
                            continue
                        [(part_voltage,)] = result3
                        if part_voltage is None:
                            voltage = None
                            continue
                        if ';' not in part_voltage and ',' not in part_voltage and int(part_voltage) >= 220000:
                            voltage = part_voltage
                            break

            if voltage is None:
                logging.debug("Could not determine voltage of relation")
                num_eligible_relations -= 1
                continue

            relation_covered = False
            num_hit_p2p_connections = 0
            for circuit in circuits:
                if Util.have_common_voltage(circuit.voltage, voltage):
                    station1 = circuit.members[0]
                    station1_connected_stations = InferenceValidator.find_connected_stations(stations_dict, voltage,
                                                                                             station1.connected_stations[
                                                                                                 voltage],
                                                                                             set([station1.id]))
                    index1 = 0
                    index2 = index1 + 1
                    while index2 < len(station_ids):
                        if station_ids[index1] in station1_connected_stations and station_ids[
                            index2] in station1_connected_stations:
                            num_hit_p2p_connections += 1
                        index1 += 1
                        index2 = index1 + 1
                if num_hit_p2p_connections == len(station_ids) - 1:
                    relation_covered = True
                    break
            if relation_covered:
                hits += 1
            else:
                not_hit_connections.append(id)
        hit_rate = hits * 1.0 / num_eligible_relations
        logging.info('Found %d of %d eligible point-to-point connections (%.2lf)', hits, num_eligible_relations,
                     hit_rate)
        logging.info('Not hit point-to-point connections: %s', str(not_hit_connections))

    @staticmethod
    def find_connected_stations(stations, voltage, connected_stations, covered_stations):
        for station_id in connected_stations.difference(covered_stations):
            covered_stations.add(station_id)
            connected_stations.update(InferenceValidator.find_connected_stations(stations, voltage, stations[
                station_id].connected_stations[voltage], covered_stations))
        return connected_stations

    def num_stations(self, circuits):
        stations = set()
        stations.clear()
        for circuit in circuits:
            stations.add(circuit.members[0])
            stations.add(circuit.members[-1])
        return len(stations)
