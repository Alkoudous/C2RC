import sqlite3
from src.general.utils import formatNumber
from src.general.colored_text import Coloring
from werkzeug.exceptions import abort

color = Coloring().colored
input_tbl = 'civ_inputs'
input_files_tbl = 'input_files'

database = 'DATABASE_TBL'
events = 'EVENTS_TBL'
person = 'PERSON_TBL'
referents = 'CLUSTERS_TBL'
association_list = 'ASSOCIATION_DICT_TBL'
association_dict = 'ASSOCIATION_DICT_TBL'

qry_all = 'SELECT * FROM {}'
qry_all_from_input_tbl = F'SELECT * FROM {input_files_tbl}'
qry_id_from_input_tbl = F'SELECT * FROM {input_files_tbl} WHERE description = ?'
insert_dict_cmd = "INSERT INTO {} (id, serialised) VALUES (?, ?)"

db_path = './web/db/databases/{}.db'


def connect(db_name):

    if db_name == "None":
        return None

    # print(db_path.format(db_name))
    conn = sqlite3.connect(db_path.format(db_name))
    conn.row_factory = sqlite3.Row

    return conn


def get_database(db_name):

    if db_name == "None":
        return None

    conn = connect(db_name)

    try:
        # print(db_name)
        data = conn.execute(qry_all.format(database)).fetchall()
        conn.commit()
        conn.close()
        if data is None:
            abort(404)
        return data
    except Exception as err:
        print(F"\t- [DB:{db_name}] {err}")
        conn.close()
        pass


def get_datasets(db_name):

    if db_name == "None":
        return None

    conn = connect(db_name)

    try:
        data = conn.execute(qry_all_from_input_tbl).fetchall()
        conn.commit()
        conn.close()
        if data is None:
            abort(404)
        return data

    except Exception as err:
        print(F"\t- {input_files_tbl} {err}")
        conn.close()
        pass

    return []


def get_file(db_name, file_name):

    if db_name == "None":
        return None

    conn = connect(db_name)

    data = conn.execute(qry_id_from_input_tbl, (file_name,)).fetchone()
    conn.commit()
    conn.close()
    if data is None:
        abort(404)
    return data


def get_rows(db_name, table):

    if db_name == "None":
        return None

    conn = connect(db_name)
    data = conn.execute(qry_all.format(table)).fetchall()
    conn.commit()
    conn.close()
    if data is None:
        abort(404)

    return data


def rows_count(db_name, table):
    return formatNumber(get_rows(db_name, table), currency='')


def select_row(db_name, table, column, value):

    row = None
    value = [value]

    if db_name is None or db_name == "None":
        return None

    conn = connect(db_name)

    try:
        cmd = F'SELECT * FROM {table} WHERE {column} = ?'
        # print(db_name, cmd, value)
        row = conn.execute(cmd, value).fetchone()
        conn.commit()
        conn.close()

    except Exception as err:
        print(F"ERROR: \t- {table} {err}")
        conn.close()
        pass

    # print(F"ROW----- {table}", row[0])

    return row


def select_rows(db_name, table, selected_col=None):

    row = None
    if selected_col is None:
        selected_col = "*"
    if db_name == "None" or db_name is None:
        return None

    conn = connect(db_name)

    try:
        cmd = F'SELECT {selected_col} FROM {table}'
        # print(F" {cmd}")
        row = conn.execute(cmd).fetchall()
        conn.commit()
        conn.close()

    except Exception as err:
        print(F"ERROR: \t- {table} {err}")
        conn.close()
        pass

    return row


def select(db_name, cmd):

    row = None
    if db_name == "None" or db_name is None:
        return None

    conn = connect(db_name)

    try:
        # print(cmd)
        row = conn.execute(cmd).fetchall()
        conn.commit()
        conn.close()

    except Exception as err:
        print(F"ERROR: \t- {cmd} {err}\n")
        conn.close()
        pass

    return row


def select_last_row(db_name, table, column):

    row = None
    # print("SELECT LAST ROW")
    if db_name == "None":
        return None

    conn = connect(db_name)

    try:
        cmd = F"SELECT * FROM {table} WHERE {column} = (SELECT MAX({column}) FROM {table})"
        # cmd = F"SELECT * FROM {table} WHERE  ID = 2"
        # print(cmd)
        row = conn.execute(cmd).fetchone()
        # print(F"""{" | ".join(str(col) for col in row)}""")
        conn.commit()
        conn.close()

    except Exception as err:
        print(F"ERROR: \t- {table} {err}")
        conn.close()
        pass

    # print(F"ROW----- {table}", row[0])

    return row


def convert_row(db_name, table, column, value):

    row = None
    value = [value]
    if db_name == "None":
        return None
    conn = connect(db_name)

    try:
        row = conn.execute(F'SELECT * FROM {table} WHERE {column} = ?', value).fetchone()
        conn.commit()
        conn.close()

    except Exception as err:
        print(F"\t- {table} {err}")
        conn.close()
        pass

    # print(F"ROW----- {table}", row)
    return row


def insert_row(db_name, cmd, values):

    # print(db_name)
    if db_name == "None":
        return None
    conn = connect(db_name)

    try:
        # print(cmd, values)
        cur = conn.cursor()
        cur.execute(cmd, values)
        conn.commit()
        conn.close()
        print(color(7, F"\t- The row has been successfully inserted"))

    except Exception as err:
        print(F"\t  ERROR ==> {color(7, err)}")
        conn.close()
        pass


def insert_rows(db_name, cmd, values):

    # print(color(7, F"\n\t- Importing cmd: {cmd}\n\t- Importing values: {len(values[0])}"))
    if db_name == "None":
        return None

    conn = connect(db_name)

    try:
        cur = conn.cursor()
        cur.executemany(cmd, values)
        conn.commit()
        conn.close()
        rows = len(values)
        print(color(7, F"\n\t- {formatNumber(rows, currency='')} rows {'has' if rows < 2 else 'have'} "
                       F"been successfully inserted.\n"))
        return rows
    except Exception as err:
        print(F"\t  ==> {color(7, err)}")
        conn.close()
        pass

    return -1


def insert_dictionary(db_name, dictionary, table):

    print(color(7, F"\n\t- Importing Dictionary into table: {table}"))
    data = []

    if db_name == "None":
        return None

    conn = connect(db_name)

    try:

        cur = conn.cursor()
        for key, value in dictionary.items():
            data.append((key, str(value)))
        cur.executemany(insert_dict_cmd.format(table), data)
        conn.commit()
        conn.close()
        inserted = len(data)
        print(color(7, F"\t- {formatNumber(inserted, currency='')} {'rows have' if inserted > 1 else 'row has'}"
                       F" been successfully inserted into {table}"))
        return inserted
    except Exception as err:
        print(F"\t  ==> {color(7, err)}")
        conn.close()
        pass

    return -1


def insert_many(db_name, cmd, values):

    # print(color(7, F"\n\t- Importing Dictionary into table: {table}"))

    if db_name == "None":
        return None

    conn = connect(db_name)

    try:

        cur = conn.cursor()
        cur.executemany(cmd, values)
        conn.commit()
        conn.close()
        inserted = len(values)
        print(color(7, F"\t- {formatNumber(inserted, currency='')} {'rows have' if inserted > 1 else 'row has'} "
                       F"has been successfully inserted."))
        return inserted
    except Exception as err:
        print(F"\t  ==> {color(7, err)}")
        conn.close()
        pass

    return -1


def check(db_name, table):
    cmd = F"SELECT name FROM sqlite_master WHERE name='{table}'"
    return bool(connect(db_name).cursor().execute(cmd).fetchone())


def check_cmd(db_name, cmd):
    return bool(connect(db_name).cursor().execute(cmd).fetchone())


def db_tables(db_name, display=False):

    if db_name == "None":
        return None
    con = sqlite3.connect(db_path.format(db_name))

    tables = con.cursor().execute("SELECT name FROM sqlite_master").fetchall()
    tables = [table[0] for table in tables if table[0].startswith('sqlite_') is False]

    if display is True:
        count = 1
        print(F"\nTABLES IN THE [{db_name}] DATABASE\n")
        for table in tables:
            if table[0].startswith('sqlite_') is False:
                print(F"\t{count:>3}. {table}")
                count += 1
        print(F"")

    return tables

# print(db_tables(db_name="shared"))


def insert_person(db_name, dictionary):

    print(color(7, F"\n\t- Importing Dictionary into table: PERSON_TBL"))

    cmd = "INSERT INTO PERSON_TBL (id, personID, type, age, gender, " \
          "givenName, familyName, occupationTitle, prefixFamilyName)" \
          " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"

    data = [(key, value['personID'], value['type'], value['age'],
             value['gender'], value['givenName'], value['familyName'],
             value['occupationTitle'], value['prefixFamilyName'])
            for key, value in dictionary.items()]

    if db_name is None and db_name == "None":
        return None

    conn = connect(db_name)

    try:

        cur = conn.cursor()
        cur.executemany(cmd, data)
        conn.commit()
        conn.close()
        inserted = len(data)
        print(
            color(7, F"\t- {formatNumber(inserted, currency='')} {'rows have' if inserted > 1 else 'row has'} "
                     F"has been successfully inserted into PERSON_TBL"))
        return inserted

    except Exception as err:
        print(F"\t  ==> {color(7, err)}")
        conn.close()
        pass

    return -1


def update(db_name, cmd):

    if db_name == "None":
        return None

    conn = connect(db_name)

    # print(cmd)
    try:
        cur = conn.cursor()
        cur.execute(cmd)
        conn.commit()
        conn.close()
        # print(cmd)
        # print(F"\t{color(7, 'Your [Update] has been completed!')}")

    except Exception as err:
        print(F"\tdb    : {db_name}\n"
              F"\tcmd   : {cmd}\n"
              F"\t  db command [Update] ==> {color(7, err)}")
        conn.close()
        pass


def delete_row(db_name, cmd):

    if db_name == "None":
        return None

    conn = connect(db_name)

    try:
        cur = conn.cursor()
        cur.execute(cmd)
        conn.commit()
        conn.close()
    except Exception as err:
        print(F"\t  db command [delete] ==> {color(7, err)}")
        conn.close()
        pass


def selected_db():
    selected = select_last_row(db_name='shared', table='SELECTED_DB_TBL', column='id')
    # print(F"SELECTED: {selected}")
    if selected is None:
        return None
    return selected['db_name']


def about_DB(db_name):

    db = select_row(db_name=db_name, table='DATABASE_TBL', column='name', value=db_name)
    # print(db['name'], db['civil_registries_path'], db['reconstituted_path'])

    if db_name == 'None':
        return None

    return {
        'name': db['name'],
        'registries_path': db['civil_registries_path'],
        'reconstituted_path': db['reconstituted_path']
    }


def display_rows(db_name, table, stop=5):

    pr = get_rows(db_name, table)
    print(F"\n{db_name}.db  [{table}] Length: {len(pr)}")
    count = 0
    for row in pr:
        print(F"""{" | ".join(str(col) for col in row)}\n""")
        if count == stop:
            break
        count += 1


# def x():
#     connection = connect(F"Zeeland")
#     cmd1 = "DROP TABLE IF EXISTS RESULT_TBL;"
#     cmd = """
#     CREATE TABLE RESULT_TBL (
#     cid integer PRIMARY KEY,
#     c_size integer NOT NULL,
#     name TEXT NOT NULL,
#     flag TEXT NOT NULL,
#     marital_text TEXT NOT NULL,
#     bads integer NOT NULL,
#     maybes integer NOT NULL,
#     summary TEXT NOT NULL,
#     html_table TEXT NOT NULL
#     );
#     """
#     connection.execute(cmd)
#     connection.commit()
#     connection.close()
#
# x()

# display_rows(db_name='shared', table='SELECTED_DB_TBL')

# display_rows(db_name='Utrecht', table='FULL_EVENTS_TBL')
# display_rows(db_name='Utrecht', table='ASSOCIATION_DICT_TBL')
# display_rows(db_name='Zeeland', table='ASSOCIATION_DICT_TBL')
# display_rows(db_name='Utrecht', table='PERSON_2_EVENTS_TBL')


# display_rows(db_name='Zeeland', table='RESULT_TBL')

# row = select_row(db_name='shared', table='SELECTED_DB_TBL', column='id', value=1)
# print(row[1])

# selected = selected_db()

# row = select_row(db_name='shared', table='SELECTED_DB_TBL', column='id', value=1)
# print(row)


# db_tables()
#
# print(check('PERSON_ID2CLUSTER_TBL'))
# PID = 'p-2272899'
# CID = '1736834'
# r = select_row('ASSOCIATION_DICT_TBL', 'id', CID)


#
# display_rows(db_name='Zeeland', table='DATABASE_TBL')
#
# r = select_row(db_name='Zeeland', table='DATABASE_TBL', column='name', value='Zeeland')
#
# print(r['name'], r['civil_registries_path'], r['reconstituted_path'])

# display_rows('SELECTED_DB_TBL')

# display_rows(db_name='Zeeland', table='DATABASE_TBL')
# display_rows(table='PERSON_TBL')
# display_rows(table='EVENTS_TBL')
# display_rows(table='FULL_EVENTS_TBL')
# display_rows(table='PERSON_2_EVENTS_TBL')

# r = get_rows('EVENTS_TBL')
# r = get_rows('ASSOCIATION_DICT_TBL')

# print(get_rows('PERSON_ID2CLUSTER_TBL')[70][2])
# print(r[0], r[2])
# print(r[0][2])
# print(r[1][0])
# for k, v in r.items():
#     print(k, v)
