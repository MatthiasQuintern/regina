from enum import auto
from collect import parse_log, add_requests_to_db
from sys import argv, exit
from database import create_db
from os.path import isfile

def parse_config_file(path):
    server_name =""
    access_log_path = ""
    db_path = ""
    filegroups = ""
    locs_and_dirs = []
    auto_group_filetypes = []
    with open(path, "r") as file:
        lines = file.readlines()
    for line in lines:
        line = line.strip("\n ")
        if line.startswith("#"): continue
        arg, val = line.split("=")
        arg = arg.strip(" ")
        val = val.strip(" ")
        if arg == "server-name": server_name = val
        elif arg == "log": access_log_path = val
        elif arg == "db": db_path = val
        elif arg == "filegroups": filegroups = val
        elif arg == "locs-and-dirs": locs_and_dirs = val
        elif arg == "auto-group-filetypes": auto_group_filetypes = val
    return server_name, access_log_path, db_path, filegroups, locs_and_dirs, auto_group_filetypes


def help():
    helpstring = """Command line options:
    --server-name               string
    --log                       path to the access.log
    --db                        name of the database
    --filegroups                string describing filegroups, eg 'name1: file1, file2; name2: file3, file4, file5;'
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
if __name__ == '__main__':
    server_name =""
    access_log_path = ""
    db_path = ""
    config_file = ""
    filegroups = ""
    auto_group_filetypes =[]
    locs_and_dirs = []
    # parse args
    i = 1
    while i in range(1, len(argv)):
        if argv[i] == "--server-name":
            if len(argv) > i + 1: server_name = argv[i+1]
            else: missing_arg_val(argv[i])
            i += 1
        elif argv[i] == "--db":
            if len(argv) > i + 1: db_path = argv[i+1]
            else: missing_arg_val(argv[i])
            i += 1
        elif argv[i] == "--log":
            if len(argv) > i + 1: access_log_path = argv[i+1]
            else: missing_arg_val(argv[i])
            i += 1
        elif argv[i] == "--config":
            if len(argv) > i + 1: config_file = argv[i+1]
            else: missing_arg_val(argv[i])
            i += 1
        elif argv[i] == "--filegroups":
            if len(argv) > i + 1: filegroups = argv[i+1]
            else: missing_arg_val(argv[i])
            i += 1
        elif argv[i] == "--auto-group-filetypes":
            if len(argv) > i + 1: auto_group_filetypes = argv[i+1]
            else: missing_arg_val(argv[i])
            i += 1
        elif argv[i] == "--locs-and-dirs":
            if len(argv) > i + 1: locs_and_dirs = argv[i+1]
            else: missing_arg_val(argv[i])
            i += 1
        elif argv[i] == "--help":
            help()
            exit(0)
        else:
            i += 1

    if config_file:
        server_name, access_log_path, db_path, filegroups, locs_and_dirs, auto_group_filetypes = parse_config_file(config_file)

    if not server_name: missing_arg("--server-name")
    if not access_log_path: missing_arg("--log")
    if not db_path: missing_arg("--db")
    if type(auto_group_filetypes) == str:
        auto_group_filetypes = auto_group_filetypes.split(",")
    if type(locs_and_dirs) == str:
        locs_and_dirs = [ loc_and_dir.split(":") for loc_and_dir in locs_and_dirs.split(",") ]
    if not isfile(db_path):
        create_db(db_path, filegroups, locs_and_dirs, auto_group_filetypes)
    requests = parse_log(access_log_path)
    add_requests_to_db(requests, db_path)
