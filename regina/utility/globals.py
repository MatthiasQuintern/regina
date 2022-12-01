"""global variables for regina"""

version = "1.0"

# default settings, these are overwriteable through a config file
settings = {
    # GENERAL
    "server_name": "",
    # DATA COLLECTION
    "access_log": "",
    "db": "",
    "locs_and_dirs": [],
    "auto_group_filetypes": [],
    "filegroups": "",
    "request_location_regex_blacklist": "",
    "request_is_same_on_same_day": True,  # mutiple requests from same user to same file at same day are counted as 1
    "unique_user_is_ip_address": False,
    "user_get_country": True,

    # VISUALIZATION
    "get_human_percentage": False,
    "human_needs_success": True,  # a human must have at least 1 successful request (status < 300)
    "status_300_is_success": False,  # 300 codes are success
    # "file_ranking_regex_whitelist": r".*\.((txt)|(html)|(css)|(php)|(png)|(jpeg)|(jpg)|(svg)|(gif))",
    "file_ranking_regex_whitelist": r".*\.(html)",
    "file_ranking_ignore_error_files": False,  # skip files that only had unsuccessful requests (status < 300)
    "referer_ranking_ignore_protocol": True,
    "referer_ranking_ignore_subdomain": False,
    "referer_ranking_ignore_location": True,
    "referer_ranking_ignore_tld": False,
    "referer_ranking_regex_whitelist": r"^[^\-].*",  # minus means empty
    "user_agent_ranking_regex_whitelist": r"",
    "file_ranking_plot_max_files": 15,
    # "plot_figsize": (60, 40),
    "plot_dpi": 300,
    "plot_add_count_label": True,
    "img_dir": "",
    "img_location": "",
    "img_filetype": "svg",
    "template_html": "",
    "html_out_path": "",
    "last_x_days": 30,
}

# these oses and browser can be detected:
# lower element takes precedence
user_agent_operating_systems = ["Windows", "Android", "Linux", "iPhone", "iPad", "Mac", "BSD"]
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


