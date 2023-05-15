from sys import exit
from os import path

try:
    import sqlite3
except ImportError as e:
    print(f"ImportError: {e}")
    print(f"Your python installation is missing the sqlite3 module")

import argparse

if __name__ == "__main__":  # make relative imports work as described here: https://peps.python.org/pep-0366/#proposed-change
    if __package__ is None:
        __package__ = "regina"
        import sys
        filepath = path.realpath(path.abspath(__file__))
        sys.path.insert(0, path.dirname(path.dirname(filepath)))

from .data_collection.parse_log import parse_log
from .database import Database
from .data_visualization.visualize import visualize
from .utility.globals import settings, version, config_dir, data_dir
from .utility.utility import pmessage, pdebug, make_parent_dirs

"""
start regina, launch either collect, visualize or update_geoip
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
    parser = argparse.ArgumentParser(prog="regina")
    parser.add_argument("--config", "-c",   action="store",         help="path to an alternate config file", metavar="config-file")
    parser.add_argument("--update-geoip",   action="store",         help="path to IP-COUNTRY-REGION-CITY database in csv format", metavar="geoip-csv")
    parser.add_argument("--visualize",      action="store_true",    help="generate the visualization website")
    parser.add_argument("--collect",        action="store_true",    help="fill the database from the nginx access log")
    parser.add_argument("--log-file",       action="store",         help="use alternate logfile than what is set in the config file", metavar="log-file")
    args = parser.parse_args()

    if not (args.collect or args.visualize or args.update_geoip):
        parser.error("at least one of --visualize, --collect, or --update-geoip is required.")

    if args.config:
        if not path.isfile(args.config):
            parser.error(f"invalid path to configuration file: '{args.config}'")
        config_path = args.config

    else:
        config_path = f"{config_dir}/regina.conf"
        if not path.isfile(config_path):
            parser.error(f"missing configuration file: '{config_path}' and no alternative given.")

    try:
        settings.load(config_path)
    except ValueError as e:
        error(f"value error while loading the configuration in '{config_path}':\n\t{e}")
    except KeyError as e:
        error(f"key error while loading the configuration in '{config_path}':\n\t{e}")
    except Exception as e:
        error(f"while loading the configuration in '{config_path}':\n\t{e}")
    settings.set("regina", "version", version, allow_new=True)

    if args.log_file:
        settings.set("regina", "access_log", args.log_file)

    pdebug(f"Settings:\n{settings}", lvl=1)

    if not settings["regina"]["database"]:
        settings.set(f"regina", "database", f"{data_dir}/{settings['regina']['server_name']}.db")
    db_path = settings["regina"]["database"]
    make_parent_dirs(db_path)
    db = Database(db_path)
    # if not isfile(settings["db"]):
    #     create_db(settings["db"], settings["filegroups"], settings["locs_and_dirs"], settings["auto_group_filetypes"])

    if args.update_geoip:
        if not path.isfile(args.update_geoip):
            parser.error(f"invalid path to GeoIP database: '{args.update_geoip}'")
        db.update_geoip_tables(args.update_geoip)
        # update visitors
        for visitor_id,  in db(f"SELECT visitor_id FROM visitor"):
            db.update_ip_range_id(visitor_id)

    if args.collect:
        pmessage(f"regina version {version} with server-name '{settings['regina']['server_name']}', database '{db_path}' and logfile '{settings['regina']['access_log']}'")
        requests = parse_log(settings['regina']["access_log"])
        request_count, visitors_count, new_visitors_count = db.add_requests(requests)
        if visitors_count > 0: percentage = 100.0*new_visitors_count/visitors_count
        else: percentage = '--'
        pmessage(f"Added {request_count} new requests from {visitors_count} different visitors, from which {new_visitors_count} are new ({percentage:2}%)")

    if args.visualize:
        pmessage(f"regina version {version} with server-name '{settings['regina']['server_name']}', database '{db_path}'")
        visualize(db)

if __name__ == '__main__':
    main()
