from re import fullmatch

from regina.database import Database
from regina.utility.globals import settings
from regina.utility.utility import pdebug, warning, missing_arg

# re_uri_protocol = f"(https?)://"
re_uri_protocol = f"(https?://)?"
re_uri_ipv4 = r"(?:(?:(?:\d{1,3}\.?){4})(?::\d+)?)"
# re_uri_ipv6 = ""
re_uri_domain = r"(?:([^/]+\.)*[^/]+\.[a-zA-Z]{2,})"
re_uri_route = r"(?:/(.*))?"
re_uri_full = f"{re_uri_protocol}({re_uri_domain}|{re_uri_ipv4})({re_uri_route})"
# (https?://)?((?:([^/]+\.)*[^/]+\.[a-zA-Z]{2,})|(?:(?:(?:\d{1,3}\.?){4})(?::\d+)?))((?:/(.*))?)

def cleanup_referer(referer: str) -> str:
    """
    split the referer uri into its parts and reassemeble them depending on settings
    """
    m = fullmatch(re_uri_full, referer)
    if not m:
        warning(f"cleanup_referer: Could not match referer '{referer}'")
        return referer
    # pdebug(f"cleanup_referer: {referer} - {m.groups()}")
    protocol = m.groups()[0]
    subdomains = m.groups()[2]
    if not subdomains: subdomains = ""
    domain = m.groups()[1].replace(subdomains, "")
    route = m.groups()[3]

    referer = domain
    if settings["referer_ranking_ignore_tld"]:
        if len(domain.split(".")) == 2:  # if domain.tld
            referer = domain.split(".")[0]
    if not settings["referer_ranking_ignore_subdomain"]: referer = subdomains + referer
    if not settings["referer_ranking_ignore_protocol"]: referer = protocol + referer
    if not settings["referer_ranking_ignore_route"]: referer += route
    # pdebug(f"cleanup_referer: cleaned up: {referer}")
    return referer



def get_where_date_str(at_date=None, min_date=None, max_date=None):
    """
    get a condition string that sets a condition on the time
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

def is_valid_status(status: int):
    if status >= 400: return False
    if settings["status_300_is_success"] and status >= 300: return True
    return status < 300

#
# GETTERS
#
def get_unique_visitor_ids_for_date(db: Database, date:str) -> list[int]:
    return [ visitor_id[0] for visitor_id in db(f"SELECT DISTINCT visitor_id FROM request WHERE {date}") ]

def append_human_visitors(db: Database, unique_visitor_ids, unique_visitor_ids_human: list):
    """
    for visitor in unique_visitor_ids:
        if human -> append to unique_visitor_ids_human
    """
    for visitor_id in unique_visitor_ids:
        db.execute(f"SELECT is_human FROM visitor WHERE visitor_id = {visitor_id}")
        if db.fetchone()[0] == 1:
            unique_visitor_ids_human.append(visitor_id)

def get_unique_request_ids_for_date(db: Database, date_constraint:str):
    return [ request_id[0] for request_id in db(f"SELECT DISTINCT request_id FROM request WHERE {date_constraint}")]

def append_unique_request_ids_for_date_and_visitor(db: Database, date_constraint:str, visitor_id: int, unique_request_ids_human: list):
    """append all unique requests for visitor_id at date_constraint to unique_request_ids_human"""
    for request_id in db(f"SELECT DISTINCT request_id FROM request WHERE {date_constraint} AND visitor_id = {visitor_id}"):
        unique_request_ids_human.append(request_id[0])

# get number of requests per day
def get_request_count_for_date(db: Database, date_constraint:str) -> int:
    db.execute(f"SELECT COUNT(*) FROM request WHERE {date_constraint}")
    return db.fetchone()[0]

def get_unique_visitor_count(db: Database) -> int:
    return sql_tablesize(db.cur, "visitor")
