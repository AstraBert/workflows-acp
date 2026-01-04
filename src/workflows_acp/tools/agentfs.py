import os
import re

from agentfs_sdk import AgentFS, AgentFSOptions
from agentfs_sdk.errors import ErrnoException
from rich.progress import track
from pathlib import Path
from typing import cast, Literal
from .todo import _find_git_root
from ..constants import AGENTFS_FILE, DEFAULT_TO_AVOID, DEFAULT_TO_AVOID_FILES


def _add_to_gitignore(git_root: Path) -> None:
    gitignore = git_root / ".gitignore"
    to_write = f"\n# agentfs database\n{str(AGENTFS_FILE)}*\n"
    if gitignore.exists():
        if to_write not in gitignore.read_text():
            with open(gitignore, "a") as f:
                f.write(to_write)
    else:
        with open(gitignore, "a") as f:
            f.write(to_write)


async def configure_agentfs() -> AgentFS:
    git_root = _find_git_root()
    if git_root is not None:
        _add_to_gitignore(git_root)
    return await AgentFS.open(AgentFSOptions(path=str(AGENTFS_FILE)))


async def _load_noprogress(
    agentfs: AgentFS, dirs_to_avoid: list[str], files_to_avoid: list[str]
) -> None:
    for root, dirs, files in os.walk(Path.cwd()):
        dirs[:] = [d for d in dirs if d not in dirs_to_avoid]
        files[:] = [f for f in files if f not in files_to_avoid]
        for file in files:
            path = os.path.join(root, file)
            with open(path, "rb") as f:
                content = f.read()
                await agentfs.fs.write_file(path, content=content)


async def _load_progress(
    agentfs: AgentFS, dirs_to_avoid: list[str], files_to_avoid: list[str]
) -> None:
    for root, dirs, files in track(
        os.walk(Path.cwd()), description="Uploading files to AgentFS"
    ):
        dirs[:] = [d for d in dirs if d not in dirs_to_avoid]
        files[:] = [f for f in files if f not in files_to_avoid]
        for file in files:
            path = os.path.join(root, file)
            with open(path, "rb") as f:
                content = f.read()
                await agentfs.fs.write_file(path, content=content)


async def load_all_files(
    to_avoid_dirs: list[str] | None = None,
    to_avoid_files: list[str] | None = None,
    progress: bool = False,
) -> None:
    agentfs = await configure_agentfs()
    dirs_to_avoid = to_avoid_dirs or DEFAULT_TO_AVOID
    files_to_avoid = to_avoid_files or DEFAULT_TO_AVOID_FILES
    if progress:
        await _load_progress(agentfs, dirs_to_avoid, files_to_avoid)
    else:
        await _load_noprogress(agentfs, dirs_to_avoid, files_to_avoid)


async def _is_accessible_path(
    agentfs: AgentFS, path: str, check: Literal["file", "dir"]
) -> bool:
    try:
        if check == "dir":
            return (await agentfs.fs.stat(path)).is_directory()
        else:
            return (await agentfs.fs.stat(path)).is_file()
    except ErrnoException:
        return False


async def describe_dir_content_agentfs(directory: str) -> str:
    """
    Describe the contents of a directory, listing files and subfolders.

    Args:
        directory (str): Path to the directory.
    Returns:
        str: Description of the directory contents or an error message.
    """
    agentfs = await configure_agentfs()
    directory = str(Path(directory).resolve())
    if not await _is_accessible_path(agentfs, directory, "dir"):
        return f"Directory {directory} does not exist"
    children = await agentfs.fs.readdir(directory)
    if not children:
        return f"Directory {directory} is empty"
    description = f"Content of {directory}\n"
    files = []
    directories = []
    for child in children:
        fullpath = os.path.join(directory, child)
        if (await agentfs.fs.stat(fullpath)).is_file():
            files.append(fullpath)
        else:
            directories.append(fullpath)
    description += "FILES:\n- " + "\n- ".join(files)
    if not directories:
        description += "\nThis folder does not have any sub-folders"
    else:
        description += "\nSUBFOLDERS:\n- " + "\n- ".join(directories)
    return description


async def read_file_agentfs(file_path: str) -> str:
    """
    Read and return the contents of a file.

    Args:
        file_path (str): Path to the file.
    Returns:
        str: File contents or an error message if the file does not exist.
    """
    file_path = str(Path(file_path).resolve())
    agentfs = await configure_agentfs()
    if not await _is_accessible_path(agentfs, file_path, "file"):
        return f"No such file: {file_path}"
    text = await agentfs.fs.read_file(file_path)
    return cast(str, text)


async def grep_file_content_agentfs(file_path: str, pattern: str) -> str:
    """
    Search for a regex pattern in a file's content and return all matches.

    Args:
        file_path (str): Path to the file.
        pattern (str): Regex pattern to search for.
    Returns:
        str: List of matches or a message if no matches are found.
    """
    file_path = str(Path(file_path).resolve())
    agentfs = await configure_agentfs()
    if not await _is_accessible_path(agentfs, file_path, "file"):
        return f"No such file: {file_path}"
    content = await agentfs.fs.read_file(file_path)
    r = re.compile(pattern=pattern, flags=re.MULTILINE)
    matches = r.findall(cast(str, content))
    if matches:
        return f"MATCHES for {pattern} in {file_path}:\n\n- " + "\n- ".join(matches)
    return "No matches found"


async def glob_paths_agentfs(directory: str, pattern: str) -> str:
    """
    Find all paths in a directory matching a regex pattern.

    Args:
        directory (str): Path to the directory.
        pattern (str): Regex pattern to match files or folders.
    Returns:
        str: List of matching paths or a message if no matches are found.
    """
    directory = str(Path(directory).resolve())
    agentfs = await configure_agentfs()
    if not await _is_accessible_path(agentfs, directory, "dir"):
        return f"Directory {directory} does not exist"
    entries = await agentfs.fs.readdir(directory)
    pat = re.compile(pattern)
    matches = []
    for entry in entries:
        if pat.match(entry) is not None:
            matches.append(entry)
    if matches:
        return f"MATCHES for {pattern} in {directory}:\n\n- " + "\n- ".join(matches)
    return "No matches found"


async def write_file_agentfs(file_path: str, content: str, overwrite: bool) -> str:
    """
    Write content to a file, optionally overwriting if it exists.

    Args:
        file_path (str): Path to the file.
        content (str): Content to write.
        overwrite (bool): Whether to overwrite the file if it exists.
    Returns:
        str: Success or error message.
    """
    file_path = str(Path(file_path).resolve())
    agentfs = await configure_agentfs()
    if (await _is_accessible_path(agentfs, file_path, "file")) and not overwrite:
        return f"File {file_path} already exist and overwrite is set to False. Cannot proceed"
    else:
        try:
            await agentfs.fs.write_file(file_path, content=content, encoding="utf-8")
        except Exception as e:
            return f"There was an error while writing the file: {e}"
        return "File written with success"


async def edit_file_agentfs(
    file_path: str, old_string: str, new_string: str, count: int = -1
) -> str:
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
    file_path = str(Path(file_path).resolve())
    agentfs = await configure_agentfs()
    if not await _is_accessible_path(agentfs, file_path, "file"):
        return f"No such file: {file_path}"
    content = await agentfs.fs.read_file(file_path)
    content = cast(str, content)
    content = content.replace(old_string, new_string, count)
    try:
        await agentfs.fs.write_file(file_path, content=content, encoding="utf-8")
    except Exception as e:
        return f"An error occurred while editing the file: {e}"
    return "File edited with success"
