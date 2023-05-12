# from sys import path
# print(f"{__file__}: __name__={__name__}, __package__={__package__}, sys.path[0]={path[0]}")
# __package__="."
from sys import argv, exit
from os.path import isfile
import sqlite3 as sql

import argparse

if __name__ == "__main__":  # make relative imports work as described here: https://peps.python.org/pep-0366/#proposed-change
    if __package__ is None:
        __package__ = "regina"
        import sys
        from os import path
        filepath = path.realpath(path.abspath(__file__))
        sys.path.insert(0, path.dirname(path.dirname(filepath)))

from .data_collection.parse_log import parse_log
from .database import Database
from .data_visualization import visualize
from .utility.settings_manager import read_settings_file
from .utility.globals import settings, version
from .utility.utility import pmessage
from .utility.sql_util import sql_tablesize

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


def main2():
    parser = argparse.ArgumentParser(prog="regina")
    parser.add_argument("--config", "-c",   action="store",         help="path to a config file that specifies all the other parameters", metavar="config-file", required=True)
    parser.add_argument("--update-geoip",   action="store",         help="path to IP-COUNTRY-REGION-CITY database in csv format", metavar="geoip-csv")
    parser.add_argument("--visualize",      action="store_true",    help="generate the visualization website")
    parser.add_argument("--collect",        action="store_true",    help="fill the database from the nginx access log")
    parser.add_argument("--log-file",       action="store",         help="use alternate logfile than what is set in the config file", metavar="log-file")
    args = parser.parse_args()

    if not (args.collect or args.visualize or args.update_geoip):
        parser.error("at least one of --visualize, --collect, or --update-geoip is required.")

    if not path.isfile(args.config):
        parser.error(f"invalid path to configuration file: '{args.config}'")

    read_settings_file(args.config, settings)
    settings["version"] = version

    if args.log_file:
        settings["access_log"] = args.log_file

    if not settings["server_name"]:
        error("'server-name' is missing in the configuration file.")

    if not settings["access_log"]:
        error("'log' is missing in the configuration file.")

    if not settings["db"]:
        error("'db' is missing in the configuration file.")

    db = Database(settings["db"])
    # if not isfile(settings["db"]):
    #     create_db(settings["db"], settings["filegroups"], settings["locs_and_dirs"], settings["auto_group_filetypes"])

    if args.update_geoip:
        if not isfile(args.update_geoip):
            error(f"Not a file: '{args.update_geoip}'")
        db.update_geoip_tables(args.update_geoip)
        # update visitors
        for (visitor_id) in db(f"SELECT visitor_id FROM visitor"):
            db.update_ip_range_id(visitor_id)
    if args.collect:
        pmessage(f"regina version {version} with server-name '{settings['server_name']}', database '{settings['db']}' and logfile '{settings['access_log']}'")
        requests = parse_log(settings["access_log"])
        db.add_requests(requests)
    if args.visualize:
        pmessage(f"regina version {version} with server-name '{settings['server_name']}', database '{settings['db']}'")
        if not isfile(settings["db"]): error(f"Invalid database path: '{settings['db']}'")
        visualize(settings)

if __name__ == '__main__':
    main2()
