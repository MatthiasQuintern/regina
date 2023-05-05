# from sys import path
import sqlite3 as sql
from csv import reader
from os import path, listdir
import pkg_resources
import re
from datetime import datetime as dt
# local
from .utility.sql_util import sanitize, sql_select, sql_exists, sql_insert, sql_tablesize, sql_max
from .utility.utility import pdebug, get_filepath, warning, pmessage
from .utility.globals import settings
from .db_operation.request import Request
from .utility.globals import visitor_agent_operating_systems, visitor_agent_browsers, settings

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
t_visitor = "visitor"
t_city = "city"
t_country = "country"
t_ip_range = "ip_range"

visitor_id = Entry("visitor_id", "INTEGER")
request_id = Entry("request_id", "INTEGER")
filegroup_id = Entry("group_id", "INTEGER")
ip_address_entry = Entry("ip_address", "INTEGER")
filename_entry = Entry("filename", "TEXT")
city_id = Entry("city_id", "INTEGER")
country_id = Entry("country_id", "INTEGER")
ip_range_id = Entry("ip_range_id", "INTEGER")

database_tables = {
    t_visitor: Table(t_visitor, visitor_id, [
            Entry("ip_address", "INTEGER"),
            Entry("visitor_agent", "TEXT"),
            Entry("platform", "TEXT"),
            Entry("browser", "TEXT"),
            Entry("mobile", "INTEGER"),
            Entry("is_human", "INTEGER"),
            ip_range_id,
        ],
        [f"UNIQUE({visitor_id.name})"]),
    t_file: Table(t_file, filename_entry,
            [filegroup_id],
            [f"UNIQUE({filename_entry.name})"]),
    t_filegroup: Table(t_filegroup, filegroup_id,
            [Entry("groupname", "TEXT")],
            [f"UNIQUE({filegroup_id.name})"]),
    t_request: Table(t_request, request_id, [
            visitor_id,
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



class Database:
    def __init__(self, database_path):
        self.conn = sql.connect(database_path)
        self.cur = self.conn.cursor()
        # verify that the database is created
        self.cur.execute("pragma schema_version")
        if self.cur.fetchone()[0] == 0:  # not created
            pdebug(f"Database.__init__: Creating database at {database_path}")
            with open(pkg_resources.resource_filename("regina", "sql/create_db.sql"), "r") as file:
                create_db = file.read()
            self.cur.execute(create_db)

    def __call__(self, s):
        """execute a command and return fetchall()"""
        self.cur.execute(s)
        return self.cur.fetchall()

    #
    # VISITOR
    #
    def visitor_exists(self, request) -> bool:
        if settings["hash_ip_address"]:
            ip_address = hash(request.ip_address)
        else:
            ip_address = request.ip_address
        if settings["unique_visitor_is_ip_address"]:
            return sql_exists(self.cur, t_visitor, [("ip_address", ip_address)])
        else:
            return sql_exists(self.cur, t_visitor, [("ip_address", ip_address), ("visitor_agent", request.visitor_agent)])

    def is_visitor_human(self, visitor_id: int):
        """
        check if they have a known platform AND browser
        check if at least one request did not result in an error (http status >= 400)
        """
        max_success_status = 400
        if settings["status_300_is_success"]: max_success_status = 300
        self.cur.execute(f"SELECT browser, platform FROM {t_visitor} WHERE visitor_id = {visitor_id}")
        browsers_and_platforms = self.cur.fetchall()
        if len(browsers_and_platforms) != 1:
            pdebug(f"is_visitor_human: {visitor_id} - could not find visitor or found too many")
            return False
        if not browsers_and_platforms[0][0] in visitor_agent_browsers:
            return False
        if not browsers_and_platforms[0][1] in visitor_agent_operating_systems:
            return False
        # check if has browser
        # self.cur.execute(f"SELECT EXISTS (SELECT 1 FROM {t_visitor} WHERE visitor_id = {visitor_id} AND platform IS NOT NULL AND browser IS NOT NULL)")
        # if no browser and platform
        # exists = self.cur.fetchone()
        # if exists is None or exists[0] == 0:
        #     return False
        # if human needs successful request
        if settings["human_needs_success"]:
            # check if at least request was successful (status < 400)
            self.cur.execute(f"SELECT EXISTS (SELECT 1 FROM {t_request} WHERE visitor_id = {visitor_id} AND status < {max_success_status})")
            if self.cur.fetchone()[0] == 1:
                # pdebug(f"is_visitor_human: Visitor {visitor_id} is human")
                pass
            else:
                # pdebug(f"is_visitor_human: Visitor {visitor_id} only had unsuccessful requests")
                return False
        return True

    def get_visitor_id(self, request: Request) -> int:
        """
        get the visitor_id. Adds the visitor if not already existing
        """
        if settings["hash_ip_address"]:
            ip_address = hash(request.ip_address)
        else:
            ip_address = request.ip_address

        if self.visitor_exists(request):
            if settings["unique_visitor_is_ip_address"]:
                visitor_id = sql_select(self.cur, t_visitor, [("ip_address", ip_address)])[0][0]
            else:
                visitor_id = sql_select(self.cur, t_visitor, [("ip_address", ip_address), ("visitor_agent", request.visitor_agent)])[0][0]
        else:  # new visitor 
            # new visitor_id is number of elements
            visitor_id = sql_max(self.cur, t_visitor, "visitor_id") + 1
            # pdebug("new visitor:", visitor_id, request.ip_address)
            platform, browser, mobile = get_os_browser_pairs_from_agent(request.visitor_agent)
            ip_range_id_val = 0
            if settings["get_visitor_location"]:
                ip_range_id_val = get_ip_range_id(self.cur, request.ip_address)
            is_human = 0 # is_visitor_human cannot be called until visitor is in db int(is_visitor_human(self.cur, visitor_id))
            self.cur.execute(f"INSERT INTO {t_visitor} (visitor_id, ip_address, visitor_agent, platform, browser, mobile, is_human, {ip_range_id.name}) VALUES ({visitor_id}, '{ip_address}', '{request.visitor_agent}', '{platform}', '{browser}', '{int(mobile)}', '{is_human}', '{ip_range_id_val}');")
        return visitor_id


    #
    # REQUEST
    #
    def request_exists(self, request: Request, visitor_id: int, group_id: int):
        # get all requests from same visitor to same location
        # TODO this looks wrong
        self.cur.execute(f"SELECT request_id, date FROM {t_request} WHERE visitor_id = '{visitor_id}' AND group_id = '{group_id}'")
        date0 = dt.fromtimestamp(request.time_local).strftime("%Y-%m-%d")
        for request_id, date1 in self.cur.fetchall():
            if settings["request_is_same_on_same_day"]:
                date1 = dt.fromtimestamp(date1).strftime("%Y-%m-%d")
                if date0 == date1:
                    pdebug(f"request_exists: Request is on same day as request {request_id}")
                    return True
        return False

    def add_request(self, request: Request) -> (int | None):
        """returns visitor_id if new request was added, else None"""
        # skip requests to blacklisted locations
        if request_blacklist:
            if re.fullmatch(request_blacklist, request.request_file):
                # pdebug(f"add_requests_to_db: request on blacklist '{request.request_file}'")
                return None
        # pdebug("add_requests_to_db:", i, "request:", request)
        visitor_id = self.get_visitor_id(request)
        self.conn.commit()
        group_id: int = self.get_filegroup(request.request_file)
        # check if request is unique
        if self.request_exists(request, visitor_id, group_id):
            # pdebug("request exists:", request)
            return None
        else:
            # pdebug("new request:", request)
            sql_insert(t_request, [[None, visitor_id, group_id, request.time_local, request.referer, request.status]])
            return visitor_id

    def add_requests(self, requests: list[Request]):
        added_requests = 0
        # check the new visitors later
        request_blacklist = settings["request_location_regex_blacklist"]
        new_visitors = []
        for i in range(len(requests)):
            visitor = self.add_request(requests[i])
            if visitor:
                new_visitors.append(visitor)

        # update the is_human column for all new visitors
        for visitor_id in new_visitors:
            if not sql_exists(self.cur, t_visitor, [(str(visitor_id), "visitor_id")]): continue
            is_human = self.is_visitor_human(visitor_id)
            self.cur.execute(f"SELECT * FROM {t_visitor} WHERE visitor_id = {visitor_id}")
            # pdebug(f"add_rq_to_db: {visitor_id} is_human? {is_human}, {self.cur.fetchall()}")
            if is_human:
                self.cur.execute(f"UPDATE {t_visitor} SET is_human = 1 WHERE visitor_id = {visitor_id}")
        self.conn.commit()
        pmessage(f"Collection Summary: Added {len(new_visitors)} new visitors and {added_requests} new requests.")

    #
    # FILE(GROUP)
    #
    def get_filegroup(self, filename: str) -> int:
        """
        get the filegroup
        returns the group where
        1) filename is the groupname
        2) the filetype of filename is the groupname
        3) new group with filename as gorupname
        """
        # pdebug(f"get_filegroup: {filename}")
        if sql_exists(self.cur, t_file, [("filename", filename)]):
            return sql_select(self.cur, t_file, [("filename", filename)])[0][1]
        else:
            suffix = filename.split('.')[-1]
            self.cur.execute(f"SELECT group_id FROM {t_filegroup} WHERE groupname = '{suffix}'")
            # self.cur.execute(f"SELECT group_id FROM {t_filegroup} WHERE groupname LIKE '%.{suffix}'")
            group_id_candidates = self.cur.fetchall()
            # pdebug(f"get_filegroup: file={filename} candidates={group_id_candidates}")
            if group_id_candidates:
                return group_id_candidates[0][0]
            else:  # add new group file filename
                group_id = sql_max(self.cur, t_filegroup, "group_id") + 1

                # pdebug("new file(group):", group_id, filename)
                # add group
                sql_insert(self.cur, t_filegroup, [[group_id, filename]])
                # add file
                sql_insert(self.cur, t_file, [[filename, group_id]])
                return group_id

    #
    # GEOIP
    #
    def get_ip_range_id(self, ip_address: int):
        self.cur.execute(f"SELECT {ip_range_id.name} FROM {t_ip_range} WHERE '{ip_address}' BETWEEN lower AND upper")
        results = self.cur.fetchall()
        ip_range_id_val = 0
        if len(results) == 0:
            pass
        elif len(results) > 1:
            warning(f"get_ip_range_id: Found multiple ip_ranges for ip_address={ip_address}: results={results}")
        else:
            ip_range_id_val = results[0][0]
        return ip_range_id_val

    def update_ip_range_id(self, visitor_id: int):
        self.cur.execute(f"SELECT ip_address FROM {t_visitor} WHERE visitor_id = {visitor_id}")
        results = self.cur.fetchall()
        if len(results) == 0:
            warning(f"update_ip_range_id: Invalid visitor_id={visitor_id}")
            return
        elif len(results) > 1:
            warning(f"update_ip_range_id: Found multiple ip_addresses for visitor_id={visitor_id}: results={results}")
            return
        ip_address = results[0][0]
        self.cur.execute(f"UPDATE {t_visitor} SET {ip_range_id.name} = '{get_ip_range_id(self.cur, ip_address)}' WHERE visitor_id = '{visitor_id}'")

def create_filegroups(cursor: sql.Cursor, filegroup_str: str):
    """
    TODO: make re-usable (alter groups when config changes)
    """
    # filegroup_str: 'name1: file1, file2, file3; name2: file33'
    groups = filegroup_str.strip(";").split(";")
    pdebug("create_filegroups:", groups)
    for group in groups:
        name, vals = group.split(":")
        # create/get group
        if sql_exists(cursor, t_filegroup, [("groupname", name)]):
            group_id = sql_select(cursor, t_filegroup, [("groupname", name)])[0][0]
        else:
            group_id = sql_max(cursor, t_filegroup, "group_id") + 1
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
    if len(location_and_dirs) > 0 and len(location_and_dirs[0]) == 2:
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
