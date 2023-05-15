# from sys import path
import sqlite3 as sql
from csv import reader
from os import path, listdir
import pkg_resources
import re
from datetime import datetime as dt

if __name__ == "__main__":  # make relative imports work as described here: https://peps.python.org/pep-0366/#proposed-change
    if __package__ is None:
        __package__ = "regina"
        import sys
        from os import path
        filepath = path.realpath(path.abspath(__file__))
        sys.path.insert(0, path.dirname(path.dirname(filepath)))

# local
from regina.utility.sql_util import replace_null, sanitize, sql_select, sql_exists, sql_tablesize
from regina.utility.utility import pdebug, get_filepath, warning, pmessage, is_blacklisted, is_whitelisted
from regina.utility.globals import settings
from regina.data_collection.request import Request
from regina.utility.globals import user_agent_platforms, user_agent_browsers, settings

"""
create reginas database as shown in the uml diagram database.uxf
"""

class Database:
    def __init__(self, database_path):
        self.conn = sql.connect(database_path)
        self.cur = self.conn.cursor()
        # verify that the database is created
        self.cur.execute("pragma schema_version")
        if self.cur.fetchone()[0] == 0:  # not created
            pdebug(f"Database.__init__: Creating new databse at {database_path}", lvl=1)
            with open(pkg_resources.resource_filename("regina", "sql/create_db.sql"), "r") as file:
                create_db = file.read()
            self.cur.executescript(create_db)
            self.conn.commit()
        else:
            pdebug(f"Database.__init__: Opening existing database at {database_path}", lvl=1)

    def __del__(self):
        self.cur.close()
        self.conn.commit()
        self.conn.close()

    def __call__(self, s):
        """execute a command and return fetchall()"""
        pdebug(f"Database: execute: \"{s}\"", lvl=4)
        self.cur.execute(s)
        return self.cur.fetchall()
    def execute(self, s):
        self.cur.execute(s)
    def fetchone(self):
        return self.cur.fetchone()

    #
    # VISITOR
    #
    def is_visitor_human(self, visitor_id: int):
        self.execute(f"SELECT is_human FROM visitor WHERE visitor_id = {visitor_id}")
        if self.fetchone()[0] == 1:
            return True
        return False

    def update_is_visitor_human(self, visitor_id: int):
        """
        check if they have a known platform AND browser
        if settings "human_needs_success": check if at least one request did not result in an error (http status >= 400)

        updates the visitor.is_human column
        @returns True if human, else False
        """
        def set_not_human(debug_str=""):
            pdebug(f"update_is_visitor_human: visitor_id={visitor_id:5} is not human: Failed check: {debug_str}", lvl=3)
            self.cur.execute(f"UPDATE visitor SET is_human = 0 WHERE visitor_id = {visitor_id}")
            return False

        self.cur.execute(f"SELECT browser_id, platform_id FROM visitor WHERE visitor_id = {visitor_id}")
        browser_id, platform_id = self.cur.fetchall()[0]
        browser = self.get_name("browser", browser_id)
        if not browser in user_agent_browsers:
            return set_not_human("browser")

        platform = self.get_name("platform", platform_id)
        if not platform in user_agent_platforms:
            return set_not_human("platform")

        max_success_status = 300
        if settings["data-collection"]["status_300_is_success"]: max_success_status = 400

        if settings["data-collection"]["human_needs_successful_request"]:
            # check if at least request was successful (status < 400)
            self.cur.execute(f"SELECT EXISTS (SELECT 1 FROM request WHERE visitor_id = {visitor_id} AND status < {max_success_status})")
            if self.cur.fetchone()[0] == 0:
                return set_not_human("successful request")
        # if here, is human
        self.cur.execute(f"UPDATE visitor SET is_human = 1 WHERE visitor_id = {visitor_id}")
        return True

    def get_visitor_id(self, request: Request, insert=True) -> tuple[int | None, bool]:
        """
        get the visitor_id:
        if settings unique_visitor_is_ip_address: Check if visitor with ip address exists
        else: check if visitor with ip_address, browser and platform exists

        @return visitor_id, is_new_visitor
        if visitor does not exist:
            if insert:  return visitor_id, True
            else:       return None, False
        else:       return visitor_id, False
        """
        ip_address = request.ip_address

        # if insert == True, ids will be int
        browser_id: int | None = self.get_id("browser", request.get_browser(), insert=insert)
        platform_id: int | None = self.get_id("platform", request.get_platform(), insert=insert)
        constraints = [("ip_address", ip_address)]
        if not settings["data-collection"]["unique_visitor_is_ip_address"]:
            if browser_id: constraints.append(("browser_id", browser_id))
            if platform_id: constraints.append(("platform_id", platform_id))
        is_new_visitor = False
        if not sql_exists(self.cur, "visitor", constraints):
            is_new_visitor = True
            if not insert:
                return None, False
            is_mobile = int(request.get_mobile())
            ip_range_id = 0
            if settings["data-collection"]["get_visitor_location"]:
                ip_range_id = self.get_ip_range_id(request.ip_address)
            is_human = 0  # update_is_visitor_human cannot be called until visitor is in db
            self.cur.execute(f"INSERT INTO visitor (ip_address, ip_range_id, platform_id, browser_id, is_mobile, is_human) VALUES ('{ip_address}', '{ip_range_id}', '{platform_id}', '{browser_id}', '{is_mobile}', '{is_human}');")
        visitor_id = sql_select(self.cur, "visitor", constraints)[0][0]
        return visitor_id, is_new_visitor

    def get_visitor_ids_for_date(self, date:str) -> list[int]:
        return [ visitor_id[0] for visitor_id in self(f"SELECT DISTINCT visitor_id FROM request WHERE {date}") ]

    def get_visitor_count(self) -> int:
        return sql_tablesize(self.cur, "visitor")

    #
    # REQUEST
    #
    def get_request_count(self) -> int:
        return sql_tablesize(self.cur, "request")

    def request_exists(self, request_timestamp: int, visitor_id: int, route_id: int):
        """
        Return if a request from same visitor was made to same route within the timespan set by the 'ignore_duplicate_requests_within_x_seconds' option
        """
        ignore_seconds = settings["data-collection"]["ignore_duplicate_requests_within_x_seconds"]
        time_min, time_max = max(0, request_timestamp - ignore_seconds), request_timestamp + ignore_seconds
        requests = self(f"SELECT request_id, time FROM request WHERE visitor_id = '{visitor_id}' AND  route_id = '{route_id}' AND time BETWEEN {time_min} AND {time_max}")
        if len(requests) > 0:
            pdebug(f"request_exists: Found {len(requests)} requests within {ignore_seconds} minutes (v_id={visitor_id}, r_id={route_id}, t={request_timestamp})")
            return True
        return False

    def add_request(self, request: Request) -> tuple[int | None, bool]:
        """
        @returns visitor_id, is_new_visitor
        if new request was added, else None
        """
        visitor_id, is_new_visitor = self.get_visitor_id(request)
        referer_id = self.get_id("referer", request.referer)
        route_id   = self.get_id("route", request.route)
        # check if request is unique
        if self.request_exists(request.time_local, visitor_id, route_id):
            pdebug("add_request: exists:", request, lvl=3)
            return None, is_new_visitor
        else:
            pdebug("add_request: added", request, lvl=3)
            self.cur.execute(f"INSERT INTO request (visitor_id, route_id, referer_id, time, status) VALUES ({visitor_id}, {route_id}, {referer_id}, {request.time_local}, {request.status})")
            return visitor_id, is_new_visitor

    def add_requests(self, requests: list[Request]):
        """
        Add a list of requests to the database
        Adds the visitors, if needed
        @returs added_request_count, visitors_count, new_visitors_count
        """
        added_request_count = 0
        # check the new visitors later
        visitors: set[int] = set()
        new_visitors: set[int] = set()
        for i in range(len(requests)):
            if     is_blacklisted(requests[i].route, settings["data-collection"]["request_route_blacklist"]): continue
            if not is_whitelisted(requests[i].route, settings["data-collection"]["request_route_whitelist"]): continue
            visitor_id, is_new_visitor = self.add_request(requests[i])
            if visitor_id:
                added_request_count += 1
                visitors.add(visitor_id)
                if is_new_visitor:
                    new_visitors.add(visitor_id)

        # update the is_human column for all new visitors
        for visitor_id in new_visitors:
            self.update_is_visitor_human(visitor_id)

        return added_request_count, len(visitors), len(new_visitors)


    def get_id(self, table: str, name: str, insert=True) -> int | None:
        """
        get the id of name in table
        if name is not in table:
            if insert: add and return id
            else: return None
        supported tables: platform, browser, referer, route, city
        """
        supported_tables = ["platform", "browser", "referer", "route", "city"]
        if not table in supported_tables: raise ValueError(f"table '{table}' is not supported ({supported_tables})")
        name = sanitize(replace_null(name))
        # if non existent, add name
        pdebug(f"get_id(table={table},\tname={name}", lvl=4)
        if not sql_exists(self.cur, table, [("name", name)], do_sanitize=False):  # double sanitizing might lead to problems with quotes
            if not insert: return None
            self.cur.execute(f"INSERT INTO {table} (name) VALUES ('{name}')")
        return self(f"SELECT {table}_id FROM {table} WHERE name = '{name}'")[0][0]

    def get_name(self, table: str, id_: int) -> (str | None):
        """
        get the name of id in table
        if id is not in table, returns None
        supported tables: platform, browser, referer, route, city
        """
        supported_tables = ["platform", "browser", "referer", "route", "city"]
        if not table in supported_tables: raise ValueError(f"table '{table}' is not supported ({supported_tables})")
        ret = self(f"SELECT name FROM {table} WHERE {table}_id = '{id_}'")
        if len(ret) == 0: return None
        return ret[0][0]



    #
    # GEOIP
    #
    def get_ip_range_id(self, ip_address: int) -> int:
        results = self(f"SELECT ip_range_id FROM ip_range WHERE '{ip_address}' BETWEEN low AND high")
        ip_range_id_val = 0
        if len(results) == 0:
            pass
        elif len(results) > 1:
            warning(f"get_ip_range_id: Found multiple ip_ranges for ip_address={ip_address}: results={results}")
        else:
            ip_range_id_val = results[0][0]
        return ip_range_id_val


    def update_ip_range_id(self, visitor_id: int):
        """
        update the ip_range_id column of visitor with visitor_id
        """
        results = self(f"SELECT ip_address FROM visitor WHERE visitor_id = '{visitor_id}'")
        if len(results) == 0:  # sanity checks
            warning(f"update_ip_range_id: Invalid visitor_id={visitor_id}")
            return
        elif len(results) > 1:
            warning(f"update_ip_range_id: Found multiple ip_addresses for visitor_id={visitor_id}: results={results}")
            return
        ip_address = results[0][0]
        self.cur.execute(f"UPDATE visitor SET ip_range_id = '{self.get_ip_range_id(ip_address)}' WHERE visitor_id = '{visitor_id}'")



    def get_country_id(self, name, code) -> int:
        """
        get the id of country of name
        if not present, insert and return id
        """
        name = sanitize(name)
        code = sanitize(code)
        if not sql_exists(self.cur, "country", [("name", name)], do_sanitize=False):
            self.cur.execute(f"INSERT INTO country (name, code) VALUES ('{name}', '{code}')")
        countries = self(f"SELECT country_id FROM country WHERE name = '{name}'")
        if len(countries) > 0:
            country_id_val = countries[0][0]
        else:
            warning(f"get_country_id: Could not get country_id for name='{name}'.")
            return 0
        assert(type(country_id_val) == int)
        return country_id_val

    def get_city_id(self, name, region, country_id) -> int:
        name = sanitize(name)
        region = sanitize(region)
        if not sql_exists(self.cur, "city", [("name", name), ("region", region), ("country_id", country_id)], do_sanitize=False):
            self.cur.execute(f"INSERT INTO city (name, region, country_id) VALUES ('{name}', '{region}', '{country_id}')")
        cities = sql_select(self.cur, "city", [("name", name), ("region", region), ("country_id", country_id)], do_sanitize=False)
        if len(cities) > 0:
            city_id_val = cities[0][0]
        else:
            warning(f"get_city_id: Could not get city_id for name='{name}', region='{region}' and country_id='{country_id}'.")
            return 0
        assert(type(city_id_val) == int)
        return city_id_val


    def update_geoip_tables(self, geoip_city_csv_path: str):
        """
        update the geoip data with the contents of the geoip_city_csv file

        Make sure to update the visitor.ip_range_id column for all visitors.
        In case something changed, they might point to a different city.

        TODO: update teh visitor.ip_range_id column to match (potentially) new city ip range
        """
        # indices for the csv
        FROM = 0; TO = 1; CODE = 2; COUNTRY = 3; REGION = 4; CITY = 5

        # FROM https://stackoverflow.com/questions/845058/how-to-get-line-count-of-a-large-file-cheaply-in-python (Quentin Pradet)
        def _count_generator(reader):
            b = reader(1024 * 1024)
            while b:
                yield b
                b = reader(1024*1024)
        def rawgencount(filename):
            with open(filename, "rb") as file:
                f_gen = _count_generator(file.raw.read)
                return sum( buf.count(b'\n') for buf in f_gen )

        pmessage(f"Recreating the GeoIP database from {geoip_city_csv_path}. This might take a long time...")
        row_count = rawgencount(geoip_city_csv_path)
        pmessage(f"Total rows: {row_count}")

        with open(geoip_city_csv_path, 'r') as file:
            csv = reader(file, delimiter=',', quotechar='"')
            file.seek(0)
            # execute only if file could be opened
            # delete all previous data
            self.cur.execute(f"DELETE FROM ip_range")
            self.cur.execute(f"DELETE FROM city")
            self.cur.execute(f"DELETE FROM country")
            self.conn.commit()
            self.cur.execute(f"VACUUM")

            # guarantees that unkown city/country will have id 0
            self.cur.execute(f"INSERT INTO country (country_id, name, code) VALUES (0, 'Unknown', 'XX') ")
            self.cur.execute(f"INSERT INTO city (city_id, name, region) VALUES (0, 'Unknown', 'Unkown') ")

            # for combining city ranges into a 'City in <Country>' range
            # country_id for the range that was last added (for combining multiple csv rows in one ip_range)
            RANGE_DONE = -1
            combine_range_country_id = RANGE_DONE
            combine_range_country_name = ""
            combine_range_low = RANGE_DONE
            combine_range_high = RANGE_DONE

            def add_range(low, high, city_name, region, country_id):
                city_id = self.get_city_id(city_name, region, country_id)
                pdebug(f"update_ip_range_id: Adding range for city={city_name:20}, country_id={country_id:3}, low={low:16}, high={high:16}", lvl=2)
                self.cur.execute(f"INSERT INTO ip_range (low, high, city_id) VALUES ({low}, {high}, {city_id})")
            for i, row in enumerate(csv, 1):
                # if i % 100 == 0:
                pmessage(f"Updating GeoIP database: {i:7}/{row_count} ({100.0*i/row_count:.2f}%)", end="\r")
                # these might contain problematic characters (')
                # row[CITY] = sanitize(row[CITY])
                if row[COUNTRY] == "United Kingdom of Great Britain and Northern Ireland":
                    row[COUNTRY] = "United Kingdom"
                # row[COUNTRY] = sanitize(row[COUNTRY])
                # row[REGION] = sanitize(row[REGION])

                # make sure country exists
                country_id = self.get_country_id(row[COUNTRY], row[CODE])
                # only add cities for countries the user is interested in
                if row[CODE] in settings["data-collection"]["get_cities_for_countries"]:
                    add_range(row[FROM], row[TO], row[CITY], row[REGION], country_id)
                else:
                    # if continuing 
                    if combine_range_country_id != RANGE_DONE:
                        # if continuing previous range, extend the upper range limit
                        if combine_range_country_id == country_id:
                            combine_range_high = row[TO]
                        else:  # new range for country, append
                            add_range(combine_range_low, combine_range_high, f"City in {combine_range_country_name}", f"Region in {combine_range_country_name}", combine_range_country_id)
                            combine_range_country_id = RANGE_DONE
                    # not elif, this has to be executed if previous else was executed
                    if combine_range_country_id == RANGE_DONE :  # currently in new range, combine with later ranges
                        combine_range_country_id = country_id
                        combine_range_country_name = row[COUNTRY]
                        combine_range_low = row[FROM]
                        combine_range_high = row[TO]
            if combine_range_country_id >= 0:  # last range , append
                add_range(combine_range_low, combine_range_high, f"City in {combine_range_country_name}", f"Region in {combine_range_country_name}", combine_range_country_id)


    #
    # REQUEST
    #
    # TIME/DATE
    def get_earliest_timestamp(self) -> int:
        """return the earliest time as unixepoch"""
        date = self(f"SELECT MIN(time) FROM request")[0][0]
        if not isinstance(date, int): return 0
        else: return date

    def get_latest_timestamp(self) -> int:
        """return the latest time as unixepoch"""
        date = self(f"SELECT MAX(time) FROM request")[0][0]
        if not isinstance(date, int): return 0
        else: return date

    def get_months_where(self, date_constraint:str) -> list[str]:
        """get a list of all dates in yyyy-mm format
        @param date_constraint parameter sqlite constraint
        """
        dates = self.get_days_where(date_constraint)
        date_dict = {}
        for date in dates:
            date_without_day = date[0:date.rfind('-')]
            date_dict[date_without_day] = 0
        return list(date_dict.keys())

    def get_days_where(self, date_constraint:str) -> list[str]:
        """get a list of all dates in yyyy-mm-dd format
        @param date_constraint parameter sqlite constraint
        """
        days = [ date[0] for date in self(f"SELECT DISTINCT DATE(time, 'unixepoch') FROM request WHERE {date_constraint}") ]  # fetchall returns tuples (date, ) 
        days.sort()
        return days



if __name__ == '__main__':
    db = Database("test.db")
