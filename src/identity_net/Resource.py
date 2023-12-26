class Resource:

    def __init__(self, uri, label=None, alt_name=None, interchange=True):
        self.index = None
        self.uri = uri
        self.label = uri if interchange else label
        self.component = None
        self.alt_name = alt_name
        self.neighbors = set()

    def set_index(self, index):
        self.index = index

    def set_component(self, index):
        self.component = index

    def update_neighbors(self, vertex):
        self.neighbors.update(vertex)

    def printer(self):
        return F"""
        Component : {self.component} 
        Index     : {self.index} 
        Label     : {self.label} 
        URI       : {self.uri}
        neighbors : {" | ".join(F"{x}" for x in self.neighbors)}\n"""
