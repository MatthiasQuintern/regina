from re import fullmatch, match
from regina.data_collection.request import Request
from regina.utility.utility import pdebug, warning, pmessage

"""
collect information from the access log and put it into the database
"""

re_remote_addr = r"[0-9a-fA-F.:]+"
re_remote_user = ".*"
re_time_local = r"\[.+\]"
re_request = r'"[^"]*"'
re_status = r'\d+'
re_body_bytes_sent = r'\d+'
re_http_referer = r'"([^"]*)"'
re_http_user_agent = r'"([^"]*)"'
re_log_format: str = f'({re_remote_addr}) - ({re_remote_user}) ({re_time_local}) ({re_request}) ({re_status}) ({re_body_bytes_sent}) {re_http_referer} {re_http_user_agent}'

def parse_log(logfile_path:str) -> list[Request]:
    """
    create Request objects from each line in the logfile
    """
    requests = []
    with open(logfile_path, "r") as file:
        lines = file.readlines()
    for i in range(len(lines)):
        m = match(re_log_format, lines[i])
        if m is None:
            warning(f"parse_log: Could not match line {i:3}: '{lines[i].strip('\n')}'")
            continue
        pdebug(f"parse_log: line {i:3} match groups:", m.groups(), lvl=4)
        # _ is user
        ip_address, _, timestamp, request_, status, bytes_sent, referer, user_agent = m.groups()
        request_parts = request_.split(" ")
        if len(request_parts) != 3:
            warning(f"parse_log: Could not parse request of line {i:3}: '{request_}'")
            continue
        http_function, route, protocol = request_parts
        requests.append(Request(ip_address=ip_address, time_local=timestamp,
                                request_type=http_function, request_route=route, request_protocol=protocol,
                                status=status, bytes_sent=bytes_sent, referer=referer, user_agent=user_agent))
    return requests

