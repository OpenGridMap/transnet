from Way import Way

class Station(Way):

    def __init__(self, id, geom, type, name, nodes, tags):
        Way.__init__(self, id, geom, type, name, nodes, tags)

    def __str__(self):
        return 'Station - ' + Way.__str__(self)