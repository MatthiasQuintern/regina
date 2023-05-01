# from sys import path
# print(f"{__file__}: __name__={__name__}, __package__={__package__}, sys.path[0]={path[0]}")
import sqlite3 as sql
from sys import exit
from re import fullmatch
import matplotlib.pyplot as plt
from os.path import isdir
from datetime import datetime as dt

from numpy import empty
# local
from regina.db_operation.database import t_request, t_visitor, t_file, t_filegroup, t_ip_range, t_city, t_country
from regina.utility.sql_util import sanitize, sql_select, sql_exists, sql_insert, sql_tablesize, sql_get_count_where
from regina.utility.utility import pdebug, warning, missing_arg
from regina.utility.globals import settings

"""
visualize information from the databse
"""

palette = {
    "red": "#ee4035",
    "orange": "#f37736",
    "yellow": "#fdf458",
    "green": "#7bc043",
    "blue": "#0392cf",
    "purple": "#b044a0",
}
color_settings_filetypes = {
    palette["red"]: ["html"],
    palette["green"]: ["jpg", "png", "jpeg", "gif", "svg", "webp"],
    palette["yellow"]: ["css"],
    "grey": ["txt"]
}
color_settings_alternate = list(palette.values())

color_settings_browsers = {
    palette["red"]: ["Safari"],
    palette["orange"]: ["Firefox"],
    palette["yellow"]: ["Chrome"],
    "grey": ["Edge"],
    palette["green"]: ["Chromium"],
    palette["purple"]: ["Brave"]
}
color_settings_operating_systems = {
    palette["red"]: ["Mac"],
    palette["green"]: ["Android"],
    "grey": ["iPhone", "iPad"],
    palette["yellow"]: ["Linux"],
    palette["purple"]: ["BSD"],
    palette["blue"]: ["Windows"],
}


def len_list_list(l: list[list]):
    size = 0
    for i in range(len(l)):
        size += len(l[i])
    return size

def valid_status(status: int):
    if status >= 400: return False
    if settings["status_300_is_success"] and status >= 300: return True
    return status < 300

#
# FILTERS
#
def get_os_browser_mobile_rankings(cur: sql.Cursor, visitor_ids: list[int]):
    """
    returns [(count, operating_system)], [(count, browser)], mobile_visitor_percentage
    """
    os_ranking = {}
    os_count = 0.0
    browser_ranking = {}
    browser_count = 0.0
    mobile_ranking = { True: 0.0, False: 0.0 }
    for visitor_id in visitor_ids:
        cur.execute(f"SELECT platform,browser,mobile FROM {t_visitor} WHERE visitor_id = {visitor_id}")
        os, browser, mobile = cur.fetchone()
        mobile = bool(mobile)
        if os:
            if os in os_ranking: os_ranking[os] += 1
            else: os_ranking[os] = 1
            os_count += 1
        if browser:
            if browser in browser_ranking: browser_ranking[browser] += 1
            else: browser_ranking[browser] = 1
            browser_count += 1
        if (os or browser):
            mobile_ranking[mobile] += 1
    try:
        mobile_visitor_percentage = mobile_ranking[True] / (mobile_ranking[True] + mobile_ranking[False])
    except ZeroDivisionError:
        mobile_visitor_percentage = 0.0

    os_ranking =  [(c * 100/os_count, n) for n, c in os_ranking.items()]
    os_ranking.sort()
    browser_ranking = [(c * 100/browser_count, n) for n, c in browser_ranking.items()]
    browser_ranking.sort()
    return os_ranking, browser_ranking, mobile_visitor_percentage*100

#
# GETTERS
#
def get_where_date_str(at_date=None, min_date=None, max_date=None):
    # dates in unix time
    s = ""
    if at_date is not None:
        if isinstance(at_date, str):
            s += f"DATE(date, 'unixepoch') = '{sanitize(at_date)}' AND "
        elif isinstance(at_date, int|float):
            s += f"date = {int(at_date)} AND "
        else:
            print(f"WARNING: get_where_date_str: Invalid type of argument at_date: {type(at_date)}")
    if min_date is not None:
        if isinstance(min_date, str):
            s += f"DATE(date, 'unixepoch') >= '{sanitize(min_date)}' AND "
        elif isinstance(min_date, int|float):
            s += f"date >= {int(min_date)} AND "
        else:
            print(f"WARNING: get_where_date_str: Invalid type of argument min_date: {type(min_date)}")
    if max_date is not None:
        if isinstance(max_date, str):
            s += f"DATE(date, 'unixepoch') <= '{sanitize(max_date)}' AND "
        elif isinstance(max_date, int|float):
            s += f"date <= {int(max_date)} AND "
        else:
            print(f"WARNING: get_where_date_str: Invalid type of argument max_date: {type(max_date)}")
    if s == "":
        print(f"WARNING: get_where_date_str: no date_str generated. Returning 'date > 0'. at_date={at_date}, min_date={min_date}, max_date={max_date}")
        return "date > 0"
    return s.removesuffix(" AND ")


# get the earliest date
def get_earliest_date(cur: sql.Cursor) -> int:
    """return the earliest time as unixepoch"""
    cur.execute(f"SELECT MIN(date) FROM {t_request}")
    date = cur.fetchone()[0]
    if not isinstance(date, int): return 0
    else: return date

# get the latest date
def get_latest_date(cur: sql.Cursor) -> int:
    """return the latest time as unixepoch"""
    cur.execute(f"SELECT MAX(date) FROM {t_request}")
    date = cur.fetchone()[0]
    if not isinstance(date, int): return 0
    else: return date

# get all dates
# the date:str parameter in all these function must be a sqlite constraint
def get_days(cur: sql.Cursor, date:str) -> list[str]:
    """get a list of all dates in yyyy-mm-dd format"""
    cur.execute(f"SELECT DISTINCT DATE(date, 'unixepoch') FROM {t_request} WHERE {date}")
    days = [ date[0] for date in cur.fetchall() ]  # fetchall returns tuples (date, )
    days.sort()
    return days

def get_months(cur: sql.Cursor, date:str) -> list[str]:
    """get a list of all dates in yyyy-mm format"""
    cur.execute(f"SELECT DISTINCT DATE(date, 'unixepoch') FROM {t_request} WHERE {date}")
    dates = get_days(cur, date)
    date_dict = {}
    for date in dates:
        date_without_day = date[0:date.rfind('-')]
        date_dict[date_without_day] = 0
    return list(date_dict.keys())


def get_visitor_agent(cur: sql.Cursor, visitor_id: int):
    return sql_select(cur, t_visitor, [("visitor_id", visitor_id)])[0][2]

def get_unique_visitor_ids_for_date(cur: sql.Cursor, date:str) -> list[int]:
    cur.execute(f"SELECT DISTINCT visitor_id FROM {t_request} WHERE {date}")
    return [ visitor_id[0] for visitor_id in cur.fetchall() ]

def get_human_visitors(cur: sql.Cursor, unique_visitor_ids, unique_visitor_ids_human: list):
    """
    check if they have a known platform AND browser
    check if at least one request did not result in an error (http status >= 400)
    """
    for visitor_id in unique_visitor_ids:
        cur.execute(f"SELECT is_human FROM {t_visitor} WHERE visitor_id = {visitor_id}")
        # if not visitor
        if cur.fetchone()[0] == 0:
            # pdebug(f"get_human_visitors: {visitor_id}, is_human is 0")
            continue
        else:
            # pdebug(f"get_human_visitors: {visitor_id}, is_human is non-zero")
            pass

        # visitor is human
        unique_visitor_ids_human.append(visitor_id)
    # pdebug("get_human_visitors: (2)", unique_visitor_ids_human)

def get_unique_request_ids_for_date(cur: sql.Cursor, date:str):
    cur.execute(f"SELECT DISTINCT request_id FROM {t_request} WHERE {date}")
    return [ request_id[0] for request_id in cur.fetchall()]

def get_unique_request_ids_for_date_and_visitor(cur: sql.Cursor, date:str, visitor_id: int, unique_request_ids_human: list):
    cur.execute(f"SELECT DISTINCT request_id FROM {t_request} WHERE {date} AND visitor_id = {visitor_id}")
    # all unique requests for visitor_id
    for request_id in cur.fetchall():
        unique_request_ids_human.append(request_id[0])

# get number of requests per day
def get_request_count_for_date(cur: sql.Cursor, date:str) -> int:
    cur.execute(f"SELECT COUNT(*) FROM {t_request} WHERE {date}")
    return cur.fetchone()[0]

def get_unique_visitor_count(cur: sql.Cursor) -> int:
    return sql_tablesize(cur, t_visitor)



#
# RANKINGS
#
def get_file_ranking(cur: sql.Cursor, date:str) -> list[tuple[int, str]]:
    global settings
    """
    :returns [(request_count, groupname)]
    """
    ranking = []
    cur.execute(f"SELECT group_id, groupname FROM {t_filegroup}")
    for group in cur.fetchall():
        group_id = group[0]
        # filename = sql_select(cur, t_file, [("group_id", group)])
        # if len(filename) == 0: continue
        # filename = filename[0][0]
        filename = group[1]
        if settings["file_ranking_regex_whitelist"]:  # if file in whitelist
            if not fullmatch(settings["file_ranking_regex_whitelist"], filename):
                pdebug(f"get_file_ranking: file with group_id {group_id} is not in whitelist")
                continue
        if settings["file_ranking_ignore_error_files"]:  # if request to file was successful
            success = False
            cur.execute(f"SELECT status FROM {t_request} WHERE group_id = {group_id}")
            for status in cur.fetchall():
                if valid_status(status[0]):
                    pdebug(f"get_file_ranking: success code {status[0]} for file with group_id {group_id} and groupname {filename}")
                    success = True
                    break
            if not success:
                pdebug(f"get_file_ranking: file with group_id {group_id} and groupname {filename} has only requests resulting in error")
                continue


        # ranking.append((sql_get_count_where(cur, t_request, [("group_id", group)]), filename))
        cur.execute(f"SELECT COUNT(*) FROM {t_request} WHERE group_id = {group_id} AND {date}")
        ranking.append((cur.fetchone()[0], filename))
    ranking.sort()
    # print(ranking)
    return ranking

def get_visitor_agent_ranking(cur: sql.Cursor, date:str) -> list[tuple[int, str]]:
    """
    :returns [(request_count, visitor_agent)]
    """
    ranking = []
    cur.execute(f"SELECT DISTINCT visitor_id FROM {t_request} WHERE {date}")
    for visitor_id in cur.fetchall():
        visitor_id = visitor_id[0]
        visitor_agent = sql_select(cur, t_visitor, [("visitor_id", visitor_id)])
        if len(visitor_agent) == 0: continue
        visitor_agent = visitor_agent[0][2]
        if settings["visitor_agent_ranking_regex_whitelist"]:
            if not fullmatch(settings["visitor_agent_ranking_regex_whitelist"], visitor_agent):
                continue
        # ranking.append((sql_get_count_where(cur, t_request, [("group_id", group)]), filename))
        cur.execute(f"SELECT COUNT(*) FROM {t_request} WHERE visitor_id = {visitor_id} AND {date}")
        ranking.append((cur.fetchone()[0], visitor_agent))
    ranking.sort()
    # print(ranking)
    return ranking

def get_request_ranking(field_name: str, table: str, whitelist_regex: str, cur: sql.Cursor, date_condition:str) -> list[tuple[int, str]]:
    """
    1) get all the distinct entries for field_name after min_date_unix_time
    2) call get_name_function with the distinct entry
    3) for every entry, get the count in table after min_date_unix_time
    3) sort by count in ascending order
    :returns [(request_count, name)]
    """
    ranking = []
    cur.execute(f"SELECT DISTINCT {field_name} FROM {table} WHERE {date_condition}")
    for name in cur.fetchall():
        name = name[0]
        if whitelist_regex:
            if not fullmatch(whitelist_regex, name):
                continue
        # ranking.append((sql_get_count_where(cur, t_request, [("group_id", group)]), filename))
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {field_name} = '{name}' AND {date_condition}")
        ranking.append((cur.fetchone()[0], name))
    ranking.sort()
    # print(ranking)
    return ranking

# re_uri_protocol = f"(https?)://"
re_uri_protocol = f"(https?://)?"
re_uri_ipv4 = r"(?:(?:(?:\d{1,3}\.?){4})(?::\d+)?)"
# re_uri_ipv6 = ""
re_uri_domain = r"(?:([^/]+\.)*[^/]+\.[a-zA-Z]{2,})"
re_uri_location = r"(?:/(.*))?"
re_uri_full = f"{re_uri_protocol}({re_uri_domain}|{re_uri_ipv4})({re_uri_location})"
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
    location = m.groups()[3]

    referer = domain
    if settings["referer_ranking_ignore_tld"]:
        if len(domain.split(".")) == 2:  # if domain.tld
            referer = domain.split(".")[0]
    if not settings["referer_ranking_ignore_subdomain"]: referer = subdomains + referer
    if not settings["referer_ranking_ignore_protocol"]: referer = protocol + referer
    if not settings["referer_ranking_ignore_location"]: referer += location
    # pdebug(f"cleanup_referer: cleaned up: {referer}")
    return referer

def cleanup_referer_ranking(referer_ranking: list[tuple[int, str]]):
    unique_referers = dict()
    for count, referer in referer_ranking:
        referer = cleanup_referer(referer)
        if referer in unique_referers:
            unique_referers[referer] += count
        else:
            unique_referers[referer] = count
    referer_ranking.clear()
    for referer, count in unique_referers.items():
        referer_ranking.append((count, referer))
    referer_ranking.sort()

def get_city_and_country_ranking(cur:sql.Cursor, require_humans=True, regex_city_blacklist="", regex_country_blacklist=""):
    sql_cmd = f"SELECT ci.name, c.code, c.name FROM {t_country} AS c, {t_city} as ci, {t_visitor} as u, {t_ip_range} as i WHERE u.ip_range_id = i.ip_range_id AND i.city_id = ci.city_id AND ci.country_id = c.country_id"
    if require_humans: sql_cmd += " AND u.is_human = 1"
    cur.execute(sql_cmd)
    pdebug(f"get_city_and_country_ranking: require_humans={require_humans}, regex_city_blacklist='{regex_city_blacklist}', regex_country_blacklist='{regex_country_blacklist}'")
    cities = cur.fetchall()
    cities_dict = {}
    country_dict = {}
    pdebug(f"get_city_and_country_ranking: found {len(cities)} ip_ranges")

    validate_city_cmd = lambda _ : True
    validate_country_cmd = lambda _ : True
    if len(regex_city_blacklist) > 0: validate_city_cmd = lambda city : fullmatch(regex_city_blacklist, city) is None
    if len(regex_country_blacklist) > 0 : validate_country_cmd = lambda country : fullmatch(regex_country_blacklist, country) is None
    for i in range(len(cities)):
        if cities[i][0] in cities_dict:
            cities_dict[cities[i][0]][0] += 1
        else:
            if validate_city_cmd(cities[i][0]):
                cities_dict[cities[i][0]] = [1, cities[i][1], cities[i][2]]  # count, country code
        if cities[i][2] in country_dict:
            country_dict[cities[i][2]] += 1
        else:
            if validate_country_cmd(cities[i][2]):
                country_dict[cities[i][2]] = 1  # count, country code
    city_ranking = [(v[0], f"{k} ({v[1]})") for k,v in cities_dict.items()]
    city_ranking.sort()
    country_ranking = [(v, k) for k,v in country_dict.items()]
    country_ranking.sort()
    return city_ranking, country_ranking

#
# PLOTTING
#
# add value labels
def add_vertikal_labels_in_bar_plot(labels, max_y_val, ax, bar_plot):
    # pdebug("add_vertikal_labels_in_bar_plot:", labels)
    for idx,rect in enumerate(bar_plot):
        height = rect.get_height()
        if height > 0.6 * max_y_val:  # if the bar is large, put label in the bar
            height = 0.05 * max_y_val
        ax.text(rect.get_x() + rect.get_width()/2., height + 0.025 * max_y_val,
                labels[idx],
                ha='center', va='bottom', rotation=90)
# add count labels
def add_labels_at_top_of_bar(xdata, ydata, max_y_val, ax, bar_plot):
    # pdebug("add_labels_at_top_of_bar:", xdata, ydata)
    y_offset = 0.05 * max_y_val
    for idx,rect in enumerate(bar_plot):
        ax.text(rect.get_x() + rect.get_width()/2, ydata[idx] - y_offset, round(ydata[idx], 1), ha='center', bbox=dict(facecolor='white', alpha=0.8))

def plot_ranking(ranking: list[tuple[int, str]], fig=None, xlabel="", ylabel="", color_settings:dict|list=[], figsize=None):
    """
    make a bar plot of the most requested files
    """
    # pdebug(f"plot_ranking: ranking={ranking}")
    if not fig:
        fig = plt.figure(figsize=figsize, dpi=settings["plot_dpi"], linewidth=1.0, frameon=True, subplotpars=None, layout=None)
    # create new axis if none is given
    ax = fig.add_subplot(xlabel=xlabel, ylabel=ylabel)
    # fill x y data
    if len(ranking) > settings["file_ranking_plot_max_files"]:
        start_index = len(ranking) - settings["file_ranking_plot_max_files"]
    else: start_index = 0
    x_names = []
    y_counts = []
    colors = []
    for i in range(start_index, len(ranking)):
        x_names.append(ranking[i][1])
        y_counts.append(ranking[i][0])
        ft = ranking[i][1].split(".")[-1]
        color = palette["blue"]
        # if not color_settings: color = palette["blue"]
        if isinstance(color_settings, dict):
            for key, val in color_settings.items():
                if ft in val: color = key
            if not color: color = palette["blue"]
        elif isinstance(color_settings, list):
            # print(color_settings, (i - start_index) % len(color_settings))
            color = color_settings[(i - start_index) % len(color_settings)]
        colors.append(color)
    bar = ax.bar(x_names, y_counts, tick_label="", color=colors)

    if len(y_counts) > 0:
        add_vertikal_labels_in_bar_plot(x_names, y_counts[-1], ax, bar)
        if settings["plot_add_count_label"]: add_labels_at_top_of_bar(x_names, y_counts, y_counts[-1], ax, bar)
    # ax.ylabel(y_counts)
    return fig


# def plot(xdata, ydata, fig=None, ax=None, xlabel="", ylabel="", label="", linestyle='-', marker="", color="blue", rotate_xlabel=0):
#     if not fig:
#         fig = plt.figure(figsize=None, dpi=settings["plot_dpi"], linewidth=1.0, frameon=True, subplotpars=None, layout=None)
#     if not ax:
#         ax = fig.add_subplot(xlabel=xlabel, ylabel=ylabel)
#     else:
#         ax = ax.twinx()
#         ax.set_ylabel(ylabel)
#         # ax.tick_params(axis="y", labelcolor="r")
#     ax.plot(xdata, ydata, marker=marker, label=label, linestyle=linestyle, color=color)
#     plt.xticks(rotation=rotate_xlabel)
#     if label: ax.legend()
#     return fig, ax

def plot2y(xdata, ydata1, ydata2, fig=None, ax1=None, ax2=None, plots=None, xlabel="", ylabel1="", ylabel2="", label1="", label2="", linestyle='-', marker="", color1="blue", color2="orange", grid="major", rotate_xlabel=0, figsize=None):
    if not fig:
        fig = plt.figure(figsize=figsize, dpi=settings["plot_dpi"], linewidth=1.0, frameon=True, subplotpars=None, layout=None)
    if not (ax1 and ax2):
        ax1 = fig.add_subplot(xlabel=xlabel, ylabel=ylabel1)
        ax2 = ax1.twinx()
        ax2.set_ylabel(ylabel2)
    ax1.tick_params(axis="x", rotation=90)
    plot1 = ax1.plot(xdata, ydata1, marker=marker, label=label1, linestyle=linestyle, color=color1)
    plot2 = ax2.plot(xdata, ydata2, marker=marker, label=label2, linestyle=linestyle, color=color2)
    # ax1.set_xticks(ax1.get_xticks())
    # ax1.set_xticklabels(xdata, rotation=rotate_xlabel, rotation_mode="anchor")
    # if label1 or label2: ax1.legend()
    if plots: plots += plot1 + plot2
    else: plots = plot1 + plot2
    plt.legend(plots, [ l.get_label() for l in plots])

    if grid == "major" or grid == "minor" or grid == "both":
        if grid == "minor" or "both":
            ax1.minorticks_on()
        ax1.grid(visible=True, which=grid, linestyle="-", color="#888")

    return fig, ax1, ax2, plots


#
# MAIN
#

def visualize(loaded_settings: dict):
    pdebug("visualizing...")
    global settings
    settings = loaded_settings
    if not settings["db"]: missing_arg("db")
    if not settings["server_name"]: missing_arg("server_name")

    img_dir = settings["img_dir"]
    pdebug("img_dir:", img_dir)
    img_filetype = settings["img_filetype"]
    img_location = settings["img_location"]
    names = {
        # paths
        "img_file_ranking_last_x_days": f"ranking_files_last_x_days.{img_filetype}",
        "img_referer_ranking_last_x_days": f"ranking_referers_last_x_days.{img_filetype}",
        "img_countries_last_x_days": f"ranking_countries_last_x_days.{img_filetype}",
        "img_cities_last_x_days": f"ranking_cities_last_x_days.{img_filetype}",
        "img_browser_ranking_last_x_days": f"ranking_browsers_last_x_days.{img_filetype}",
        "img_operating_system_ranking_last_x_days": f"ranking_operating_systems_last_x_days.{img_filetype}",
        "img_visitors_and_requests_last_x_days": f"visitor_request_count_daily_last_x_days.{img_filetype}",

        "img_file_ranking_total": f"ranking_files_total.{img_filetype}",
        "img_referer_ranking_total": f"ranking_referers_total.{img_filetype}",
        "img_countries_total": f"ranking_countries_total.{img_filetype}",
        "img_cities_total": f"ranking_cities_total.{img_filetype}",
        "img_browser_ranking_total": f"ranking_browsers_total.{img_filetype}",
        "img_operating_system_ranking_total": f"ranking_operating_systems_total.{img_filetype}",
        "img_visitors_and_requests_total": f"visitor_request_count_daily_total.{img_filetype}",
        # values
        "mobile_visitor_percentage_total": 0.0,
        "mobile_visitor_percentage_last_x_days": 0.0,
        "visitor_count_last_x_days": 0,
        "visitor_count_total": 0,
        "request_count_last_x_days": 0,
        "request_count_total": 0,
        "human_visitor_percentage_last_x_days": 0.0,
        "human_visitor_percentage_total": 0.0,
        "human_request_percentage_last_x_days": 0.0,
        "human_request_percentage_total": 0.0,
        # general
        "regina_version": settings["version"],
        "server_name": settings["server_name"],
        "last_x_days": settings["last_x_days"],  # must be after all the things with last_x_days!
        "earliest_date": "1990-1-1",
        "generation_date": "1990-1-1 0:0:0",
    }

    conn = sql.connect(settings["db"])
    if isdir(img_dir) and img_filetype:
        gen_img = True
    else:
        print(f"Warning: Not generating images since at least one required variable is invalid: img_dir='{img_dir}', img_filetype='{img_filetype}'")
        gen_img = False
    cur = conn.cursor()

    get_humans = settings["get_human_percentage"]
    # pdebug(f"visualize: settings {settings}")
    # DATE STRINGS
    earliest_date = get_earliest_date(cur)
    names["earliest_date"] = dt.fromtimestamp(earliest_date).strftime("%Y-%m-%d")
    names["generation_date"] = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    # LAST_X_DAYS
    # last_x_days_min_date: latest_date - last_x_days
    secs_per_day = 86400
    last_x_days_min_date = get_latest_date(cur) - settings["last_x_days"] * secs_per_day
    last_x_days_str = get_where_date_str(min_date=last_x_days_min_date)
    days = get_days(cur, last_x_days_str)
    days_strs = [get_where_date_str(at_date=day) for day in days]

    # ALL DATES
    all_time_str = get_where_date_str(min_date=0)
    # all months in yyyy-mm format
    months_all_time = get_months(cur, all_time_str)
    # sqlite constrict to month string
    months_strs = []
    for year_month in months_all_time:
        year, month = year_month.split("-")
        # first day of the month
        min_date  = dt(int(year), int(month), 1).timestamp()
        month = (int(month) % 12) + 1  # + 1 month
        year = int(year)
        if month == 1: year += 1
        # first day of the next month - 1 sec
        max_date = dt(year, month, 1).timestamp() - 1
        months_strs.append(get_where_date_str(min_date=min_date, max_date=max_date))

    for i in range(2):
        suffix = ["_total", "_last_x_days"][i]
        date_str = [all_time_str, last_x_days_str][i]
        date_names = [months_all_time, days][i]
        date_strs = [months_strs, days_strs][i]
        assert(len(date_names) == len(date_strs))

        # FILES
        file_ranking = get_file_ranking(cur, date_str)
        if gen_img:
            fig_file_ranking = plot_ranking(file_ranking, xlabel="Filename/Filegroup", ylabel="Number of requests", color_settings=color_settings_filetypes, figsize=settings["plot_size_broad"])
            fig_file_ranking.savefig(f"{img_dir}/{names[f'img_file_ranking{suffix}']}", bbox_inches="tight")

        # REFERER
        referer_ranking = get_request_ranking("referer", t_request, settings["referer_ranking_regex_whitelist"], cur, date_str)
        pdebug("Referer ranking", referer_ranking)
        cleanup_referer_ranking(referer_ranking)
        if gen_img:
            fig_referer_ranking = plot_ranking(referer_ranking, xlabel="HTTP Referer", ylabel="Number of requests", color_settings=color_settings_alternate, figsize=settings["plot_size_broad"])
            fig_referer_ranking.savefig(f"{img_dir}/{names[f'img_referer_ranking{suffix}']}", bbox_inches="tight")

        # GEOIP
        if settings["do_geoip_rankings"]:
            city_ranking, country_ranking = get_city_and_country_ranking(cur, require_humans=settings["geoip_only_humans"], regex_city_blacklist=settings["city_ranking_regex_blacklist"], regex_country_blacklist=settings["country_ranking_regex_blacklist"])
            pdebug("Country ranking:", country_ranking)
            pdebug("City ranking:", city_ranking)
            if gen_img:
                fig_referer_ranking = plot_ranking(country_ranking, xlabel="Country", ylabel="Number of visitors", color_settings=color_settings_alternate, figsize=settings["plot_size_broad"])
                fig_referer_ranking.savefig(f"{img_dir}/{names[f'img_countries{suffix}']}", bbox_inches="tight")

                fig_referer_ranking = plot_ranking(city_ranking, xlabel="City", ylabel="Number of visitors", color_settings=color_settings_alternate, figsize=settings["plot_size_broad"])
                fig_referer_ranking.savefig(f"{img_dir}/{names[f'img_cities{suffix}']}", bbox_inches="tight")


        # USER
        # visitor_agent_ranking = get_visitor_agent_ranking(cur, date_str)
        # for the time span
        unique_visitor_ids = get_unique_visitor_ids_for_date(cur, date_str)
        unique_visitor_ids_human = []
        get_human_visitors(cur, unique_visitor_ids, unique_visitor_ids_human)
        # for each date
        date_count = len(date_strs)
        unique_visitor_ids_dates: list[list[int]] = []
        unique_request_ids_dates: list[list[int]] = []
        unique_visitor_ids_human_dates: list[list[int]] = [[] for _ in range(date_count)]
        unique_request_ids_human_dates: list[list[int]] = [[] for _ in range(date_count)]
        for i in range(date_count):
            date_str_ = date_strs[i]
            unique_visitor_ids_dates.append(get_unique_visitor_ids_for_date(cur, date_str_))
            unique_request_ids_dates.append(get_unique_request_ids_for_date(cur, date_str_))
            if get_humans:
                # empty_list = []
                # unique_visitor_ids_human_dates.append(empty_list)
                get_human_visitors(cur, unique_visitor_ids_dates[i], unique_visitor_ids_human_dates[i])
                # unique_request_ids_human_dates.append(list())
                for human in unique_visitor_ids_human_dates[i]:
                    get_unique_request_ids_for_date_and_visitor(cur, date_str_, human, unique_request_ids_human_dates[i])
        # print("\n\tuu", unique_visitor_ids_dates, "\n\tur",unique_request_ids_dates, "\n\tuuh", unique_visitor_ids_human_dates, "\n\turh", unique_request_ids_human_dates)
        # pdebug("uui",   unique_visitor_ids)
        # pdebug("uuih",  unique_visitor_ids_human)
        # pdebug("uuid",  unique_visitor_ids_dates)
        # pdebug("uuidh", unique_visitor_ids_human_dates)
        # pdebug("urid",  unique_request_ids_dates)
        # pdebug("uridh", unique_visitor_ids_human_dates)
        # pdebug(f"human_visitor_precentage: len_list_list(visitor_ids)={len_list_list(unique_visitor_ids_dates)}, len_list_list(visitor_ids_human)={len_list_list(unique_visitor_ids_human_dates)}")
        if get_humans:
            try:
                names[f"human_visitor_percentage{suffix}"] = round(100 * len_list_list(unique_visitor_ids_human_dates) / len_list_list(unique_visitor_ids_dates), 2)
            except:
                names[f"human_visitor_percentage{suffix}"] = -1.0
            try:
                names[f"human_request_percentage{suffix}"] = round(100 * len_list_list(unique_request_ids_human_dates) / len_list_list(unique_request_ids_dates), 2)
            except:
                names[f"human_request_percentage{suffix}"] = -1.0
        names[f"visitor_count{suffix}"] = len_list_list(unique_visitor_ids_dates)
        names[f"request_count{suffix}"] = len_list_list(unique_request_ids_dates)
        if gen_img:
            fig_daily, ax1, ax2, plots = plot2y(date_names, [len(visitor_ids) for visitor_ids in unique_visitor_ids_dates], [len(request_ids) for request_ids in unique_request_ids_dates], xlabel="Date", ylabel1="Visitor count", label1="Unique visitors", ylabel2="Request count", label2="Unique requests", color1=palette["red"], color2=palette["blue"], rotate_xlabel=-45, figsize=settings["plot_size_broad"])
            if get_humans:
                fig_daily, ax1, ax2, plots = plot2y(date_names, [len(visitor_ids) for visitor_ids in unique_visitor_ids_human_dates], [len(request_ids) for request_ids in unique_request_ids_human_dates], label1="Unique visitors (human)", label2="Unique requests (human)", color1=palette["orange"], color2=palette["green"], fig=fig_daily, ax1=ax1, ax2=ax2, plots=plots, rotate_xlabel=-45, figsize=settings["plot_size_broad"])
            fig_daily.savefig(f"{img_dir}/{names[f'img_visitors_and_requests{suffix}']}", bbox_inches="tight")

        # os & browser
        os_ranking, browser_ranking, names[f"mobile_visitor_percentage{suffix}"] = get_os_browser_mobile_rankings(cur, unique_visitor_ids_human)
        if gen_img:
            fig_os_rating = plot_ranking(os_ranking, xlabel="Platform", ylabel="Share [%]", color_settings=color_settings_operating_systems, figsize=settings["plot_size_narrow"])
            fig_os_rating.savefig(f"{img_dir}/{names[f'img_operating_system_ranking{suffix}']}", bbox_inches="tight")
            fig_browser_rating = plot_ranking(browser_ranking, xlabel="Browsers", ylabel="Share [%]", color_settings=color_settings_browsers, figsize=settings["plot_size_narrow"])
            fig_browser_rating.savefig(f"{img_dir}/{names[f'img_browser_ranking{suffix}']}", bbox_inches="tight")

    # print("OS ranking", os_ranking)
    # print("Browser ranking", browser_ranking)
    # print("Mobile percentage", names["mobile_visitor_percentage"])
    if settings["template_html"] and settings["html_out_path"]:
        pdebug(f"visualize: writing to html: {settings['html_out_path']}")

        with open(settings["template_html"], "r") as file:
            html = file.read()
        for name, value in names.items():
            if "img" in name:
                value = f"{img_location}/{value}"
            html = html.replace(f"%{name}", str(value))
        with open(settings["html_out_path"], "w") as file:
            file.write(html)
    else:
        warning(f"Skipping html generation because either template_html or html_out_path is invalid: template_html='{settings['template_html']}', html_out_path='{settings['html_out_path']}'")
