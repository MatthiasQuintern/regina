"""global variables for regina"""

import os
import re
import importlib.metadata

if __name__ == "__main__":  # make relative imports work as described here: https://peps.python.org/pep-0366/#proposed-change
    if __package__ is None:
        __package__ = "regina"
        import sys
        from os import path
        filepath = path.realpath(path.abspath(__file__))
        sys.path.insert(0, path.dirname(path.dirname(path.dirname(filepath))))

from regina.utility.config import CFG_Entry, CFG_File, ReginaSettings, Path, comment

version = importlib.metadata.version("regina")

# these oses and browser can be detected:
# lower element takes precedence
user_agent_platforms = ["Windows", "Android", "Linux", "iPhone", "iPad", "Mac", "BSD", "CrOS", "PlayStation", "Xbox", "Nintendo Switch"]
"""
some browsers have multiple browsers in their user agent:
    SeaMonkey: Firefox
    Waterfox: Firefox
    Chrome: Safari
    Edge: Chrome, Safari
    SamsungBrowser: Chrome, Safari

"""
user_agent_browsers = [
    # todo YaBrowser/Yowser, OPR, Edg
    # order does not matter, as long as firefox, chrome safari come later
    "DuckDuckGo", "SeaMonkey", "Waterfox", "Vivaldi", "Yandex", "Brave", "SamsungBrowser", "Lynx", "Epiphany",
    # order does matter
    # Edg sometimes uses Edg or EdgA (android)
    "Firefox", "Opera", "Edg", "Chromium", "Chrome", "Safari"
]


# set directories
config_dir   = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),       "regina")
data_dir     = os.path.join(os.environ.get("XDG_DATA_HOME",   os.path.expanduser("~/.local/share")),  "regina")
cache_dir    = os.path.join(os.environ.get("XDG_CACHE_HOME",  os.path.expanduser("~/.cache")),        "regina")

# check if environment variables are set and use them if they are
if 'REGINA_CONFIG_DIR'  in os.environ: config_dir = os.environ['REGINA_CONFIG_DIR']
if 'REGINA_DATA_DIR'    in os.environ: data_dir   = os.environ['REGINA_DATA_DIR']
if 'REGINA_CACHE_DIR'   in os.environ: cache_dir  = os.environ['REGINA_CACHE_DIR']


cfg = CFG_File(header=r"""
************************************* REGINA CONFIGURATION **************************************
                      .__
_______   ____   ____ |__| ____ _____
\_  __ \_/ __ \ / ___\|  |/    \\__  \
|  | \/\  ___// /_/  >  |   |  \/ __ \_
|__|    \___  >___  /|__|___|  (____  /
            \/_____/         \/     \/
*************************************************************************************************
data_dir:   ~/.local/share/regina   < $XDG_DATA_HOME/regina     < $REGINA_DATA_DIR
config_dir: ~/.config/regina        < $XDG_CONFIG_HOME/regina   < $REGINA_CONFIG_DIR
*************************************************************************************************

""".strip(" \n"), footer=r"""
*************************************************************************************************
https://git.quintern.xyz/MatthiasQuintern/regina
*************************************************************************************************
""".strip(" \n"))
cfg.add_section("regina", desc="", entries=[
    CFG_Entry("server_name",
            desc="name of the server or website\nwill be avaiable as variable for the generated html as %server_name",
            typ_=str,
            exam="my_website"),
    CFG_Entry("database",
            desc="database path. if None, 'data_dir/server_name.db' is used",
            typ_=[Path(permissions="rw"), None],
            exam="/home/my_user/.local/share/regina/my_website.db"),
    CFG_Entry("access_log",
            desc="path to the nginx access log to parse",
            typ_=Path(permissions="r"),
            exam="/var/log/nginx/access.log"),
    ])

cfg.add_section("data-collection", desc="These settings affect the data collection. If changed, they will affect how the database is being filled in the future.", entries=[
    CFG_Entry("unique_visitor_is_ip_address",
            dflt=False,
            desc="whether a unique visitor is only identified by IP address. if False, browser and platform are also taken into account",
            typ_=bool),
    CFG_Entry("human_needs_successful_request",
            dflt=True,
            desc="whether a visitor needs at least one successful request to be a human",
            typ_=bool),
    CFG_Entry("status_300_is_success",
            dflt=True,
            desc="whether a request with 30x HTTP status counts as successful request",
            typ_=bool),
    CFG_Entry("ignore_duplicate_requests_within_x_seconds",
            dflt=0,
            desc="ignore requests from the same visitor to the same route if one was made within the last x seconds",
            typ_=int),

    CFG_Entry("delete_ip_addresses",  # TODO: Implement
            dflt=True,
            desc="delete all ip addresses after the collection is done (not implemented yet!)",
            typ_=bool),

    CFG_Entry("request_route_blacklist",
            desc="don't collect requests to locations that match this regex",
            typ_=[re.Pattern, None],
            exam="/analytics.*"),
    CFG_Entry("request_route_whitelist",
            desc="only collect requests to locations that match this regex",
            typ_=[re.Pattern, None]),

    CFG_Entry("get_visitor_location",
            dflt=False,
            desc="whether to get visitor location information (requires GeoIP database)",
            typ_=bool),
    CFG_Entry("get_cities_for_countries",
            desc="countries for which the GeoIP needs to be resolved at city level (example is EU, China, US). write 'all' to get all countries",
            typ_="list of capitalized ISO 3166-1 alpha-2 country codes: https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2#Officially_assigned_code_elements",
            exam="AT, BE, BG, HR, CY, CZ, DK, EE, FI, FR, DE, GZ, HU, IE, IT, LV, LT, LU, MT, NL, PL, PT, RO, SK, SI, ES, SE, CN, US"),
    ])

cfg.add_section("data-visualization", desc="These settings affect the data visualization, they can be changed at any time since they do not affect the database itself.", entries=[
    CFG_Entry("total",
            desc="generate all statistics for the whole database",
            dflt=True,
            typ_=bool),
    CFG_Entry("last_x_days",
            desc="generate all statistics for the last x days. Will be skipped if 0",
            dflt=30,
            typ_=int),
    CFG_Entry("history_track_human_visitors",
            desc="generate extra entries in visitor-request history for visitors/requests that come from human visitor",
            dflt=True,
            typ_=bool),
    CFG_Entry("history_track_new_visitors",  # TODO
            desc="generate extra entry in visitor-request history for new visitors",
            dflt=True,
            typ_=bool),
    ])

cfg.add_section("html-generation", desc="The template and generated file do actually have to be htmls, you can change it to whatever you want", entries=[
    CFG_Entry("template_html",
            desc="template html input. If None, no html will be generated",
            typ_=[Path(permissions="r"), None],
            exam="/home/my_user/.config/regina/template.html"),
    CFG_Entry("html_out_path",
            desc="output for the generated html. If None, no html will be generated",
            typ_=[Path(permissions="w"), None],
            exam="/www/analytics/statistics.html"),
    CFG_Entry("img_location",
            desc="nginx location for the generated images (this has to map to img_out_dir)",
            typ_=str,
            exam="/images"),
    ])

cfg.add_section("plot-generation", desc="Settings that affect the generated plots and images", entries=[
    CFG_Entry("img_out_dir",
            desc="output directory for the generated plots. If None, no plots will be generated",
            typ_=[Path(permissions="w", is_dir=True), None],
            exam="/www/analytics/images"),
    CFG_Entry("filetype",
            dflt="svg",
            desc="file extension for the generated plots",
            typ_=str),
    CFG_Entry("dpi",
            dflt=300,
            desc="DPI for plots",
            typ_=int),
    CFG_Entry("size_broad",
            dflt=(14, 5),
            desc="plot size for broad plots: width, height",
            typ_=(int, int)),
    CFG_Entry("size_narrow",
            dflt=(7, 5),
            desc="plot size for narrow plots: width, height",
            typ_=(int, int)),
    CFG_Entry("add_count_label",
            dflt=True,
            desc="add the height of the bar as label in bar plots",
            typ_=bool),
    ])

cfg.add_section("data-export", desc="", entries=[
    CFG_Entry("data_out_dir",
            desc="output directory for the generated data files. If None, no data will be exported",
            typ_=[Path(permissions="w", is_dir=True), None],
            exam="/www/analytics/images"),
    CFG_Entry("filetype",
            dflt="csv",
            desc="file extension for the exported data",
            typ_="'csv' or 'pkl'"),
    ])

cfg.add_section("rankings", desc="These options only apply if img_out_dir is not None", entries=[
    comment("""
Explanation for blacklists and whitelists:
If a blacklist is given: values that fully match the blacklist are excluded
If a whitelist is given: values that do not fully match the whitelist are excluded
Both are optional: you can provide, none or both
    """.strip("\n")),
    CFG_Entry("geoip_only_humans",
            dflt=True,
            desc="whether to use only humans for city and country rankings",
            typ_=bool),
    CFG_Entry("city_blacklist",
            typ_=[re.Pattern, None],
            dflt="City in .*"),
    CFG_Entry("city_whitelist",
            typ_=[re.Pattern, None]),
    CFG_Entry("city_add_country_code",
            desc="whether to add the 2 letter country code to the name of the city",
            typ_=bool,
            dflt=True),

    CFG_Entry("country_blacklist",
            typ_=[re.Pattern, None]),
    CFG_Entry("country_whitelist",
            typ_=[re.Pattern, None]),

    CFG_Entry("route_blacklist",
            typ_=[re.Pattern, None],
            exam=r".*\.((css)|(txt))"),
    CFG_Entry("route_whitelist",
            typ_=[re.Pattern, None],
            exam=r".*\.((php)|(html)|(php)|(png)|(jpeg)|(jpg)|(svg)|(gif))"),
    CFG_Entry("route_plot_max_routes",
            dflt=20,
            desc="maximum number of entries in route ranking plot",
            typ_=int),
    CFG_Entry("route_ignore_404",
            dflt=True,
            desc="whether to ignore non-existing routes in ranking",
            typ_=bool),
    # TODO add groups
    # Entry("route_groups",
            # desc="route groups for images",
            # typ_=[re.Pattern, None],
            # exam="*.gif, *.jpeg, *.jpg, *.png, *.svg".replace(", ", "\n")),

    CFG_Entry("referer_blacklist",
            dflt=re.compile("-"),
            typ_=[re.Pattern, None],
            exam="Example: exclude '-' (nginx sets this when there is no referer)"),
    CFG_Entry("referer_whitelist",
            typ_=[re.Pattern, None]),
    CFG_Entry("referer_ignore_protocol",
            dflt=True,
            desc="whether to ignore protocol in the referer ranking (if True: https://domain.com == http://domain.com -> domain.com)",
            typ_=bool),
    CFG_Entry("referer_ignore_subdomain",
            dflt=False,
            desc="whether to ignore subdomains in the referer ranking (if True: sub.domain.com == another.sub2.domain.com -> domain.com)",
            typ_=bool),
    CFG_Entry("referer_ignore_tld",
            dflt=False,
            desc="whether to ignore the top level domain in the referer ranking (if True: domain.com == domain.net -> domain)",
            typ_=bool),
    CFG_Entry("referer_ignore_port",
            dflt=True,
            desc="whether to ignore the port in the referer ranking (if True: domain.com:80 == domain.com:8080 -> domain.com)",
            typ_=bool),
    CFG_Entry("referer_ignore_route",
            dflt=False,
            desc="whether to ignore route in the referer ranking (if True: domain.com/route1 == domain.com/route2 -> domain.com)",
            typ_=bool),
    ])
cfg.add_section("route-groups", desc="Group certain routes together using by matching them with a regular expression.\nThe route's request count will be added to all matching groups and the route will be removed from the ranking.", entries=[
    comment("Home = /|(/home.html)|(/index.html)"),
    comment(r"Images = .*\.((png)|(jpe?g)|(gif)|(webp)|(svg)|(ico))"),
    comment(r"Resources = /resources/.*"),
    ])

cfg.add_section("debug", desc="", entries=[
    CFG_Entry("debug_level",
            dflt=0,
            desc="Debug level: 0-4",
            typ_=int),
    ])

# with open("generated-default.cfg", "w") as file:
#     file.write(f"{cfg}")

settings = ReginaSettings(cfg)
# settings.load("generated-default.cfg")

def write_config():
    # export the configuration as generated-default.cfg
    with open("regina-default.cfg", "w") as file:
        file.write(f"{cfg}")

if __name__ == "__main__":
    write_config()
