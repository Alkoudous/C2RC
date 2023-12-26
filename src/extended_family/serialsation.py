import ast
from os import path
from sys import stdout
from re import search, findall
from time import time
from datetime import timedelta
from io import StringIO as Buffer
from collections import defaultdict
from rdflib import Dataset
from pathlib import Path
from os.path import basename, splitext

from src.general.colored_text import Coloring
from src.general.utils import formatNumber, summarize_list
from src.general.parameters import TRIPLE_FOLDER
from src.extended_family.db_commands import get_rows, insert_dictionary, insert_person, about_DB, insert_row

color = Coloring().colored
week_date = Coloring().print_week_date


# 1. Think of using a base URI
# 2. Expert user study
# 3 User centric rule based validation if civil registries knowledge graph
# eventID-PersonID

ns_civ = 'https://iisg.amsterdam/id/civ/'
ns_event = 'https://iisg.amsterdam/id/zeeland/event/'
ns_person = 'https://iisg.amsterdam/id/zeeland/person/'

prefix_civ = F"@prefix {'civ:':>10} <{ns_civ}> .\n"
prefix_event = F"@prefix {'ev:':>10} <{ns_event}> .\n"
prefix_person = F"@prefix {'person:':>10} <{ns_person}> .\n"

# =====================================================================================
# 1. SERIALISING THE RECONSTITUTED PERSONS
# =====================================================================================
"""
    1.1 PERSON IDs TO EXTRACT
    @prefix person: <https://iisg.amsterdam/links/person/> .
    @prefix predicate: <https://iisg.amsterdam/links/vocab/> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    --- TRIPLE EXAMPLE ----------------------------------------
    -----------------------------------------------------------
    person:3960236 predicate:personID "3960236"^^xsd:integer .

    1.2 THE BIRTH YEAR OF A RECONSTITUTED PERSON
    @prefix reconstituted: <https://iisg.amsterdam/links/person/> .
    @prefix dbpedia: <http://dbpedia.org/ontology/> .
    --- TRIPLE EXAMPLE ----------------------------------------
    -----------------------------------------------------------
    reconstituted:i-99999 dbpedia:birthYear "1826"^^xsd:gYear .
"""

# THE BIRTH YEAR OF A RECONSTITUTED OBJECT
birth_year = "http://dbpedia.org/ontology/birthYear"

# THE PERSON ID PREDICATE OF A RECONSTITUTED OBJECT
predicate_per_id = "https://iisg.amsterdam/links/vocab/personID"

# A TRIPLE WHERE THE SUBJECT IS A RECONSTITUTED INDIVIDUAL WITH AN INTEGER VALUE
reconstituted_int_value_pattern = F"<.*i-(.*)> <(.*)> [\"]*([\\d*]*)[\"^]*<(.*)>"

# =====================================================================================
# 2. SERIALISING PERSON DATA FROM THE CIVIL REGISTRY
# =====================================================================================
"""
    2.1 RESOURCE IS AT THE SUBJECT POSITION
    FINDING TRIPLES FOR WHICH THE SUBJECT IS A RESOURCE OF TYPE PERSON WITH
    THE URI STARTING WITH <https://iisg.amsterdam/id/zeeland/person/p.....>
    @prefix schema: <http://schema.org/> .
    @prefix person: <https://iisg.amsterdam/id/zeeland/person/> .
    @prefix civ: <https://iisg.amsterdam/id/civ/> .
    --- TRIPLE EXAMPLE ----------------------------------------
    -----------------------------------------------------------
    person:p-1
      a                                      schema:Person ;
      schema:gender                          "m" ;
      schema:familyName                      "stevens" ;
      schema:givenName                       "johannes franciescus" ;
      ...
      civ:personID                            "1"^^<http://www.w3.org/2001/XMLSchema#int> .


    2.2 RESOURCE IS AT THE OBJECT POSITION
    PATTERN WHERE THE PERSON RESOURCE IS AT THE OBJECT POSITION IN THE TRIPLE
    @prefix event: <https://iisg.amsterdam/id/zeeland/event/e-1>.
    --- TRIPLE EXAMPLE ----------------------------------------
    -----------------------------------------------------------
    event:e-1
      civ:newborn                             person:p-1 .
"""

# PATTERN FOR EXTRACTING DATA ABOUT THE OCCURRENCE OF A PERSON
person_pattern = '<.*\\/(p-\\d*)> <(.*)> ["<]*(.*)[">] .'

# =====================================================================================
# 3. SERIALISING EVENTS DATA FROM THE CIVIL REGISTRY
# =====================================================================================
"""
    p-2   : {'father': ['father in e-1']})
    p-3   : {'mother': ['mother in e-1']})
    p-1   : {'newborn': ['newborn in e-1']})
    p-29  : {'father': ['father in e-10']})
"""

# PATTERN FOR EXTRACTING EVENT DATA ABOUT THE OCCURRENCE OF A PERSON
event_pattern_trig = '<.*\\/(e-\\d*)> <.*civ\\/(.*)> <.*\\/(p-\\d*)>'
event_pattern = F'{event_pattern_trig} .'
relation_pattern = '<.*\\/(p-\\d*)> <.*civ\\/(.*)> <.*\\/(p-\\d*)> .'

# PATTERN FOR EXTRACTING ALL EVENT TYPES
# event_type_pattern = '<.*\\/(e-\\d*)> <.*type> <(.*)>'
civ_event_type_pattern = '<.*\\/(e-\\d*)> <.*type> <.*civ\\/(.*)>'
# =====================================================================================
# 4. SERIALISING FULL EVENTS DATA FROM THE CIVIL REGISTRY
# =====================================================================================
"""
    e-1 : {
      'eventDate': '1833-12-23',
      'father': 'p-2',
      'mother': 'p-3',
      'newborn': 'p-1',
      'registrationDate': '1833-12-24',
      'registrationID': '1',
      'registrationSeqID': '34'
    }

    e-100 : {
      'eventDate': '1817-11-17',
      'father': 'p-299',
      'mother': 'p-300',
      'newborn': 'p-298',
      'registrationDate': '1817-11-18',
      'registrationID': '100',
      'registrationSeqID': '62'
    }
"""

# PATTERN FOR EXTRACTING INTEGER RELATED TO EVENTS
xsd_pattern = '<.*\\/(e-\\d*)> <.*civ\\/(.*)> "([-\\d]*)"'

line = '-' * 84
PREPROCESS_LINE = 78

# =====================================================================================
# 5. GENERATING AN EXTENDED FAMILY RELATION IN A TURTLE FILE FORMAT
# =====================================================================================


# BECAUSE AST HAS A PROBLEM WITH A SERIALISATION STARTING WITH DEFAULT DICTIARARY, A
# SOLUTION IS TO REMOVE THAT STRING FROM THE STRING TO DE-SERIALISE
def serialise(data):
    if data.startswith('defaultdict'):
        data = data[data.find("{"):-1]
        return ast.literal_eval(data)
    return ast.literal_eval(data)


def header(message, input_files, output_files: list):

    output, header_line = Buffer(), 100

    output.write(F"\t{'-' * header_line}\n\t{message:^{header_line}}\n\t{'-' * header_line}")

    for i in range(len(input_files)):
        input_f = path.split(input_files[i])
        output.write(F"\n\t- Input Folder-{i + 1}          : {color(6, input_f[0])}"
                     F"\n\t- Input File-{i + 1}            : {color(6, input_f[1])}")

    for i in range(len(output_files)):
        output_f = path.split(output_files[i])
        output.write(F"\n\t- Output Folder-{i + 1}         : {color(6, output_f[0])}"
                     F"\n\t- Output File-{i + 1}           : {color(6, output_f[1])}")

    print(F"{output.getvalue()}")


def split_uri(uri):
    uri = uri.strip()

    if uri is None or len(uri) == 0:
        return None

    if uri.startswith("<") and uri.endswith(">"):
        uri = uri[1:len(uri) - 1]

    # EXPECTED PATTERN
    good_pattern = "(.*[\\/\\#:])(.*)$"

    # CAN BE EXTENDED TO CHECK WHETHER THE URI
    # ENDS WITH NON-ALPHANUMERIC CHARACTERS
    bad_pattern = "(.*)[\\/\\#:\\+& ?-]+$"

    # CHECK WHETHER THE URI MATCHES
    # THE EXPECTED OUTLINED PATTERN
    good = findall(good_pattern, uri)
    bad = findall(bad_pattern, uri)

    # REMOVE THE UNEXPECTED CHARACTERS
    # AND POSSIBLY RETURN THE LOCAL NAME
    if len(bad) > 0:
        return split_uri(bad[0])

    # RETURN THE LOCAL NAME
    elif len(good) > 0 and len(good[0]) > 0:
        return good[0]

    return None, None


def completed(started):
    return color(6, F"{str(timedelta(seconds=time() - started))}")


def completed_2(started):
    return F"{str(timedelta(seconds=time() - started))}"


def completed_job(started, tabs="\t"):
    print('\n{}{:.^100}'.format(tabs, F" COMPLETED IN {timedelta(seconds=time() - started)} "))
    print('{}{:.^100}'.format(tabs, F" JOB DONE! "))


def progress(i, start, text="Progress", tab="", padding=24, pace=50000):
    if i % pace == 0:
        stdout.write(
            F"""\r\x1b[K {tab}{F"- {text:{padding}}: {color(6, formatNumber(i, currency=''))} in {color(6, str(timedelta(seconds=time() - start)))}"}""")
        stdout.flush()


# =====================================================================================
# SERIALISATIONS
# =====================================================================================


# 1. EXTRACT RECONSTITUTED PERSONS AS A DICTIONARY
def extract_reconstituted(db_name):

    db = about_DB(db_name) if db_name is not None else None
    reconstituted_data = db['reconstituted_path'] if db is not None else None

    global line
    F"""{'-'*90}
    ---{'DATA STRUCTURE':^84}---
    {line}
    The RDF file containing RECONSTITUTED individuals is transformed to a dictionary
    using an individual's ID as the key for accessing the following data:
        - Number of person observations
        - Number of births
        - List of birth years
        - List of person IDs for a reconstituted individual

    {line}
    ---{'SERIALIZATION EXAMPLE':^84}---
    {line}
    key   : 0
    value : {{
        'cor_count': 7, 'birth_count': 1, 'years': ['1885'],
        'ids': ['1145835', '1376264', '2420114', '2782525', '2914718', '299993', '619002']
    }}"""

    if db_name is None:
        return False

    i = 0
    start = time()
    co_referents = defaultdict()
    # output_files=[s_coReferents]
    header(message='1. Serialisation of RECONSTITUTED persons from the Reconstruction Dataset',
           input_files=[reconstituted_data], output_files=[])

    # MAPPING CO-REFERENTS TO THEIR RESPECTIVE CLUSTER
    pid2cluster = dict()

    with open(reconstituted_data, 'r', encoding='utf-8') as file:

        for triple in file:
            i += 1
            terms = search(reconstituted_int_value_pattern, triple)
            if terms:
                progress(i, start=start, tab="\t")
                # PERSON ID
                if terms[2] == predicate_per_id:
                    pid2cluster[terms[3]] = terms[1]
                    if terms[1] not in co_referents:
                        co_referents[terms[1]] = {"cor_count": 1, "ids": [terms[3]], "birth_count": 0, "years": []}
                    else:
                        co_referents[terms[1]]["cor_count"] += 1
                        co_referents[terms[1]]["ids"].append(terms[3])
                # BIRTH YEAR
                elif terms[2] == birth_year:
                    if terms[1] not in co_referents:
                        co_referents[terms[1]] = {"cor_count": 0, "ids": [], "birth_count": 1, "years": [terms[3]]}
                    else:
                        co_referents[terms[1]]["birth_count"] += 1
                        co_referents[terms[1]]["years"].append(terms[3])

        print(F"\n\t_ Nbr of reconstituted    : {color(6, formatNumber(len(co_referents), currency=''))}\n"
              F"\t_ Completed in            : {completed(start)}")

    # INSERT IT INTO THE CO-REFERENT TABLE OF THE DB
    cmd = F"INSERT INTO DB_STATIC_INFO (db_name, size_summary) VALUES (?, ?)"
    list_summary = summarize_list(list({val["cor_count"] for val in co_referents.values()}))

    # print(list_summary)
    insert_row(db_name="shared", cmd=cmd, values=(db_name, list_summary))
    insert_dictionary(db_name=db_name, dictionary=co_referents, table='CLUSTERS_TBL')
    insert_dictionary(db_name=db_name, dictionary=pid2cluster, table='PERSON_ID2CLUSTER_TBL')

    return True


# 2. USE OF THE SERIALISED FILE FOR OUTPUTTING SOME STATS AND PLOTTING
def stats_of_reconstructed(db_name):

    multiple_births = 0
    # number of clusters sharing the same birth year count
    births = defaultdict(int)
    # Persons is a dictionary associating a cluster ID to a person
    persons = defaultdict(set)

    if db_name is None:
        return ""

    print("\n\tLOADING THE CO-REFERENTS")
    start_load = time()
    co_referents = get_rows(db_name, table='CLUSTERS_TBL')
    print(F"\t- Done in {completed(start_load)}")

    # ==========================================================================================
    # GENERAL STATS
    # ==========================================================================================
    for row in co_referents:

        cid, c = row[0], serialise(data=row[1])
        birth_count = c["birth_count"]

        # TOTAL NUMBER OF PERSONS CLUSTERED
        for ids in c["ids"]:
            persons[ids].add(cid)

        # CLUSTERS WITH THE SAME NUMBER OF BIRTH YEARS
        births[birth_count] += 1

        # CLUSTERS FOR WITCH MULTIPLE BIRTH YEAR RECORD EXIST
        if birth_count > 1:
            multiple_births += 1

    reconciled = len(co_referents)

    # GENERAL STATISTICS PRINT
    general_stat = F"""
    {line}
    ---{'STATISTICS':^{PREPROCESS_LINE}}---
    {line}
    \t- Person observations                     : {formatNumber(len(persons), currency=""):>10}
    \t- Reconstituted                           : {formatNumber(reconciled, currency=""):>10}
    \t- Reconstituted with NO birthdate         : {formatNumber(births[0], currency=""):>10}\t: {round(births[0] * 100 / reconciled, 2):>5}%
    \t- Reconstituted with ONE birthdate        : {formatNumber(births[1], currency=""):>10}\t: {round(births[1] * 100 / reconciled, 2):>5}%
    \t- Reconstituted with MULTIPLE birthrates  : {formatNumber(multiple_births, currency=""):>10}\t: {round(multiple_births * 100 / reconciled, 2):>5}%
    
    """
    print(general_stat)

    return general_stat


# 3. EXTRACTING PERSONS AND EVENTS FORM THE ZEELAND CIVIL REGISTRY
def extract_registries(db_name):

    """--- THE SERIALIZATION OF PERSONS' OCCURRENCES ------------------------------------
    -------------------------------------------------------------------------------------
    This serialization consist in documenting data about the occurrence of a person
    as a dictionary which is obtained by running a regular expression on two distinct
    triples patters. The first pattern depicts a person-resource
    <https://iisg.amsterdam/id/zeeland/person/p.....> at the SUBJECT position while
    the second tries to extract other related information available  when the resource
    is this time at OBJECT [2] position.

    p-1 defaultdict(<class 'str'>, {
        'gender': 'm',
        'personID': '1'
        'familyName': 'stevens',
        'givenName': 'johannes franciescus',
        'type': 'http://schema.org/Person',
    })

    --- (1) TRIPLE PATTERN OF A PERSON AT THE SUBJECT POSITION -----------------------
    ----------------------------------------------------------------------------------
    <https://iisg.amsterdam/id/zeeland/person/p-1>
        <http://schema.org/familyName>                      "stevens" .
        <http://schema.org/gender>                          "m" .
        <http://schema.org/givenName>                       "johannes franciescus" .
        <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>   <http://schema.org/Person> .
        <https://iisg.amsterdam/id/civ/personID>            "1"^^<http://www.w3.org/2001/XMLSchema#int> .

    --- (2) TRIPLE PATTERN OF A PERSON AT THE OBJECT POSITION ------------------------
    ----------------------------------------------------------------------------------
    <https://iisg.amsterdam/id/zeeland/event/e-1>
        <https://iisg.amsterdam/id/civ/newborn>         <https://iisg.amsterdam/id/zeeland/person/p-1> .

    """

    start = time()
    p, eve, idx = 0, 0, 0
    events_types = set()
    persons, events = dict(), dict()
    full_events = defaultdict(dict)
    person_predicates = defaultdict()
    event_predicates = defaultdict()

    db = about_DB(db_name) if db_name is not None else None
    civil_registries_data = db['registries_path'] if db is not None else None
    header(message='2. Serialisation of PERSON data from the Civil Registries Dataset', input_files=[], output_files=[])

    if db_name is None:
        return {'persons': 0, 'events': 0, "full-events": 0}

    with open(civil_registries_data, 'r', encoding='utf-8') as file:

        for triple in file:
            idx += 1
            progress(idx, start=start, tab="\t")

            # =======================================================================
            # RESOURCE IS AT THE SUBJECT POSITION
            # EXTRACTING DATA ABOUT A PERSON
            # =======================================================================
            # FINDING TRIPLES FOR WHICH THE SUBJECT IS A RESOURCE OF TYPE PERSON WITH
            # THE URI STARTING WITH <https://iisg.amsterdam/id/zeeland/person/p.....>
            # <https://iisg.amsterdam/id/zeeland/person/p-1>
            #       <http://schema.org/familyName>                      "stevens" .
            #       <http://schema.org/gender>                          "m" .
            #       <http://schema.org/givenName>                       "johannes franciescus" .
            #       <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>   <http://schema.org/Person> .
            #       <https://iisg.amsterdam/id/civ/personID>            "1"^^<http://www.w3.org/2001/XMLSchema#int> .
            # p-1 : {
            #   'familyName': 'stevens', 'gender': 'm', 'givenName': 'johannes franciescus',
            #   'type': 'Person', 'personID': '1'})
            # '<.*\\/(p-\\d*)> <(.*)> ["<]*(.*)[">] .'

            subj_triples = search(person_pattern, triple)
            if subj_triples:

                p += 1
                try:
                    obj = (subj_triples[3][:subj_triples[3].index('^')]).replace('"', '')
                except ValueError:
                    obj = subj_triples[3].replace('"', '')

                if obj.__contains__("/"):
                    o_ns, obj = split_uri(obj)

                # SAVING THE PREDICATE USED
                if subj_triples[2] not in person_predicates:

                    # SEPARATE THE NAMESPACE FROM THE PREDICATE
                    ns, predicate = split_uri(subj_triples[2])
                    predicate = subj_triples[2] if predicate is None else predicate

                    # REGISTER THE PREDICATE
                    person_predicates[subj_triples[2]] = predicate

                # REGISTERING THE PERSON AT THE SUBJECT POSITION OF THE TRIPLE
                if subj_triples[1] not in persons:

                    # DICTIONARY LINKING THE PREDICATE THE OBJECT OF THE TRIPLE
                    temp = defaultdict(str)
                    temp[person_predicates[subj_triples[2]]] = obj

                    # THE PERSON IS NOW CONNECTED TO THE OBJECT VIA THE PREDICATE
                    persons[subj_triples[1]] = temp

                else:
                    # FOR A REGISTERED PERSON, LINK THE OBJECT TO THE RIGHT PREDICATE
                    persons[subj_triples[1]][person_predicates[subj_triples[2]]] = obj

            # =======================================================================
            # RESOURCE IS AT THE OBJECT POSITION
            # EXTRACTING EVENTS
            # =======================================================================
            # PATTERN WHERE THE PERSON RESOURCE IS AT THE OBJECT POSITION IN THE TRIPLE
            # <https://iisg.amsterdam/id/zeeland/event/e-1>
            #       <https://iisg.amsterdam/id/civ/newborn>         <https://iisg.amsterdam/id/zeeland/person/p-1> .
            # '<.*\\/(e-\\d*)> <.*civ\\/(.*)> <.*\\/(p-\\d*)> .'

            obj_triple = search(event_pattern, triple)
            if obj_triple:
                eve += 1
                if obj_triple[2] not in event_predicates:
                    ns, predicate = split_uri(obj_triple[2])
                    predicate = obj_triple[2] if predicate is None else predicate
                    event_predicates[obj_triple[2]] = predicate

                # EXTRACTING THE FULL EVENT
                # e-1 {'eventDate': '1833-12-23', 'father': 'p-2', 'mother': 'p-3',
                #      'newborn': 'p-1', 'registrationDate': '1833-12-24',
                #      'registrationID': '1', 'registrationSeqID': '34'}
                full_events[obj_triple[1]][event_predicates[obj_triple[2]]] = obj_triple[3]

                # p-2 : {father: ['father in e-1']}
                if obj_triple[3] not in events:
                    temp = defaultdict(list)
                    temp[event_predicates[obj_triple[2]]].append(
                        F"{event_predicates[obj_triple[2]]} in {obj_triple[1]}")
                    events[obj_triple[3]] = temp

                else:
                    (events[obj_triple[3]])[event_predicates[obj_triple[2]]].append(
                        F"{event_predicates[obj_triple[2]]} in {obj_triple[1]}")

            else:
                xsd_triple = search(xsd_pattern, triple)
                if xsd_triple:
                    if xsd_triple[2] not in event_predicates:
                        ns, predicate = split_uri(xsd_triple[2])
                        predicate = xsd_triple[2] if predicate is None else predicate
                        event_predicates[xsd_triple[2]] = predicate

                    full_events[xsd_triple[1]][event_predicates[xsd_triple[2]]] = xsd_triple[3]

            # EXTRACTING EVENT TYPE
            types = search(civ_event_type_pattern, triple)
            if types:
                events_types.add(types[2])

    # PRINTING ON THE TERMINAL
    # gen_stats = F"""
    # _ Nbr of Persons          : {color(6, formatNumber(len(persons), currency=''))}
    # _ Nbr of Events           : {color(6, formatNumber(len(events), currency=''))}
    # _ Nbr of Full-Events      : {color(6, formatNumber(len(full_events), currency=''))}
    # _ Completed in            : {completed(start)}
    # """
    # print(gen_stats)

    # INSERT IT INTO THE CO-REFERENT TABLE OF THE DB
    t_persons = insert_person(db_name, persons)
    t_events = insert_dictionary(db_name, events, table='EVENTS_TBL')
    t_f_events = insert_dictionary(db_name, full_events, table='FULL_EVENTS_TBL')

    # OUTPUT THE INSERTIONS STATS : NUMBERS OF INSERTED ROWS
    return {'persons': t_persons, 'events': t_events, "full-events": t_f_events}


# 4. GENERATING THE ASSOCIATION FILE (IN TWO FORMATS: TTL AND NT) BASED ON THE EVENT OBJECTS
# IT SPECIFIES THE MAIN PERSON'S EVENT, THE WITNESSES AND THE EVENT ID
# ### DEATH ASSOCIATION 1
# person:p-3624675
# 	civ:dHasMother  person:p-3624678 ;
# 	civ:dHasFather  person:p-3624677 ;
# 	civ:dHasPartner person:p-3624676 ;
# 	civ:inEvent     ev:e-1000000 .
def associations_ttl(db_name):

    """--- THE SERIALIZATION OF PERSONS' OCCURRENCES ------------------------------------
    ----------------------------------------------------------------------------------
    With this preprocessing a .ttl file format is generated for representing the
    extended family of each person recorded withing the Civil Registries dataset.
    A second file is also generated as a list of dictionaries serialisation using the
    previous files so that all information about a particular individual could be
    quickly fetched.

    --- EXAMPLE: Extended Family -----------------------------------------------------
    ----------------------------------------------------------------------------------
    ### DEATH ASSOCIATION 121111
    person:p-4037410
        civ:dHasMother  person:p-4037413 ;
        civ:dHasFather  person:p-4037412 ;
        civ:dHasPartner person:p-4037411 ;
        civ:inEvent     ev:e-1121144 .

    --- EXAMPLE: Extended Family -dictionary -----------------------------------------
    ----------------------------------------------------------------------------------
    {
        'http://schema.org/gender': 'm',
        'https://iisg.amsterdam/id/civ/age': '0',
        'http://schema.org/givenName': 'levenloos',
        'http://schema.org/familyName': 'verstringe',
        'https://iisg.amsterdam/id/civ/personID': '4666885',
        'http://www.w3.org/1999/02/22-rdf-syntax-ns#type': 'http://schema.org/Person'
    }
    """

    start = time()
    ev_idx = 0
    space, ns = 15, 80
    events = dict()
    ev_types = set()
    issues = Buffer()
    predicates = set()
    pred_writer = Buffer()
    type_writer = Buffer()
    summary_writer = Buffer()
    person2event = defaultdict(list)

    ttl_relations_file = Path(TRIPLE_FOLDER) / F"{db_name}-Relations.ttl"
    nt_relations_file = Path(TRIPLE_FOLDER) / F"{db_name}-Relations.nt"

    db = about_DB(db_name) if db_name is not None else None
    civil_registries_data = db['registries_path'] if db is not None else None

    issues.write(F"\n\n\t=== Issues Found ===\n\t{'-' * 20}\n")
    summary_writer.write(F"\n\t=== SUMMARY ===\n\t{'-' * 15}\n")
    births, marriages, divorces, deaths, counter, idx = 0, 0, 0, 0, 0, 0
    header(message='3. Creation of the EXTENDED FAMILY per reconstituted person using the Civil Registries Dataset',
           input_files=[civil_registries_data], output_files=[ttl_relations_file, nt_relations_file])

    # READ THE CIVIL REGISTRY AND FETCH ALL EVENTS
    with open(civil_registries_data, 'r', encoding='utf-8') as file:

        for triple in file:
            ev_idx += 1
            progress(ev_idx, start=start, text="CIV Progress", tab="\t")

            # '<.*\\/(e-\\d*)> <.*civ\\/(.*)> <.*\\/(p-\\d*)>'
            found = search(event_pattern_trig, triple)
            if found:
                predicates.add(found[2])
                if found[1] not in events:
                    events[found[1]] = {found[2]: found[3]}
                else:
                    events[found[1]][found[2]] = found[3]

            e_type = search(civ_event_type_pattern, triple)
            if e_type:
                ev_types.add(e_type[2])
                if e_type[1] not in events:
                    events[e_type[1]] = {'type': e_type[2]}
                else:
                    events[e_type[1]]['type'] = e_type[2]

        # === Event Types Found ===
        type_writer.write(F"\n\n\t=== Event Types Found ===\n\t{'-' * 25}")
        type_writer.write("".join(F"\n\t- {item}" for item in ev_types))

        # === Predicates Found ===
        pred_writer.write(F"\n\n\t=== Predicates Found ===\n\t{'-' * 24}")
        pred_writer.write("".join(F"\n\t- {item}" for item in predicates))

    print("")

    # WRITING OUT TO THE ASSOCIATION FILE
    with open(ttl_relations_file, "w") as ttl_file:

        ttl_file.write(F"{'#' * ns}\n#{'NAMESPACE':^{ns - 2}}#\n{'#' * ns}\n\n"
                       F"@prefix {'ev:':>10} <{ns_event}> .\n"
                       F"@prefix {'civ:':>10} <{ns_civ}> .\n"
                       F"@prefix {'person:':>10} <{ns_person}> .\n\n\n"
                       F"{'#' * ns}\n#{'ASSOCIATIONS':^{ns - 2}}#\n{'#' * ns}\n\n")

        for e_id, event in events.items():

            idx += 1
            progress(idx, start=start, text="TTL Progress", tab="\t")

            # -----------------------------
            # ABOUT BIRTH EVENTS OPTION 1
            # -----------------------------

            if 'type' not in event:

                if 'newborn' in event:

                    births += 1
                    person2event[event['newborn']].append(e_id)

                    # GENERATE THE ASSOCIATION
                    # THE NEWBORN HAS BOTH A FATHER AND A MOTHER
                    if 'father' in event and 'mother' in event:
                        person2event[event['father']].append(e_id)
                        person2event[event['mother']].append(e_id)
                        ttl_file.write(F"### BIRTH ASSOCIATION {births}\n"
                                       F"person:{event['newborn']}\n"
                                       F"\t{'civ:inEvent':{space}} ev:{e_id} ;\n"
                                       F"\t{'civ:nHasFather':{space}} person:{event['father']} ;\n"
                                       F"\t{'civ:nHasMother':{space}} person:{event['mother']} .\n\n")

                    # MAYBE A MISSING PARENT
                    # THE NEWBORN HAS A FATHER
                    elif 'father' in event:
                        person2event[event['father']].append(e_id)
                        ttl_file.write(F"### BIRTH ASSOCIATION {births}\n"
                                       F"person:{event['newborn']}\n"
                                       F"\t{'civ:inEvent':{space}} ev:{e_id} ;\n"
                                       F"\t{'civ:nHasFather':{space}} person:{event['father']} .\n\n")

                    # THE NEWBORN HAS A MOTHER
                    elif 'mother' in event:
                        person2event[event['mother']].append(e_id)
                        ttl_file.write(F"### BIRTH ASSOCIATION {births}\n"
                                       F"person:{event['newborn']}\n"
                                       F"\t{'civ:inEvent':{space}} ev:{e_id} ;\n"
                                       F"\t{'civ:nHasMother':{space}} person:{event['mother']} .\n\n")

                counter += 1

            # -----------------------------
            # ABOUT BIRTH EVENTS OPTION 2
            # -----------------------------

            elif event['type'] == 'Birth':
                births += 1
                # MISSING NEWBORN
                if 'newborn' not in event:
                    issues.write(F"\t{e_id} with no birth\n")

                # GENERATE THE ASSOCIATION THAT THE NEWBORN HAS A FATHER AND A MOTHER
                elif 'father' in event and 'mother' in event:
                    person2event[event['newborn']].append(e_id)
                    person2event[event['father']].append(e_id)
                    person2event[event['mother']].append(e_id)
                    ttl_file.write(F"### BIRTH ASSOCIATION {births}\n"
                                   F"person:{event['newborn']}\n"
                                   F"\t{'civ:inEvent':{space}} ev:{e_id} ;\n"
                                   F"\t{'civ:nHasFather':{space}} person:{event['father']} ;\n"
                                   F"\t{'civ:nHasMother':{space}} person:{event['mother']} .\n\n")

                # GENERATE THE ASSOCIATION THAT THE NEWBORN ONLY HAS A FATHER
                elif 'father' in event:
                    person2event[event['newborn']].append(e_id)
                    person2event[event['father']].append(e_id)
                    ttl_file.write(F"### BIRTH ASSOCIATION {births}\n"
                                   F"person:{event['newborn']}\n"
                                   F"\t{'civ:inEvent':{space}} ev:{e_id} ;\n"
                                   F"\t{'civ:nHasFather':{space}} person:{event['father']} .\n\n")

                # GENERATE THE ASSOCIATION THAT THE NEWBORN ONLY HAS A MOTHER
                elif 'mother' in event:
                    person2event[event['newborn']].append(e_id)
                    person2event[event['mother']].append(e_id)
                    ttl_file.write(F"### BIRTH ASSOCIATION {births}\n"
                                   F"person:{event['newborn']}\n"
                                   F"\t{'civ:inEvent':{space}} ev:{e_id} ;\n"
                                   F"\t{'civ:nHasMother':{space}} person:{event['mother']} .\n\n")

            # -----------------------------
            # ABOUT MARRIAGE EVENTS
            # -----------------------------

            elif event['type'] == 'Marriage':
                marriages += 1
                bride_m, bride_f, groom_m, groom_f = '', '', '', ''
                # print(event)

                # POSSIBLE RELATIONS
                if 'motherBride' in event:
                    person2event[event['motherBride']].append(e_id)
                    bride_m = F"\t{'civ:bHasMother':{space}} person:{event['motherBride']} ;\n"
                if 'fatherBride' in event:
                    person2event[event['fatherBride']].append(e_id)
                    bride_f = F"\t{'civ:bHasFather':{space}} person:{event['fatherBride']} ;\n"
                if 'motherGroom' in event:
                    person2event[event['motherGroom']].append(e_id)
                    groom_m = F"\t{'civ:gHasMother':{space}} person:{event['motherGroom']} ;\n"
                if 'fatherGroom' in event:
                    person2event[event['fatherGroom']].append(e_id)
                    groom_f = F"\t{'civ:gHasFather':{space}} person:{event['fatherGroom']} ;\n"

                # WRITE THE MARRIAGE TO FILE
                ttl_file.write(F"### MARRIAGE ASSOCIATION {marriages}\n")
                if 'bride' in event and 'groom' in event:
                    ttl_file.write(F"person:{event['bride']}\n"
                                   F"\t{'civ:married':{space}} person:{event['groom']} ;\n"
                                   F"\t{'civ:inEvent':{space}} ev:{e_id} .\n\n")

                # WRITE THE PARENTS OF BRIDE TO FILE
                if 'bride' in event:
                    person2event[event['bride']].append(e_id)
                    ttl_file.write(F"person:{event['bride']}\n"
                                   F"{bride_m}{bride_f}"
                                   F"\t{'civ:inEvent':{space}} ev:{e_id} .\n\n")

                # WRITE THE PARENTS OF GROOM TO FILE
                if 'groom' in event:
                    person2event[event['groom']].append(e_id)
                    ttl_file.write(F"person:{event['groom']}\n"
                                   F"{groom_m}{groom_f}"
                                   F"\t{'civ:inEvent':{space}} ev:{e_id} .\n\n")

                # MISSING BRIDE OR GROOM
                if 'bride' not in event:
                    issues.write(F"\t{e_id} with no bride\n")

                if 'groom' not in event:
                    issues.write(F"\t{e_id} with no groom\n")

            # -----------------------------
            # ABOUT DIVORCE EVENTS
            # -----------------------------

            elif event['type'] == 'Divorce':
                divorces += 1
                bride_m, bride_f, groom_m, groom_f = '', '', '', ''

                # POSSIBLE RELATIONS
                if 'bride' in event:

                    person2event[event['bride']].append(e_id)
                    if 'motherBride' in event:
                        person2event[event['motherBride']].append(e_id)
                        bride_m = F"\t{'civ:bHasMother':{space}} person:{event['motherBride']} ;\n"

                    if 'fatherBride' in event:
                        person2event[event['fatherBride']].append(e_id)
                        bride_f = F"\t{'civ:bHasFather':{space}} person:{event['fatherBride']} ;\n"

                if 'groom' in event:

                    person2event[event['groom']].append(e_id)
                    if 'motherGroom' in event:
                        person2event[event['motherGroom']].append(e_id)
                        groom_m = F"\t{'civ:gHasMother':{space}} person:{event['motherGroom']} ;\n"

                    if 'fatherGroom' in event:
                        person2event[event['fatherGroom']].append(e_id)
                        groom_f = F"\t{'civ:gHasFather':{space}} person:{event['fatherGroom']} ;\n"

                # WRITE THE DIVORCES TO FILE
                ttl_file.write(F"### DIVORCE ASSOCIATION {divorces}\n")
                ttl_file.write(F"person:{event['bride']}\n"
                               F"\t{'civ:divorced':{space}} person:{event['groom']} ;\n"
                               F"\t{'civ:inEvent':{space}} ev:{e_id} .\n\n")

                # WRITE THE PARENTS OF BRIDE TO FILE
                ttl_file.write(F"person:{event['bride']}\n"
                               F"{bride_m}{bride_f}"
                               F"\t{'civ:inEvent':{space}} ev:{e_id} .\n\n")

                # ttl_file THE PARENTS OF GROOM TO FILE
                ttl_file.write(F"person:{event['groom']}\n"
                               F"{groom_m}{groom_f}"
                               F"\t{'civ:inEvent':{space}} ev:{e_id} .\n\n")

            # -----------------------------
            # ABOUT DEATH EVENTS
            # -----------------------------

            elif event['type'] == 'Death':
                deaths += 1
                mother, father, partner = '', '', ''

                # POSSIBLE RELATION
                if 'father' in event:
                    person2event[event['father']].append(e_id)
                    father = F"\t{'civ:dHasFather':{space}} person:{event['father']} ;\n"
                if 'mother' in event:
                    person2event[event['mother']].append(e_id)
                    mother = F"\t{'civ:dHasMother':{space}} person:{event['mother']} ;\n"
                if 'partner' in event:
                    person2event[event['partner']].append(e_id)
                    partner = F"\t{'civ:dHasPartner':{space}} person:{event['partner']} ;\n"

                # WRITE TO FILE
                ttl_file.write(F"### DEATH ASSOCIATION {deaths}\n"
                               F"person:{event['deceased']}\n"
                               F"{mother}{father}{partner}"
                               F"\t{'civ:inEvent':{space}} ev:{e_id} .\n\n")

            # == Issues Found ===
            else:
                issues.write(str(event))

        # === SUMMARY ===
        summary_writer.write(
              F"\t- Events    : {formatNumber(len(events), currency=''):>9}\n"
              F"\t- Newborns  : {formatNumber(births, currency=''):>9}\n"
              F"\t- Marriages : {formatNumber(marriages, currency=''):>9}\n"
              F"\t- Divorces  : {formatNumber(divorces, currency=''):>9}\n"
              F"\t- Deaths    : {formatNumber(deaths, currency=''):>9}\n"
              F"\t- ----------------------\n"
              F"\t- Totals    : {formatNumber(births + marriages + divorces + deaths, currency=''):>9}")

        # print(f"{type_writer.getvalue()}{pred_writer.getvalue()}{issues.getvalue()}{issues.getvalue()}")

    insert_dictionary(db_name, person2event, table='PERSON_2_EVENTS_TBL')

    print(F"\t- Data                    : Loading it to RDFLIB")

    # CHECK FOR THE CORRECTNESS OF THE FILE
    # g = check_rdf_file(ttl_relations_file)

    g = Dataset()
    rdf_file = basename(ttl_relations_file)
    extension = splitext(rdf_file)[1]
    extension = extension.replace(".", "")
    graph_format = extension
    if graph_format == 'ttl':
        graph_format = "turtle"
    g.parse(source=ttl_relations_file, format=graph_format)

    print(F"\t- Data                    : Saving it to file as ntriples")
    g.serialize(destination=nt_relations_file, format="ntriples", encoding="utf-8")

    return len(g)


# 5. GENERATE THE ASSOCIATION DICTIONARY WITH THE RELATION TYPE
# association_resource(data_1=s_person_registries, data_2=nt_relations_file)
def association_resource(db_name):

    start, counter = time(), 0
    association_dict = defaultdict(list)
    nt_relations_file = Path(TRIPLE_FOLDER) / F"{db_name}-Relations.nt"

    # {'http://schema.org/familyName': 'verstringe', 'http://schema.org/gender': 'm',
    # 'http://schema.org/givenName': 'levenloos',
    # 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type': 'http://schema.org/Person',
    # 'https://iisg.amsterdam/id/civ/age': '0', 'https://iisg.amsterdam/id/civ/personID': '4666885'}

    header(message='4. Creation of RESOURCE ASSOCIATIONS dictionary', input_files=[], output_files=[])

    # THE OBJECT ABOUT PERSON RELATIONS FROM THE CIVIL REGISTRY
    with open(nt_relations_file, "r") as triples:

        for triple in triples:
            counter += 1
            # '<.*\\/(p-\\d*)> <.*civ\\/(.*)> <.*\\/(p-\\d*)> .'
            terms = search(relation_pattern, triple)
            progress(counter, start=start, tab="\t")

            if terms:

                # 1. THE ORIGINAL TRIPLE DIRECTION
                association_dict[terms[1]].append([F"--{terms[2]:-^10}->", terms[3]])

                # 2. THE NEWBORN SPECIAL CASE
                if terms[2] == 'nHasMother':
                    association_dict[terms[3]].append([F"<-{'hasMother':-^10}--", terms[1]])

                elif terms[2] == 'nHasFather':
                    association_dict[terms[3]].append([F"<-{'hasFather':-^10}--", terms[1]])

                # 3. THE REVERSED TRIPLE DIRECTION
                # elif terms[2] in ['married', 'divorced']:
                else:
                    # print(F"<-{terms[2]:-^10}--")
                    association_dict[terms[3]].append([F"<-{terms[2]:-^10}--", terms[1]])

    print(F"\n\t- Saving the relation list object"
          F"\n\t- Saving the relation dictionary object")

    insert_dictionary(db_name, association_dict, table='ASSOCIATION_DICT_TBL')

    return True


# =====================================================================================
# EXECUTION
# =====================================================================================

