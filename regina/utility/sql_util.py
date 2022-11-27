import sqlite3 as sql
"""Various utilities"""
def sanitize(s):
    if type(s) != str: return s
    return s\
        .replace("''", "'").replace("'", r"''").strip(" ")
        # .replace('"', r'\"')\

def sql_get_constaint_str(constraints: list[tuple[str, str|int]], logic="AND") -> str:
    c_str = ""
    for name, val in constraints:
        c_str += f"{name} = '{sanitize(val)}' {logic} "
    return c_str.strip(logic + " ")

def sql_get_value_str(values: list[list]) -> str:
    c_str = ""
    for params in values:
        c_str += "("
        for p in params: c_str += f"'{sanitize(p)}', "
        c_str = c_str.strip(", ") + "), "
    return c_str.strip(", ")

def sql_exists(cur: sql.Cursor, table: str, constraints: list[tuple[str, str|int]], logic="AND") -> bool:
    cur.execute(f"SELECT EXISTS (SELECT 1 FROM {table} WHERE {sql_get_constaint_str(constraints, logic)})")
    return cur.fetchone()[0] == 1

def sql_select(cur: sql.Cursor, table: str, constraints: list[tuple[str, str|int]], logic="AND"):
    cur.execute(f"SELECT * FROM {table} WHERE {sql_get_constaint_str(constraints, logic)}")
    return cur.fetchall()

def sql_insert(cur: sql.Cursor, table: str, values: list[list]):
    cur.execute(f"INSERT INTO {table} VALUES {sql_get_value_str(values)}")

def sql_tablesize(cur: sql.Cursor, table: str) -> int:
    cur.execute(f"SELECT Count(*) FROM {table}")
    return cur.fetchone()[0]

def sql_get_count_where(cur: sql.Cursor, table, constraints) -> int:
    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {sql_get_constaint_str(constraints)}")
    return cur.fetchone()[0]
