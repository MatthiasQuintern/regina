import sqlite3 as sql
from re import fullmatch, match
from ipaddress import IPv4Address, ip_address
from time import mktime
from datetime import datetime as dt
from regina.db_operation.database import t_request, t_visitor, t_file, t_filegroup, t_ip_range, database_tables, get_filegroup, ip_range_id
from regina.utility.sql_util import sanitize, sql_select, sql_exists, sql_insert, sql_tablesize
from regina.utility.utility import pdebug, warning, pmessage
from regina.utility.globals import visitor_agent_operating_systems, visitor_agent_browsers, settings

"""
collect information from the access log and put it into the database
"""
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aut", "Sep", "Oct", "Nov", "Dec"]



class Request:
    def __init__(self, ip_address="", time_local="", request_type="", request_file="", request_protocol="", status="", bytes_sent="", referer="", visitor_agent=""):
        self.ip_address = int(IPv4Address(sanitize(ip_address)))
        self.time_local = 0
        #[20/Nov/2022:00:47:36 +0100]
        m =  match(r"\[(\d+)/(\w+)/(\d+):(\d+):(\d+):(\d+).*\]", time_local)
        if m:
            g = m.groups()
            try:
                if g[1] in months:
                    datetime_ = dt(int(g[2]), months.index(g[1])+1, int(g[0]), int(g[3]), int(g[4]), int(g[5]))
                    # pdebug(f"Request __init__: datetime {datetime_}, from {g}")
                    self.time_local = int(mktime(datetime_.timetuple()))
                else:
                    warning(f"Request:__init__: Unkown month: '{g[1]}'. Using timestamp {self.time_local}")
            except Exception as e:
                warning(f"Request:__init__: {e}")
        else:
            warning(f"Request:__init__: Could not match time: '{time_local}'")
        self.request_type = sanitize(request_type)
        self.request_file = sanitize(request_file)
        self.request_protocol = sanitize(request_protocol)
        self.status = sanitize(status)
        self.bytes_sent = sanitize(bytes_sent)
        self.referer = sanitize(referer)
        self.visitor_agent = sanitize(visitor_agent)

    def __repr__(self):
        return f"{self.ip_address} - {self.time_local} - {self.request_file} - {self.visitor_agent} - {self.status}"

re_remote_addr = r"[0-9a-fA-F.:]+"
re_remote_visitor = ".*"
re_time_local = r"\[.+\]"
re_request = r'"[^"]+"'
re_status = r'\d+'
re_body_bytes_sent = r'\d+'
re_http_referer = r'"([^"]*)"'
re_http_visitor_agent = r'"([^"]*)"'
re_log_format: str = f'({re_remote_addr}) - ({re_remote_visitor}) ({re_time_local}) ({re_request}) ({re_status}) ({re_body_bytes_sent}) {re_http_referer} {re_http_visitor_agent}'
def parse_log(logfile:str) -> list[Request]:
    """
    create Request objects from each line in the logfile
    """
    requests = []
    with open(logfile, "r") as file:
        lines = file.readlines()
    for line in lines:
        m = match(re_log_format, line)
        if m is None:
            warning(f"parse_log: Unmatched line: '{line}'")
            continue
        # print(m.groups())
        g = m.groups()
        request_ = m.groups()[3].split(" ")
        if len(request_) != 3:
            warning(f"parse_log: len('{m.groups()[3]}'.split(' ')) is {len(request_)} and not 3")
            continue
        requests.append(Request(ip_address=g[0], time_local=g[2],
                                request_type=request_[0], request_file=request_[1], request_protocol=request_[2],
                                status=g[4], bytes_sent=g[5], referer=g[6], visitor_agent=g[7]))
    return requests


def visitor_exists(cursor, request) -> bool:
    if settings["unique_visitor_is_ip_address"]:
        return sql_exists(cursor, t_visitor, [("ip_address", request.ip_address)])
    else:
        return sql_exists(cursor, t_visitor, [("ip_address", request.ip_address), ("visitor_agent", request.visitor_agent)])

def get_visitor_id(request: Request, cursor: sql.Cursor) -> int:
    """
    get the visitor_id. Adds the visitor if not already existing
    """
    # if visitor exists
    if visitor_exists(cursor, request):
        if settings["unique_visitor_is_ip_address"]:
            visitor_id = sql_select(cursor, t_visitor, [("ip_address", request.ip_address)])[0][0]
        else:
            visitor_id = sql_select(cursor, t_visitor, [("ip_address", request.ip_address), ("visitor_agent", request.visitor_agent)])[0][0]
    else:  # new visitor 
        # new visitor_id is number of elements
        visitor_id: int = sql_tablesize(cursor, t_visitor)
        # pdebug("new visitor:", visitor_id, request.ip_address)
        platform, browser, mobile = get_os_browser_pairs_from_agent(request.visitor_agent)
        ip_range_id_val = 0
        if settings["get_visitor_location"]:
            ip_range_id_val = get_ip_range_id(cursor, request.ip_address)
        is_human = 0 # is_visitor_human cannot be called until visitor is in db int(is_visitor_human(cursor, visitor_id))
        cursor.execute(f"INSERT INTO {t_visitor} (visitor_id, ip_address, visitor_agent, platform, browser, mobile, is_human, {ip_range_id.name}) VALUES ({visitor_id}, '{request.ip_address}', '{request.visitor_agent}', '{platform}', '{browser}', '{int(mobile)}', '{is_human}', '{ip_range_id_val}');")
    return visitor_id

def is_visitor_human(cur: sql.Cursor, visitor_id: int):
    global settings
    """
    check if they have a known platform AND browser
    check if at least one request did not result in an error (http status >= 400)
    """
    max_success_status = 400
    if settings["status_300_is_success"]: max_success_status = 300
    cur.execute(f"SELECT browser, platform FROM {t_visitor} WHERE visitor_id = {visitor_id}")
    browsers_and_platforms = cur.fetchall()
    if len(browsers_and_platforms) != 1:
        pdebug(f"is_visitor_human: {visitor_id} - could not find visitor or found too many")
        return False
    if not browsers_and_platforms[0][0] in visitor_agent_browsers:
        return False
    if not browsers_and_platforms[0][1] in visitor_agent_operating_systems:
        return False
    # check if has browser
    # cur.execute(f"SELECT EXISTS (SELECT 1 FROM {t_visitor} WHERE visitor_id = {visitor_id} AND platform IS NOT NULL AND browser IS NOT NULL)")
    # if no browser and platform
    # exists = cur.fetchone()
    # if exists is None or exists[0] == 0:
    #     return False
    # if human needs successful request
    if settings["human_needs_success"]:
        # check if at least request was successful (status < 400)
        cur.execute(f"SELECT EXISTS (SELECT 1 FROM {t_request} WHERE visitor_id = {visitor_id} AND status < {max_success_status})")
        if cur.fetchone()[0] == 1:
            # pdebug(f"is_visitor_human: Visitor {visitor_id} is human")
            pass
        else:
            # pdebug(f"is_visitor_human: Visitor {visitor_id} only had unsuccessful requests")
            return False
    # visitor is human
    return True

def request_exists(cur: sql.Cursor, request: Request, visitor_id: int, group_id: int):
    # get all requests from same visitor to same location
    cur.execute(f"SELECT request_id, date FROM {t_request} WHERE visitor_id = '{visitor_id}' AND group_id = '{group_id}'")
    date0 = dt.fromtimestamp(request.time_local).strftime("%Y-%m-%d")
    for request_id, date1 in cur.fetchall():
        if settings["request_is_same_on_same_day"]:
            date1 = dt.fromtimestamp(date1).strftime("%Y-%m-%d")
            if date0 == date1:
                pdebug(f"request_exists: Request is on same day as request {request_id}")
                return True
    return False


# re_visitor_agent = r"(?: ?([\w\- ]+)(?:\/([\w.]+))?(?: \(([^()]*)\))?)"
# 1: platform, 2: version, 3: details
def get_os_browser_pairs_from_agent(visitor_agent):
    # for groups in findall(re_visitor_agent, visitor_agent):
    operating_system = ""
    browser = ""
    mobile = "Mobi" in visitor_agent
    for os in visitor_agent_operating_systems:
        if os in visitor_agent:
            operating_system = os
            break
    for br in visitor_agent_browsers:
        if br in visitor_agent:
            browser = br
            break
    # if not operating_system or not browser: print(f"Warning: get_os_browser_pairs_from_agent: Could not find all information for agent '{visitor_agent}', found os: '{operating_system}' and browser: '{browser}'")
    return operating_system, browser, mobile


def get_ip_range_id(cur: sql.Cursor, ip_address: int):
    cur.execute(f"SELECT {ip_range_id.name} FROM {t_ip_range} WHERE '{ip_address}' BETWEEN lower AND upper")
    results = cur.fetchall()
    ip_range_id_val = 0
    if len(results) == 0:
        pass
    elif len(results) > 1:
        warning(f"get_countries: Found multiple ip_ranges for ip_address={ip_address}: results={results}")
    else:
        ip_range_id_val = results[0][0]
    return ip_range_id_val

def update_ip_range_id(cur: sql.Cursor, visitor_id: int):
    cur.execute(f"SELECT ip_address FROM {t_visitor} WHERE visitor_id = {visitor_id}")
    results = cur.fetchall()
    if len(results) == 0:
        warning(f"update_ip_range_id: Invalid visitor_id={visitor_id}")
        return
    elif len(results) > 1:
        warning(f"update_ip_range_id: Found multiple ip_addresses for visitor_id={visitor_id}: results={results}")
        return
    ip_address = results[0][0]
    cur.execute(f"UPDATE {t_visitor} SET {ip_range_id.name} = '{get_ip_range_id(cur, ip_address)}' WHERE visitor_id = '{visitor_id}'")


def add_requests_to_db(requests: list[Request], db_name: str):
    conn = sql.connect(db_name)
    cursor = conn.cursor()
    added_requests = 0
    # check the new visitors later
    max_visitor_id = sql_tablesize(cursor, t_visitor)
    request_blacklist = settings["request_location_regex_blacklist"]
    for i in range(len(requests)):
        request = requests[i]
        # skip requests to blacklisted locations
        if request_blacklist:
            if fullmatch(request_blacklist, request.request_file):
                # pdebug(f"add_requests_to_db: request on blacklist '{request.request_file}'")
                continue
        # pdebug("add_requests_to_db:", i, "request:", request)
        visitor_id = get_visitor_id(request, cursor)
        conn.commit()
        group_id: int = get_filegroup(request.request_file, cursor)
        # check if request is unique
        if request_exists(cursor, request, visitor_id, group_id):
            # pdebug("request exists:", request)
            pass
        else:
            # pdebug("new request:", request)
            request_id = sql_tablesize(cursor, t_request)
            sql_insert(cursor, t_request, [[request_id, visitor_id, group_id, request.time_local, request.referer, request.status]])
            added_requests += 1
    visitor_count = sql_tablesize(cursor, t_visitor)
    for visitor_id in range(max_visitor_id, visitor_count):
        is_human = is_visitor_human(cursor, visitor_id)
        cursor.execute(f"SELECT * FROM {t_visitor} WHERE visitor_id = {visitor_id}")
        # pdebug(f"add_rq_to_db: {visitor_id} is_human? {is_human}, {cursor.fetchall()}")
        if is_human:
            cursor.execute(f"UPDATE {t_visitor} SET is_human = 1 WHERE visitor_id = {visitor_id}")
    cursor.close()
    conn.commit()
    pmessage(f"Collection Summary: Added {visitor_count - max_visitor_id} new visitors and {added_requests} new requests.")
