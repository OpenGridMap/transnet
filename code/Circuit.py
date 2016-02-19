import sys

class Circuit:
    members = None
    voltage = None
    name = None
    ref = None

    def __init__(self, members, voltage, name, ref):
        self.members = members
        self.voltage = voltage
        self.name = name
        self.ref = ref

    @staticmethod
    def print_relation(relation):
        string = ''
        overpass = ''
        for way in relation:
            string += str(way) + '\n'
            overpass += 'way(' + str(way.id) + ');'
        print(string + overpass)

    def print_circuit(self):
        Circuit.print_relation(self.members)
        s = list('')
        if self.name:
            s.append('Name: ' + self.name)
        if self.ref:
            s.append(' Ref: ' + self.ref)
        if self.voltage:
            s.append(' Voltage: ' + self.voltage)
        print(''.join(s))
        print('')

    def validate(self, cur, circuit_no):
        first_station = self.members[0]
        last_station = self.members[len(self.members) - 1]
        sql = "select id, parts from planet_osm_rels where ARRAY[ " + str(first_station.id) + ", " + str(last_station.id) + "]::bigint[] <@ parts::bigint[]"
        cur.execute(sql)
        result = cur.fetchall()
        most_similar_relation = None
        max = 0
        for (id, parts) in result:
            print("Found substation-covering relation (Id=" + str(id) + "; Parts=" + str(parts))
            covered_parts = 0
            for part in parts:
                for member in self.members:
                    if part == member.id:
                        covered_parts += 1
                        break
            if covered_parts > max:
                max = covered_parts
                most_similar_relation = (id, parts)
        if most_similar_relation:
            accuracy = max * 1.0/len(self.members)
            print("Most similar relation is " + str(most_similar_relation[0]) + " with " + str(accuracy*100) + "% coverage")
            if accuracy < 1:
                print(str(most_similar_relation[1]) + " (Existing relation)")
                print(str(self.to_member_id_list()) + " (Estimated relation)")
            if len(most_similar_relation[1]) < len(self.members):
                sys.stderr.write("Warning at circuit " + str(circuit_no) + ": #existing < #estimated parts\n")
            return (most_similar_relation[0], accuracy)
        return 0


    def to_member_id_list(self):
        id_list = []
        for member in self.members:
            id_list.append(member.id)
        return id_list




