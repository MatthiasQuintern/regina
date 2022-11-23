import sqlite3 as sql
from sql_util import sanitize, sql_select, sql_exists, sql_insert, sql_tablesize
from os import path, listdir


"""
create reginas database as shown in the uml diagram database.uxf
"""

DEBUG = True
def pdebug(*args):
    if DEBUG: print(*args)

class Entry:
    """
    represents an sql entry
    type_ is INTEGER, TEXT, REAL...
    """
    def __init__(self, name, type_) -> None:
        self.name = name
        self.type_ = type_
    def __repr__(self):
        return f"[{self.name}] {self.type_}"

class Table:
    def __init__(self, name, key: Entry, entries: list[Entry]=[], constaints: list[str]=[]):
        self.name = name
        self.key = key
        self.entries =  entries
        self.constaints = constaints
    def create_sql_str(self):
        return f"CREATE TABLE IF NOT EXISTS {self.name}\n({self})\n"
    def __repr__(self):
        s = f"{self.key} PRIMARY KEY"
        for entry in self.entries:
            s += f", {entry}"
        for c in self.constaints:
            s += f", {c}"
        return s
t_request = "request"
t_file = "file"
t_filegroup = "filegroup"
t_user = "user"

user_id = Entry("user_id", "INTEGER")
request_id = Entry("request_id", "INTEGER")
filegroup_id = Entry("group_id", "INTEGER")
ip_address_entry = Entry("ip_address", "TEXT")
filename_entry = Entry("filename", "TEXT")
database_tables = {
    t_user: Table(t_user, user_id, [Entry("ip_address", "TEXT"), Entry("user_agent", "TEXT"), Entry("platform", "TEXT"), Entry("browser", "TEXT"), Entry("mobile", "INTEGER")], [f"UNIQUE({user_id.name})"]),
    t_file: Table(t_file, filename_entry, [filegroup_id], [f"UNIQUE({filename_entry.name})"]),
    t_filegroup: Table(t_filegroup, filegroup_id, [Entry("groupname", "TEXT")], [f"UNIQUE({filegroup_id.name})"]),
    t_request: Table(t_request, request_id, [
        user_id, filegroup_id, Entry("date", "INTEGER"), Entry("referer", "TEXT"), Entry("status", "INTEGER")
    ], ["UNIQUE(request_id)"]),
}



def get_filegroup(filename: str, cursor: sql.Cursor) -> int:
    """
    get the user_id. Adds the user if not already existing
    """
    if sql_exists(cursor, t_file, [("filename", filename)]):
        return sql_select(cursor, t_file, [("filename", filename)])[0][1]
    else:
        group_id = sql_tablesize(cursor, t_filegroup)
        # pdebug("new file(group):", group_id, filename)
        # add group
        sql_insert(cursor, t_filegroup, [[group_id, filename]])
        # add file
        sql_insert(cursor, t_file, [[filename, group_id]])
        return group_id

def create_filegroups(cursor: sql.Cursor, filegroup_str: str):
    # filegroup_str: 'name1: file1, file2, file3; name2: file33'
    groups = filegroup_str.strip(";").split(";")
    pdebug("create_filegroups", groups)
    for group in groups:
        name, vals = group.split(":")
        # create/get group
        if sql_exists(cursor, t_filegroup, [("groupname", name)]):
            group_id = sql_select(cursor, t_filegroup, [("groupname", name)])[0][0]
        else:
            group_id = sql_tablesize(cursor, t_filegroup)
            sql_insert(cursor, t_filegroup, [(group_id, name)])
        # pdebug("create_filegroups: group_id", group_id)
        # create/edit file
        for filename in vals.split(","):
            if sql_exists(cursor, t_file, [("filename", filename)]):  # if exist, update
                cursor.execute(f"UPDATE {t_file} SET group_id = {group_id} WHERE filename = '{filename}'")
            else:
                sql_insert(cursor, t_file, [[filename, group_id]])

def get_files_from_dir_rec(p: str, files: list[str]):
    """recursivly append all files to files"""
    pdebug("get_files_from_dir_rec:",p)
    if path.isfile(p):
        files.append(p)
    elif path.isdir(p):
        for p_ in listdir(p):
            get_files_from_dir_rec(p + "/" + p_, files)

def get_auto_filegroup_str(location_and_dirs:list[tuple[str, str]], auto_group_filetypes:list[str]) -> str:
    """
    :param list of nginx locations and the corresponding directories
    :param auto_filetype_groups list of filetypes for auto grouping
    """
    files: list[str] = []
    start_i = 0
    for location, dir_ in location_and_dirs:
        get_files_from_dir_rec(dir_, files)
        # replace dir_ with location, eg /www/website with /
        for i in range(start_i, len(files)):
            files[i] = files[i].replace(dir_, location).replace("//", "/")
    filegroups = ""
    # create groups for each filetype
    for ft in auto_group_filetypes:
        filegroups += f"{ft}:"
        for file in files:
            if file.endswith(f".{ft}"):
                filegroups += f"{file},"
        filegroups = filegroups.strip(",") + ";"
    pdebug("get_auto_filegroup_str: found files:", files, "filegroups_str:", filegroups)
    return filegroups

def create_db(name, filegroup_str="", location_and_dirs:list[tuple[str, str]]=[], auto_group_filetypes=[]):
    """
    create the name with database_tables
    """
    print(f"creating database: '{name}'")
    conn = sql.connect(f"{name}")
    cursor = conn.cursor()
    for table in database_tables.values():
        cursor.execute(table.create_sql_str())
    filegroup_str = filegroup_str.strip("; ") + ";" + get_auto_filegroup_str(location_and_dirs, auto_group_filetypes)
    create_filegroups(cursor, filegroup_str)
    conn.commit()
    conn.close()


if __name__ == '__main__':
    create_db("test.db")
