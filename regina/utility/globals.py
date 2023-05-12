"""global variables for regina"""

import os

version = "2.0"



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


# set directories
config_dir   = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),       "regina")
data_dir     = os.path.join(os.environ.get("XDG_DATA_HOME",   os.path.expanduser("~/.local/share")),  "regina")
cache_dir    = os.path.join(os.environ.get("XDG_CACHE_HOME",  os.path.expanduser("~/.cache")),        "regina")

# check if environment variables are set and use them if they are
if 'REGINA_CONFIG_DIR' in os.environ: config_dir = os.environ['REGINA_CONFIG_DIR']
if 'REGINA_DATA_DIR' in os.environ: data_dir = os.environ['REGINA_DATA_DIR']
if 'REGINA_CACHE_DIR' in os.environ: cache_dir = os.environ['REGINA_CACHE_DIR']
