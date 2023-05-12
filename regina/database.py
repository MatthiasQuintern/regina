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
from regina.utility.sql_util import replace_null, sanitize, sql_select, sql_exists
from regina.utility.utility import pdebug, get_filepath, warning, pmessage, is_blacklisted, is_whitelisted
from regina.utility.globals import settings
from regina.data_collection.request import Request
from regina.utility.globals import visitor_agent_operating_systems, visitor_agent_browsers, settings

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
            pdebug(f"Database.__init__: Creating database at {database_path}")
            with open(pkg_resources.resource_filename("regina", "sql/create_db.sql"), "r") as file:
                create_db = file.read()
            self.cur.executescript(create_db)
            self.conn.commit()

    def __call__(self, s):
        """execute a command and return fetchall()"""
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
        """
        check if they have a known platform AND browser
        if settings "human_needs_success": check if at least one request did not result in an error (http status >= 400)
        """
        max_success_status = 400
        if settings["status_300_is_success"]: max_success_status = 300
        self.cur.execute(f"SELECT browser_id, platform_id FROM visitor WHERE visitor_id = {visitor_id}")
        browsers_and_platforms = self.cur.fetchall()
        if len(browsers_and_platforms) != 1:
            pdebug(f"is_visitor_human: {visitor_id} - could not find visitor or found too many")
            return False
        browser = self.get_name("browser", browsers_and_platforms[0][0])
        if not browser in visitor_agent_browsers:
            return False
        platform = self.get_name("platform", browsers_and_platforms[0][1])
        if not platform in visitor_agent_operating_systems:
            return False
        if settings["human_needs_success"]:
            # check if at least request was successful (status < 400)
            self.cur.execute(f"SELECT EXISTS (SELECT 1 FROM request WHERE visitor_id = {visitor_id} AND status < {max_success_status})")
            if self.cur.fetchone()[0] == 1:
                # pdebug(f"is_visitor_human: Visitor {visitor_id} is human")
                pass
            else:
                # pdebug(f"is_visitor_human: Visitor {visitor_id} only had unsuccessful requests")
                return False
        return True

    def get_visitor_id(self, request: Request, insert=True) -> int | None:
        """
        get the visitor_id. Adds the visitor if not already existing
        """
        """
        get the visitor_id:
        If settings unique_visitor_is_ip_address: Check if visitor with ip address exists
        Else: check if visitor with ip_address, browser and platform exists

        If visitor does not exist and insert: insert, return id
        Else: return None
        """
        if settings["hash_ip_address"]:
            ip_address = hash(request.ip_address)
        else:
            ip_address = request.ip_address

        # if insert == True, ids will be int
        browser_id: int | None = self.get_id("browser", request.get_browser(), insert=insert)
        platform_id: int | None = self.get_id("platform", request.get_platform(), insert=insert)
        constraints = [("ip_address", ip_address)]
        if not settings["unique_visitor_is_ip_address"]:
            if browser_id: constraints.append(("browser_id", browser_id))
            if platform_id: constraints.append(("platform_id", platform_id))
        require_update_is_human = False
        if not sql_exists(self.cur, "visitor", constraints):
            require_update_is_human = True
            if not insert:
                return None
            is_mobile = int(request.get_mobile())
            ip_range_id = 0
            if settings["get_visitor_location"]:
                ip_range_id = self.get_ip_range_id(request.ip_address)
            is_human = 0  # is_visitor_human cannot be called until visitor is in db
            self.cur.execute(f"INSERT INTO visitor (ip_address, ip_range_id, platform_id, browser_id, is_mobile, is_human, ip_range_id) VALUES ('{ip_address}', '{ip_range_id}', '{platform_id}', '{browser_id}', '{is_mobile}', '{is_human}');")
        visitor_id = sql_select(self.cur, "visitor", constraints)[0][0]
        # TODO: if requests are not added yet, visitor might not be recognized since it does not have a successful requets yet
        if require_update_is_human:
            is_human = self.is_visitor_human(visitor_id)
            if is_human:
                self.cur.execute(f"UPDATE visitor SET is_human = 1 WHERE visitor_id = {visitor_id}")
        return visitor_id


    #
    # REQUEST
    #
    def request_exists(self, request: Request, visitor_id: int, route_id: int):
        """
        Check if a request from same visitor was made to same location in the same day, if setting "request_is_same_on_same_day" is True
        If not, always returns False
        """
        if not settings["request_is_same_on_same_day"]: return False
        # get all requests from same visitor to same route
        self.cur.execute(f"SELECT request_id, time FROM request WHERE visitor_id = '{visitor_id}' AND  = route_id = '{route_id}'")
        # check if on same day
        date0 = dt.fromtimestamp(request.time_local).strftime("%Y-%m-%d")
        for request_id, date1 in self.cur.fetchall():
            date1 = dt.fromtimestamp(date1).strftime("%Y-%m-%d")
            if date0 == date1:
                pdebug(f"request_exists: Request is on same day as request {request_id}")
                return True
        return False

    def add_request(self, request: Request) -> (int | None):
        """returns visitor_id if new request was added, else None"""
        visitor_id = self.get_visitor_id(request)
        self.conn.commit()
        # browser_id = self.get_id("browser", request.get_browser())
        # platform_id = self.get_id("platform", request.get_platform())
        referer_id = self.get_id("referer", request.referer)
        route_id   = self.get_id("route", request.route)
        # check if request is unique
        if self.request_exists(request, visitor_id, route_id):
            # pdebug("request exists:", request)
            return None
        else:
            # pdebug("new request:", request)
            self.cur.execute(f"INSERT INTO request (visitor_id, route_id, referer_id, time, status) VALUES ({visitor_id}, {route_id}, {referer_id}, {request.time_local}, {request.status})")
            return visitor_id

    def add_requests(self, requests: list[Request]):
        added_requests = 0
        # check the new visitors later
        new_visitors = []
        for i in range(len(requests)):
            if     is_blacklisted(requests[i].request_route, settings["request_route_blacklist"]): continue
            if not is_whitelisted(requests[i].request_route, settings["request_route_whitelist"]): continue
            visitor = self.add_request(requests[i])
            if visitor:
                new_visitors.append(visitor)

        # update the is_human column for all new visitors
        for visitor_id in new_visitors:
            # TODO this does not look right
            if not sql_exists(self.cur, "visitor", [("visitor_id", visitor_id)]): continue
            # pdebug(f"add_rq_to_db: {visitor_id} is_human? {is_human}, {self.cur.fetchall()}")
        self.conn.commit()
        pmessage(f"Collection Summary: Added {len(new_visitors)} new visitors and {added_requests} new requests.")


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
        if not sql_exists(self.cur, table, [("name", name)]):
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
        # TODO check if this returns tuple or value
        return ret[0]



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
        results = self(f"SELECT ip_address FROM visitor WHERE visitor_id = {visitor_id}")
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
        if not sql_exists(self.cur, "country", [("name", name)]):
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
        if not sql_exists(self.cur, "city", [("name", name), ("region", region), ("country_id", country_id)]):
            self.cur.execute(f"INSERT INTO city (name, region, country_id) VALUES ('{name}', '{region}', '{country_id}')")
        cities = sql_select(self.cur, "city", [("name", name), ("region", region), ("country_id", country_id)])
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
        with open(geoip_city_csv_path, 'r') as file:
            csv = reader(file, delimiter=',', quotechar='"')
            # execute only if file could be opened
            # delete all previous data
            self.cur.execute(f"DELETE FROM ip_range")
            self.cur.execute(f"DELETE FROM city")
            self.cur.execute(f"DELETE FROM country")
            self.cur.execute(f"VACUUM")

            # guarantees that unkown city/country will have id 0
            self.cur.execute(f"INSERT INTO country (country_id, name, code) VALUES (0, 'Unknown', 'XX') ")
            self.cur.execute(f"INSERT INTO city (city_id, name, region) VALUES (0, 'Unknown', 'Unkown') ")
            print(f"Recreating the geoip database from {geoip_city_csv_path}. This might take a long time...")

            # for combining city ranges into a 'City in <Country>' range
            # country_id for the range that was last added (for combining multiple csv rows in one ip_range)
            RANGE_DONE = -1
            combine_range_country_id = RANGE_DONE
            combine_range_country_name = ""
            combine_range_low = RANGE_DONE
            combine_range_high = RANGE_DONE

            def add_range(low, high, city_name, region, country_id):
                city_id = self.get_city_id(city_name, region, country_id)
                pdebug(f"update_ip_range_id: Adding range for city={city_name}, country_id={country_id}, low={low}, high={high}")
                self.cur.execute(f"INSERT INTO ip_range (low, high, city_id) VALUES ({low}, {high}, {city_id})")
            for row in csv:
                # these might contain problematic characters (')
                row[CITY] = sanitize(row[CITY])
                row[COUNTRY] = sanitize(row[COUNTRY])
                row[REGION] = sanitize(row[REGION])

                # make sure country exists
                country_id = self.get_country_id(row[COUNTRY], row[CODE])
                # only add cities for countries the user is interested in
                if row[CODE] in settings["get_cities_for_countries"]:
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
    def get_earliest_date(self) -> int:
        """return the earliest time as unixepoch"""
        date = self(f"SELECT MIN(time) FROM request")[0][0]
        if not isinstance(date, int): return 0
        else: return date

    def get_latest_date(self) -> int:
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
