# from sys import path
# print(f"{__file__}: __name__={__name__}, __package__={__package__}, sys.path[0]={path[0]}")
# __package__="."
from sys import argv, exit
from os.path import isfile
import sqlite3 as sql
from regina.db_operation.collect import parse_log, add_requests_to_db, update_ip_range_id
from regina.db_operation.database import create_db, update_geoip_tables, t_visitor
from regina.db_operation.visualize import visualize
from regina.utility.settings_manager import read_settings_file
from regina.utility.globals import settings, version
from regina.utility.utility import pmessage
from regina.utility.sql_util import sql_tablesize

"""
start regina, launch either collect or visualize
TODO:
- optionen:
    - unique visitor = ip address
    - max requests/time
    - unique request datums unabhängig
X fix datum im visitor and request count plot
X fix datum monat is 1 zu wenig
X fix ms edge nicht dabei
- für letzten Tag: uhrzeit - requests/visitors plot
- checken warum last x days und total counts abweichen
- länder aus ip addresse
- "manuelle" datenbank beabeitung in cli:
    - visitor + alle seine requests löschen
- visitor agents:
    X android vor linux suchen, oder linux durch X11 ersetzen
    - alles was bot drin hat als bot betrachten
- wenn datenbankgröße zum problem wird:
    - referrer table die die schon zusammengelegten referrer enthält, request verlinkt nur mit id
    - selbes für platforms und browsers
- test:
    - human detection
    X referer cleanup
X geoip
- schöne log nachrichten für die cron mail
- testing!
"""


def help():
    helpstring = """Command line options:
    --config <path>             path to a config file that specifies all the other parameters: param = value, where value has the same formatting as on the command line
    --update-geoip <path>       path to IP-COUNTRY-REGION-CITY database in csv format
    --visualize                 generate the visualization website
    --collect                   fill the database from the nginx access log
    --log-file <path>           use alternate logfile
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
    geoip_city_csv = ""
    # parse args
    i = 1
    while i in range(1, len(argv)):
        if argv[i] in ["--config", "-c"]:
            if len(argv) > i + 1: config_file = argv[i+1]
            else: missing_arg_val(argv[i])
        elif argv[i] == "--log-file":
            if len(argv) > i + 1: log_file = argv[i+1]
            else: missing_arg_val(argv[i])
        if argv[i] == "--update-geoip":
            if len(argv) > i + 1: geoip_city_csv = argv[i+1]
            else: missing_arg_val(argv[i])
        elif argv[i] in ["--help", "-h"]:
            help()
            exit(0)
        elif argv[i] == "--collect":
            collect = True
        elif argv[i] == "--visualize":
            visualize_ = True
        else:
            pass
        i += 1
    if not (collect or visualize_ or geoip_city_csv):
        missing_arg("--visualize or --collect or --update-geoip")

    if not config_file:
        missing_arg("--config")
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

    if not isfile(config_file):
        error(f"Not a file: '{config_file}'")


    if not isfile(settings["db"]):
        create_db(settings["db"], settings["filegroups"], settings["locs_and_dirs"], settings["auto_group_filetypes"])

    if geoip_city_csv:
        if not isfile(geoip_city_csv):
            error(f"Not a file: '{geoip_city_csv}'")
        conn = sql.connect(settings['db'], isolation_level=None)  # required vor vacuum
        cur = conn.cursor()
        update_geoip_tables(cur, geoip_city_csv)
        # update visitors
        for visitor_id in range(sql_tablesize(cur, t_visitor)):
            update_ip_range_id(cur, visitor_id)
        cur.close()
        conn.commit()
        conn.close()
    if collect:
        pmessage(f"regina version {version} with server-name '{settings['server_name']}', database '{settings['db']}' and logfile '{settings['access_log']}'")
        requests = parse_log(settings["access_log"])
        add_requests_to_db(requests, settings["db"])
    if visualize_:
        pmessage(f"regina version {version} with server-name '{settings['server_name']}', database '{settings['db']}'")
        if not isfile(settings["db"]): error(f"Invalid database path: '{settings['db']}'")
        visualize(settings)

if __name__ == '__main__':
    main()
