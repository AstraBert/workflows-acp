from typing import Literal

from ..models import Tool
from .bash import bash_output, execute_command
from .filesystem import read_file, grep_file_content, glob_paths, describe_dir_content, write_file, edit_file

describe_dir_content_tool = Tool(
    name="describe_dir_content",
    description="Describes the contents of a directory, listing files and subfolders.",
    fn=describe_dir_content
)

read_file_tool = Tool(
    name="read_file",
    description="Reads the contents of a file and returns it as a string.",
    fn=read_file
)

grep_file_content_tool = Tool(
    name="grep_file_content",
    description="Searches for a regex pattern in a file and returns all matches.",
    fn=grep_file_content
)

glob_paths_tool = Tool(
    name="glob_paths",
    description="Finds files in a directory matching a glob pattern.",
    fn=glob_paths
)

write_file_tool = Tool(
    name="write_file",
    description="Writes content to a file, with an option to overwrite.",
    fn=write_file
)

edit_file_tool = Tool(
    name="edit_file",
    description="Edits a file by replacing occurrences of a string with another string.",
    fn=edit_file
)

execute_command_tool = Tool(
    name="execute_command",
    description="Executes a shell command with arguments. Optionally waits for completion.",
    fn=execute_command
)

bash_output_tool = Tool(
    name="bash_output",
    description="Retrieves the stdout and stderr output of a previously started background process by PID.",
    fn=bash_output
)

# List of all tools
TOOLS = [
    describe_dir_content_tool,
    read_file_tool,
    grep_file_content_tool,
    glob_paths_tool,
    write_file_tool,
    edit_file_tool,
    execute_command_tool,
    bash_output_tool,
]

DefaultToolType = Literal[
    "describe_dir_content",
    "read_file",
    "grep_file_content",
    "glob_paths",
    "write_file",
    "edit_file",
    "execute_command",
    "bash_output",
]

def filter_tools(names: list[DefaultToolType]) -> list[Tool]:
    tools: list[Tool] = []
    for name in names:
        for tool in TOOLS:
            if tool.name == name:
                tools.append(tool)
                break
    return tools
            