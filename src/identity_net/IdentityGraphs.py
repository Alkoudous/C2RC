import numpy
from itertools import product
from graph_tool.all import*
from copy import deepcopy
from collections import defaultdict, Counter
from src.identity_net.Resource import Resource
from src.identity_net.Reconciled import Reconciled


# Introduction to Network Mathematics   :   http://edshare.soton.ac.uk/922/2/index.html#graph
# Converting NetworkX to Graph-Tool     :   https://bbengfort.github.io/2016/06/graph-tool-from-networkx/
# Graph Tool Documentation              :   https://graph-tool.skewed.de/static/doc/index.html
# Lenticular Lens Tool                  :   https://lenticularlens.goldenagents.org/
# https://www.samotics.com/about/about-us


class Parameters:

    def __init__(self):
        self.size = "size"
        self.birth = "birth"
        self.mother = "mother"
        self.father = "father"
        self.married = "married"
        self.divorced = "divorced"
        self.children = "children"
        self.children_with_more_than_one_parents = "children_with_more_than_one_parents"
        self.married_children = "married_children"
        self.max_consecutive_age_diff = "max_consecutive_age_diff"
        self.last_first_age_diff = "last_first_age_diff"
        self.associated_clusters = "associated_clusters"
        self.grounded_resources = "grounded_resources"
        self.expected_sub_reconstitutions = "expected_sub_reconstitutions"
        self.likely = "likely"
        self.unlikely = "unlikely"
        self.uncertain = "uncertain"

    def size(self):
        return self.size

    def birth(self):
        return self.birth

    def mother(self):
        return self.mother

    def father(self):
        return self.father

    def married(self):
        return self.married

    def divorced(self):
        return self.divorced

    def children(self):
        return self.children

    def children_with_more_than_one_parents(self):
        return self.children_with_more_than_one_parents

    def married_children(self):
        return self.married_children

    def max_consecutive_age_diff(self):
        return self.max_consecutive_age_diff

    def last_first_age_diff(self):
        return self.last_first_age_diff

    def associated_clusters(self):
        return self.associated_clusters

    def grounded_resources(self):
        return self.grounded_resources

    def expected_sub_reconstitutions(self):
        return self.expected_sub_reconstitutions

    def likely(self):
        return self.likely

    def unlikely(self):
        return self.unlikely

    def uncertain(self):
        return self.uncertain


class IdentityGraphs:

    def __init__(self, links: list):

        # This initializer CREATES a graph with the predefined number of vertices,
        # SETS the graph as UNDIRECTED and INITIALISES a vertex and edge properties
        # for assigning respectively a text and a weight information to the network.

        self.relations_map = defaultdict(list)

        # Indexes of vertices and edges list
        index, edges = 0, []
        # Dictionary of vertices' index based on links
        # It maps a URI to its vertex index
        self.vertices = defaultdict(int)
        self.vertices.default_factory = lambda: None
        # Maps the components and the reconciled object
        self.reconciliations = defaultdict(Reconciled)
        # Map an index to the resource it represents
        self.resources = defaultdict(dict)
        self.cycles = defaultdict(set)
        self.validated = set()
        # New edges generated due to new evidence obtained from the added relations
        self.new_edges = []

        # Initialisation
        self.graphs = Graph(directed=False)
        self.graphs.vp["label"] = self.graphs.new_vertex_property("string")
        self.graphs.vp["index"] = self.graphs.new_vertex_property("string")
        self.graphs.vp["validations"] = self.graphs.new_vertex_property("bool")
        self.graphs.vp["components"] = self.graphs.new_vertex_property("bool")
        self.graphs.ep["weight"] = self.graphs.new_edge_property("float")
        self.graphs.ep["inverted_weight"] = self.graphs.new_edge_property("float")
        self.graphs.ep["validations"] = self.graphs.new_edge_property("bool")

        self.v_validations, self.v_components = self.graphs.vp["validations"], self.graphs.vp["validations"]
        self.v_labels, self.v_index = self.graphs.vp["label"], self.graphs.vp["index"],
        self.e_weights, self.e_validations = self.graphs.ep["weight"], self.graphs.ep["validations"]
        self.e_inv_weights = self.graphs.ep["inverted_weight"]

        # Generate the vertices indexes
        for (sbj, obj, w) in links:

            if sbj.uri not in self.vertices:
                sbj.set_index(index)
                # MAPPING A VERTEX INDEX TO THE ACTUAL RESOURCE
                self.resources[index] = sbj
                # MAPPING THE ACTUAL VERTEX NODE TO ITS INDEX
                self.vertices[sbj.uri] = index
                # MAPPING THE VERTEX INDEX TO A LABEL
                self.v_labels[index] = sbj.label
                # VERTEX INDEX
                # self.graphs.vp["Index"][index] = index
                # VERTEX SHORT NAME
                # self.v_index[index] = F"{sbj.label[0]}{index}"
                # VERTEX ALTERNATE NAME
                # self.v_index[index] = F"{sbj.alt_name}-{index}"
                # VERTEX URI
                self.v_index[index] = F"{sbj.uri}"
                index += 1

            if obj.uri not in self.vertices:
                obj.set_index(index)
                self.resources[index] = obj
                self.vertices[obj.uri] = index
                self.v_labels[index] = obj.label
                # VERTEX INDEX
                # self.graphs.vp["Index"][index] = index
                # VERTEX SHORT NAME
                # self.v_index[index] = F"{obj.label[0]}{index}"
                # VERTEX ALTERNATE NAME
                # self.v_index[index] = F"{obj.alt_name}-{index}"
                # VERTEX URI
                self.v_index[index] = F"{obj.uri}"
                index += 1

            # print(sbj.label, obj.label)
            # edg = self.graphs.edge(self.vertices[sbj.uri], self.vertices[obj.uri])
            # self.e_weights[edg] = 1.0
            # self.graphs.ep.validation[index] = 1
            edges.append((self.vertices[sbj.uri], self.vertices[obj.uri]))

            # e = self.graphs.add_edge(self.vertices[sbj.uri], self.vertices[obj.uri])
            edge = self.graphs.add_edge(self.vertices[sbj.uri], self.vertices[obj.uri])
            self.e_weights[edge] = w
            self.e_inv_weights[edge] = 1-float(w)

        # Create a graph of n vertices
        # self.graphs.add_vertex(len(self.vertices))

        # Add the edges to the created graph
        # self.graphs.add_edge_list(edges)

        # Label the components to which each vertex in the graph belongs.
        comp, self.hist = label_components(self.graphs, attractors=False)

        # LIST COMPONENTS BASED ON VERTICES INDEX
        self.components = comp.a

        # SET OF CLUSTER INDEXES
        # self.clusters = set(self.components)
        self.clusters_and_sizes = Counter(self.components)

        # LIST OF VERTEX INDEX IN A STRING TYPE
        self.vertex_index = [F"{pos}" for pos in self.graphs.get_vertices()]

        self.graphs_copy = Graph(self.graphs)

        # print(list(all_circuits(self.graphs, unique=True)))

    def get_clusters_label(self, relation: (Resource, Resource)):

        # Given two linked resources, the function returns a label
        # representing the clusters the two resources belong too.

        src_v_uri, trg_v_uri = self.vertices[relation[0].uri], self.vertices[relation[1].uri]
        source_comp, target_comp = self.components[src_v_uri], self.components[trg_v_uri]

        # A PAIR OF VERTICES
        if (isinstance(source_comp, numpy.int32) and isinstance(target_comp, numpy.int32)) and \
                source_comp != target_comp:

            relation[0].set_component(source_comp)
            relation[1].set_component(target_comp)

            # ASSIGNING THE COMPONENT A VERTEX RESOURCE BELONGS TO
            self.resources[src_v_uri].set_component(source_comp)
            self.resources[trg_v_uri].set_component(target_comp)

            # ASSIGNING THE NEIGHBORS OF A VERTEX
            self.resources[src_v_uri].update_neighbors(set(self.graphs.get_all_neighbors(src_v_uri)))
            self.resources[trg_v_uri].update_neighbors(set(self.graphs.get_all_neighbors(trg_v_uri)))

            # CONNECTED COMPONENTS USING A RELATION
            label = F"{source_comp} {target_comp}" \
                if self.clusters_and_sizes[source_comp] < self.clusters_and_sizes[target_comp] \
                else F"{target_comp} {source_comp}"

            # print(label)
            return label,  (source_comp, target_comp), (src_v_uri, trg_v_uri)

        # A SINGLE VERTEX
        else:
            return None, (None, None), (None, None)

    @staticmethod
    def reconciliation_strength(weights_sum, path_length, evidenceStrength=80):
        penalty = 100 - evidenceStrength
        elongated_distance = 2 * path_length - weights_sum
        return (100 - penalty * elongated_distance) / 100

    def consolidate(self, component_ID, cluster_ID):

        links, results = [], defaultdict(set)
        if len(self.reconciliations) == 0:
            # "\tNo consolidation needed"
            return None
        reconciled = self.reconciliations[component_ID]

        # DESCRIPTIVE INFO BEFORE
        n, nn, nnn, size = "\n\t\t", "\n\t\t\t", "\n", len(reconciled.sub_vertices)
        res1 = F"""\tComponent index {cluster_ID} was split into {size} sub-graph{'s' if size > 1 else ''}
            {F''.join(
            F'{n}Using component {key}, {len(val)} vertices got validated {nn}'
            F'{[self.vertices[v] for v in val]}{nnn}' for key, val in reconciled.sub_vertices.items())}"""

        # CREATE THE LINKS AND SET THE GRAPH
        for (src, trg) in reconciled.validated.keys():
            links.append((Resource(src, src), Resource(trg, trg), 1))
        graphs = IdentityGraphs(links)

        # THIS PRODUCES A SUBSET OF VERTICES WITH THE RESPECTIVE URI INSTEAD OF
        # THE INDEX TAS HE NEW INDEX MAY NOT CORRESPOND TO THE ORIGINAL INDEX
        # BUT USING THE URI, THE ORIGINAL INDEX MAY BE RECOVERED USING THE
        # VERTICES PROPERTY OF IdentityGraphs
        for i in range(len(graphs.components)):
            # uri = g.v_index[i]
            # index = self.vertices[uri]
            results[graphs.components[i]].add(self.vertices[graphs.v_index[i]])

        # RESET THE CONSOLIDATED
        reconciled.sub_vertices = results

        # DESCRIPTIVE INFO AFTER
        size = len(reconciled.sub_vertices)
        complete = F"All vertices of cluster {cluster_ID} are validated and not split."
        partial = F"*** Cluster {cluster_ID} is split into {size} sub-graph{'s' if size > 0 else ''}"

        # FIND THE COMPONENT OF FIRST VERTEX AT THE FIRST KEY
        first_vertices = list(reconciled.sub_vertices[list(reconciled.sub_vertices.keys())[0]])
        # FIRST BAG OF VERTICES
        first_vertex = first_vertices[0]
        # THE COMPONENT TO WHICH THE FIRST VERTEX FROM THE FIRST KEY
        comp = self.components[first_vertex]
        comp_size = self.clusters_and_sizes[comp]
        res2 = F"""\t{complete if len(reconciled.sub_vertices) == 1 
                                  and len(first_vertices) == comp_size else partial}
            {F''.join(
        F'{n}Using component {key}, {len(val)} vertices got validated {nn}'
        F'{[v for v in val]}{nnn}' for key, val in results.items())}"""

        return res1 if size < len(reconciled.sub_vertices) else res2

    def rec_cycles(self, relations):

        # The function looks for pairs of clusters for which there exist cycles induced by two or more relations.
        # It then returns a dictionary with the label of linked components as the key of the dictionary and the
        # set of at least two relation-links that enable a cycle hence serve as co-referent evidence for validation.

        temp = defaultdict()
        for relation in relations:
            # Mapping the relations
            if self.vertices[relation[0].uri] is not None and self.vertices[relation[1].uri] is not None:
                self.relations_map[self.vertices[relation[0].uri]].append(self.vertices[relation[1].uri])
                self.relations_map[self.vertices[relation[1].uri]].append(self.vertices[relation[0].uri])

        # FINDING CYCLES
        for relation in relations:

            # Extracting the component pair-name, the source and target components and the source and target resources
            linked_components, (src_comp, trg_comp), (src_v, trg_v) = self.get_clusters_label(relation)

            # E=scape condition
            if linked_components is None:
                continue

            # print(linked_components, relation[0].label, relation[1].label)
            # print(src_v, self.graphs.get_all_neighbors(src_v))

            # First edge in temp for a possible cycle
            if linked_components not in temp:
                # Label of the linked components associated to the relation
                temp[linked_components] = relation

            # Edges of a cycle
            else:

                temp_relation = temp[linked_components]
                lbl_of_linked_components, (tp_s_comp, tp_t_comp), (tp_s_v, tp_t_v) = \
                    self.get_clusters_label(temp_relation)

                # ------------------
                # FIRST CYCLE
                # ------------------
                if linked_components not in self.cycles:

                    # ==========================================
                    # THE FINDING OF A CYCLE FOR TWO COMPONENTS
                    # ==========================================

                    # The linked components in temp and its relation
                    self.cycles[linked_components] = {temp_relation}

                    # The current relation for the same connected components
                    self.cycles[linked_components].add(deepcopy(relation))

                    # ==========================================
                    # RECONCILED COMPONENTS AND EVIDENCE
                    # ==========================================

                    # CURRENT SOURCE RELATION
                    if src_comp not in self.reconciliations:
                        self.reconciliations[src_comp] = Reconciled(
                            component=src_comp, connected={src_comp, trg_comp},
                            evidence={deepcopy(relation)}, validated=defaultdict(set))
                    else:
                        self.reconciliations[src_comp].connected.add(trg_comp)
                        self.reconciliations[src_comp].evidence.add(deepcopy(relation))

                    # CURRENT TARGET RELATION
                    if trg_comp not in self.reconciliations:
                        self.reconciliations[trg_comp] = Reconciled(
                            component=trg_comp, connected={src_comp, trg_comp},
                            evidence={deepcopy(relation)}, validated=defaultdict(set))
                    else:
                        self.reconciliations[trg_comp].connected.add(trg_comp)
                        self.reconciliations[trg_comp].evidence.add(deepcopy(relation))

                    # TEMP SOURCE RELATION
                    if tp_s_comp not in self.reconciliations:
                        self.reconciliations[tp_s_comp] = Reconciled(
                            component=tp_s_comp, connected={tp_s_comp, tp_t_comp},
                            evidence={temp_relation}, validated=defaultdict(set))
                    else:
                        self.reconciliations[tp_s_comp].connected.add(trg_comp)
                        self.reconciliations[tp_s_comp].evidence.add(deepcopy(temp_relation))

                    # TEMP TARGET RELATION
                    if tp_t_comp not in self.reconciliations:
                        self.reconciliations[tp_t_comp] = Reconciled(
                            component=tp_t_comp, connected={tp_s_comp, tp_t_comp},
                            evidence={deepcopy(temp_relation)}, validated=defaultdict(set))
                    else:
                        # UPDATING THE CYCLE
                        self.reconciliations[tp_t_comp].connected.add(tp_s_comp)
                        self.reconciliations[tp_t_comp].evidence.add(deepcopy(temp_relation))

                    # ==========================================
                    # REGISTERING VALIDATED EDGES
                    # # ==========================================

                    # print(self.components[src_v], self.components[tp_s_v])
                    # print(src_v, tp_s_v)
                    # print(trg_comp, tp_t_v)

                    # IN CASE OF NON INVERTED COMPONENTS
                    # ALPHA OF [1] <-----> JULIETTE OF [2]
                    # ECHO OF [1]  <-----> INDIA OF [2]
                    if self.components[src_v] == self.components[tp_s_v]:

                        # FINDING A VALIDATED EDGE FOR THE SOURCE COMPONENT
                        s_corroborated_by = self.corroborated_by(investigated=[src_v, tp_s_v])

                        if self.resources[src_v] != self.resources[tp_s_v]:
                            self.reconciliations[src_comp].validated[
                                (self.resources[src_v].label,
                                 self.resources[tp_s_v].label)].update(s_corroborated_by)
                            self.validated.add((self.resources[src_v].index, self.resources[tp_s_v].index))

                        # FINDING A VALIDATED EDGE FOR THE TARGET COMPONENT
                        t_corroborated_by = self.corroborated_by(investigated=[trg_v, tp_t_v])

                        if self.resources[trg_v] != self.resources[tp_t_v]:
                            self.reconciliations[trg_comp].validated[(
                                self.resources[trg_v].label, self.resources[tp_t_v].label)].update(t_corroborated_by)
                            self.validated.add((self.resources[trg_v].index, self.resources[tp_t_v].index))

                    # IN CASE OF INVERTED COMPONENTS
                    # ALPHA OF [1] <-----> JULIETTE OF [2]
                    # INDIA OF [2] <-----> ECHO OF [1]
                    else:

                        # FINDING A VALIDATED EDGE FOR THE SOURCE COMPONENT
                        s_corroborated_by = self.corroborated_by(investigated=[src_v, tp_t_v])

                        if self.resources[src_v] != self.resources[tp_t_v]:
                            self.reconciliations[src_comp].validated[(
                                self.resources[src_v].label, self.resources[tp_t_v].label)].update(s_corroborated_by)
                            self.validated.add((self.resources[src_v].index, self.resources[tp_t_v].index))

                        # FINDING A VALIDATED EDGE FOR THE TARGET COMPONENT
                        t_corroborated_by = self.corroborated_by(investigated=[trg_v, tp_s_v])

                        if self.resources[trg_v] != self.resources[tp_s_v]:
                            self.reconciliations[trg_comp].validated[
                                (self.resources[trg_v].label, self.resources[tp_s_v].label)].update(t_corroborated_by)
                            self.validated.add((self.resources[trg_v].index, self.resources[tp_s_v].index))

                    # UPDATING THE INVOLVED VERTICES AS A CONSEQUENCE OF OF THE CURRENT RELATION
                    self.reconciliations[src_comp].vertices.add(self.resources[src_v].index)
                    self.reconciliations[trg_comp].vertices.add(self.resources[trg_v].index)
                    # UPDATING THE INVOLVED VERTICES AS A CONSEQUENCE OF OF THE TEMPORARY RELATION
                    self.reconciliations[src_comp].sub_vertices[trg_comp].add(self.resources[src_v].index)
                    self.reconciliations[trg_comp].sub_vertices[src_comp].add(self.resources[trg_v].index)

                    # UPDATING THE INVOLVED VERTICES AS A CONSEQUENCE OF OF THE CURRENT RELATION
                    self.reconciliations[tp_s_comp].vertices.add(self.resources[tp_s_v].index)
                    self.reconciliations[tp_t_comp].vertices.add(self.resources[tp_t_v].index)
                    # UPDATING THE INVOLVED SUB-VERTICES AS A CONSEQUENCE OF OF THE TEMPORARY RELATION
                    self.reconciliations[tp_s_comp].sub_vertices[tp_t_comp].add(self.resources[tp_s_v].index)
                    self.reconciliations[tp_t_comp].sub_vertices[tp_s_comp].add(self.resources[tp_t_v].index)

                    # # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

                # ------------------
                # MORE CYCLE EDGES
                # ------------------
                else:
                    self.cycles[linked_components].add(relation)
                    # print(linked_components, relation[0].label, relation[1].label, "\n")
                    # UPDATING THE CYCLE
                    self.reconciliations[src_comp].connected.add(trg_comp)
                    self.reconciliations[trg_comp].connected.add(src_comp)
                    self.reconciliations[src_comp].evidence.add(deepcopy(relation))
                    self.reconciliations[trg_comp].evidence.add(deepcopy(relation))

                    # FINDING A VALIDATED EDGE FOR THE TARGET COMPONENT
                    for vertex in self.reconciliations[src_comp].sub_vertices[trg_comp]:
                        # print("B", src_comp, vertex, self.resources[src_v].label, self.resources[vertex].label)
                        # validated relation as label
                        s_corroborated_by = self.corroborated_by(investigated=[src_v, vertex])

                        if self.resources[src_v] != self.resources[vertex]:
                            self.reconciliations[src_comp].validated[
                                (self.resources[src_v].label, self.resources[vertex].label)].update(s_corroborated_by)

                            # validated relation as index
                            self.validated.add((self.resources[src_v].index, self.resources[vertex].index))

                    # print("")
                    # FINDING A VALIDATED EDGE FOR THE SOURCE COMPONENT
                    for vertex in self.reconciliations[trg_comp].sub_vertices[src_comp]:
                        # print("A", trg_comp, vertex, self.resources[trg_v].label, self.resources[vertex].label)
                        t_corroborated_by = self.corroborated_by(investigated=[trg_v, vertex])

                        if self.resources[trg_v].label != self.resources[vertex]:
                            self.reconciliations[trg_comp].validated[
                                (self.resources[trg_v].label, self.resources[vertex].label)].update(t_corroborated_by)

                            # validated relation as index
                            self.validated.add((self.resources[trg_v].index, self.resources[vertex].index))

                    # UPDATING THE INVOLVED VERTICES
                    self.reconciliations[trg_comp].vertices.add(self.resources[trg_v].index)
                    self.reconciliations[src_comp].vertices.add(self.resources[src_v].index)
                    # UPDATING THE INVOLVED SUB-VERTICES
                    self.reconciliations[src_comp].sub_vertices[trg_comp].add(self.resources[src_v].index)
                    self.reconciliations[trg_comp].sub_vertices[src_comp].add(self.resources[trg_v].index)

    def apply_validation(self):

        print("\nDistance per validated edges")
        for (src, trg) in self.validated:

            edg = self.graphs.edge(src, trg)

            # EXISTING VERTICES
            if edg:

                # Validated Edge
                self.e_validations[edg] = True
                self.v_validations[src] = True
                self.v_validations[trg] = True

                # # The shortest path from the source to the target
                # d_before = shortest_distance(
                #     g=self.graphs_copy, source=src, target=trg,
                #     weights=self.graphs_copy.ep["weight"]) / shortest_distance(
                #     g=self.graphs_copy, source=src, target=trg)
                #
                # d_after = i(
                #     g=self.graphs, source=src, target=trg, weights=self.e_weights)
                #
                # self.e_weights[edg] = d_before * d_after
                # print(F"Old \t{src:2} ---> {trg:>2} \tBefore {self.e_weights[edg] :5} \tAfter {self.e_weights[edg] }")

            # NEW GENERATED VERTICES
            else:

                # As the edge does not exist, add it to the graph
                self.graphs.add_edge(src, trg)
                # Extract the just created edge
                edg = self.graphs.edge(src, trg)
                # Assign the TRUE boolean value indicated that the edge has been validated
                self.e_validations[edg] = True
                self.v_validations[src] = True
                self.v_validations[trg] = True
                self.new_edges.append(edg)
                # self.e_weights[edg] = 1
                # print("*", src, trg)

                d_before = shortest_distance(
                    g=self.graphs_copy, source=src, target=trg,
                    weights=self.graphs_copy.ep["weight"]) / shortest_distance(
                    g=self.graphs_copy, source=src, target=trg)

                d_after = 1
                self.e_weights[edg] = d_before if d_before != 0 else d_after

                print(F"New \t{src} ---> {trg} \tBefore {round(d_before, 3) :5} \tAfter {round(d_after, 3)}")
                for path in all_shortest_paths(self.graphs_copy, src, trg, dist_map=self.graphs_copy.ep["weight"]):
                    print(F"\t\t---> {path}")

            # print(F"\t{src:2} --> {trg:2}\t\tBefore:{round(d_before,5):<6}\t\tAfter:{round(d_after,5):<6}")
        print()

    def print_reconciliations(self, component=None):

        if component is not None and len(self.reconciliations) > 0:
            self.reconciliations[component].printer()
        else:
            for component_index, reconciled in self.reconciliations.items():
                reconciled.printer()

    def print_reconciliations_results(self, component=None):

        if component is not None:
            self.reconciliations[component].result()
        else:
            for component_index, reconciled in self.reconciliations.items():
                reconciled.result()

    def draw(self, name):
        # weight = g.ep["weight"]
        # edge_pen_width = weight,
        # , edge_color = [0.1]
        graph_draw(self.graphs, vertex_text=self.v_index,
                   vertex_shape="double_circle", vertex_font_size=9, vertex_pen_width=2,
                   output=F"{name}.pdf")

    def draw_component_DEL(self, clusterID, component_ID):
        # weight = g.ep["weight"]
        # edge_pen_width = weight,
        # , edge_color = [0.1]

        # comp, self.hist = label_components(self.graphs, attractors=False)
        # temp_comp = comp.a

        copy = deepcopy(self.v_validations)
        for i in range(len(self.components)):
            if self.components[i] == component_ID and self.v_validations[i]:
                # self.v_components[i] = True
                pass
            else:
                self.v_validations[i] = False

        self.graphs.set_vertex_filter(self.v_validations)
        # self.graphs.set_vertex_filter(self.v_components)

        graph_draw(self.graphs, vertex_text=self.v_index,
                   vertex_shape="double_circle", vertex_font_size=8, vertex_pen_width=2,
                   output=F"{clusterID}-Component-{component_ID}.pdf")

        print(F"\t===> Done printing {clusterID}-Component-{component_ID}.pdf\n")
        self.v_validations = copy
        self.graphs.clear_filters()

    def draw_component_DEL2(self, clusterID, component_ID):
        # weight = g.ep["weight"]
        # edge_pen_width = weight,
        # , edge_color = [0.1]
        # comp, self.hist = label_components(self.graphs, attractors=False)
        # temp_comp = comp.a

        copy = deepcopy(self.v_validations)
        for key, sub_vertices in self.reconciliations[component_ID].sub_vertices.items():
            for i in range(len(self.components)):
                if self.components[i] == component_ID and self.v_validations[i] and i in sub_vertices:
                    # self.v_components[i] = True
                    pass
                else:
                    self.v_validations[i] = False

            # print(list(self.v_validations))
            self.graphs.set_vertex_filter(self.v_validations)
            # self.graphs.set_vertex_filter(self.v_components)

            graph_draw(self.graphs, vertex_text=self.v_index,
                       vertex_shape="double_circle", vertex_font_size=8, vertex_pen_width=2,
                       output=F"{clusterID}-Component-{component_ID}-{key}.pdf")

            print(F"\t===> Done printing {clusterID}-Component-{component_ID}-{key}.pdf")
            self.v_validations = deepcopy(copy)
        self.graphs.clear_filters()

    def draw_component(self, clusterID, component_ID):
        # weight = g.ep["weight"]
        # edge_pen_width = weight,
        # , edge_color = [0.1]
        # comp, self.hist = label_components(self.graphs, attractors=False)
        # temp_comp = comp.a

        copy = deepcopy(self.v_validations)
        for key, sub_vertices in self.reconciliations[component_ID].sub_vertices.items():
            for i in range(len(self.components)):
                if self.v_validations[i] and i in sub_vertices:
                    # FOR PRINTING ALL SUB-GRAPHS IN A SINGLE PLOT
                    # self.v_components[i] = True
                    pass
                else:
                    self.v_validations[i] = False

            self.graphs.set_vertex_filter(self.v_validations)
            # FOR PRINTING ALL SUB-GRAPHS IN A SINGLE PLOT
            # self.graphs.set_vertex_filter(self.v_components)

            graph_draw(self.graphs, vertex_text=self.v_index,
                       vertex_shape="double_circle", vertex_font_size=8, vertex_pen_width=2,
                       output=F"{clusterID}-Component-{component_ID}-{key}.pdf")

            print(F"\t===> Done printing {clusterID}-Component-{component_ID}-{key}.pdf")

            # RESETTING THE ORIGINAL BOOLEAN v_validations LIST
            self.v_validations = deepcopy(copy)

        # CLEAR ALL FILTERS
        self.graphs.clear_filters()

    def corroborated_by(self, investigated):

        # List of the edges on the shortest path
        edges_paths = []
        # List of the weights of the path of reconciliation evidence
        recon_strength = []
        # List of vertices of interest
        src_corroborating = []
        trg_corroborating = []
        # The original weights
        weights = list(self.graphs_copy.ep["weight"])

        # Source and Target of the corroborating path mapped using the relations
        src_v_corroborations = self.relations_map[investigated[0]]
        trg_v_corroborations = self.relations_map[investigated[1]]

        # For each vertex in src_v_corroborations and trg_v_corroborations, get the component attached to them
        src_comp = {self.components[vertex] for vertex in src_v_corroborations if vertex}
        tar_comp = {self.components[vertex] for vertex in trg_v_corroborations if vertex}
        comp_intersection = src_comp.intersection(tar_comp)

        if len(src_comp) == 0 or len(tar_comp) == 0:
            return set()

        # print("\t", evidence[0], evidence[1])
        # print(F"\nInvestigated: [{investigated[0]}, {investigated[1]}]",
        #       F"Investigated Component: {self.components[investigated[0]]}",
        #       F"Component Intersection: {comp_intersection}")
        # print("\t", src_v_corroborations, trg_v_corroborations)

        # Gathering the list of vertices of interest in the source
        for corroborating_vertex in src_v_corroborations:
            if self.components[corroborating_vertex] in comp_intersection:
                src_corroborating.append(corroborating_vertex)

        # Gathering the list of vertices of interest in the target
        for corroborating_vertex in trg_v_corroborations:
            if self.components[corroborating_vertex] in comp_intersection:
                trg_corroborating.append(corroborating_vertex)

        # Cartesian Product as a combination of source vs targets vertices options
        combination = set(product(src_corroborating, trg_corroborating))

        # Filtering edges that do not belong to the same cluster
        combination = set(filter(lambda x: self.components[x[0]] == self.components[x[1]], combination))

        # Computing the weight of the best path for the investigated edge
        for edge in combination:
            # Get the shortest path for the given edge
            path = (shortest_path(self.graphs_copy, edge[0], edge[1], weights=self.graphs_copy.ep["inverted_weight"]))
            # Compute the sum of the weight for the best path
            weights_sum = sum(weights[self.graphs_copy.edge_index[ed]] for ed in list(path[1]))
            # Compute the reconciliation strength for the best path found
            recon_strength.append(
                IdentityGraphs.reconciliation_strength(weights_sum, len(path[1]), evidenceStrength=80))
            edges_paths.append(list(path[1]))

        # Update the computed weight for the reconciled edge
        reconciled_edge = list(combination)[list(recon_strength).index(max(recon_strength))]

        # Corresponding edge in the graph
        if investigated[0] != investigated[1]:
            edge = self.graphs.edge(investigated[0], investigated[1])
            if edge:
                self.graphs.ep["weight"][self.graphs.edge(investigated[0], investigated[1])] = max(recon_strength)
                self.e_validations[edge] = True
                self.v_validations[investigated[0]] = True
                self.v_validations[investigated[1]] = True
            else:
                self.graphs.add_edge(investigated[0], investigated[1])
                edge = self.graphs.edge(investigated[0], investigated[1])
                self.graphs.ep["weight"][edge] = max(recon_strength)
                self.e_validations[edge] = True
                self.v_validations[investigated[0]] = True
                self.v_validations[investigated[1]] = True
                self.new_edges.append(edge)

        # self.e_weights[self.graphs.edge(reconciled_edge[0], reconciled_edge[1])] = max(recon_strength)
        # print(F"{investigated} ---> {combination} ====> {recon_strength}, {reconciled_edge}\n")

        return set(reconciled_edge)

    def explanation(self):
        print(self.graphs)
        # THE SIZE OF THE CLUSTER AT A MAX OF 10
        # THE RECONCILED/CONSOLIDATED CLUSTER IS SPLIT
        # THE CLUSTER CONTAINS MORE THAN ONE NEWBORN
        #   nHasFather nHasMother
