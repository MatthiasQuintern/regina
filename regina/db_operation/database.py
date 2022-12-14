# from sys import path
import sqlite3 as sql
from csv import reader
from os import path, listdir
# local
from regina.utility.sql_util import sanitize, sql_select, sql_exists, sql_insert, sql_tablesize
from regina.utility.utility import pdebug
from regina.utility.globals import settings

"""
create reginas database as shown in the uml diagram database.uxf
"""

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
t_city = "city"
t_country = "country"
t_ip_range = "ip_range"

user_id = Entry("user_id", "INTEGER")
request_id = Entry("request_id", "INTEGER")
filegroup_id = Entry("group_id", "INTEGER")
ip_address_entry = Entry("ip_address", "TEXT")
filename_entry = Entry("filename", "TEXT")
city_id = Entry("city_id", "INTEGER")
country_id = Entry("country_id", "INTEGER")
ip_range_id = Entry("ip_range_id", "INTEGER")

database_tables = {
    t_user: Table(t_user, user_id, [
            Entry("ip_address", "INTEGER"),
            Entry("user_agent", "TEXT"),
            Entry("platform", "TEXT"),
            Entry("browser", "TEXT"),
            Entry("mobile", "INTEGER"),
            Entry("is_human", "INTEGER"),
            ip_range_id,
        ],
        [f"UNIQUE({user_id.name})"]),
    t_file: Table(t_file, filename_entry,
            [filegroup_id],
            [f"UNIQUE({filename_entry.name})"]),
    t_filegroup: Table(t_filegroup, filegroup_id,
            [Entry("groupname", "TEXT")],
            [f"UNIQUE({filegroup_id.name})"]),
    t_request: Table(t_request, request_id, [
            user_id,
            filegroup_id,
            Entry("date", "INTEGER"),
            Entry("referer", "TEXT"),
            Entry("status", "INTEGER")
        ],
        ["UNIQUE(request_id)"]),
    t_ip_range: Table(t_ip_range, ip_range_id, [
            Entry("lower", "INTEGER"),
            Entry("upper", "INTEGER"),
            city_id,
        ],
        [f"UNIQUE({ip_range_id.name})"]),
    t_city: Table(t_city, city_id, [
            country_id,
            Entry("name", "TEXT"),
            Entry("region", "TEXT"),
        ],
        [f"UNIQUE({city_id.name})"]),
    t_country: Table(t_country, country_id, [
            Entry("name", "TEXT"),
            Entry("code", "TEXT"),
        ],
        [f"UNIQUE({country_id.name})"]),
}



def get_filegroup(filename: str, cursor: sql.Cursor) -> int:
    """
    get the filegroup
    returns the group where
    1) filename is the groupname
    2) the filetype of filename is the groupname
    3) new group with filename as gorupname
    """
    # pdebug(f"get_filegroup: {filename}")
    if sql_exists(cursor, t_file, [("filename", filename)]):
        return sql_select(cursor, t_file, [("filename", filename)])[0][1]
    else:
        suffix = filename.split('.')[-1]
        cursor.execute(f"SELECT group_id FROM {t_filegroup} WHERE groupname = '{suffix}'")
        # cursor.execute(f"SELECT group_id FROM {t_filegroup} WHERE groupname LIKE '%.{suffix}'")
        group_id_candidates = cursor.fetchall()
        # pdebug(f"get_filegroup: file={filename} candidates={group_id_candidates}")
        if group_id_candidates:
            return group_id_candidates[0][0]
        else:  # add new group file filename
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
    pdebug("create_filegroups:", groups)
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

def get_country_id(cur:sql.Cursor, name, code, country_tablesize):
    # countries = sql_select(cur, t_country, [("name", name)])
    cur.execute(f"SELECT {country_id.name} FROM {t_country} WHERE name = '{name}'")
    countries = cur.fetchall()
    if len(countries) > 0:
        country_id_val = countries[0][0]
    else:  # insert new country
        country_id_val = country_tablesize
        # pdebug(f"update_geoip_tables: Adding country #{country_id_val}, name={name}")
        cur.execute(f"INSERT INTO {t_country} ({country_id.name}, name, code) VALUES ({country_id_val}, '{name}', '{code}')")
        country_tablesize += 1
    return country_id_val, country_tablesize

def get_city_id(cur: sql.Cursor, name, region, country_id, city_tablesize):
    # cities = sql_select(cur, t_city, [("name", name)])
    cur.execute(f"SELECT {city_id.name} FROM {t_city} WHERE name = '{name}'")
    cities = cur.fetchall()
    if len(cities) > 0:
        city_id_val = cities[0][0]
    else:  # insert new city
        city_id_val = city_tablesize
        # pdebug(f"update_geoip_tables: Adding city #{city_id_val}, name={row[CITY]}, country={country_id_val}")
        cur.execute(f"INSERT INTO {t_city} ({city_id.name}, name, region, country_id) VALUES ({city_id_val}, '{name}', '{region}', '{country_id}')")
        city_tablesize += 1
    return city_id_val, city_tablesize

def update_geoip_tables(cur: sql.Cursor, geoip_city_csv: str):
    FROM = 0; TO = 1; CODE = 2; COUNTRY = 3; REGION = 4; CITY = 5
    ip_range_id_val = 0
    with open(geoip_city_csv, 'r') as file:
        # delete all previous data
        cur.execute(f"DELETE FROM {t_ip_range}")
        cur.execute(f"VACUUM")
        csv = reader(file, delimiter=',', quotechar='"')


        # guarantees that unkown city/country will have id 0
        if not sql_exists(cur, t_country, [("name", "Unknown")]):
            cur.execute(f"INSERT INTO {t_country} ({country_id.name}, name, code) VALUES (0, 'Unknown', 'XX') ")
        if not sql_exists(cur, t_city, [("name", "Unknown")]):
            cur.execute(f"INSERT INTO {t_city} ({city_id.name}, name, region) VALUES (0, 'Unknown', 'Unkown') ")
        country_tablesize = sql_tablesize(cur, t_country)
        city_tablesize = sql_tablesize(cur, t_city)
        print(f"Recreating the geoip database from {geoip_city_csv}. This might take a long time...")
        combine_range_country_id = 0
        combine_range_lower = -1
        combine_range_upper = -1
        combine_range_country_name = ""
        for row in csv:
            # these might contain problematic characters (')
            row[CITY] = sanitize(row[CITY])
            row[COUNTRY] = sanitize(row[COUNTRY])
            row[REGION] = sanitize(row[REGION])

            # make sure country exists
            country_id_val, country_tablesize = get_country_id(cur, row[COUNTRY], row[CODE], country_tablesize)
            if row[CODE] in settings["get_cities_for_countries"]:
                # make sure city exists
                city_id_val, city_tablesize = get_city_id(cur, row[CITY], row[REGION], country_id_val, city_tablesize)
                pdebug(f"update_ip_range_id: ip_range_id={ip_range_id_val}, Adding range for city={row[CITY]}, country={row[COUNTRY]}, lower={row[FROM]}, upper={row[TO]}")
                cur.execute(f"INSERT INTO {t_ip_range} ({ip_range_id.name}, lower, upper, {city_id.name}) VALUES ({ip_range_id_val}, {row[FROM]}, {row[TO]}, {city_id_val})")
                ip_range_id_val += 1
            else:
                if combine_range_country_id >= 0:
                    if combine_range_country_id == country_id_val: combine_range_upper = row[TO]
                    else:  # new range for country, append
                        # get id for dummy city
                        pdebug(f"update_ip_range_id: ip_range_id={ip_range_id_val}, Adding combined range for country={combine_range_country_name}, lower={combine_range_lower}, upper={combine_range_upper}")
                        city_id_val, city_tablesize = get_city_id(cur, f"City in {combine_range_country_name}", f"Region in {combine_range_country_name}", combine_range_country_id, city_tablesize)
                        cur.execute(f"INSERT INTO {t_ip_range} ({ip_range_id.name}, lower, upper, {city_id.name}) VALUES ({ip_range_id_val}, {combine_range_lower}, {combine_range_upper}, {city_id_val})")
                        ip_range_id_val += 1
                    combine_range_country_id = -1
                if combine_range_country_id < 0 :  # combine with later ranges
                    combine_range_country_id = country_id_val
                    combine_range_lower = row[FROM]
                    combine_range_upper = row[TO]
                    combine_range_country_name = row[COUNTRY]
        if combine_range_country_id >= 0:  # last range , append
            # get id for dummy city
            pdebug(f"update_ip_range_id: ip_range_id={ip_range_id_val}, Adding combined range for country={combine_range_country_name}, lower={combine_range_lower}, upper={combine_range_upper}")
            city_id_val, city_tablesize = get_city_id(cur, f"City in {combine_range_country_name}", f"Region in {combine_range_country_name}", combine_range_country_id, city_tablesize)
            cur.execute(f"INSERT INTO {t_ip_range} ({ip_range_id.name}, lower, upper, {city_id.name}) VALUES ({ip_range_id_val}, {combine_range_lower}, {combine_range_upper}, {city_id_val})")
            ip_range_id_val += 1


def create_db(db_name, filegroup_str="", location_and_dirs:list[tuple[str, str]]=[], auto_group_filetypes=[]):
    """
    create the name with database_tables
    """
    print(f"creating database: '{db_name}'")
    conn = sql.connect(f"{db_name}")
    cursor = conn.cursor()
    for table in database_tables.values():
        cursor.execute(table.create_sql_str())
    filegroup_str = filegroup_str.strip("; ") + ";" + get_auto_filegroup_str(location_and_dirs, auto_group_filetypes)
    create_filegroups(cursor, filegroup_str)
    cursor.close()
    conn.commit()
    conn.close()


if __name__ == '__main__':
    create_db("test.db")
