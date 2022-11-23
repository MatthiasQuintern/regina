
def read_settings_file(filepath: str, settings:dict, ignore_invalid_lines=True, allow_new_keys=False, convert_to_type=True):
    lines = []
    with open(filepath, "r") as file:
        lines = file.readlines()

    for i in range(len(lines)):
        line = lines[i].strip("\n ")
        if line.startswith("#"): continue
        vals = line.split("=")
        if not len(vals) == 2:
            if ignore_invalid_lines: continue
            else: raise KeyError(f"Invalid line: '{line}'")
        vals[0] = vals[0].strip(" ")
        if not allow_new_keys and vals[0] not in settings.keys():
            if ignore_invalid_lines: continue
            else: raise KeyError(f"Invalid key: '{vals[0]}'")
        if convert_to_type and type(settings[vals[0]]) not in [str, None]:
            try:
                settings[vals[0]] = type(settings[vals[0]])(vals[1].strip(" "))
            except Exception as e:
                if not ignore_invalid_lines: raise e
                else: continue
        else:
            settings[vals[0]] = vals[1].strip(" ")
