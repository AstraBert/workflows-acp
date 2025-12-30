import os
import re
import glob


def describe_dir_content(directory: str) -> str:
    if not os.path.exists(directory) or not os.path.isdir(directory):
        return f"No such directory: {directory}"
    children = os.listdir(directory)
    if not children:
        return f"Directory {directory} is empty"
    description = f"Content of {directory}\n"
    files = []
    directories = []
    for child in children:
        fullpath = os.path.join(directory, child)
        if os.path.isfile(fullpath):
            files.append(fullpath)
        else:
            directories.append(fullpath)
    description += "FILES:\n- " + "\n- ".join(files)
    if not directories:
        description += "\nThis folder does not have any sub-folders"
    else:
        description += "\nSUBFOLDERS:\n- " + "\n- ".join(directories)
    return description


def read_file(file_path: str) -> str:
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return f"No such file: {file_path}"
    with open(file_path, "r") as f:
        return f.read()


def grep_file_content(file_path: str, pattern: str) -> str:
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return f"No such file: {file_path}"
    with open(file_path, "r") as f:
        content = f.read()
    r = re.compile(pattern=pattern, flags=re.MULTILINE)
    matches = r.findall(content)
    if matches:
        return f"MATCHES for {pattern} in {file_path}:\n\n- " + "\n- ".join(matches)
    return "No matches found"


def glob_paths(directory: str, pattern: str) -> str:
    if not os.path.exists(directory) or not os.path.isdir(directory):
        return f"No such directory: {directory}"
    matches = glob.glob(f"./{directory}/{pattern}")
    if matches:
        return f"MATCHES for {pattern} in {directory}:\n\n- " + "\n- ".join(matches)
    return "No matches found"


def write_file(file_path: str, content: str, overwrite: bool) -> str:
    if os.path.exists(file_path) and os.path.isfile(file_path) and not overwrite:
        return f"File {file_path} already exist and overwrite is set to False. Cannot proceed"
    else:
        with open(file_path, "w") as f:
            f.write(content)
        return "File written with success"


def edit_file(file_path: str, old_string: str, new_string: str, count: int = -1) -> str:
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return f"No such file: {file_path}"
    with open(file_path, "r") as f:
        content = f.read()
    content = content.replace(old_string, new_string, count=count)  # type: ignore[no-matching-overload]
    with open(file_path, "w") as f:
        f.write(content)
    return "File edited with success"
