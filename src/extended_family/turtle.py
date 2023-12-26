from src.general.utils import hasher
import src.general.parameters as par
from io import StringIO as Buffer
from datetime import datetime

cid = "cid"
size = "size"
birth = "birth"
mother = "mother"
father = "father"
marriages = "marriages"
divorced = "divorced"
children = "children"
last_delivery_age = "last_delivery_age"

age_first_marriage = "age_of_first_marriage"
children_with_more_than_one_parents = "children_with_more_than_one_parent"
married_children = "married_children"
max_consecutive_age_diff = "max_consecutive_age_diff"
last_first_age_diff = "last_first_age_diff"
associated_clusters = "associated_clusters"
computed_sub_reconstitutions = "computed_sub_reconstitutions"
groundless_resources = "groundless_resources"
expected_sub_reconstitutions = "expected_sub_reconstitutions"
likely = "likely"
unlikely = "broken_hard_rules"
uncertain = "broken_soft_rules"
flag = "flag"
text = "text"

# Design_Intent_Ontology
dio = "<https://w3id.org/dio#>"
dcterms_ns = "<http://purl.org/dc/terms/>"
civ = 'https://iisg.amsterdam/id/civ/'
ind = "<https://iisg.amsterdam/links/person/>"
heuristic_ns = '<https://iisg.amsterdam/id/civ/Heuristic/>'
voidPlus_ns = '<http://lenticularlens.org/voidPlus/>'
validation_set = '<http://lenticularlens.org/voidPlus/ValidationSet/>'
resource_ns = F"{civ}resource/"
voidPlus_pref = 'voidPlus'
heuristic_pref = 'heuristic'
resource = 'resource'
heuristic_name = 'resource:heuristic-Extended_Family'
dcterms = "dcterms"

Validation_set = 'heuristic-Extended_Family-Based_Validations'
reconstitution_set = 'Zeeland-Reconstitutions-Stats'

# PROPERTIES

broken_rule = "broken_rule"
# broken_hard_rule = "broken_hard_rule"
# broken_soft_rule = "broken_soft_rule"

test = {
    "cid": "563339", 'size': 66, 'birth': 4, 'mother': 4, 'father': 4, 'marriages': 0, 'divorced': 0, 'children': 28,
    'children_with_more_than_one_parent': 4, 'married_children': 11, 'age_of_first_marriage': 0, "last_delivery_age": 0,
    'max_consecutive_age_diff': 19, 'last_first_age_diff': 66, 'associated_clusters': 22,
    'computed_sub_reconstitutions': 14, 'groundless_resources': 17, 'expected_sub_reconstitutions': 12,
    'broken_hard_rules': 5, 'broken_soft_rules': 3, 'flag': 'UNLIKELY',
    "text": "voila"}

sr_names = [
    'consecutive-children-age', 'divorce_vs_marriage', 'married-children_vs_children',
    'computed-sub-reconstitutions_vs_expected-sub-reconstitutions', 'groundless-reconstitutions',
    'maximum-children', 'marriages']

hr_names = [
    'one-birth-event', 'one-mother', 'one-father', 'who-is-the-parent', 'max-first-last-age-diff',
    'minimum-age-to-get-married', 'max-procreation-age', 'max-warnings']

p_space = 40


def initialize_triple_data():
    """
        Annaert Seraphina
            - Married at the age of [23, 36], he is known to have had 10 children between the age of 23 and 43.
            - The maximum age difference between two consecutive children is 3 while the first and last children
            are 19 years of age apart.

            Size             : 20  ✔
            Births           :  1  ✔
            Mother           :  1  ✔
            Father           :  1  ✔
            Married          :  2
            Divorced         :  0  ✔
            Children         : 10
            - Cons. Age Diff :  [1, 2, 1, 1, 2, 2, 2, 1, 0, 3] ✔
            - L-F Age Diff   : 19  ✔
            - Married        :  6  ✔
            - parent > 1     :  1  ❌
           ----------------------------------------------------------------------------------------------------------------
           ASSOCIATION SUMMARY
           ----------------------------------------------------------------------------------------------------------------
           ASSOCIATED LINKS      : 25
           ASSOCIATED CLUSTERS   : 10
           NBR OF NEW CLUSTERS   : 7
                {11, 1, 3}
                {18, 5, 7}
                {8, 2}
                {10, 13}
                {6, 15}
                {16, 9}
                {17, 4}
           GROUNDLESS COMPONENTS :  4 ⚠️
           EXPECTED COMPONENTS   :  7 ✔
           ----------------------------------------------------------------------------------------------------------------
           FLAG SUMMARY
           ----------------------------------------------------------------------------------------------------------------
           Maybe                 : 1  ✔
           Bad                   : 1
        """

    return {
        'size': 0, 'birth': 0, 'mother': 0, 'father': 0, 'marriages': 0, 'divorced': 0, 'children': 0,
        'children_with_more_than_one_parents': 0, 'married_children': 0, 'age_of_first_marriage': 0,
        "last_delivery_age": 0, 'max_consecutive_age_diff': 0, 'last_first_age_diff': 0, "associated_clusters": "",
        "computed_sub_reconstitutions": "", "groundless_resources": "", "expected_sub_reconstitutions": "",
        'broken_hard_rules': 0, 'broken_soft_rules': 0, "flag": "", "text": ""}


def view(data):
    for key, value in data.items():
        print(F"\t{key:40}{value:>2}")


def prefixes():
    space = 10
    return F"""
@prefix {'rdf':>{space}}: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix {'rdfs':>{space}}: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix {'dio':>{space}}: {dio} .
@prefix {dcterms:>{space}}: {dcterms_ns} .
@prefix {'civ':>{space}}: <{civ}> .
@prefix {'ind':>{space}}: {ind} .
@prefix {voidPlus_pref:>{space}}: {voidPlus_ns} .
@prefix {'resource':>{space}}: <{resource_ns}> .
    """


def rule_resource(index, soft=True):
    return F"{resource}:S-{sr_names[index]}" if soft else F"{resource}:H-{hr_names[index]}"


def heuristic():
    rdf_rules = Buffer()

    soft_rules = [
        F"Any pair of consecutive children of the RECONSTITUTED SHOULD NOT be more than "
        F"{par.MAX_CONS_AGE_DIFF} years of age apart.",
        F"The RECONSTITUTED SHOULD NOT have divorced more times than it got married.",
        F"The RECONSTITUTED SHOULD NOT have more married children than (s)he had children.",
        F"The number of evidence-based SUB-RECONSTITUTIONS of the RECONSTITUTED SHOULD align with the number of "
        F"expected SUB-RECONSTITUTIONS.",
        F"The RECONSTITUTED SHOULD NOT exhibit groundless SUB-RECONSTITUTIONS.",
        F"The RECONSTITUTED resource should not have more than {par.MAX_CHILDREN} children.",
        F"The RECONSTITUTED resource may not have been married more than {par.MAX_MARRIAGE}"
    ]

    hard_rules = [
        F"The RECONSTITUTED MUST have at most one BIRTH event.",
        F"The RECONSTITUTED MUST share at most one known or/and unknown MOTHER. ",
        F"The RECONSTITUTED MUST share at most one known or/and unknown FATHER.",
        F"For each child X of the RECONSTITUTED, X MUST share at most one BIRTH event.",
        F"The first and last children OF THE RECONSTITUTED MOTHER SHOULD NOT be more than "
        F"{par.MAX_FIRST_LAST} years of age apart.",
        F"The RECONSTITUTED CANNOT be WED before the age of {par.MAX_MARRIAGE_AGE}.",
        F"The RECONSTITUTED CANNOT have a CHILDBIRTH beyond the age of {par.MAX_DELIVERY_AGE}.",
        F"The RECONSTITUTED MUST not be flagged with more than two soft warnings."]

    def get_soft_rule(index):
        return F"""
    {rule_resource(index, soft=True)}
        a                           civ:Rule, civ:Soft-Rule ;
        rdfs:label                  "Extended Family Rule {index}" ;
        {dcterms}:description         "{soft_rules[index]}" .
    """

    def get_hard_rule(index):
        return F"""
    {rule_resource(index, soft=False)}
        a                           civ:Rule, civ:Hard-Rule  ;
        rdfs:label                  "Extended Family Rule {index}" ;
        {dcterms}:description         "{hard_rules[index]}" .
    """

    for i in range(len(soft_rules)):
        rdf_rules.write(get_soft_rule(i))

    for i in range(len(hard_rules)):
        rdf_rules.write(get_hard_rule(i))

    description = F"""
        The Extended-Family heuristic defined here based on a set of rules is intended to help spot obvious clues 
        providing the user with reasons for a manual check of the RECONSTITUTED resource. The provided clues may  
        not be sufficient or tangible justification for accepting or rejecting the RECONSTITUTION but may serve  
        as a starting point for further QUALITY CHECK.
        
        The rules are executed on statistics computed on the network of extended family of A RECONSTITUTED person.
        In this setting, the extended family network consists of relatives such as father - mother - partner(s) and 
        children that appeared together with the RECONSTITUTED person in events they participated in such as BIRTH - 
        MARRIAGE - DIVORCE  - BAPTISM and DEATH.
        
        Finally, two of the SOFT RULES rules defined below (4 and 5) are computed using the CYCLE algorithm which 
        helps finding at least two occurrences with the same RECONSTITUTED relative. These combinations of events  
        happen for example, when the RECONSTITUTED resource appears
        - with the MOTHER/FATHER at the BIRTH, MARRIAGE and/or DEATH events;
        - with a CHILD at her/his BIRTH, BAPTISM, MARRIAGE and/or DEATH events;
        - with a PARTNER at the MARRIAGE, DIVORCE and/or DEATH events.
        Using the algorithm, SUB-RECONSTITUTIONS are generated with the meaning that they bear a supported evidence
        of validity. In other words, two or more occurrences with a RECONSTITUTED relative bear more weight than the 
        occurrences that happened once with a RECONSTITUTED relative.
        
        The rules are organised into SOFT and HARD suggesting the necessity for an in-depth investigation. 
        
        SOFT RULES
        1. {soft_rules[0]} ({rule_resource(0, soft=True)})
        2. {soft_rules[1]} ({rule_resource(1, soft=True)})
        3. {soft_rules[2]} ({rule_resource(2, soft=True)})
        4. {soft_rules[3]} ({rule_resource(3, soft=True)})
        5. {soft_rules[4]} ({rule_resource(4, soft=True)})
        6. {soft_rules[5]} ({rule_resource(5, soft=True)})
        7. {soft_rules[6]} ({rule_resource(6, soft=True)})
    
        HARD RULES
        1. {hard_rules[0]} ({resource}:EF-HR-{0})
        2. {hard_rules[1]} ({resource}:EF-HR-{1})
        3. {hard_rules[2]} ({resource}:EF-HR-{2})
        4. {hard_rules[3]} ({resource}:EF-HR-{3})
        5. {hard_rules[4]} ({resource}:EF-HR-{4})
        6. {hard_rules[5]} ({resource}:EF-HR-{5})
        7, {hard_rules[6]} ({resource}:EF-HR-{6})
        8. {hard_rules[7]} ({resource}:EF-HR-{7})
        """

    triples = F"""
    {rdf_rules.getvalue()}
    {heuristic_name}
        a                           dio:Heuristic ;
        rdfs:label                  "Extended-Family" ;
        {dcterms}:description         \"\"\"{description}\"\"\" .
    """

    return triples


def convert2ttl(data, count=1, stats=None, checks=None):

    # xsd = '"{}"^^xsd:integer'
    # ind_ns = "https://iisg.amsterdam/links/person/"
    # p_ns = 'https://iisg.amsterdam/id/civ/'
    pref = "civ"
    dio_pref = 'dio'
    ind_pref = "ind"
    tab = "    \t"
    # ----------------------------------------------------
    # DESCRIPTION OF SOFT WARNING
    # ----------------------------------------------------

    y = data[max_consecutive_age_diff]

    warning_1 = F"\n{tab}- BROKEN SOFT RULE : there exist at least a pair of consecutive children with {str(y)} " \
                F"years of age difference." if y > par.MAX_CONS_AGE_DIFF else ''

    warning_2 = F"\n{tab}- BROKEN SOFT RULE : there exist more divorce events ({data[divorced]}) than there exist " \
                F"marriage ({data[marriages]}) events." if data[divorced] > data[marriages] else ''

    warning_3 = F"\n{tab}- BROKEN SOFT RULE : there exist more married children ({data[married_children]}) than there  " \
                F"exist children({data[children]})." if data[married_children] > data[children] else ''

    warning_4 = F"\n{tab}- BROKEN SOFT RULE : the number of computed evidence-based SUB-RECONSTITUTIONS " \
                F"({data[computed_sub_reconstitutions]}) do not align with the number of expected" \
                F" SUB-RECONSTITUTIONS ({data[expected_sub_reconstitutions]})." \
        if data[computed_sub_reconstitutions] != data[expected_sub_reconstitutions] else ''

    warning_5 = F"\n{tab}- BROKEN SOFT RULE : there exist ({data[groundless_resources]}) groundless resources." \
        if data[groundless_resources] > 0 else ''

    warning_6 = F"\n{tab}- BROKEN SOFT RULE : the RECONSTITUTED appears to have ({data[children]}) children.'" \
        if data[children] > par.MAX_CHILDREN else ''
    warning_7 = F"\n{tab}- BROKEN SOFT RULE : the RECONSTITUTED appears to have been married ({data[marriages]}) times.'" \
        if data[marriages] > par.MAX_MARRIAGE else ''

    soft_warnings = F"{warning_1}{warning_2}{warning_3}{warning_4}{warning_5}{warning_6}{warning_7}"

    s_rules = [
        # 1. CONSECUTIVE           # 2. DIVORCE vs MARRIAGE        # 3. MARIED CHILDREN vs. CHILDREN
        y > par.MAX_CONS_AGE_DIFF, data[divorced] > data[marriages], data[married_children] > data[children],
        # 4. COMPUTED. SUB-RECONSTRUCTIONS vs EXPECTED. SUB-RECONSTRUCTIONS
        data[computed_sub_reconstitutions] != data[expected_sub_reconstitutions],
        # 5. GROUNDLESS SUB-RECONSTRUCTIONS # 6. NO MORE THAN 20 CHILDREN # 7. MARRIED LESS THAN 5 TIMES
        data[groundless_resources] > 0, data[children] > par.MAX_CHILDREN, data[marriages] > par.MAX_MARRIAGE
    ]

    h_rules = [
        # 1. ONE BIRTH EVENT # 2. ONE MOTHER # 3. ONE FATHER # 4. WHO IS THE PARENT
        data[birth] > 1, data[mother] > 1, data[father] > 1, data[children_with_more_than_one_parents] > 0,
        # 5. MAXIMUM AGE DIFF BETWEEN FIRST AND LAST   # 6.  MINIMUM AGE OF MARRIAGE
        data[last_first_age_diff] > par.MAX_FIRST_LAST, data[age_first_marriage] < par.MAX_MARRIAGE_AGE,
        # 7. MAX CHILD BRITH AGE                        # MAX WARNINGS
        data[last_delivery_age] > par.MAX_DELIVERY_AGE, data[uncertain] > 2
    ]

    rdf_s_rules = F" ,\n{' ' * 53}".join(F"{rule_resource(i, soft=True)}" for i in range(len(s_rules)) if s_rules[i])
    rdf_h_rules = F" ,\n{' ' * 53}".join(F"{rule_resource(i, soft=False)}" for i in range(len(h_rules)) if h_rules[i])

    x = data[children_with_more_than_one_parents]

    # ----------------------------------------------------
    # DESCRIPTION OF HARD WARNING
    # ----------------------------------------------------

    births = F"\n{tab}- BROKEN HARD RULE : it presents {str(data[birth])} birth certificates." \
        if data[birth] > 1 else ''

    mothers = F"\n{tab}- BROKEN HARD RULE : it appears to point to {str(data[mother])} distinct mothers." \
        if data[mother] > 1 else ''

    fathers = F"\n{tab}- BROKEN HARD RULE : it appears to point to {str(data[father])} distinct fathers." \
        if data[father] > 1 else ''

    c_parents = F"\n{tab}- BROKEN HARD RULE : it shows that {str(x)} {'child points' if x == 1 else 'children point'} " \
                F"to at least one other parent." if x > 0 else ''

    age_dif = F"\n{tab}- BROKEN HARD RULE : it appears that there is {str(data[last_first_age_diff])} years of age " \
              F"difference between the first and last child." if data[last_first_age_diff] > par.MAX_FIRST_LAST else ''

    marriage_age = F"\n{tab}- BROKEN HARD RULE : the RECONSTRUCTED appears to have gotten married at the age of" \
                   F" {str(data[age_first_marriage])}." if data[age_first_marriage] < par.MAX_MARRIAGE_AGE else ''

    childbirth_age = F"\n{tab}- BROKEN HARD RULE : the RECONSTRUCTED appears to have had her last child birth at the age of" \
                     F" {str(data[last_delivery_age])}." if data[last_delivery_age] > par.MAX_DELIVERY_AGE else ''

    bad_warning = F"\n{tab}- BROKEN HARD RULE : the RECONSTRUCTED exhibits {str(data[uncertain])} soft warning." \
        if data[uncertain] > 2 else ''

    # ----------------------------------------------------
    # FLAG EXPLANATION
    # ----------------------------------------------------

    predicate = F"\n    \t{pref}:{text:{p_space}}"

    flag_explanation = F"\n{tab}Based on the rules defined in {heuristic_name}, this RECONSTITUTION is " \
                       F"{'very ' if data[unlikely] > 1 else ''}UNLIKELY for the following reason(s):" \
                       F"{births}{mothers}{fathers}{c_parents}{age_dif}{marriage_age}{childbirth_age}" \
                       F"{bad_warning}{soft_warnings}" if data[flag] == 'Unlikely' \
        else F"\n{tab}Based on the rules defined in {heuristic_name}, we are UNCERTAIN about this " \
             F"RECONSTITUTION for the following reason(s):" \
             F"{soft_warnings}" \
        if data[flag] == 'UNCERTAIN' \
        else F"\n{tab}Using the rules defined at {heuristic_name}, we could not find any information " \
             "that could lead to inferring that the RECONSTITUTION is problematic."

    description = F"{predicate} \"\"\"{data[text]}{flag_explanation}\"\"\"" \
        if len(data[text]) > 0 and len(flag_explanation) > 0 else F"{predicate} \"\"\"{data[text]}\"\"\"" \
        if len(data[text]) > 0 else F"{predicate} \"\"\"{flag_explanation}\"\"\"" if len(flag_explanation) > 0 else ''

    soft = F" ;\n{tab}{pref}:{broken_rule:{p_space}} {rdf_s_rules}" if len(rdf_s_rules) > 0 else ''
    hard = F" ;\n{tab}{pref}:{broken_rule:{p_space}} {rdf_h_rules}" if len(rdf_h_rules) > 0 else ''

    validation = F"""
    ### RECONSTITUTION VALIDATION {data[size]}.{count}
    ++++++++++ 
    \t{'a':{p_space + 5}}{'voidPlus:Validation'} ;
    \t{dio_pref}:{'usesHeuristic':{p_space}} {heuristic_name} ;
    \t{pref}:{'validationOf':{p_space}} {ind_pref}:i-{data[cid]:3} ;
    \t{pref}:{unlikely:{p_space}} {data[unlikely]:3} ;
    \t{pref}:{uncertain:{p_space}} {data[uncertain]:3} ;
    \t{pref}:{associated_clusters:{p_space}} {data[associated_clusters]:3} ;
    \t{pref}:{groundless_resources:{p_space}} {data[groundless_resources]:3} ;
    \t{pref}:{computed_sub_reconstitutions:{p_space}} {data[computed_sub_reconstitutions]:3} ;
    \t{pref}:{expected_sub_reconstitutions:{p_space}} {data[expected_sub_reconstitutions]:3} ;
    \t{pref}:{flag:{p_space}} "{data[flag]}"{soft}{hard}{' ;' + description + ' .' if len(description) > 0 else ' .'}
"""

    reconstructed = F"""
    ### RECONSTITUTION STATISTICS {data[size]}.{count}
    {ind_pref}:i-{data[cid]:3}
    \t{pref}:{size:{p_space}} {data[size]:3} ;
    \t{pref}:{birth:{p_space}} {data[birth]:3} ;
    \t{pref}:{mother:{p_space}} {data[mother]:3} ;
    \t{pref}:{father:{p_space}} {data[father]:3} ;
    \t{pref}:{children:{p_space}} {data[children]:3} ;
    \t{pref}:{age_first_marriage:{p_space}} {data[age_first_marriage]:3} ;
    \t{pref}:{marriages:{p_space}} {data[marriages]:3} ;
    \t{pref}:{divorced:{p_space}} {data[divorced]:3} ;
    \t{pref}:{last_delivery_age:{p_space}} {data[last_delivery_age]:3} ;
    \t{pref}:{married_children:{p_space}} {data[married_children]:3} ;
    \t{pref}:{last_first_age_diff:{p_space}} {data[last_first_age_diff]:3} ;
    \t{pref}:{max_consecutive_age_diff:{p_space}} {data[max_consecutive_age_diff]:3} ;
    \t{pref}:{children_with_more_than_one_parents:{p_space}} {data[children_with_more_than_one_parents]:3} ;
    \t{pref}:{'hasValidation':{p_space}} {'++++++++++'} .
"""

    val_code = F"{resource}:check-{str(hasher(validation, size=15))}"
    validation = validation.replace('++++++++++', val_code)
    reconstructed = reconstructed.replace('++++++++++', val_code)

    if stats is not None:
        stats.write(reconstructed)

    if checks is not None:
        checks.write(validation)

    return F"{validation}{reconstructed}"


def namespaces():
    space = 10
    return F"@prefix {'rdf':>{space}}: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n" \
           F"@prefix {'rdfs':>{space}}: <http://www.w3.org/2000/01/rdf-schema#> .\n" \
           F"@prefix {dcterms:>{space}}: {dcterms_ns} .\n" \
           F"@prefix {voidPlus_pref:>{space}}: {voidPlus_ns} .\n" \
           F"@prefix {'resource':>{space}}: <{resource_ns}> .\n" \
           F"@prefix {'dio':>{space}}: {dio} .\n" \
           F"@prefix {'civ':>{space}}: <{civ}> .\n" \
           F"@prefix {'ind':>{space}}: {ind} .\n"


def generate_named_graph(db_name, extra: str, rdf_text: str):

    extra = '' if len(extra) == 0 else F"-{extra}"
    graph = F"resource:{db_name}{extra}-{hasher(rdf_text)}"
    graph_rsc = F"{namespaces()}\n{graph} " + "\n{{{}}}"
    return graph_rsc

    # return graph_rsc + "{{{}}}"


def group_validation2rdf(db_name, c_id, groups: dict):

    idx = 0
    rdf = Buffer()
    modifications = Buffer()
    values = groups.values()
    tab = "\t\t"

    civ_pref = "civ"
    void_plus = 'voidPlus:'
    split_cluster = 'SplitCluster'
    resource_cluster = 'ResourceCluster'
    has_validated_sub_cluster = "hasValidatedSubCluster"
    is_composed_of = "isComposedOf"
    derived_from = "derivedFrom"

    individual = "ind:"
    graph = F"resource:{db_name}-{hasher(groups)}"

    pre_space = 35
    new_line = 40
    rdf.write("\n")
    # INITIATE WITH THE NAMESPACES
    # rdf.write(namespaces())
    graph_rsc = F"{namespaces()}\n{graph} "

    # SET THE GRAPH NAME
    # rdf.write(F"\n{graph} {{\n")
    graph_rsc = graph_rsc + "{{{}}}"

    # START THE GRAPH WITH THE CLUSTER RESOURCE IN QUESTION
    main_group = f"ind:i-{c_id}"
    rdf.write(F"\n\t### {datetime.now()}\n"
              F"\t{main_group}\n")
    rdf.write(F"{tab}{'a':{pre_space + 4}} {void_plus}{resource_cluster},\n"
              F"{tab}{'':{pre_space + 4}} {void_plus}{split_cluster};\n")

    # GENERATE THE RESOURCE CODE FOR EACH SUBMITTED GROUP
    modification_codes = [str(hasher(group, size=15)) for group in groups.values()]

    for persons in values:

        # RDF ON HOW THE CURRENT CLUSTER IS GOT SPLIT
        new_group = F"{individual}i-{idx+1}_{modification_codes[idx]}"
        rdf.write(
            F"{tab}{void_plus}{has_validated_sub_cluster:{pre_space-5}} {new_group} "
            F"{'.' if idx == len(values)-1 else ';'}\n")

        # THE NEW RESOURCE CLUSTERS
        data = """, """.join(
            F"\n{' ':56}{individual}{p}" if (persons.index(p) != 0 and persons.index(p) % 3 == 0) else F"{individual}{p}"
            for p in persons)

        modifications.write(f"\n\t{new_group}\n")
        modifications.write(
            F"{tab}{'a':{pre_space + 4}} {void_plus}{resource_cluster},\n"
            F"{tab}{'':{pre_space + 4}} {void_plus}{split_cluster};\n"
            F"{tab}{void_plus}{derived_from:{pre_space-5}} {main_group} ;\n"
            F"{tab}{void_plus}{is_composed_of:{pre_space-5}} {data} .\n")

        idx += 1

    rdf.write(modifications.getvalue())

    # CLOSE THE GRAPH
    # print(graph_rsc.format(rdf.getvalue()))
    # rdf.write("}")

    return graph_rsc, rdf.getvalue()


# print(prefixes())
# print(heuristic())
# print(convert2ttl(test))
# from src.scripts.Util import check_rdf_file
# check_rdf_file(F"/Users/al/PycharmProjects/Clariah/SIN/src/Evaluations/validation-10.ttl")
