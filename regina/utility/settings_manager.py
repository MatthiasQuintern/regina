
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
