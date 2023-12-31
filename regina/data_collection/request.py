from ipaddress import IPv4Address, ip_address
from time import mktime
from re import fullmatch, match
from datetime import datetime as dt

from regina.utility.sql_util import sanitize, sql_select, sql_exists, sql_insert, sql_tablesize, sql_max
from regina.utility.utility import pdebug, warning, pmessage
from regina.utility.globals import user_agent_platforms, user_agent_browsers, settings

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

class Request:
    def __init__(self, ip_address="", time_local="", request_type="", request_route="", request_protocol="", status="", bytes_sent="", referer="", user_agent=""):
        self.ip_address = int(IPv4Address(sanitize(ip_address)))
        self.time_local = 0
        # turn [20/Nov/2022:00:47:36 +0100] to unix time
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
        self.type = sanitize(request_type)        # GET, POST, ...
        self.route = sanitize(request_route)      # eg. /index.html
        self.protocol = sanitize(request_protocol)    # eg. HTTP/1.1
        self.status = sanitize(status)            # http status code
        self.bytes_sent = sanitize(bytes_sent)
        self.referer = sanitize(referer)
        self.user_agent = sanitize(user_agent)

    def __repr__(self):
        return f"{self.ip_address} - {self.time_local} - {self.route} - {self.user_agent} - {self.status}"

    def get_platform(self):
        # for groups in findall(re_visitor_agent, visitor_agent):
        operating_system = ""
        for os in user_agent_platforms:
            if os in self.user_agent:
                operating_system = os
                break
        return operating_system

    def get_browser(self):
        browser = ""
        for br in user_agent_browsers:
            if br in self.user_agent:
                browser = br
                break
        return browser

    def get_mobile(self):
        return "Mobi" in self.user_agent


