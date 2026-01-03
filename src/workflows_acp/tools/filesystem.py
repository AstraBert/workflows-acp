import os
import re
import glob


def describe_dir_content(directory: str) -> str:
    """
    Describe the contents of a directory, listing files and subfolders.

    Args:
        directory (str): Path to the directory.
    Returns:
        str: Description of the directory contents or an error message.
    """
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
    """
    Read and return the contents of a file.

    Args:
        file_path (str): Path to the file.
    Returns:
        str: File contents or an error message if the file does not exist.
    """
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return f"No such file: {file_path}"
    with open(file_path, "r") as f:
        return f.read()


def grep_file_content(file_path: str, pattern: str) -> str:
    """
    Search for a regex pattern in a file's content and return all matches.

    Args:
        file_path (str): Path to the file.
        pattern (str): Regex pattern to search for.
    Returns:
        str: List of matches or a message if no matches are found.
    """
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
    """
    Find all paths in a directory matching a glob pattern.

    Args:
        directory (str): Path to the directory.
        pattern (str): Glob pattern to match files or folders.
    Returns:
        str: List of matching paths or a message if no matches are found.
    """
    if not os.path.exists(directory) or not os.path.isdir(directory):
        return f"No such directory: {directory}"
    matches = glob.glob(f"./{directory}/{pattern}")
    if matches:
        return f"MATCHES for {pattern} in {directory}:\n\n- " + "\n- ".join(matches)
    return "No matches found"


def write_file(file_path: str, content: str, overwrite: bool) -> str:
    """
    Write content to a file, optionally overwriting if it exists.

    Args:
        file_path (str): Path to the file.
        content (str): Content to write.
        overwrite (bool): Whether to overwrite the file if it exists.
    Returns:
        str: Success or error message.
    """
    if os.path.exists(file_path) and os.path.isfile(file_path) and not overwrite:
        return f"File {file_path} already exist and overwrite is set to False. Cannot proceed"
    else:
        with open(file_path, "w") as f:
            f.write(content)
        return "File written with success"


def edit_file(file_path: str, old_string: str, new_string: str, count: int = -1) -> str:
    """
    Replace occurrences of a string in a file with a new string.

    Args:
        file_path (str): Path to the file.
        old_string (str): String to be replaced.
        new_string (str): Replacement string.
        count (int): Maximum number of replacements (-1 for all).
    Returns:
        str: Success or error message.
    """
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return f"No such file: {file_path}"
    with open(file_path, "r") as f:
        content = f.read()
    content = content.replace(old_string, new_string, count)
    with open(file_path, "w") as f:
        f.write(content)
    return "File edited with success"
