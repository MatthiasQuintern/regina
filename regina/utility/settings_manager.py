from configparser import ConfigParser

"""
Classes and methods for managing regina configuration

Using CFG_File and CFG_Entry, you set defaults and type restrictions for
a dictionary like ReginaSettings object and also export the defaults as a .cfg file
"""

def comment(s):
    return "# " + s.replace("\n", "\n# ").strip("# ")

# for eventual later type checking
class regexp:
    """
    represents a regular expression
    """
    pass

class Path:
    """
    represents a path
    """
    def __init__(self, permissions="r", is_dir=False):
        self.is_dir = is_dir
        self.permissions = permissions
    def __repr__(self):
        if self.is_dir:
            s = "directory"
        else:
            s = "file"

        if self.permissions:
            s += " ("
            if "r" in self.permissions: s += "read, "
            if "w" in self.permissions: s += "write, "
            if "x" in self.permissions: s += "execute, "
            s = s[:-2] + " permissions)"
        return s


class CFG_Entry:
    """
    key - value pair in a cfg file
    extra parameters for comments on top of the key - value pair
    """
    types = str|Path|None|type[regexp]|type[str]|type[bool]|type[int]
    def __init__(self, key, dflt=None, typ_: types|list[types]|tuple[types] =str, desc="", exam=""):   # all 4 letters -> nice indent
        """
        @param typ: type for the value:
            use list of types if multiple types are allowed
            use tuple of types for tuple of types
        """
        self.key = key
        self.default = dflt
        self.type_ = typ_
        self.descripton= desc
        self.example = exam

    def type_str(self):
        def _type_str(t):
            if type(t) == str:          return t
            if t is None:               return "None"
            if t == str:    return "string"
            if t == bool:   return "True/False"
            if t == int:    return "int"
            if t == float:  return "float"
            if t == regexp: return "regexp"
            if type(t) == Path:         return str(t)
            try:
                return t.__name__
            except AttributeError:
                return str(t)

        s = ""
        if type(self.type_) == list:
            for i in range(len(self.type_)):
                s += _type_str(self.type_[i])
                if i < len(self.type_) - 2: s += ", "
                elif i == len(self.type_) - 2: s += " or "
        elif type(self.type_) == tuple:
            for i in range(len(self.type_)):
                s += _type_str(self.type_[i])
                if i < len(self.type_) - 1: s += ", "
        else:
            s = _type_str(self.type_)
        return s

    def __repr__(self):
        s = ""
        if self.descripton: s += f"{comment(self.descripton)}\n"
        if self.type_:      s += f"{comment('type: ' + self.type_str())}\n"
        # if self.example:    s += f"{comment('eg: ' + self.example)}\n"
        if self.example:    s += comment(f"{self.key} = {self.example}\n")
        s += f"{self.key} = "
        if self.default:    s += f"{self.default}"
        s += "\n"
        return s


class CFG_File:
    """
    represents a cfg file
    use the __repr__ method to export to a file
    """
    def __init__(self, header="", footer=""):
        self.sections = []  # (name, desc, entries)
        self.header = header
        self.footer = footer

    def add_section(self, name:str, entries: list[CFG_Entry|str], desc=""):
        self.sections.append((name, desc, entries))

    def __repr__(self):
        s = comment(self.header) + "\n"

        for name, desc, entries in self.sections:
            if desc:    s += f"\n{comment(desc)}"
            s += f"\n[ {name} ]\n"
            for entry in entries:
                s += f"{entry}\n"
        s += comment(self.footer)
        return s


if __name__ == "__main__":
    cfg = CFG_File(header=r"""
    ************************************* REGINA CONFIGURATION **************************************
                          .__
    _______   ____   ____ |__| ____ _____
    \_  __ \_/ __ \ / ___\|  |/    \\__  \
    |  | \/\  ___// /_/  >  |   |  \/ __ \_
    |__|    \___  >___  /|__|___|  (____  /
                \/_____/         \/     \/
    ************************************************************************************************* """.strip(" \n"), footer=r"""
    *************************************************************************************************
    https://git.quintern.xyz/MatthiasQuintern/regina
    *************************************************************************************************
    """.strip(" \n"))
    cfg.add_section("regina", desc="Common Settings", entries=[
        CFG_Entry("server_name",
                desc="name (not url) of the server or website\nwill be avaiable as variable for the generated html as %server_name",
                typ_=str,
                exam="my_website"),
        CFG_Entry("database",
                desc="database path",
                typ_=Path(permissions="rw"),
                exam="/home/my_user/regina/my_website.db"),
        CFG_Entry("access_log",
                desc="path to the nginx access log to parse",
                typ_=Path(permissions="r"),
                exam="/var/log/nginx/access.log"),
        ])

    cfg.add_section("html-generation", desc="The template and generated file do actually have to be htmls, you can change it to whatever you want", entries=[
        CFG_Entry("generate_html",
                typ_=bool,
                dflt=True),
        CFG_Entry("template_html",
                desc="template html input",
                typ_=Path(permissions="r"),
                exam="/home/my_visitor/.regina/template.html"),
        CFG_Entry("html_out_path",
                desc="output for the generated html",
                typ_=Path(permissions="w"),
                exam="/www/analytics/statistics.html"),
        CFG_Entry("img_out_dir",
                desc="output directory for the generated plots",
                typ_=Path(permissions="w", is_dir=True),
                exam="/www/analytics/images"),
        CFG_Entry("img_location",
                desc="nginx location for the generated images (this has to map to img_out_dir)",
                typ_="eg: images",
                exam="/images"),
        ])


    cfg.add_section("data-collection", desc="These settings affect the data collection. If changed, they will affect how the database is being filled in the future.", entries=[
        CFG_Entry("unique_visitor_is_ip_address",
                dflt=False,
                desc="whether a unique visitor is only identified by IP address",
                typ_=bool),
        CFG_Entry("human_needs_success",
                dflt=True,
                desc="whether a visitor needs at least one successful request to be a human",
                typ_=bool),
        CFG_Entry("status_300_is_success",
                dflt=True,
                desc="whether a request with 30x HTTP status counts as successful request",
                typ_=bool),

        CFG_Entry("delete_ip_addresses",  # TODO: Implement
                dflt=True,
                desc="delete all ip addresses after the collection is done",
                typ_=bool),

        CFG_Entry("request_location_blacklist",
                desc="don't collect requests to locations that match this regex",
                typ_=[regexp, None],
                exam="/analytics.*"),
        CFG_Entry("get_visitor_location",
                dflt=False,
                desc="whether to get visitor location information",
                typ_=bool),

        CFG_Entry("do_geoip_rankings",  # TODO: is used?
                dflt=False,
                desc="whether to generate country and city rankings using GeoIP (requires GeoIP Database)",
                typ_=bool),
        CFG_Entry("get_cities_for_countries",
                desc="countries for which the GeoIP needs to be resolved at city level",
                typ_="list of capitalized ISO 3166-1 alpha-2 country codes",
                exam="AT, BE, BG, HR, CY, CZ, DK, EE, FI, FR, DE, GZ, HU, IE, IT, LV, LT, LU, MT, NL, PL, PT, RO, SK, SI, ES, SE"),
        CFG_Entry("geoip_only_humans", # TODO: is used?
                dflt=True,
                desc="whether to use only humans for GeoIP rankings (requires GeoIP Database)",
                typ_=bool),
        ])

# cfg.add_section("data-visualization", desc="", entries=[

    cfg.add_section("rankings", desc="", entries=[
        comment("""
    Explanation for blacklists and whitelists:
    If a blacklist is given: values that fully match the blacklist are excluded
    If a whitelist is given: values that do not fully match the whitelist are excluded
    Both are optional: you can provide, none or both
        """.strip("\n")),
        CFG_Entry("city_ranking_blacklist",
                typ_=[regexp, None],
                exam="City in .*"),
        CFG_Entry("city_ranking_whitelist",
                typ_=[regexp, None]),
        CFG_Entry("country_ranking_blacklist",
                typ_=[regexp, None]),
        CFG_Entry("country_ranking_whitelist",
                typ_=[regexp, None]),

        CFG_Entry("route_ranking_blacklist",
                typ_=[regexp, None],
                exam=r".*\.((css)|(txt))"),
        CFG_Entry("route_ranking_whitelist",
                typ_=[regexp, None],
                exam=r".*\.((php)|(html)|(php)|(png)|(jpeg)|(jpg)|(svg)|(gif))"),
        CFG_Entry("route_ranking_plot_max_routes",
                dflt=20,
                desc="maximum number of entries in route ranking",
                typ_=int),
        CFG_Entry("route_ranking_ignore_404",
                dflt=True,
                desc="whether to ignore non-existing routes in ranking",
                typ_=bool),
        # TODO add groups
        # Entry("route_groups",
                # desc="route groups for images",
                # typ_=[regexp, None],
                # exam="*.gif, *.jpeg, *.jpg, *.png, *.svg".replace(", ", "\n")),

        CFG_Entry("referer_ranking_blacklist",
                dflt="-",
                typ_=[regexp, None],
                exam="Example: exclude '-' (nginx sets this when there is no referer)"),
        CFG_Entry("referer_ranking_whitelist",
                typ_=[regexp, None]),
        CFG_Entry("referer_ranking_ignore_protocol",
                dflt=True,
                desc="whether to ignore protocol in referer ranking (if True: https://domain.com == http://domain.com -> domain.com)",
                typ_=bool),
        CFG_Entry("referer_ranking_ignore_subdomain",
                dflt=False,
                desc="whether to ignore subdomains inreferer ranking (if True: sub.domain.com == another.sub2.domain.com -> domain.com)",
                typ_=bool),
        CFG_Entry("referer_ranking_ignore_route",
                dflt=True,
                desc="whether to ignore route in referer ranking (if True: domain.com/route1 == domain.com/route2 -> domain.com)",
                typ_=bool),
        ])

    cfg.add_section("plots", desc="", entries=[
        CFG_Entry("plot_dpi",
                dflt=300,
                desc="DPI for plots",
                typ_=int),
        CFG_Entry("plot_size_broad",
                dflt="14, 5",
                desc="plot size for broad plots: width, heigh",
                typ_=(int, int)),
        CFG_Entry("plot_size_narrow",
                dflt="7, 5",
                desc="plot size for narrow plots: width, height",
                typ_=(int, int)),
        ])

    with open("generated-default.cfg", "w") as file:
        file.write(f"{cfg}")

def get_bool(bool_str: str, fallback=False):
    if bool_str in ["true", "True"]: return True
    elif bool_str in ["false", "False"]: return False
    return fallback

def get_iterable(s, original_iterable, require_same_length=False):
    val_type = str
    if len(original_iterable) > 0: val_type = type(original_iterable[0])
    new_iter = type(original_iterable)(val_type(v.strip(" ")) for v in s.split(","))
    if require_same_length and len(original_iterable) != len(new_iter):
        raise Exception(f"{new_iter} does not have the same length as {original_iterable}")
    return new_iter


def read_settings_file(filepath: str, settings:dict, ignore_invalid_lines=True, allow_new_keys=False, convert_to_type=True):
    ignore_invalid_lines = False
    lines = []
    with open(filepath, "r") as file:
        lines = file.readlines()

    for i in range(len(lines)):
        line = lines[i].strip("\n ")
        if line.startswith("#") or len(line) == 0: continue
        vals = line.split("=")
        if not len(vals) == 2:
            if ignore_invalid_lines: continue
            else: raise KeyError(f"Invalid line: '{line}'")
        vals[0] = vals[0].strip(" ")
        if not allow_new_keys and vals[0] not in settings.keys():
            if ignore_invalid_lines: continue
            else: raise KeyError(f"Invalid key: '{vals[0]}'")
        if convert_to_type and not isinstance(settings[vals[0]], str|list|None):
            if isinstance(settings[vals[0]], bool):
                settings[vals[0]] = get_bool(vals[1].strip(" "), fallback=settings[vals[0]])
            elif isinstance(settings[vals[0]], tuple):
                try:
                    settings[vals[0]] = get_iterable(vals[1], settings[vals[0]], require_same_length=True)
                except Exception as e:
                    if not ignore_invalid_lines: raise e
                    else: continue
            elif isinstance(settings[vals[0]], list):
                try:
                    settings[vals[0]] = get_iterable(vals[1], settings[vals[0]], require_same_length=False)
                except Exception as e:
                    if not ignore_invalid_lines: raise e
                    else: continue
            else:
                try:
                    settings[vals[0]] = type(settings[vals[0]])(vals[1].strip(" "))
                except Exception as e:
                    if not ignore_invalid_lines: raise e
                    else: continue
        else:
            settings[vals[0]] = vals[1].strip(" ")


class ReginaSettings:
    def __init__(self, config_file):
        parser = ConfigParser()
        # with open(config_file, "r") as file
        # default settings, these are overwriteable through a config file
        self._settings = {
            # GENERAL
            "server_name": "default_sever",
            # DATA COLLECTION
            "access_log": "",
            "db": "",
            "locs_and_dirs": [],
            "auto_group_filetypes": [],
            "filegroups": "",
            "request_location_blacklist": "",
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
            "city_ranking_blacklist": "",
            "country_ranking_blacklist": "",
            # "file_ranking_whitelist": r".*\.((txt)|(html)|(css)|(php)|(png)|(jpeg)|(jpg)|(svg)|(gif))",
            "file_ranking_whitelist": r".*\.(html)",
            "file_ranking_ignore_error_files": False,  # skip files that only had unsuccessful requests (status < 300)
            "referer_ranking_ignore_protocol": True,
            "referer_ranking_ignore_subdomain": False,
            "referer_ranking_ignore_location": True,
            "referer_ranking_ignore_tld": False,
            "referer_ranking_whitelist": r"^[^\-].*",  # minus means empty
            "visitor_agent_ranking_whitelist": r"",
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


        def __getitem__(self, key):
            return self._settings[key]

        def __setitem__(self, key, value):
            """
            set key to value.
            if key already exists, TypeError is raised if value is not of the same type as the current value
            """
            if key in self._settings.keys():
                if type(value) != type(self._settings[key]):
                    raise TypeError(f"ReginaSettings: Trying to set value of '{key}' to '{value}' of type '{type(value)}', but the current type is '{type(self._settings[key])}'.")
            self._settings[key] = value
