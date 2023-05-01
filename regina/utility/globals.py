"""global variables for regina"""

version = "1.0"

# default settings, these are overwriteable through a config file
settings = {
    # GENERAL
    "server_name": "default_sever",
    # DATA COLLECTION
    "access_log": "",
    "db": "",
    "locs_and_dirs": [],
    "auto_group_filetypes": [],
    "filegroups": "",
    "request_location_regex_blacklist": "",
    "request_is_same_on_same_day": True,  # mutiple requests from same visitor to same file at same day are counted as 1
    "unique_visitor_is_ip_address": False,
    "get_visitor_location": False,
    "get_cities_for_countries": [""],  # list if country codes for which the ip address ranges need to be collected at city level, not country level
    "hash_ip_address": True,

    # VISUALIZATION
    "get_human_percentage": False,
    "human_needs_success": True,  # a human must have at least 1 successful request (status < 300)
    "status_300_is_success": False,  # 300 codes are success
    "do_geoip_rankings": False,
    "geoip_only_humans": True,
    "city_ranking_regex_blacklist": "",
    "country_ranking_regex_blacklist": "",
    # "file_ranking_regex_whitelist": r".*\.((txt)|(html)|(css)|(php)|(png)|(jpeg)|(jpg)|(svg)|(gif))",
    "file_ranking_regex_whitelist": r".*\.(html)",
    "file_ranking_ignore_error_files": False,  # skip files that only had unsuccessful requests (status < 300)
    "referer_ranking_ignore_protocol": True,
    "referer_ranking_ignore_subdomain": False,
    "referer_ranking_ignore_location": True,
    "referer_ranking_ignore_tld": False,
    "referer_ranking_regex_whitelist": r"^[^\-].*",  # minus means empty
    "visitor_agent_ranking_regex_whitelist": r"",
    "file_ranking_plot_max_files": 15,
    # "plot_figsize": (60, 40),
    "plot_dpi": 300,
    "plot_add_count_label": True,
    "plot_size_broad": (10, 5),
    "plot_size_narrow": (6.5, 5),
    "img_dir": "",
    "img_location": "",
    "img_filetype": "svg",
    "template_html": "",
    "html_out_path": "",
    "last_x_days": 30,
    # regina
    "debug": False
}

# these oses and browser can be detected:
# lower element takes precedence
visitor_agent_operating_systems = ["Windows", "Android", "Linux", "iPhone", "iPad", "Mac", "BSD", "CrOS", "PlayStation", "Xbox", "Nintendo Switch"]
"""
some browsers have multiple browsers in their visitor agent:
    SeaMonkey: Firefox
    Waterfox: Firefox
    Chrome: Safari
    Edge: Chrome, Safari
    SamsungBrowser: Chrome, Safari

"""
visitor_agent_browsers = [
    # todo YaBrowser/Yowser, OPR, Edg
    # order does not matter, as long as firefox, chrome safari come later
    "DuckDuckGo", "SeaMonkey", "Waterfox", "Vivaldi", "Yandex", "Brave", "SamsungBrowser", "Lynx", "Epiphany",
    # order does matter
    # Edg sometimes uses Edg or EdgA (android)
    "Firefox", "Opera", "Edg", "Chromium", "Chrome", "Safari"
]


