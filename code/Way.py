class Way:
    id = None
    type = None
    nodes = None
    tags = None
    name = None


    def __init__(self, id, type, name, nodes, tags):
        self.id = id
        self.type = type
        self.nodes = nodes
        self.tags = tags
        self.name = name

    def __str__(self):
        return 'ID: ' + str(self.id) + ' Type: ' + self.type

    def first_node(self):
        if self.nodes and len(self.nodes) > 0:
            return self.nodes[0]
        return None

    def last_node(self):
        if self.nodes and len(self.nodes) > 0:
            return self.nodes[len(self.nodes) - 1]
        return None
