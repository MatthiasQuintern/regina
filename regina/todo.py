

def get_files_from_dir_rec(p: str, files: list[str]):
    """recursivly append all files to files"""
    pdebug("get_files_from_dir_rec:",p)
    if path.isfile(p):
        files.append(p)
    elif path.isdir(p):
        for p_ in listdir(p):
            get_files_from_dir_rec(p + "/" + p_, files)


def create_filegroups(cursor: sql.Cursor, filegroup_str: str):
    """
    TODO: make re-usable (alter groups when config changes)
    """
    # filegroup_str: 'name1: file1, file2, file3; name2: file33'
    groups = filegroup_str.strip(";").split(";")
    pdebug("create_filegroups:", groups)
    for group in groups:
        name, vals = group.split(":")
        # create/get group
        if sql_exists(cursor, "", [("groupname", name)]):
            group_id = sql_select(cursor, "", [("groupname", name)])[0][0]
        else:
            group_id = sql_max(cursor, "", "group_id") + 1
            sql_insert(cursor, "", [(group_id, name)])
        # pdebug("create_filegroups: group_id", group_id)
        # create/edit file
        for filename in vals.split(","):
            if sql_exists(cursor, "", [("filename", filename)]):  # if exist, update
                cursor.execute(f"UPDATE file SET group_id = {group_id} WHERE filename = 'fil'")
            else:
                sql_insert(cursor, "", [[filename, group_id]])
