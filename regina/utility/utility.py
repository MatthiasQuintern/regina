# from sys import path
# print(f"{__file__}: __name__={__name__}, __package__={__package__}, sys.path[0]={path[0]}")
from sys import exit
from os import path
from re import fullmatch

from regina.utility.globals import settings

"""
Various utitity
"""

def is_whitelisted(val: str, whitelist: str|list[str]|None):
    """
    Check if val is in a regex whitelist
    whitelist: regexp, list of regexp or None
    if whitelist is None, always return True
    """
    if not whitelist: return True
    if type(whitelist) == str:
        return fullmatch(whitelist, val)
    if type(whitelist) == list:
        for w in whitelist:
            if not fullmatch(w, val): return False
    return True

def is_blacklisted(val: str, blacklist: str|list[str]|None):
    """
    Check if val is in a regex blacklist
    blacklist: regexp, list of regexp or None
    if blacklist is None, always return False
    """
    return not is_whitelisted(val, blacklist)


def pdebug(*args, **keys):
    if settings["debug"]: print(*args, **keys)

def warning(*w, **k):
    print("Warning:", *w, **k)

def pmessage(*args, **keys):
    print(*args, **keys)

def error(*arg):
    print("Error:", *arg)
    exit(1)

def missing_arg_val(arg):
    print("Missing argument for", arg)
    exit(1)

def missing_arg(arg):
    print("Missing ", arg)
    exit(1)


def get_filepath(filename, directories: list):
    """search directories for file and return the full path to the file"""
    for d in directories:
        p = f"{path.expanduser(d)}/{filename}"
        if path.isfile(p):
            return p
    raise FileNotFoundError(f"{filename} not in {directories}")
