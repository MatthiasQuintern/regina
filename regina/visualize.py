import sqlite3 as sql
from sys import argv, exit
from database import t_request, t_user, t_file, t_filegroup, database_tables
from sql_util import sanitize, sql_select, sql_exists, sql_insert, sql_tablesize, sql_get_count_where
from re import fullmatch, findall
import matplotlib.pyplot as plt
import matplotlib as mpl
from os.path import isdir
"""
TODO:
- bei referrers &auml;hnliche zusammenlegen, z.b. www.google.de und https://google.com
"""

settings = {}

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

# these oses and browser can be detected:
# lower element takes precedence
user_agent_operating_systems = ["Windows", "Android", "Linux", "iPhone", "iPad", "Mac", "BSD"]
user_agent_browsers = ["Firefox", "DuckDuckGo", "SeaMonkey", "Vivaldi", "Yandex", "Brave", "SamsungBrowser", "Lynx", "Epiphany", "Chromium", "Chrome", "Safari", "Opera", "Edge"]
color_settings_browsers = {
    palette["red"]: ["Safari"],
    palette["orange"]: ["Firefox"],
    palette["yellow"]: ["Chrome"],
    "grey": ["Edge"],
    palette["green"]: ["Chromium"],
    palette["purple"]: ["Brave"]
}
color_settings_operating_systems = {
    palette["red"]: ["Macintosh"],
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
    # if not operating_system or not browser: print(f"Warning: get_os_browser_pairs_from_agent: Could not find all information for agent '{user_agent}', found os: '{operating_system}' and browser: '{browser}'")
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

    os_ranking =  [(c * 100/os_count, n) for n, c in os_ranking.items()]
    os_ranking.sort()
    browser_ranking = [(c * 100/browser_count, n) for n, c in browser_ranking.items()]
    browser_ranking.sort()
    return os_ranking, browser_ranking, mobile_user_percentage*100

#
# GETTERS
#
# get all dates
def get_dates(cur: sql.Cursor) -> list[str]:
    cur.execute(f"SELECT DISTINCT DATE(date, 'unixepoch') FROM {t_request}")
    return [ date[0] for date in cur.fetchall() ]  # fetchall returns tuples (date, )

def get_unique_user_ids_for_date(cur: sql.Cursor, date:str) -> list[int]:
    cur.execute(f"SELECT DISTINCT user_id FROM {t_request} WHERE DATE(date, 'unixepoch') = '{sanitize(date)}'")
    return [ user_id[0] for user_id in cur.fetchall() ]

def get_user_agent(cur: sql.Cursor, user_id: int):
    return sql_select(cur, t_user, [("user_id", user_id)])[0][2]

def get_unique_user_ids_for_date_human(cur: sql.Cursor, date: str):
    cur.execute(f"SELECT DISTINCT user_id FROM {t_request} WHERE DATE(date, 'unixepoch') = '{sanitize(date)}'")
    human_user_ids = []
    for user_id in cur.fetchall():
        user_agent = get_user_agent(cur, user_id[0])
        os, browser, mobile = get_os_browser_pairs_from_agent(user_agent)
        # print("get_unique_user_ids_for_date", user_id[0], os, browser, user_agent)
        if os and browser:
            human_user_ids.append(user_id[0])
    return human_user_ids

def get_unique_request_ids_for_date(cur: sql.Cursor, date:str) -> list[int]:
    cur.execute(f"SELECT DISTINCT request_id FROM {t_request} WHERE DATE(date, 'unixepoch') = '{sanitize(date)}'")
    return [ request_id[0] for request_id in cur.fetchall() ]

def get_unique_request_ids_for_date_and_user(cur: sql.Cursor, date:str, user_id: int) -> list[int]:
    cur.execute(f"SELECT DISTINCT request_id FROM {t_request} WHERE DATE(date, 'unixepoch') = '{sanitize(date)}' AND user_id = {user_id}")
    return [ request_id[0] for request_id in cur.fetchall() ]

# get number of requests per day
def get_request_count_for_date(cur: sql.Cursor, date:str) -> int:
    return sql_get_count_where(cur, t_request, [("DATE(date, 'unixepoch')", date)])

def get_unique_user_count(cur: sql.Cursor) -> int:
    return sql_tablesize(cur, t_user)



#
# RANKINGS
#
def get_file_ranking(cur: sql.Cursor, min_date_unix_time = 0) -> list[tuple[int, str]]:
    global settings
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
        ax.text(rect.get_x() + rect.get_width()/2., height + 0.025 * max_y_val,
                labels[idx],
                ha='center', va='bottom', rotation=90)

def plot_ranking(ranking: list[tuple[int, str]], fig=None, xlabel="", ylabel="", color_settings:dict|list=[]):
    """
    make a bar plot of the most requested files
    """
    if not fig:
        fig = plt.figure(figsize=None, dpi=settings["plot_dpi"], linewidth=1.0, frameon=True, subplotpars=None, layout=None)
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
            # print(color_settings, (i - start_index) % len(color_settings))
            color = color_settings[(i - start_index) % len(color_settings)]
        colors.append(color)
    bar = ax.bar(x_names, y_counts, tick_label="", color=colors)
    add_vertikal_labels_in_bar_plot(x_names, y_counts[-1], ax, bar)
    # ax.ylabel(y_counts)
    return fig


def plot(xdata, ydata, fig=None, ax=None, xlabel="", ylabel="", label="", linestyle='-', marker="", color="blue"):
    if not fig:
        fig = plt.figure(figsize=None, dpi=settings["plot_dpi"], linewidth=1.0, frameon=True, subplotpars=None, layout=None)
    if not ax:
        ax = fig.add_subplot(xlabel=xlabel, ylabel=ylabel)
    else:
        ax = ax.twinx()
        ax.set_ylabel(ylabel)
        # ax.tick_params(axis="y", labelcolor="r")
    ax.plot(xdata, ydata, marker=marker, label=label, linestyle=linestyle, color=color)
    if label: ax.legend()
    # if xlim:
    #     if xlim[0] != xlim[1]:
    #         ax.set_xlim(*xlim)

    # if ylim:
    #     if ylim[0] != ylim[1]:
    #         ax.set_ylim(*ylim)
    return fig, ax

def plot2y(xdata, ydata1, ydata2, fig=None, ax1=None, ax2=None, plots=None, xlabel="", ylabel1="", ylabel2="", label1="", label2="", linestyle='-', marker="", color1="blue", color2="orange", grid="major"):
    if not fig:
        fig = plt.figure(figsize=None, dpi=settings["plot_dpi"], linewidth=1.0, frameon=True, subplotpars=None, layout=None)
    if not (ax1 and ax2):
        ax1 = fig.add_subplot(xlabel=xlabel, ylabel=ylabel1)
        ax2 = ax1.twinx()
        ax2.set_ylabel(ylabel2)
            # ax.tick_params(axis="y", labelcolor="r")
    plot1 = ax1.plot(xdata, ydata1, marker=marker, label=label1, linestyle=linestyle, color=color1)
    plot2 = ax2.plot(xdata, ydata2, marker=marker, label=label2, linestyle=linestyle, color=color2)
    # if label1 or label2: ax1.legend()
    if plots: plots += plot1 + plot2
    else: plots = plot1 + plot2
    plt.legend(plots, [ l.get_label() for l in plots])

    if grid == "major" or grid == "minor" or grid == "both":
        if grid == "minor" or "both":
            ax1.minorticks_on()
        ax1.grid(visible=True, which=grid, linestyle="-", color="#888")

    # if xlim:
    #     if xlim[0] != xlim[1]:
    #         ax.set_xlim(*xlim)

    # if ylim:
    #     if ylim[0] != ylim[1]:
    #         ax.set_ylim(*ylim)
    return fig, ax1, ax2, plots


#
# MAIN
#
def missing_arg_val(arg):
    print("Missing argument for", arg)
    exit(1)

def missing_arg(arg):
    print("Missing ", arg)
    exit(1)

def visualize(loaded_settings: dict):
    global settings
    settings = loaded_settings
    if not settings["db"]: missing_arg("db")
    if not settings["server-name"]: missing_arg("server-name")

    img_dir = settings["img_dir"]
    img_filetype = settings["img_filetype"]
    names = {
        # general
        "regina_version": settings["version"]
        # paths
        "img_file_ranking": f"{img_dir}/ranking_all_time_files.{img_filetype}",
        "img_referer_ranking": f"{img_dir}/ranking_all_time_referers.{img_filetype}",
        "img_browser_ranking": f"{img_dir}/ranking_all_time_browsers.{img_filetype}",
        "img_operating_system_ranking": f"{img_dir}/ranking_all_time_operating_systems.{img_filetype}",
        "img_daily": f"{img_dir}/user_request_count_daily.{img_filetype}",
        # values
        "mobile_user_percentage": 0.0,
        "server-name": settings["server-name"],
        "last_x_days": settings["last_x_days"],
        # order matters!
        "total_user_count_x_days": 0,
        "total_request_count_x_days": 0,
        "total_user_count": 0,
        "total_request_count": 0,
        "human_user_percentage_x_days": 0,
        "human_request_percentage_x_days": 0,
        "human_user_percentage": 0,
        "human_request_percentage": 0,
    }

    conn = sql.connect(settings["db"])
    if isdir(img_dir) and img_filetype:
        gen_img = True
    else:
        print(f"Warning: Not generating images since at least one required variable is invalid: img_dir='{img_dir}', img_filetype='{img_filetype}'")
        gen_img = False
    cur = conn.cursor()

    get_humans = settings["get-human-percentage"]
    print("\t>>>>>>", get_humans)

    # files
    file_ranking = get_file_ranking(cur)
    if gen_img:
        fig_file_ranking = plot_ranking(file_ranking, xlabel="Filename/Filegroup", ylabel="Number of requests", color_settings=color_settings_filetypes)
        fig_file_ranking.savefig(names["img_file_ranking"])

    # referer
    referer_ranking = get_ranking("referer", t_request, settings["referer_ranking_regex_whitelist"], cur)
    print("Referer ranking", referer_ranking)
    if gen_img:
        fig_referer_ranking = plot_ranking(referer_ranking, xlabel="HTTP Referer", ylabel="Number of requests", color_settings=color_settings_alternate)
        fig_referer_ranking.savefig(names["img_referer_ranking"])

    # dates
    dates = get_dates(cur)
    # user
    user_agent_ranking = get_user_agent_ranking(cur)
    unique_user_ids_for_dates = []
    unique_request_ids_for_dates = []
    unique_user_ids_for_dates_human = []
    unique_request_ids_for_dates_human = []
    for date in dates:
        unique_user_ids_for_dates.append(get_unique_user_ids_for_date(cur, date))
        unique_request_ids_for_dates.append(get_unique_request_ids_for_date(cur, date))
        if get_humans:
            unique_user_ids_for_dates_human.append(get_unique_user_ids_for_date_human(cur, date))
            unique_request_ids_for_dates_human.append([])
            for human in unique_user_ids_for_dates_human[-1]:
                unique_request_ids_for_dates_human[-1] += get_unique_request_ids_for_date_and_user(cur, date, human)
    if get_humans:
        try:
            names["human_user_percentage_x_days"] = round(100 * len_list_list(unique_user_ids_for_dates_human) / len_list_list(unique_user_ids_for_dates), 2)
            names["human_request_percentage_x_days"] = round(100 * len_list_list(unique_request_ids_for_dates_human) / len_list_list(unique_request_ids_for_dates), 2)
        except: pass
    print(">>>", len_list_list(unique_request_ids_for_dates), len_list_list(unique_request_ids_for_dates_human))
    names["total_user_count"] = sql_tablesize(cur, t_user)
    names["total_request_count"] = sql_tablesize(cur, t_request)
    names["total_user_count_x_days"] = len_list_list(unique_user_ids_for_dates)
    names["total_request_count_x_days"] = len_list_list(unique_request_ids_for_dates)

    # os & browser
    os_ranking, browser_ranking, names["mobile_user_percentage"] = get_os_browser_mobile_rankings(user_agent_ranking)
    if gen_img:
        fig_os_rating = plot_ranking(os_ranking, xlabel="Platform", ylabel="Share [%]", color_settings=color_settings_operating_systems)
        fig_os_rating.savefig(names["img_operating_system_ranking"])
        fig_browser_rating = plot_ranking(browser_ranking, xlabel="Browsers", ylabel="Share [%]", color_settings=color_settings_browsers)
        fig_browser_rating.savefig(names["img_browser_ranking"])

    # print("File Ranking", file_ranking)
    # print("referer Ranking", referer_ranking)
    # print("user agent ranking", user_agent_ranking)
    # print("Unique Users:", get_unique_user_count(cur))
    # fig_daily, ax_daily_users = plot(dates, [len(user_ids) for user_ids in unique_user_ids_for_dates], xlabel="Datum", ylabel="Einzigartige Nutzer", label="Einzigartige Nutzer", color="blue")
    # fig_daily, ax_daily_requests = plot(dates, [len(request_ids) for request_ids in unique_request_ids_for_dates], fig=fig_daily, ax=ax_daily_users, xlabel="Datum", ylabel="Einzigartige Anfragen", label="Einzigartige Anfragen", color="orange")
    # fig_daily.savefig(f"{img_dir}/daily.{img_filetype}")
    if gen_img:
        fig_daily, ax1, ax2, plots = plot2y(dates, [len(user_ids) for user_ids in unique_user_ids_for_dates], [len(request_ids) for request_ids in unique_request_ids_for_dates], xlabel="Date", ylabel1="User count", label1="Unique users", ylabel2="Request count", label2="Unique requests", color1=palette["red"], color2=palette["blue"])
        if get_humans:
            fig_daily, ax1, ax2, plots = plot2y(dates, [len(user_ids) for user_ids in unique_user_ids_for_dates_human], [len(request_ids) for request_ids in unique_request_ids_for_dates_human], label1="Unique users (human)", ylabel2="Einzigartige Anfragen", label2="Unique requests (human)", color1=palette["orange"], color2=palette["green"], fig=fig_daily, ax1=ax1, ax2=ax2, plots=plots)
        fig_daily.savefig(names["img_daily"])
    print("OS ranking", os_ranking)
    print("Browser ranking", browser_ranking)
    print("Mobile percentage", names["mobile_user_percentage"])
    print(dates, "\n\tuu", unique_user_ids_for_dates, "\n\tur",unique_request_ids_for_dates, "\n\tuuh", unique_user_ids_for_dates_human, "\n\turh", unique_request_ids_for_dates_human)
    if settings["template_html"] and settings["html_out_path"]:
        with open(settings["template_html"], "r") as file:
            html = file.read()
        for name, value in names.items():
            html = html.replace(f"%{name}", str(value))
        with open(settings["html_out_path"], "w") as file:
            file.write(html)


