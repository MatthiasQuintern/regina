from configparser import ConfigParser
import re
from os import path, access, R_OK, W_OK, X_OK

"""
Classes and methods for managing regina configuration

Using CFG_File and CFG_Entry, you set defaults and type restrictions for
a dictionary like ReginaSettings object and also export the defaults as a .cfg file
"""

def comment(s):
    return "# " + s.replace("\n", "\n# ").strip("# ")


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

    def has_permissions(self, p):

        def get_first_existing_path(p_):
            """
            Returns the first existing part of the given path.
            """
            p_parent = path.dirname(p_)
            while p_ != p_parent:
                if path.exists(p_):
                    return p_
                p_ = p_parent
                p_parent = path.dirname(p_)
            if path.exists(p_):
                return p_
            return None

        p_ = get_first_existing_path(p)
        # print(f"has_permissions: path='{p}': first existing part='{p_}'")
        if not p_: return False

        for permission in self.permissions:
            if permission == 'r' and not access(p_, R_OK):
                return False
            elif permission == 'w' and not access(p_, W_OK):
                return False
            elif permission == 'x' and not access(p_, X_OK):
                return False
        return True


class CFG_Entry:
    """
    key - value pair in a cfg file
    extra parameters for comments on top of the key - value pair
    """
    types = str|Path|None|type[re.Pattern]|type[str]|type[bool]|type[int]
    def __init__(self, key, dflt=None, typ_: types|list[types]|type[tuple]=str, desc="", exam=""):   # all 4 letters -> nice indent
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
            if t == str:                return "string"
            if t == bool:               return "True/False"
            if t == int:                return "int"
            if t == float:              return "float"
            if t == re.Pattern:         return "regexp"
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

    def get_val_str(self, x):
        if type(x) == re.Pattern: return x.pattern
        elif type(x) == tuple:
            s = ""
            for i in range(len(x)):
                s += f"{x[i]}, "
            return s.strip(", ")
        return str(x)

    def __repr__(self):
        s = ""
        if self.descripton:             s += f"{comment(self.descripton)}\n"
        if self.type_ is not None:      s += f"{comment('type: ' + self.type_str())}\n"
        # if self.example:              s += f"{comment('eg: ' + self.example)}\n"
        if self.example:                s += comment(f"{self.key} = {self.example}\n")
        s += f"{self.key} = "
        if self.default is not None:    s += self.get_val_str(self.default)
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
            s += f"\n[{name}]\n"
            for entry in entries:
                s += f"{entry}\n"
        s += comment(self.footer)
        return s


#
# CONVERSION
#
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

def get_None(x):
    if x in [None, ""]:
        return None
    else:
        raise ValueError(f"'{x}' is not None")

def get_str(x):
    if x:
        return str(x)
    else:
        raise ValueError(f"'{x}' is not a valid string")


class ReginaSettings:
    # (new val, old val) -> converted new val
    converters = {
        int:    lambda x, _: int(x),
        float:  lambda x, _: float(x),
        tuple:  lambda x, old: get_iterable(x, old, require_same_length=True),
        re.Pattern: lambda x, _: re.compile(x),
        str:    lambda x, _: get_str(x),
        bool:   lambda x, _: get_bool(x),
        None:   lambda x, _: get_None(x),
    }

    def __init__(self, cfg: CFG_File):
        """
        create from CFG_File
        this way, information about the desired type is preserved
        """
        self._settings: dict[str, dict] = {}
        self._types:    dict[str, dict] = {}
        for sec_name, _, entries in cfg.sections:
            self._settings[sec_name] = {}
            self._types[sec_name] = {}
            for entry in entries:
                if type(entry) != CFG_Entry: continue  # filter strings/comments
                self._settings[sec_name][entry.key] = entry.default
                self._types[sec_name][entry.key] = entry.type_

    def load(self, cfg_path: str):
        parser = ConfigParser()
        parser.read(cfg_path)  # TODO: add other files
        for section, vals in parser.items():
            allow_new = True if section in ["route-groups"] else False
            for key, val in vals.items():
                self.set(section, key, val, allow_new=allow_new)


    def __getitem__(self, section):
        return self._settings[section]

    def set(self, section: str, key: str, value, allow_new=False):
        """
        set key in section to value.
        if key already exists:
            try to convert value to one of the allowed types
            if failed, raise TypeError
        if the key does not exist:
            if allow_new: insert
            else raise KeyError, new values are not allowed
        """
        if section not in self._settings:
            if allow_new:
                self._settings[section] = {}
                self._types[section] = {}
            else:
                raise KeyError(f"ReginaSettings: key '{key}': Invalid section: {section}")

        def convert(value, to_type_):
            if isinstance(to_type_, Path):
                # check if user has permissions for the given path
                value = path.expanduser(value)
                if not to_type_.has_permissions(value):
                    raise ValueError(f"ReginaSettings: key '{key}': Insufficent permissions for path '{value}'. '{to_type_.permissions}' are required.")
            elif type(to_type_) == list:  # list of types
                success = False
                for t in to_type_:
                    try:
                        value = convert(value, t)
                        success = True
                        break;
                    except Exception as e:
                        pass
                        # print(f"Exception while trying t={t}")
                if not success:
                    raise TypeError(f"ReginaSettings: key: '{key}': Could not convert '{value}' to one of these types: '{to_type_}'")
            elif type(to_type_) == str:   # allow if type is descriptive string
                pass
            elif to_type_ in ReginaSettings.converters:
                try:
                    value = ReginaSettings.converters[to_type_](value, current_val)
                except Exception as e:
                    raise Exception(f"ReginaSettings: key '{key}': {e}")
            elif type(to_type_) in ReginaSettings.converters:
                try:
                    value = ReginaSettings.converters[type(to_type_)](value, current_val)
                except Exception as e:
                    raise Exception(f"ReginaSettings: key '{key}': {e}")
            elif type(value) != type(current_val):
                # print(type(to_type_), type(value), ReginaSettings.converters.keys())
                raise TypeError(f"ReginaSettings: key: '{key}': Trying to set value '{value}' of type '{type(value)}', but the current type is '{type(current_val)}'.")
            return value

        if key in self._settings[section]:
            current_val = self._settings[section][key]
            type_ = self._types[section][key]
            value = convert(value, type_)
        elif not allow_new:
            raise KeyError(f"ReginaSettings: key '{key}' is unsupported in section '{section}'")
        self._settings[section][key] = value

    def __repr__(self):
        s = ""
        for section in self._settings.keys():
            s += f"{section}:\n"
            for k, v in self._settings[section].items():
                s += f"\t{k:12}: {v}\n"
        return s
