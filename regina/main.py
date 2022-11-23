from enum import auto
from collect import parse_log, add_requests_to_db
from sys import argv, exit
from database import create_db
from os.path import isfile, isdir
from visualize import visualize
from settings_manager import read_settings_file

version = "1.0"

# default settings, these are overwriteable through a config file
settings = {
    # GENERAL
    "server-name": "",
    # DATA COLLECTION
    "access-log": "",
    "db": "",
    "locs-and-dirs": [],
    "auto-group-filetypes": [],
    "filegroups": "",

    # VISUALIZATION
    "get-human-percentage": False,
    # "file_ranking_regex_whitelist": r".*\.((txt)|(html)|(css)|(php)|(png)|(jpeg)|(jpg)|(svg)|(gif))",
    "file_ranking_regex_whitelist": r".*\.(html)",
    "referer_ranking_regex_whitelist": r"^[^\-].*",  # minus means empty
    "user_agent_ranking_regex_whitelist": r"",
    "file_ranking_plot_max_files": 15,
    # "plot_figsize": (60, 40),
    "plot_dpi": 300,
    "img_dir": "",
    "img_filetype": "svg",
    "template_html": "",
    "html_out_path": "",
    "last_x_days": 30,
}


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

if __name__ == '__main__':
    config_file = ""
    collect = False
    visualize_ = False
    # parse args
    i = 1
    while i in range(1, len(argv)):
        if argv[i] == "--config":
            if len(argv) > i + 1: config_file = argv[i+1]
            else: missing_arg_val(argv[i])
        elif argv[i] == "--help":
            help()
            exit(0)
        elif argv[i] == "--collect":
            collect = True
            exit(0)
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

    if not settings["server-name"]: missing_arg("server-name")
    if not settings["access-log"]: missing_arg("log")
    if not settings["db"]: missing_arg("db")
    if type(settings["auto-group-filetypes"]) == str:
        settings["auto-group-filetypes"] = settings["auto-group-filetypes"].split(",")
    if type(settings["locs-and-dirs"]) == str:
        settings["locs-and-dirs"] = [ loc_and_dir.split(":") for loc_and_dir in settings["locs-and-dirs"].split(",") ]
    if collect:
        if not isfile(settings["db"]):
            create_db(settings["db"], settings["filegroups"], settings["locs-and-dirs"], settings["auto-group-filetypes"])
        requests = parse_log(settings["access-log"])
        add_requests_to_db(requests, settings["db"])
    if visualize:
        if not isfile(settings["db"]): error(f"Invalid database path: '{settings['db']}'")
        visualize(settings)
