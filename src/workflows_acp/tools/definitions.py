from typing import Literal

from ..models import Tool
from .bash import bash_output, execute_command
from .filesystem import (
    read_file,
    grep_file_content,
    glob_paths,
    describe_dir_content,
    write_file,
    edit_file,
)
from .agentfs import (
    read_file_agentfs,
    grep_file_content_agentfs,
    glob_paths_agentfs,
    describe_dir_content_agentfs,
    write_file_agentfs,
    edit_file_agentfs,
)
from .memory import write_memory, read_memory
from .todo import create_todos, list_todos, update_todo

describe_dir_content_tool = Tool(
    name="describe_dir_content",
    description="Describes the contents of a directory, listing files and subfolders.",
    fn=describe_dir_content,
)

read_file_tool = Tool(
    name="read_file",
    description="Reads the contents of a file and returns it as a string.",
    fn=read_file,
)

grep_file_content_tool = Tool(
    name="grep_file_content",
    description="Searches for a regex pattern in a file and returns all matches.",
    fn=grep_file_content,
)

glob_paths_tool = Tool(
    name="glob_paths",
    description="Finds files in a directory matching a glob pattern.",
    fn=glob_paths,
)

write_file_tool = Tool(
    name="write_file",
    description="Writes content to a file, with an option to overwrite.",
    fn=write_file,
)

edit_file_tool = Tool(
    name="edit_file",
    description="Edits a file by replacing occurrences of a string with another string.",
    fn=edit_file,
)

describe_dir_content_tool_agentfs = Tool(
    name="describe_dir_content",
    description="Describes the contents of a directory, listing files and subfolders.",
    fn=describe_dir_content_agentfs,
)

read_file_tool_agentfs = Tool(
    name="read_file",
    description="Reads the contents of a file and returns it as a string.",
    fn=read_file_agentfs,
)

grep_file_content_tool_agentfs = Tool(
    name="grep_file_content",
    description="Searches for a regex pattern in a file and returns all matches.",
    fn=grep_file_content_agentfs,
)

glob_paths_tool_agentfs = Tool(
    name="glob_paths",
    description="Finds files and folders in a directory matching a regex pattern.",
    fn=glob_paths_agentfs,
)

write_file_tool_agentfs = Tool(
    name="write_file",
    description="Writes content to a file, with an option to overwrite.",
    fn=write_file_agentfs,
)

edit_file_tool_agentfs = Tool(
    name="edit_file",
    description="Edits a file by replacing occurrences of a string with another string.",
    fn=edit_file_agentfs,
)

execute_command_tool = Tool(
    name="execute_command",
    description="Executes a shell command with arguments. Optionally waits for completion.",
    fn=execute_command,
)

bash_output_tool = Tool(
    name="bash_output",
    description="Retrieves the stdout and stderr output of a previously started background process by PID.",
    fn=bash_output,
)

write_memory_tool = Tool(
    name="write_memory",
    description="Writes a memory with content and relevance score to persistent storage.",
    fn=write_memory,
)

read_memory_tool = Tool(
    name="read_memory",
    description="Reads the most recent and relevant memory records from persistent storage.",
    fn=read_memory,
)

create_todos_tool = Tool(
    name="create_todos",
    description="Creates a TODO list with specified items and statuses.",
    fn=create_todos,
)

list_todos_tool = Tool(
    name="list_todos",
    description="Lists all TODO items and their statuses.",
    fn=list_todos,
)

update_todo_tool = Tool(
    name="update_todo",
    description="Updates the status of a TODO item.",
    fn=update_todo,
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
    write_memory_tool,
    read_memory_tool,
    create_todos_tool,
    list_todos_tool,
    update_todo_tool,
]

AGENTFS_TOOLS = [
    describe_dir_content_tool_agentfs,
    read_file_tool_agentfs,
    grep_file_content_tool_agentfs,
    glob_paths_tool_agentfs,
    write_file_tool_agentfs,
    edit_file_tool_agentfs,
    execute_command_tool,
    bash_output_tool,
    write_memory_tool,
    read_memory_tool,
    create_todos_tool,
    list_todos_tool,
    update_todo_tool,
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
    "write_memory",
    "read_memory",
    "create_todos",
    "list_todos",
    "update_todo",
]


def filter_tools(names: list[DefaultToolType], use_agentfs: bool = False) -> list[Tool]:
    tools: list[Tool] = []
    to_filter = TOOLS if not use_agentfs else AGENTFS_TOOLS
    for name in names:
        for tool in to_filter:
            if tool.name == name:
                tools.append(tool)
                break
    return tools
