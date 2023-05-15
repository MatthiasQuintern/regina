from re import fullmatch

from regina.database import Database
from regina.utility.globals import settings
from regina.utility.utility import pdebug, warning
from regina.utility.sql_util import sanitize, sql_tablesize

# re_uri_protocol = f"(https?)://"
re_uri_protocol = f"(https?://)?"
re_uri_ipv4 = r"(?:\d{1,3}\.?){4}"
# re_uri_ipv6 = ""
re_uri_domain = r"(?:[^/:]+)"
re_uri_port = r"(?::\d+)?"
re_uri_route = r"(?:/.*)?"
re_uri_full = f"{re_uri_protocol}({re_uri_domain}|{re_uri_ipv4})({re_uri_port})({re_uri_route})"
# (https?://)?((?:([^/]+\.)*[^/]+\.[a-zA-Z]{2,})|(?:(?:(?:\d{1,3}\.?){4})(?::\d+)?))((?:/(.*))?)

re_domain = r"[^/:]+\.[a-z]{2,}"

def cleanup_referer(referer: str) -> str:
    """
    split the referer uri into its parts and reassemeble them depending on settings
    """
    m = fullmatch(re_uri_full, referer)
    if not m:
        warning(f"cleanup_referer: Could not match referer '{referer}'")
        return referer
    pdebug(f"cleanup_referer: {referer} - {m.groups()}", lvl=4)
    protocol, domain, port, route = m.groups()
    if not protocol: protocol = ""
    if not port: port = ""

    if fullmatch(re_domain, domain):  # no ip address
        parts = domain.split(".")
        if len(parts) < 2:
            warning(f"cleanup_referer: Domain has not enough parts: '{domain}'")
        tld = parts[-1]
        referer = parts[-2]
        subdomains = ""
        for sd in parts[:-2]:
            subdomains += f"{sd}."
        if not settings["rankings"]["referer_ignore_tld"]: referer += "." + tld
        if not settings["rankings"]["referer_ignore_subdomain"]: referer = subdomains + referer
    else:
        referer = domain
    if not settings["rankings"]["referer_ignore_protocol"]: referer = protocol + referer
    if not settings["rankings"]["referer_ignore_port"]: referer += port
    if not settings["rankings"]["referer_ignore_route"]: referer += route
    # pdebug(f"cleanup_referer: cleaned up: {referer}")
    return referer

def is_valid_status(status: int):
    if status >= 400: return False
    if settings["data-collection"]["status_300_is_success"] and status >= 300: return True
    return status < 300


def len_list_list(l: list[list]):
    size = 0
    for i in range(len(l)):
        size += len(l[i])
    return size


