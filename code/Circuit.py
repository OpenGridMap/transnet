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

    def print_overpass(self):
        overpass = ''
        for way in self.members:
            overpass += 'way(' + str(way.id) + ');'
        print(overpass)

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