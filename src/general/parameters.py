from os import mkdir, path
from src.web.db.databases import DB_FOLDER
from src.data.outputs.serialised import SERIALIZATION_Folder
from src.data.outputs.evaluations import EVALUATION_Folder

# THE MAXIMUM NUMBER OF POSSIBLE CHILDREN
MAX_CHILDREN = 20

# THE MAXIMUM NUMBER OF ACCEPTABLE AMOUNT OF MARRIAGES
MAX_MARRIAGE = 5

# THE MAXIMUM AGE DIFFERENCE BETWEEN THE FIRST AND LAST CHILD
MAX_FIRST_LAST = 30

# THE ACCEPTABLE MINIMUM AGE OF BEING WED
MAX_MARRIAGE_AGE = 13

# THE MAXIMUM AGE OF CHILD BIRTH
MAX_DELIVERY_AGE = 50

# THE MAXIMUM AGE DIFFERENCE BETWEEN TWO CONSECUTIVE CHILDREN
MAX_CONS_AGE_DIFF = 10

MAX_TABLE_ROWS = 10


# --------------------------------------------------------------
# TRIG DATA FOLDERS: RECONSTITUTED AND CIVIL REGISTRIES
# --------------------------------------------------------------
# reconstituted_data = F"{INPUTS_Folder}/Reconstituted.trig"
# civil_registries_data = F"{INPUTS_Folder}/CivilRegistries.trig"


# --------------------------------------------------------------
# FOLDER FOR SERIALISED OBJECTS
# --------------------------------------------------------------
main_f = F"{SERIALIZATION_Folder}/Main"
if path.exists(main_f) is False:
    mkdir(main_f)

TRIPLE_FOLDER = F"{SERIALIZATION_Folder}/Triples"
if path.exists(TRIPLE_FOLDER) is False:
    mkdir(TRIPLE_FOLDER)

html_folder = F"{EVALUATION_Folder}/HTMLS"
if path.exists(html_folder) is False:
    mkdir(html_folder)

rdf_folder = F"{EVALUATION_Folder}/rdfs"
if path.exists(rdf_folder) is False:
    mkdir(rdf_folder)

validation_set = 'resource:{}-Extended_Family-Based_Validations'
reconstitution_set = 'resource:{}-Reconstitutions-Stats'
s_coReferents = F"{main_f}/S-CoReferents_dict"
s_person_registries = F"{main_f}/S-Persons_dict"
person2event_dict = F"{main_f}/S-Person2event_dict.txt"
s_events_registries = F"{main_f}/S-Events_dict"
s_rel_events_registries = F"{main_f}/S-Relation_Events_dict"
s_full_events_registries = F"{main_f}/S-FullEvents_dict"
s_relations_list = F"{main_f}/S-Associations_list"
s_relations_dict = F"{main_f}/S-Associations_dict"
nt_relations_file = F"{TRIPLE_FOLDER}/T-Relations.nt"
ttl_relations_file = F"{TRIPLE_FOLDER}/T-Relations.ttl"

# 'http://schema.org/familyName', 'http://schema.org/givenName', "http://schema.org/gender"
f_name, g_name, gender, f_name_prefix, = 'familyName', 'givenName', "gender", "prefixFamilyName"

