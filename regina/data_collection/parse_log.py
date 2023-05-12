from re import fullmatch, match
from regina.data_collection.request import Request
from regina.utility.utility import pdebug, warning, pmessage

"""
collect information from the access log and put it into the database
"""

re_remote_addr = r"[0-9a-fA-F.:]+"
re_remote_visitor = ".*"
re_time_local = r"\[.+\]"
re_request = r'"[^"]+"'
re_status = r'\d+'
re_body_bytes_sent = r'\d+'
re_http_referer = r'"([^"]*)"'
re_http_visitor_agent = r'"([^"]*)"'
re_log_format: str = f'({re_remote_addr}) - ({re_remote_visitor}) ({re_time_local}) ({re_request}) ({re_status}) ({re_body_bytes_sent}) {re_http_referer} {re_http_visitor_agent}'

def parse_log(logfile_path:str) -> list[Request]:
    """
    create Request objects from each line in the logfile
    """
    requests = []
    with open(logfile_path, "r") as file:
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
                                request_type=request_[0], request_route=request_[1], request_protocol=request_[2],
                                status=g[4], bytes_sent=g[5], referer=g[6], user_agent=g[7]))
    return requests

