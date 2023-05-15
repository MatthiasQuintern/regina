# from sys import path
# print(f"{__file__}: __name__={__name__}, __package__={__package__}, sys.path[0]={path[0]}")
import matplotlib.pyplot as plt
from pickle import dump
from os import path, makedirs
from datetime import datetime as dt

# local
from regina.database import Database
from regina.utility.sql_util import get_date_constraint, sanitize
from regina.utility.utility import pdebug, warning, error, make_parent_dirs, dict_str
from regina.utility.globals import settings
from regina.data_visualization.utility import len_list_list
from regina.data_visualization.ranking import get_referer_ranking, cleanup_referer_ranking, get_route_ranking, route_ranking_group_routes, get_browser_ranking, get_platform_ranking, get_city_ranking, get_country_ranking, make_ranking_relative
import regina.data_visualization.history as h

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

color_settings_history = {
    "visitors":         "#000050",
    "visitors_human":   "#3366ff",
    "visitors_new":     "#66ccff",
    "requests":         "#770000",
    "requests_human":   "#ff3500",
    "requests_new":     "#ff9999",
}


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

def plot_ranking(ranking: list[tuple[int or float, str]], fig=None, xlabel="", ylabel="", color_settings:dict|list=[], figsize=None):
    """
    make a bar plot of the ranking
    """
    # pdebug(f"plot_ranking: ranking={ranking}")
    if not fig:
        fig = plt.figure(figsize=figsize, dpi=settings["plot-generation"]["dpi"], linewidth=1.0, frameon=True, subplotpars=None, layout=None)
    # create new axis if none is given
    ax = fig.add_subplot(xlabel=xlabel, ylabel=ylabel)
    # fill x y data
    if len(ranking) > settings["rankings"]["route_plot_max_routes"]:
        start_index = len(ranking) - settings["rankings"]["route_plot_max_routes"]
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
        if settings["plot-generation"]["add_count_label"]: add_labels_at_top_of_bar(x_names, y_counts, y_counts[-1], ax, bar)
    # ax.ylabel(y_counts)
    return fig


# def plot(xdata, ydata, fig=None, ax=None, xlabel="", ylabel="", label="", linestyle='-', marker="", color="blue", rotate_xlabel=0):
#     if not fig:
#         fig = plt.figure(figsize=None, dpi=settings["plot-generation"]["dpi"], linewidth=1.0, frameon=True, subplotpars=None, layout=None)
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


class Plot2Y:
    def __init__(self, xlabel, ylabel_left, ylabel_right, grid="major", rotate_xlabel=0, figsize=None):
        self.fig, self.ax1 = plt.subplots(figsize=figsize, dpi=settings["plot-generation"]["dpi"], linewidth=1.0, frameon=True, subplotpars=None, layout=None)
        self.ax1.set_xlabel(xlabel=xlabel) #, ylabel=ylabel_left)
        self.ax1.set_ylabel(ylabel=ylabel_left) #, ylabel=ylabel_left)
        self.ax2 = self.ax1.twinx()
        self.ax2.set_ylabel(ylabel_right)
        self.ax1.tick_params(axis="x", rotation=90)
        self.plots = None
        if grid == "major" or grid == "minor" or grid == "both":
            if grid == "minor" or "both":
                self.ax1.minorticks_on()
            self.ax1.grid(visible=True, which=grid, linestyle="-", color="#888")

    def _plot(self, ax, xdata, ydata, label="", linestyle="-", marker="", color="blue"):
        plot = ax.plot(xdata, ydata, marker=marker, label=label, linestyle=linestyle, color=color)
        # ax1.set_xticks(ax1.get_xticks())
        # ax1.set_xticklabels(xdata, rotation=rotate_xlabel, rotation_mode="anchor")
        # if label1 or label2: ax1.legend()
        if self.plots: self.plots += plot
        else: self.plots = plot
        plt.legend(self.plots, [ l.get_label() for l in self.plots ])


    def plot_left(self, xdata, ydata, label="", linestyle="-", marker="", color="blue"):
        self._plot(self.ax1, xdata, ydata, label, linestyle, marker, color)

    def plot_right(self, xdata, ydata, label="", linestyle="-", marker="", color="blue"):
        self._plot(self.ax2, xdata, ydata, label, linestyle, marker, color)

    def get_fig(self):
        return self.fig


#
# MAIN
#
def visualize(db: Database):
    """
    This assumes sanity checks have been done
    """
    pdebug("visualizing...")

    def make_dir_if_not_None(d):
        if d:
            if not path.isdir(d):
                makedirs(d)

    # plot generation
    img_out_dir = settings["plot-generation"]["img_out_dir"]
    make_dir_if_not_None(img_out_dir)
    img_filetype = settings["plot-generation"]["filetype"]
    img_location = settings["html-generation"]["img_location"]
    pdebug(f"visualize: img_out_dir='{img_out_dir}', filetype='{img_filetype}', {img_location}='{img_location}'", lvl=2)
    if not img_out_dir:
        pdebug(f"visualize: Not generating images since img_out_dir is None", lvl=1)

    # data export
    data_out_dir = settings["data-export"]["data_out_dir"]
    make_dir_if_not_None(data_out_dir)
    data_filetype = settings["data-export"]["filetype"]
    pdebug(f"visualize: data_out_dir='{data_out_dir}', filetype='{data_filetype}'", lvl=2)
    if not data_out_dir:
        pdebug(f"visualize: Not exporting data since data_out_dir is None", lvl=1)

    if not data_out_dir and not img_out_dir:
        warning(f"data_out_dir and img_out_dir are both None. No data will be exported and no plots will be generated!")

    html_variables = {
        # values
        "visitor_count_last_x_days": "NaN",
        "visitor_count_total": "NaN",
        "request_count_last_x_days": "NaN",
        "request_count_total": "NaN",
        "visitor_count_human_last_x_days": "NaN",
        "visitor_count_human_total": "NaN",
        "request_count_human_last_x_days": "NaN",
        "request_count_human_total": "NaN",
        "human_visitor_percentage_last_x_days": "NaN",
        "human_visitor_percentage_total": "NaN",
        "human_request_percentage_last_x_days": "NaN",
        "human_request_percentage_total": "NaN",
        "mobile_visitor_percentage_total": "NaN",
        "mobile_visitor_percentage_last_x_days": "NaN",
        # general
        "regina_version":   settings["regina"]["version"],
        "server_name":      settings["regina"]["server_name"],
        "last_x_days":      settings["data-visualization"]["last_x_days"],
        "earliest_date":    "1990-1-1",
        "generation_date":  "1990-1-1 0:0:0",
    }

    for suffix in ["last_x_days", "total"]:
        # add all plot paths as variables: img_plot_suffix -> plot_suffix.filetype
        # not adding img_location or img_out_dir since these names are needed for both
        html_variables.update((f"img_{plot_}_{suffix}", f"{plot_}_{suffix}.{img_filetype}") for plot_ in ["ranking_platform", "ranking_browser", "ranking_country", "ranking_city", "ranking_referer", "ranking_route", "history_visitor_request"])

    get_humans_visitors = settings["data-visualization"]["history_track_human_visitors"]
    get_new_visitors = settings["data-visualization"]["history_track_new_visitors"]

    # DATE STRINGS
    earliest_timestamp = db.get_earliest_timestamp()
    html_variables["earliest_date"] = dt.fromtimestamp(earliest_timestamp).strftime("%Y-%m-%d")
    html_variables["generation_date"] = dt.now().strftime("%Y-%m-%d %H:%M:%S")

    todos: list[tuple[str, tuple[int, int], list[str], list[str], list[tuple[int, int]]]] = []  # suffix, whole_time_timestamps, history_date_constraints, history_date_names, history_date_timestamps

    now_stamp = int(dt.now().timestamp())
    total: bool = settings["data-visualization"]["total"]
    if total:
        all_time_timestamps = (0, now_stamp)
        # all months in yyyy-mm format
        month_names = db.get_months_where(get_date_constraint(min_date=0))
        month_timestamps = []
        # sqlite constrict to month string
        month_constraints = []
        for year_month in month_names:
            year, month = year_month.split("-")
            # timestamp of first day of the month
            min_date  = int(dt(int(year), int(month), 1).timestamp())
            month = (int(month) % 12) + 1  # + 1 month
            year = int(year)
            # first day of the next month - 1 sec
            if month == 1: year += 1
            max_date = int(dt(year, month, 1).timestamp()) - 1
            month_constraints.append(get_date_constraint(min_date=min_date, max_date=max_date))
            month_timestamps.append((min_date, max_date))
        todos.append(("total", all_time_timestamps, month_constraints, month_names, month_timestamps))

    last_x_days: int = settings["data-visualization"]["last_x_days"]
    if last_x_days > 0:
        secs_per_day   = 86400
        last_x_days_min_date      = db.get_latest_timestamp() - last_x_days * secs_per_day
        last_x_days_timestamps = (last_x_days_min_date, now_stamp)
        last_x_days_constraint    = get_date_constraint(min_date=last_x_days_min_date)
        days                = db.get_days_where(last_x_days_constraint)  # yyyy-mm-dd
        day_constrains      = [ get_date_constraint(at_date=day) for day in days ]
        day_timestamps  = []
        for day in days:
            year, month, day = day.split("-")
            min_date  = int(dt(int(year), int(month), int(day)).timestamp())
            max_date = min_date + secs_per_day
            day_timestamps.append((min_date, max_date))

        todos.append(("last_x_days", last_x_days_timestamps, day_constrains, days, day_timestamps))

    def export_ranking(name: str, column_name: str, ranking: list[tuple[int or float, str]]):
        filename = f"{data_out_dir}/{name}.{data_filetype}"
        if data_filetype == "pkl":
            pdebug(f"visualize: Exporting {name} as pickle to '{filename}'", lvl=2)
            with open(filename, "wb") as file:
                dump(ranking, file)
        elif data_filetype == "csv":
            pdebug(f"visualize: Exporting {name} as csv to '{filename}'", lvl=2)
            s = f'"{name}"\n'
            s += f'"count","{column_name}"\n'
            for count, item in ranking:
                s += f'{count},"{item}"\n'
            s = s.strip("\n")
            with open(filename, "w") as file:
                file.write(s)
        else:
            error(f"visualize: Unsupported data filetype: '{data_filetype}'")

    def savefig(name: str, figure):
        filename = f"{img_out_dir}/{name}.{img_filetype}"
        pdebug(f"visualize: Saving plot for {name} as '{filename}'")
        figure.savefig(filename, bbox_inches="tight")  # bboximg_inches="tight"


    pdebug(f"visualize: total={total}, last_x_days={last_x_days}", lvl=3)
    for suffix, whole_timespan_timestamps, single_date_constraints, single_date_names, single_date_timestamps in todos:
        assert(len(single_date_names) == len(single_date_constraints))

        # STATISTICS
        visitor_count = h.get_visitor_count_between(db, whole_timespan_timestamps)
        request_count = h.get_request_count_between(db, whole_timespan_timestamps)
        html_variables[f"visitor_count_{suffix}"] = visitor_count
        html_variables[f"request_count_{suffix}"] = request_count

        if get_humans_visitors:
            visitor_count_human = h.get_visitor_count_between(db, whole_timespan_timestamps, only_human=True)
            request_count_human = h.get_request_count_between(db, whole_timespan_timestamps, only_human=True)
            html_variables[f"visitor_count_human_{suffix}"] = visitor_count_human
            html_variables[f"request_count_human_{suffix}"] = request_count_human
            try:                        html_variables[f"human_visitor_percentage_{suffix}"] = 100.0 * visitor_count_human / visitor_count
            except ZeroDivisionError:   pass
            try:                        html_variables[f"human_request_percentage_{suffix}"] = 100.0 * request_count_human / request_count
            except ZeroDivisionError:   pass
            try:                        html_variables[f"mobile_visitor_percentage_{suffix}"] = 100.0 * h.get_mobile_visitor_count_between(db, whole_timespan_timestamps, only_human=True) / visitor_count_human
            except ZeroDivisionError:   pass

        # HISTORY
        date_count = len(single_date_constraints)
        visitor_count_dates = [ h.get_visitor_count_between(db, single_date_timestamps[i], only_human=False) for i in range(date_count) ]
        request_count_dates = [ h.get_request_count_between(db, single_date_timestamps[i], only_human=False) for i in range(date_count) ]

        visitor_count_human_dates = [ h.get_visitor_count_between(db, single_date_timestamps[i], only_human=True) for i in range(date_count) ]
        request_count_human_dates = [ h.get_request_count_between(db, single_date_timestamps[i], only_human=True) for i in range(date_count) ]

        visitor_count_new_dates = [ h.get_new_visitor_count_between(db, single_date_timestamps[i]) for i in range(date_count) ]
        request_count_new_dates = [ h.get_request_from_new_visitor_count_between(db, single_date_timestamps[i]) for i in range(date_count) ]

        if img_out_dir:
            plt_history = Plot2Y(xlabel="Date", ylabel_left="Visitor count", ylabel_right="Request count", rotate_xlabel=-45, figsize=settings["plot-generation"]["size_broad"])
            # visitors, plot on correct order
            plt_history.plot_left(single_date_names, visitor_count_dates, label="Unique visitors", color=color_settings_history["visitors"])
            if get_humans_visitors:
                plt_history.plot_left(single_date_names, visitor_count_human_dates, label="Unique visitors (human)", color=color_settings_history["visitors_human"])
            if get_new_visitors:
                plt_history.plot_left(single_date_names, visitor_count_new_dates, label="Unique visitors (new)", color=color_settings_history["visitors_new"])
            # requests
            plt_history.plot_right(single_date_names, request_count_dates, label="Unique requests", color=color_settings_history["requests"])
            if get_humans_visitors:
                plt_history.plot_left(single_date_names, request_count_human_dates, label="Unique requests (human)", color=color_settings_history["requests_human"])
            if get_new_visitors:
                plt_history.plot_left(single_date_names, request_count_new_dates, label="Unique requests (new)", color=color_settings_history["requests_new"])

            savefig(f"history_visitor_request_{suffix}", plt_history.get_fig())
        # if data_out_dir:  # TODO export history
        #     s = ""

        # ROUTES
        # TODO handle groups
        route_ranking = get_route_ranking(db, whole_timespan_timestamps)
        route_ranking = route_ranking_group_routes(route_ranking)
        pdebug("visualize: route ranking", route_ranking, lvl=3)
        if img_out_dir:
            fig_file_ranking = plot_ranking(route_ranking, xlabel="Route", ylabel="Number of requests", color_settings=color_settings_filetypes, figsize=settings["plot-generation"]["size_broad"])
            savefig(f"ranking_route_{suffix}", fig_file_ranking)
        if data_out_dir:
            export_ranking(f"ranking_route_{suffix}", "route", route_ranking)


        # REFERER
        referer_ranking = get_referer_ranking(db, whole_timespan_timestamps)
        cleanup_referer_ranking(referer_ranking)
        pdebug("visualize: referer ranking", referer_ranking, lvl=3)
        if img_out_dir:
            fig_referer_ranking = plot_ranking(referer_ranking, xlabel="HTTP Referer", ylabel="Number of requests", color_settings=color_settings_alternate, figsize=settings["plot-generation"]["size_broad"])
            savefig(f"ranking_referer_{suffix}", fig_referer_ranking)
        if data_out_dir:
            export_ranking(f"ranking_referer_{suffix}", "referer", referer_ranking)

        # GEOIP
        if settings["data-collection"]["get_visitor_location"]:
            country_ranking = get_country_ranking(db, whole_timespan_timestamps, only_human=settings["rankings"]["geoip_only_humans"])
            pdebug("visualize: country ranking:", country_ranking, lvl=3)
            city_ranking = get_city_ranking(db, whole_timespan_timestamps, add_country_code=settings["rankings"]["city_add_country_code"], only_human=settings["rankings"]["geoip_only_humans"])
            pdebug("visualize: city ranking:", city_ranking, lvl=3)
            if img_out_dir:
                fig_referer_ranking = plot_ranking(country_ranking, xlabel="Country", ylabel="Number of visitors", color_settings=color_settings_alternate, figsize=settings["plot-generation"]["size_broad"])
                savefig(f"ranking_country_{suffix}", fig_referer_ranking)
                fig_referer_ranking = plot_ranking(city_ranking, xlabel="City", ylabel="Number of visitors", color_settings=color_settings_alternate, figsize=settings["plot-generation"]["size_broad"])
                savefig(f"ranking_city_{suffix}", fig_referer_ranking)
            if data_out_dir:
                export_ranking(f"ranking_country_{suffix}", "country", country_ranking)
                export_ranking(f"ranking_city_{suffix}", "city", city_ranking)

        # os & browser
        browser_ranking = get_browser_ranking(db, whole_timespan_timestamps, only_human=False)
        browser_ranking = make_ranking_relative(browser_ranking)
        pdebug("visualize: browser ranking:", browser_ranking, lvl=3)
        platform_ranking = get_platform_ranking(db, whole_timespan_timestamps, only_human=False)
        platform_ranking = make_ranking_relative(platform_ranking)
        pdebug("visualize: platform ranking:", platform_ranking, lvl=3)
        if img_out_dir:
            fig_os_rating = plot_ranking(platform_ranking, xlabel="Platform", ylabel="Share [%]", color_settings=color_settings_platforms, figsize=settings["plot-generation"]["size_narrow"])
            savefig(f"ranking_platform_{suffix}", fig_os_rating)
            fig_browser_rating = plot_ranking(browser_ranking, xlabel="Browser", ylabel="Share [%]", color_settings=color_settings_browsers, figsize=settings["plot-generation"]["size_narrow"])
            savefig(f"ranking_browser_{suffix}", fig_browser_rating)
        if data_out_dir:
            export_ranking(f"ranking_platform_{suffix}", "platform", platform_ranking)
            export_ranking(f"ranking_browser_{suffix}", "browser", browser_ranking)


    html_variables_str = dict_str(html_variables).replace('\n', '\n\t')
    pdebug(f"visualize: html_variables:\n\t{html_variables_str}", lvl=2)

    template_html: str|None = settings["html-generation"]["template_html"]
    html_out_path: str|None = settings["html-generation"]["html_out_path"]
    if template_html and html_out_path:
        pdebug(f"visualize: generating from template '{template_html}' to '{html_out_path}'", lvl=2)
        if not path.isfile(template_html):
            error(f"Invalid template file path: '{template_html}'")
        with open(template_html, "r") as file:
            html = file.read()
        for name, value in html_variables.items():
            if "img" in name:
                value = f"{img_location}/{value}"
            elif type(value) == float:
                value = f"{value:.2f}"
            html = html.replace(f"%{name}", str(value))
        make_parent_dirs(html_out_path)
        with open(html_out_path, "w") as file:
            file.write(html)
    else:
        pdebug(f"visualize: skipping html generation because either template_html or html_out_path is None: template_html='{template_html}', html_out_path='{html_out_path}'", lvl=1)
