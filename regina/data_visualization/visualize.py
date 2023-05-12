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
from regina.database import Database
from regina.utility.sql_util import sanitize, sql_select, sql_exists, sql_insert, sql_tablesize, sql_get_count_where
from regina.utility.utility import pdebug, warning, missing_arg
from regina.utility.globals import settings
from regina.data_visualization.utility import cleanup_referer, get_where_date_str, get_unique_visitor_ids_for_date, get_unique_request_ids_for_date, append_human_visitors, append_unique_request_ids_for_date_and_visitor
from regina.data_visualization.ranking import get_city_and_country_ranking, get_platform_browser_mobile_rankings, get_ranking, cleanup_referer_ranking, get_route_ranking

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
    palette["red"]: ["html", "php"],
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
color_settings_platforms = {
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


#
# PLOTTING
#
def add_vertikal_labels_in_bar_plot(labels, max_y_val, ax, bar_plot):
    """
    Add the label of the bar in or on top of the bar, depending on the bar size
    """
    # pdebug("add_vertikal_labels_in_bar_plot:", labels)
    for idx,rect in enumerate(bar_plot):
        height = rect.get_height()
        if height > 0.6 * max_y_val:  # if the bar is large, put label in the bar
            height = 0.05 * max_y_val
        ax.text(rect.get_x() + rect.get_width()/2., height + 0.025 * max_y_val,
                labels[idx],
                ha='center', va='bottom', rotation=90)

def add_labels_at_top_of_bar(xdata, ydata, max_y_val, ax, bar_plot):
    """
    add the height of the bar on the top of each bar
    """
    # pdebug("add_labels_at_top_of_bar:", xdata, ydata)
    y_offset = 0.05 * max_y_val
    for idx,rect in enumerate(bar_plot):
        ax.text(rect.get_x() + rect.get_width()/2, ydata[idx] - y_offset, round(ydata[idx], 1), ha='center', bbox=dict(facecolor='white', alpha=0.8))

def plot_ranking(ranking: list[tuple[int, str]], fig=None, xlabel="", ylabel="", color_settings:dict|list=[], figsize=None):
    """
    make a bar plot of the ranking
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
def visualize(db: Database):
    """
    This assumes sanity checks have been done
    """
    pdebug("visualizing...")
    if not settings["db"]:          missing_arg("db")
    if not settings["server_name"]: missing_arg("server_name")

    img_dir = settings["img_dir"]
    pdebug("img_dir:", img_dir)
    img_filetype = settings["img_filetype"]
    if isdir(img_dir) and img_filetype:
        gen_img = True
    else:
        print(f"Warning: Not generating images since at least one required variable is invalid: img_dir='{img_dir}', img_filetype='{img_filetype}'")
        gen_img = False

    img_location = settings["img_location"]
    names = {
        # paths
        "img_route_ranking_last_x_days": f"ranking_routes_last_x_days.{img_filetype}",
        "img_referer_ranking_last_x_days": f"ranking_referers_last_x_days.{img_filetype}",
        "img_countries_last_x_days": f"ranking_countries_last_x_days.{img_filetype}",
        "img_cities_last_x_days": f"ranking_cities_last_x_days.{img_filetype}",
        "img_browser_ranking_last_x_days": f"ranking_browsers_last_x_days.{img_filetype}",
        "img_platform_ranking_last_x_days": f"ranking_platforms_last_x_days.{img_filetype}",
        "img_visitors_and_requests_last_x_days": f"visitor_request_count_daily_last_x_days.{img_filetype}",

        "img_route_ranking_total": f"ranking_routes_total.{img_filetype}",
        "img_referer_ranking_total": f"ranking_referers_total.{img_filetype}",
        "img_countries_total": f"ranking_countries_total.{img_filetype}",
        "img_cities_total": f"ranking_cities_total.{img_filetype}",
        "img_browser_ranking_total": f"ranking_browsers_total.{img_filetype}",
        "img_platform_ranking_total": f"ranking_platforms_total.{img_filetype}",
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

    db = Database(database_path=settings["db"])

    get_humans = settings["get_human_percentage"]
    # pdebug(f"visualize: settings {settings}")
    # DATE STRINGS
    earliest_date = db.get_earliest_date()
    names["earliest_date"] = dt.fromtimestamp(earliest_date).strftime("%Y-%m-%d")
    names["generation_date"] = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    # LAST_X_DAYS
    # last_x_days_min_date: latest_date - last_x_days
    secs_per_day = 86400
    last_x_days_min_date = db.get_latest_date() - settings["last_x_days"] * secs_per_day
    last_x_days_constraint = get_where_date_str(min_date=last_x_days_min_date)
    last_x_days = db.get_days_where(last_x_days_constraint)
    last_x_days_contraints = [get_where_date_str(at_date=day) for day in last_x_days]

    # ALL DATES
    all_time_constraint = get_where_date_str(min_date=0)
    # all months in yyyy-mm format
    months_all_time = db.get_months_where(all_time_constraint)
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
        date_constraint = [all_time_constraint, last_x_days_constraint][i]
        date_names = [months_all_time, last_x_days][i]
        date_constraints = [months_strs, last_x_days_contraints][i]
        assert(len(date_names) == len(date_constraints))

        # FILES
        # TODO handle groups
        file_ranking = get_route_ranking(db, date_constraint)
        if gen_img:
            fig_file_ranking = plot_ranking(file_ranking, xlabel="Route Name", ylabel="Number of requests", color_settings=color_settings_filetypes, figsize=settings["plot_size_broad"])
            fig_file_ranking.savefig(f"{img_dir}/{names[f'img_route_ranking{suffix}']}", bbox_inches="tight")

        # REFERER
        referer_ranking = get_ranking(db, "request", "referer", date_constraint, settings["referer_ranking_whitelist"], settings["referer_ranking_whitelist"])
        pdebug("Referer ranking", referer_ranking)
        cleanup_referer_ranking(referer_ranking)
        if gen_img:
            fig_referer_ranking = plot_ranking(referer_ranking, xlabel="HTTP Referer", ylabel="Number of requests", color_settings=color_settings_alternate, figsize=settings["plot_size_broad"])
            fig_referer_ranking.savefig(f"{img_dir}/{names[f'img_referer_ranking{suffix}']}", bbox_inches="tight")

        # GEOIP
        if settings["do_geoip_rankings"]:
            city_ranking, country_ranking = get_city_and_country_ranking(db, require_humans=settings["geoip_only_humans"])
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
        unique_visitor_ids = get_unique_visitor_ids_for_date(db, date_constraint)
        unique_visitor_ids_human = []
        append_human_visitors(db, unique_visitor_ids, unique_visitor_ids_human)
        # for each date
        date_count = len(date_constraints)
        unique_visitor_ids_dates: list[list[int]] = []
        unique_request_ids_dates: list[list[int]] = []
        unique_visitor_ids_human_dates: list[list[int]] = [[] for _ in range(date_count)]
        unique_request_ids_human_dates: list[list[int]] = [[] for _ in range(date_count)]
        for i in range(date_count):
            date_constraint_ = date_constraints[i]
            unique_visitor_ids_dates.append(get_unique_visitor_ids_for_date(db, date_constraint_))
            unique_request_ids_dates.append(get_unique_request_ids_for_date(db, date_constraint_))
            if get_humans:
                # empty_list = []
                # unique_visitor_ids_human_dates.append(empty_list)
                append_human_visitors(db, unique_visitor_ids_dates[i], unique_visitor_ids_human_dates[i])
                # unique_request_ids_human_dates.append(list())
                for human in unique_visitor_ids_human_dates[i]:
                    append_unique_request_ids_for_date_and_visitor(db, date_constraint_, human, unique_request_ids_human_dates[i])
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
        platform_ranking, browser_ranking, names[f"mobile_visitor_percentage{suffix}"] = get_platform_browser_mobile_rankings(db, unique_visitor_ids_human)
        if gen_img:
            fig_os_rating = plot_ranking(platform_ranking, xlabel="Platform", ylabel="Share [%]", color_settings=color_settings_platforms, figsize=settings["plot_size_narrow"])
            fig_os_rating.savefig(f"{img_dir}/{names[f'img_platform_ranking{suffix}']}", bbox_inches="tight")
            fig_browser_rating = plot_ranking(browser_ranking, xlabel="Browser", ylabel="Share [%]", color_settings=color_settings_browsers, figsize=settings["plot_size_narrow"])
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
            if type(value) == float:
                value = f"{value:.2f}"
            html = html.replace(f"%{name}", str(value))
        with open(settings["html_out_path"], "w") as file:
            file.write(html)
    else:
        warning(f"Skipping html generation because either template_html or html_out_path is invalid: template_html='{settings['template_html']}', html_out_path='{settings['html_out_path']}'")
