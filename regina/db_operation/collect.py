import sqlite3 as sql
from re import match
from time import mktime
from datetime import datetime as dt
from regina.db_operation.database import t_request, t_user, t_file, t_filegroup, database_tables, get_filegroup
from regina.utility.sql_util import sanitize, sql_select, sql_exists, sql_insert, sql_tablesize
from regina.utility.utility import pdebug, warning, pmessage
from regina.utility.globals import user_agent_operating_systems, user_agent_browsers, settings

"""
collect information from the access log and put it into the database
"""
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aut", "Sep", "Oct", "Nov", "Dez"]



class Request:
    def __init__(self, ip_address="", time_local="", request_type="", request_file="", request_protocol="", status="", bytes_sent="", referer="", user_agent=""):
        self.ip_address = sanitize(ip_address)
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
        self.user_agent = sanitize(user_agent)

    def __repr__(self):
        return f"{self.ip_address} - {self.time_local} - {self.request_file} - {self.user_agent} - {self.status}"

re_remote_addr = r"[0-9a-fA-F.:]+"
re_remote_user = ".*"
re_time_local = r"\[.+\]"
re_request = r'"[^"]+"'
re_status = r'\d+'
re_body_bytes_sent = r'\d+'
re_http_referer = r'"([^"]*)"'
re_http_user_agent = r'"([^"]*)"'
re_log_format: str = f'({re_remote_addr}) - ({re_remote_user}) ({re_time_local}) ({re_request}) ({re_status}) ({re_body_bytes_sent}) {re_http_referer} {re_http_user_agent}'
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
                                status=g[4], bytes_sent=g[5], referer=g[6], user_agent=g[7]))
    return requests


def user_exists(cursor, request) -> bool:
    if settings["unique_user_is_ip_address"]:
        return sql_exists(cursor, t_user, [("ip_address", request.ip_address)])
    else:
        return sql_exists(cursor, t_user, [("ip_address", request.ip_address), ("user_agent", request.user_agent)])

def get_user_id(request: Request, cursor: sql.Cursor) -> int:
    """
    get the user_id. Adds the user if not already existing
    """
    # if user exists
    if user_exists(cursor, request):
        if settings["unique_user_is_ip_address"]:
            user_id = sql_select(cursor, t_user, [("ip_address", request.ip_address)])[0][0]
        else:
            user_id = sql_select(cursor, t_user, [("ip_address", request.ip_address), ("user_agent", request.user_agent)])[0][0]
    else:  # new user 
        # new user_id is number of elements
        user_id: int = sql_tablesize(cursor, t_user)
        # pdebug("new user:", user_id, request.ip_address)
        platform, browser, mobile = get_os_browser_pairs_from_agent(request.user_agent)
        is_human = 0 # is_user_human cannot be called until user is in db int(is_user_human(cursor, user_id))
        cursor.execute(f"INSERT INTO {t_user} (user_id, ip_address, user_agent, platform, browser, mobile, is_human) VALUES ({user_id}, '{request.ip_address}', '{request.user_agent}', '{platform}', '{browser}', '{int(mobile)}', '{is_human}');")
    return user_id

def is_user_human(cur: sql.Cursor, user_id: int):
    global settings
    """
    check if they have a known platform AND browser
    check if at least one request did not result in an error (http status >= 400)
    """
    max_success_status = 400
    if settings["status_300_is_success"]: max_success_status = 300
    cur.execute(f"SELECT browser, platform FROM {t_user} WHERE user_id = {user_id}")
    browsers_and_platforms = cur.fetchall()
    if len(browsers_and_platforms) != 1:
        pdebug(f"is_user_human: {user_id} - could not find user or found too many")
        return False
    if not browsers_and_platforms[0][0] in user_agent_browsers:
        return False
    if not browsers_and_platforms[0][1] in user_agent_operating_systems:
        return False
    # check if has browser
    # cur.execute(f"SELECT EXISTS (SELECT 1 FROM {t_user} WHERE user_id = {user_id} AND platform IS NOT NULL AND browser IS NOT NULL)")
    # if no browser and platform
    # exists = cur.fetchone()
    # if exists is None or exists[0] == 0:
    #     return False
    # if human needs successful request
    if settings["human_needs_success"]:
        # check if at least request was successful (status < 400)
        cur.execute(f"SELECT EXISTS (SELECT 1 FROM {t_request} WHERE user_id = {user_id} AND status < {max_success_status})")
        if cur.fetchone()[0] == 1:
            # pdebug(f"is_user_human: User {user_id} is human")
            pass
        else:
            # pdebug(f"is_user_human: User {user_id} only had unsuccessful requests")
            return False
    # user is human
    return True


# re_user_agent = r"(?: ?([\w\- ]+)(?:\/([\w.]+))?(?: \(([^()]*)\))?)"
# 1: platform, 2: version, 3: details
def get_os_browser_pairs_from_agent(user_agent):
    # for groups in findall(re_user_agent, user_agent):
    operating_system = ""
    browser = ""
    mobile = "Mobi" in user_agent
    for os in user_agent_operating_systems:
        if os in user_agent:
            operating_system = os
            break
    for br in user_agent_browsers:
        if br in user_agent:
            browser = br
            break
    # if not operating_system or not browser: print(f"Warning: get_os_browser_pairs_from_agent: Could not find all information for agent '{user_agent}', found os: '{operating_system}' and browser: '{browser}'")
    return operating_system, browser, mobile


# def set_countries(cur: sql.Cursor, user_ids: list[int]):
#     if settings["user_get_country"]:
#         ipconn = sql.connect(ip2nation_db_path)
#         ipcur = ipconn.cursor()
#         for user_id in user_ids:
#             ip_address = sql_select(cur, t_user, [("user_id", user_id)])
#             cur.execute(f"SELECT ip_address FROM {t_user} WHERE user_id = {user_id}")
#             ip_address = cur.fetchall()[0][0]
#             ipcur.execute("SELECT iso_code_3 FROM ip2nationCountries WHERE ip")


def add_requests_to_db(requests: list[Request], db_name: str):
    conn = sql.connect(db_name)
    cursor = conn.cursor()
    added_requests = 0
    # check the new users later
    max_user_id = sql_tablesize(cursor, t_user)
    request_blacklist = settings["request_location_regex_blacklist"]
    for i in range(len(requests)):
        request = requests[i]
        # skip requests to blacklisted locations
        if request_blacklist:
            if match(request_blacklist, request.request_file):
                # pdebug(f"add_requests_to_db: request on blacklist '{request.request_file}'")
                continue
        # pdebug("add_requests_to_db:", i, "request:", request)
        user_id = get_user_id(request, cursor)
        conn.commit()
        group_id: int = get_filegroup(request.request_file, cursor)
        # check if request is unique
        group_id_name = database_tables[t_filegroup].key.name
        user_id_name = database_tables[t_user].key.name
        if sql_exists(cursor, t_request, [(group_id_name, group_id), (user_id_name, user_id), ("date", request.time_local)]):
            # pdebug("request exists:", request)
            pass
        else:
            # pdebug("new request:", request)
            request_id = sql_tablesize(cursor, t_request)
            sql_insert(cursor, t_request, [[request_id, user_id, group_id, request.time_local, request.referer, request.status]])
            added_requests += 1
    user_count = sql_tablesize(cursor, t_user)
    for user_id in range(max_user_id, user_count):
        is_human = is_user_human(cursor, user_id)
        cursor.execute(f"SELECT * FROM {t_user} WHERE user_id = {user_id}")
        # pdebug(f"add_rq_to_db: {user_id} is_human? {is_human}, {cursor.fetchall()}")
        if is_human:
            cursor.execute(f"UPDATE {t_user} SET is_human = 1 WHERE user_id = {user_id}")
    cursor.close()
    conn.commit()
    pmessage(f"Collection Summary: Added {user_count - max_user_id} new users and {added_requests} new requests.")
