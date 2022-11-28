# from sys import path
# print(f"{__file__}: __name__={__name__}, __package__={__package__}, sys.path[0]={path[0]}")
# __package__="."
from sys import argv, exit
from os.path import isfile
from regina.db_operation.collect import parse_log, add_requests_to_db
from regina.db_operation.database import create_db
from regina.db_operation.visualize import visualize
from regina.utility.settings_manager import read_settings_file
from regina.utility.globals import settings, version
from regina.utility.utility import pmessage

"""
start regina, launch either collect or visualize
TODO:
- optionen:
    - unique user = ip address
    - max requests/time
- fix datum im user and request count plot
- fix datum monat is 1 zu wenig
- checken warum last x days und total counts abweichen
- länder aus ip addresse
- "manuelle" datenbank beabeitung in cli:
    - user + alle seine requests löschen
- user agents:
    - android vor linux suchen, oder linux durch X11 ersetzen
    - alles was bot drin hat als bot betrachten
- wenn datenbankgröße zum problem wird:
    - referrer table die die schon zusammengelegten referrer enthält, request verlinkt nur mit id
    - selbes für platforms und browsers
- test:
    - human detection
    - referer cleanup
- schöne log nachrichten für die cron mail
- testing!
"""


def help():
    helpstring = """Command line options:
    --server-name               string
    --log                       path to the access.log
    --db                        name of the database
    --settings["filegroups"]                string describing settings["filegroups"], eg 'name1: file1, file2; name2: file3, file4, file5;'
    --auto-group-filetypes      comma separated list of filetypes, eg 'css,png,gif'
    --locs-and_dirs             comma separated list of nginx_location:directory pairs, eg '/:/www/website'
    --config-file               path to a config file that specifies all the other parameters: param = value, where value has the same formatting as on the command line
    """
    print(helpstring)

def missing_arg_val(arg):
    print("Missing argument for", arg)
    exit(1)

def missing_arg(arg):
    print("Missing ", arg)
    exit(1)

def error(arg):
    print("Error:", arg)
    exit(1)

def main():
    config_file = ""
    collect = False
    visualize_ = False
    log_file = ""
    # parse args
    i = 1
    while i in range(1, len(argv)):
        if argv[i] == "--config":
            if len(argv) > i + 1: config_file = argv[i+1]
            else: missing_arg_val(argv[i])
        if argv[i] == "--log-file":
            if len(argv) > i + 1: log_file = argv[i+1]
            else: missing_arg_val(argv[i])
        elif argv[i] == "--help":
            help()
            exit(0)
        elif argv[i] == "--collect":
            collect = True
        elif argv[i] == "--visualize":
            visualize_ = True
        else:
            pass
        i += 1
    if not collect and not visualize_:
        missing_arg("--visualize or --collect")

    if not config_file:
        missing_arg("--config_file")
    if not isfile(config_file):
        error(f"Not a file: '{config_file}'")
    read_settings_file(config_file, settings)
    settings["version"] = version
    if log_file: settings["access_log"] = log_file


    if not settings["server_name"]: missing_arg("server-name")
    if not settings["access_log"]: missing_arg("log")
    if not settings["db"]: missing_arg("db")
    if isinstance(settings["auto_group_filetypes"], str):
        settings["auto_group_filetypes"] = settings["auto_group_filetypes"].split(",")
    if isinstance(settings["locs_and_dirs"], str):
        settings["locs_and_dirs"] = [ loc_and_dir.split(":") for loc_and_dir in settings["locs_and_dirs"].split(",") ]


    if collect:
        pmessage(f"regina version {version} with server-name '{settings['server_name']}', database '{settings['db']}' and logfile '{settings['access_log']}'")
        if not isfile(settings["db"]):
            create_db(settings["db"], settings["filegroups"], settings["locs_and_dirs"], settings["auto_group_filetypes"])
        requests = parse_log(settings["access_log"])
        add_requests_to_db(requests, settings["db"])
    elif visualize_:
        pmessage(f"regina version {version} with server-name '{settings['server_name']}', database '{settings['db']}'")
        if not isfile(settings["db"]): error(f"Invalid database path: '{settings['db']}'")
        visualize(settings)
    else:
        error("Either --collect --visualize has to be provided")

if __name__ == '__main__':
    main()
