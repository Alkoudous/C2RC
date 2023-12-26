from sqlite3 import connect

# REGISTRIES = '../../data/inputs/CivilRegistries.trig'
# RECONSTITUTED = '../../data/inputs/Reconstituted.trig'
INPUT_FILES = "INSERT INTO input_files (description, path) VALUES (?, ?)"

route = F"web/db/databases/"
schemas = F"web/db/schemas/"


def initiate_shared():
    connection = connect(F"{route}shared.db")
    with open(F'{schemas}shared_schema.sql') as f:
        connection.executescript(f.read())
    connection.commit()
    connection.close()


def initiate(db_name):
    connection = connect(F'{route}{db_name}.db')
    with open(F'{schemas}schema.sql') as f:
        connection.executescript(f.read())
    connection.commit()
    connection.close()

