import ast
import math
from time import time
from sys import stdout
from string import capwords
from io import StringIO as Buffer
from itertools import combinations
from collections import defaultdict
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta

import operator

# import src.extended_family.turtle as ttl
from src.identity_net.IdentityGraphs import IdentityGraphs
from src.extended_family.db_commands import select_row
from src.identity_net.Resource import Resource
from src.general.colored_text import Coloring
import src.extended_family.turtle as ttl
from src.extended_family import db_commands as func
from string import capwords


# ## PARAMETERS ================================================================
# ==============================================================================
import src.general.parameters as par
from src.general.parameters import f_name_prefix, f_name, g_name, gender

css_list = Coloring().css
triple_data = ttl.initialize_triple_data()
color = Coloring().colored
week_date = Coloring().print_week_date

stop, tab = '1', "    "
max_size, dot_size2, dot_size = 200, 185, 183

# ## HELPER FUNCTIONS ==========================================================
# ==============================================================================


def serialise(data):
    if data.startswith('defaultdict'):
        data = data[data.find("{"):-1]
        return ast.literal_eval(data)
    return ast.literal_eval(data)


def completed(started):
    return color(7, F"{str(timedelta(seconds=time() - started))}")


def progressOut(i, total, start=None, bars=50):

    extra_for_color = 15
    increment = 100/float(bars)
    ratio = i * bars / total if total > 0 else 0
    dif = "" if start is None else F" in {color(7, str(timedelta(seconds=time() - start)))}"
    progressed = u"\u2588" * int(round(ratio, 0))
    progressed = F"| {color(7, progressed):{bars+extra_for_color}} | {str(round(ratio * increment, 0)):>5}%{dif} [{i}] "

    stdout.write(F"\r\x1b[K \t{progressed.__str__()}")
    stdout.flush()


def rsc_name(db_name, pers_id):

    referents = select_row(db_name=db_name, table='PERSON_TBL', column='id', value=pers_id)

    if referents is not None:
        # return F"{' '.join(term.capitalize() for term in referents[f_name].split(' '))} " \
        #        F"{' '.join(term.capitalize() for term in referents[g_name].split(' '))}"
        return F"{' '.join(term.capitalize() for term in referents[g_name].split(' '))} {referents[f_name_prefix]} " \
               F"{referents[f_name].capitalize()}"
    return ''


# RETURN A CLUSTER BASED ON A PERSONS ID
def find_cluster_on_pid(db_name, pers_id):

    # value=p-1100241 value=p-1446513 value=p-1599176
    result = select_row(db_name=db_name, table='PERSON_ID2CLUSTER_TBL', column='id', value=pers_id.replace('p-', ''))
    if result is not None:
        return serialise(result[1])
    return None


# ==========================================================================
# THE RECONCILIATION RECONCILIATION PROCESS
# ==========================================================================


def reconciliation(
        link_list, relation_list, view_validation_table=False,  clusterID=None, component_ID=None, draw=False):

    message = Buffer()

    # 1. GENERATE THE GRAPHS
    i_graphs = IdentityGraphs(links=link_list)
    edges_before_relations = i_graphs.graphs.get_edges()

    # 2. SEARCH FOR CYCLES AND VALIDATED EDGES
    i_graphs.rec_cycles(relations=relation_list)

    # 3. CONSOLIDATION OF SUB-GRAPHS OF THE CURRENT MAIN GRAPH
    # print(i_graphs.consolidate(cluster_ID=clusterID, component_ID=component_ID))
    i_graphs.consolidate(cluster_ID=clusterID, component_ID=component_ID)

    # PRINTING VALIDATE COMPONENTS
    # i_graphs.print_reconciliations(component=component_ID)
    # i_graphs.print_reconciliations_results(component=component_ID)

    # DATA PRINTING & GRAPHS DRAWING
    if view_validation_table:
        i_graphs.draw("Before")
        message.write(F"\tBEFORE RELATIONS    : {edges_before_relations.shape}\n")
        message.write(F"\tVALIDATED EDGES     : {i_graphs.validated}\n")
        message.write(F"\tAFTER RELATIONS     : {i_graphs.graphs.get_edges().shape}\n")

        # APPLY THE VALIDATION FILTER OF EDGES AND VERTICES OF THE CURRENT GRAPH
        i_graphs.graphs.set_edge_filter(i_graphs.e_validations)
        i_graphs.graphs.set_vertex_filter(i_graphs.v_validations)

        # DRAW THE FILTERED (VALIDATED) GRAPHS
        i_graphs.draw("After")
        message.write(F"\tVALIDATED EDGES     : {i_graphs.graphs.get_edges().shape}\n")
        message.write(F"\tNEW EDGES COUNT     : {i_graphs.new_edges.__len__()}\n")

        if component_ID is not None and draw:
            i_graphs.draw_component(clusterID, int(component_ID))

        i_graphs.graphs.clear_filters()
        message.write("Source \t\tTarget \tValidated-Edges \tWeights\n")
        # print(i_graphs.graphs.get_edges([i_graphs.e_validations, i_graphs.e_weights]))
        # message.write(i_graphs.graphs.get_edges([i_graphs.e_validations, i_graphs.e_weights]))

    else:
        # APPLY THE VALIDATION FILTER OF EDGES AND VERTICES OF THE CURRENT GRAPH
        i_graphs.graphs.set_edge_filter(i_graphs.e_validations)
        i_graphs.graphs.set_vertex_filter(i_graphs.v_validations)

    # print(consolidated)
    # print(message.getvalue())
    # print("")
    return i_graphs


# RETURN A TABLE IN PLAIN HTML TEXT
def cycle_check_0(cid, co_referents, db_name, lst=True):

    done, css = [], dict()
    counter, color_idx, count_sub_v = 0, 0, 0
    component_id, groundless_evidence = 0, 0
    html_data, subcomponents = Buffer(), Buffer()
    temp_lines_html = defaultdict(list)
    index_color = 0

    style = F"""    <style type='text/css'>
    .content {{max-width: 1400px; margin: auto;}}
    {css_list(index_color)} {css_list(1)} 
    </style> 
    """

    # TABLE HEADER
    html_data.write(
        F"{'-' * (dot_size2 - 6)}<br>{tab}| {'Clustered Identical Persons with P-IDS':53} | "
        F"{'Associated Relations toward Other Associated Persons':88} | "
        F"{'Associated Clusters and Size':28} |<br>{tab}{'-' * (dot_size2 - 6)}<br>")
    html_data.write(F"{tab}|{' ' * (dot_size2 - 8)}|\n")

    # COLORING FUNCTIONS
    # t_line = Coloring().table_line
    t_line_html = Coloring().table_line_html

    # IDS OF THE CO-REFERENTS
    ids = co_referents['ids']

    # MAIN Cluster, RELATIONS OF INTEREST AND ASSOCIATED CLUSTERS
    main_relations, associated_clusters = 0, set()

    # full_events, associations_dict, person2events = None, None, None
    links, association_list, association_summary, table,  = [], [], '', ''

    # RETURN A FORMATTED RESOURCE NAME
    def _rsc_name(prs_id):

        prs = select_row(db_name=db_name, table='PERSON_TBL', column='id', value=prs_id)

        alt_name = F"{prs[f_name][0].capitalize() if prs[f_name] else ''}" \
                     F"{''.join(term[0] if term else '' for term in prs[g_name].split(' '))}"

        name = F"{prs[f_name].capitalize()} {''.join(term.capitalize() for term in prs[g_name].split(' '))}"

        return name, alt_name

    # GENERATING A COMPLETE GRAPH BASED ON THE LIST OF CO-REFERENT IDS
    def link_gen(prs_ids):

        for (sub, obj) in combinations(prs_ids, 2):

            # DATA FOR CREATING A RESOURCE AND A LINK
            sp, op = F"p-{sub}", F"p-{obj}"
            s_name, s_alt_name = _rsc_name(sp)
            o_name, o_alt_name = _rsc_name(op)

            # GENERATE THE LINKS AND LOAD THEM TO THE LINK LIST
            links.append((Resource(sp, s_name, s_alt_name), Resource(op, o_name, o_alt_name), 1))

    # GENERATING A COMPLETE GRAPH FOR THE MAIN CLUSTER
    if lst is True:

        count_ids = 0

        # LOAD THE COMPLETE LINKS GENERATED BASED ON THE CO-REFERENT IDS
        link_gen(prs_ids=ids)

        for p_id in ids:

            # For the clustered persons in the main cluster get the associated clusters and relations
            pid, des = F'p-{p_id}', ''

            # ASSOCIATION_DICT_TBL : p-5183067 | [['--dHasMother->', 'p-5183069'], ['--dHasFather->', 'p-5183068']]
            prs_associations = select_row(db_name=db_name, table='ASSOCIATION_DICT_TBL', column='id', value=pid)

            if prs_associations is not None:

                # THE ASSOCIATION FOR A PERSON RETURNS A LIST OF RELATIONS
                # print(len(associations_dict[pid]), associations_dict[pid])
                # Generate the association using person ID and concatenated name
                sub_name, sub_alt_name = _rsc_name(pid)

                for [predicate, pid_2] in serialise(prs_associations[1]):
                    # predicate, pid_2 = x[0], x[1]
                    # Generate the association using person ID and concatenated name
                    obj_name, obj_alt_name = _rsc_name(pid_2)
                    # Populate the person relation dictionary
                    main_relations += 1

                    # PERSON_2_EVENTS_TBL: p-2999 | ['e-1000']
                    prs2evt = select_row(db_name=db_name, table='PERSON_2_EVENTS_TBL', column='id', value=pid_2)
                    prs2evt = serialise(prs2evt[1]) if prs2evt is not None else []
                    e_id = prs2evt[0] if len(prs2evt) > 0 else ''

                    # e-1 | { 'eventDate': '1833-12-23', 'father': 'p-2', 'mother': 'p-3', 'newborn': 'p-1',
                    # 'registrationDate': '1833-12-24', 'registrationID': '1', 'registrationSeqID': '34'}
                    full_event = select_row(db_name=db_name, table='FULL_EVENTS_TBL', column='id', value=e_id)
                    full_event = serialise(full_event[1]) if full_event is not None else ''
                    event_date = full_event["eventDate"]

                    if len(prs2evt) > 1:
                        print("PERSON WITH MORE THAN ONE EVENT")

                    # Find the associated clusters
                    associated_cid = find_cluster_on_pid(db_name=db_name, pers_id=pid_2)

                    if associated_cid is not None:

                        # GENERATING A COMPLETE GRAPH FOR THE ASSOCIATED EVIDENCE CLUSTER
                        associated_referents = select_row(
                            db_name=db_name, table='CLUSTERS_TBL', column='id', value=associated_cid)
                        associated_referents = ast.literal_eval(associated_referents[1])

                        if associated_cid not in associated_clusters:
                            associated_clusters.add(associated_cid)
                            link_gen(prs_ids=associated_referents['ids'])
                            des = F"i-{associated_cid} of size [{associated_referents['cor_count']}]"

                        elif associated_cid in associated_clusters:
                            des = F"i-{associated_cid} of size [{associated_referents['cor_count']}]"

                        text_list = [str(count_ids), pid, sub_name, predicate, e_id, event_date, pid_2, obj_name, des]
                        temp_lines_html[count_ids].append(t_line_html(text_list))

                    else:
                        # des = F"associated to cluster [------] of size [--]"
                        des = F"not clustered"

                        text_list = [str(count_ids), pid, sub_name, predicate, e_id, event_date, pid_2, obj_name, des]
                        temp_lines_html[count_ids].append(t_line_html(text_list))

                    # Append it to the association list
                    association_list.append(
                        (Resource(pid, sub_name, sub_alt_name), Resource(pid_2, obj_name, obj_alt_name)))

            count_ids += 1

    # EXECUTE THE RECONCILIATION OF THE CLUSTER
    rec_g = reconciliation(
        link_list=links, relation_list=association_list,
        view_validation_table=False, clusterID=cid, component_ID=component_id, draw=False)

    # GROUNDED AND GROUNDLESS EVIDENCE
    if len(rec_g.reconciliations) > 0:

        # EVIDENCE GROUNDED RESOURCES
        for key, values in rec_g.reconciliations[component_id].sub_vertices.items():
            css[key] = css_list(key)
            count_sub_v += 1
            for value in values:
                for line in temp_lines_html[value]:
                    html_data.write(line(index_color))
                done.append(value)

            # INSET THE EMPTY LINE
            html_data.write(F"{tab}|{'&nbsp;' * (dot_size2 - 8)}|\n")
            subcomponents.write(F"\t\t\t{values}\n")

            color_idx += 1

        # EVIDENCE GROUNDLESS RESOURCES
        for key in temp_lines_html.keys():

            if key not in done:

                # COUNTING UNVALIDATED
                groundless_evidence += 1

                if counter == 0:
                    html_data.write(F"{tab}|{'-' * (dot_size2 - 8)}|\n")
                    html_data.write(F"{tab}|{'&nbsp;' * (dot_size2 - 8)}|\n")

                counter += 1

                for line in temp_lines_html[key]:
                    html_data.write(line(1).replace(' ', '&nbsp;'))

        # LAST TABLE LINE
        if groundless_evidence > 0:
            html_data.write(F"{tab}|{'&nbsp;' * (dot_size2 - 8)}|\n")

        html_data.write(F"{tab}{'-' * (dot_size2 - 6)}\n")

    grounded_components = len(rec_g.reconciliations[component_id].sub_vertices) if len(rec_g.reconciliations) > 0 else 0

    return F"{style}{html_data.getvalue()}", groundless_evidence, grounded_components, associated_clusters


def role_mapping(role):

    if role in ['--nHasFather->', '--bHasFather->', '--gHasFather->']:
        return 'Father'

    if role in ['--nHasMother->', '--bHasMother->', '--gHasMother->']:
        return 'Mother'

    if role in ['<-hasMother---', '<-hasFather---', '<-gHasMother--', '<-bHasMother--']:
        return 'Child'

    elif role in ['---married--->']:
        return 'spouse'

    else:
        return None


# GATHER DATA
def get_detail(db_name, cluster_id):
    names = set()
    extended_family = set()
    roles = defaultdict(set)
    roles_groundless = defaultdict(set)
    # Fetch data about the cluster
    cmd = "SELECT id, serialised FROM CLUSTERS_TBL WHERE id={cid} ;"
    detail = func.select(db_name=db_name, cmd=cmd.format(cid=cluster_id))
    if detail is not None:
        # Get the IDs used for each observation
        persons = serialise(detail[0]['serialised'])['ids']
        # Collect data on each observation
        for pid in persons:
            p_id = F"p-{pid}"
            prs = select_row(db_name=db_name, table='PERSON_TBL', column='id', value=p_id)
            if prs is not None:
                names.add(capwords(F"{prs[f_name]} {prs[g_name]}"))
                # ASSOCIATED FAMILY CLUSTERS
                prs_associations = select_row(db_name=db_name, table='ASSOCIATION_DICT_TBL', column='id', value=p_id)
                for [predicate, pid_2] in serialise(prs_associations[1]):
                    cid = find_cluster_on_pid(db_name=db_name, pers_id=pid_2)
                    if cid is not None:
                        roles[cid].add(role_mapping(predicate))
                    else:
                        roles_groundless[pid_2].add(role_mapping(predicate))
                    # extended_family.add(cid)

    return names, roles, roles_groundless


# GIVEN A RECONSTITUTED, HE OR SHE CAN BE SPLIT OR A MEMBER OF THE EXTENDED FAMILY CAN BE SPLIT
def family_thread(db_name, processed):

    cmd = "SELECT id, serialised FROM CLUSTERS_TBL WHERE id={cid} ;"
    # print(cmd.format(cid=list(family_cluster_ids)[0]))

    family = defaultdict(list)

    name_variants, extended_family_cid, roles_groundless = get_detail(db_name, processed)
    family[processed] = ['RECONSTITUTED', " | ".join(name for name in name_variants)]
    print(F"{processed}: {name_variants}")

    # for family_cluster, role_set in extended_family_cid.items():
    #     name_variants_2, extended_family_cid_2, roles_groundless_2 = get_detail(db_name, family_cluster)
    #     print(F"\t├── {family_cluster} {role_set} : {name_variants_2}")

    # GROUNDED

    for family_cluster, role_set in extended_family_cid.items():
        info = get_detail(db_name, family_cluster)
        role = " | ".join(role for role in role_set)
        name = " | ".join(str(name) for name in info[0])
        family[family_cluster] = [role, name]

    # GROUNDLESS
    for family_cluster, role_set in roles_groundless.items():
        prs = select_row(db_name=db_name, table='PERSON_TBL', column='id', value=family_cluster)
        name_variants_2 = F"{prs[f_name]} {prs[g_name]}"
        role = " | ".join(role for role in role_set)
        family[family_cluster] = [role, name_variants_2]

    print(F"\n{'='*100}\n")
    count, end = 0, len(family)-1
    for cid, [role, name] in family.items():
        if count == 0:
            print(F"{role} {cid} {name}")
        else:
            print(F"\t{'├── ' if count != end else '└── '} {F'{role} {cid}':20} {name}")
        count += 1
    print(F"\n{'=' * 100}\n")


# RETURNS TWO TABLE OBJECTS: GROUNDED AND GROUNDLESS
def cycle_check(cid, co_referents, db_name, lst=True):

    done, css = [], dict()
    counter, color_idx, count_sub_v = 0, 0, 0
    component_id, groundless_evidence = 0, 0
    grounded_table, groundless_table, subcomponents = defaultdict(list), defaultdict(list), Buffer()
    temp_lines_html = defaultdict(list)

    # COMPUTE THE ACTUAL SIZE OF GROUNDED OR GROUNDLESS BASED ON THE PERSONS ID
    actual_size = defaultdict(set)

    # IDS OF THE CO-REFERENTS
    ids = co_referents['ids']

    # MAIN Cluster, RELATIONS OF INTEREST AND ASSOCIATED CLUSTERS
    main_relations, associated_clusters = 0, set()

    # full_events, associations_dict, person2events = None, None, None
    links, association_list, association_summary,  = [], [], ''

    # RETURN A FORMATTED RESOURCE NAME
    def _rsc_name(prs_id):

        prs = select_row(db_name=db_name, table='PERSON_TBL', column='id', value=prs_id)

        alt_name = F"{prs[f_name][0].capitalize() if prs[f_name] else ''}" \
                     F"{''.join(term[0] if term else '' for term in prs[g_name].split(' '))}"

        name = F"{' '.join(term.capitalize() for term in prs[g_name].split(' '))} {prs[f_name_prefix]} " \
               F"{prs[f_name].capitalize()}"

        return name, alt_name

    # GENERATING A COMPLETE GRAPH BASED ON THE LIST OF CO-REFERENT IDS
    def link_gen(prs_ids):

        for (sub, obj) in combinations(prs_ids, 2):

            # DATA FOR CREATING A RESOURCE AND A LINK
            sp, op = F"p-{sub}", F"p-{obj}"
            s_name, s_alt_name = _rsc_name(sp)
            o_name, o_alt_name = _rsc_name(op)

            # GENERATE THE LINKS AND LOAD THEM TO THE LINK LIST
            links.append((Resource(sp, s_name, s_alt_name), Resource(op, o_name, o_alt_name), 1))

    def table_line_dict(txt_list):

        return {"rid": txt_list[0],
                "p_ID": F"{txt_list[1]}",
                "p_name": F"{txt_list[2]}",
                "role": F"{txt_list[3]}",
                "certificate": F"{txt_list[4]}",
                "certificateDate": F"{txt_list[5]}",
                "associationPersonID": F"{txt_list[6]}",
                "associationPersonName": F"{txt_list[7]}",
                "associated_cluster": F"{txt_list[8]}"}

    # GENERATING A COMPLETE GRAPH FOR THE MAIN CLUSTER
    if lst is True:

        count_ids = 0

        # LOAD THE COMPLETE LINKS GENERATED BASED ON THE CO-REFERENT IDS
        link_gen(prs_ids=ids)

        for p_id in ids:

            # For the clustered persons in the main cluster get the associated clusters and relations
            pid, des = F'p-{p_id}', ''

            # ASSOCIATION_DICT_TBL : p-5183067 | [['--dHasMother->', 'p-5183069'], ['--dHasFather->', 'p-5183068']]
            prs_associations = select_row(db_name=db_name, table='ASSOCIATION_DICT_TBL', column='id', value=pid)

            if prs_associations is not None:

                # THE ASSOCIATION FOR A PERSON RETURNS A LIST OF RELATIONS
                # print(len(associations_dict[pid]), associations_dict[pid])
                # Generate the association using person ID and concatenated name
                sub_name, sub_alt_name = _rsc_name(pid)

                # print(F"{pid} {serialise(prs_associations[1])}")

                for [predicate, pid_2] in serialise(prs_associations[1]):
                    # predicate, pid_2 = x[0], x[1]
                    # Generate the association using person ID and concatenated name
                    obj_name, obj_alt_name = _rsc_name(pid_2)
                    # Populate the person relation dictionary
                    main_relations += 1

                    # PERSON_2_EVENTS_TBL: p-2999 | ['e-1000']
                    prs2evt = select_row(db_name=db_name, table='PERSON_2_EVENTS_TBL', column='id', value=pid_2)
                    prs2evt = serialise(prs2evt[1]) if prs2evt is not None else []
                    e_id = prs2evt[0] if len(prs2evt) > 0 else ''

                    # e-1 | { 'eventDate': '1833-12-23', 'father': 'p-2', 'mother': 'p-3', 'newborn': 'p-1',
                    # 'registrationDate': '1833-12-24', 'registrationID': '1', 'registrationSeqID': '34'}
                    full_event = select_row(db_name=db_name, table='FULL_EVENTS_TBL', column='id', value=e_id)
                    full_event = serialise(full_event[1]) if full_event is not None else ''
                    event_date = full_event["eventDate"]

                    if len(prs2evt) > 1:
                        print("PERSON WITH MORE THAN ONE EVENT")

                    # Find the associated clusters
                    associated_cid = find_cluster_on_pid(db_name=db_name, pers_id=pid_2)

                    if associated_cid is not None:

                        # GENERATING A COMPLETE GRAPH FOR THE ASSOCIATED EVIDENCE CLUSTER
                        associated_referents = select_row(
                            db_name=db_name, table='CLUSTERS_TBL', column='id', value=associated_cid)
                        associated_referents = ast.literal_eval(associated_referents[1])

                        if associated_cid not in associated_clusters:
                            associated_clusters.add(associated_cid)
                            link_gen(prs_ids=associated_referents['ids'])
                            des = F"i-{associated_cid} of size {associated_referents['cor_count']}"

                        elif associated_cid in associated_clusters:
                            des = F"i-{associated_cid} of size {associated_referents['cor_count']}"

                        text_list = [str(count_ids), pid, sub_name, predicate, e_id, event_date, pid_2, obj_name, des]
                        temp_lines_html[count_ids].append(table_line_dict(text_list))

                    else:

                        des = F"not clustered"
                        text_list = [str(count_ids), pid, sub_name, predicate, e_id, event_date, pid_2, obj_name, des]
                        temp_lines_html[count_ids].append(table_line_dict(text_list))

                    # Append it to the association list
                    association_list.append(
                        (Resource(pid, sub_name, sub_alt_name), Resource(pid_2, obj_name, obj_alt_name)))

            actual_size[count_ids].add(pid)
            count_ids += 1

    # EXECUTE THE RECONCILIATION OF THE CLUSTER
    rec_g = reconciliation(
        link_list=links, relation_list=association_list,
        view_validation_table=False, clusterID=cid, component_ID=component_id, draw=False)

    grounded_size = 0
    groundless_size = 0

    # GROUNDED AND GROUNDLESS EVIDENCE
    if len(rec_g.reconciliations) > 0:

        # EVIDENCE GROUNDED RESOURCES
        for key, values in rec_g.reconciliations[component_id].sub_vertices.items():
            for value in values:
                for line in temp_lines_html[value]:
                    grounded_size += len(actual_size[value])
                    grounded_table[color_idx].append(line)
                done.append(value)
            subcomponents.write(F"\t\t\t{values}\n")
            color_idx += 1

    # EVIDENCE GROUNDLESS RESOURCES
    # print(F"temp_lines_html : {temp_lines_html}")

    for key in temp_lines_html.keys():
        if key not in done:
            for line in temp_lines_html[key]:
                groundless_evidence += 1
                groundless_size += len(actual_size[key])
                groundless_table[0].append(line)

    grounded_components = len(rec_g.reconciliations[component_id].sub_vertices) if len(rec_g.reconciliations) > 0 else 0

    for k, value in grounded_table.items():
        grounded_table[k] = sorted(value, key=lambda x: x["certificateDate"])

    return grounded_size, groundless_size, grounded_table, groundless_table, \
        groundless_evidence, grounded_components, associated_clusters


def quality_check(db_name, cluster_id, referents, counter=1, process_count=4):

    if True:

        if referents is None:
            data = {
                'name': "", 'marital_text': "", 'flag': None,  'bads': 0, 'cid': '', 'maybes': 0, 'html_table': "",
                'c_size': "", 'grounded_table': dict(), 'groundless_table': dict(),
                'html_summary': F"\t\tSorry...\n\n"
                                F"\t\tNo result could be found for RECONSTITUTED cluster with id [{cluster_id}].\n\n\n"
            }
            return None,  data

        tabs = "    \t"
        dt = ttl.initialize_triple_data()
        # CLUSTER IS A NEWBORN AND HAS A FATHER AND A MOTHER
        n_mother, n_father = '--nHasMother->', '--nHasFather->'
        # CLUSTER IS A BRIDE OR GROOM AND HAS A MOTHER
        b_mother, g_mother = '--bHasMother->', '--gHasMother->'
        # CLUSTER IS A BRIDE OR GROOM AND HAS A FATHER
        b_father, g_father = '--bHasFather->', '--gHasFather->'
        # THE CLUSTER is the FATHER OR MOTHER OF the associated
        child_mother, child_father = '<-hasMother---', '<-hasFather---'
        # MARRIED CHILDREN
        g_is_mother, g_is_father = '<-gHasMother--', '<-gHasFather--'
        b_is_mother, b_is_father = '<-bHasMother--', '<-bHasFather--'

        # NUMBER OF BIRTHS
        births = defaultdict(set)
        is_married_1 = '---married--->'
        is_married_2 = '<--married----'
        is_divorced = '---divorced-->'
        # ['<-hasMother---', '<-bHasMother--', '---married--->',
        # '--bHasFather->', '--bHasMother->', '--nHasMother->', '--nHasFather->']
        size = referents['cor_count']

        description = dict()
        relations = defaultdict(int)
        rel_data = defaultdict(set)
        sub_name = None
        unknown_m, unknown_f = 0, 0
        f_birth_per_child = defaultdict(set)
        m_birth_per_child = defaultdict(set)
        child_issue = set()

        main_gender = ''
        marriage_ages = set()
        children_birth_age = []
        birth_date = set()
        marriage_date = set()
        children_birth_dates = set()
        # CHILDREN AGE DIFFERENCE
        consecutive_age_diff, max_age_diff = [], 0

        # print(F"CLUSTERED: {referents['ids']}\n")

        # LIST OF CLUSTERED PERSONS WITHIN THE CLUSTER OF INTEREST
        for person_id in referents['ids']:

            pid = F'p-{person_id}'
            sub_name = rsc_name(db_name, pid)
            person = select_row(db_name=db_name, table='PERSON_TBL', column='id', value=pid)
            relatives = select_row(db_name=db_name, table='ASSOCIATION_DICT_TBL', column='id', value=pid)

            # GENDER OF THE RECONSTITUTED
            main_gender = person[gender]

            # NO FAMILY MEMBERS COULD BE FOUND
            if relatives is None:

                print(F"person_id {person_id} person_id {relatives}")
                data = {
                    'name': "", 'marital_text': "", 'flag': None, 'html_table': "",
                    'html_summary': F"\t\tSorry...\n\n\t\t {process_count - 4} more processes need to be run prior to "
                                    F"analysing a =RECONSTITUTED individual of interest.\n\n\n"}
                return None, data

            # FAMILY MEMBERS OF THE RECONSTITUTED
            relatives = serialise(data=relatives[1])

            # FIND PERSONS RELATED TO THE CURRENT CLUSTERED RESOURCE
            for [predicate, pid_2] in relatives:

                relations[predicate] += 1
                p2event = serialise(data=select_row(
                    db_name=db_name, table='PERSON_2_EVENTS_TBL', column='id', value=pid_2)[1])
                name = rsc_name(db_name, pid_2)
                associated_cluster = find_cluster_on_pid(db_name, pid_2)
                full_event = serialise(data=select_row(
                    db_name=db_name, table='FULL_EVENTS_TBL', column='id', value=p2event[0])[1])

                # CHILD'S BIRTH DATE
                if predicate in [child_father, child_mother]:
                    children_birth_dates.add(datetime.strptime(full_event['eventDate'], '%Y-%m-%d'))

                # 1. UNKNOWN PARENT
                if len(name) == 0:
                    # if predicate == b_mother or predicate == g_mother or predicate == n_mother:
                    if predicate in [b_mother, g_mother, n_mother]:
                        unknown_m += 1
                    # if predicate == b_father or predicate == g_father or predicate == n_father:
                    if predicate in [b_father, g_father, n_father]:
                        unknown_f += 1

                # 2. COUNTING THE NUMBER OF BIRTH
                if associated_cluster is not None:

                    if predicate == child_mother:
                        m_birth_per_child[associated_cluster].add(p2event[0])
                    elif predicate == child_father:
                        f_birth_per_child[associated_cluster].add(p2event[0])

                # 3. COUNTING THE NUMBER OF BIRTHS FOR THE CLUSTER ITSELF
                if predicate in [n_mother, n_father]:
                    births['p2event'].add(p2event[0])
                    birth_date.add(datetime.strptime(full_event['eventDate'], '%Y-%m-%d'))

                # MARRIAGE DATE
                if predicate == is_married_1 or predicate == is_married_2:
                    marriage_date.add(datetime.strptime(full_event['eventDate'], '%Y-%m-%d'))

                if associated_cluster is not None:
                    c_id = associated_cluster
                    rel_data[predicate].add(F'i-{c_id}')

                else:
                    rel_data[predicate].add(pid_2)

        # COMPUTING THE AGE AT WHICH THE PERSON(S) GOT MARRIED
        if len(birth_date) > 0:

            if len(marriage_date) > 0:
                # CONVERTING TO A LIST OBJECT AND SORTING THEM
                birth_date = list(birth_date)
                marriage_date = list(marriage_date)
                birth_date.sort(), marriage_date.sort()

                # COMPUTING THE AGES AT THE WHICH THE RECONSTITUTED GOT MARRIED
                marriage_ages = [relativedelta(m_date, birth_date[0]).years for m_date in marriage_date]

            # CHILDREN BIRTH DATES
            children_birth_dates = list(children_birth_dates)
            children_birth_dates.sort()

            if isinstance(birth_date, list):
                children_birth_age = [relativedelta(child_b_date, birth_date[0]).years
                                      for child_b_date in children_birth_dates]

        # MOTHER'S BIRTH
        for child, value in m_birth_per_child.items():
            if len(value) > 1:
                child_issue.add(child)

        # FATHER'S PARENTING
        for child, value in f_birth_per_child.items():
            if len(value) > 1:
                child_issue.add(child)

        # -----------------------------
        #   SOFT RULES VERIFICATION
        # ----------------------------

        maybe_count, bad_count = 0, 0

        mother = rel_data[b_mother].union(rel_data[g_mother]).union(rel_data[n_mother])
        father = rel_data[b_father].union(rel_data[g_father]).union(rel_data[n_father])

        # The CURRENT married - was married by - was a groom OR a bride
        groom_parents = max(len(rel_data[g_father]), len(rel_data[g_mother]))
        bride_parents = max(len(rel_data[b_father]), len(rel_data[b_mother]))
        married = max(len(rel_data[is_married_1]), len(rel_data[is_married_2]), groom_parents, bride_parents)

        # SR-5. CONSECUTIVE CHILDREN SHOULD NOT BE MORE THAN 10 YEARS APART
        if isinstance(children_birth_dates, list) and len(children_birth_dates) > 1:
            consecutive_age_diff = [relativedelta(children_birth_dates[i], children_birth_dates[i - 1]).years
                                    for i in range(1, len(children_birth_dates))]
            max_age_diff = relativedelta(children_birth_dates[len(children_birth_dates) - 1], children_birth_dates[0]).years
        ok_child_age_dif = 0 < max(consecutive_age_diff) <= par.MAX_CONS_AGE_DIFF \
            if len(consecutive_age_diff) > 0 and main_gender == 'm' else True
        if ok_child_age_dif is False:
            maybe_count += 1
            # print("ok_child_age_dif")
            description['MAX AGE OF CONSECUTIVE CHILDREN'] = [
                "Search for the roles <-hasFather--- or <-hasMother---. Check the dates of the birth certificates. "
                "Compute the ages difference between consecutive children.",
                "Consequently, split the person observation rows into separate subclusters based on distinct birth"
                " certificates of the children. This requires a particular attention as the split may be implemented "
                "at the parent level (if different parents) or at the children level (if different children)."]

        # SR-4. MORE MARRIAGES THAN DIVORCES
        divorced = rel_data[is_divorced]
        ok_divorced = married >= len(divorced)
        if ok_divorced is False:
            maybe_count += 1
            # print("ok_divorced")
            description['SR-4. MARRIED MORE THAN 5 TIMES'] = [
                "Search for the roles ---divorced--> or <--divorced---. Count and compare it to the frequency of the "
                "roles ---married---> or <---married---. Compare the names of the spouses and divorcees. Check whether "
                "the date of the divorce follows after the date of the marriage between the same (ex)couple",
                "Consequently, split the person observation rows into separate subclusters based on distinct marriages "
                "and / or divorce certificates."]

        # SR-3. MORE MARRIED CHILDREN THAN CHILDREN
        children_count = len(rel_data[child_mother].union(rel_data[child_father]))
        married_children = rel_data[g_is_mother].union(rel_data[g_is_father]).union(
            rel_data[b_is_mother]).union(rel_data[b_is_father])
        ok_married_children = len(married_children) <= len(rel_data[child_mother].union(rel_data[child_father]))
        if ok_married_children is False:
            maybe_count += 1
            # print("ok_married_children")
            description['SR-3. MARRIED CHILDREN'] = [
                "Search for the roles <-hasFather-- or <-hasMother--. Count and compare it to the frequency of the "
                "roles <-gHasFather- or <-gHasMother- and / or <-bHasFather- or <-bHasMother-",
                "Consequently, split the person observation rows into separate subclusters based on distinct birth and "
                "marriage certificates of the children."]

        # SR-2. MARRIED MORE THAN 5 TIMES
        ok_married = married <= par.MAX_MARRIAGE
        if ok_married is False:
            maybe_count += 1
            # print("ok_married")
            description['SR-2. DIVORCES'] = [
                "Search for the roles ---married---> or <--married----. Carefully look at the names of the spouses and "
                "the dates of the marriages.",
                "Consequently, split the person observation rows into separate subclusters based on distinct birth "
                "certificates."]

        # SR-1. MAXIMUM NUMBER OF CHILDREN
        ok_nbr_children = children_count <= par.MAX_CHILDREN
        if ok_nbr_children is False:
            maybe_count += 1
            # print("ok_nbr_children")
            description['SR-1. MAXIMUM NUMBER OF CHILDREN'] = [
                "Search for the roles <-hasFather--- or <-hasMOther--- and count the number of children.",
                "Consequently, split the person observation rows into separate subclusters based on distinct birth and "
                "marriage certificates of the children."]

        # SR-7. THE NUMBER OF COMPUTED COMPONENTS OF A SET OF CO-REFERENTS SHOULD ALIGN WITH THE NUMBER OF EXPECTED COMPONENTS.
        # HOW MANY TIMES THE NUMBER OF SUBCOMPONENTS IS BIGGER THAN CHILDREN + 1 (if there is a birth)
        union = len(rel_data[child_mother].union(rel_data[child_father]))
        min_max = min(union, len(married_children)) if union > 0 and len(married_children) > 0 \
            else max(union, len(married_children))
        expected_components = min_max + (1 if len(births['p2event']) > 0 else 0)

        # ---------------------------
        #   HARD RULES VERIFICATION
        # ---------------------------

        # HR-1. AGE AT FIRST MARRIAGE
        age_first_marriage = min(marriage_ages) if len(marriage_ages) > 0 else 0
        ok_age_first_marriage = age_first_marriage >= par.MAX_MARRIAGE_AGE or len(marriage_ages) == 0
        if ok_age_first_marriage is False:
            bad_count += 1
            # print("ok_age_first_marriage")
            description[" HR-1. MOTHER'S AGE AT FIRST MARRIAGE"] = [
                "Search for the roles --nHasFather-> and / or --nHasMother->. Check the date of the birth certificate. "
                "Compute the age at first marriage by searching for the first ---married---> and subtracting the date "
                "on the marriage certificate from the date of birth.",
                "Split the person observation rows into separate subclusters based on distinct marriage and birth "
                "certificates"]

        # HR-2. AGE AT LAST CHILDBIRTH OF A MOTHER
        last_delivery_age = children_birth_age[len(children_birth_age) - 1] if len(children_birth_age) > 0 else 0
        ok_last_delivery_age = True if main_gender == "m" else last_delivery_age <= par.MAX_DELIVERY_AGE
        if ok_last_delivery_age is False:
            bad_count += 1
            # print("ok_last_delivery_age")
            description['HR-2. MOTHER AGE AT LAST CHILDBIRTH'] = [
                "Search for the roles --nHasFather-> and / or --nHasMother->. Check the date of the birth certificate."
                " Calculate the age at last childbirth by searching for the last <-hasMother--- and subtract the date"
                " on the birth certificate of the eldest child from the date of birth of the mother.",
                "Split the person observation rows into separate subclusters based on distinct birth certificates for"
                " children of the same mother."]

        # HR-3. AT MOST ONE BIRTH CERTIFICATE
        ok_births = len(births['p2event']) <= 1
        if ok_births is False:
            bad_count += 1
            # print("ok_births")
            description['HR-3. MULTIPLE BIRTH CERTIFICATES'] = [
                "Search for the roles --nHasFather-> and / or --nHasMother->. Carefully look at the dates of the birth"
                " certificates and the names of the parents.",
                "Split the person observation rows into separate subclusters based on distinct birth certificates."]

        # HR-4. AT MOST [ONE KNOWN FATHER / MOTHER] OR [ONE KNOWN AND UNKNOWN].
        ok_n_mother, ok_n_father = len(mother) <= 1, len(father) <= 1
        ok_unknown_m = len(mother) <= 1 or abs(len(mother) - unknown_m) <= 1
        ok_unknown_f = len(father) <= 1 or abs(len(father) - unknown_f) <= 1
        if ok_unknown_m is False or ok_n_mother is False:
            bad_count += 1
            description['HR-4. MULTIPLE MOTHERS'] = [
                "Search for the rules --nHasFather-> and / or --nHasMother->. First check for empty names, then "
                "carefully look at the dates of the birth certificates and the names of the parents.",
                "Split the person observation rows into separate subclusters based on distinct birth certificates."]
            # print("ok_unknown_m")
        if ok_unknown_f is False or ok_n_father is False:
            bad_count += 1
            # print("ok_unknown_f")
            description['HR-4. MULTIPLE FATHERS'] = [
                "Search for the rules --nHasFather-> and / or --nHasMother->. First check for empty names, then "
                "carefully look at the dates of the birth certificates and the names of the parents.",
                "Split the person observation rows into separate subclusters based on distinct birth certificates."]

        # HR-5. CHILDREN WITH MORE THAN ONE MOTHER OR FATHER
        ok_parent_per_child = len(child_issue) == 0
        if ok_parent_per_child is False:
            bad_count += 1
            # print("ok_parent_per_child")
            description['HR-5. CHILDREN WITH MORE THAN ONE MOTHER OR FATHER'] = [
                "Search for the rules <-hasMother--- or <-hasFather---. Look for children with the same name who have "
                "more than one father or mother.",
                "Split the person observation rows into separate subclusters based on distinct birth certificates."]

        # HR-6. CHILDREN AGE DIFFERENCE BETWEEN LAST AND FIRST
        ok_max_child_age_diff = True if main_gender == "m" else max_age_diff <= par.MAX_FIRST_LAST
        if ok_max_child_age_diff is False:
            bad_count += 1
            # print("ok_max_child_age_diff")
            description['HR-6. CHILDREN AGE DIFFERENCE BETWEEN LAST AND FIRST'] = [
                "Search for the rules <-hasMother--- or <-hasFather---. Check the dates of birth certificates of the "
                "eldest and youngest children. Compute the age difference.",
                "Consequently, split the person observation rows into separate subclusters based on distinct birth "
                 "certificates."]

        # --------------------------------------------------
        # DATA TO USE FOR GENERATING THE TURTLE FILE
        # --------------------------------------------------

        dt[ttl.size] = size
        dt[ttl.cid] = cluster_id
        dt[ttl.birth] = len(births['p2event'])
        dt[ttl.mother] = len(mother)
        dt[ttl.father] = len(father)
        dt[ttl.marriages] = married
        dt[ttl.divorced] = len(divorced)
        dt[ttl.children] = children_count
        dt[ttl.last_first_age_diff] = max_age_diff
        dt[ttl.married_children] = len(married_children)
        dt[ttl.children_with_more_than_one_parents] = len(child_issue)
        dt[ttl.max_consecutive_age_diff] = max(consecutive_age_diff) if len(consecutive_age_diff) > 0 else 0
        dt[ttl.expected_sub_reconstitutions] = expected_components
        dt[ttl.age_first_marriage] = age_first_marriage
        dt[ttl.last_delivery_age] = last_delivery_age

        # --------------------------------------------------
        # EXPLANATION
        # --------------------------------------------------

        # 1. BRITH EVENT AND MARRIAGE
        len_birth = dt[ttl.birth]
        births_review = F"{'She' if main_gender == 'f' else 'He'} appears on " \
                        F"{dt[ttl.birth] if len_birth > 0 else 'no'} birth certificate" \
                        F"{'s' if dt[ttl.birth] > 1 else ''} with " \
                        F"{dt[ttl.mother]} mother{'' if dt[ttl.mother] < 2 else 's'} and {dt[ttl.father]}" \
                        F" father{'' if dt[ttl.father] < 2 else 's'}."

        # 2. MARITAL DESCRIPTION AND NUMBER OF CHILDREN
        marr_ages_list = list(marriage_ages)
        marriage_ages_text = F"{marriage_ages[0]} and {marriage_ages[1]}" if len(marriage_ages) == 2 \
            else (', '.join(str(age) for age in marr_ages_list[:-1]) + F' and {marr_ages_list[len(marriage_ages)-1]}') \
            if len(marriage_ages) > 1 else ''
        married_at = F"Married at the age{'s' if len(marriage_ages) > 1 else ''} of " \
                     F"{marriage_ages[0] if len(marriage_ages)==1 else marriage_ages_text}, " \
            if len(marriage_ages) > 0 else "With no available marriage recorde, " if children_count else ''

        # 5. CHILDREN WITH MORE PARENTS THAN EXPECTED
        len_child_issue = len(child_issue)
        # issues = F"birth and child-parent issues" if len_birth > 0 and len_child_issue > 0 else \
        #     ('birth issue' if len_birth > 0 else ('child-parent issue' if len_child_issue > 0 else ''))
        # split_it = 0 if len_child_issue == 0 else (2 if len_child_issue == 1 else len_child_issue)
        # split_it = max(split_it, len_birth) if len_birth > 1 else split_it

        #  7. FINALLY
        # split_text = F"\n{tabs}Finally, given the observed {issues} it is likely that this reconstitution ends up being " \
        #              F"split into possibly {split_it} new reconstitutions." if split_it > 0 else ''
        split_text = ''

        # 3. MAXIMUM AGE DIFFERENCE BETWEEN YWO CONSECUTIVE CHILDREN
        age_diff_text = F"\n{tabs}The maximum age difference between two consecutive children is " \
                        F"{max(consecutive_age_diff)}" if len(consecutive_age_diff) > 0 else ''

        # 4. AGE DIF BETWEEN FIRST AND LAST CHILDREN
        age_35_diff = F" while the first and last children are {max_age_diff} years of age apart." \
            if max_age_diff > 0 else ''

        # 6. IN ADDITION
        child_more_parents = '' if dt[ttl.children_with_more_than_one_parents] < 1 else \
            F"\n{tabs}In addition, the data show that {len_child_issue if len_child_issue > 0 else 'none'} of " \
            F"{'her' if main_gender == 'f' else 'his'} children point{'s' if len_child_issue == 1 else ''} to " \
            F"more than one mother and / or father.{split_text}"

        age_diff_text += age_35_diff

        age_at_first_child = children_birth_age[0] if len(children_birth_age) > 0 else ''
        age_at_last_child = children_birth_age[len(children_birth_age) - 1] if len(children_birth_age) > 1 else ''

        # # MARITAL DESCRIPTION
        # married_at = F"Married at the age{'s' if len(marriage_ages)>1 else ''} of {marriage_ages}, " \
        #     if len(marriage_ages) > 0 else "With no available marriage recorde, " if children_count else ''

        #  3. MARRIED CHILDREN
        p_gender = 'she' if main_gender == 'f' else 'he'
        p_role = 'mother' if main_gender == 'f' else 'father'
        children = 'children' if children_count > 1 else 'child' if children_count == 1 else 'did not have any children'
        m_c = 'children' if dt[ttl.married_children] > 1 else 'Child'
        m_children = ' which got married' if dt[ttl.married_children] == 1 \
            else F". However, the reconstitution reveals that {p_gender}'s got {dt[ttl.married_children]} married {m_c}" if dt[ttl.married_children] > children_count \
            else F', of which {str(dt[ttl.married_children])} got married' if dt[ttl.married_children] > 1 else ''

        if children_count == 0:
            marital_text = F"{births_review}\n{tabs}{married_at}" \
                           F"{p_gender} {children}."

        if children_count == 1:
            marital_text = F"{births_review}\n{tabs}{married_at}" \
                           F"{p_gender} became the {p_role} of {children_count} {children} " \
                           F"at the age of {str(age_at_first_child) if age_at_first_child else '---'}{m_children}. " \
                           F"{age_diff_text} {child_more_parents}"

        elif children_count > 1:
            marital_text = F"{births_review}\n{tabs}{married_at}" \
                           F"{p_gender} became the {p_role} of {children_count} {children} " \
                           F"between the age of {str(age_at_first_child) if age_at_first_child else '---'} and " \
                           F"{str(age_at_last_child) if age_at_last_child else '---'}{m_children}. " \
                           F"{age_diff_text} {child_more_parents}"

        # marital_text = F"{births_review}" \
        #                F"\n{tabs}{married_at}{'she' if main_gender == 'f' else 'he'} " \
        #                F"{'became a mother of ' if main_gender == 'f' and children_count > 0 else 'became a father of ' if children_count > 0 else ''} " \
        #                F"{children_count if children_count > 0 else ''} " \
        #                F"{'children' if children_count > 1 else 'child' if children_count == 1 else 'did not have any children'}" \
        #                F"{' between the age of ' + str(age_at_first_child) + ' and ' + str(age_at_last_child) if len(children_birth_age) > 1 else ''}" \
        #                F"{', of which ' + str(dt[ttl.married_children]) + ' got married' if dt[ttl.married_children] > 0 else ''}." \
        #                F"{' at the age of ' + str(age_at_first_child) if len(children_birth_age) == 1 else ''}" \
        #                F"{age_diff_text}" \
        #                F"{child_more_parents}"
        # ️(˘︹˘) 🤷

        # --------------------------------------------------
        # PRINTS FOR THE HTML FILE
        # --------------------------------------------------

        t_size = F"{size:3}  {'' if size <= max_size else '❌':<3}"
        t_births = F"{dt[ttl.birth]:3}  {'✔' if ok_births else '❌':<{10 if ok_births is False else 11}}"
        t_mother = F"{dt[ttl.mother]:3}  {'❌' if ok_unknown_m is not True else ('✔' if ok_n_mother else '⚠️'):<{10 if ok_n_mother is False else 11}}"
        t_father = F"{dt[ttl.father]:3}  {'❌' if ok_unknown_f is not True else ('✔' if ok_n_father else '⚠️'):<{10 if ok_n_father is False else 11}}"
        t_married = F"{dt[ttl.marriages]:3}  {'✔' if ok_married else '⚠️':<{11 if ok_married is True else 12}}"
        t_divorced = F"{dt[ttl.divorced]:3}  {'✔' if ok_divorced else '⚠️':<{10 if ok_divorced is False else 11}}"
        t_children = F"{dt[ttl.children]:3}  {'✔' if ok_nbr_children else '⚠️':<{10 if ok_nbr_children is False else 11}}"
        t_age_first_marriage = F"{dt[ttl.age_first_marriage] if dt[ttl.birth] > 0 else 'n/a':3}  " \
                               F"{'' if dt[ttl.marriages] == 0 else '✔' if ok_age_first_marriage else '❌️':<{7 if ok_age_first_marriage is False else 8}}"
        t_age_last_childbirth = F"{dt[ttl.last_delivery_age] if dt[ttl.last_delivery_age] > 0 else 'n/a':3}  " \
                                F"{'' if dt[ttl.last_delivery_age] == 0 else '✔' if ok_last_delivery_age else '❌️' if dt[ttl.birth] > 0 else '':<{9 if ok_last_delivery_age is False else 10}}"
        t_age_diff = F"{dt[ttl.max_consecutive_age_diff] if len(consecutive_age_diff) > 0 else 'n/a':3}  " \
                     F"{'' if len(consecutive_age_diff) == 0 else ('✔' if ok_child_age_dif else '⚠️'):<4}"
        t_f_l_a_diff = F"{max_age_diff:3}  {'✔' if ok_max_child_age_diff else '❌':<4}"
        t_married_children = F"{dt[ttl.married_children]:3}  {'✔' if ok_married_children else '⚠️':<4}"
        t_child_parents = F"{dt[ttl.children_with_more_than_one_parents]:3}  {'✔' if ok_parent_per_child else '❌':<4}"

        # --------------------------------------------------
        # RUNNING THE CYCLE ALGORITHM
        # --------------------------------------------------
        grounded_size, groundless_size, grounded_table, groundless_table, \
            groundless_evidence, grounded_components, associated_clusters = cycle_check(
                cluster_id, referents, db_name, lst=True)

        # SR-6 GROUNDLESS OBSERVATIONS
        # A SET OF CO-REFERENTS ARE NOT EXPECTED TO EXHIBIT GROUNDLESS COMPONENTS.
        ok_groundless = groundless_evidence == 0
        if ok_groundless is False:
            maybe_count += 1
            description['SR-6 GROUNDLESS OBSERVATIONS'] = [
                "Search for rows highlighted in red and isolated from other rows.",
                "Consequently, merge isolated person observations or groundless singleton subclusters "
                "with other subclusters."]

        # SR-7. THE NUMBER OF COMPUTED COMPONENTS OF A SET OF CO-REFERENTS SHOULD ALIGN WITH THE NUMBER OF EXPECTED COMPONENTS.
        ok_expectation = expected_components == grounded_components
        if ok_expectation is False:
            maybe_count += 1
            description['SR-7. EXPECTED GROUNDED OBSERVATIONS'] = [
                "Look for the subgroup number of the last yellow subcluster. Compare this to the frequency of <-hasFather--- or "
                "<-hasMother--- plus one. If the observed number is different from the computed one, check for issues "
                "with the father, mother or spouse.",
                "Consequently, try to split or merge subclusters of person observations."]

        # SR-8. SIZE OF GROUNDLESS OBSERVATIONS
        ok_groundless_size = False if (size == 2 and groundless_size > 0) \
            else (True if groundless_size <= math.ceil(size / 3) else False)
        if ok_groundless_size is False:
            maybe_count += 1
            description['SR-7. THE SIZE OF GROUNDLESS OBSERVATIONS'] = [
                "Count the number of rows highlighted in red and compare it to the size of the cluster.",
                "Consequently, merge isolated person observations or groundless singleton subclusters "
                "with other subclusters."]

        # HR-7. MORE THAN 2 WARNINGS
        ok_maybe = maybe_count < 3
        if ok_maybe is False:
            bad_count += 1
            description['HR-7. MORE THAN 2 WARNINGS'] = [
                "Have a look at the Rules' Summary and check whether there are more than two warning flags ⚠️.",
                "If yes, refer to the suggested solutions offered for each warning."]

        t_groundless = F"{'YES' if groundless_size > 0 else 'NO':>3}  {'✔' if ok_groundless is True else '⚠️':<3}"
        t_grounded = F"{grounded_components:>3}  {'✔' if ok_expectation is True else '⚠️':<3}"
        t_groundless_size = F"{groundless_size:>3}  {'✔' if ok_groundless_size is True else '⚠️':<3}"

        # --------------------------------------------------
        # FLAGGING OF THE RECONSTRUCTED/CLUSTERED RESOURCE
        # --------------------------------------------------

        is_good = ok_n_mother and ok_n_father and ok_births and ok_married_children \
                  and ok_divorced and ok_unknown_m and ok_child_age_dif and ok_maybe

        is_bad = ok_births is False or ok_parent_per_child is False or \
                 ok_unknown_m is False or ok_unknown_f is False or \
                 ok_age_first_marriage is False or ok_last_delivery_age is False or ok_maybe is False

        flag = "Unlikely" if is_bad else ("Likely" if is_good is True else 'Uncertain')

        # --------------------------------------------------
        # DATA TO USE FOR GENERATING THE TURTLE FILE
        # --------------------------------------------------

        dt[ttl.flag] = flag
        dt[ttl.text] = F"\n{tabs}{sub_name.upper()}:\n{tabs}{marital_text}"
        dt[ttl.unlikely] = bad_count
        dt[ttl.uncertain] = maybe_count
        dt[ttl.expected_sub_reconstitutions] = expected_components
        dt[ttl.groundless_resources] = groundless_evidence
        dt[ttl.computed_sub_reconstitutions] = grounded_components
        dt[ttl.associated_clusters] = len(associated_clusters)

        html_summary = F"""    Size                   : {t_size:}      {'CHILDREN':45}: {t_children:<3}
    Births                 : {t_births}- Married                                  : {t_married_children:<3}
    Mother                 : {t_mother}- Max consecutive age difference           : {t_age_diff:<3}
    Father                 : {t_father}- with more than one father/mother         : {t_child_parents:<3}
    Married                : {t_married}- Age difference between first and last    : {t_f_l_a_diff:<3}
    Divorced               : {t_divorced}
    Age at first marriage  : {t_age_first_marriage} CLUSTER
    Age at last childbirth : {t_age_last_childbirth}{'- Extended Family members':41}   : {len(associated_clusters):>3} 
    {'':40}- {'Expected number of subclusters ':41} : {expected_components:>3}
    {'':40}- {'Grounded subclusters':41} : {t_grounded}
    {'':40}- {'Presence of a groundless subcluster':41} : {t_groundless}
    {'':40}- {'Groundless subcluster > 1/3 of its size':41} : {t_groundless_size}"""

        data = {'name': capwords(sub_name), 'marital_text': marital_text, 'flag': flag, 'bads': bad_count,
                'cid': cluster_id, 'maybes': maybe_count, 'grounded_table': grounded_table,
                'groundless_table': groundless_table, 'html_summary': html_summary, 'c_size': size, 'rdf_data': dt,
                'description': description}

        return expected_components, data

    # except Exception as err:
    #     print(F"ANALYSIS: {err}")
    #     return None, F"\n\n\t\tSorry...\n\t\tNo result could be found for RECONSTITUTED cluster with id [{cluster_id}].", None, None, None


def html_table(db_name, cid='646994'):

    count_ids = 0
    html_data = Buffer()
    clustered = defaultdict(list)
    un_clustered = defaultdict(list)
    t_line_html = Coloring().table_line_html
    main_relations, inv_clusters = 0, set()

    # MAIN Cluster, RELATIONS OF INTEREST AND INVOLVED CLUSTERS
    main_cluster = ast.literal_eval(select_row(db_name=db_name, table='CLUSTERS_TBL', column='id', value=cid)[1])

    # GENERATING THE LINKS FROM THE MAIN CLUSTER
    ids = main_cluster['ids']

    # TABLE HEADER
    html_data.write(
        F"{'-' * (dot_size2 - 6)}<br>{tab}| {'Clustered Identical Persons with P-IDS':53} | "
        F"{'Associated Relations toward Other Associated Persons':88} | "
        F"{'Associated Clusters and Size':28} |<br>{tab}{'-' * (dot_size2 - 6)}<br>")
    html_data.write(F"{tab}|{' ' * (dot_size2 - 8)}|\n")

    def _rsc_name(db_name_, pers_id):

        person = select_row(db_name=db_name_, table='PERSON_TBL', column='id', value=pers_id)
        alt_name = F"{person[f_name].capitalize() if person[f_name] else ''}" \
                     F"{''.join(term[0] if term else '' for term in person[g_name].split(' '))}"
        name = F"{person[f_name].capitalize()}" \
                 F"{''.join(term.capitalize() for term in person[g_name].split(' '))}"

        return name, alt_name

    for p_id in ids:

        # For the clustered persons in the main cluster get the associated clusters and relations
        pid, des = F'p-{p_id}', ''

        # PERSONS ASSOCIATED TO THE RECONSTITUTED CLUSTER
        associated_per = ast.literal_eval(select_row(
            db_name=db_name, table='ASSOCIATION_DICT_TBL', column='id', value=pid)[1])
        sub_name, sub_alt_name = _rsc_name(db_name, pid)

        for [predicate, pid_2] in associated_per:

            main_relations += 1

            # Generate the association using person ID and concatenated name
            obj_name, obj_alt_name = _rsc_name(db_name, pid_2)

            # Populate the person relation dictionary
            p2event = ast.literal_eval(select_row(
                db_name=db_name, table='PERSON_2_EVENTS_TBL', column='id', value=pid_2)[1])

            if len(p2event) > 1:
                print("PERSON WITH MORE THAN ONE EVENT")

            # Find the associated cluster
            associated_clus_id = find_cluster_on_pid(db_name, pid_2.replace('p-', ''))
            row = select_row(db_name=db_name, table='CLUSTERS_TBL', column='id', value=associated_clus_id)
            e_id = p2event[0]
            full_ev = ast.literal_eval(select_row(
                db_name=db_name, table='FULL_EVENTS_TBL', column='id', value=e_id)[1])

            if row is not None:
                # THE CLUSTER OF THE ASSOCIATED RELATIVE
                tp_cluster = ast.literal_eval(row[1])
                des = F"i-{associated_clus_id} of size [{tp_cluster['cor_count']}]"

                event_date = full_ev["eventDate"] if e_id and "eventDate" in full_ev else ''
                text_list = [str(count_ids), pid, sub_name, predicate, e_id, event_date, pid_2, obj_name, des]
                clustered[count_ids].append(t_line_html(text_list))
                # print(F"""{count_ids}. {pid}   {sub_name}  | {predicate} {p2event[0]}  {event_date}  {pid_2}  {obj_name} |   {des}""")

            else:
                des = F"not clustered"
                event_date = full_ev["eventDate"] if e_id and "eventDate" in full_ev else ''
                text_list = [str(count_ids), pid, sub_name, predicate, e_id, event_date, pid_2, obj_name, des]
                un_clustered[count_ids].append(t_line_html(text_list))
                # print(F"""{count_ids}.  {pid}   {sub_name}  | {predicate} {p2event[0]}  {event_date}  {pid_2}  {obj_name} |   {des}""")

        count_ids += 1

    # RECONSTITUTED CONNECTS WITH CLUSTERED EXTENDED RELATIVES
    for key, value in clustered.items():
        for line in value:
            html_data.write(line(0))

    # EMPTY LINES SEPARATING RECON THE TWO OPTIONS
    html_data.write(F"{tab}|{' ' * (dot_size2 - 8)}|\n")
    html_data.write(F"{tab}|{'-' * (dot_size2 - 8)}|\n")
    html_data.write(F"{tab}|{' ' * (dot_size2 - 8)}|\n")

    # RECONSTITUTED THAT DO NOT CONNECT WITH CLUSTERED EXTENDED RELATIVES
    for key, value in un_clustered.items():
        for line in value:
            html_data.write(line(1))

    html_data.write(F"{tab}|{' ' * (dot_size2 - 8)}|\n")
    html_data.write(F"{tab}{'-' * (dot_size2 - 6)}\n")

    style = F"""    <style type='text/css'>
    .content {{max-width: 1400px; margin: auto;}}
    {css_list(0)} {css_list(1)} 
    </style> 
    """

    return F"{style}{html_data.getvalue()}"
