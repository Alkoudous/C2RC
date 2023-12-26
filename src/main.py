
# =================================================================================================================
# INSTALLATION
# =================================================================================================================

# pip install pipreqs
# pipreqs /path/to/project

# 1. IDE                PYCHARM : https://www.jetbrains.com/products/compare/?product=pycharm&product=pycharm-ce
# 2. PACKAGE MANAGER    CONDA   : https://conda.io/projects/conda/en/latest/user-guide/getting-started.html
# 3. LIBRARIES
#   FLASK                       : pip install flask
#   RDFLIB                      : pip install rdflib
#   DATE UTIL                   : pip install python_dateutil
#   GRAPH-TOOL                  : conda install -c conda-forge graph-tool
# 4. INSTALLATION
#   In Pycharm, create a new project "C2RC" using CONDA as your new environment.
#   Once created, add the src folder to the C2RC folder.
#   Open src/main.py in pycharm.
#   Right click it and run to get the server running
#   The UI can then be found at http://127.0.0.1:5000

# DARK BROWN  : #663333
# Gray        : #757574

# =================================================================================================================
# =================================================================================================================

import ast
import math
import random

from datetime import datetime
from datetime import timedelta

from re import search
from string import capwords
from time import time
from sys import stdout
from os import listdir, remove, mkdir, rename
from os.path import join, exists
from io import StringIO as Buffer
from collections import defaultdict
from flask import Flask, render_template, request, Response
from pathlib import Path

import src.extended_family.turtle as ttl
import src.general.parameters as par
from src.general.utils import summarize_list, serialise, formatNumber
from src.general.colored_text import Coloring
from src.extended_family import db_commands as func
from src.web.db.schemas.init_db import initiate, initiate_shared
from src.extended_family.quality_controller import quality_check, cycle_check
from src.extended_family.serialsation import stats_of_reconstructed, week_date, \
    extract_reconstituted, extract_registries, associations_ttl, association_resource
from src.data.outputs.serialised import SERIALIZATION_Folder

from src.general.parameters import f_name, g_name

# ===============================================================================================
app = Flask('CivCleaner', template_folder='./web/templates', static_folder='./web/static')
# ===============================================================================================


clr = Coloring().colored

ABOVE = 25
PADDING = 30
LINE = '-' * 84
PREPROCESS_LINE = 78
DEFAULT_LIMIT = 10
GREEN, BLACK = "color: green", "color: black"
OUTPUT_FILE_TABLE = 'output_files'
DB_ROUTE_FOLDER = "./web/db/databases/"
DATA_INPUT_FOLDER = "./data/inputs/"
TRIPLE_FOLDER = Path(SERIALIZATION_Folder) / "Triples"


# ===============================================================================================
#                                      DATABASE COMMANDS
# ===============================================================================================
#     c_size integer PRIMARY KEY,
#     total integer NOT NULl,
#     likelyWithoutWarning integer NOT NULl,
#     likelyWithWarning integer NOT NULl,
#     uncertain integer NOT NULl,
#     unlikely integer NOT NULl


INSERT = {
    'state': "INSERT INTO STATE_TBL (cluster_size, max_pages, current_page, table_row, table_limit, "
             "filter, validated, hide_table) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",

    'manual_validation': "INSERT INTO RDF_MANUAL_VALIDATION_TBL (cid, c_size, validation) VALUES (?, ?, ?)",

    'eval_stats': "INSERT INTO EVAL_STATS "
                  "(c_size, total, likelyWithoutWarning, likelyWithWarning, uncertain, unlikely) VALUES (?, ?, ?, ?, ?, ?)",

    'db_name': "INSERT INTO SELECTED_DB_TBL (db_name) VALUES (?)",
    'output': F"INSERT INTO {OUTPUT_FILE_TABLE} (name, description) VALUES (?, ?)",
    'result': "INSERT INTO RESULT_TBL (cid, c_size, name, flag, marital_text, bads, maybes, summary, " 
                F"grounded_table, groundless_table, rdf_data, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
}

SELECT = {

    'name':  F'SELECT * FROM {OUTPUT_FILE_TABLE} WHERE name = ?',
    'stats': "SELECT * FROM EVAL_STATS ORDER BY c_size",
    'overall_stats': "SELECT stats FROM DATABASE_TBL WHERE name = '{db_name}'",
    'size_summary': 'SELECT size_summary FROM DB_STATIC_INFO WHERE db_name = ?',
    'size_flags': """
        SELECT likely_s, likely, uncertain, unlikely, total FROM 
            (SELECT COUNT(DISTINCT cid) as likely_s FROM RESULT_TBL WHERE c_size={0} AND maybes=0 AND flag='Likely'),
            (SELECT COUNT(DISTINCT cid) as likely FROM RESULT_TBL WHERE c_size={0} AND maybes>0 AND flag='Likely'),
            (SELECT COUNT(DISTINCT cid) as uncertain FROM RESULT_TBL WHERE c_size={0} AND flag='Uncertain'),
            (SELECT COUNT(DISTINCT cid) as unlikely FROM RESULT_TBL WHERE c_size={0} AND flag='Unlikely'),
            (SELECT COUNT(DISTINCT cid) as total FROM RESULT_TBL WHERE c_size={0});
    """,
    'all_flags': """
    SELECT likely_s, likely, uncertain, unlikely, total FROM 
        (SELECT COUNT(DISTINCT cid) as likely_s FROM RESULT_TBL WHERE maybes=0 AND flag='Likely'),
        (SELECT COUNT(DISTINCT cid) as likely FROM RESULT_TBL WHERE maybes>0 AND flag='Likely'),
        (SELECT COUNT(DISTINCT cid) as uncertain FROM RESULT_TBL WHERE flag='Uncertain'),
        (SELECT COUNT(DISTINCT cid) as unlikely FROM RESULT_TBL WHERE flag='Unlikely'),
        (SELECT COUNT(DISTINCT cid) as total FROM RESULT_TBL);
    """,
    "likely": "SELECT COUNT(DISTINCT cid) FROM RESULT_TBL WHERE c_size={c_size} AND flag='Likely';"
}

UPDATE = {
    'state': "UPDATE STATE_TBL SET (cluster_size, max_pages, current_page, table_row, table_limit, "
             "filter, validated, hide_table) = ({values})",
    'hide-table': "UPDATE STATE_TBL SET (hide_table) = ({values})",
    'state_2': "UPDATE STATE_TBL SET (cluster_size, max_pages, current_page, table_row, table_limit, "
               "filter, validated)  = ({values})",
    'db_name': "UPDATE SELECTED_DB_TBL SET db_name = '{new_db_name}' WHERE db_name = '{old_db_name}' ;",
    'local_db_name': "UPDATE DATABASE_TBL SET name='{new_db_name}' WHERE name='{old_db_name}' ;",
    'overall_stats': """UPDATE DATABASE_TBL SET stats="{stats}" WHERE name='{db_name}' ;""",
    'validated': "UPDATE RESULT_TBL SET validated='yes' WHERE cid={} ;",
    'validated_set': "UPDATE RESULT_TBL SET validated='yes' WHERE cid IN ({}) ;",
    'validated_no': "UPDATE RESULT_TBL SET validated='no' WHERE cid={} ;",
    'validated_no_sel': "UPDATE RESULT_TBL SET validated='no' WHERE cid IN ({}) ;",
    'validation': "UPDATE RDF_MANUAL_VALIDATION_TBL SET validation='{}' WHERE cid={}",
    'validated_table': """UPDATE RESULT_TBL SET validated_table="{validated_table}" WHERE cid={cid} ;""",
}

DELETE = {
    'db': "DELETE FROM 'SELECTED_DB_TBL' WHERE db_name = '{db_name}';",
    'manual_validation': "DELETE FROM RDF_MANUAL_VALIDATION_TBL WHERE cid={cid}"}


# ===============================================================================================
#                                           HELPERS
# ===============================================================================================


def progressOut(i, total, start=None, bars=50):

    increment = 100/float(bars)
    ratio = i * bars / total if total > 0 else 0
    dif = "" if start is None else F" in {str(timedelta(seconds=time() - start))}"
    progressed = u"\u2588" * int(round(ratio, 0))
    progressed = F"| {progressed:{bars}} | {str(round(ratio * increment, 0)):>5}%{dif} [{i}] "

    stdout.write(F"\r\x1b[K \t{progressed.__str__()}")
    stdout.flush()


def completed_job(started, tabs="\t"):
    print('\n{}{:.^100}'.format(tabs, F" COMPLETED IN {timedelta(seconds=time() - started)} "))
    print('{}{:.^100}\n'.format(tabs, F" JOB DONE! "))


def get_db_fle_names():

    # GETTING THE DB FILE NAMES FROM THE DB FOLDER
    result = [
        f.replace('.db', "") for f in listdir(DB_ROUTE_FOLDER)
        if f.endswith('.db') and f not in ['None.db', 'shared.db']]
    result.sort()
    return result


def selected_db():
    selected = func.select_last_row(db_name='shared', table='SELECTED_DB_TBL', column='id')
    if selected is None:
        return None
    return selected['db_name']


def update_selected_db(db_name):

    print("\nUpdating")
    c = Coloring()
    # files = get_db_fle_names()
    selected_db_name = selected_db()

    # INSERT THE FIRST ROW IF THE TABLE IS EMPTY
    if selected_db_name is None:
        print(F"\t- Newly selected name: {db_name}")
        func.insert_row(db_name='shared', cmd=INSERT['db_name'], values=[db_name])

    # AS IT IS NOT EMPTY, UPDATE THE FIRST ROW
    elif len(db_name) > 1:
        print(F"\t- Update selected DB from {c.colored(7, selected_db_name)} to {c.colored(7, db_name)}")
        func.update(db_name='shared', cmd=UPDATE['db_name'].format(new_db_name=db_name, old_db_name=selected_db_name))


def refresh_ds():

    # GET THE LATEST UPDATE ON THE DB FILES
    databases = []

    # GETTING THE DB FILE NAMES FROM THE DB FOLDER
    files = get_db_fle_names()

    if len(files) > 0:

        for file in files:
            db_name = file.replace('.db', "")

            # VERIFY WEATHER THE DB EXISTS
            current_db = func.get_database(db_name)

            if current_db is not None:
                databases.append(current_db)

    return {'files': databases, "db": files}


def check_process_count():

    # CHECK WHETHER THE DATA HAS BEEN PROCESSED COMPLETELY AS THERE  FOUR STEPS FOR IT COMPLETION

    selected_db_name = selected_db()
    process_count = 0
    if selected_db_name is not None:

        process_count += 1 if func.select_row(
            db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Co-referents') is not None else 0

        process_count += 1 if func.select_row(
            db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Persons') is not None else 0

        process_count += 1 if func.select_row(
            db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Extended-Family1') is not None else 0

        process_count += 1 if func.select_row(
            db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Extended-Family2') is not None else 0

    return process_count


def process_message():

    # RETURN THE STATUS OF THE PRE-PROCESSED DB. THERE ARE 4 STEPS FOR IT COMPLETION
    selected_db_name = selected_db()
    reconstituted_check, civil_registries_check, extended_family1_check, extended_family2_check = None, None, None, None

    process_count = 0
    if selected_db_name is not None:
        reconstituted_check = func.select_row(
            db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Co-referents')
        civil_registries_check = func.select_row(
            db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Persons')
        extended_family1_check = func.select_row(
            db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Extended-Family1')
        extended_family2_check = func.select_row(
            db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Extended-Family2')

    process_count += 1 if reconstituted_check is not None else 0
    process_count += 1 if civil_registries_check is not None else 0
    process_count += 1 if extended_family1_check is not None else 0
    process_count += 1 if extended_family2_check is not None else 0

    description = F"""
    The uploaded datasets are processed in four stages.
    A completed process is followed by ✔ DONE.
    To run a process followed by ❌ NOT DONE, click the corresponding tab.
    To run all 4 processes or all remaining in one go, click the "Process All" tab.

        1. Reconstituted                        {'✔ DONE' if reconstituted_check is not None else '❌ NOT DONE'}
        2. Civil Registries                     {'✔ DONE' if civil_registries_check is not None else '❌ NOT DONE'}
        3. Extended Family (Turtle file)        {'✔ DONE' if extended_family1_check is not None else '❌ NOT DONE'}
        4. Extended Family (Resources)          {'✔ DONE' if extended_family2_check is not None else '❌ NOT DONE'}
    """

    # Return the description of path process and the file path
    return description, process_count


def available_size(db_name, size, flag_filter, validated, limit=0):

    # IN HERE THE CODE RETRIEVES ALL CLUSTER SISES AVAILABLE
    # WITHIN THE CURRENT DB AS WELL AS THE PROCESSED SISES

    selected_size = size
    validated = '' if validated == 'ignore' or len(validated) == 0 else F" AND validated='{validated}'"

    print(flag_filter)

    maybes = ' AND maybes>0' if flag_filter == "Likely" else ('AND maybes=0' if flag_filter == 'Likely-Star' else '')
    flag_filter = flag_filter.replace("-Star", '') if flag_filter.__contains__("-Star") else flag_filter

    flag_filter = '' if flag_filter == 'All' or len(flag_filter) == 0 else F" AND flag='{flag_filter}'"
    size = '' if selected_size is None else F"WHERE c_size={size}{flag_filter}{validated}{maybes}"
    limit = '' if limit == 0 else F"LIMIT {limit}"

    processed_reconstitutions = func.select_rows(
        db_name=db_name, table=F"RESULT_TBL {size} ORDER BY name,"
                               F"{' c_size, ' if selected_size is None else ' ' }cid {limit}",
        selected_col="cid, c_size, flag, name, validated")

    if processed_reconstitutions is None:
        return [], [], "---"

    processed_sizes = summarize_list(list({row['c_size'] for row in processed_reconstitutions}))

    # processed_sizes           : THE SUMMARY ALL PROCESSED SIZES
    # processed_reconstitutions : ALL RECONSTITUTION SIZES ALREADY PROCESSED
    return selected_size, processed_reconstitutions, processed_sizes


def get_row_index(db, size, cid, max_rows):

    cmd = F"""
    SELECT rowNumber, cid, name  
    FROM (SELECT row_number() OVER (ORDER BY name) AS rowNumber, cid, name FROM RESULT_TBL WHERE c_size={size})
    WHERE cid={cid}
    ; """

    row = func.select(db, cmd=cmd)
    if row is not None and len(row) > 0:
        row = row[0]
        page = (row['rowNumber'] // max_rows) + 1
        start_from = max_rows * page - max_rows
        table_idx = row['rowNumber'] - start_from
        print(F"page {page} start_from {start_from} table_idx {table_idx}")
        print({'rowNumber': row['rowNumber'], 'cid': row['cid'], 'name': row['name']})
        return {'page': page, 'start_from': start_from, 'table_idx': table_idx}
    return None


def offset_size(db_name, size, flag_filter, validated, start_from, nbr_rows):

    # IN HERE, THE CODE RETURNS THE RESULTS OF A PROCESSED SIZE REQUESTED BASED ON A NUMBER OF CONSTRAINTS THAT INCLUDE
    # - THE NAME OF THE CURRENT DB
    # - THE SIZE OF THE PROCESSED CLUSTER OF INTEREST
    # - THE SPECIFIC FLAG OF INTEREST (ALL - LIKELY-STAR, LIKELY, UNCERTAIN AND UNLIKE)
    #   SPECIFICALLY, LIKELY-STAR INCLUDES INSTANCES WITH NO WARNING FLAGS WHILE LIKE ARE
    #   ABOUT INSTANCES WITH AT LEAST ONE UNLIKELY FLAG
    # - WHETHER THE INTEREST LIES IN VALIDATED (YES, NO, ALL) INSTANCES OF THE PARTICULAR
    # - THE LIMIT WHICH SPECIFIES THE MAXIMUM NUMBER OF ROWS
    # - THE OFFSET WHICH SPECIFIES WHAT ROW TO START FORM IN THE DB. THIS PARTICULARLY HELPS FOR PAGINATION

    selected_size = size
    flag_filter = "All" if flag_filter is None else flag_filter
    validated = "ignore" if validated is None else validated
    validated = '' if validated == 'ignore' or len(validated) == 0 else F" AND validated='{validated}'"

    maybes = ' AND maybes>0' if flag_filter == "Likely" else (' AND maybes=0' if flag_filter == 'Likely-Star' else '')
    flag_filter = flag_filter.replace("-Star", '') if flag_filter.__contains__("-Star") else flag_filter

    flag_filter = '' if flag_filter == 'All' or len(flag_filter) == 0 else F" AND flag='{flag_filter}'"
    size = '' if selected_size is None else F"WHERE c_size={size}{flag_filter}{validated}{maybes}"

    # ORDER BY c_size, cid
    processed_reconstitutions = func.select_rows(
        db_name=db_name, table=F"RESULT_TBL {size} ORDER BY name,{' c_size, ' if selected_size is None else ' ' }"
                               F"cid LIMIT {nbr_rows} OFFSET {start_from} ",
        selected_col="cid, c_size, flag, name, validated")

    if processed_reconstitutions is None:
        return [], [], "---"

    processed_sizes = summarize_list(list({row['c_size'] for row in processed_reconstitutions}))

    # processed_sizes           : THE SUMMARY ALL PROCESSED SIZES
    # processed_reconstitutions : ALL RECONSTITUTION SIZES ALREADY PROCESSED

    # print(F"RESULT_TBL {size} ORDER BY name,{' c_size, ' if selected_size is None else ' ' }"
    #                            F"cid LIMIT {nbr_rows} OFFSET {start_from} ")
    # print(F"\nOFFSET\n"
    #       F"\t{'selected_size':{PADDING}} : {selected_size}\n"
    #       F"\t{'processed_reconstitutions':{PADDING}} : {len(processed_reconstitutions)}\n"
    #       F"\t{'processed_sizes':{PADDING}} : {processed_sizes}\n")

    return selected_size, processed_reconstitutions, processed_sizes


def processed_rec_sizes(db_name):
    processed_reconstitutions = func.select_rows(
        db_name=db_name, table=F"RESULT_TBL ORDER BY c_size", selected_col="c_size")
    processed_sizes = {row['c_size'] for row in processed_reconstitutions}
    return summarize_list(list(processed_sizes))


def batch_rec_table(db_name, size=None, limit=DEFAULT_LIMIT):

    selected_size = size
    size = '' if selected_size is None else F"WHERE c_size={selected_size}"

    processed_reconstitutions = func.select_rows(
        db_name=db_name, table=F"RESULT_TBL {size} ORDER BY name,{' c_size, ' if selected_size is None else ' ' }"
                               F"cid", selected_col="cid, c_size, name")

    if processed_reconstitutions is None:
        return "", [], [], "---"

    # TABLE DISPLAY
    table = Buffer()
    processed_sizes = set()
    l1, l2, count, width = 40, 130, 0, 90

    table.write(F"\n\n{'-' * l2}\n")
    table.write(F"|{'Index':^15}|{'Size':^8}|{'Cluster ID':^13}|{'Name':^{width}}|\n")
    table.write(F"{'-' * l2}\n")

    for row in processed_reconstitutions:
        count += 1
        processed_sizes.add(row['c_size'])
        if count <= limit:
            table.write(F"|{count:^15}|{row['c_size']:^8}|{row['cid']:^13}|{row['name']:^{width}}|\n")
    table.write(F"{'-' * l2}\n")

    return table.getvalue()


def available_full_size(db_name, size=None, limit=DEFAULT_LIMIT):

    # IN HERE THE CODE RETRIEVES ALL CLUSTER SISES AVAILABLE
    # WITHIN THE CURRENT DB AS WELL AS THE PROCESSED SISES

    selected_size = size
    size = '' if selected_size is None else F"WHERE c_size={selected_size}"

    processed_reconstitutions = func.select_rows(
        db_name=db_name, table=F"RESULT_TBL {size} ORDER BY name,{' c_size, ' if selected_size is None else ' ' }"
                               F"cid", selected_col="cid, c_size, name")

    if processed_reconstitutions is None:
        return "", [], [], "---"

    # TABLE DISPLAY
    table = Buffer()
    processed_sizes = set()
    l1, l2, count, width = 40, 130, 0, 90

    table.write(F"\n\n{'-' * l2}\n")
    table.write(F"|{'Index':^15}|{'Size':^8}|{'Cluster ID':^13}|{'Name':^{width}}|\n")
    table.write(F"{'-' * l2}\n")

    for row in processed_reconstitutions:
        count += 1
        processed_sizes.add(row['c_size'])
        if count <= limit:
            table.write(F"|{count:^15}|{row['c_size']:^8}|{row['cid']:^13}|{row['name']:^{width}}|\n")
    table.write(F"{'-' * l2}\n")

    processed_sizes = summarize_list(list(processed_sizes))

    # processed_sizes           : THE SUMMARY ALL PROCESSED SIZES
    # processed_reconstitutions :  ALL RECONSTITUTION SIZES ALREADY PROCESSED

    # print(F"AVAILABLE FULL SIZE\n"
    #       F"\t{'- processed_reconstitutions':{PADDING}} : {len(processed_reconstitutions)}\n"
    #       F"\t{'- processed_sizes':{PADDING}} : {processed_sizes}\n"
    #       F"\t{'- selected_size':{PADDING}} : {selected_size}", "\n")

    return table.getvalue(), selected_size, processed_reconstitutions, processed_sizes


def random_size(first=False):

    # RANDOMLY SELECT A SIZE TO DISPLAY FROM ALL AVAILABLE PROCESSED SIZES

    selected_db_name = selected_db()
    table, selected_size_all, processed_reconstitutions_all, processed_sizes_all = available_full_size(
        selected_db_name, size=None)

    rand = 0

    # random.seed(datetime.now().weekday())
    if first is True:
        return [int(sub) for size in processed_sizes_all.split(' ') for sub in size.split('-')][0]

    else:
        if processed_sizes_all is not None and len(processed_sizes_all) > 0 and processed_sizes_all != '---':
            rand = int(random.choice([sub for size in processed_sizes_all.split(' ') for sub in size.split('-')
                                      if size is not None and len(size) > 0]))
            print(F"RANDOM TABLE IS: {rand}  WITH SEED: {datetime.now().weekday()}\n")

    return rand


def nbr_of_pages(selected_db_name, rand_size, flag_filter, validated, max_rows):

    # COMPUTE THE NUMBER OF PAGES FOR PAGINATION BASED ON
    # - THE NAME OF THE CURRENT DB
    # - THE SIZE OF THE PROCESSED CLUSTER OF INTEREST
    # - THE SPECIFIC FLAG OF INTEREST (ALL - LIKELY-STAR, LIKELY, UNCERTAIN AND UNLIKE)
    # - WHETHER THE INTEREST LIES IN VALIDATED (YES, NO, ALL) INSTANCES OF THE PARTICULAR
    # - THE LIMIT WHICH SPECIFIES THE MAXIMUM NUMBER OF ROWS

    flag_filter = "All" if flag_filter is None else flag_filter
    validated = "ignore" if validated is None else validated

    maybes = ' AND maybes>0' if flag_filter == "Likely" else ('AND maybes=0' if flag_filter == 'Likely-Star' else '')
    flag_filter = flag_filter.replace("-Star", '') if flag_filter.__contains__("-Star") else flag_filter
    flag_filter = '' if flag_filter == 'All' or len(flag_filter) == 0 else F"AND flag='{flag_filter}'"
    validated = '' if validated == 'ignore' or len(validated) == 0 else F"AND validated='{validated}'"
    count_cmd = F"SELECT COUNT(DISTINCT cid) FROM RESULT_TBL WHERE c_size={rand_size} {flag_filter}  {validated} {maybes};"
    count_row = func.select(db_name=selected_db_name, cmd=count_cmd)
    fetched_items = [col for item in count_row for col in item][0] if count_row is not None else 0

    # print(F"NUMBER OF PAGES\n\n"
    #       F"\t- {'max_rows':{PADDING}} : {max_rows}\n"
    #       F"\t- {'rand_size':{PADDING}} : {rand_size}\n"
    #       F"\t- {'fetched_items':{PADDING}} : {fetched_items}\n"
    #       F"\t- {'command':{PADDING}} : {count_cmd}\n")

    return math.ceil(fetched_items / max_rows) if max_rows > 0 else 0


def responses(name):

    # THIS PROVIDES GENERIC OUTPUT INFO FOR THE UI

    info = refresh_ds()
    # print(info)

    if name == 'run':
        return {'run_active_color': GREEN, 'selected_db_name': selected_db(), 'db': get_db_fle_names()}

    elif name == 'C2RC':
        return {
            'db': info['db'], 'files': info['files'],
            'C2RC_active_color': GREEN, 'selected_db_name': selected_db()}

    elif name == 'dataset':
        return {
            'db': info['db'], 'files': info['files'],
            'datasets_active_color': GREEN, 'selected_db_name': selected_db()}

    elif name == 'preprocessing':
        return {'preprocesses_active_color': GREEN, 'selected_db_name': selected_db(),
                'db': get_db_fle_names(), 'process_count': check_process_count()}

    elif name == 'analysis':
        return {'analysis_active_color': GREEN, "db": get_db_fle_names(), 'selected_db_name': selected_db()}

    elif name == 'consistency':
        return {'consistency_active_color': GREEN, "db": get_db_fle_names(), 'selected_db_name': selected_db()}

    elif name == 'export':
        return {'export_active_color': GREEN, 'selected_db_name': selected_db(), 'db': get_db_fle_names()}


def current_stats(db_name, c_size):

    # COMPUTE THE STAT OF THE REQUESTED CLUSTER SIZE.
    # WITHIN THIS POOL, THE STAT CONSISTS ON PROVIDING THE NUMBER OF
    # - CLUSTERS FLAGGED AS LIKELY
    # - CLUSTERS FLAGGED AS LIKELY-STAR
    # - CLUSTERS FLAGGED AS UNCERTAIN
    # - CLUSTERS FLAGGED AS UNLIKELY
    # SPECIFICALLY, WHILE
    # - LIKELY-STAR INCLUDES INSTANCES WITH NO WARNING FLAGS
    # - LIKE ARE ABOUT INSTANCES WITH AT LEAST ONE WARNING FLAG

    all_flags = func.select(db_name=db_name, cmd=SELECT['size_flags'].format(c_size))
    all_flags = [[row['likely'], row['uncertain'], row['unlikely'], row['total'], row['likely_s']]
                 for row in all_flags][0] if all_flags is not None else [0, 0, 0, 0, 0]

    print(F"CURRENT FLAG STAT\n\n"
          F"\t+ {'all_flagged_likely':{PADDING}}\n"
          F"\t  - {'LIKELY':{PADDING-2}} : {formatNumber(all_flags[0], currency='')}\n"
          F"\t  - {'LIKELY-STAR':{PADDING-2}} : {formatNumber(all_flags[4], currency='')}\n"
          F"\t  - {'UNCERTAIN':{PADDING-2}} : {formatNumber(all_flags[1], currency='')}\n"
          F"\t  - {'UNLIKELY':{PADDING-2}} : {formatNumber(all_flags[2], currency='')}\n"
          F"\t  - {'TOTAL':{PADDING-2}} : {formatNumber(all_flags[3], currency='')}\n"
          F"\t- {'C. SIZE':{PADDING}} : {c_size}\n"
          F"\t- {'FLAGS':{PADDING}} : {all_flags[0]}\n"
          F"\t- {'FULL SIZE':{PADDING}} : {all_flags[3]}\n")

    if len(all_flags) == 0:
        return {
            'likely_s': 0,
            'likely': 0, 'uncertain': 0, 'unlikely': 0, 'total': 0, "full_size": 0,
            "percentage_likely": 0, "percentage_uncertain": 0, 'percentage_unlikely': 0}

    totals = all_flags[3]
    percentage_likely_s = round((all_flags[4] * 100) / totals, 2) if totals > 0 else 0
    percentage_likely = round((all_flags[0] * 100) / totals, 2) if totals > 0 else 0
    percentage_uncertain = round((all_flags[1] * 100) / totals, 2) if totals > 0 else 0
    percentage_unlikely = round((all_flags[2] * 100) / totals, 2) if totals > 0 else 0

    return {'likely': all_flags[0], 'likely_s': formatNumber(number=all_flags[4], currency=""),
            'uncertain': all_flags[1], 'unlikely': all_flags[2], "full_size": formatNumber(number=totals, currency=""),
            "percentage_likely": percentage_likely, "percentage_uncertain": percentage_uncertain,
            'percentage_unlikely': percentage_unlikely, "percentage_likely_s": percentage_likely_s}


def overall_stats(db_name, update_it=False):

    # COMPUTE THE OVERALL STAT OF ALL PROCESSED CLUSTER SIZES CURRENTLY AVAILABLE IN THE DB.
    # THIS CONSISTS ON PROVIDING STATS ON THE NUMBER OF
    # - CLUSTERS FLAGGED AS LIKELY
    # - CLUSTERS FLAGGED AS LIKELY-STAR
    # - CLUSTERS FLAGGED AS UNCERTAIN
    # - CLUSTERS FLAGGED AS UNLIKELY
    # SPECIFICALLY, WHILE
    # - LIKELY-STAR INCLUDES INSTANCES WITH NO WARNING FLAGS
    # - LIKE ARE ABOUT INSTANCES WITH AT LEAST ONE WARNING FLAG

    # CHECK BEFORE COMPUTING
    check = func.select(db_name=db_name, cmd=SELECT['overall_stats'].format(db_name=db_name))
    check = check[0]['stats'] if check is not None else None
    check = serialise(check) if check is not None else None

    if update_it is True:

        all_flags = func.select(db_name=db_name, cmd=SELECT['all_flags'])
        all_flags = [[row['likely'], row['uncertain'], row['unlikely'], row['total'], row['likely_s']]
                     for row in all_flags][0] if all_flags is not None else [0, 0, 0, 0, 0]

        if len(all_flags) == 0:
            return {
                'likely_s': 0,
                'likely': 0, 'uncertain': 0, 'unlikely': 0, 'total': 0, "full_size": 0,
                "percentage_likely": 0, "percentage_uncertain": 0, 'percentage_unlikely': 0}

        totals = all_flags[3]
        percentage_likely_s = round((all_flags[4] * 100) / totals, 2) if totals > 0 else 0
        percentage_likely = round((all_flags[0] * 100) / totals, 2) if totals > 0 else 0
        percentage_uncertain = round((all_flags[1] * 100) / totals, 2) if totals > 0 else 0
        percentage_unlikely = round((all_flags[2] * 100) / totals, 2) if totals > 0 else 0

        print(F"OVERALL FLAG STATS\n\n"
              F"\t- {'all_flagged_likely':{PADDING}}\n"
              F"\t  - {'LIKELY':{PADDING-2}} : {formatNumber(all_flags[0], currency='')}\n"
              F"\t  - {'LIKELY-STAR':{PADDING-2}} : {formatNumber(all_flags[4], currency='')}\n"
              F"\t  - {'UNCERTAIN':{PADDING-2}} : {formatNumber(all_flags[1], currency='')}\n"
              F"\t  - {'UNLIKELY':{PADDING-2}} : {formatNumber(all_flags[2], currency='')}\n"
              F"\t  - {'TOTAL':{PADDING-2}} : {formatNumber(all_flags[3], currency='')}\n"
              F"\t- {'FLAGS':{PADDING}} : {all_flags[0]}\n"
              F"\t- {'FULL SIZE':{PADDING}} : {totals}\n")

        result = {'likely': all_flags[0], 'likely_s': all_flags[4], 'uncertain': all_flags[1],
                  'unlikely': all_flags[2], "full_size": formatNumber(number=totals, currency=""),
                  "percentage_likely": percentage_likely, "percentage_uncertain": percentage_uncertain,
                  'percentage_unlikely': percentage_unlikely, "percentage_likely_s": percentage_likely_s}

        func.update(db_name=db_name, cmd=UPDATE['overall_stats'].format(stats=str(result), db_name=db_name))

        return result

    return check


def convert_list_summary2list(list_summary):

    # print(list_summary)
    # RETURN A LIST OF ALL SIZES PROCESSED

    new_sizes = []
    sizes = [size for size in list_summary.split(' ')]

    for size in sizes:
        if len(size.strip()) > 0 and size.__contains__("-") is False:
            new_sizes.append(int(size))
        elif size.__contains__("-") is True:
            for i in range(int(size.split('-')[0]), int(size.split('-')[1])+1):
                new_sizes.append(i)
    # print(F"{'Size':{PADDING}} : {new_sizes}")
    return new_sizes


def get_state(db_name):

    #     cluster_size INTEGER DEFAULT 0 NOT NULL,
    #     current_page INTEGER DEFAULT 0 NOT NULL,
    #     table_row INTEGER DEFAULT 1 NOT NULL,
    #     max_pages INTEGER DEFAULT 0 NOT NULL
    #     filter TEXT DEFAULT 'All' NOT NULL,
    #     validated TEXT DEFAULT 'ignore' NOT NULL,

    state = func.select_last_row(db_name=db_name, table="STATE_TBL", column='cluster_size')

    if state is None:
        print(F"{'UPDATING THE STATE TABLE'}")
        func.insert_row(db_name=db_name, cmd=INSERT['state'],
                        values=[0, 0, 0, 1, par.MAX_TABLE_ROWS, 'All', 'ignore', 'off'])
        state = func.select_last_row(db_name=db_name, table="STATE_TBL", column='cluster_size')

    if state is not None:
        state = {"cluster_size": state["cluster_size"], "current_page": state["current_page"],
                 "table_row": state["table_row"], "table_limit": state["table_limit"], "max_pages": state["max_pages"],
                 "filter": state["filter"], "validated": state["validated"], 'hide_table': state["hide_table"]}

        # print(F"GET STATE")
        # for key, value in state.items():
        #     print(F"\t- {key:{PADDING}} : {value}")
        # print(F"")

        return state

    return {"cluster_size": 0, "current_page": 0, "table_row": 0, "table_limit": 0,
            "max_pages": par.MAX_TABLE_ROWS, "filter": 'All', "validated": 'ignore', 'hide_table': 'on'}


def update_state(db_name, state):

    # STATE UPDATE : cluster_size, max_pages, current_page, table_row, filter, validated

    if len(state) == 8:
        values = F"{state['cluster_size']}, {state['max_pages']},  {state['current_page']}, {state['table_row']}, " \
                 F"{state['table_limit']}, '{state['filter']}', '{state['validated']}', '{state['hide_table']}'"

        func.update(db_name=db_name, cmd=UPDATE['state'].format(values=values))

    elif len(state) == 1:
        values = F"'{state['hide_table']}'"
        func.update(db_name=db_name, cmd=UPDATE['hide-table'].format(values=values))

    else:
        values = F"{state['cluster_size']}, {state['max_pages']},  {state['current_page']}, {state['table_row']}, " \
                 F"{state['table_limit']}, '{state['filter']}', '{state['validated']}'"

        func.update(db_name=db_name, cmd=UPDATE['state_2'].format(values=values))


# ===============================================================================================
#                        EXTENDED FAMILY VALIDATION CONSISTENCY HELPERS
# ===============================================================================================


# RETURN A CLUSTER BASED ON A PERSONS ID
def find_cluster_on_pid(db_name, pers_id):

    # value=p-1100241 value=p-1446513 value=p-1599176
    result = func.select_row(db_name=db_name, table='PERSON_ID2CLUSTER_TBL', column='id', value=pers_id.replace('p-', ''))
    if result is not None:
        return serialise(result[1])
    return None


def role_mapping(role):

    if role in ['--nHasFather->', '--bHasFather->', '--gHasFather->']:
        return 'Father'

    if role in ['--nHasMother->', '--bHasMother->', '--gHasMother->']:
        return 'Mother'

    if role in ['<-hasMother---', '<-hasFather---', '<-gHasFather--', '<-bHasFather--',
                '<-gHasMother--', '<-bHasMother--', '<--married---- ']:
        return 'Child'

    elif role in ['---married--->', '<--married----']:
        return 'Spouse'

    else:
        return role


# GATHER DATA
def get_detail(db_name, cluster_id):

    size = 0
    names = set()
    roles = defaultdict(set)
    roles_groundless = defaultdict(set)
    # Fetch data about the cluster
    cmd = "SELECT id, serialised FROM CLUSTERS_TBL WHERE id={cid} ;"
    validated_cmd = "SELECT validated FROM RESULT_TBL WHERE cid={cid} ;"

    # 1.1 GET DATA ABOUT THE SUBMITTED RECONSTITUTION AND CHECK WHETHER IT HAS BEEN VALIDATED
    #     THE SUBMITTED ID IS A CLUSTER
    if str(cluster_id).__contains__('p-') is False:
        detail = func.select(db_name=db_name, cmd=cmd.format(cid=cluster_id))
        validated = func.select(db_name=db_name, cmd=validated_cmd.format(cid=cluster_id))

    # 1.2 GET DATA ABOUT THE SUBMITTED RECONSTITUTION AND CHECK WHETHER IT HAS BEEN VALIDATED
    #     THE SUBMITTED ID IS NOT A CLUSTER
    else:
        detail = None
        validated = None

    # 1.2 GET DATA ABOUT THE SUBMITTED RECONSTITUTION AND CHECK WHETHER IT HAS BEEN VALIDATED
    #     FINALISE THE VALIDATION STATUS
    validated = validated[0]['validated'] if validated is not None and len(validated) > 0 else None

    # 1.3 THE RECONSTITUTED HAS BEEN CLUSTERED SO GATHER DATA ON EACH FAMILY MEMBER:
    #     - THE CLUSTER ID OF THE FAMILY MEMBER
    #     - NAME VARIANTS OF THE FAMILY MEMBER
    #     - THE ROLE OF THE FAMILY MEMBER
    if detail is not None:
        deserialised = serialise(detail[0]['serialised'])
        # Get the custer size
        size = deserialised['cor_count']
        # Get the IDs used for each observation
        persons = deserialised['ids']
        # Collect data on each observation
        for pid in persons:
            p_id = F"p-{pid}"
            prs = func.select_row(db_name=db_name, table='PERSON_TBL', column='id', value=p_id)
            if prs is not None:
                names.add(capwords(F"{prs[f_name]} {prs[g_name]}"))
                # ASSOCIATED FAMILY CLUSTERS
                prs_associations = func.select_row(db_name=db_name, table='ASSOCIATION_DICT_TBL', column='id', value=p_id)
                for [predicate, pid_2] in serialise(prs_associations[1]):
                    cid = find_cluster_on_pid(db_name=db_name, pers_id=pid_2)
                    if cid is not None:
                        roles[cid].add(role_mapping(predicate))
                    elif pid_2 is not None:
                        roles_groundless[pid_2].add(role_mapping(predicate))

    # IT RETURNS THE NAME VARIANTS, THE SIZE AND THE VALIDATION STATUS OF THE RECONSTITUTED
    # FOR EACH CLUSTERED MEMBER, IT RETURNS THE CLUSTER ID AND THE ROLE OF THE FAMILY MEMBER
    # FOR EACH NON-CLUSTERED MEMBER, IT RETURNS THE PERSON'S ID AND THE ROLE OF THE FAMILY MEMBER
    return names, roles, roles_groundless, size, validated


# GIVEN A RECONSTITUTED, HE OR SHE CAN BE SPLIT
# OR A MEMBER OF THE EXTENDED FAMILY CAN BE SPLIT
def family_thread(db_name, processed):

    family = defaultdict(list)

    # 1. DETAIL ABOUT THE CURRENT RECONSTITUTION
    name_variants, extended_family_cid, roles_groundless, size, validated = get_detail(db_name, processed)
    family[processed] = ['RECONSTITUTED', " | ".join(name for name in name_variants), len(name_variants), size, validated]

    # 2.1 DETAIL ABOUT THE FAMILY MEMBERS OF THE RECONSTITUTED
    #     ONLY, THESE FAMILY MEMBERS HAVE BEEN CLUSTERED
    for family_cluster, role_set in extended_family_cid.items():
        info = get_detail(db_name, family_cluster)
        n_variants = len(info[0]) if info is not None else 0
        role = " | ".join(role.upper() for role in role_set) if role_set is not None else ""
        name = " -- ".join(capwords(str(name)) for name in info[0]) if info is not None else ""
        family[family_cluster] = [role, name, n_variants, info[3], info[4]]

    # 2.2 DETAIL ABOUT THE FAMILY MEMBERS OF THE RECONSTITUTED
    #     ONLY, THESE FAMILY MEMBERS HAVE NOT BEEN CLUSTERED
    for family_cluster, role_set in roles_groundless.items():
        prs = func.select_row(db_name=db_name, table='PERSON_TBL', column='id', value=family_cluster)
        info = get_detail(db_name, family_cluster)
        name = capwords(F"{prs[f_name]} {prs[g_name]}")
        role = " | ".join(role.upper() for role in role_set)
        family[family_cluster] = [role, name, 1, 1, info[4]]

    return family


# APPLICABLE TO THE VALIDATED RECONSTITUTION
def family_thread_2(db_name, processed, validated_list, valid_names):

    family = defaultdict(list)
    name_variants, extended_family_cid, roles_groundless, size, validated = get_detail(db_name, processed)

    # Use the list of valid names instead of the list of all names that came from the original reconstitution
    family[processed] = ['RECONSTITUTED', " | ".join(name for name in valid_names), len(name_variants), size, validated]

    # GROUNDED
    for family_cluster, role_set in extended_family_cid.items():

        if str(family_cluster) in validated_list:
            info = get_detail(db_name, family_cluster)
            n_variants = len(info[0]) if info is not None else 0
            role = " | ".join(role.upper() for role in role_set) if role_set is not None else ""
            name = " -- ".join(capwords(str(name)) for name in info[0]) if info is not None else ""
            family[family_cluster] = [role, name, n_variants, info[3], info[4]]

    # GROUNDLESS
    for family_cluster, role_set in roles_groundless.items():
        if str(family_cluster) in validated_list:
            prs = func.select_row(db_name=db_name, table='PERSON_TBL', column='id', value=family_cluster)
            info = get_detail(db_name, family_cluster)
            name = capwords(F"{prs[f_name]} {prs[g_name]}")
            role = " | ".join(role.upper() for role in role_set)
            family[family_cluster] = [role, name, 1, 1, info[4]]

    return family


def validated_thread(cluster_id, validated_table, db_name):

    # validated_table is a dictionary
    sub_family = defaultdict(set)
    # As the main reconstitution get split, this variable helps ensuring
    # that each group is assigned the correct name variants list
    valid_names = defaultdict(set)
    validated_family = dict()
    # EXTRACT THE CLUSTER ID
    cid_pattern = F"i-(.*) of size ([\\d*]*)"

    if validated_table is not None:

        # GENERATE THE SUBGROUPS
        for subgroup, p_observations in validated_table.items():
            # FOR EACH SUBGROUP, COLLECT THE RESPECTIVE CLUSTER IDS
            for observation in p_observations:
                cid = search(cid_pattern, observation['associated_cluster'])
                sub_family[subgroup].add(cid[1]) if cid else sub_family[subgroup].add(observation['associationPersonID'])
                valid_names[subgroup].add(observation['p_name'])

        for group, c_ids in sub_family.items():
            validated_family[group] = family_thread_2(
                db_name=db_name, processed=cluster_id, validated_list=c_ids, valid_names=valid_names[group])

    return validated_family


# ===============================================================================================
#                                           DATASETS
# ===============================================================================================


# # print(F"\n{' Index html ':.^100}\n")
# @app.route('/download')
# def generate_large_csv():
#     def generate():
#         for row in range(10000000000):
#             yield ','.join(row) + '\n'
#     return Response(generate(), mimetype='text/csv')


@app.route('/')
def index():
    week_date(message="Index html ")
    return render_template('index.html', response=responses('C2RC'), input_files=['files'], )


@app.route('/data', methods=['GET', 'POST'])
def datasets():
    week_date(message="ABOUT DATABASES")
    return render_template('data.html', response=responses('dataset'))


@app.route('/data/dropdown', methods=['GET', 'POST'])
def dropdown():

    # SELECT A DATABASE OF INTEREST
    c = Coloring()
    week_date(message="ABOUT DATABASES DROPDOWN")

    obj = request.args.get('name')

    tbl_size = func.get_rows(db_name='shared', table='SELECTED_DB_TBL')
    tbl_size = len(tbl_size) if tbl_size is not None else 0

    # INSERT THE FIRST ROW IF THE TABLE IS EMPTY
    if tbl_size == 0:
        func.insert_row(db_name='shared', cmd=INSERT['db_name'], values=[obj])

    # AS IT IS NOT EMPTY, UPDATE THE FIRST ROW
    elif tbl_size > 0:
        selected = func.select_last_row(db_name='shared', table='SELECTED_DB_TBL', column='id')
        if selected is not None and len(selected) > 0:
            selected = selected['db_name']
            print(F"    Update selected DB from {c.colored(7, selected)} to {c.colored(7, obj)}")
            func.update(db_name='shared', cmd=UPDATE['db_name'].format(new_db_name=obj, old_db_name=selected))

    # MAKE SURE IT IS UPDATED
    selected = func.select_last_row(db_name='shared', table='SELECTED_DB_TBL', column='id')
    selected = selected['db_name'] if selected is not None and len(selected) > 0 else None
    print(F"    Newly selected : {selected if len(selected)>0 else 'N/A'}")

    return render_template('data.html', response=responses('dataset'))


@app.route('/uploader', methods=['GET', 'POST'])
def uploader():

    week_date(message="UPLOADING THE DATABASES")

    folder = Path(DB_ROUTE_FOLDER)
    cil_registries_ds = request.files['file1']
    reconstituted_ds = request.files['file2']
    db_name = request.form.get('db_name')

    print(cil_registries_ds.filename)
    db_name = db_name.strip() if db_name is not None else None

    reg_ok = True if cil_registries_ds.filename is not None and len(cil_registries_ds.filename) > 0 else False
    rec_ok = True if reconstituted_ds.filename is not None and len(reconstituted_ds.filename) > 0 else False
    db_ok = True if db_name is not None and len(db_name) > 0 else False

    cmd = "INSERT INTO DATABASE_TBL (name, civil_registries_path, reconstituted_path) VALUES (?, ?, ?)"

    def upload(file):
        path = None
        if file:

            print("\nWe will upload: {}".format(file.filename))
            print("Path: {}".format(join(DATA_INPUT_FOLDER, file.filename)))
            path = join(DATA_INPUT_FOLDER, file.filename)
            file.save(path)
            print("File uploaded")

        return path

    curr_triple_files = [f for f in listdir(folder) if str(f).split('.')[0].startswith(db_name)]
    name_exists = F"{db_name}.db" in curr_triple_files and db_ok
    good = reg_ok is True and rec_ok is True and db_ok is True and name_exists is False
    exist = F"{'❌' if db_ok is False else ('✔' if name_exists is False else '❌'):<4}"

    print(F"DB file-Name             : {db_name} {exist}")
    print(F"Civ Reg file-Name        : {cil_registries_ds.filename}")
    print(F"Reconstituted file-Name  : {reconstituted_ds.filename}\n"
          F"Proceed                  : {'✔' if good is True else ' ❌'}")

    if good is True:
        pass
        # UPLOADING THE DATABASE
        cil_registries_path = upload(cil_registries_ds)
        reconstituted_path = upload(reconstituted_ds)

        # CREATE THE DATABASE
        initiate(db_name)
        func.insert_row(db_name, cmd, values=[db_name, cil_registries_path, reconstituted_path])
        update_selected_db(db_name)

    return render_template('data.html', response=responses('dataset'))


@app.route('/delete_db', methods=['GET', 'POST'])
def delete_db():

    c = Coloring()
    week_date(message="DELETE A DATABASE")
    old_db_name = request.form.get('old-db-name')
    new_db_name = request.form.get('new-db-name')
    task = request.form.get('btn-delete-update')
    input_one, input_two = request.form.get('hidden_input1'), request.form.get('hidden_input2')

    db_name = input_one if input_one is not None else input_two
    name = F"{db_name}.db"

    triple_folder = Path(TRIPLE_FOLDER)
    true_update = old_db_name is not None and new_db_name is not None

    if task == 'delete':

        db_path = join(par.DB_FOLDER, name)
        curr_triple_files = [f for f in listdir(triple_folder) if str(f).startswith(db_name)]
        print(F"\n\tDeleting {name}\n"
              F"\tPath : {db_path}")

        if exists(db_path) is True:

            # DROP TABLE addresses;
            if selected_db() == db_name:
                func.delete_row('shared', cmd=DELETE['db'].format(db_name='db_name'))

            remove(db_path)
            print(F"\t {name} has been Deleted\n")

            # REMOVE THE TRIPLE FILES
            for i in range(len(curr_triple_files)):
                print(F"\n\tremoving {curr_triple_files[i]}\n")
                remove(triple_folder / str(curr_triple_files[i]))

        else:
            print(F"\tSuch a path does not exist\n")

    elif task == 'update' and true_update is True:

        curr_triple_files = [f for f in listdir(Path(triple_folder)) if str(f).split('.')[0].startswith(old_db_name)]
        curr_dbs = [f for f in listdir(Path(DB_ROUTE_FOLDER)) if str(f).startswith(new_db_name)]
        name_exists = F"{new_db_name}.db" in curr_dbs

        print(curr_triple_files)

        old_db_name = old_db_name.strip() if old_db_name is not None else None
        new_db_name = new_db_name.strip() if new_db_name is not None else None

        print(F"\n\tUpdating DB name from [{old_db_name if old_db_name is not None else '---'}] "
              F"to [{new_db_name if new_db_name is not None else '---'}]\n")

        if new_db_name is not None and name_exists is False and len(new_db_name) > 3:

            # CHECK WHETHER THE OLD DB NAME EXIST
            check = F"SELECT name FROM DATABASE_TBL WHERE name='{old_db_name}' ;"
            fetch = func.select(db_name=old_db_name, cmd=check)
            fetch = [row['name'] for row in fetch] if fetch is not None else None

            if fetch is not None and len(fetch) > 0:

                info = func.get_database(old_db_name)
                print(F"\t{'DB NAME':{PADDING}} : {info[0]['name']}\n"
                      F"\t{'REGISTRIES':{PADDING}} : {info[0]['civil_registries_path']}\n"
                      F"\t{'RECONSTITUTIONS':{PADDING}} : {info[0]['reconstituted_path']}\n")

                # GET THE FILE PATH OF THE OLD DB AND UPDATE THE OLD NAME WITH THE NEW ONE
                files = [Path(DB_ROUTE_FOLDER) / F"{file}.db" for file in get_db_fle_names() if file == old_db_name]
                rename(files[0], str(Path(DB_ROUTE_FOLDER) / F"{new_db_name}.db"))
                func.update(db_name=new_db_name, cmd=UPDATE['local_db_name'].format(
                    table='DATABASE_TBL', new_db_name=new_db_name, old_db_name=old_db_name))

                # UPDATE SELECTED DB
                print(F"    Update selected DB from {c.colored(7, old_db_name)} to {c.colored(7, new_db_name)}\n")
                func.update(db_name='shared', cmd=UPDATE['db_name'].format(
                    new_db_name=new_db_name, old_db_name=old_db_name))

                # UPDATE THE TRIPLE FILES
                new_file_names = [str(file).replace(old_db_name, new_db_name) for file in curr_triple_files]
                print(F"UPDATING TRIPLE FILE NAME \n"
                      F"\t - FROM : {curr_triple_files}\n"
                      F"\t - TO   : {new_file_names}\n")
                for i in range(len(curr_triple_files)):
                    rename(triple_folder/str(curr_triple_files[i]), triple_folder/new_file_names[i])

        elif new_db_name is not None and name_exists is True:
            print(F"\t{c.colored(7, 'PROBLEM: We can not proceed with the update as a database already exists under the same name.')}\n")

        else:
            print("NO")

        task = ""

    return render_template('data.html', response=responses('dataset'), db_name=db_name, task=task)


# ===============================================================================================
#                                       DATA PREPROCESSING
# ===============================================================================================


# @app.route('/data/preprocessing')
def streamed_response():
    from flask import stream_with_context, Response

    def gen():

        for i in range(1000):
            yield i
            # sleep(1)

    def stream_template(template_name, **context):
        app.update_template_context(context)
        t = app.jinja_env.get_template(template_name)
        rv = t.stream(context)
        # rv.enable_buffering(5)
        rv.disable_buffering()
        return rv

    # return render_template('test.html', count=1)
    yep = gen()
    return Response(stream_with_context(stream_template('test.html', rows=yep)))

    # def generate():
    #     return Response(stream_template('test.html', count=1))
    #     yield 'Hello '
    #     yield request.args['name']
    #     yield '!'
    # return Response(stream_with_context(generate()))


@app.route('/data/preprocessing')
def preprocesses():

    week_date(message="ABOUT PROCESSES")
    # Return the description of path process and the file path
    selected_db_name = selected_db()
    ref_row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Co-referents')
    civ_row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Persons')
    f_1_row = func.select_row(selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Extended-Family1')
    f_2_row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Extended-Family2')

    ref_row = {'description': ''} if ref_row is None else ref_row
    civ_row = {'description': ''} if civ_row is None else civ_row
    f_1_row = {'description': ''} if f_1_row is None else f_1_row
    f_2_row = {'description': ''} if f_2_row is None else f_2_row

    description, process_count = process_message()

    response = {'preprocesses_active_color': GREEN, 'selected_db_name': selected_db_name, 'db': get_db_fle_names(),
                'process_count': process_count}

    return render_template('preprocessing.html', response=response, description=description,
                           reconstituted=ref_row['description'], civil_registries=civ_row['description'],
                           family_1=f_1_row['description'], family_2=f_2_row['description'])


@app.route('/data/preprocessing/process_all')
def process_all():
    week_date(message="PROCESS IT ALL process started on ")
    selected_db_name = selected_db()

    # ================================================================================
    # 1. RECONSTITUTED
    # ================================================================================

    # CHECK THE DB IF THE RECONSTITUTED DATA HAS ALREADY BEEN PROCESSED
    row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Co-referents')

    # Create the dictionary of co-referents
    description = F"""
        {LINE}
        ---{'DATA STRUCTURE':^{PREPROCESS_LINE}}---
        {LINE}
        The downloaded RDF database about RECONSTITUTED individuals is serialised as a 
        dictionary where the ID of a RECONSTITUTED serves as the key for accessing all 
        data about the RECONSTITUTED. This data includes:

            - The number of births.
            - The list of birth years.
            - The size of the reconstituted cluster.
            - A list of IDs representing person observations.

        {LINE}
        ---{'EXAMPLE':^{PREPROCESS_LINE}}---
        {LINE}
        key   : 0
        value : {{ 'cor_count': 7, 'birth_count': 1, 'years': ['1885'],
                   'ids': ['1145835', '1376264', '2420114', 
                   '2782525', '2914718', '299993', '619002'] 
                }}"""

    if row is not None and selected_db_name is not None:
        pass

    elif row is None and selected_db_name is None:
        pass

    else:
        # EXECUTE THE SERIALISATION
        print("EXTRACTING RECONSTITUTED\n")
        is_finished = extract_reconstituted(selected_db_name)
        print(F"\n\t- Extraction {'successful' if is_finished else 'unsuccessful'}")

        # RUNNING THE STATS
        print("\nRUNNING STATS OF RECONSTITUTED")
        statistics = stats_of_reconstructed(selected_db_name)
        print(F"\t- Completed stats {'successfully' if len(statistics) > 0 else 'unsuccessfully'}")

        output = F"{statistics}{description}"

        # Insert the dictionary of co-referents into the DB
        if statistics is not None and len(statistics) > 0:
            func.insert_row(selected_db_name, INSERT['output'], values=['Co-referents', output])

    # ================================================================================
    # 2. CIVIL REGISTRIES
    # ================================================================================

    # check the DB
    row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Persons')
    if row is not None:
        pass

    else:
        # Create the dictionary of person occurrences data
        results = extract_registries(selected_db_name)
        description = F"""
            {LINE}
            ---{"STATISTICS":^{PREPROCESS_LINE}}---
            {LINE}
            Persons      : {func.formatNumber(results['persons'], currency="") if results['persons'] >= 0 else 'N/A'} 
            Certificates : {func.formatNumber(results['full-events'], currency="") if results['full-events'] >= 0 else 'N/A'}
    
            {LINE}
            ---{"DATA STRUCTURE":^{PREPROCESS_LINE}}---
            {LINE}
            THE RDF file containing CIVIL REGISTRY data is converted to a table adding the
            following data to each certificate (birth, marriage, death).
    
                - person ID
                - family name
                - given name
                - age
                - gender
                - data-type
                - occupationTitle
            """

        # INSERT THE RESULT DESCRIPTION OF THE PERSON INTO THE OUTPUT-FILE-TABLE
        if results is not None and results['persons'] > 0:
            func.insert_row(selected_db_name, INSERT['output'], values=['Persons', description])

    # ================================================================================
    # 3. FAMILY 1
    # ================================================================================

    prs = func.select_row(selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Persons')
    if prs is None:
        pass

    # check the DB
    fm1_row = func.select_row(selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Extended-Family1')
    if fm1_row is not None:
        pass

    else:
        # Create the dictionary of person occurrences data
        triples = associations_ttl(selected_db_name)
        # triples = 4860373
        description = F"""
        {LINE}
        ---{"DATA STRUCTURE":^{PREPROCESS_LINE}}---
        {LINE}
    
        The generated turtle file format contains {func.formatNumber(triples, currency="")} triples.
        It is generated to represent the EXTENDED FAMILY of a reconstituted individual 
        recorded in the civil registry dataset. The family ties are based on the events 
        recorded in civil certificates with the persons who participated.
    
        {LINE}
        ---{"EXAMPLE":^{PREPROCESS_LINE}}---
        {LINE}
    
        ### RELATIVES PRESENT IN THE DEATH OF PERSON:121111
    
        person:p-4037410
            civ:dHasMother  person:p-4037413 ;
            civ:dHasFather  person:p-4037412 ;
            civ:dHasPartner person:p-4037411 ;
            civ:inEvent     ev:e-1121144 .
        """

        # Insert file data into the DB
        if triples > 0:
            func.insert_row(selected_db_name, INSERT['output'], values=['Extended-Family1', description])

    # ================================================================================
    # 4. FAMILY 2
    # ================================================================================

    description = F"""
        {LINE}
        ---{"DATA STRUCTURE":^{PREPROCESS_LINE}}---
        {LINE}

        The RDF file containing the EXTENDED FAMILY of a reconstituted individual is 
        transformed to a dictionary using a person's ID as the key for assessing the 
        various relations in an extended family. 

        {LINE}
        ---{"EXAMPLE":^{PREPROCESS_LINE}}---
        {LINE}

        For example, person [p-2272899] plays the role of 
            --> [--nHasMother->] with [p-717147] while he also plays the role of 
            --> [--nHasFather->] with [p-717146].
        """
    prs = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Persons')
    fam1_row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name",
                               value='Extended-Family1')

    if prs is None or fam1_row is None:
        process_check, process_count = process_message()
        response = responses('preprocessing')
        response['process_count'] = process_count
        return render_template(
            'preprocessing.html', response=responses('preprocessing'), family_2='',
            description="[CIVIL REGISTRIES DATASET] AND [EXTENDED-FAMILY-1] SHOULD BE PROCESSED BEFOREHAND.")

    # check the DB
    fam2_row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name",
                               value='Extended-Family2')
    ref_row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Co-referents')
    civ_row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Persons')
    ref_row = {'description': ''} if ref_row is None else ref_row['description']
    civ_row = {'description': ''} if civ_row is None else civ_row['description']
    fam1_row = {'description': ''} if fam1_row is None else fam1_row['description']

    if fam2_row is not None and fam2_row != 'None':
        process_check, process_count = process_message()
        response = responses('preprocessing')
        response['process_count'] = process_count
        print("\n\tRetrieving the description of the processed extended family 2 data file.\n")
        return render_template(
            'preprocessing.html', response=responses('preprocessing'), description=process_check,
            reconstituted=ref_row, civil_registries=civ_row, family_1=fam1_row, family_2=fam2_row['description'])

    # Create the dictionary of person occurrences data
    association_resource(selected_db_name)

    # Insert file data into the DB
    func.insert_row(db_name=selected_db_name, cmd=INSERT['output'], values=['Extended-Family2', description])

    process_check, process_count = process_message()
    response = responses('preprocessing')
    response['process_count'] = process_count

    # Return the description of path process and the file path
    return render_template('preprocessing.html', response=responses('preprocessing'),
                           reconstituted=ref_row, civil_registries=civ_row, family_1=fam1_row, family_2=description)


@app.route('/data/preprocessing/reconstituted')
def reconstituted():

    week_date(message="RECONSTITUTED process started on ")
    selected_db_name = selected_db()

    # CHECK THE DB IF THE RECONSTITUTED DATA HAS ALREADY BEEN PROCESSED
    row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Co-referents')
    process_check, process_count = process_message()
    response = {'preprocesses_active_color': GREEN, 'selected_db_name': selected_db(),
                'db': get_db_fle_names(), 'process_count': check_process_count()}

    # Create the dictionary of co-referents
    description = F"""
    {LINE}
    ---{'DATA STRUCTURE':^{PREPROCESS_LINE}}---
    {LINE}
    The downloaded RDF database about RECONSTITUTED individuals is serialised as a 
    dictionary where the ID of a RECONSTITUTED serves as the key for accessing all 
    data about the RECONSTITUTED. This data includes:

        - The number of births.
        - The list of birth years.
        - The size of the reconstituted cluster.
        - A list of IDs representing person observations.

    {LINE}
    ---{'EXAMPLE':^{PREPROCESS_LINE}}---
    {LINE}
    key   : 0
    value : {{ 'cor_count': 7, 'birth_count': 1, 'years': ['1885'],
               'ids': ['1145835', '1376264', '2420114', 
               '2782525', '2914718', '299993', '619002'] 
            }}"""

    if row is not None and selected_db_name is not None:
        print("\n\tRetrieving the description of the processed reconstitutions data file.\n")
        return render_template('preprocessing.html', response=responses('preprocessing'),
                               description=process_check, reconstituted=row['description'])

    elif row is None and selected_db_name is None:
        return render_template(
            'preprocessing.html', response=response,
            reconstituted='\n Something went wrong. \n Please, check whether you have selected a dataset')

    # EXECUTE THE SERIALISATION
    print("EXTRACTING RECONSTITUTED\n")
    is_finished = extract_reconstituted(selected_db_name)
    print(F"\n\t- Extraction {'successful' if is_finished else 'unsuccessful'}")

    # RUNNING THE STATS
    print("\nRUNNING STATS OF RECONSTITUTED")
    statistics = stats_of_reconstructed(selected_db_name)
    print(F"\t- Completed stats {'successfully' if len(statistics) > 0 else 'unsuccessfully'}")

    output = F"{statistics}{description}"

    # Insert the dictionary of co-referents into the DB
    if statistics is not None and len(statistics) > 0:
        func.insert_row(selected_db_name, INSERT['output'], values=['Co-referents', output])

    # update
    process_check, process_count = process_message()

    # Return the description of path process and the file path
    return render_template(
        'preprocessing.html',  process_count=process_count, process_check=process_check,
        response=responses('preprocessing'), reconstituted=output)


@app.route('/data/preprocessing/civil_registries')
def civil_registries():

    week_date(message="Civil Registries process started on ")
    selected_db_name = selected_db()
    process_check, process_count = process_message()

    # check the DB
    ref_row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Co-referents')
    row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Persons')
    ref_row = {'description': ''} if ref_row is None else ref_row

    if row is not None:
        print("\n\tRetrieving the description of the processed civil registries data file.\n")
        return render_template('preprocessing.html', response=responses('preprocessing'),
                               description=process_check, reconstituted=ref_row['description'],
                               civil_registries=row['description'])

    # Create the dictionary of person occurrences data
    # {'persons': t_persons, 'events': t_events, "full-events": t_f_events}
    results = extract_registries(selected_db_name)

    description = F"""
    {LINE}
    ---{"STATISTICS":^{PREPROCESS_LINE}}---
    {LINE}
    Persons      : {func.formatNumber(results['persons'], currency="") if results['persons'] >= 0 else 'N/A'} 
    Certificates : {func.formatNumber(results['full-events'], currency="") if results['full-events'] >= 0 else 'N/A'}

    {LINE}
    ---{"DATA STRUCTURE":^{PREPROCESS_LINE}}---
    {LINE}
    THE RDF file containing CIVIL REGISTRY data is converted to a table adding the
    following data to each certificate (birth, marriage, death).
    
        - person ID
        - family name
        - given name
        - age
        - gender
        - data-type
        - occupationTitle
    """

    # INSERT THE RESULT DESCRIPTION OF THE PERSON INTO THE OUTPUT-FILE-TABLE
    if results is not None and results['persons'] > 0:
        func.insert_row(selected_db_name, INSERT['output'], values=['Persons', description])

    process_check, process_count = process_message()
    response = responses('preprocessing')
    response['process_count'] = process_count

    return render_template(
        'preprocessing.html', description=process_check, response=responses('preprocessing'),
        reconstituted=ref_row['description'], civil_registries=description)


@app.route('/data/preprocessing/extended-family1')
def extended_family1():

    week_date(message="EXTENDED-FAMILY1 process started on ")
    selected_db_name = selected_db()

    prs = func.select_row(selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Persons')
    if prs is None:
        return render_template(
            'preprocessing.html', response=responses('preprocessing'), family_1='',
            description="THE [CIVIL REGISTRIES DATASET] SHOULD BE PROCESSED BEFOREHAND.")

    # check the DB
    fm1_row = func.select_row(selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Extended-Family1')
    ref_row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Co-referents')
    civ_row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Persons')
    ref_row = {'description': ''} if ref_row is None else ref_row['description']
    civ_row = {'description': ''} if civ_row is None else civ_row['description']

    process_check, process_count = process_message()
    response = responses('preprocessing')
    response['process_count'] = process_count

    if fm1_row is not None:
        print("\n\tRetrieving the description of the processed extended family data file.\n")
        return render_template('preprocessing.html', response=response, description=process_check,
                               reconstituted=ref_row, civil_registries=civ_row, family_1=fm1_row['description'])

    # Create the dictionary of person occurrences data
    triples = associations_ttl(selected_db_name)
    # triples = 4860373
    description = F"""
    {LINE}
    ---{"DATA STRUCTURE":^{PREPROCESS_LINE}}---
    {LINE}
    
    The generated turtle file format contains {func.formatNumber(triples, currency="")} triples.
    It is generated to represent the EXTENDED FAMILY of a reconstituted individual 
    recorded in the civil registry dataset. The family ties are based on the events 
    recorded in civil certificates with the persons who participated.

    {LINE}
    ---{"EXAMPLE":^{PREPROCESS_LINE}}---
    {LINE}

    ### RELATIVES PRESENT IN THE DEATH OF PERSON:121111
    
    person:p-4037410
        civ:dHasMother  person:p-4037413 ;
        civ:dHasFather  person:p-4037412 ;
        civ:dHasPartner person:p-4037411 ;
        civ:inEvent     ev:e-1121144 .
    """

    # Insert file data into the DB
    if triples > 0:
        func.insert_row(selected_db_name, INSERT['output'], values=['Extended-Family1', description])

    # update
    process_check, process_count = process_message()
    response = responses('preprocessing')
    response['process_count'] = process_count

    # Return the description of path process and the file path
    return render_template(
        'preprocessing.html', response=responses('preprocessing'), description=process_check,
        reconstituted=ref_row, civil_registries=civ_row, family_1=description)


@app.route('/data/preprocessing/extended-family2')
def extended_family2():

    description = F"""
    {LINE}
    ---{"DATA STRUCTURE":^{PREPROCESS_LINE}}---
    {LINE}
    
    The RDF file containing the EXTENDED FAMILY of a reconstituted individual is 
    transformed to a dictionary using a person's ID as the key for assessing the 
    various relations in an extended family. 
    
    {LINE}
    ---{"EXAMPLE":^{PREPROCESS_LINE}}---
    {LINE}
    
    For example, person [p-2272899] plays the role of 
        --> [--nHasMother->] with [p-717147] while he also plays the role of 
        --> [--nHasFather->] with [p-717146].
    """

    week_date(message="EXTENDED-FAMILY2 process started on ")
    selected_db_name = selected_db()

    prs = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Persons')
    fam1_row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Extended-Family1')

    if prs is None or fam1_row is None:
        process_check, process_count = process_message()
        response = responses('preprocessing')
        response['process_count'] = process_count
        return render_template(
            'preprocessing.html', response=responses('preprocessing'),  family_2='',
            description="[CIVIL REGISTRIES DATASET] AND [EXTENDED-FAMILY-1] SHOULD BE PROCESSED BEFOREHAND.")

    # check the DB
    fam2_row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Extended-Family2')
    ref_row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Co-referents')
    civ_row = func.select_row(db_name=selected_db_name, table=OUTPUT_FILE_TABLE, column="name", value='Persons')
    ref_row = {'description': ''} if ref_row is None else ref_row['description']
    civ_row = {'description': ''} if civ_row is None else civ_row['description']
    fam1_row = {'description': ''} if fam1_row is None else fam1_row['description']

    if fam2_row is not None and fam2_row != 'None':
        process_check, process_count = process_message()
        response = responses('preprocessing')
        response['process_count'] = process_count
        print("\n\tRetrieving the description of the processed extended family 2 data file.\n")
        return render_template(
            'preprocessing.html', response=responses('preprocessing'), description=process_check,
            reconstituted=ref_row, civil_registries=civ_row, family_1=fam1_row, family_2=fam2_row['description'])

    # Create the dictionary of person occurrences data
    association_resource(selected_db_name)

    # Insert file data into the DB
    func.insert_row(db_name=selected_db_name, cmd=INSERT['output'], values=['Extended-Family2', description])

    process_check, process_count = process_message()
    response = responses('preprocessing')
    response['process_count'] = process_count

    # Return the description of path process and the file path
    return render_template('preprocessing.html', response=responses('preprocessing'),
                           reconstituted=ref_row, civil_registries=civ_row, family_1=fam1_row, family_2=description,)


def reconstituted_data(selected_db_name, cid):

    # FETCH DATA ABOUT THE RECONSTITUTED
    fetch_reconstituted = func.select_row(db_name=selected_db_name, table='RESULT_TBL', column='cid', value=cid)
    data = {
        'exists': False, 'name': '', 'marital_text': '', 'flag': None, 'bads': 0, 'cid': '', 'maybes': 0,
        'html_table': '', 'html_summary': '', 'c_size': "", 'grounded_table': dict(), 'groundless_table': dict(),
        'validated_table': None, "description": None}

    if cid is None or cid == 0:
        return data

    if fetch_reconstituted is not None:

        data = {'exists': True, 'name': capwords(fetch_reconstituted['name']), 'c_size': fetch_reconstituted['c_size'],
                'marital_text': fetch_reconstituted['marital_text'], 'flag': fetch_reconstituted['flag'],
                'bads': fetch_reconstituted['bads'], 'cid': fetch_reconstituted['cid'],
                'maybes': fetch_reconstituted['maybes'], 'html_summary': fetch_reconstituted['summary'],
                'grounded_table': serialise(fetch_reconstituted['grounded_table']),
                'groundless_table': serialise(fetch_reconstituted['groundless_table']),
                'validated_table': serialise(fetch_reconstituted['validated_table']),
                'description': serialise(fetch_reconstituted['description'])}

        return data

    return data


# ===============================================================================================
#                                           RUNNING BATCH
# ===============================================================================================
# response = {'analysis_active_color': color}


def run_helper(size=0, limit=10):

    selected_db_name = selected_db()
    sub_size = 0

    # list_summary = '2-56 58-59 61-64 66 95 116'
    list_summary = func.select_row(
        db_name="shared", table="DB_STATIC_INFO", column="db_name", value=selected_db_name)
    all_sizes_summary = [] if list_summary is None else list_summary['size_summary']

    # REQUEST FOR ALL AVAILABLE SIZES
    available_sizes = func.select_rows(
        db_name=selected_db_name, table=F" RESULT_TBL ORDER BY c_size", selected_col="DISTINCT c_size")

    # CONVERT THE AVAILABLE SIZES TO A LIST
    available_sizes_list = [row['c_size'] for row in available_sizes] if available_sizes is not None else []

    submitted_size = available_sizes_list[sub_size] if size == 0 and len(available_sizes_list) > 0 else size

    # REQUEST A TABLE OF THE FIRST AVAILABLE SIZE
    table, selected_size, processed_reconstitutions, processed_sizes = available_full_size(
        selected_db_name, submitted_size if len(available_sizes_list) > 0 else '', limit=limit)

    available_sizes = summarize_list(available_sizes_list)

    # stats = func.select_rows(db_name=selected_db(), table='EVAL_STATS')
    stats = func.select(db_name=selected_db(), cmd=SELECT['stats'])


    return render_template(
        'run.html', response=responses('run'), list_summary=all_sizes_summary, selected_size=selected_size,
        selected_index=index, table=table, processed_reconstitutions=processed_reconstitutions, limit=limit,
        processed_sizes=available_sizes, next_size=0, previous_size=0, table_size=len(processed_reconstitutions),
        stats=stats, above=ABOVE, overall_stats=overall_stats(selected_db_name))


@app.route('/run', methods=['GET', 'POST'])
def run():

    week_date(message="RUN AVAILABLE FULL SIZE")
    limit = request.form.get("table-limit")
    size = request.form.get("submitted-size")
    size = int(size.strip()) if size is not None and size.strip().isdigit() else 0
    limit = int(limit.strip()) if limit is not None and limit.strip().isdigit() else DEFAULT_LIMIT

    print(F"{'TABLE LIMIT':{PADDING}} : {limit}\n"
          F"{'CLUSTER SIZE':{PADDING}} : {size}\n")

    return run_helper(size, limit=limit)


@app.route('/runners', methods=['GET', 'POST'])
def runners():

    start = time()
    week_date(message="RUNNERS")
    reconstitutions = dict()
    limit = request.form.get("table-limit-cs")
    size_cs = request.form.get("submitted-size-cs")
    size_cs = int(size_cs.strip()) if size_cs is not None and size_cs.strip().isdigit() else 0
    limit = int(limit.strip()) if limit is not None and limit.strip().isdigit() else DEFAULT_LIMIT

    print(F"{'TABLE LIMIT':{PADDING}} : {limit}\n"
          F"{'CLUSTER SIZE':{PADDING}} : {size_cs}\n")

    # FETCH THE INPUT
    sizes = request.form.get('sizes')
    # FETCH THE SELECTED DB NAE
    selected_db_name = selected_db()
    # FETCH THE CO-REFERENTS FROM THE DB
    co_referents = func.get_rows(selected_db_name, table='CLUSTERS_TBL')
    # CHECK FOR INPUT SYNTAX ERROR
    error = (sizes.__contains__('- ') or sizes.__contains__(' -') or len(sizes) == 0) is True
    # PROCESS THE SIZE INPUT
    sizes = [size for size in sizes.split(' ') if len(size) > 0]

    # 1.  Collecting reconstitutions' data per cluster size
    print(F"INPUT: {sizes}\n"
          F"1. Collecting reconstitutions' data per cluster size")

    for row in co_referents:
        dict_data = serialise(row[1])
        size = dict_data["cor_count"]
        if size in reconstitutions:
            reconstitutions[size][row[0]] = dict_data['ids']
        else:
            reconstitutions[size] = {row[0]: dict_data['ids']}

    print("2. Computing the available sizes")
    # GET THE SIZE RANGES OF THE DATA: '2-56 58-59 61-64 66 95 116'
    # list_summary = '2-56 58-59 61-64 66 95 116'
    list_summary = summarize_list(list(reconstitutions.keys()))

    if error is True:
        return render_template(
            'run.html', response=responses('run'), list_summary=list_summary,
            requested_sizes=sizes, error=error, color_run=GREEN, previous_size=0, next_size=0)

    def check_sum():

        summation = 0
        for size in sizes:

            rge = size.split('-')
            if len(rge) == 1:
                cur_size = int(rge[0])
                if cur_size in reconstitutions:
                    check_size = func.select_rows(
                        db_name=selected_db_name,
                        table=F"RESULT_TBL WHERE c_size={cur_size}", selected_col="DISTINCT c_size")
                    if check_size is not None and len(check_size) > 0:
                        pass
                    else:
                        summation += len(reconstitutions[cur_size])

            elif len(rge) == 2:
                if int(rge[0]) < int(rge[1]):
                    for cur_size in range(int(rge[0]), int(rge[1]) + 1):
                        if cur_size in reconstitutions:
                            check_size = func.select_rows(
                                db_name=selected_db_name,
                                table=F"RESULT_TBL WHERE c_size={cur_size}", selected_col="DISTINCT c_size")
                            if check_size is not None and len(check_size) > 0:
                                pass
                            else:
                                summation += len(reconstitutions[cur_size])

        return summation

    def helper(rec_size):

        cmd_values = []
        counter = 0
        start_time = time()

        if rec_size in reconstitutions:

            referents = reconstitutions[rec_size]
            size = len(referents)
            print(F"  It contains {size} reconstituted clusters.")
            # 563339 533367 43768
            for cid, p_ids in referents.items():

                # data.keys() = {'name', 'marital_text', 'flag', 'bads', 'cid', 'maybes', 'html_table', 'html_summary'}
                referents = func.select_row(db_name=selected_db_name, table='CLUSTERS_TBL', column='id', value=cid)
                referents = ast.literal_eval(referents[1])
                expected_components, data = quality_check(selected_db_name, cid, referents)

                # print(F"\t{'CID':{PADDING}}: {cid}\n"
                #       F"\t{'KEYS LENGTH':{PADDING}}: {len(p_ids)}\n"
                #       F"\t{'REFERENTS':{PADDING}}: {referents}\n")
                # print(data)

                # cid, name, flag, marital_text, bads, maybes, summary, html_table
                cmd_values.append((data['cid'], data['c_size'], data['name'], data['flag'], data['marital_text'],
                                   data['bads'], data['maybes'], data['html_summary'], F"{data['grounded_table']}",
                                   F"{data['groundless_table']}", F"{data['rdf_data']}", F"{data['description']}"))

                counter += 1
                progressOut(i=counter, total=size, start=start_time, bars=50)

        return cmd_values

    # GO THROUGH THE VARIOUS REQUESTED RANGES

    total = check_sum()
    print(F"3. A total of {total} reconstitutions to process.\n")
    # F"  It will take about {to_days(minutes=(total * 10 // 600))} hours\n"

    def gen():

        last_size = 0
        inserted_count = 0

        # GOING THROUGH THE SIZE INPUT
        for size in sizes:

            # CHECK WHETHER IY IS A RANGE
            rge = size.split('-')

            # IT IS NOT A RANGE
            if len(rge) == 1:
                cur_size = int(rge[0])
                last_size = cur_size

                print(F"\n\n- RECONSTITUTIONS OF SIZE: {cur_size}")
                # CHECK WHETHER THE SIZE HAS ALREADY BEEN PROCESSED
                check_size = func.select_rows(
                    db_name=selected_db_name,
                    table=F"RESULT_TBL WHERE c_size={cur_size}", selected_col="DISTINCT c_size")

                # IT HAS ALREADY BEEN PROCESSED
                if check_size is not None and len(check_size) > 0:
                    print(F"\nSize {cur_size} has already been processed")

                # CONTINUE FOR PROCESSING
                else:
                    # COLLECT ALL VALUES FOR INSERTION
                    values = helper(rec_size=cur_size)
                    if len(values) > 0:
                        inserted_count += func.insert_rows(db_name=selected_db_name, cmd=INSERT['result'], values=values)

                # INSERT THE STATS FOR THIS SET OF CLUSTERS
                statistics = current_stats(db_name=selected_db_name, c_size=size)

                # c_size, total, likelyWithoutWarning, likelyWithWarning, uncertain, unlikely
                values = (size, statistics['full_size'], statistics['percentage_likely_s'],
                          statistics['percentage_likely'], statistics['percentage_uncertain'],
                          statistics['percentage_unlikely'])

                func.insert_row(db_name=selected_db_name, cmd=INSERT['eval_stats'], values=values)

            # IT IS A RANGE
            elif len(rge) == 2:

                if int(rge[0]) < int(rge[1]):

                    for r_size in range(int(rge[0]), int(rge[1])+1):

                        last_size = r_size
                        print(F'\n\n- RECONSTITUTIONS OF SIE: {r_size}')

                        # CHECK WHETHER THE SIZE HAS ALREADY BEEN PROCESSED
                        check_size = func.select_rows(
                            db_name=selected_db_name,
                            table=F"RESULT_TBL WHERE c_size={r_size}", selected_col="DISTINCT c_size")

                        # IT HAS ALREADY BEEN PROCESSED
                        if check_size is not None and len(check_size) > 0:
                            print(F"  Size {r_size} has already been processed")

                        # CONTINUE FOR PROCESSING
                        else:
                            # COLLECT ALL VALUES FOR INSERTION
                            values = helper(rec_size=r_size)
                            inserted_count += func.insert_rows(
                                db_name=selected_db_name, cmd=INSERT['result'], values=values)

                        # INSERT THE STATS FOR THIS SET OF CLUSTERS
                        statistics = current_stats(db_name=selected_db_name, c_size=r_size)

                        # c_size, total, likelyWithoutWarning, likelyWithWarning, uncertain, unlikely
                        values = (r_size, statistics['full_size'], statistics['percentage_likely_s'],
                                  statistics['percentage_likely'], statistics['percentage_uncertain'],
                                  statistics['percentage_unlikely'])

                        func.insert_row(db_name=selected_db_name, cmd=INSERT['eval_stats'], values=values)

        # COMPUTE THE OVERALL STAT OF ALL PROCESSED CLUSTER SIZES CURRENTLY AVAILABLE IN THE DB.
        overall_stats(selected_db_name, update_it=True)
        return last_size

    l_size = gen()

    table = batch_rec_table(selected_db_name, size=l_size, limit=DEFAULT_LIMIT)
    full_processed_sizes = processed_rec_sizes(selected_db_name)
    _size, _processed_reconstitutions, _processed_sizes = available_size(
        db_name=selected_db_name, size=l_size, flag_filter="All", validated="ignore", limit=DEFAULT_LIMIT)

    # UPDATE STATE
    pages = nbr_of_pages(
        selected_db_name=selected_db_name, rand_size=l_size, flag_filter='All', validated='ignore', max_rows=DEFAULT_LIMIT)
    state = {'cluster_size': l_size, 'max_pages': pages, 'current_page': 1, 'table_row': 1,
             'table_limit': par.MAX_TABLE_ROWS, 'filter': "All", 'validated': 'ignore', 'hide_table': 'on'}
    update_state(db_name=selected_db_name, state=state)

    # stats = func.select_rows(db_name=selected_db(), table='EVAL_STATS')
    stats = func.select(db_name=selected_db(), cmd=SELECT['stats'])

    print(F"""
    sizes {sizes}
    processed {full_processed_sizes}
    """)

    completed_job(started=start)

    return render_template('run.html', response=responses('run'), list_summary=list_summary, sizes_request=sizes,
                           error=error, table=table, previous_size=0, next_size=0, processed_sizes=full_processed_sizes,
                           processed_reconstitutions=_processed_reconstitutions, selected_size=l_size,
                           table_size=len(_processed_reconstitutions), stats=stats, above=ABOVE,
                           overall_stats=overall_stats(selected_db_name))


@app.route('/run_previous', methods=['GET', 'POST'])
def run_previous():

    week_date(message="RUN PREVIOUS AVAILABLE FULL SIZE")
    selected_db_name = selected_db()

    limit = request.form.get("table-limit-p")
    size = request.form.get("submitted-size-p")
    size = int(size.strip()) if size is not None and size.strip().isdigit() else 0
    limit = int(limit.strip()) if limit is not None and limit.strip().isdigit() else 10

    print(F"{'TABLE LIMIT':{PADDING}} : {limit}\n"
          F"{'CLUSTER SIZE':{PADDING}} : {size}\n")

    previous_size = request.form.get('submitted_previous_size')
    previous_size = 0 if previous_size is None else int(previous_size) - 1

    # list_summary = '2-56 58-59 61-64 66 95 116'
    list_summary = func.select_row(
        db_name="shared", table="DB_STATIC_INFO", column="db_name", value=selected_db_name)
    all_sizes_summary = [] if list_summary is None else list_summary['size_summary']

    processed_rec = func.select_rows(
        db_name=selected_db_name, table=F" RESULT_TBL ORDER BY c_size", selected_col="DISTINCT c_size")
    processed_rec = [row['c_size'] for row in processed_rec]

    previous_size = previous_size if previous_size > 0 else 0

    table, selected_size, processed_reconstitutions, processed_sizes = available_full_size(
        selected_db_name, processed_rec[previous_size] if len(processed_rec) > 0 else '', limit=limit)

    processed_rec = summarize_list(processed_rec)

    stats = func.select(db_name=selected_db(), cmd=SELECT['stats'])

    return render_template('run.html', response=responses('run'), selected_size=selected_size, table=table,
                           processed_reconstitutions=processed_reconstitutions, processed_sizes=processed_rec,
                           list_summary=all_sizes_summary, selected_index=index, previous_size=previous_size,
                           next_size=previous_size, table_size=len(processed_reconstitutions), limit=limit,
                           stats=stats, above=ABOVE, overall_stats=overall_stats(selected_db_name))


@app.route('/run_next', methods=['GET', 'POST'])
def run_next():

    week_date(message="RUN NEXT AVAILABLE FULL SIZE")
    selected_db_name = selected_db()
    next_size = request.form.get('submitted_size')
    next_size = 0 if next_size is None else int(next_size) + 1

    limit = request.form.get("table-limit-n")
    size = request.form.get("submitted-size-n")
    size = int(size.strip()) if size is not None and size.strip().isdigit() else 0
    limit = int(limit.strip()) if limit is not None and limit.strip().isdigit() else 10

    print(F"{'TABLE LIMIT':{PADDING}} : {limit}\n"
          F"{'CLUSTER SIZE':{PADDING}} : {size}\n")

    # list_summary = '2-56 58-59 61-64 66 95 116'
    list_summary = func.select_row(
        db_name="shared", table="DB_STATIC_INFO", column="db_name", value=selected_db_name)
    all_sizes_summary = [] if list_summary is None else list_summary['size_summary']

    processed_rec = func.select_rows(
        db_name=selected_db_name, table=F" RESULT_TBL ORDER BY c_size", selected_col="DISTINCT c_size")
    processed_rec = [row['c_size'] for row in processed_rec]

    next_size = len(processed_rec) - 1 if next_size >= len(processed_rec) else next_size

    table, selected_size, processed_reconstitutions, processed_sizes = available_full_size(
        selected_db_name, processed_rec[next_size] if len(processed_rec) > 0 else '', limit=limit)

    summarize_list(processed_rec)

    stats = func.select(db_name=selected_db(), cmd=SELECT['stats'])

    return render_template('run.html', response=responses('run'), selected_size=selected_size, table=table,
                           processed_reconstitutions=processed_reconstitutions, processed_sizes=summarize_list(processed_rec),
                           list_summary=all_sizes_summary, selected_index=index, previous_size=next_size, next_size=next_size,
                           table_size=len(processed_reconstitutions), limit=limit, stats=stats, above=ABOVE,
                           overall_stats=overall_stats(selected_db_name))


@app.route('/run_Analysis', methods=['GET', 'POST'])
def run_Analysis():

    week_date(message=" RUN ANALYSIS ")
    selected_db_name = selected_db()
    cluster_size = request.form.get('CLUSTER_SIZE').strip()
    print(cluster_size)

    state = get_state(db_name=selected_db_name)
    flag_filter = state['filter']
    validated = state['validated']
    max_rows = state['table_limit']
    hide_table = state['hide_table']

    # UPDATE STATE AS THE SIZE IS NOT SET
    pages = nbr_of_pages(selected_db_name, cluster_size, flag_filter, validated, max_rows)
    state = {'cluster_size': cluster_size, 'max_pages': pages, 'current_page': 1, 'table_row': 1,
             'table_limit': max_rows, 'filter': flag_filter, 'validated': validated}
    update_state(db_name=selected_db_name, state=state)

    previous_page = 1
    second_page = previous_page + 1
    rand_size = int(cluster_size)
    next_page = 1

    start_from = max_rows * previous_page - max_rows
    start_from = start_from if start_from >= 0 else 0

    return _analysis_(selected_db_name=selected_db_name, cluster_size=rand_size, pages=pages, flag_filter=flag_filter,
                      validated=validated, previous_page=1, next_page=next_page, second_page=second_page,
                      max_page=pages, max_rows=max_rows, start_from=start_from, tbl_idx=1, hide_table=hide_table)


# ===============================================================================================
#                                           ANALYSIS
# ===============================================================================================

# bads_cmd = F"SELECT COUNT(*) FROM (SELECT bads FROM RESULT_TBL WHERE c_size={selected_size} AND bads>0 {limit_text});"
# fetch_bads = func.select(db_name=selected_db_name, cmd=bads_cmd)
# bads = [col for item in fetch_bads for col in item][0] if fetch_bads is not None else 0

# https://personal.sron.nl/~pault/

nightfall = ['#FFFFFF', '#125A56', '#00767B', '#238F9D', '#42A7C6', '#60BCE9', '#9DCCEF', '#C6DBED', '#DEE6E7', '#ECEADA',
             '#F0E6B2', '#F9D576', '#FFB954', '#FD9A44', '#F57634', '#E94C1F', '#D11807', '#A01813', '#FFFFFF']

incandescent = ['#CEFFFF', '#C6F7D6', '#A2F49B', '#BBE453', '#D5CE04', '#E7B503',
                '#F19903', '#F6790B', '#F94902', '#E40515', '#A80003', '#888888']


def _analysis_(
        selected_db_name, cluster_size, pages, previous_page,  next_page, second_page, max_page, start_from, max_rows,
        flag_filter="All", validated='ignore', tbl_idx=None, show=False, rdf_data='', hide_table='on', only_hide=False):

    # size 20 : 1383 [Likely] - 1769, 3055 [Birth child-parent issues] 646994

    selected_size, bads, cid = 0, 0, 0
    show_submitted_id = ''
    processed_reconstitutions = []
    table_cid = request.form.get('cid')
    c_size = request.form.get('c_size')
    submitted_cid = request.form.get('reconstitution_id')
    data = reconstituted_data(selected_db_name, cid=None)
    table_index = request.form.get('index') if tbl_idx is None else tbl_idx
    status = 'DEFAULT' if submitted_cid is None or len(submitted_cid if submitted_cid else '') == 0 else 'CID-SUBMISSION'

    # DEFAULT ANALYSIS
    if status == 'DEFAULT':

        submitted_cid = ''

        if cluster_size > 0:
            c_size = cluster_size
            table_index = 1 if table_index is None else int(table_index)

        else:
            c_size = -1 if c_size is None else c_size
            table_index = -1 if table_index is None else table_index

        # FETCH THE FILTERED-BASED RECONSTITUTED
        selected_size, processed_reconstitutions, processed_sizes = offset_size(
            selected_db_name, c_size, flag_filter=flag_filter,
            validated=validated, start_from=start_from, nbr_rows=max_rows)

        # UPDATE THE SELECTED SIZE
        selected_size = 0 if len(str(selected_size)) == 0 \
                             or str(selected_size) == "---" or str(selected_size).strip().isdigit() is False \
            else int(selected_size)

        max_page = min(max_page, len(processed_reconstitutions))

        if cluster_size > 0 and table_index - 1 < len(processed_reconstitutions):
            table_cid = F"{processed_reconstitutions[table_index - 1]['cid']}"

        bads = len([row['flag'] for row in processed_reconstitutions if row['flag'] == 'Unlikely'])\
            if processed_reconstitutions is not None else 0

        cid = table_cid
        data = reconstituted_data(selected_db_name, cid)

    # SUBMIT A RECONSTITUTION ID
    elif status == 'CID-SUBMISSION':

        show_submitted_id = 'show'
        table_index = -1 if table_index is None else table_index
        submitted_cid = request.form.get('reconstitution_id')

        # IF A RECONSTITUTED ID IS SUBMITTED, DISCARD THE TABLE ID
        # cid = table_cid if submitted_cid is None or len(submitted_cid if submitted_cid else '') == 0 else submitted_cid
        cid = submitted_cid
        data = reconstituted_data(selected_db_name, cid)
        c_size = int(data['c_size']) if len(str(data['c_size'])) > 0 else 0

        # MAXIMUM PAGES
        pages = nbr_of_pages(selected_db_name, c_size, flag_filter='All', validated='ignore', max_rows=max_rows)
        update = get_row_index(db=selected_db_name, size=c_size, cid=cid, max_rows=max_rows)
        if update is not None:
            previous_page = update['page']
            next_page = previous_page + 1
            second_page = next_page
            table_index = update['table_idx']
            start_from = update['start_from']

        # FETCH THE FILTERED-BASED RECONSTITUTED
        selected_size, processed_reconstitutions, processed_sizes = offset_size(
            selected_db_name, c_size, flag_filter='All', validated='ignore', start_from=start_from, nbr_rows=max_rows)

        max_page = min(max_page, len(processed_reconstitutions))
        bads = len([row['flag'] for row in processed_reconstitutions if row['flag'] == 'Unlikely'])\
            if processed_reconstitutions is not None else 0

    process_count = check_process_count()
    table, selected_size_all, processed_reconstitutions_all, processed_sizes_all = available_full_size(
        selected_db_name, size=None)

    # EXIT IF THERE IS NO SELECTED DB
    if selected_db_name is None:
        data['html_summary'] = "<h2 style='text-align: center' ><strong>Please select a DB.</strong></h2>"
        return render_template(
            'evaluation.html', response=responses('analysis'), analysis_data=data, selected_index=table_index,
            processed_sizes=processed_sizes_all, processed_reconstitutions=processed_reconstitutions,
            selected_size=selected_size, table_size=len(processed_reconstitutions), bads=bads, pages=pages,
            previous_page=previous_page, next_page=next_page, second_page=second_page, max_page=max_page,
            submitted_reconstitution_id=submitted_cid, likely=current_stats(selected_db_name, c_size),
            overall_stats=overall_stats(selected_db_name, c_size), flag_filter=flag_filter, validated=validated)

    # EXIT IF THERE IS A PROBLEM WITH THE CLUSTER ID
    elif cid == 0:
        data['html_summary'] = "<h2 style='text-align: center' ><strong>The request box is empty</strong></h2>"
        return render_template(
            'evaluation.html', analysis_data=data, selected_index=table_index, processed_sizes=processed_sizes_all,
            processed_reconstitutions=processed_reconstitutions, selected_size=c_size, color000=GREEN,
            db=get_db_fle_names(), selected_db_name=selected_db_name, table_size=len(processed_reconstitutions),
            bads=bads, pages=pages, previous_page=previous_page, next_page=next_page, flag_filter=flag_filter,
            second_page=second_page, max_page=max_page, submitted_reconstitution_id=submitted_cid,
            likely=current_stats(selected_db_name, c_size), overall_stats=overall_stats(selected_db_name),
            validated=validated)

    # GATHER STATS
    # flagged_likely = func.select(db_name=selected_db_name, cmd=SELECT['likely'].format(c_size=c_size))
    # flagged_likely = [row['COUNT(DISTINCT cid)'] for row in flagged_likely][0] if flagged_likely is not None else []
    # full_size_cmd = F"SELECT COUNT(DISTINCT cid) FROM RESULT_TBL WHERE c_size={c_size};"
    # full_size = func.select(db_name=selected_db_name, cmd=full_size_cmd)
    # full_size = [row['COUNT(DISTINCT cid)'] for row in full_size][0] if full_size is not None else []

    if data['exists'] is False:

        # GET THE RECONSTITUTED FROM THE CLUSTER TABLE
        referents = func.select_row(db_name=selected_db_name, table='CLUSTERS_TBL', column='id', value=cid)
        referents = ast.literal_eval(referents[1]) if referents is not None else None

        # GET THE RULES-BASED REPORT
        expected_components, data = quality_check(selected_db_name, cid, referents, process_count=process_count)
        data['validated_table'], data['description'] = None, None

        # NON PROCESSED DATA
        if data is not None:
            print("THE DATA HAS NOT BEEN PROCESSED BUT THE ANALYSIS IS AVAIBLE\n")
            c_size = data['c_size']
            # TO NOT CREATE CONFUSION, DO NOT SAVE THE DATA THAT HAS NOT BEEN PROCESSED
            # values = [(data['cid'], data['c_size'], data['name'], data['flag'], data['marital_text'], data['bads'],
            #                        data['maybes'], data['html_summary'], data['html_table'])]
            # func.insert_rows(db_name=selected, cmd=insert_result, values=values)

        # ALREADY PROCESSED DATA
        else:
            data = {'name': '', 'marital_text': '', 'flag': None, 'bads': 0, 'cid': '', 'maybes': 0,
                    'html_table': '',  'c_size': "", 'grounded_table': dict(), 'groundless_table': dict(),
                    'validated_table': None, "description": None,
                    'html_summary': "<h2 style='text-align: center' ><strong>Please select a DB.</strong></h2>"}

    print(F"STATUS: {status}\n\n"
          F"\t- {'SHOW TABLE':{PADDING}} : {hide_table}\n"
          # F"\t- {'FLAGS':{PADDING}} : {flagged_likely}\n"
          # F"\t- {'FULL SIZE':{PADDING}} : {full_size}\n"
          F"\t- {'TABLE CID':{PADDING}} : {table_cid}\n"
          F"\t- {'START FROM':{PADDING}} : {start_from}\n"
          F"\t- {'TABLE INDEX':{PADDING}} : {table_index}\n"
          F"\t- {'SELECTED SIZE':{PADDING}} : {c_size}\n"
          F"\t- {'TABLE SIZE':{PADDING}} : {len(processed_reconstitutions)}\n"
          F"\t- {'max_page':{PADDING}} : {max_page}\n"
          F"\t- {'submitted CID':{PADDING}} : {submitted_cid}\n"
          F"\t- {'RUNNING CID':{PADDING}} : {cid}\n"
          F"\t- {'BADS':{PADDING}} : {bads}\n"
          F"\t- {'START FROM':{PADDING}} : {start_from}\n"
          # F"\t- {'Rows Fetched':{PADDING}} : {len(fetch_reconstituted) if fetch_reconstituted is not None else 0}\n"
          F"\t- {'GROUNDED TABLE':{PADDING}} : {len(data['grounded_table'])}\n"
          F"\t- {'GROUNDLESS TABLE':{PADDING}} : {len(data['groundless_table'])}\n")

    # COMPUTING THE FAMILY'S THREAD
    table_index = int(table_index)
    c_size = -1 if c_size is None or len(str(c_size).strip()) == 0 else c_size
    family = family_thread(db_name=selected_db_name, processed=data['cid'])
    validated_family = validated_thread(data['cid'], data['validated_table'], selected_db_name)
    list_of_processed_sizes = convert_list_summary2list(processed_sizes_all)

    return render_template('evaluation.html', response=responses('analysis'), analysis_data=data,
                           processed_sizes=processed_sizes_all, processed_reconstitutions=processed_reconstitutions,
                           selected_size=c_size, selected_index=table_index, table_size=len(processed_reconstitutions),
                           bads=bads, pages=pages, previous_page=previous_page, next_page=next_page,
                           second_page=second_page, max_page=max_page, show="show" if show is True else "",
                           rdf_data=rdf_data, show_submitted_id=show_submitted_id, flag_filter=flag_filter,
                           submitted_reconstitution_id=submitted_cid, likely=current_stats(selected_db_name, c_size),
                           overall_stats=overall_stats(selected_db_name), validated=validated, hide_table=hide_table,
                           only_hide=only_hide, max_rows=max_rows, family=family, validated_family=validated_family,
                           list_of_processed_sizes=list_of_processed_sizes, nightfall=incandescent)


def _next_analysis_(max_rows, flag_filter, validated):

    selected_db_name = selected_db()
    get_state(selected_db_name)

    table_cid = request.form.get('cid')
    c_size = request.form.get('selected_size')
    table_index = request.form.get('selected_index')
    table_index = int(table_index if table_index is not None and table_index != '---' and table_index != 'None' else 0)

    next_page = request.form.get('next_page_3')
    next_page = int(next_page)-1 if len(next_page) > 0 and next_page is not None else 1
    next_page = next_page if next_page > 0 else 1
    start_from = max_rows * next_page - max_rows

    # previous_page = next_page - 1 if next_page > 0 else 1
    # second_page = previous_page + 1
    max_page = nbr_of_pages(selected_db_name, c_size, flag_filter, validated, max_rows)
    next_page += 1

    # bads_cmd = F"SELECT COUNT(bads) FROM RESULT_TBL WHERE c_size={table_size} and bads > 0;"
    # flags_cmd = F"SELECT cid, flag FROM RESULT_TBL WHERE c_size={table_size};"
    # count = func.select(db_name=selected_db_name, cmd=bads_cmd)
    # flag_rows = func.select(db_name=selected_db_name, cmd=flags_cmd)
    # bads = [col for item in count for col in item] if count is not None else [0]
    # flags = {row['cid']: row['flag'] for row in flag_rows}

    # SELECTING ROWS
    # print(F"SELECTING ROWS")
    processed_rec = func.select_rows(
        db_name=selected_db_name, table=F" RESULT_TBL ORDER BY c_size", selected_col="DISTINCT c_size")
    processed_rec = [row['c_size'] for row in processed_rec]

    process_count = check_process_count()

    # about full size
    # print(F"ABOUT FULL SIZE")
    table, selected_size_all, processed_reconstitutions_all, processed_sizes_all = available_full_size(
        selected_db_name, size=None)

    # print("OFFSET\n")
    selected_size, processed_reconstitutions, processed_sizes = offset_size(
        db_name=selected_db_name, size=c_size, flag_filter=flag_filter,
        validated=validated, start_from=start_from, nbr_rows=max_rows)

    next_row = int(table_index) + 1
    table_index = next_row if table_index < len(processed_reconstitutions) else int(table_index)

    # MOVE TO NEXT PAGE
    if next_row > len(processed_reconstitutions) and next_page + 1 <= max_page + 1:

        table_index = 1
        next_page += 1
        second_page = next_page
        previous_page = second_page - 1
        start_from = max_rows * previous_page - max_rows

        selected_size, processed_reconstitutions, processed_sizes = offset_size(
            db_name=selected_db_name, size=c_size, flag_filter=flag_filter,
            validated=validated, start_from=start_from, nbr_rows=max_rows)
    else:

        second_page = next_page
        previous_page = second_page - 1
        start_from = max_rows * previous_page - max_rows

        selected_size, processed_reconstitutions, processed_sizes = offset_size(
            db_name=selected_db_name, size=c_size, flag_filter=flag_filter,
            validated=validated, start_from=start_from, nbr_rows=max_rows)

    bads = len([row['flag'] for row in processed_reconstitutions if row['flag'] == 'Unlikely']) \
        if processed_reconstitutions is not None else 0

    if len(processed_rec) > 0:
        if 0 < table_index <= len(processed_reconstitutions):
            table_cid = F"{processed_reconstitutions[table_index - 1]['cid']}"

    print(F"OUTPUT DATA\n"
          F"\t- {'NEXT PAGE':{PADDING}} : {next_page}\n"
          F"\t- {'TABLE INDEX':{PADDING}} : {table_index}\n"
          F"\t- {'NEXT ROW':{PADDING}} : {next_row}\n"
          F"\t- {'TABLE SIZE':{PADDING}} : {len(processed_reconstitutions)}\n"
          F"\t- {'SELECTED SIZE':{PADDING}} : {c_size}\n\n"
          F"\t- {'MAX PAGE':{PADDING}} : {max_page}\n"
          F"\t- {'PREVIOUS PAGE':{PADDING}} : {previous_page}\n"
          F"\t- {'SECOND PAGE':{PADDING}} : {second_page}\n"
          F"\t- {'NEXT PAGE':{PADDING}} : {next_page}\n\n"
          F"\t- {'START FROM':{PADDING}} : {start_from}\n\n"
          F"\t- {'FLAG FILTER':{PADDING}} : {flag_filter}\n"
          F"\t- {'TABLE CID':{PADDING}} : {table_cid}\n"
          F"\t- {'RUNNING CID':{PADDING}} : {table_cid}")

    data = reconstituted_data(selected_db_name, cid=table_cid)

    c_size = int(c_size) if c_size is not None else 0

    state = {'cluster_size': c_size, 'max_pages': max_page, 'current_page': previous_page, 'table_row': table_index,
             'table_limit': max_rows, 'filter': flag_filter, 'validated': validated}
    update_state(db_name=selected_db_name, state=state)

    hide_table = get_state(selected_db_name)['hide_table']

    # EXIT IF THERE IS NO SELECTED DB
    if selected_db_name is None:
        data['html_summary'] = "<h2 style='text-align: center' ><strong>Please select a DB.</strong></h2>"
        return render_template(
            'evaluation.html', response=responses('analysis'), analysis_data=data, selected_index=table_index,
            processed_sizes=processed_sizes_all, processed_reconstitutions=processed_reconstitutions,
            selected_size=selected_size, table_size=len(processed_reconstitutions), bads=bads, flag_filter=flag_filter,
            validated=validated, likely=current_stats(selected_db_name, c_size),
            overall_stats=overall_stats(selected_db_name))

    # IF THERE IS A PROBLEM WITH THE CLUSTER ID
    elif table_cid is None or len(table_cid) == 0:
        family = family_thread(db_name=selected_db_name, processed=data['cid'])
        data['html_summary'] = "<h2 style='text-align: center' ><strong>The request box is empty</strong></h2>"
        return render_template(
            'evaluation.html', response=responses('analysis'), analysis_data=data, selected_index=table_index,
            processed_sizes=processed_sizes_all, processed_reconstitutions=processed_reconstitutions,
            selected_size=c_size, table_size=len(processed_reconstitutions), bads=bads, flag_filter=flag_filter,
            validated=validated,  likely=current_stats(selected_db_name, c_size), previous_page=previous_page,
            overall_stats=overall_stats(selected_db_name), max_rows=max_rows, family=family)

    if data['exists'] is False:
        referents = func.select_row(db_name=selected_db_name, table='CLUSTERS_TBL', column='id', value=table_cid)
        referents = ast.literal_eval(referents[1])

        # GET THE RULES-BASED REPORT
        expected_components, data = quality_check(selected_db_name, table_cid, referents, process_count=process_count)

        cycle_check(table_cid, referents, selected_db_name, lst=True)

        if 'cid' in data:
            pass
            # values = [(data['cid'], data['c_size'], data['name'], data['flag'], data['marital_text'], data['bads'],
            #                        data['maybes'], data['html_summary'], data['html_table'])]
            # func.insert_rows(db_name=selected, cmd=insert_result, values=values)

        else:
            print(data)
            data['html_summary'] = F"<h2 style='text-align: center' ><strong>{data['html_summary']}</strong></h2>"

    # STATE UPDATE
    pages = nbr_of_pages(selected_db_name, c_size, flag_filter, validated, max_rows)
    state = {'cluster_size': c_size, 'max_pages': pages, 'current_page': previous_page, 'table_row': table_index,
             'table_limit': max_rows, 'filter': flag_filter, 'validated': validated, 'hide_table': hide_table}
    update_state(db_name=selected_db_name, state=state)
    family = family_thread(db_name=selected_db_name, processed=data['cid'])
    validated_family = validated_thread(data['cid'], data['validated_table'], selected_db_name)
    list_of_processed_sizes = convert_list_summary2list(processed_sizes_all)

    return render_template('evaluation.html', response=responses('analysis'), analysis_data=data,
                           processed_sizes=processed_sizes_all, processed_reconstitutions=processed_reconstitutions,
                           selected_size=c_size, selected_index=table_index, table_size=len(processed_reconstitutions),
                           bads=bads, pages=pages, previous_page=previous_page, next_page=next_page, second_page=next_page,
                           max_page=max_page, max_rows=max_rows, start_from=start_from, flag_filter=flag_filter,
                           validated=validated, likely=current_stats(selected_db_name, c_size), hide_table=hide_table,
                           overall_stats=overall_stats(selected_db_name), family=family, nightfall=incandescent,
                           list_of_processed_sizes=list_of_processed_sizes, validated_family=validated_family)


@app.route('/recon_sizes', methods=['GET', 'POST'])
def analysis_rec_size():

    week_date(message=" RECONSTITUTED SIZE ")
    selected_db_name = selected_db()

    # =============================================================
    # SUBMIT A REC ID
    # =============================================================

    # STATE INPUT
    max_rows = int(par.MAX_TABLE_ROWS)
    cluster_size = request.form.get('cluster_size').strip()
    flag_filter = request.form.get('Filter-Flags')
    validated = request.form.get('Filter-Validated')
    table_limit = request.form.get('Table-Limit')
    only_hide = request.form.get("Submit-Table-Setting")

    # UPDATE TABLE SHOW STATE
    if only_hide != "submit it all":
        update_state(db_name=selected_db_name, state={'hide_table': only_hide})

    # STATES
    if get_state(db_name=selected_db_name)['cluster_size'] > 0:

        if only_hide == "submit it all":
            # UPDATE STATE AS THE SIZE IS NOT SET
            table_limit = table_limit.strip()
            # print(table_limit, table_limit.isnumeric())
            pages = nbr_of_pages(selected_db_name, cluster_size, flag_filter, validated,
                                 int(table_limit) if table_limit.isnumeric() is True else max_rows)
            state = {'cluster_size': cluster_size, 'max_pages': pages, 'current_page': 1, 'table_row': 1,
                     'table_limit': table_limit, 'filter': flag_filter, 'validated': validated}
            update_state(db_name=selected_db_name, state=state)

        print(F"USING STATE - {only_hide}\n")
        state = get_state(db_name=selected_db_name)
        pages = state['max_pages']
        flag_filter = state['filter']
        row_index = state['table_row']
        validated = state['validated']
        next_page = state['current_page']
        cluster_size = state['cluster_size']
        hide_table = state['hide_table']
        max_rows = state['table_limit']

        previous_page = next_page
        second_page = previous_page + 1
        next_page += 1
        start_from = max_rows * previous_page - max_rows
        start_from = start_from if start_from >= 0 else 0

    else:
        previous_page = 1
        next_page = 2
        second_page = 2
        start_from = 0
        row_index = 1

        pages = nbr_of_pages(selected_db_name, cluster_size, flag_filter, validated, max_rows)
        cluster_size = int(cluster_size) if len(cluster_size) > 0 and cluster_size is not None else 0

        # UPDATE STATE AS THE SIZE IS NOT SET
        hide_table = only_hide if only_hide != "submit it all" else 'on'
        state = {'cluster_size': cluster_size, 'max_pages': pages, 'current_page': 1, 'table_row': row_index,
                 'table_limit': table_limit, 'filter': flag_filter, 'validated': validated, 'hide_table': hide_table}
        update_state(db_name=selected_db_name, state=state)

    # INITIALIZATION OF THE ANALYSIS DATA OBJECT
    analysis_data = {
        'name': '', 'marital_text': '', 'flag': None, 'bads': 0, 'cid': '', 'maybes': 0,
        'html_table': '', 'html_summary': '', 'c_size': "", 'grounded_table': dict(),
        'groundless_table': dict(), 'validated_table': None, 'description': None}

    # OUTPUT VARIABLES

    # GENERATE THE PROCESSED SIZES
    processed_rec = func.select_rows(
        db_name=selected_db_name, table=F" RESULT_TBL ORDER BY c_size", selected_col="DISTINCT c_size")
    processed_rec = summarize_list([row['c_size'] for row in processed_rec])

    # FETCH THE RECONSTITUTED BASED ON FILTERS NAD PAGINATION
    selected_size, processed_reconstitutions, processed_sizes = offset_size(
        db_name=selected_db_name, size=cluster_size, flag_filter=flag_filter,
        validated=validated, start_from=start_from, nbr_rows=max_rows)

    # COUNT THE NUMBER OF BADS
    bads = len([row['flag'] for row in processed_reconstitutions if row['flag'] == 'Unlikely']) \
        if processed_reconstitutions is not None else 0

    print(F"\t- {'HIDE TABLE':{PADDING}} : {only_hide}\n"
          F"\t- {'FLAG FILTER':{PADDING}} : {flag_filter}\n"
          F"\t- {'VALIDATED':{PADDING}} : {validated}\n"
          F"\t- {'C-SIZE':{PADDING}} : {cluster_size}\n"
          F"\t- {'START FROM':{PADDING}} : {start_from}\n"
          F"\t- {'MAX ROWS':{PADDING}} : {max_rows}\n"
          F"\t- {'MAX PAGES':{PADDING}} : {pages}\n"
          F"\t- {'LIMIT':{PADDING}} : {max_rows}\n")

    # STATE UPDATE
    if only_hide == "submit it all":
        state = {'cluster_size': cluster_size, 'max_pages': pages, 'current_page': 1, 'table_row': state['table_row'],
                 'table_limit': table_limit, 'filter': flag_filter, 'validated': validated, 'hide_table': only_hide}
        update_state(db_name=selected_db_name, state=state)

    # FETCH THE FIRST CLUSTER ID FROM THE TABLE
    selected_index = row_index if len(processed_reconstitutions) > 0 else 0
    if selected_index > 0:
        cid = F"{processed_reconstitutions[selected_index - 1]['cid']}"
        # CHECK IF THE RECONSTITUTED EXISTS IN THE DATABASE 117162
        analysis_data = reconstituted_data(selected_db_name, cid=cid)

        # for key, va in serialise(fetch_reconstituted['groundless_table']).items():
        #     print('groundless_table', key, len(va))
        #
        # for key, va in serialise(fetch_reconstituted['grounded_table']).items():
        #     print(key, len(va))

    table, selected_size_all, processed_reconstitutions_all, processed_sizes_all = available_full_size(
        selected_db_name, size=None)
    family = family_thread(db_name=selected_db_name, processed=analysis_data['cid'])
    validated_family = validated_thread(analysis_data['cid'], analysis_data['validated_table'], selected_db_name)
    list_of_processed_sizes = convert_list_summary2list(processed_sizes_all)

    return render_template(
        'evaluation.html', response=responses('analysis'), selected_size=cluster_size, analysis_data=analysis_data,
        processed_reconstitutions=processed_reconstitutions, processed_sizes=processed_rec, previous_size=0,
        next_size=0,  selected_index=selected_index, table_size=len(processed_reconstitutions), bads=bads,
        pages=pages, previous_page=previous_page, next_page=next_page, second_page=second_page, max_page=pages,
        max_rows=max_rows, start_from=start_from, show_submitted_size='show', likely=current_stats(selected_db_name, cluster_size),
        validated=validated, overall_stats=overall_stats(selected_db_name), flag_filter=flag_filter, hide_table=hide_table,
        only_hide=only_hide, family=family, nightfall=incandescent, list_of_processed_sizes=list_of_processed_sizes,
        validated_family=validated_family)


@app.route('/analysis', methods=['GET', 'POST'])
def analysis():

    week_date(message="QUALITY CHECK OF A RECONSTITUTED ")

    selected_db_name = selected_db()
    table_index = request.form.get('index')
    table_analysis_btn = request.form.get('table_analysis_btn')

    state = get_state(db_name=selected_db_name)
    if state['cluster_size'] > 0 and table_analysis_btn is None:

        print("USING THE SATE\n")
        pages = state['max_pages']
        flag_filter = state['filter']
        row_index = state['table_row']
        validated = state['validated']
        next_page = state['current_page']
        cluster_size = state['cluster_size']
        hide_table = state['hide_table']
        max_rows = state['table_limit']

        previous_page = next_page
        second_page = previous_page + 1
        rand_size = cluster_size
        next_page += 1

        start_from = max_rows * previous_page - max_rows
        start_from = start_from if start_from >= 0 else 0

    else:

        print("CREATING A STATE\n")
        hide_table = get_state(selected_db_name)['hide_table']
        next_page = request.form.get('next_page_2')
        validated = request.form.get('tbl_analysis_btn')
        cluster_size = request.form.get('cluster_size_2')
        flag_filter = request.form.get('tbl_analysis_btn_flag_filter')
        max_rows = request.form.get('Table-Limit-Btn')
        max_rows = int(max_rows) if max_rows is not None else 0

        flag_filter = "All" if flag_filter is None or len(flag_filter) == 0 else flag_filter
        validated = "ignore" if validated is None or len(validated) == 0 else validated

        next_page = int(next_page) if next_page is not None else 2
        curr_page = next_page - 1 if next_page > 0 else 0

        cluster_size = int(cluster_size) if cluster_size is not None else 0
        rand_size = random_size() if cluster_size == 0 else cluster_size

        start_from = max_rows * curr_page - max_rows
        start_from = start_from if start_from >= 0 else 0

        previous_page = curr_page
        second_page = previous_page + 1
        pages = nbr_of_pages(selected_db_name, rand_size, flag_filter, validated, max_rows)

        row_index = None

        if table_analysis_btn == 'table-analysis-btn':
            print("UPDATING A STATE\n")
            # STATE UPDATE
            row_index = int(table_index)
            state = {'cluster_size': cluster_size, 'max_pages': pages, 'current_page': previous_page,
                     'table_row': row_index, 'table_limit': max_rows, 'filter': flag_filter, 'validated': validated,
                     'hide_table': hide_table}
            update_state(db_name=selected_db_name, state=state)

    print(F"SUBMITTED VALUES\n"
          F"\n\t- {'Random-Size':{PADDING}} : {rand_size}"
          F"\n\t- {'Cluster-Size':{PADDING}} : {cluster_size}"
          F"\n\t- {'Maximum Rows':{PADDING}} : {max_rows}"
          F"\n\t- {'Table Rows':{PADDING}} : {table_index}"
          F"\n\t- {'Maximum Pages':{PADDING}} : {pages}"
          F"\n\t- {'Previous Page':{PADDING}} : {previous_page}"
          F"\n\t- {'Next Page':{PADDING}} : {next_page}"
          F"\n\t- {'table row':{PADDING}} : {row_index}"
          F"\n\t- {'hide table':{PADDING}} : {hide_table}\n")

    return _analysis_(selected_db_name=selected_db_name, cluster_size=rand_size, pages=pages, flag_filter=flag_filter,
                      validated=validated, previous_page=previous_page, next_page=next_page, second_page=second_page,
                      max_page=pages, max_rows=max_rows, start_from=start_from, tbl_idx=row_index, hide_table=hide_table)


@app.route('/next_analysis', methods=['GET', 'POST'])
def next_analysis():

    week_date(message="NEXT QUALITY CHECK OF A RECONSTITUTED ")
    f_filter = request.form.get('next_table_idx_flag_filter')
    validated = request.form.get('next_table_idx_validated')
    max_rows = request.form.get('next_table_limit_validated')
    max_rows = par.MAX_TABLE_ROWS if max_rows is None else int(max_rows)
    return _next_analysis_(max_rows, f_filter, validated)


@app.route('/analysis_next_pagination', methods=['GET', 'POST'])
def analysis_next_pagination():

    week_date(message="NEXT PAGINATION QUALITY CHECK OF A RECONSTITUTED ")

    selected_db_name = selected_db()
    flag_filter = request.form.get('next_pagination_flag_filter')
    cluster_size = request.form.get('cluster_size_next')
    cluster_size = int(cluster_size) if cluster_size is not None else 0

    validated = request.form.get('next_pagination_validated')
    rand_size = random_size() if cluster_size == 0 else cluster_size

    max_rows = request.form.get('Table-Limit_Next')
    print("limit", max_rows)
    max_rows = par.MAX_TABLE_ROWS if max_rows is None else int(max_rows)

    # count_cmd = F"SELECT COUNT(*) FROM RESULT_TBL WHERE c_size={rand_size};"
    # count_row = func.select(db_name=selected_db_name, cmd=count_cmd)
    # pages = [col for item in count_row for col in item][0] if count_row is not None else 0

    hide_table = 1
    next_page = request.form.get('next_page')
    next_page = int(next_page)
    start = max_rows * next_page - max_rows

    previous_page = next_page
    second_page = previous_page + 1
    pages = nbr_of_pages(selected_db_name, rand_size, flag_filter, validated, max_rows)

    state = get_state(db_name=selected_db_name)
    if state['cluster_size'] > 0:
        print("Using State")
        pages = state['max_pages']
        flag_filter = state['filter']
        validated = state['validated']
        cluster_size = state['cluster_size']
        hide_table = state['hide_table']
        max_rows = state['table_limit']
        rand_size = cluster_size
        next_page += 1
    else:
        next_page += 1

    print(F"\t- {'Flag Filters':{PADDING}} : {flag_filter}\n"
          F"\t- {'cluster_size':{PADDING}} : {cluster_size}\n"
          F"\t- {'Max Pages':{PADDING}} : {pages}\n"
          F"\t- {'Max Rows':{PADDING}} : {max_rows}\n"
          F"\t- {'Next':{PADDING}} : {next_page}\n"
          F"\t- {'Previous Page':{PADDING}} : {previous_page}\n"
          F"\t- {'Second Page':{PADDING}} : {second_page}\n"
          F"\t- {'Start At':{PADDING}} : {start} \n")

    # STATE UPDATE
    state = {'cluster_size': cluster_size, 'max_pages': pages, 'current_page': previous_page, 'table_row': 1,
             'table_limit': max_rows, 'filter': flag_filter, 'validated': validated}
    update_state(db_name=selected_db_name, state=state)
    # hide_table = get_state(selected_db_name)['hide_table']

    return _analysis_(selected_db_name=selected_db_name, cluster_size=rand_size, pages=pages, previous_page=previous_page,
                      next_page=next_page, second_page=second_page, max_page=pages, max_rows=max_rows, start_from=start,
                      flag_filter=flag_filter, validated=validated, hide_table=hide_table, tbl_idx=1)


@app.route('/analysis_previous_pagination', methods=['GET', 'POST'])
def analysis_previous_pagination():

    flag_filter = request.form.get('pagination_previous_flag_filter')
    week_date(message="PAGINATION PREVIOUS QUALITY CHECK OF A RECONSTITUTED ")
    selected_db_name = selected_db()

    cluster_size = request.form.get("pagination_number_previous_cs")
    validated = request.form.get('previous_pagination_validated')
    cluster_size = int(cluster_size) if cluster_size is not None else 0
    rand_size = random_size() if cluster_size == 0 else cluster_size

    max_rows = request.form.get("pagination_number_table-limit")
    max_rows = par.MAX_TABLE_ROWS if max_rows is None else int(max_rows)

    table_size = rand_size

    previous_page = request.form.get('previous_page')
    previous_page = int(previous_page) if previous_page is not None else 1
    previous_page = previous_page - 1 if previous_page > 1 else 1
    next_page = previous_page + 1
    print(F"{'PREVIOUS PAGE':{PADDING+6}} : {previous_page}\n")

    hide_table = 'on'
    steps = previous_page + max_rows
    second_page = previous_page + 1
    pagination = nbr_of_pages(selected_db_name, rand_size, flag_filter, validated, max_rows)
    max_page = steps if steps <= pagination else pagination
    start = max_rows * previous_page - max_rows

    state = get_state(db_name=selected_db_name)
    if state['cluster_size'] > 0:
        print("USING STATE\n")
        flag_filter = state['filter']
        validated = state['validated']
        cluster_size = state['cluster_size']
        hide_table = state['hide_table']
        max_rows = state['table_limit']
        # next_page += 1

    # STATE UPDATE
    state = {'cluster_size': cluster_size, 'max_pages': max_page, 'current_page': previous_page, 'table_row': 1,
             'table_limit': max_rows, 'filter': flag_filter, 'validated': validated}
    update_state(db_name=selected_db_name, state=state)

    return _analysis_(selected_db_name=selected_db_name, cluster_size=table_size, pages=pagination,
                      previous_page=previous_page, next_page=next_page, second_page=second_page,
                      max_page=max_page, max_rows=max_rows, start_from=start,
                      flag_filter=flag_filter, validated=validated, hide_table=hide_table)


@app.route('/analysis_pagination_number', methods=['GET', 'POST'])
def analysis_pagination_number():

    week_date(message="PAGINATION [PAGE] QUALITY CHECK OF A RECONSTITUTED ")
    flag_filter = request.form.get('pagination_number_flag_filter')
    selected_db_name = selected_db()

    cluster_size = request.form.get("analysis_pagination_number_cs")
    validated = request.form.get('nbr_pagination_validated')
    cluster_size = int(cluster_size) if cluster_size is not None else 0
    rand_size = random_size() if cluster_size == 0 else cluster_size

    max_rows = request.form.get("analysis_pagination_number_table_limit")
    max_rows = par.MAX_TABLE_ROWS if max_rows is None else int(max_rows)

    table_size = rand_size

    previous_page = request.form.get('next_button_page')
    previous_page = int(previous_page) if previous_page is not None else 1
    next_page = previous_page + 1

    second_page = previous_page + 1
    pages = nbr_of_pages(selected_db_name, rand_size, flag_filter, validated, max_rows)
    start = max_rows * previous_page - max_rows

    print(F"\t{'Flag Filter':{PADDING}} : {flag_filter}\n"
          F"\t{'Previous Page':{PADDING}} : {previous_page}\n"
          F"\t{'Next Page':{PADDING}} : {next_page}\n"
          F"\t{'Max Page':{PADDING}} : {pages}\n"
          F"\t{'Start From Row':{PADDING}} : {start}\n")

    state = get_state(db_name=selected_db_name)
    if state['cluster_size'] > 0:
        print("USING SATE")
        pages = state['max_pages']
        flag_filter = state['filter']
        validated = state['validated']
        cluster_size = state['cluster_size']
        hide_table = state['hide_table']
        max_rows = state['table_limit']
        # next_page += 1
    else:
        hide_table = 'on'

    # STATE UPDATE
    state = {'cluster_size': cluster_size, 'max_pages': pages, 'current_page': previous_page, 'table_row': 1,
             'table_limit': max_rows, 'filter': flag_filter, 'validated': validated}
    update_state(db_name=selected_db_name, state=state)

    return _analysis_(selected_db_name=selected_db_name, cluster_size=table_size, pages=pages,
                      previous_page=previous_page, next_page=next_page, second_page=second_page,
                      max_page=pages, max_rows=max_rows, start_from=start,
                      flag_filter=flag_filter, validated=validated, hide_table=hide_table)


# ===============================================================================================
#                       FAMILY EXTENSION CONSISTENCY
# ===============================================================================================


@app.route('/validation_consistency', methods=['GET', 'POST'])
def validation_consistency():

    week_date(message="validation consistency  ")
    selected_db_name = selected_db()
    parameters = request.form.get('consistency-ID').split(" | ")

    consistency_id = parameters[0]
    current_role = parameters[1]
    main_cid = parameters[2]
    main_name = parameters[3]

    data = reconstituted_data(selected_db_name, cid=consistency_id)

    origin = F"{current_role} of {main_name} ({main_cid})"
    print(origin)
    print(F"SUBMITTED VALUES\n"
          F"\t- {'CONSISTENCY ID':{PADDING}} {consistency_id}\n")

    if data['exists'] is False:
        data['html_summary'] = F"<h2 style='text-align: center' ><strong>{data['html_summary']}</strong></h2>"

    # COMPUTING THE FAMILY'S THREAD
    family = family_thread(db_name=selected_db_name, processed=consistency_id)
    validated_family = validated_thread(data['cid'], data['validated_table'], selected_db_name)
    return render_template('consistency.html', response=responses('consistency'), analysis_data=data, family=family,
                           validated_family=validated_family, selected_size=family[list(family.keys())[0]][3],
                           nightfall=incandescent, origin=origin)


@app.route('/write_manual_consistency_validation', methods=['GET', 'POST'])
def write_manual_consistency_validation():

    rdf_data = ''
    mappings = dict()
    tables = defaultdict(list)
    week_date(message="CONSISTENCY VALIDATION  ")
    new_grounded = defaultdict(set)
    new_groundless = defaultdict(set)
    selected_db_name = selected_db()

    todo = request.form.get('rdf')

    # RECONSTITUTION ID
    rid = request.form.get('reconstitution-id')
    cluster_size = request.form.get('occurrence_recon_size')
    cluster_size = int(cluster_size.strip()) if cluster_size is not None else 0
    rand_size = random_size() if cluster_size == 0 else cluster_size
    cluster_size = request.form.get('occurrence_recon_size')
    cluster_size = int(cluster_size.strip()) if cluster_size is not None else 0

    if todo == 'write' or todo == 'merger-and-write':

        week_date(message="WRITING MANUAL VALIDATIONS  ")

        # GROUND RECONSTITUTIONS
        grounded_groups = request.form.getlist('g_selected')
        grounded_row_ids = request.form.getlist('row-id')
        # print(F"{grounded_groups}")
        # print(F"{len(grounded_row_ids)}")

        # GROUNDLESS RECONSTITUTIONS
        groundless_groups = request.form.getlist('g-less-selected')
        groundless_row_ids = request.form.getlist('row-id-2')
        # print(F"{groundless_groups}")
        # print(F"{groundless_row_ids}")

        # FETCH THE REFERENTS BASED ON THE CLUSTER ID
        referents = func.select_row(db_name=selected_db_name, table='CLUSTERS_TBL', column='id', value=rid)
        referents = ast.literal_eval(referents[1]) if referents is not None else None

        # EXTRACT ALL PERSON IDs CONSTITUTING THIS CLUSTER
        rids = referents['ids']

        if todo == 'write':

            # REGROUP GROUNDED
            for i in range(len(grounded_groups)):
                new_grounded[grounded_groups[i]].add(F"p-{rids[int(grounded_row_ids[i])]}")

            # REGROUP GROUNDLESS
            for i in range(len(groundless_groups)):
                new_groundless[groundless_groups[i]].add(F"p-{rids[int(groundless_row_ids[i])]}")

            # UPDATE grounded_groups WITH groundless_groups
            for key, value in new_groundless.items():
                if key in new_grounded:
                    new_grounded[key].update(value)
                else:
                    new_grounded[key] = value

        elif todo == 'merger-and-write':

            # REGROUP GROUNDED
            for i in range(len(grounded_groups)):
                new_grounded[1].add(F"p-{rids[int(grounded_row_ids[i])]}")

            # REGROUP GROUNDLESS
            for i in range(len(groundless_groups)):
                new_groundless[1].add(F"p-{rids[int(groundless_row_ids[i])]}")

            # UPDATE grounded_groups WITH groundless_groups
            for key, value in new_groundless.items():
                if key in new_grounded:
                    new_grounded[key].update(value)
                else:
                    new_grounded[key] = value

        # CHECK IF THE RECONSTITUTED EXISTS IN THE DATABASE 117162
        fetch_reconstituted = func.select_row(db_name=selected_db_name, table='RESULT_TBL', column='cid',
                                              value=rid)
        if fetch_reconstituted is not None:
            grounded_tables = serialise(fetch_reconstituted['grounded_table'])
            groundless_tables = serialise(fetch_reconstituted['groundless_table'])

            for group, persons in new_grounded.items():
                for person in persons:
                    mappings[person] = group

            for group, observations in grounded_tables.items():
                for observation in observations:
                    tables[mappings[observation['p_ID']]].append(observation)

            # GENERATE A NEW VALIDATED TABLE
            for group, observations in groundless_tables.items():
                for observation in observations:
                    tables[mappings[observation['p_ID']]].append(observation)

            # UPDATE THE RECORD
            func.update(db_name=selected_db_name,
                        cmd=UPDATE['validated_table'].format(validated_table=tables, cid=rid))

        updated = {key: list(value) for key, value in new_grounded.items()}
        formatter, rdf_data = ttl.group_validation2rdf(db_name=selected_db_name, c_id=rid, groups=updated)

        # INSERTING THE RESULT TO THE DB
        check_cmd = F"SELECT cid FROM RDF_MANUAL_VALIDATION_TBL WHERE cid={rid};"
        fetched = F"SELECT validation FROM RDF_MANUAL_VALIDATION_TBL WHERE cid={rid};"
        check = func.check_cmd(db_name=selected_db_name, cmd=check_cmd)

        if check is False:

            print(F"\t- The validation will be inserted")

            # INSERT THE FIRST TOME VALIDATION
            func.insert_row(db_name=selected_db_name, cmd=INSERT['manual_validation'],
                            values=[rid, rand_size, rdf_data])

            # UPDATE RESULT_TBL AS THE CLUSTER HAS BEEN MANUALLY VALIDATED
            func.update(db_name=selected_db_name, cmd=UPDATE['validated'].format(rid))

        else:

            print(F"\t- The validation will be updated\n")

            # FETCH THE ODL VALIDATION
            row = func.select(db_name=selected_db_name, cmd=fetched)
            old_result = row[0]['validation']

            # UPDATE WITH THE CURRENT VALIDATION
            func.update(db_name=selected_db_name, cmd=UPDATE['validation'].format(rdf_data, rid))

            rdf_data = F"\nTHE VALIDATION HAS BEEN MODIFIED FROM\n\n{formatter.format(old_result)}\n\n" \
                       F"TO\n\n{formatter.format(rdf_data)}"

    elif todo == 'view':

        week_date(message="VIEWING MANUAL VALIDATIONS  ")
        validation_cmd = F"SELECT validation FROM RDF_MANUAL_VALIDATION_TBL WHERE cid={rid}"
        data = func.select(db_name=selected_db_name, cmd=validation_cmd)

        if len(data) > 0:
            rdf_data = data[0]['validation']
            print(F"data\n{rdf_data}\n")
            graph = ttl.generate_named_graph(selected_db_name, "Manual-Validation", rdf_data)
            rdf_data = F"\n\n{graph.format(rdf_data)}"

    print(F"\n\t{'TO DO':{PADDING}} : {todo}\n"
          F"\t{'CLUSTER ID':{PADDING}} : {rid}\n"
          F"\t{'occurrence_recon_size':{PADDING}} : {cluster_size}\n")

    data = reconstituted_data(selected_db_name, cid=rid)

    print(F"SUBMITTED VALUES\n"
          F"\t- {'CONSISTENCY ID':{PADDING}} {rid}\n")

    if data['exists'] is False:
        data['html_summary'] = F"<h2 style='text-align: center' ><strong>{data['html_summary']}</strong></h2>"

    # COMPUTING THE FAMILY'S THREAD
    family = family_thread(db_name=selected_db_name, processed=rid)
    validated_family = validated_thread(data['cid'], data['validated_table'], selected_db_name)
    return render_template('consistency.html', response=responses('consistency'), analysis_data=data, family=family,
                           validated_family=validated_family, rdf_data=rdf_data, show='show', selected_size=cluster_size,
                           nightfall=incandescent)


@app.route('/cancel_manual_consistency_validation', methods=['GET', 'POST'])
def cancel_manual_consistency_validation():

    week_date(message="CANCELLING MANUAL VALIDATIONS  ")
    selected_db_name = selected_db()
    cluster_size = request.form.get('cancel_validation_cs')
    rid = request.form.get('cancel_validation_reconstitution_id')
    selected_index = request.form.get("cancel_validation_selected_index")
    cluster_size = int(cluster_size.strip()) if cluster_size is not None else 0

    # data = {'name': '', 'marital_text': '', 'flag': None, 'bads': 0, 'cid': '', 'maybes': 0,
    #         'html_table': '', 'html_summary': '', 'c_size': "", 'grounded_table': dict(),
    #         'groundless_table': dict(), 'validated_table': None}

    # UPDATE RESULT_TBL AS THE CLUSTER HAS BEEN MANUALLY VALIDATED
    print(F"\t- {clr(7, 'UPDATING THE VALIDATION STATUS IN RESULT_TBL.')}")
    func.update(db_name=selected_db_name, cmd=UPDATE['validated_no'].format(rid))

    # UPDATE RESULT_TBL AS THE CLUSTER HAS BEEN MANUALLY VALIDATED
    print(F"\t- {clr(7, F'DELETING THE VALIDATION FOR RECONSTITUTED {rid} FROM RDF_MANUAL_VALIDATION_TBL')}")
    func.update(db_name=selected_db_name, cmd=DELETE['manual_validation'].format(cid=rid))
    func.update(db_name=selected_db_name, cmd=UPDATE['validated_table'].format(validated_table=None, cid=rid))

    print(F"\n{'CLUSTER SIZE':{PADDING}} : {cluster_size}\n"
          F"{'SELECTED INDEX':{PADDING}} : {selected_index}\n")

    # return _analysis_(selected_db_name=selected_db_name, cluster_size=rand_size, pages=pages, previous_page=previous_page,
    #                   next_page=next_page, second_page=second_page, max_page=pages, max_rows=max_r, tbl_idx=selected_index,
    #                   start_from=start_from, show=True, rdf_data='', flag_filter=flag_filter, validated=validated)

    # FETCH DATA ABOUT THE RECONSTITUTED
    # fetch_reconstituted = func.select_row(db_name=selected_db_name, table='RESULT_TBL', column='cid', value=rid)

    # if fetch_reconstituted is not None:
    #
    #     data = {'name': capwords(fetch_reconstituted['name']), 'c_size': fetch_reconstituted['c_size'],
    #             'marital_text': fetch_reconstituted['marital_text'], 'flag': fetch_reconstituted['flag'],
    #             'bads': fetch_reconstituted['bads'], 'cid': fetch_reconstituted['cid'],
    #             'maybes': fetch_reconstituted['maybes'], 'html_summary': fetch_reconstituted['summary'],
    #             'grounded_table': serialise(fetch_reconstituted['grounded_table']),
    #             'groundless_table': serialise(fetch_reconstituted['groundless_table']),
    #             'validated_table': serialise(fetch_reconstituted['validated_table'])}

    data = reconstituted_data(selected_db_name, cid=rid)

    if data['exists'] is False:
        data['html_summary'] = F"<h2 style='text-align: center' ><strong>{data['html_summary']}</strong></h2>"

    # COMPUTING THE FAMILY'S THREAD
    family = family_thread(db_name=selected_db_name, processed=rid)
    validated_family = validated_thread(data['cid'], data['validated_table'], selected_db_name)
    return render_template('consistency.html', response=responses('consistency'), analysis_data=data, family=family,
                           validated_family=validated_family, rdf_data='', show='show', selected_size=cluster_size,
                           nightfall=incandescent)


# ===============================================================================================
#                       EXPORT AUTOMATED ANALYSIS AND MANUAL VALIDATIONS
# ===============================================================================================

# analysis_data['groundless_table']|length != 0  or
#                                     analysis_data['grounded_table']|length != 0


def validations_stats(db_name):

    cmd = F"SELECT COUNT(DISTINCT cid ) FROM RDF_MANUAL_VALIDATION_TBL"
    manual_validations = func.select(db_name=db_name, cmd=cmd)
    manual_validations = formatNumber([col for row in manual_validations for col in row][0], currency='') \
        if manual_validations is not None and len(manual_validations) > 0 else 0

    cmd = F"SELECT COUNT(DISTINCT cid ) FROM RESULT_TBL"
    automated_validations = func.select(db_name=db_name, cmd=cmd)
    automated_validations = formatNumber([col for row in automated_validations for col in row][0], currency='') \
        if automated_validations is not None and len(automated_validations) > 0 else 0

    return automated_validations, manual_validations


@app.route('/write_manual_validation', methods=['GET', 'POST'])
def write_manual_validation():

    rdf_data = ''
    mappings = dict()
    tables = defaultdict(list)
    new_grounded = defaultdict(set)
    new_groundless = defaultdict(set)
    selected_db_name = selected_db()

    flag_filter = request.form.get('nxt_tbl_idx_filter')
    validated = request.form.get('write_validated_rdf')
    todo = request.form.get('rdf')

    # RECONSTITUTION ID
    rid = request.form.get('reconstitution-id')
    selected_index = request.form.get("occurrence_index")

    next_page = request.form.get('write_validated_next_page')
    print(F"next_page: {next_page}")
    next_page = int(next_page) if next_page is not None else 2
    curr_page = next_page - 1 if next_page is not None else 1
    curr_page = curr_page if curr_page > 0 else 1

    cluster_size = request.form.get('occurrence_recon_size')
    cluster_size = int(cluster_size.strip()) if cluster_size is not None else 0

    state = get_state(db_name=selected_db_name)
    max_rows = request.form.get('occurrence_recon_table_limit')
    max_rows = par.MAX_TABLE_ROWS if max_rows is None else int(max_rows)
    rand_size = random_size() if cluster_size == 0 else cluster_size

    start_from = max_rows * curr_page - max_rows
    start_from = start_from if start_from >= 0 else 0
    previous_page = curr_page if curr_page > 0 else 1
    second_page = previous_page + 1
    pages = nbr_of_pages(selected_db_name, rand_size, flag_filter, validated, max_rows)

    if todo == 'write' or todo == 'merger-and-write':

        week_date(message="WRITING MANUAL VALIDATIONS  ")

        # GROUND RECONSTITUTIONS
        grounded_groups = request.form.getlist('g_selected')
        grounded_row_ids = request.form.getlist('row-id')
        # print(F"grounded_groups {grounded_groups}")
        # print(F"grounded_row_ids {grounded_row_ids}")

        # GROUNDLESS RECONSTITUTIONS
        groundless_groups = request.form.getlist('g-less-selected')
        groundless_row_ids = request.form.getlist('row-id-2')
        # print(F"groundless_groups {groundless_groups}")
        # print(F"groundless_row_ids {groundless_row_ids}")

        # FETCH THE REFERENTS BASED ON THE CLUSTER ID
        referents = func.select_row(db_name=selected_db_name, table='CLUSTERS_TBL', column='id', value=rid)
        referents = ast.literal_eval(referents[1]) if referents is not None else None

        # EXTRACT ALL PERSON IDs CONSTITUTING THIS CLUSTER
        rids = referents['ids']

        if todo == 'write':

            # REGROUP GROUNDED
            for i in range(len(grounded_groups)):
                new_grounded[grounded_groups[i]].add(F"p-{rids[int(grounded_row_ids[i])]}")

            # REGROUP GROUNDLESS
            for i in range(len(groundless_groups)):
                new_groundless[groundless_groups[i]].add(F"p-{rids[int(groundless_row_ids[i])]}")

            # UPDATE grounded_groups WITH groundless_groups
            for key, value in new_groundless.items():
                if key in new_grounded:
                    new_grounded[key].update(value)
                else:
                    new_grounded[key] = value

        elif todo == 'merger-and-write':

            # REGROUP GROUNDED
            for i in range(len(grounded_groups)):
                new_grounded[1].add(F"p-{rids[int(grounded_row_ids[i])]}")

            # REGROUP GROUNDLESS
            for i in range(len(groundless_groups)):
                new_groundless[1].add(F"p-{rids[int(groundless_row_ids[i])]}")

            # UPDATE grounded_groups WITH groundless_groups
            for key, value in new_groundless.items():
                if key in new_grounded:
                    new_grounded[key].update(value)
                else:
                    new_grounded[key] = value

        # CHECK IF THE RECONSTITUTED EXISTS IN THE DATABASE 117162
        fetch_reconstituted = func.select_row(db_name=selected_db_name, table='RESULT_TBL', column='cid', value=rid)

        # THE RECONSTITUTION EXISTS
        if fetch_reconstituted is not None:

            grounded_tables = serialise(fetch_reconstituted['grounded_table'])
            groundless_tables = serialise(fetch_reconstituted['groundless_table'])

            # ASSIGN A PERSON TO ITS USER DEFINE GROUP
            for group, persons in new_grounded.items():
                for person in persons:
                    mappings[person] = group

            # CREATE NEW TABLE FOR EACH GROUP BASE ON THE GROUNDED GROUPS
            for group, observations in grounded_tables.items():
                for observation in observations:
                    tables[mappings[observation['p_ID']]].append(observation)

            # GENERATE A NEW VALIDATED TABLE BASE ON THE GROUNDLESS GROUPS
            for group, observations in groundless_tables.items():
                for observation in observations:
                    tables[mappings[observation['p_ID']]].append(observation)

            # UPDATE THE RECORD
            func.update(db_name=selected_db_name,
                        cmd=UPDATE['validated_table'].format(validated_table=tables, cid=rid))

        updated = {key: list(value) for key, value in new_grounded.items()}
        formatter, rdf_data = ttl.group_validation2rdf(db_name=selected_db_name, c_id=rid, groups=updated)

        # INSERTING THE RESULT INTO THE DB
        check_cmd = F"SELECT cid FROM RDF_MANUAL_VALIDATION_TBL WHERE cid={rid};"
        fetched = F"SELECT validation FROM RDF_MANUAL_VALIDATION_TBL WHERE cid={rid};"
        check = func.check_cmd(db_name=selected_db_name, cmd=check_cmd)

        if check is False:

            print(F"\t- The validation will be inserted")

            # INSERT THE VALIDATION
            func.insert_row(db_name=selected_db_name, cmd=INSERT['manual_validation'], values=[rid, rand_size, rdf_data])

            # UPDATE RESULT_TBL AS THE CLUSTER HAS BEEN MANUALLY VALIDATED
            func.update(db_name=selected_db_name, cmd=UPDATE['validated'].format(rid))

        else:

            print(F"\t- The validation will be updated\n")

            # FETCH THE ODL VALIDATION
            row = func.select(db_name=selected_db_name, cmd=fetched)
            old_result = row[0]['validation']

            # UPDATE WITH THE CURRENT VALIDATION
            func.update(db_name=selected_db_name, cmd=UPDATE['validation'].format(rdf_data, rid))

            rdf_data = F"\nTHE VALIDATION HAS BEEN MODIFIED FROM\n\n{formatter.format(old_result)}\n\n" \
                  F"TO\n\n{formatter.format(rdf_data)}"

    elif todo == 'view':

        week_date(message="VIEWING MANUAL VALIDATIONS  ")
        validation_cmd = F"SELECT validation FROM RDF_MANUAL_VALIDATION_TBL WHERE cid={rid}"
        data = func.select(db_name=selected_db_name, cmd=validation_cmd)

        if len(data) > 0:
            rdf_data = data[0]['validation']
            print(F"data\n{rdf_data}\n")
            graph = ttl.generate_named_graph(selected_db_name, "Manual-Validation", rdf_data)
            rdf_data = F"\n\n{graph.format(rdf_data)}"

    print(F"\n\t{'TO DO':{PADDING}} : {todo}\n"
          F"\t{'Flag Filter':{PADDING}} : {flag_filter}\n"
          F"\t{'CLUSTER ID':{PADDING}} : {rid}\n"
          F"\t{'selected_index':{PADDING}} : {selected_index}\n"
          F"\t{'occurrence_recon_size':{PADDING}} : {cluster_size}\n"
          F"\t{'Previous Page':{PADDING}} : {previous_page}\n"
          F"\t{'Next page':{PADDING}} : {next_page}\n")

    return _analysis_(selected_db_name=selected_db_name, cluster_size=rand_size, pages=pages, flag_filter=flag_filter,
                      validated=validated, previous_page=previous_page, next_page=next_page, second_page=second_page,
                      max_page=pages, max_rows=max_rows, tbl_idx=selected_index, start_from=start_from, show=True,
                      rdf_data=rdf_data, hide_table=state['hide_table'])


@app.route('/cancel_manual_validation', methods=['GET', 'POST'])
def cancel_manual_validation():

    week_date(message="CANCELLING MANUAL VALIDATIONS  ")
    selected_db_name = selected_db()

    state = get_state(db_name=selected_db_name)
    max_r = par.MAX_TABLE_ROWS if state['table_limit'] is None or len(str(state['table_limit'])) == 0 else state['table_limit']

    validated = request.form.get('cancel_validated_rdf')
    cluster_size = request.form.get('cancel_validation_cs')
    next_page = request.form.get('cancel_validation_next_page')
    rid = request.form.get('cancel_validation_reconstitution_id')
    flag_filter = request.form.get('cancel_validation_flag_filter')
    selected_index = request.form.get("cancel_validation_selected_index")

    state = get_state(db_name=selected_db_name)

    print(state['hide_table'])

    #     state = get_state(db_name=selected_db_name)
    #     if state['cluster_size'] > 0 and table_analysis_btn is None:
    #
    #         print("USING THE SATE\n")
    #         pages = state['max_pages']
    #         flag_filter = state['filter']
    #         row_index = state['table_row']
    #         validated = state['validated']
    #         next_page = state['current_page']
    #         cluster_size = state['cluster_size']
    #         hide_table = state['hide_table']
    #         max_rows = state['table_limit']
    #         previous_page = next_page
    #         second_page = previous_page + 1
    #         rand_size = cluster_size
    #         next_page += 1
    #
    #         start_from = max_rows * previous_page - max_rows
    #         start_from = start_from if start_from >= 0 else 0

    cluster_size = int(cluster_size.strip()) if cluster_size is not None else 0
    rand_size = random_size() if cluster_size == 0 else cluster_size

    next_page = int(next_page) if next_page is not None else 2
    curr_page = next_page - 1 if next_page is not None else 1
    curr_page = curr_page if curr_page > 0 else 1

    start_from = max_r * curr_page - max_r
    start_from = start_from if start_from >= 0 else 0

    previous_page = curr_page if curr_page > 0 else 1
    second_page = previous_page + 1
    pages = nbr_of_pages(selected_db_name, rand_size, flag_filter, validated, max_r)

    # UPDATE RESULT_TBL AS THE CLUSTER HAS BEEN MANUALLY VALIDATED
    print(F"\t- {clr(7, 'UPDATING THE VALIDATION STATUS IN RESULT_TBL.')}")
    func.update(db_name=selected_db_name, cmd=UPDATE['validated_no'].format(rid))

    # UPDATE RESULT_TBL AS THE CLUSTER HAS BEEN MANUALLY VALIDATED
    print(F"\t- {clr(7, F'DELETING THE VALIDATION FOR RECONSTITUTED {rid} FROM RDF_MANUAL_VALIDATION_TBL')}")
    func.update(db_name=selected_db_name, cmd=DELETE['manual_validation'].format(cid=rid))
    func.update(db_name=selected_db_name, cmd=UPDATE['validated_table'].format(validated_table=None, cid=rid))

    print(F"\n{'CLUSTER SIZE':{PADDING}} : {cluster_size}\n"
          F"{'SELECTED INDEX':{PADDING}} : {selected_index}\n")

    return _analysis_(selected_db_name=selected_db_name, cluster_size=rand_size, pages=pages, previous_page=previous_page,
                      next_page=next_page, second_page=second_page, max_page=pages, max_rows=max_r, tbl_idx=selected_index,
                      start_from=start_from, show=True, rdf_data='', flag_filter=flag_filter, validated=validated,
                      hide_table=state['hide_table'])


@app.route('/export')
def export():

    week_date(message="EXPORT  ")

    selected_db_name = selected_db()

    # GENERATE THE PROCESSED RECONSTITUTED SIZES
    table, selected_size_all, processed_reconstitutions_all, processed_sizes_all = available_full_size(
        selected_db_name, size=None)

    # VALIDATIONS STATISTICS
    automated_validations, manual_validations = validations_stats(selected_db_name)

    folder = Path(TRIPLE_FOLDER)
    curr_triple_files = [folder / str(f) for f in listdir(folder)
                         if str(f).split('.')[0].startswith(selected_db()) and str(f).split('.')[1] == 'ttl']

    # GENERIC RESPONSE
    response = responses('export')
    response['processed_sizes'] = processed_sizes_all
    response['processed_reconstitutions_all'] = len(processed_reconstitutions_all)
    response['relations_path'] = curr_triple_files[0] if len(curr_triple_files) > 0 else None

    print(F"{'MANUAL VALIDATIONS':{PADDING}} : {manual_validations}\n"
          F"{'AUTOMATED VALIDATIONS':{PADDING}} : {automated_validations}\n"
          F"{'PROCESSED RECONSTITUTIONS':{PADDING}} : {len(processed_reconstitutions_all)}\n"
          F"{'PROCESSED SIZES':{PADDING}} : {processed_sizes_all}\n"
          F"{'RELATIONS FILE':{PADDING}} : {curr_triple_files[0] if len(curr_triple_files) > 0 else None}\n")

    return render_template('export.html', response=response,
                           automated_validations=automated_validations, manual_validations=manual_validations)


def export_automated_validations_file(db_name, cluster_size):

    # CONTINUE BECAUSE THE SUBMITTED SIZE HAS INDEED BEEN PROCESSED
    val_folder = Path(F"{par.rdf_folder}")
    stat_folder = Path(F"{par.rdf_folder}")

    # MAKE SURE THE FOLDER EXISTS
    if exists(val_folder) is False:
        mkdir(val_folder)
    if exists(stat_folder) is False:
        mkdir(stat_folder)

    # SELECT ALL CLUSTER IDs STEMMED FROM THE SUBMITTED SIZE
    cmd = F"SELECT c_size, cid, rdf_data FROM RESULT_TBL WHERE c_size={cluster_size}"
    referent_results = func.select(db_name=db_name, cmd=cmd)
    print(F"\t- {F'Clusters Found for size {cluster_size}':{PADDING}} : {len(referent_results)}")

    with open(val_folder / F"{db_name}-validation-{cluster_size}.trig", "w", encoding="utf-8") as validation_file:
        with open(stat_folder / F"{db_name}-statistics-{cluster_size}.trig", "w", encoding="utf-8") as stats_file:

            # INITIALIZE THE STAT GRAPH
            stats_file.write(ttl.prefixes())
            stats_file.write(F'\n{par.reconstitution_set.format(db_name)}\n{{')

            # INITIALIZE THE VALIDATION GRAPH
            validation_file.write(ttl.prefixes())
            validation_file.write(F'\n{par.validation_set.format(db_name)}\n{{')
            validation_file.write(ttl.heuristic())

            count = 0
            for row in referent_results:
                # for key, value in serialise(row['rdf_data']).items():
                #     print(F"{key:>55} : {value}")
                # print("\n")
                count += 1
                ttl.convert2ttl(serialise(row['rdf_data']), count=count, stats=stats_file, checks=validation_file)

            stats_file.write('}')
            validation_file.write('}')


def export_automated_validations(db_name, cluster_size):

    count = 0
    file = Buffer()

    # CONTINUE BECAUSE THE SUBMITTED SIZE HAS INDEED BEEN PROCESSED
    val_folder = Path(F"{par.rdf_folder}")
    stat_folder = Path(F"{par.rdf_folder}")

    # MAKE SURE THE FOLDER EXISTS
    if exists(val_folder) is False:
        mkdir(val_folder)
    if exists(stat_folder) is False:
        mkdir(stat_folder)

    # SELECT ALL CLUSTER IDs STEMMED FROM THE SUBMITTED SIZE
    cmd = F"SELECT c_size, cid, rdf_data FROM RESULT_TBL WHERE c_size={cluster_size}"
    referent_results = func.select(db_name=db_name, cmd=cmd)
    print(F"\t- {F'Clusters Found for size {cluster_size}':{PADDING}} : {len(referent_results)}")

    for row in referent_results:
        # for key, value in serialise(row['rdf_data']).items():
        #     print(F"{key:>55} : {value}")
        # print("\n")
        count += 1
        file.write(ttl.convert2ttl(serialise(row['rdf_data']), count=count))

    return file.getvalue()


@app.route('/export_automated_validation_group', methods=['GET', 'POST'])
def export_automated_validation_group():

    db_name = selected_db()
    c_size = request.form.get('c_size')
    c_size = int(c_size) if c_size.isdigit() else 0

    week_date(message=F"EXPORT A RECONSTITUTED OF SIZE {c_size}")

    # GENERATE THE PROCESSED RECONSTITUTED SIZES
    table, selected_size_all, processed_reconstitutions_all, processed_sizes_all = available_full_size(db_name, size=None)
    processed_sizes = convert_list_summary2list(processed_sizes_all)
    size_ok = c_size in processed_sizes

    def gen():

        if size_ok is True:

            print(F"\t- {'Processed Sizes':{PADDING}} : {processed_sizes_all}\n"
                  F"\t- {'Submitted Size':{PADDING}} : {c_size} {'❌' if size_ok is False else '✔'}")

            # INITIALIZE THE VALIDATION GRAPH
            file = Buffer()
            file.write(ttl.prefixes())
            file.write(F'\n{par.validation_set.format(db_name)}\n{{')
            file.write(ttl.heuristic())
            yield file.getvalue()

            # GENERATE THE RDF-GRAPH FILE
            yield export_automated_validations(db_name, c_size)

            yield '\n}'

        else:
            c = Coloring()
            print(c.colored(7, F"The requested size has not been processed yet"))

    if size_ok is True:
        return Response(gen(), mimetype='application/.trig')

    # return Response(status=204)
    response = responses('export')
    response['c_size'] = c_size
    response['processed_sizes'] = processed_sizes_all
    automated_validations, manual_validations = validations_stats(db_name)
    return render_template('export.html', response=response, error=F"The requested size has not been processed yet",
                           automated_validations=automated_validations, manual_validations=manual_validations)


@app.route('/export_all_automated_validations', methods=['GET', 'POST'])
def export_all_automated_validations():

    week_date(message=F"EXPORT ALL RECONSTITUTIONS ")
    db_name = selected_db()

    # GENERATE THE PROCESSED RECONSTITUTED SIZES
    table, selected_size_all, processed_reconstitutions_all, processed_sizes_all = available_full_size(db_name, size=None)
    processed_sizes = convert_list_summary2list(processed_sizes_all)
    print(F"\t- {'Processed Sizes' :{PADDING}} : {processed_sizes_all}")

    # EXPORTING
    def gen():

        # INITIALIZE THE VALIDATION GRAPH
        file = Buffer()
        file.write(ttl.prefixes())
        file.write(F'\n{par.validation_set.format(db_name)}\n{{')
        file.write(ttl.heuristic())
        yield file.getvalue()

        for c_size in processed_sizes:
            yield "".join(export_automated_validations(db_name, c_size))

        yield '\n}'

    return Response(gen(), mimetype='application/.trig')


@app.route('/export_manual_validations', methods=['GET', 'POST'])
def export_manual_validations():

    week_date(message=F"EXPORT ALL MANUALLY RECONSTITUTIONS ")
    db_name = selected_db()
    table, selected_size_all, processed_reconstitutions_all, processed_sizes_all = available_full_size(db_name, size=None)
    response = responses('export')
    response['processed_sizes'] = processed_sizes_all

    cmd = F"SELECT validation FROM RDF_MANUAL_VALIDATION_TBL"
    mnl_validations = func.select(db_name=db_name, cmd=cmd)
    mnl_validations = "".join(col for row in mnl_validations for col in row)

    print(F"EXPORTING THE MANUAL VALIDATIONS")

    def gen():

        graph = ttl.generate_named_graph(db_name=db_name, extra="Manual-Validation", rdf_text=mnl_validations)
        yield F"{graph} {{"

        for row in mnl_validations:
            for col in row:
                yield col

        yield "\n}"

    return Response(gen(), mimetype='application/.trig')


@app.route('/export_relations', methods=['GET', 'POST'])
def export_relations():

    week_date(message=F"EXPORT RELATIONS ")
    path = request.form.get('relations-file')
    print(F"{'RELATIONS FILE':{PADDING}} : {path}\n")

    def gen():
        if path is not None:
            with open(str(path).strip(), 'r', encoding='utf-8') as file:
                for triple in file:
                    yield triple
        else:
            yield ''

    if path is not None:
        return Response(gen(), mimetype='application/.ttl')


@app.route('/batch_validations', methods=['GET', 'POST'])
def batch_validations():

    # GET ALL RECONSTITUTION OF THE SPECIFIED SIZE
    # STATE INPUT
    rdf = ''
    sample_size = 10
    rdf_buffer = Buffer()
    db_name = selected_db()

    state = get_state(db_name=db_name)
    batch_validation_task = request.form.get("Batch-Validation-Task")
    batch_validation_flag_filter = request.form.get("Batch-Filter-Flags")
    batch_validation_size = request.form.get("Batch-Filter-Size")

    # flag_filter = request.form.get('flexRadioDefault-val')
    processed_sizes = request.form.get("validation_processed_sizes")
    selected_index = request.form.get("validation_occurrence_index")
    cluster_sz = request.form.get('validation_cluster_size').strip()
    table_limit = request.form.get("validation_cluster_table_limit")
    table_limit = par.MAX_TABLE_ROWS if table_limit is None else int(table_limit)

    week_date(message=F"VALIDATIONS FOR SIZE {cluster_sz}  ")

    flag_filter = "ignore" if batch_validation_flag_filter is None else batch_validation_flag_filter
    cluster_sz = int(cluster_sz.strip()) if len(cluster_sz) != 0 and cluster_sz is not None else 0

    next_page = 1
    curr_page = next_page
    rand_size = random_size() if cluster_sz == 0 else cluster_sz
    start_from = 0

    hide_table = state['hide_table']
    previous_page = curr_page
    second_page = previous_page + 1

    maybes = ' AND maybes>0' if flag_filter == "Likely" else (' AND maybes=0' if flag_filter == 'Likely-Star' else '')
    temp_flag_filter = flag_filter.replace("-Star", '') if flag_filter.__contains__("-Star") else flag_filter
    temp_flag_filter = '' if temp_flag_filter == 'All' or len(temp_flag_filter) == 0 else F" AND flag='{temp_flag_filter}'"

    def one_validation(cluster_size):

        rdf_data, idx = '', 0
        constraint = F"c_size={cluster_size}{temp_flag_filter}{maybes}"
        cmd = F"SELECT cid, grounded_table, groundless_table FROM RESULT_TBL WHERE {constraint}"
        reconstitutions = func.select(db_name=db_name, cmd=cmd)
        cluster_ids = [[row['cid'], row['grounded_table'], row['groundless_table']]
                       for row in reconstitutions] if len(reconstitutions) > 0 else []
        print(F"\t- {'DATA ROWS RESULTS':{PADDING}} : {len(cluster_ids)}\n")

        insert_values, c_ids = [], []

        # VALIDATING THE FETCHED CLUSTER IDS
        for [cid, grounded_table, groundless_table] in cluster_ids:
            grounded_table = serialise(grounded_table)
            groundless_table = serialise(groundless_table)

            new_grounded = defaultdict(set)
            new_groundless = defaultdict(set)

            # for key, val in grounded_table.items():
            #     print(cid, key, val)

            # FETCH THE REFERENTS BASED ON THE CLUSTER ID
            referents = func.select_row(db_name=db_name, table='CLUSTERS_TBL', column='id', value=cid)
            referents = ast.literal_eval(referents[1]) if referents is not None else None
            person_ids = referents['ids']

            # REGROUP GROUNDED
            for idx, data in grounded_table.items():
                for values in data:
                    new_grounded[idx].add(F"p-{person_ids[int(values['rid'])]}")

            # REGROUP GROUNDLESS
            for idx, data in groundless_table.items():
                for values in data:
                    new_groundless[len(grounded_table) + int(values['rid'])].add(F"p-{person_ids[int(values['rid'])]}")

            # UPDATE grounded_groups WITH groundless_groups
            for key, value in new_groundless.items():
                if key in new_grounded:
                    new_grounded[key].update(value)
                else:
                    new_grounded[key] = value

            updated = {key: list(value) for key, value in new_grounded.items()}
            formatter, rdf_data = ttl.group_validation2rdf(db_name=db_name, c_id=cid, groups=updated)
            if idx <= sample_size:
                rdf_buffer.write(F"{rdf_data}\n")
                idx += 1

            # INSERTING THE RESULT TO THE DB
            check_cmd = F"SELECT cid FROM RDF_MANUAL_VALIDATION_TBL WHERE cid={cid};"
            fetched = F"SELECT validation FROM RDF_MANUAL_VALIDATION_TBL WHERE cid={cid};"
            check = func.check_cmd(db_name=db_name, cmd=check_cmd)

            # NEW INSERTION
            if check is False:

                # GATHER INSERTION VALUES
                insert_values.append((cid, cluster_size, rdf_data))

                # GATHER CLUSTER IDS TO UPDATE
                c_ids.append(cid)
                func.update(db_name=db_name, cmd=UPDATE['validated'].format(cid))

            # AN UPDATE
            else:

                print(F"\t- The validation will be updated")

                # FETCH THE ODL VALIDATION
                row = func.select(db_name=db_name, cmd=fetched)
                old_result = row[0]['validation']

                # UPDATE WITH THE CURRENT VALIDATION
                func.update(db_name=db_name, cmd=UPDATE['validation'].format(rdf_data, cid))

                rdf_data = F"\nTHE VALIDATION HAS BEEN MODIFIED FROM\n\n{formatter.format(old_result)}\n\n" \
                      F"TO\n\n{formatter.format(rdf_data)}"

        # INSERT THE VALIDATION FOR THE FIRST TIME
        if len(insert_values) > 0:

            # GATHER INSERTION VALUES
            print(F"\t- The validation will be inserted")
            func.insert_many(db_name=db_name, cmd=INSERT['manual_validation'], values=insert_values)

            # UPDATE RESULT_TBL AS THE CLUSTER HAS BEEN MANUALLY VALIDATED
            ids = ', '.join(str(c_id) for c_id in c_ids)

            func.update(db_name=db_name, cmd=UPDATE['validated_set'].format(ids))
            rdf_data = rdf_buffer.getvalue()

        return rdf_data

    validated = 'ignore'
    if batch_validation_task == "validate":
        validated = 'yes'
        if batch_validation_size == "current-size":
            print("validate current size")
            rdf = one_validation(cluster_size=cluster_sz)

        elif batch_validation_size == "all-sizes":
            print("validate current size")
            pro_sizes = convert_list_summary2list(processed_sizes)
            for c_size in pro_sizes:
                rdf = one_validation(cluster_size=c_size)

    elif batch_validation_task == "reset":
        validated = 'ignore'
        if batch_validation_size == "current-size":
            print("reset current size")
            delete_insertions(db_name, flag_filter, cluster_sz)

        elif batch_validation_size == "all-sizes":
            print("reset all sizes")
            pro_sizes = convert_list_summary2list(processed_sizes)
            for c_size in pro_sizes:
                delete_insertions(db_name, flag_filter, c_size)

    pages = nbr_of_pages(db_name, rand_size, flag_filter, validated, table_limit)

    # STATE UPDATE
    state = {'cluster_size': cluster_sz, 'max_pages': pages, 'current_page': previous_page, 'table_row': selected_index,
             'table_limit': table_limit, 'filter': flag_filter, 'validated': validated, "hide_table": hide_table}
    update_state(db_name=db_name, state=state)

    print(F"\t- {'Batch Validation Task':{PADDING}} : {batch_validation_task}\n"
          F"\t- {'Batch Validation Flag  Filter':{PADDING}} : {batch_validation_flag_filter}\n"
          F"\t- {'Batch Validation Size  Filter':{PADDING}} : {batch_validation_size}\n"
          F"\t- {'Batch Validation Cluster Size':{PADDING}} : {cluster_sz}\n"
          F"\t- {'Pages':{PADDING}} : {pages}\n")

    print(F"\nSUBMITTED VALUES\n\n"
          F"\t- {'FILTERS':{PADDING}} : {flag_filter}\n"
          F"\t- {'CLUSTER SIZE':{PADDING}} : {cluster_sz}\n"
          F"\t- {'LIMIT':{PADDING}} : {table_limit}\n"
          F"\t- {'SELECTED INDEX':{PADDING}} : {selected_index}\n"
          F"\t- {'PROCESSED SIZES':{PADDING}} : {processed_sizes}")

    return _analysis_(selected_db_name=db_name, cluster_size=rand_size, pages=pages, flag_filter=flag_filter,
                      validated=validated, previous_page=previous_page, next_page=next_page, second_page=second_page,
                      max_page=pages, max_rows=table_limit, tbl_idx=selected_index, start_from=start_from, show=True,
                      rdf_data=rdf,  hide_table=hide_table)


def delete_insertions(db_name, flag_filter, cluster_size):

    maybes = ' AND maybes>0' if flag_filter == "Likely" else (' AND maybes=0' if flag_filter == 'Likely-Star' else '')
    temp_flag_filter = flag_filter.replace("-Star", '') if flag_filter.__contains__("-Star") else flag_filter
    temp_flag_filter = '' if temp_flag_filter == 'All' or len(
        temp_flag_filter) == 0 else F" AND flag='{temp_flag_filter}'"
    constraint = F"c_size={cluster_size}{temp_flag_filter}{maybes}"

    print(F"\nRESETTING THE VALIDATIONS FOR SIZE {cluster_size}\n\n\t- {'CONSTRAINT':{PADDING}} : {constraint}")

    cmd = F"SELECT cid, grounded_table, groundless_table FROM RESULT_TBL WHERE {constraint}"
    reconstitutions = func.select(db_name=db_name, cmd=cmd)
    cluster_ids = [row['cid'] for row in reconstitutions] if len(reconstitutions) > 0 else []
    ids = ', '.join(str(identifier) for identifier in cluster_ids)
    delete_cmd = F"DELETE FROM RDF_MANUAL_VALIDATION_TBL WHERE cid IN ({ids}) ;"
    func.delete_row(db_name=db_name, cmd=delete_cmd)
    func.update(db_name=db_name, cmd=UPDATE['validated_no_sel'].format(ids))

    print(F"\t- {F'UPDATED ROWS':{PADDING}} : {len(cluster_ids)}\n")


if __name__ == '__main__':

    from multiprocessing import Process
    server = Process(target=app.run)

    # app.run(host='0.0.0.0', port=3000)
    # shared
    if len(func.db_tables(db_name='shared')) == 0:
        initiate_shared()

    app.run(debug=True)

    server.start()
    server.terminate()
    server.join()


# ==================================================================================================
#
# Go to System Preferences → Sharing → Untick Airplay Receiver.
# export FLASK_APP=/Users/al/PycharmProjects/Clariah/Conda/C2RC/src/main
# export FLASK_ENV=development
# export FLASK_DEBUG=on
# flask run OR flask run -p 5001
#
# docker build --tag c2rv-python-docker .
# docker run --publish 5000:5000 c2rv-python-docker
#
# SQLITE :           https://www.sqlitetutorial.net/sqlite-alter-table/
# BOOTSTRAP :        https://getbootstrap.com/docs/5.3/components/accordion/
# FLASK TEMPLATE :   https://www.digitalocean.com/community/tutorials/how-to-use-templates-in-a-flask-application
# https://developer.mozilla.org/en-US/docs/Web/CSS/font-size
# https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/file
# https://medium.com/fintechexplained/running-python-in-docker-container-58cda726d574
# https://www.w3schools.com/howto/howto_css_center_button.asp

#
# https://www.howtogeek.com/devops/how-to-run-gui-applications-in-a-docker-container/
# https://github.com/docker/awesome-compose/tree/master/flask
# https://realpython.com/python-pathlib/
#

# https://www.w3schools.com/cssref/css3_pr_text-justify.php
# https://www.tutorialspoint.com/sqlite/sqlite_and_or_clauses.htm
# https://developer.mozilla.org/en-US/docs/Web/HTML/Element/strong
#
# ==================================================================================================
