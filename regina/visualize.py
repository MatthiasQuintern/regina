import sqlite3 as sql
from sys import argv, exit
from database import t_request, t_user, t_file, t_filegroup, database_tables
from sql_util import sanitize, sql_select, sql_exists, sql_insert, sql_tablesize, sql_get_count_where
from re import fullmatch, findall
import matplotlib.pyplot as plt
import matplotlib as mpl

settings = {
    # "file_ranking_regex_whitelist": r".*\.((txt)|(html)|(css)|(php)|(png)|(jpeg)|(jpg)|(svg)|(gif))",
    "file_ranking_regex_whitelist": r".*\.(html)",
    "referer_ranking_regex_whitelist": r"",
    "user_agent_ranking_regex_whitelist": r"",
    "file_ranking_plot_max_files": 15,
    # "plot_figsize": (60, 40),
    "plot_dpi": 300,
    "plot_tight_layout": False,
    "plot_constrained_layout": False,
}
color_settings_filetypes = {
    "red": ["html"],
    "green": ["jpg", "png", "jpeg", "gif", "svg", "webp"],
    "yellow": ["css"],
    "grey": ["txt"]
}

img_ft = "svg"
# these oses and browser can be detected:
# lower element takes precedence
user_agent_operating_systems = ["Windows", "Android", "Linux", "iPhone", "iPad", "Mac", "BSD"]
user_agent_browsers = ["Firefox", "DuckDuckGo", "SeaMonkey", "Vivaldi", "Yandex", "Brave", "SamsungBrowser", "Lynx", "Epiphany", "Chromium", "Chrome", "Safari", "Opera", "Edge"]
color_settings_browsers = {
    "red": ["Safari"],
    "orange": ["Firefox"],
    "yellow": ["Chrome"],
    "grey": ["Edge"],
    "green": ["Chromium"],
    "teal": ["Brave"]
}
color_settings_operating_systems = {
    "red": ["Macintosh"],
    "green": ["Android"],
    "grey": ["iPhone", "iPad"],
    "yellow": ["Linux"],
    "teal": ["BSD"],
    "#6464ff": ["Windows"],
}




# get all dates
def get_dates(cur: sql.Cursor) -> list[str]:
    cur.execute(f"SELECT DISTINCT DATE(date, 'unixepoch') FROM {t_request}")
    return [ date[0] for date in cur.fetchall() ]  # fetchall returns tuples (date, )

def get_unique_user_ids_for_date(cur: sql.Cursor, date:str) -> list[int]:
    cur.execute(f"SELECT DISTINCT user_id FROM {t_request} WHERE DATE(date, 'unixepoch') = '{sanitize(date)}'")
    return [ user_id[0] for user_id in cur.fetchall() ]

# get number of requests per day
def get_request_count_for_date(cur: sql.Cursor, date:str) -> int:
    return sql_get_count_where(cur, t_request, [("DATE(date, 'unixepoch')", date)])

def get_unique_user_count(cur: sql.Cursor) -> int:
    return sql_tablesize(cur, t_user)

def get_user_agent(cur: sql.Cursor, user_id: int):
    return sql_select(cur, t_user, [("user_id", user_id)])[0]

#
# FILTERS
#
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
    if not operating_system or not browser: print(f"Warning: get_os_browser_pairs_from_agent: Could not find all information for agent '{user_agent}', found os: '{operating_system}' and browser: '{browser}'")
    return operating_system, browser, mobile

def get_os_browser_mobile_rankings(user_agent_ranking):
    """
    returns [(count, operating_system)], [(count, browser)], mobile_user_percentage
    """
    os_ranking = {}
    os_count = 0.0
    browser_ranking = {}
    browser_count = 0.0
    mobile_ranking = { True: 0.0, False: 0.0 }
    for count, agent in user_agent_ranking:
        os, browser, mobile = get_os_browser_pairs_from_agent(agent)
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
        mobile_user_percentage = mobile_ranking[True] / (mobile_ranking[True] + mobile_ranking[False])
    except ZeroDivisionError:
        mobile_user_percentage = 0.0

    os_ranking =  [(c/os_count, n) for n, c in os_ranking.items()]
    os_ranking.sort()
    browser_ranking = [(c/browser_count, n) for n, c in browser_ranking.items()]
    browser_ranking.sort()
    return os_ranking, browser_ranking, mobile_user_percentage

#
# RANKINGS
#
def get_file_ranking(cur: sql.Cursor, min_date_unix_time = 0) -> list[tuple[int, str]]:
    """
    :returns [(request_count, filename)]
    """
    ranking = []
    cur.execute(f"SELECT DISTINCT group_id FROM {t_filegroup}")
    for group in cur.fetchall():
        group = group[0]
        filename = sql_select(cur, t_file, [("group_id", group)])
        if len(filename) == 0: continue
        filename = filename[0][0]
        if settings["file_ranking_regex_whitelist"]:
            if not fullmatch(settings["file_ranking_regex_whitelist"], filename):
                continue
        # ranking.append((sql_get_count_where(cur, t_request, [("group_id", group)]), filename))
        cur.execute(f"SELECT COUNT(*) FROM {t_request} WHERE group_id = {group} AND date >= {min_date_unix_time}")
        ranking.append((cur.fetchone()[0], filename))
    ranking.sort()
    # print(ranking)
    return ranking

def get_user_agent_ranking(cur: sql.Cursor, min_date_unix_time = 0) -> list[tuple[int, str]]:
    """
    :returns [(request_count, user_agent)]
    """
    ranking = []
    cur.execute(f"SELECT DISTINCT user_id FROM {t_request} WHERE date >= {min_date_unix_time}")
    for user_id in cur.fetchall():
        user_id = user_id[0]
        user_agent = sql_select(cur, t_user, [("user_id", user_id)])
        if len(user_agent) == 0: continue
        user_agent = user_agent[0][2]
        if settings["user_agent_ranking_regex_whitelist"]:
            if not fullmatch(settings["user_agent_ranking_regex_whitelist"], user_agent):
                continue
        # ranking.append((sql_get_count_where(cur, t_request, [("group_id", group)]), filename))
        cur.execute(f"SELECT COUNT(*) FROM {t_request} WHERE user_id = {user_id} AND date >= {min_date_unix_time}")
        ranking.append((cur.fetchone()[0], user_agent))
    ranking.sort()
    # print(ranking)
    return ranking

def get_ranking(field_name: str, table: str, whitelist_regex: str, cur: sql.Cursor, min_date_unix_time = 0) -> list[tuple[int, str]]:
    """
    1) get all the distinct entries for field_name after min_date_unix_time
    2) call get_name_function with the distinct entry
    3) for every entry, get the count in table after min_date_unix_time
    3) sort by count in ascending order
    :returns [(request_count, name)]
    """
    ranking = []
    cur.execute(f"SELECT DISTINCT {field_name} FROM {table} WHERE date >= {min_date_unix_time}")
    for name in cur.fetchall():
        name = name[0]
        if whitelist_regex:
            if not fullmatch(whitelist_regex, name):
                continue
        # ranking.append((sql_get_count_where(cur, t_request, [("group_id", group)]), filename))
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {field_name} = '{name}' AND date >= {min_date_unix_time}")
        ranking.append((cur.fetchone()[0], name))
    ranking.sort()
    # print(ranking)
    return ranking


#
# PLOTTING
#
def add_vertikal_labels_in_bar_plot(labels, max_y_val, ax, bar_plot):
    for idx,rect in enumerate(bar_plot):
        height = rect.get_height()
        if height > 0.8 * max_y_val:
            height = 0.05 * max_y_val
        ax.text(rect.get_x() + rect.get_width()/2., 1.05*height,
                labels[idx],
                ha='center', va='bottom', rotation=90)

def plot_ranking(ranking: list[tuple[int, str]], fig=None, xlabel="", ylabel="", color_settings:dict|list=[]):
    """
    make a bar plot of the most requested files
    """
    if not fig:
        fig = plt.figure(figsize=None, dpi=settings["plot_dpi"], linewidth=1.0, frameon=True, subplotpars=None, tight_layout=settings["plot_tight_layout"], constrained_layout=settings["plot_constrained_layout"])
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
        color = "blue"
        if not color_settings: color = "blue"
        elif type(color_settings) == dict:
            for key, val in color_settings.items():
                if ft in val: color = key
            if not color: color = "blue"
        elif type(color_settings) == list:
            color = color_settings[(i - start_index) % len(color_settings)]
        colors.append(color)
    bar = ax.bar(x_names, y_counts, tick_label="", color=colors)
    add_vertikal_labels_in_bar_plot(x_names, y_counts[-1], ax, bar)
    # ax.ylabel(y_counts)
    return fig


def plot_users_per_day(days, user_counts, fig=None):
    pass


#
# MAIN
#
def missing_arg_val(arg):
    print("Missing argument for", arg)
    exit(1)

def missing_arg(arg):
    print("Missing ", arg)
    exit(1)
if __name__ == '__main__':
    server_name =""
    db_path = ""
    # parse args
    i = 1
    while i in range(1, len(argv)):
        if argv[i] == "--server-name":
            if len(argv) > i + 1: server_name = argv[i+1]
            else: missing_arg_val(argv[i])
            i += 1
        elif argv[i] == "--db":
            if len(argv) > i + 1: db_path = argv[i+1]
            else: missing_arg_val(argv[i])
            i += 1
        else:
            i += 1

    if not server_name: missing_arg("--server-name")
    if not db_path: missing_arg("--db")



    conn = sql.connect(db_path)
    cur = conn.cursor()
    file_ranking = get_file_ranking(cur)
    referer_ranking = get_ranking("referer", t_request, settings["referer_ranking_regex_whitelist"], cur)
    user_agent_ranking = get_user_agent_ranking(cur)
    for count, agent in user_agent_ranking:
        get_os_browser_pairs_from_agent(agent)
    fig_file_ranking = plot_ranking(file_ranking, xlabel="Filename/Filegroup", ylabel="Number of requests", color_settings=color_settings_filetypes)
    fig_file_ranking.savefig(f"ranking_files.{img_ft}")

    dates = get_dates(cur)
    unique_users_for_dates = []
    print(dates, unique_users_for_dates)
    for date in dates:
        unique_users_for_dates.append(get_unique_user_ids_for_date(cur, date))
    print(dates, unique_users_for_dates)
    os_ranking, browser_ranking, mobile_user_percentage = get_os_browser_mobile_rankings(user_agent_ranking)
    fig_os_rating = plot_ranking(os_ranking, xlabel="Operating Systems", ylabel="Percentage", color_settings=color_settings_operating_systems)
    fig_os_rating.savefig(f"ranking_operating_systems.{img_ft}")
    fig_browser_rating = plot_ranking(browser_ranking, xlabel="Browsers", ylabel="Percentage", color_settings=color_settings_browsers)
    fig_browser_rating.savefig(f"ranking_browsers.{img_ft}")
    # print("File Ranking", file_ranking)
    # print("referer Ranking", referer_ranking)
    # print("user agent ranking", user_agent_ranking)
    # print("Unique Users:", get_unique_user_count(cur))
    print("OS ranking", os_ranking)
    print("Browser ranking", browser_ranking)
    print("Mobile percentage", mobile_user_percentage)
