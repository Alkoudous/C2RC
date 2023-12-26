from collections import defaultdict
# from src.scripts.Resource import Resource


class Reconciled:

    def __init__(self, component, connected, evidence, validated):

        self.component = component

        # SET OF INDEXES OF THE CONNECTED COMPONENTS
        self.connected = connected

        # SET OF RELATIONS ENABLING A CYCLE AND USED AS EVIDENCE
        self.evidence = evidence

        # LIST OF VALIDATED EDGES
        # VALIDATED is a dictionary for which a key is the validated edge and the value is the corroborated edge
        self.validated = validated

        # INDEXES OF VALIDATED VERTICES
        self.vertices = set()

        # LIST THE VALIDATED VERTICES FROM THE SOURCE AND POINTS TO THE EVIDENCE CLUSTER
        self.sub_vertices = defaultdict(set)

        # INDICATING WHETHER THE CLUSTER HAS BEEN CYCLE-CHECKED
        self.status = False

    def printer(self):
        n, nn = "\n\t\t", "\n\t"
        keys = list(self.validated.keys())
        print(F"""Component index     : {self.component}
    Connected       : {self.connected}
    Evidence Count  : {len(self.evidence)}
    Evidence        : 
           {" | ".join(F"{list(self.evidence)[x][0].label} --- {list(self.evidence)[x][1].label} [{list(self.evidence)[x][1].component}]{n if x != 0 and (x+1)%3==0 else ''}" for x in range(len(self.evidence)))}
    Validated       : 
           {" | ".join(F"{keys[i]} --> {list(self.validated[keys[i]])}{n if i != 0 and (i+1)%3==0 else ''}" for i in range(len(self.validated)))}
    Vertices Size   : {len(self.vertices)}
    Valid Vertices  : {self.vertices}
    Status          : {self.status}
    sub_vertices    : 
    {F'{nn}'.join(F'{key:3}: {val}' for key, val in self.sub_vertices.items())}
    """
              )

    def result(self):
        nn = "\n\t"
        size = len(self.sub_vertices)
        res = F"""
    Component index {self.component} was split into {size} sub-graph{'s' if size > 1 else ''}
    {F'{nn}'.join(F'{key:3}: {val}' for key, val in self.sub_vertices.items())}\n"""
        print(res)
