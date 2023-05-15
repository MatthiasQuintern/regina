# from sys import path
# print(f"{__file__}: __name__={__name__}, __package__={__package__}, sys.path[0]={path[0]}")
from sys import exit, stderr
from os import path, makedirs
from re import fullmatch, Pattern

from regina.utility.globals import settings

"""
Various utitity
"""

def _fullmatch(val, regexp, match_none=True):
    """
    Check if val fully matches regexp
    Regexp can be:
        None -> return match_none
        str
        re.Pattern
        list of the above, in which case True if returned if it matches any of the expressions in the list

    """
    if not regexp: return match_none
    if type(regexp) == str:
        if fullmatch(regexp, val):
            return True
    elif type(regexp) == list:
        for w in regexp:
            if _fullmatch(val, w):
                return True
    elif type(regexp) == Pattern:
        if not regexp.pattern:  # if whitelist = re.compile('')
            return match_none
        elif fullmatch(regexp, val):
            return True
    else:
        warning(f"_fullmatch: Unsupported regexp type: {type(regexp)}")
    return False

def is_whitelisted(val: str, whitelist: str|Pattern|None|list) -> bool:
    """
    Check if val is in a regex whitelist
    whitelist: regexp as str or compiled pattern or None, or a list of them
    if whitelist is None, always return True
    """
    wl = _fullmatch(val, whitelist)
    if not wl: pdebug(f"is_whitelisted: value='{val}' is not on whitelist: '{whitelist}'", lvl=4)
    return wl

def is_blacklisted(val: str, blacklist: str|Pattern|None|list):
    """
    Check if val is in a regex blacklist
    blacklist: regexp as str or compiled pattern or None, or a list of them
    if blacklist is None, always return False
    """
    bl = _fullmatch(val, blacklist, match_none=False)
    if bl: pdebug(f"is_blacklisted: value='{val}' is blacklisted: '{blacklist}'", lvl=4)
    return bl


def pdebug(*args, lvl=2, **keys):
    if settings["debug"]["debug_level"] >= lvl: print(*args, **keys)

def warning(*w, **k):
    print("Warning:", *w, file=stderr, **k)

def pmessage(*args, **keys):
    print(*args, **keys)

def error(*args, errno: int=1, **k):
    print("Error:", *args, file=stderr, **k)
    exit(errno)

def dict_str(d: dict):
    """nicer string for dictionaries"""
    s = ""
    for k, v in d.items():
        s += f"{k}:\t{v}\n"
    return s.strip("\n")


def get_filepath(filename, directories: list):
    """search directories for file and return the full path to the file"""
    for d in directories:
        p = f"{path.expanduser(d)}/{filename}"
        if path.isfile(p):
            return p
    raise FileNotFoundError(f"{filename} not in {directories}")

def make_parent_dirs(p):
    parent = path.dirname(p)
    if not path.isdir(parent):
        pdebug(f"make_parent_dirs: Making directory '{parent}'", lvl=2)
        makedirs(parent)
