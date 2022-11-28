# from sys import path
# print(f"{__file__}: __name__={__name__}, __package__={__package__}, sys.path[0]={path[0]}")
from sys import exit

"""
Various utitity
"""

DEBUG = True
def pdebug(*args):
    if DEBUG: print(*args)

def warning(*w):
    print("Warning:", *w)

def error(*arg):
    print("Error:", *arg)
    exit(1)

def missing_arg_val(arg):
    print("Missing argument for", arg)
    exit(1)

def missing_arg(arg):
    print("Missing ", arg)
    exit(1)

