import sqlite3 as sql
"""Various utilities"""

def get_date_constraint(at_date=None, min_date=None, max_date=None):
    """
    get a condition string that sets a condition on the time to a certain date
    the conditions can be a string representing a date or an int/float in unixepoch
    """
    # dates in unix time
    s = ""
    if at_date is not None:
        if isinstance(at_date, str):
            s += f"DATE(time, 'unixepoch') = '{sanitize(at_date)}' AND "
        elif isinstance(at_date, int|float):
            s += f"time = {int(at_date)} AND "
        else:
            print(f"WARNING: get_where_date_str: Invalid type of argument at_date: {type(at_date)}")
    if min_date is not None:
        if isinstance(min_date, str):
            s += f"DATE(time, 'unixepoch') >= '{sanitize(min_date)}' AND "
        elif isinstance(min_date, int|float):
            s += f"time >= {int(min_date)} AND "
        else:
            print(f"WARNING: get_where_date_str: Invalid type of argument min_date: {type(min_date)}")
    if max_date is not None:
        if isinstance(max_date, str):
            s += f"DATE(time, 'unixepoch') <= '{sanitize(max_date)}' AND "
        elif isinstance(max_date, int|float):
            s += f"time <= {int(max_date)} AND "
        else:
            print(f"WARNING: get_where_date_str: Invalid type of argument max_date: {type(max_date)}")
    if s == "":
        print(f"WARNING: get_where_date_str: no date_str generated. Returning 'time > 0'. at_date={at_date}, min_date={min_date}, max_date={max_date}")
        return "time > 0"
    return s.removesuffix(" AND ")


def replace_null(s):
    if not s:
        return "None"
    return s

def sanitize(s):
    if type(s) != str: return s
    return s.replace("'", r"''").strip(" ")
        # .replace('"', r'\"')\

def sql_get_constaint_str(constraints: list[tuple[str, str|int]], logic="AND", do_sanitize=True) -> str:
    c_str = ""
    for name, val in constraints:
        if do_sanitize: val = sanitize(val)
        c_str += f"{name} = '{val}' {logic} "
    return c_str.strip(logic + " ")

def sql_get_value_str(values: list[list]) -> str:
    c_str = ""
    for params in values:
        c_str += "("
        for p in params: c_str += f"'{sanitize(p)}', "
        c_str = c_str.strip(", ") + "), "
    return c_str.strip(", ")

def sql_exists(cur: sql.Cursor, table: str, constraints: list[tuple[str, str|int]], logic="AND", do_sanitize=True) -> bool:
    cur.execute(f"SELECT EXISTS (SELECT 1 FROM {table} WHERE {sql_get_constaint_str(constraints, logic, do_sanitize=do_sanitize)})")
    return cur.fetchone()[0] == 1

def sql_select(cur: sql.Cursor, table: str, constraints: list[tuple[str, str|int]], logic="AND", do_sanitize=True):
    cur.execute(f"SELECT * FROM {table} WHERE {sql_get_constaint_str(constraints, logic, do_sanitize=do_sanitize)}")
    return cur.fetchall()

def sql_insert(cur: sql.Cursor, table: str, values: list[list]):
    cur.execute(f"INSERT INTO {table} VALUES {sql_get_value_str(values)}")

def sql_tablesize(cur: sql.Cursor, table: str) -> int:
    cur.execute(f"SELECT Count(*) FROM {table}")
    return cur.fetchone()[0]

def sql_max(cur: sql.Cursor, table: str, column: str) -> int:
    cur.execute(f"SELECT MAX({column}) FROM {table}")
    val = cur.fetchone()[0]
    if not type(val) == int: val = 0
    return val

def sql_get_count_where(cur: sql.Cursor, table, constraints) -> int:
    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {sql_get_constaint_str(constraints)}")
    return cur.fetchone()[0]
