# from sys import path
# print(f"{__file__}: __name__={__name__}, __package__={__package__}, sys.path[0]={path[0]}")
from sys import exit

from regina.utility.globals import settings

"""
Various utitity
"""

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

