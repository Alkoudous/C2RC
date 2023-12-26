import ast
from time import strftime, gmtime
from hashlib import md5
from rdflib import Dataset
from os.path import exists, basename, splitext


def hasher(obj, size=15):

    # h = blake2b(digest_size=10)
    # h.update(bytes(object.__str__(), encoding='utf-8'))
    # print(F"H{h.hexdigest()}")
    h = md5()
    h.update(bytes(obj.__str__(), encoding='utf-8'))
    return F"H{h.hexdigest()[:size]}" if size else F"H{h.hexdigest()}"


def summarize_list(data):

    range_text = ''
    data.sort()
    data_size = len(data)
    # print("data", data)

    if data_size == 0:
        return ""

    elif data_size == 1:
        return str(data[0])

    init, previous = data[0], data[0]

    for i in range(1, data_size):

        if data[i] != previous + 1:
            range_text += F"{init}-{previous} " if init != previous else F"{init} "
            if i == data_size - 1:
                range_text += F"{data[i]}"
            init = data[i]
            # print("1- ", range_text)

        elif i == data_size - 1:
            range_text += F"{init}-{data[i]} " if data[i] != previous else F"{previous} "
            # print("2- ", range_text)

        previous = data[i]

    # print("data", range_text)
    return range_text


def formatNumber(number, currency="€", thousands_separator=".", fractional_separator=",", decimal=2):

    # "{}{:,.f}"
    # CONVERTS 2313981 TO 2,313,981.000
    x = F"{{}}{{:,.{decimal}f}}"
    converted = x.format(currency, number)

    # CONVERTS TO 2,313,981.000 TO 2.313.981,000
    if thousands_separator == ".":

        split = converted.split(".")
        main_currency, fractional_currency = split[0].replace(",", "."), split[1]

        # REMOVES THE FRACTION PART IF COMPOSED OF ONLY ZEROS
        converted = F"{main_currency}{fractional_separator}{fractional_currency}" \
            if fractional_currency != F"{'0':0<{decimal}}" else main_currency

    return converted


def check_rdf_file(file_path):

    try:

        if not exists(file_path):
            print("\n\t[Error] The path [{}] does not exist.".format(file_path))
            return

        rdf_file = basename(file_path)
        extension = splitext(rdf_file)[1]
        extension = extension.replace(".", "")
        print("")

        graph_format = extension
        if graph_format == 'ttl':
            graph_format = "turtle"

        """ Check the currently closed RDF file """
        print(F"""{"="*120}\n    Syntactic check of: {rdf_file}\n{"="*120}\n    Loading {rdf_file}""")

        g = Dataset()
        g.parse(source=file_path, format=graph_format)
        print("    It's a valid.{} file with a RDF graph of length: {}".format(extension, str(len(g))))

        return g

    except Exception as err:
        print("\t[check_rdf_file in checkRDFFile]", err)
        return None


def serialise(data):

    if data is None or data == "NULL":
        return None
    if data.startswith('defaultdict'):
        data = data[data.find("{"):-1]
        return ast.literal_eval(data)
    return ast.literal_eval(data)


def to_days(minutes):
    n = minutes * 60
    day = n // (24 * 3600)
    day = F"{day} {'days' if day > 0 else 'day'} " if day > 0 else ''
    time_format = strftime("%H:%M:%S", gmtime(n))
    return F"{day}{time_format}"
